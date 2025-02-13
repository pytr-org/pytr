from dataclasses import dataclass
from typing import Literal, Union

from babel.numbers import format_decimal

from .event import ConditionalEventType, Event, PPEventType
from .translation import setup_translation


@dataclass
class EventCsvFormatter:
    lang: str
    csv_fmt: str = "{date};{type};{value};{note};{isin};{shares};{fees};{taxes}\n"
    date_fmt: Union[str, Literal["ISO8601"]] = "%Y-%m-%d"

    def __post_init__(self):
        self.translate = setup_translation(language=self.lang)

    def format_header(self) -> str:
        """Outputs header line

        Returns:
            str: header line
        """
        return self.csv_fmt.format(
            date=self.translate("CSVColumn_Date"),
            type=self.translate("CSVColumn_Type"),
            value=self.translate("CSVColumn_Value"),
            note=self.translate("CSVColumn_Note"),
            isin=self.translate("CSVColumn_ISIN"),
            shares=self.translate("CSVColumn_Shares"),
            fees=self.translate("CSVColumn_Fees"),
            taxes=self.translate("CSVColumn_Taxes"),
        )

    def format(self, event: Event) -> str:
        """Outputs one or multiple csv lines per event

        Args:
            event (Event): _description_

        Yields:
            str: csv line(s)
        """
        # Empty csv line for non-transaction events
        if event.event_type is None:
            return ""

        # Initialize the csv line arguments
        kwargs = dict(
            zip(
                ("date", "type", "value", "note", "isin", "shares", "fees", "taxes"),
                ["" for _ in range(8)],
            )
        )

        # Handle TRADE_INVOICE
        if event.event_type == ConditionalEventType.TRADE_INVOICE:
            assert event.value is not None, event
            event.event_type = PPEventType.BUY if event.value < 0 else PPEventType.SELL

        # Apply special formatting to the attributes
        if self.date_fmt == "ISO8601":
            kwargs["date"] = event.date.isoformat()
        else:
            kwargs["date"] = event.date.strftime(self.date_fmt)
        if isinstance(event.event_type, PPEventType):
            kwargs["type"] = self.translate(event.event_type.value)
        if event.value is not None:
            kwargs["value"] = format_decimal(event.value, locale=self.lang, decimal_quantization=True)
        kwargs["note"] = self.translate(event.note) + " - " + event.title if event.note is not None else event.title
        if event.isin is not None:
            kwargs["isin"] = event.isin
        if event.shares is not None:
            kwargs["shares"] = format_decimal(event.shares, locale=self.lang, decimal_quantization=False)
        if event.fees is not None:
            kwargs["fees"] = format_decimal(-event.fees, locale=self.lang, decimal_quantization=True)
        if event.taxes is not None:
            kwargs["taxes"] = format_decimal(-event.taxes, locale=self.lang, decimal_quantization=True)
        lines = self.csv_fmt.format(**kwargs)

        # Generate BUY and DEPOSIT events from SAVEBACK event
        if event.event_type == ConditionalEventType.SAVEBACK:
            assert event.value is not None, event
            kwargs["type"] = self.translate(PPEventType.BUY.value)
            lines = self.csv_fmt.format(**kwargs)
            kwargs["type"] = self.translate(PPEventType.DEPOSIT.value)
            kwargs["value"] = format_decimal(-event.value, locale=self.lang, decimal_quantization=True)
            kwargs["isin"] = ""
            kwargs["shares"] = ""
            lines += self.csv_fmt.format(**kwargs)

        return lines
