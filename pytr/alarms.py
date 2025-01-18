import asyncio
from datetime import datetime

from pytr.utils import preview, get_logger


class Alarms:
    def __init__(self, tr):
        self.tr = tr
        self.log = get_logger(__name__)

    async def alarms_loop(self):
        recv = 0
        await self.tr.price_alarm_overview()
        while True:
            _subscription_id, subscription, response = await self.tr.recv()

            if subscription["type"] == "priceAlarms":
                recv += 1
                self.alarms = response
            else:
                print(
                    f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}"
                )

            if recv == 1:
                return

    async def ticker_loop(self):
        recv = 0
        await self.tr.price_alarm_overview()
        while True:
            _subscription_id, subscription, response = await self.tr.recv()

            if subscription["type"] == "priceAlarms":
                recv += 1
                self.alarms = response
            else:
                print(
                    f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}"
                )

            if recv == 1:
                return

    def overview(self):
        print("ISIN         status created  target  diff% createdAt        triggeredAT")
        self.log.debug(f"Processing {len(self.alarms)} alarms")

        for (
            a
        ) in (
            self.alarms
        ):  # sorted(positions, key=lambda x: x['netValue'], reverse=True):
            self.log.debug(f"  Processing {a} alarm")
            ts = int(a["createdAt"]) / 1000.0
            target_price = float(a["targetPrice"])
            created_price = float(a["createdPrice"])
            created = datetime.fromtimestamp(ts).isoformat(sep=" ", timespec="minutes")
            if a["triggeredAt"] is None:
                triggered = "-"
            else:
                ts = int(a["triggeredAt"]) / 1000.0
                triggered = datetime.fromtimestamp(ts).isoformat(
                    sep=" ", timespec="minutes"
                )

            if a["createdPrice"] == 0:
                diffP = 0.0
            else:
                diffP = (target_price / created_price) * 100 - 100

            print(
                f"{a['instrumentId']} {a['status']} {created_price:>7.2f} {target_price:>7.2f} "
                + f"{diffP:>5.1f}% {created} {triggered}"
            )

    def get(self):
        asyncio.get_event_loop().run_until_complete(self.alarms_loop())

        self.overview()
