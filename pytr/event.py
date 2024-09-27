from dataclasses import dataclass
from datetime import datetime
from enum import auto, Enum
import re
from typing import Any, Dict, Optional, Tuple, Union


class UnprocessedEventType(Enum):
    """Events that potentially encompass multiple PPEventType events"""

    SAVEBACK = auto()
    TRADE_INVOICE = auto()


class PPEventType(Enum):
    """PP Event Types"""

    BUY = "BUY"
    DEPOSIT = "DEPOSIT"
    DIVIDEND = "DIVIDEND"
    FEES = "FEES"
    FEES_REFUND = "FEES_REFUND"  # Currently not mapped to
    INTEREST = "INTEREST"
    INTEREST_CHARGE = "INTEREST_CHARGE"  # Currently not mapped to
    REMOVAL = "REMOVAL"
    SELL = "SELL"
    TAXES = "TAXES"
    TAX_REFUND = "TAX_REFUND"
    TRANSFER_IN = "TRANSFER_IN"  # Currently not mapped to
    TRANSFER_OUT = "TRANSFER_OUT"  # Currently not mapped to


class EventType(Enum):
    PP_EVENT_TYPE = PPEventType
    UNPROCESSED_EVENT_TYPE = UnprocessedEventType


tr_eventType_mapping = {
    # Deposits
    "INCOMING_TRANSFER": PPEventType.DEPOSIT,
    "INCOMING_TRANSFER_DELEGATION": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND_GOOGLE_PAY": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND_SEPA_DIRECT_DEBIT": PPEventType.DEPOSIT,
    "card_refund": PPEventType.DEPOSIT,
    "card_successful_oct": PPEventType.DEPOSIT,
    # Dividends
    "CREDIT": PPEventType.DIVIDEND,
    "ssp_corporate_action_invoice_cash": PPEventType.DIVIDEND,
    # Interests
    "INTEREST_PAYOUT": PPEventType.INTEREST,
    "INTEREST_PAYOUT_CREATED": PPEventType.INTEREST,
    # Removals
    "OUTGOING_TRANSFER_DELEGATION": PPEventType.REMOVAL,
    "PAYMENT_OUTBOUND": PPEventType.REMOVAL,
    "card_order_billed": PPEventType.REMOVAL,
    "card_successful_atm_withdrawal": PPEventType.REMOVAL,
    "card_successful_transaction": PPEventType.REMOVAL,
    # Saveback
    "benefits_saveback_execution": UnprocessedEventType.SAVEBACK,
    # Tax refunds
    "TAX_REFUND": PPEventType.TAX_REFUND,
    # Trade invoices
    "ORDER_EXECUTED": UnprocessedEventType.TRADE_INVOICE,
    "SAVINGS_PLAN_EXECUTED": UnprocessedEventType.TRADE_INVOICE,
    "SAVINGS_PLAN_INVOICE_CREATED": UnprocessedEventType.TRADE_INVOICE,
    "TRADE_INVOICE": UnprocessedEventType.TRADE_INVOICE,
}


@dataclass
class Event:
    date: datetime
    title: str
    event_type: Optional[EventType]
    fee: Optional[float]
    isin: Optional[str]
    note: Optional[str]
    shares: Optional[float]
    tax: Optional[float]
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
        event_type: Optional[EventType] = tr_eventType_mapping.get(
            event_dict["eventType"], None
        )
        title: str = event_dict["title"]
        value: Optional[float] = (
            v
            if (v := event_dict.get("amount", {}).get("value", None)) is not None
            and v != 0.0
            else None
        )
        fee, isin, note, shares, tax = cls._parse_type_dependent_params(
            event_type, event_dict
        )
        return cls(date, title, event_type, fee, isin, note, shares, tax, value)

    @classmethod
    def _parse_type_dependent_params(
        cls, event_type: EventType, event_dict: Dict[Any, Any]
    ) -> Tuple[Optional[Union[str, float]]]:
        """Parses the fee, isin, note, shares and tax fields

        Args:
            event_type (EventType): _description_
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Tuple[Optional[Union[str, float]]]]: fee, isin, note, shares, tax  
        """
        isin, shares, tax, note, fee = (None,) * 5
        # Parse isin
        if event_type is PPEventType.DIVIDEND:
            isin = cls._parse_isin(event_dict)
            tax = cls._parse_tax(event_dict)
        # Parse shares
        elif isinstance(event_type, UnprocessedEventType):
            isin = cls._parse_isin(event_dict)
            shares, fee = cls._parse_shares_and_fee(event_dict)
            tax = cls._parse_tax(event_dict)
        # Parse taxes
        elif event_type is PPEventType.INTEREST:
            tax = cls._parse_tax(event_dict)
        # Parse card notes
        elif event_type in [PPEventType.DEPOSIT, PPEventType.REMOVAL]:
            note = cls._parse_card_note(event_dict)
        return fee, isin, note, shares, tax

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

    @staticmethod
    def _parse_shares_and_fee(event_dict: Dict[Any, Any]) -> Tuple[Optional[float]]:
        """Parses the amount of shares and the applicable fee

        Args:
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Tuple[Optional[float]]: [shares, fee]
        """
        return_vals = {}
        sections = event_dict.get("details", {}).get("sections", [{}])
        for section in sections:
            if section.get("title") == "Transaktion":
                data = section["data"]
                shares_dicts = list(
                    filter(lambda x: x["title"] in ["Aktien", "Anteile"], data)
                )
                fee_dicts = list(filter(lambda x: x["title"] == "Gebühr", data))
                titles = ["shares"] * len(shares_dicts) + ["fee"] * len(fee_dicts)
                for key, elem_dict in zip(titles, shares_dicts + fee_dicts):
                    elem_unparsed = elem_dict.get("detail", {}).get("text", "")
                    elem_parsed = re.sub("[^\,\.\d-]", "", elem_unparsed).replace(
                        ",", "."
                    )
                    return_vals[key] = (
                        None
                        if elem_parsed == "" or float(elem_parsed) == 0.0
                        else float(elem_parsed)
                    )
        return return_vals["shares"], return_vals["fee"]

    @staticmethod
    def _parse_tax(event_dict: Dict[Any, Any]) -> Tuple[Optional[float]]:
        """Parses the levied tax

        Args:
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Tuple[Optional[float]]: [Tax]
        """
        # tax keywords
        tax_keys = {"Steuer", "Steuern"}
        # Gather all section dicts
        sections = event_dict.get("details", {}).get("sections", [{}])
        # Gather all dicts pertaining to transactions
        transaction_dicts = filter(
            lambda x: x["title"] in {"Transaktion", "Geschäft"}, sections
        )
        for transaction_dict in transaction_dicts:
            # Filter for tax dicts
            data = transaction_dict.get("data", [{}])
            tax_dicts = filter(lambda x: x["title"] in tax_keys, data)
            # Iterate over dicts containing tax information and parse each one
            for tax_dict in tax_dicts:
                unparsed_tax_val = tax_dict.get("detail", {}).get("text", "")
                parsed_tax_val = re.sub("[^\,\.\d-]", "", unparsed_tax_val).replace(
                    ",", "."
                )
                if parsed_tax_val != "" and float(parsed_tax_val) != 0.0:
                    return float(parsed_tax_val)

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
