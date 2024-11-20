import json
from locale import getdefaultlocale
import asyncio
from datetime import datetime
from pytr.utils import preview

from .event import Event
from .event_formatter import EventCsvFormatter
from .utils import get_logger


def export_transactions(input_path, output_path, lang="auto", sort=False):
    """
    Create a CSV with the deposits and removals ready for importing into Portfolio Performance
    The CSV headers for PP are language dependend
    """
    log = get_logger(__name__)
    if lang == "auto":
        locale = getdefaultlocale()[0]
        if locale is None:
            lang = "en"
        else:
            lang = locale.split("_")[0]

    if lang not in [
        "cs",
        "da",
        "de",
        "en",
        "es",
        "fr",
        "it",
        "nl",
        "pl",
        "pt",
        "ru",
        "zh",
    ]:
        log.info(f"Language not yet supported {lang}")
        lang = "en"

    # Read relevant deposit timeline entries
    with open(input_path, encoding="utf-8") as f:
        timeline = json.load(f)

    log.info("Write deposit entries")

    formatter = EventCsvFormatter(lang=lang)

    events = map(lambda x: Event.from_dict(x), timeline)
    if sort:
        events = sorted(events, key=lambda x: x.date)
    lines = map(lambda x: formatter.format(x), events)
    lines = formatter.format_header() + "".join(lines)

    # Write transactions into csv file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(lines)

    log.info("Deposit creation finished!")


class Transactions:
    def __init__(self, tr, output_path, not_before):
        self.tr = tr
        self.output_path = output_path
        self.not_before = not_before
        self.transactions = []

    async def loop(self):
        await self.tr.timeline_transactions()
        while True:
            _subscription_id, subscription, response = await self.tr.recv()

            if subscription["type"] == "timelineTransactions":
                self.transactions.extend(response["items"])

                # Transactions in the response are ordered from newest to oldest
                # If the oldest (= last) transaction is older than what we want, exit the loop
                t = self.transactions[-1]
                if datetime.fromisoformat(t["timestamp"]) < self.not_before:
                    return

                await self.tr.timeline_transactions(response["cursors"]["after"])

            else:
                print(
                    f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}"
                )

    def output(self):
        # Need to loop over all transactions here since the
        # event loop might return older transactions, too
        transactions = [
            t
            for t in self.transactions
            if datetime.fromisoformat(t["timestamp"]) > self.not_before
        ]

        with open(self.output_path, mode="w", encoding="utf-8") as output_file:
            json.dump(transactions, output_file)

    def get(self):
        asyncio.get_event_loop().run_until_complete(self.loop())
        self.output()
