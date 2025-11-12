import csv
import json
import platform
from dataclasses import dataclass
from locale import getdefaultlocale
from typing import Any, Iterable, Literal, Optional, TextIO, TypedDict, Union

from babel.numbers import format_decimal

from .event import ConditionalEventType, Event, PPEventType
from .translation import setup_translation
from .utils import get_logger

SUPPORTED_LANGUAGES = {
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
}

CSVCOLUMN_TO_TRANSLATION_KEY = {
    "date": "CSVColumn_Date",
    "type": "CSVColumn_Type",
    "value": "CSVColumn_Value",
    "note": "CSVColumn_Note",
    "isin": "CSVColumn_ISIN",
    "shares": "CSVColumn_Shares",
    "fees": "CSVColumn_Fees",
    "taxes": "CSVColumn_Taxes",
}


class _SimpleTransaction(TypedDict):
    date: str
    type: Union[str, None]
    value: Union[str, float, None]
    note: Union[str, float, None]
    isin: Union[str, float, None]
    shares: Union[str, float, None]
    fees: Union[str, float, None]
    taxes: Union[str, float, None]


@dataclass
class TransactionExporter:
    """
    A helper class to convert Trade Republic events each to one or more line items that are a simplified representation
    useful for a importing for example into a portfolio manager.
    """

    lang: str = "en"
    """ The language for the CSV header / JSON keys. """

    date_with_time: bool = True
    """ Include the timestamp in ISO8601 format in the date field. """

    decimal_localization: bool = False
    """ Whether to localize the decimal format. If enabled, decimal fields will be string values. """

    csv_delimiter: str = ";"

    def __post_init__(self):
        self._log = get_logger(__name__)

        if self.lang == "auto":
            locale = getdefaultlocale()[0]
            if locale is None:
                self.lang = "en"
            else:
                self.lang = locale.split("_")[0]

        if self.lang not in SUPPORTED_LANGUAGES:
            self._log.info(f'Language not yet supported "{self.lang}", defaulting to "en"')
            self.lang = "en"

        self._translate = setup_translation(language=self.lang)

    def _decimal_format(self, value: Optional[float], quantization: bool = True) -> Union[str, float, None]:
        if value is None:
            return None
        return (
            format_decimal(value, locale=self.lang, decimal_quantization=quantization)
            if self.decimal_localization
            else value
        )

    def _localize_keys(self, txn: _SimpleTransaction) -> dict[str, Any]:
        return {self._translate(value): txn[key] for key, value in CSVCOLUMN_TO_TRANSLATION_KEY.items()}  # type: ignore[literal-required]

    def fields(self) -> list[str]:
        return [self._translate(value) for key, value in CSVCOLUMN_TO_TRANSLATION_KEY.items()]

    def from_event(self, event: Event) -> Iterable[dict[str, Any]]:
        """
        Given an event, produces one or more JSON objects representing a transaction. The returned object contains
        the given fields, localized in the selected language.

        - `date`
        - `type`
        - `value`
        - `note`
        - `isin`
        - `shares`
        - `fees`
        - `taxes`
        """

        if event.event_type is None:
            return

        kwargs: _SimpleTransaction = {
            "date": event.date.isoformat() if self.date_with_time else event.date.date().isoformat(),
            "type": self._translate(event.event_type.value) if isinstance(event.event_type, PPEventType) else None,
            "value": self._decimal_format(event.value),
            "note": self._translate(event.note) + " - " + event.title if event.note is not None else event.title,
            "isin": event.isin,
            "shares": self._decimal_format(event.shares, False),
            "fees": self._decimal_format(-event.fees) if event.fees is not None else None,
            "taxes": self._decimal_format(-event.taxes) if event.taxes is not None else None,
        }

        if event.event_type == ConditionalEventType.TRADE_INVOICE:
            assert event.value is not None, event
            ev_value = event.value
            if event.shares2:
                kwargs2 = kwargs.copy()
                kwargs2["type"] = self._translate((PPEventType.BUY if event.value < 0 else PPEventType.SELL).value)
                kwargs2["note"] = event.isin2
                if event.isin2 == "ORSTED A/S EM.09/25 DK 10":
                    kwargs2["isin"] = "DK0064307755"
                else:
                    kwargs2["isin"] = event.isin2
                kwargs2["shares"] = self._decimal_format(event.shares2, False)
                yield self._localize_keys(kwargs2)
                kwargs["value"] = self._decimal_format(0)
                ev_value = 0

            kwargs["type"] = self._translate((PPEventType.BUY if ev_value < 0 else PPEventType.SELL).value)
        elif event.event_type == ConditionalEventType.SPINOFF:
            if event.shares2:
                kwargs2 = kwargs.copy()
                kwargs2["type"] = self._translate(PPEventType.SELL.value)
                yield self._localize_keys(kwargs2)

            kwargs["type"] = self._translate(PPEventType.BUY.value)
            kwargs["note"] = event.isin2
            if event.isin2 == "BlackRock Funding":
                kwargs["isin"] = "US09290D1019"
            elif event.isin2 == "BYD":
                kwargs["isin"] = "CNE100000296"
            elif event.isin2 == "Chipotle":
                kwargs["isin"] = "US1696561059"
            elif event.isin2 == "Eckert & Ziegler":
                kwargs["isin"] = "DE0005659700"
            elif event.isin2 == "Enovix Corp. WTS 01.10.26":
                kwargs["isin"] = "US2935941318"
            elif event.isin2 == "Gamestop Corp. WTS 30.10.26":
                kwargs["isin"] = "US36467W1172"
            elif event.isin2 == "GLOBALSTAR INC. O.N.":
                kwargs["isin"] = "US3789735079"
            elif event.isin2 == "Netflix":
                kwargs["isin"] = "US64110L1061"
            elif event.isin2 == "NVIDIA":
                kwargs["isin"] = "US67066G1040"
            elif event.isin2 == "Orsted":
                kwargs["isin"] = "DK0060094928"
            elif event.isin2 == "ORSTED A/S   -ANR-":
                kwargs["isin"] = "DK0064307839"
            elif event.isin2 == "ROCKET LAB CORP. O.N.":
                kwargs["isin"] = "US7731211089"
            elif event.isin2 == "TKMS":
                kwargs["isin"] = "DE000TKMS001"
            else:
                kwargs["isin"] = event.isin2
            if event.shares2:
                kwargs["shares"] = self._decimal_format(event.shares2, False)
        # Special case for saveback events. Example payload: https://github.com/pytr-org/pytr/issues/116#issuecomment-2377491990
        # With saveback, a small amount already invested into a savings plans is invested again, effectively representing
        # a deposit (you get money from Trade Republic) and then a buy of the related asset.
        elif event.event_type == ConditionalEventType.SAVEBACK:
            assert event.value is not None, event
            kwargs["type"] = self._translate(PPEventType.BUY.value)
            yield self._localize_keys(kwargs)

            kwargs = kwargs.copy()
            kwargs["type"] = self._translate(PPEventType.DEPOSIT.value)
            kwargs["value"] = self._decimal_format(-event.value)
            kwargs["isin"] = None
            kwargs["shares"] = None
        elif event.event_type == ConditionalEventType.PRIVATE_MARKETS_ORDER:
            if event.isin == "LU3176111881":
                kwargs["note"] = "EQT"
            elif event.isin == "LU3170240538":
                kwargs["note"] = "Apollo"

            assert event.value is not None, event
            kwargs["type"] = self._translate((PPEventType.BUY if event.value < 0 else PPEventType.SELL).value)
            if event.note == "1 % Bonus":
                yield self._localize_keys(kwargs)

                kwargs = kwargs.copy()
                kwargs["type"] = self._translate(PPEventType.DEPOSIT.value)
                kwargs["value"] = self._decimal_format(-event.value)
                kwargs["isin"] = None
                kwargs["shares"] = None

        yield self._localize_keys(kwargs)

    def export(
        self,
        fp: TextIO,
        events: Iterable[Event],
        sort: bool = False,
        format: Literal["json", "csv"] = "csv",
    ) -> None:
        self._log.info("Exporting transactions...")
        if sort:
            events = sorted(events, key=lambda ev: ev.date)

        transactions = (txn for event in events for txn in self.from_event(event))

        if format == "csv":
            lineterminator = "\n" if platform.system() == "Windows" else "\r\n"
            writer = csv.DictWriter(
                fp, fieldnames=self.fields(), delimiter=self.csv_delimiter, lineterminator=lineterminator
            )
            writer.writeheader()
            writer.writerows(transactions)
        elif format == "json":
            for txn in transactions:
                fp.write(json.dumps(txn))
                fp.write("\n")

        self._log.info("Transactions exported.")
