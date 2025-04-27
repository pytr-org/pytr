import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Optional, Tuple

from babel.numbers import NumberFormatError, parse_decimal

from pytr.utils import get_logger


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
    "PAYMENT_INBOUND_CREDIT_CARD": PPEventType.DEPOSIT,
    "card_refund": PPEventType.DEPOSIT,
    "card_successful_oct": PPEventType.DEPOSIT,
    "card_tr_refund": PPEventType.DEPOSIT,
    # Dividends
    "CREDIT": PPEventType.DIVIDEND,
    "ssp_corporate_action_invoice_cash": PPEventType.DIVIDEND,
    # Interests
    "INTEREST_PAYOUT": PPEventType.INTEREST,
    "INTEREST_PAYOUT_CREATED": PPEventType.INTEREST,
    # Removals
    "OUTGOING_TRANSFER": PPEventType.REMOVAL,
    "OUTGOING_TRANSFER_DELEGATION": PPEventType.REMOVAL,
    "PAYMENT_OUTBOUND": PPEventType.REMOVAL,
    "card_failed_transaction": PPEventType.REMOVAL,
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
    "trading_savingsplan_executed": ConditionalEventType.TRADE_INVOICE,
    "trading_trade_executed": ConditionalEventType.TRADE_INVOICE,
    "benefits_spare_change_execution": ConditionalEventType.TRADE_INVOICE,
    "TRADE_INVOICE": ConditionalEventType.TRADE_INVOICE,
    "TRADE_CORRECTED": ConditionalEventType.TRADE_INVOICE,
}

logger = None


def get_event_logger():
    global logger
    if logger is None:
        logger = get_logger(__name__)
    return logger


events_known_ignored = [
    "CUSTOMER_CREATED",
    "DEVICE_RESET",
    "DOCUMENTS_ACCEPTED",
    "DOCUMENTS_CREATED",
    "EMAIL_VALIDATED",
    "ORDER_CANCELED",
    "ORDER_CREATED",
    "ORDER_EXPIRED",
    "ORDER_REJECTED",
    "PUK_CREATED",
    "RDD_FLOW",
    "REFERENCE_ACCOUNT_CHANGED",
    "SECURITIES_ACCOUNT_CREATED",
    "TAX_YEAR_END_REPORT",
    "VERIFICATION_TRANSFER_ACCEPTED",
    "card_failed_verification",
    "card_successful_verification",
    "crypto_annual_statement",
    "current_account_activated",
    "new_tr_iban",
    "trading_order_cancelled",
    "trading_order_created",
    "trading_order_rejected",
    "trading_savingsplan_execution_failed",
    "ssp_corporate_action_informative_notification",
    "ssp_corporate_action_invoice_shares",
    "ssp_dividend_option_customer_instruction",
]


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
        eventTypeStr = event_dict.get("eventType", "")
        event_type: Optional[EventType] = tr_event_type_mapping.get(eventTypeStr, None)
        if event_type is not None:
            if event_dict.get("status", "").lower() == "canceled":
                event_type = None
        else:
            if eventTypeStr not in events_known_ignored:
                get_event_logger().warning(f"Ignoring unknown event {eventTypeStr}")
                get_event_logger().debug("Unknown event %s: %s", eventTypeStr, json.dumps(event_dict, indent=4))
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
            shares, fees = cls._parse_shares_and_fees(event_dict)
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
        shares, fees = None, None
        dump_dict = {"eventType": event_dict["eventType"], "id": event_dict["id"]}

        sections = event_dict.get("details", {}).get("sections", [{}])
        transaction_dicts = filter(lambda x: x.get("title") in ["Transaktion"], sections)
        for transaction_dict in transaction_dicts:
            dump_dict["maintitle"] = transaction_dict["title"]
            data = transaction_dict.get("data", [{}])
            shares_dicts = filter(lambda x: x["title"] in ["Aktien", "Anteile"], data)
            for shares_dict in shares_dicts:
                dump_dict["subtitle"] = shares_dict["title"]
                dump_dict["type"] = "shares"
                pref_locale = (
                    "en"
                    if event_dict["eventType"] in ["benefits_saveback_execution", "benefits_spare_change_execution"]
                    and shares_dict["title"] == "Aktien"
                    else "de"
                )
                shares = cls._parse_float_from_detail(shares_dict, dump_dict, pref_locale)
                break

            fees_dicts = filter(lambda x: x["title"] == "Gebühr", data)
            for fees_dict in fees_dicts:
                dump_dict["subtitle"] = fees_dict["title"]
                dump_dict["type"] = "fees"
                fees = cls._parse_float_from_detail(fees_dict, dump_dict)
                break

            break

        return shares, fees

    @classmethod
    def _parse_taxes(cls, event_dict: Dict[Any, Any]) -> Optional[float]:
        """Parses the levied taxes

        Args:
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Optional[float]: taxes
        """
        parsed_taxes_val = None
        dump_dict = {"eventType": event_dict["eventType"], "id": event_dict["id"]}
        pref_locale = "en" if event_dict["eventType"] in ["INTEREST_PAYOUT"] else "de"

        sections = event_dict.get("details", {}).get("sections", [{}])
        transaction_dicts = filter(lambda x: x["title"] in ["Transaktion", "Geschäft"], sections)
        for transaction_dict in transaction_dicts:
            # Filter for taxes dicts
            dump_dict["maintitle"] = transaction_dict["title"]
            data = transaction_dict.get("data", [{}])
            taxes_dicts = filter(lambda x: x["title"] in ["Steuer", "Steuern"], data)
            # Iterate over dicts containing tax information and parse each one
            for taxes_dict in taxes_dicts:
                dump_dict["subtitle"] = taxes_dict["title"]
                dump_dict["type"] = "taxes"
                parsed_taxes_val = cls._parse_float_from_detail(taxes_dict, dump_dict, pref_locale)
                break
            break

        return parsed_taxes_val

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
    def _parse_float_from_detail(
        elem_dict: Dict[str, Any],
        dump_dict={"eventType": "Unknown", "id": "Unknown", "type": "Unknown"},
        pref_locale="de",
    ) -> Optional[float]:
        """Parses a "detail" dictionary potentially containing a float in a certain locale format

        Args:
            str (Dict[str, Any]): _description_

        Returns:
            Optional[float]: parsed float value or None
        """
        unparsed_val = elem_dict.get("detail", {}).get("text", "")
        if unparsed_val == "":
            return None
        parsed_val = re.sub(r"[^\,\.\d-]", "", unparsed_val)

        # Try the preferred locale first
        if pref_locale == "de":
            locales = ("de", "en")
        else:
            locales = ("en", "de")

        try:
            result = float(parse_decimal(parsed_val, locales[0], strict=True))
        except NumberFormatError:
            try:
                result = float(parse_decimal(parsed_val, locales[1], strict=True))
            except NumberFormatError:
                return None
            get_event_logger().warning(
                "Number %s parsed as %s although preference was %s: %s",
                parsed_val,
                locales[1],
                locales[0],
                json.dumps(dump_dict, indent=4),
            )
            return None if result == 0.0 else result

        alternative_result = None
        if "," in parsed_val or "." in parsed_val:
            try:
                alternative_result = float(parse_decimal(parsed_val, locales[1], strict=True))
            except NumberFormatError:
                pass

        if alternative_result is None:
            get_event_logger().debug(
                "Number %s parsed as %s: %s", parsed_val, locales[0], json.dumps(dump_dict, indent=4)
            )
        else:
            get_event_logger().debug(
                "Number %s parsed as %s but could also be parsed as %s: %s",
                parsed_val,
                locales[0],
                locales[1],
                json.dumps(dump_dict, indent=4),
            )

        return None if result == 0.0 else result
