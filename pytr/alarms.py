import asyncio
import bisect
import csv
import platform
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any

from pytr.utils import get_logger, preview


def alarms_dict_from_alarms_row(isin, alarms, max_values) -> dict[str, Any]:
    alarmRow = {
        "ISIN": isin,
    }
    for i in range(1, max_values + 1):
        alarmRow[f"alarm{i}"] = alarms[i - 1] if i <= len(alarms) else None
    return alarmRow


class Alarms:
    def __init__(self, tr, input=[], fp=None, remove_current_alarms=True):
        self.tr = tr
        self.input = input
        self.fp = fp
        self.remove_current_alarms = remove_current_alarms
        self.log = get_logger(__name__)
        self.data = {}

    async def alarms_loop(self):
        recv = 0
        await self.tr.price_alarm_overview()
        while True:
            _, subscription, response = await self.tr.recv()

            if subscription["type"] == "priceAlarms":
                recv += 1
                self.alarms = response
            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

            if recv == 1:
                return

    async def set_alarms(self):
        # get current alarms
        await self.alarms_loop()

        current_alarms = {}
        new_alarms = {}
        alarms_to_keep = {}
        isins = self.data.keys()

        if not isins:
            print("No instruments given to set alarms for")
            return

        for isin in isins:
            current_alarms.setdefault(isin, {})
            new_alarms.setdefault(isin, [])
            alarms_to_keep.setdefault(isin, [])

        for a in self.alarms:
            if a["instrumentId"] in isins:
                current_alarms[a["instrumentId"]][Decimal(a["targetPrice"])] = a["id"]

        for isin in isins:
            for a in self.data[isin]:
                if a in current_alarms[isin]:
                    alarms_to_keep[isin].append(a)
                    del current_alarms[isin][a]
                else:
                    new_alarms[isin].append(a)

            if not self.remove_current_alarms:
                current_alarms.clear()

            messages = []
            if alarms_to_keep[isin]:
                messages.append(f"Keeping {', '.join(str(v) for v in alarms_to_keep[isin])}")
            if new_alarms[isin]:
                messages.append(f"Adding {', '.join(str(v) for v in new_alarms[isin])}")
            if current_alarms[isin]:
                messages.append(f"Removing {', '.join(str(v) for v in sorted(current_alarms[isin].keys()))}")
            if not messages:
                messages.append("Nothing to do.")

            print(f"{isin}: {'; '.join(messages)}")

        action_count = 0
        for isin in isins:
            for a in new_alarms[isin]:
                await self.tr.create_price_alarm(isin, float(a))
                action_count += 1

            for a in current_alarms[isin]:
                await self.tr.cancel_price_alarm(current_alarms[isin].get(a))
                action_count += 1

        while action_count > 0:
            await self.tr.recv()
            action_count -= 1
        return

    def overview(self):
        alarms_per_ISIN = defaultdict(list)
        isins = self.data.keys()
        for a in self.alarms:
            if a["status"] != "active":
                continue
            if isins and a["instrumentId"] not in isins:
                continue
            bisect.insort(alarms_per_ISIN[a["instrumentId"]], a["targetPrice"])

        for isin in isins:
            if isin not in alarms_per_ISIN:
                alarms_per_ISIN[isin] = []

        max_values = max(len(v) for v in alarms_per_ISIN.values())
        if self.fp == sys.stdout:
            print(f"ISIN          {'  '.join(f'Alarm{i}' for i in range(1, max_values + 1))}")
            for isin, alarms in alarms_per_ISIN.items():
                print(f"{isin} {' '.join(f'{float(x):>7.2f}' for x in alarms)}")
        else:
            print(f"Writing alarms to file {self.fp.name}...")
            lineterminator = "\n" if platform.system() == "Windows" else "\r\n"
            writer = csv.DictWriter(
                self.fp,
                fieldnames=["ISIN"] + [f"alarm{i}" for i in range(1, max_values + 1)],
                delimiter=";",
                lineterminator=lineterminator,
            )
            writer.writeheader()
            writer.writerows(
                [alarms_dict_from_alarms_row(key, value, max_values) for key, value in alarms_per_ISIN.items()]
            )
            self.fp.close()

    def get(self):
        cur_isin = None
        for token in self.input:
            if len(token) == 12 and "." not in token:
                cur_isin = token
                self.data.setdefault(cur_isin, [])
            else:
                try:
                    cur_alarm = Decimal(token)
                    if cur_isin is not None:
                        bisect.insort(self.data[cur_isin], cur_alarm)
                except InvalidOperation:
                    raise ValueError(f"{token} is no valid ISIN or decimal value that could represent an alarm.")

        asyncio.run(self.alarms_loop())

        self.overview()

    def set(self):
        if self.fp == sys.stdin:
            cur_isin = None
            for token in self.input:
                if len(token) == 12 and "." not in token:
                    cur_isin = token
                    self.data.setdefault(cur_isin, [])
                else:
                    try:
                        cur_alarm = Decimal(token)
                        if cur_isin is not None:
                            bisect.insort(self.data[cur_isin], cur_alarm)
                    except InvalidOperation:
                        raise ValueError(f"{token} is no valid ISIN or decimal value that could represent an alarm.")
        else:
            lineterminator = "\n" if platform.system() == "Windows" else "\r\n"
            reader = csv.DictReader(self.fp, delimiter=";", lineterminator=lineterminator)
            fieldnames = reader.fieldnames
            fieldnum = len(fieldnames)
            for row in list(reader):
                isin = row[fieldnames[0]]
                self.data.setdefault(isin, [])
                for i in range(1, fieldnum):
                    value = row[fieldnames[i]]
                    if value is not None and value != "":
                        bisect.insort(self.data[isin], Decimal(value.replace(",", "")))

        # set/remove alarms
        asyncio.run(self.set_alarms())
