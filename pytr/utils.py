#!/usr/bin/env python3

import logging
import coloredlogs
import json
import requests
from datetime import datetime
from packaging import version


log_level = None


def get_logger(name=__name__, verbosity=None):
    '''
    Colored logging

    :param name: logger name (use __name__ variable)
    :param verbosity:
    :return: Logger
    '''
    global log_level
    if verbosity is not None:
        if log_level is None:
            log_level = verbosity
        else:
            raise RuntimeError('Verbosity has already been set.')

    shortname = name.replace('pytr.', '')
    logger = logging.getLogger(shortname)

    # no logging of libs
    logger.propagate = False

    if log_level == 'debug':
        fmt = '%(asctime)s %(name)-9s %(levelname)-8s %(message)s'
        datefmt = '%Y-%m-%d %H:%M:%S%z'
    else:
        fmt = '%(asctime)s %(message)s'
        datefmt = '%H:%M:%S'

    fs = {
        'asctime': {'color': 'green'},
        'hostname': {'color': 'magenta'},
        'levelname': {'color': 'red', 'bold': True},
        'name': {'color': 'magenta'},
        'programname': {'color': 'cyan'},
        'username': {'color': 'yellow'},
    }

    ls = {
        'critical': {'color': 'red', 'bold': True},
        'debug': {'color': 'green'},
        'error': {'color': 'red'},
        'info': {},
        'notice': {'color': 'magenta'},
        'spam': {'color': 'green', 'faint': True},
        'success': {'color': 'green', 'bold': True},
        'verbose': {'color': 'blue'},
        'warning': {'color': 'yellow'},
    }

    coloredlogs.install(level=log_level, logger=logger, fmt=fmt, datefmt=datefmt, level_styles=ls, field_styles=fs)

    return logger


def preview(response, num_lines=5):
    lines = json.dumps(response, indent=2).splitlines()
    head = '\n'.join(lines[:num_lines])
    tail = len(lines) - num_lines

    if tail <= 0:
        return f'{head}\n'
    else:
        return f'{head}\n{tail} more lines hidden'


def check_version(installed_version):
    log = get_logger(__name__)
    try:
        r = requests.get('https://api.github.com/repos/marzzzello/pytr/tags', timeout=1)
    except Exception as e:
        log.error('Could not check for a newer version')
        log.debug(str(e))
        return
    latest_version = r.json()[0]['name']

    if version.parse(installed_version) < version.parse(latest_version):
        log.warning(f'Installed pytr version ({installed_version}) is outdated. Latest version is {latest_version}')
    else:
        log.info('pytr is up to date')


class Timeline:
    def __init__(self, tr):
        self.tr = tr
        self.log = get_logger(__name__)
        self.received_detail = 0
        self.requested_detail = 0
        self.num_timeline_details = 0
        self.events_without_docs = []

    async def get_next_timeline(self, response=None, max_age_timestamp=0):
        '''
        Get timelines and save time in list timelines.
        Extract timeline events and save them in list timeline_events

        '''

        if response is None:
            # empty response / first timeline
            self.log.info('Awaiting #1  timeline')
            # self.timelines = []
            self.num_timelines = 0
            self.timeline_events = []
            await self.tr.timeline()
        else:
            timestamp = response['data'][-1]['data']['timestamp']
            self.num_timelines += 1
            # print(json.dumps(response))
            self.num_timeline_details += len(response['data'])
            for event in response['data']:
                self.timeline_events.append(event)

            after = response['cursors'].get('after')
            if after is None:
                # last timeline is reached
                self.log.info(f'Received #{self.num_timelines:<2} (last) timeline')
                await self._get_timeline_details(5)
            elif max_age_timestamp != 0 and timestamp < max_age_timestamp:
                self.log.info(f'Received #{self.num_timelines+1:<2} timeline')
                self.log.info('Reached last relevant timeline')
                await self._get_timeline_details(5, max_age_timestamp=max_age_timestamp)
            else:
                self.log.info(
                    f'Received #{self.num_timelines:<2} timeline, awaiting #{self.num_timelines+1:<2} timeline'
                )
                await self.tr.timeline(after)

    async def _get_timeline_details(self, num_torequest, max_age_timestamp=0):
        '''
        request timeline details
        '''
        while num_torequest > 0:
            if len(self.timeline_events) == 0:
                self.log.info('All timeline details requested')
                return False

            else:
                event = self.timeline_events.pop()

            action = event['data'].get('action')
            # icon = event['data'].get('icon')
            msg = ''
            if max_age_timestamp != 0 and event['data']['timestamp'] > max_age_timestamp:
                msg += 'Skip: too old'
            # elif icon is None:
            #     pass
            # elif icon.endswith('/human.png'):
            #     msg += 'Skip: human'
            # elif icon.endswith('/CashIn.png'):
            #     msg += 'Skip: CashIn'
            # elif icon.endswith('/ExemptionOrderChanged.png'):
            #     msg += 'Skip: ExemptionOrderChanged'

            elif action is None:
                if event['data'].get('actionLabel') is None:
                    msg += 'Skip: no action'
            elif action.get('type') != 'timelineDetail':
                msg += f"Skip: action type unmatched ({action['type']})"
            elif action.get('payload') != event['data']['id']:
                msg += f"Skip: payload unmatched ({action['payload']})"

            if msg != '':
                self.events_without_docs.append(event)
                self.log.debug(f"{msg} {event['data']['title']}: {event['data'].get('body')} {json.dumps(event)}")
                self.num_timeline_details -= 1
                continue

            num_torequest -= 1
            self.requested_detail += 1
            await self.tr.timeline_detail(event['data']['id'])

    async def timelineDetail(self, response, dl, max_age_timestamp=0):
        '''
        process timeline response and request timelines
        '''

        self.received_detail += 1

        # when all requested timeline events are received request 5 new
        if self.received_detail == self.requested_detail:
            remaining = len(self.timeline_events)
            if remaining < 5:
                await self._get_timeline_details(remaining)
            else:
                await self._get_timeline_details(5)

        # print(f'len timeline_events: {len(self.timeline_events)}')
        isSavingsPlan = False
        if response['subtitleText'] == 'Sparplan':
            isSavingsPlan = True
        else:
            # some savingsPlan don't have the subtitleText == 'Sparplan' but there are actions just for savingsPans
            # but maybe these are unneeded duplicates
            for section in response['sections']:
                if section['type'] == 'actionButtons':
                    for button in section['data']:
                        if button['action']['type'] in ['editSavingsPlan', 'deleteSavingsPlan']:
                            isSavingsPlan = True
                            break

        if response['subtitleText'] != 'Sparplan' and isSavingsPlan is True:
            isSavingsPlan_fmt = ' -- SPARPLAN'
        else:
            isSavingsPlan_fmt = ''

        max_details_digits = len(str(self.num_timeline_details))
        self.log.info(
            f"{self.received_detail:>{max_details_digits}}/{self.num_timeline_details}: "
            + f"{response['titleText']} -- {response['subtitleText']}{isSavingsPlan_fmt}"
        )

        for section in response['sections']:
            if section['type'] == 'documents':
                for doc in section['documents']:
                    try:
                        timestamp = datetime.strptime(doc['detail'], '%d.%m.%Y').timestamp() * 1000
                    except ValueError:
                        timestamp = datetime.now().timestamp() * 1000
                    if max_age_timestamp == 0 or max_age_timestamp < timestamp:
                        # save all savingsplan documents in a subdirectory
                        if isSavingsPlan:
                            dl.dl_doc(doc, response['titleText'], response['subtitleText'], subfolder='Sparplan')
                        else:
                            dl.dl_doc(doc, response['titleText'], response['subtitleText'])

        if self.received_detail == self.num_timeline_details:
            self.log.info('Received all details')
            dl.output_path.mkdir(parents=True, exist_ok=True)
            with open(dl.output_path / 'other_events.json', 'w', encoding='utf-8') as f:
                json.dump(self.events_without_docs, f, ensure_ascii=False, indent=2)
            dl.work_responses()
