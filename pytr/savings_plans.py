import asyncio
import csv
import platform
import sys
from locale import getdefaultlocale

from babel.numbers import format_decimal

from pytr.utils import get_logger, preview


class SavingsPlans:
    def __init__(self, tr, fp=None, decimal_localization=False, lang="en"):
        self.tr = tr
        self.fp = fp
        self.decimal_localization = decimal_localization
        self.log = get_logger(__name__)
        self.savings_plans = []

        self.lang = lang
        if self.lang == "auto":
            default_locale = getdefaultlocale()[0]
            self.lang = default_locale.split("_")[0] if default_locale else "en"

    async def savings_plans_loop(self):
        await self.tr.savings_plan_overview()
        while True:
            _, subscription, response = await self.tr.recv()

            if subscription["type"] == "savingsPlans":
                self.savings_plans = response.get("savingsPlans", [])
                return
            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

    def _format_amount(self, value):
        if value is None:
            return ""
        if self.decimal_localization:
            return format_decimal(value, format="#,##0.##", locale=self.lang)
        return str(value)

    def overview(self):
        if not self.savings_plans:
            print("No savings plans found.")
            return

        fieldnames = [
            "instrumentId",
            "amount",
            "interval",
            "nextExecutionDate",
            "previousExecutionDate",
            "paused",
        ]

        def format_plan(plan):
            row = {}
            for f in fieldnames:
                val = plan.get(f, "")
                if f == "amount":
                    val = self._format_amount(val)
                row[f] = val
            return row

        if self.fp == sys.stdout:
            header = "  ".join(f"{f}" for f in fieldnames)
            print(header)
            for plan in self.savings_plans:
                formatted = format_plan(plan)
                row = "  ".join(str(formatted.get(f, "")) for f in fieldnames)
                print(row)
        else:
            print(f"Writing savings plans to file {self.fp.name}...")
            lineterminator = "\n" if platform.system() == "Windows" else "\r\n"
            writer = csv.DictWriter(
                self.fp,
                fieldnames=fieldnames,
                delimiter=";",
                lineterminator=lineterminator,
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows([format_plan(plan) for plan in self.savings_plans])
            self.fp.close()

    def get(self):
        async def get_and_close():
            await self.savings_plans_loop()
            await self.tr.close()

        asyncio.run(get_and_close())
        self.overview()
