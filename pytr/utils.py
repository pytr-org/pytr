#!/usr/bin/env python3

import logging
import coloredlogs
import json


log_level = None


def get_logger(name=__name__, verbosity=None):
    """
    Colored logging

    :param name: logger name (use __name__ variable)
    :param verbosity:
    :return: Logger
    """
    global log_level
    if verbosity is not None:
        if log_level is None:
            log_level = verbosity
        else:
            raise RuntimeError('Verbosity has already been set.')

    shortname = name.replace('fdroid_mirror_monitor.', '')
    logger = logging.getLogger(shortname)

    # no logging of libs (and fix double logs because of fdroidserver)
    logger.propagate = False

    fmt = '%(asctime)s %(threadName)-12s %(name)-7s %(levelname)-8s %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S%z'

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
    head = "\n".join(lines[:num_lines])
    tail = len(lines) - num_lines

    if tail <= 0:
        return f"{head}\n"
    else:
        return f"{head}\n{tail} more lines hidden"


class Timeline:
    def __init__(self, tr):
        self.tr = tr

        self.received_detail = 0
        self.requested_detail = 0

    async def get_next_timeline(self, response=None):
        """
        Get timelines and save time in global list timelines.
        Extract id of timeline events and save them in global list timeline_detail_ids
        """

        if response is None:
            # empty response / first timeline
            print("Awaiting #1  timeline")
            self.timelines = []
            self.timeline_detail_ids = []
            self.timeline_events = []
            await self.tr.timeline()
        else:
            self.timelines.append(response)
            try:
                after = response["cursors"]["after"]
            except KeyError:
                # last timeline is reached
                print(f"Received #{len(self.timelines):<2} (last) timeline")
                await self.get_timeline_details(5)
            else:
                print(f"Received #{len(self.timelines):<2} timeline, awaiting #{len(self.timelines)+1:<2} timeline")
                await self.tr.timeline(after)

            # print(json.dumps(response))
            for event in response["data"]:
                self.timeline_events.append(event)
                self.timeline_detail_ids.append(event["data"]["id"])

    async def get_timeline_details(self, num_torequest):
        self.requested_detail += num_torequest

        while num_torequest > 0:
            num_torequest -= 1
            try:
                event = self.timeline_events.pop()
            except IndexError:
                return
            else:
                await self.tr.timeline_detail(event["data"]["id"])

    async def timelineDetail(self, response, dl):

        self.received_detail += 1

        if self.received_detail == self.requested_detail:
            await self.get_timeline_details(5)

        timeline_detail_id = response["id"]
        for event in self.timeline_events:
            if timeline_detail_id == event["data"]["id"]:
                self.timeline_events.remove(event)

        print(f"len timeline_events: {len(self.timeline_events)}")

        print(f"R: {self.received_detail}/{len(self.timeline_detail_ids)}")

        if response["subtitleText"] == "Sparplan":
            isSavingsPlan = True
        else:
            isSavingsPlan = False
            # some savingsPlan don't have the subtitleText == "Sparplan" but there are actions just for savingsPans
            for section in response["sections"]:
                if section["type"] == "actionButtons":
                    for button in section["data"]:
                        if button["action"]["type"] in ["editSavingsPlan", "deleteSavingsPlan"]:
                            isSavingsPlan = True
                            break

        print(f"Detail: {response['titleText']} -- {response['subtitleText']} -- istSparplan: {isSavingsPlan}")

        for section in response["sections"]:
            if section["type"] == "documents":
                for doc in section["documents"]:

                    # save all savingsplan documents in a subdirectory
                    if isSavingsPlan:
                        dl.dl_doc(doc, response['titleText'], response["subtitleText"], subfolder="Sparplan")
                    else:
                        dl.dl_doc(doc, response['titleText'], response["subtitleText"])

        if self.received_detail == len(self.timeline_detail_ids):
            print("received all details, downloading docs..")
            dl.work_responses()
        else:
            print(f"r: {self.received_detail}/{len(self.timeline_detail_ids)} - istSparplan: {isSavingsPlan}")
