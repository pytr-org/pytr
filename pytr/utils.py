#!/usr/bin/env python3

import coloredlogs
import json
import logging
import requests
from datetime import datetime 
from locale import getdefaultlocale
from packaging import version
from .event import Event, i18n
from .translation import setup_translation

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
        r = requests.get('https://api.github.com/repos/pytr-org/pytr/tags', timeout=1)
    except Exception as e:
        log.error('Could not check for a newer version')
        log.debug(str(e))
        return
    latest_version = r.json()[0]['name']

    if version.parse(installed_version) < version.parse(latest_version):
        log.warning(f'Installed pytr version ({installed_version}) is outdated. Latest version is {latest_version}')
    else:
        log.info('pytr is up to date')


def export_transactions(input_path, output_path, lang='auto'):
    '''
    Create a CSV with the deposits and removals ready for importing into Portfolio Performance
    The CSV headers for PP are language dependend

    i18n source from Portfolio Performance:
    https://github.com/buchen/portfolio/blob/93b73cf69a00b1b7feb136110a51504bede737aa/name.abuchen.portfolio/src/name/abuchen/portfolio/messages_de.properties
    https://github.com/buchen/portfolio/blob/effa5b7baf9a918e1b5fe83942ddc480e0fd48b9/name.abuchen.portfolio/src/name/abuchen/portfolio/model/labels_de.properties

    '''
    log = get_logger(__name__)
    if lang == 'auto':
        locale = getdefaultlocale()[0]
        if locale is None:
            lang = 'en'
        else:
            lang = locale.split('_')[0]

    if lang not in ['cs', 'de', 'en', 'es', 'fr', 'it', 'nl', 'pt', 'ru']:
        lang = 'en'
    lang = 'de'
    _ = setup_translation(language=lang)

    # Read relevant deposit timeline entries
    with open(input_path, encoding='utf-8') as f:
        timeline = json.load(f)

    log.info('Write deposit entries')
    with open(output_path, 'w', encoding='utf-8') as f:
        csv_fmt = '{date};{type};{value};{note};{isin};{shares}\n'
        header = csv_fmt.format(date=_("CSVColumn_Date"), type=_("CSVColumn_Type"), \
                                value=_("CSVColumn_Value"), note=_("CSVColumn_Note"), \
                                isin=_("CSVColumn_ISIN"), shares=_("CSVColumn_Shares"))
        f.write(header)

        for event_json in timeline:
            event = Event(event_json)
            if not event.is_pp_relevant:
                continue

            f.write(csv_fmt.format(date=event.date, type=_(event.pp_type), value=event.amount, 
                                    note=(_(event.note)+" "+event.title), isin=event.isin, shares=event.shares))

    log.info('Deposit creation finished!')


class Timeline:
    def __init__(self, tr, max_age_timestamp):
        self.tr = tr
        self.log = get_logger(__name__)
        self.received_detail = 0
        self.requested_detail = 0
        self.events_without_docs = []
        self.events_with_docs = []
        self.num_timelines = 0
        self.timeline_events = {}
        self.max_age_timestamp = max_age_timestamp

    async def get_next_timeline_transactions(self, response=None):
        '''
        Get timelines transactions and save time in list timelines.
        Extract timeline transactions events and save them in list timeline_events

        '''
        if response is None:
            # empty response / first timeline
            self.log.info('Subscribing to #1 timeline transactions')
            self.num_timelines = 0
            await self.tr.timeline_transactions()
        else:
            self.num_timelines += 1
            added_last_event = True
            for event in response['items']:
                if self.max_age_timestamp == 0 or datetime.fromisoformat(event['timestamp'][:19]).timestamp() >= self.max_age_timestamp:
                    event['source'] = "timelineTransaction"
                    self.timeline_events[event['id']] = event
                else:
                    added_last_event = False
                    break

            self.log.info(
                f'Received #{self.num_timelines:<2} timeline transactions'
            )
            after = response['cursors'].get('after')
            if (after is not None) and added_last_event:
                self.log.info(
                f'Subscribing #{self.num_timelines+1:<2} timeline transactions'
                )
                await self.tr.timeline_transactions(after)
            else:
                # last timeline is reached
                self.log.info('Received last relevant timeline transaction')
                await self.get_next_timeline_activity_log()


    async def get_next_timeline_activity_log(self, response=None):
        '''
        Get timelines acvtivity log and save time in list timelines.
        Extract timeline acvtivity log events and save them in list timeline_events

        '''
        if response is None:
            # empty response / first timeline
            self.log.info('Awaiting #1  timeline activity log')
            self.num_timelines = 0
            await self.tr.timeline_activity_log()
        else:
            self.num_timelines += 1
            added_last_event = True
            for event in response['items']:
                if self.max_age_timestamp == 0 or datetime.fromisoformat(event['timestamp'][:19]).timestamp() >= self.max_age_timestamp:
                    if event['id'] in self.timeline_events:
                        self.log.warning(f"Received duplicate event {event['id'] }")
                    event['source'] = "timelineActivity"
                    self.timeline_events[event['id']] = event
                else:
                    added_last_event = False
                    break

            self.log.info(f'Received #{self.num_timelines:<2} timeline activity log')
            after = response['cursors'].get('after')
            if (after is not None) and added_last_event:
                self.log.info(
                    f'Subscribing #{self.num_timelines+1:<2} timeline activity log'
                )
                await self.tr.timeline_activity_log(after)
            else:
                self.log.info('Received last relevant timeline activity log')
                await self._get_timeline_details()

    async def _get_timeline_details(self):
        '''
        request timeline details
        '''
        for event in self.timeline_events.values():
            action = event.get('action')
            msg = ''
            if action is None:
                if event.get('actionLabel') is None:
                    msg += 'Skip: no action'
            elif action.get('type') != 'timelineDetail':
                msg += f"Skip: action type unmatched ({action['type']})"
            elif action.get('payload') != event['id']:
                msg += f"Skip: payload unmatched ({action['payload']})"

            if msg != '':
                self.events_without_docs.append(event)
                self.log.debug(f"{msg} {event['title']}: {event.get('body')} ")
            else:
                self.requested_detail += 1
                await self.tr.timeline_detail_v2(event['id'])
        self.log.info('All timeline details requested')
        return False

    async def process_timelineDetail(self, response, dl):
        '''
        process timeline details response
        download any associated docs
        create other_events.json, events_with_documents.json and account_transactions.csv
        '''

        self.received_detail += 1
        event = self.timeline_events[response['id']]
        event['details'] = response

        max_details_digits = len(str(self.requested_detail))
        self.log.info(
            f"{self.received_detail:>{max_details_digits}}/{self.requested_detail}: "
            + f"{event['title']} -- {event['subtitle']} - {event['timestamp'][:19]}"
        )

        subfolder = {
                'benefits_saveback_execution': 'Saveback',
                'benefits_spare_change_execution': 'RoundUp',
                'ssp_corporate_action_invoice_cash': 'Dividende',
                'CREDIT': 'Dividende',
                'INTEREST_PAYOUT_CREATED': 'Zinsen',
                "SAVINGS_PLAN_EXECUTED":'Sparplan'
            }.get(event["eventType"])

        event['has_docs'] = False
        for section in response['sections']:
            if section['type'] != 'documents':
                continue
            for doc in section['data']:
                event['has_docs'] = True
                try:
                    timestamp = datetime.strptime(doc['detail'], '%d.%m.%Y').timestamp()
                except (ValueError, KeyError):
                    timestamp = datetime.now().timestamp()
                if self.max_age_timestamp == 0 or self.max_age_timestamp < timestamp:
                    title = f"{doc['title']} - {event['title']}"
                    if event['eventType'] in ["ACCOUNT_TRANSFER_INCOMING", "ACCOUNT_TRANSFER_OUTGOING", "CREDIT"]:
                        title += f" - {event['subtitle']}"
                    dl.dl_doc(doc, title, doc.get('detail'), subfolder)

        if event['has_docs']:
            self.events_with_docs.append(event)
        else:
            self.events_without_docs.append(event)

        if self.received_detail == self.requested_detail:
            self.log.info('Received all details')
            dl.output_path.mkdir(parents=True, exist_ok=True)
            with open(dl.output_path / 'other_events.json', 'w', encoding='utf-8') as f:
                json.dump(self.events_without_docs, f, ensure_ascii=False, indent=2)

            with open(dl.output_path / 'events_with_documents.json', 'w', encoding='utf-8') as f:
                json.dump(self.events_with_docs, f, ensure_ascii=False, indent=2)
            
            with open(dl.output_path / 'all_events.json', 'w', encoding='utf-8') as f:
                json.dump(self.events_without_docs + self.events_with_docs, f, ensure_ascii=False, indent=2)

            export_transactions(dl.output_path / 'all_events.json', dl.output_path / 'account_transactions.csv')

            dl.work_responses()
