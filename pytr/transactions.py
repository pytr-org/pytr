from locale import getdefaultlocale
from babel.numbers import format_decimal
import json
import asyncio
from datetime import datetime
from pytr.utils import preview

from .event import Event
from .utils import get_logger
from .translation import setup_translation


def export_transactions(input_path, output_path, lang="auto"):
    """
    Create a CSV with the deposits and removals ready for importing into Portfolio Performance
    The CSV headers for PP are language dependend

    i18n source from Portfolio Performance:
    https://github.com/buchen/portfolio/blob/93b73cf69a00b1b7feb136110a51504bede737aa/name.abuchen.portfolio/src/name/abuchen/portfolio/messages_de.properties
    https://github.com/buchen/portfolio/blob/effa5b7baf9a918e1b5fe83942ddc480e0fd48b9/name.abuchen.portfolio/src/name/abuchen/portfolio/model/labels_de.properties

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
    _ = setup_translation(language=lang)

    # Read relevant deposit timeline entries
    with open(input_path, encoding="utf-8") as f:
        timeline = json.load(f)

    log.info("Write deposit entries")
    with open(output_path, "w", encoding="utf-8") as f:
        csv_fmt = "{date};{type};{value};{note};{isin};{shares}\n"
        header = csv_fmt.format(
            date=_("CSVColumn_Date"),
            type=_("CSVColumn_Type"),
            value=_("CSVColumn_Value"),
            note=_("CSVColumn_Note"),
            isin=_("CSVColumn_ISIN"),
            shares=_("CSVColumn_Shares"),
        )
        f.write(header)

        for event_json in timeline:
            event = Event(event_json)
            if not event.is_pp_relevant:
                continue

            amount = format_decimal(event.amount, locale=lang) if event.amount else ""
            note = (_(event.note) + " - " + event.title) if event.note else event.title
            shares = format_decimal(event.shares, locale=lang) if event.shares else ""

            f.write(
                csv_fmt.format(
                    date=event.date,
                    type=_(event.pp_type),
                    value=amount,
                    note=note,
                    isin=event.isin,
                    shares=shares,
                )
            )

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

            if subscription['type'] == 'timelineTransactions':
                self.transactions.extend(response["items"])

                # Transactions in the response are ordered from newest to oldest
                # If the oldest (= last) transaction is older than what we want, exit the loop
                t = self.transactions[-1]
                if datetime.fromisoformat(t['timestamp']) < self.not_before:
                    return

                await self.tr.timeline_transactions(response["cursors"]["after"])

            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

    def output(self):
        # Need to loop over all transactions here since the
        # event loop might return older transactions, too
        transactions = [
            t
            for t in self.transactions
            if datetime.fromisoformat(t['timestamp']) > self.not_before
        ]

        with open(self.output_path, mode='w', encoding='utf-8') as output_file:
            json.dump(transactions, output_file)

    def get(self):
        asyncio.get_event_loop().run_until_complete(self.loop())
        self.output()
