from babel.numbers import format_decimal

from .event import Event, PPEventType, UnprocessedEventType
from .translation import setup_translation


class EventCsvFormatter:
    def __init__(self, lang):
        self.lang = lang
        self.translate = setup_translation(language=self.lang)
        self.csv_fmt = "{date};{type};{value};{note};{isin};{shares}\n"

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
                ("date", "type", "value", "note", "isin", "shares"),
                [[""] for _ in range(6)],
            )
        )

        # Handle TRADE_INVOICE
        if event.event_type == UnprocessedEventType.TRADE_INVOICE:
            event.event_type = PPEventType.BUY if event.value < 0 else PPEventType.SELL

        # Apply special formatting to date, type, value, note, isin and shares attributes
        kwargs["date"] = [event.date.strftime("%Y-%m-%d")]
        if isinstance(event.event_type, PPEventType):
            kwargs["type"] = [self.translate(event.event_type.value)]
        kwargs["value"] = [event.value]
        kwargs["note"] = (
            [self.translate(event.note) + " - " + event.title]
            if event.note is not None
            else [event.title]
        )
        if event.isin is not None:
            kwargs["isin"] = [event.isin]
        if event.shares is not None:
            kwargs["shares"] = [event.shares]
        
        # The following three event types potentially generate two or three csv lines per
        # event (buy+deposit or dividend/interest/sell+tax or buy/sell+fee or sell+tax+fee)
        # Handle SAVEBACK
        if event.event_type == UnprocessedEventType.SAVEBACK:
            kwargs["type"] = [
                self.translate(PPEventType.BUY.value),
                self.translate(PPEventType.DEPOSIT.value),
            ]
            kwargs["value"] += [-kwargs["value"][0]]
            kwargs["isin"] += [""]
            kwargs["shares"] += [""]
        # Handle Tax
        if (
            event.event_type
            in [PPEventType.DIVIDEND, PPEventType.INTEREST, PPEventType.SELL]
            and event.tax is not None
        ):
            kwargs["value"][0] += event.tax
            kwargs["type"] += [self.translate(PPEventType.TAXES.value)]
            kwargs["value"] += [event.tax]
        # Handle Fee
        if (
            event.event_type in [PPEventType.BUY, PPEventType.SELL]
            and event.fee is not None
        ):
            kwargs["value"][0] += event.fee
            kwargs["type"] += [self.translate(PPEventType.FEES.value)]
            kwargs["value"] += [event.fee]

        # Handle float to string conversion after tax and fee effects on the value field
        if event.value is not None:
            kwargs["value"] = [
                format_decimal(value, locale=self.lang, decimal_quantization=True)
                for value in kwargs["value"]
            ]
        if event.shares is not None:
            kwargs["shares"] = [
                (
                    format_decimal(shares, locale=self.lang, decimal_quantization=False)
                    if shares != ""
                    else ""
                )
                for shares in kwargs["shares"]
            ]

        # Build the csv line formatting arguments when one event generates more than one line
        single_line_generating_args = {
            key: value[0] for key, value in kwargs.items() if len(value) == 1
        }
        multi_line_generating_args = {
            key: value for key, value in kwargs.items() if len(value) > 1
        }
        list_kwargs = [
            dict(zip(multi_line_generating_args.keys(), v))
            for v in zip(*multi_line_generating_args.values())
        ]
        for line in list_kwargs:
            line.update(single_line_generating_args)
        if len(list_kwargs) == 0:
            list_kwargs += [single_line_generating_args]
        # Build csv line(s) from kwargs
        lines = "".join(map(lambda x: self.csv_fmt.format(**x), list_kwargs))
        return lines
