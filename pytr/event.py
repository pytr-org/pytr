import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Optional, Tuple

from babel.numbers import NumberFormatError, parse_decimal


class EventType(Enum):
    pass


class ConditionalEventType(EventType):
    """Events that conditionally map to None or one/multiple PPEventType events"""

    SAVEBACK = auto()
    TRADE_INVOICE = auto()


class PPEventType(EventType):
    """PP Event Types"""

    BUY = "BUY"
    DEPOSIT = "DEPOSIT"
    DIVIDEND = "DIVIDEND"
    FEES = "FEES"  # Currently not mapped to
    FEES_REFUND = "FEES_REFUND"  # Currently not mapped to
    INTEREST = "INTEREST"
    INTEREST_CHARGE = "INTEREST_CHARGE"  # Currently not mapped to
    REMOVAL = "REMOVAL"
    SELL = "SELL"
    TAXES = "TAXES"  # Currently not mapped to
    TAX_REFUND = "TAX_REFUND"
    TRANSFER_IN = "TRANSFER_IN"  # Currently not mapped to
    TRANSFER_OUT = "TRANSFER_OUT"  # Currently not mapped to


tr_event_type_mapping = {
    # Deposits
    "INCOMING_TRANSFER": PPEventType.DEPOSIT,
    "INCOMING_TRANSFER_DELEGATION": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND_APPLE_PAY": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND_GOOGLE_PAY": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND_SEPA_DIRECT_DEBIT": PPEventType.DEPOSIT,
    "card_refund": PPEventType.DEPOSIT,
    "card_successful_oct": PPEventType.DEPOSIT,
    # Dividends
    "CREDIT": PPEventType.DIVIDEND,
    "ssp_corporate_action_invoice_cash": PPEventType.DIVIDEND,
    # Failed card transactions
    "card_failed_transaction": PPEventType.REMOVAL,
    # Interests
    "INTEREST_PAYOUT": PPEventType.INTEREST,
    "INTEREST_PAYOUT_CREATED": PPEventType.INTEREST,
    # Removals
    "OUTGOING_TRANSFER": PPEventType.REMOVAL,
    "OUTGOING_TRANSFER_DELEGATION": PPEventType.REMOVAL,
    "PAYMENT_OUTBOUND": PPEventType.REMOVAL,
    "card_order_billed": PPEventType.REMOVAL,
    "card_successful_atm_withdrawal": PPEventType.REMOVAL,
    "card_successful_transaction": PPEventType.REMOVAL,
    # Saveback
    "benefits_saveback_execution": ConditionalEventType.SAVEBACK,
    # Tax refunds
    "TAX_REFUND": PPEventType.TAX_REFUND,
    "ssp_tax_correction_invoice": PPEventType.TAX_REFUND,
    # Trade invoices
    "ORDER_EXECUTED": ConditionalEventType.TRADE_INVOICE,
    "SAVINGS_PLAN_EXECUTED": ConditionalEventType.TRADE_INVOICE,
    "SAVINGS_PLAN_INVOICE_CREATED": ConditionalEventType.TRADE_INVOICE,
    "benefits_spare_change_execution": ConditionalEventType.TRADE_INVOICE,
    "TRADE_INVOICE": ConditionalEventType.TRADE_INVOICE,
    # Fees refund
    "card_tr_refund": PPEventType.DEPOSIT,
}


@dataclass
class Event:
    date: datetime
    title: str
    event_type: Optional[EventType]
    fees: Optional[float]
    isin: Optional[str]
    note: Optional[str]
    shares: Optional[float]
    taxes: Optional[float]
    value: Optional[float]

    @classmethod
    def from_dict(cls, event_dict: Dict[Any, Any]):
        """Deserializes the event dictionary into an Event object

        Args:
            event_dict (json): _description_

        Returns:
            Event: Event object
        """
        date: datetime = datetime.fromisoformat(event_dict["timestamp"][:19])
        event_type: Optional[EventType] = cls._parse_type(event_dict)
        title: str = event_dict["title"]
        value: Optional[float] = (
            v if (v := event_dict.get("amount", {}).get("value", None)) is not None and v != 0.0 else None
        )
        fees, isin, note, shares, taxes = cls._parse_type_dependent_params(event_type, event_dict)
        return cls(date, title, event_type, fees, isin, note, shares, taxes, value)

    @staticmethod
    def _parse_type(event_dict: Dict[Any, Any]) -> Optional[EventType]:
        event_type: Optional[EventType] = tr_event_type_mapping.get(event_dict.get("eventType", ""), None)
        if event_dict.get("status", "").lower() == "canceled":
            event_type = None
        return event_type

    @classmethod
    def _parse_type_dependent_params(
        cls, event_type: Optional[EventType], event_dict: Dict[Any, Any]
    ) -> Tuple[Optional[float], Optional[str], Optional[str], Optional[float], Optional[float]]:
        """Parses the fees, isin, note, shares and taxes fields

        Args:
            event_type (EventType): _description_
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Tuple[Optional[Union[str, float]]]]: fees, isin, note, shares, taxes
        """
        isin, shares, taxes, note, fees = (None,) * 5

        if event_type is PPEventType.DIVIDEND:
            isin = cls._parse_isin(event_dict)
            taxes = cls._parse_taxes(event_dict)

        elif isinstance(event_type, ConditionalEventType):
            isin = cls._parse_isin(event_dict)
            shares, fees = cls._parse_shares_and_fees(event_dict)
            taxes = cls._parse_taxes(event_dict)

        elif event_type is PPEventType.INTEREST:
            taxes = cls._parse_taxes(event_dict)

        elif event_type in [PPEventType.DEPOSIT, PPEventType.REMOVAL]:
            note = cls._parse_card_note(event_dict)

        return fees, isin, note, shares, taxes

    @staticmethod
    def _parse_isin(event_dict: Dict[Any, Any]) -> str:
        """Parses the isin

        Args:
            event_dict (Dict[Any, Any]): _description_

        Returns:
            str: isin
        """
        sections = event_dict.get("details", {}).get("sections", [{}])
        isin = event_dict.get("icon", "")
        isin = isin[isin.find("/") + 1 :]
        isin = isin[: isin.find("/")]
        isin2 = isin
        for section in sections:
            action = section.get("action", None)
            if action and action.get("type", {}) == "instrumentDetail":
                isin2 = section.get("action", {}).get("payload")
                break
        if isin != isin2:
            isin = isin2
        return isin

    @classmethod
    def _parse_shares_and_fees(cls, event_dict: Dict[Any, Any]) -> Tuple[Optional[float], Optional[float]]:
        """Parses the amount of shares and the applicable fees

        Args:
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Tuple[Optional[float]]: shares, fees
        """
        return_vals = {}
        sections = event_dict.get("details", {}).get("sections", [{}])
        for section in sections:
            if section.get("title") == "Transaktion":
                data = section["data"]
                shares_dicts = list(filter(lambda x: x["title"] in ["Aktien", "Anteile"], data))
                fees_dicts = list(filter(lambda x: x["title"] == "Gebühr", data))
                titles = ["shares"] * len(shares_dicts) + ["fees"] * len(fees_dicts)
                for key, elem_dict in zip(titles, shares_dicts + fees_dicts):
                    return_vals[key] = cls._parse_float_from_detail(elem_dict)
        return return_vals.get("shares"), return_vals.get("fees")

    @classmethod
    def _parse_taxes(cls, event_dict: Dict[Any, Any]) -> Optional[float]:
        """Parses the levied taxes

        Args:
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Optional[float]: taxes
        """
        # taxes keywords
        taxes_keys = {"Steuer", "Steuern"}
        # Gather all section dicts
        sections = event_dict.get("details", {}).get("sections", [{}])
        # Gather all dicts pertaining to transactions
        transaction_dicts = filter(lambda x: x["title"] in {"Transaktion", "Geschäft"}, sections)
        for transaction_dict in transaction_dicts:
            # Filter for taxes dicts
            data = transaction_dict.get("data", [{}])
            taxes_dicts = filter(lambda x: x["title"] in taxes_keys, data)
            # Iterate over dicts containing tax information and parse each one
            for taxes_dict in taxes_dicts:
                parsed_taxes_val = cls._parse_float_from_detail(taxes_dict)
                if parsed_taxes_val is not None:
                    return parsed_taxes_val

        return None

    @staticmethod
    def _parse_card_note(event_dict: Dict[Any, Any]) -> Optional[str]:
        """Parses the note associated with card transactions

        Args:
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Optional[str]: note
        """
        if event_dict.get("eventType", "").startswith("card_"):
            return event_dict["eventType"]
        return None

    @staticmethod
    def _parse_float_from_detail(elem_dict: Dict[str, Any]) -> Optional[float]:
        """Parses a "detail" dictionary potentially containing a float in a certain locale format

        Args:
            str (Dict[str, Any]): _description_

        Returns:
            Optional[float]: parsed float value or None
        """
        unparsed_val = elem_dict.get("detail", {}).get("text", "")
        parsed_val = re.sub(r"[^\,\.\d-]", "", unparsed_val)

        # Try the locale that will fail more likely first.
        if "." not in parsed_val:
            locales = ("en", "de")
        else:
            locales = ("de", "en")

        try:
            result = float(parse_decimal(parsed_val, locales[0], strict=True))
        except NumberFormatError:
            try:
                result = float(parse_decimal(parsed_val, locales[1], strict=True))
            except NumberFormatError:
                return None
        return None if result == 0.0 else result
