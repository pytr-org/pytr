from babel.numbers import format_decimal
from typing import Generator

from .event import Event, PPEventType, UnprocessedEventType
from .translation import setup_translation


class EventCsvFormatter:
    def __init__(self, lang):
        self.lang = lang
        self.translate = setup_translation(language=self.lang)
        self.csv_fmt = "{date};{type};{value};{note};{isin};{shares}\n"
        self.header = self.csv_fmt.format(
            date=self.translate("CSVColumn_Date"),
            type=self.translate("CSVColumn_Type"),
            value=self.translate("CSVColumn_Value"),
            note=self.translate("CSVColumn_Note"),
            isin=self.translate("CSVColumn_ISIN"),
            shares=self.translate("CSVColumn_Shares"),
        )

    def format_header(self) -> str:
        """Outputs header line

        Returns:
            str: header line
        """
        return self.header

    def format(self, event: Event) -> Generator[str, None, None]:
        """Outputs a generator that yields one or multiple csv lines per event

        Args:
            event (Event): _description_

        Yields:
            Generator[str, None, None]: _description_
        """
        # If the event_type is not captured by the mappings in event.py
        # it is not a relevant event
        if event.event_type is None:
            return
        # Initialize the csv line arguments
        kwargs = dict(
            zip(
                ("date", "type", "value", "note", "isin", "shares"),
                ["" for _ in range(6)],
            )
        )
        
        # Apply special formatting to value, note, shares and type attributes
        kwargs["value"] = [event.value] if event.value is not None else [""]
        kwargs["shares"] = [event.shares] if event.shares is not None else [""]
        kwargs["note"] = [self.translate(event.note) + " - " + event.title] if event.note is not None else [event.title]
        kwargs["isin"] = [event.isin] if event.isin is not None else [""]
        kwargs["type"] = [self.translate(event.event_type.value) if isinstance(event.event_type, PPEventType) else None]
        kwargs["date"] = [event.date.strftime("%Y-%m-%d")]

        # Handle TRADE_INVOICE
        if event.event_type == UnprocessedEventType.TRADE_INVOICE:
            event.event_type = PPEventType.BUY if event.value < 0 else PPEventType.SELL
            kwargs["type"] = [self.translate(event.event_type.value)]

        # The following three event types generate two or three csv lines per event
        # (buy+deposit or dividend/interest/sell+tax or buy/sell+fee or sell+tax+fee)
        additional_events = []
        # Handle SAVEBACK
        if event.event_type == UnprocessedEventType.SAVEBACK:
            kwargs["type"] = [
                self.translate(PPEventType.BUY.value),
                self.translate(PPEventType.DEPOSIT.value),
            ]
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
            if isinstance(kwargs["value"][0], str): breakpoint()
            kwargs["value"][0] -= event.fee
            kwargs["type"] += [self.translate(PPEventType.FEES.value)]
            kwargs["value"] += [event.fee]
        

        # Handle float to string conversion after tax and fee effects on the value field
        if event.value is not None:
            kwargs["value"] = [format_decimal(
                value, locale=self.lang, decimal_quantization=True
            ) for value in kwargs["value"]]
        if event.shares is not None:
            kwargs["shares"] = [format_decimal(
                kwargs["shares"][0], locale=self.lang, decimal_quantization=False
            )]

        # Build the csv line formatting arguments when one event generates more than one line
        single_element_dict = {
            key: value[0] for key, value in kwargs.items() if len(value) == 1
        }
        multi_element_dict = {
            key: value for key, value in kwargs.items() if len(value) > 1
        }
        list_kwargs = [dict(zip(multi_element_dict.keys(), v)) for v in zip(*multi_element_dict.values())]
        for line in list_kwargs:
            line.update(single_element_dict)
        # Assert that if one kwargs value has a greater 1 length, 
        # all greater 1 length lists must have same length
        assert len(set(map(len, multi_element_dict.values()))) <= 1
        # Yields csv lines
        for kwargs in list_kwargs:
            if "isin" not in kwargs.keys(): breakpoint()
            yield self.csv_fmt.format(**kwargs)
