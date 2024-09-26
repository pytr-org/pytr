from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import json
from typing import Any, Dict, List, Optional, Tuple
import re


class UnprocessedEventType(Enum):
    SAVEBACK = auto()
    TRADE_INVOICE = auto()


class PPEventType(Enum):
    BUY = "Buy"
    DEPOSIT = "Deposit"
    DIVIDEND = "Dividend"
    FEES = "Fees"
    FEES_REFUND = "Fees Refund"
    INTEREST = "Interest"
    INTEREST_CHARGE = "Interest Charge"
    REMOVAL = "Removal"
    SELL = "Sell"
    TAX_REFUND = "Tax Refund"
    TAXES = "Taxes"
    TRANSFER_IN = "Transfer (Inbound)"
    TRANSFER_OUT = "Transfer (Outbound)"


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
    "card_failed_transaction": PPEventType.REMOVAL,
    "card_order_billed": PPEventType.REMOVAL,
    "card_successful_atm_withdrawal": PPEventType.REMOVAL,
    "card_successful_transaction": PPEventType.REMOVAL,
    # Saveback
    "benefits_saveback_execution": UnprocessedEventType.SAVEBACK,
    # Trade invoices
    "ORDER_EXECUTED": UnprocessedEventType.TRADE_INVOICE,
    "SAVINGS_PLAN_EXECUTED": UnprocessedEventType.TRADE_INVOICE,
    "SAVINGS_PLAN_INVOICE_CREATED": UnprocessedEventType.TRADE_INVOICE,
    "TRADE_INVOICE": UnprocessedEventType.TRADE_INVOICE,
    # Tax refunds
    "TAX_REFUND": PPEventType.TAX_REFUND,
    # Taxes
    "PRE_DETERMINED_TAX_BASE_EARNING": PPEventType.TAXES,
}


@dataclass
class Event:
    value: float
    date: datetime
    event_type: EventType
    title: str
    isin: Optional[str] = field(default=None)
    note: Optional[str] = field(default=None)
    shares: Optional[float] = field(default=None)
    tax: Optional[float] = field(default=None)
    fee: Optional[float] = field(default=None)

    @classmethod
    def from_json(cls, event_json: Dict[Any, Any]):
        """Deserializes the json file into an Event object

        Args:
            event_json (json): _description_

        Returns:
            Event: Event object
        """
        value: float = event_json.get("amount", {}).get("value", None)
        date: datetime = datetime.fromisoformat(event_json["timestamp"][:19])
        event_type: EventType = tr_eventType_mapping.get(event_json["eventType"], None)
        title: str = event_json["title"]
        isin, shares, tax, note, fee = cls._parse_type_dependent_params(
            event_type, event_json
        )
        return cls(value, date, event_type, title, isin, note, shares, tax, fee)

    @classmethod
    def _parse_type_dependent_params(
        cls, event_type: EventType, event_json: Dict[Any, Any]
    ) -> Tuple[Optional[float]]:
        isin, shares, tax, note, fee = (None,) * 5
        # Parse isin
        if event_type is PPEventType.DIVIDEND:
            isin = cls._parse_isin(event_json)
            tax, note = cls._parse_tax_and_note(event_json)
        # Parse shares
        elif event_type is UnprocessedEventType.TRADE_INVOICE:
            isin = cls._parse_isin(event_json)
            shares, fee = cls._parse_shares_and_fee(event_json)
            tax, note = cls._parse_tax_and_note(event_json)
        # Parse taxes
        elif event_type is PPEventType.INTEREST:
            tax, note = cls._parse_tax_and_note(event_json)
        # Parse card notes
        elif event_type in [PPEventType.DEPOSIT, PPEventType.REMOVAL]:
            note = cls._parse_card_note(event_json)
        return isin, shares, tax, note, fee

    @staticmethod
    def _parse_isin(event_json: Dict[Any, Any]) -> str:
        """Parses the isin

        Args:
            event_json (Dict[Any, Any]): _description_

        Returns:
            str: isin
        """
        sections = event_json.get("details", {}).get("sections", [{}])
        isin = event_json.get("icon", "")
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
    def _parse_shares_and_fee(event_json: Dict[Any, Any]) -> Tuple[Optional[float]]:
        """Parses the amount of shares and the applicable fee

        Args:
            event_json (Dict[Any, Any]): _description_

        Returns:
            Tuple[Optional[float]]: [shares, fee]
        """
        return_vals = {}
        sections = event_json.get("details", {}).get("sections", [{}])
        for section in sections:
            if section.get("title") == "Transaktion":
                data = section["data"]
                shares_dicts = list(filter(lambda x: x["title"] in ["Aktien", "Anteile"], data))
                fee_dicts = list(filter(lambda x: x["title"] == "Gebühr", data))
                titles = ["shares"] * len(shares_dicts) + ["fee"] * len(fee_dicts)
                for key, elem_dict in zip(titles, shares_dicts + fee_dicts):
                    elem_unparsed = elem_dict.get("detail", {}).get("text", "")
                    elem_parsed = re.sub("[^\,\d-]", "", elem_unparsed).replace(
                        ",", "."
                    )
                    return_vals[key] = None if elem_parsed=="" or float(elem_parsed)==0. else float(elem_parsed)
        return return_vals["shares"], return_vals["fee"]

    @staticmethod
    def _parse_tax_and_note(event_json: Dict[Any, Any]) -> Tuple[Optional[float], Optional[str]]:
        """Hacky parse of the levied tax. @TODO Improve with better logs

        Args:
            event_json (Dict[Any, Any]): _description_

        Returns:
            Tuple[Optional[float], Optional[str]]: [Tax, tax info note]
        """
        tax, info = (None,) * 2
        return_values = {}
        # tax keywords
        tax_kws = ["Steuer", "Steuern", "Kapitalertragsteuer", "Solidaritätszuschlag"]
        # Gather all section dicts
        sections = event_json.get("details", {}).get("sections", [{}])
        # Gather all dicts pertaining to transactions
        transaction_dicts = list(
            filter(lambda x: x["title"] in ["Transaktion", "Geschäft"], sections)
        )
        for transaction_dict in transaction_dicts:
            # Check for "Steuer" and "infoPage" dicts
            data = transaction_dict.get("data", [{}])
            # Check for "infoPage" section
            action_dict = transaction_dict.get("action", {})
            action_sections = []
            if action_dict is not None and action_dict.get("type", "") == "infoPage":
                action_sections = action_dict.get("payload",{}).get("section",[])
            detailed_dicts = []
            if len(action_sections) == 3:
                detailed_dicts = sections[1].get("data", [])
            # Concatenate all found tax dicts
            tax_dicts = list(filter(lambda x: x["title"] in tax_kws, data + detailed_dicts))
            # Iterate over dicts containing tax information and parse it
            for tax_dict in tax_dicts:
                unparsed_tax_val = tax_dict.get("detail", {}).get("text", "")
                parsed_tax_val = re.sub("[^\,\d-]", "", unparsed_tax_val).replace(
                    ",", "."
                )
                if parsed_tax_val != "" or float(parsed_tax_val) != 0.0:
                    return_values[tax_dict.get("title", ""), ""] = parsed_tax_val
        # Parse return_values dict to tax and info variables
        tax = (
            return_values.get("Steuer", None)
            if "Steuer" in return_values.keys()
            else return_values.get("Steuern", None)
        )
        if "Steuer" in return_values.keys():
            tax = return_values["Steuer"], info = None
        elif "Steuern" in return_values.keys():
            tax = return_values["Steuern"]
            info = f"Kapitalertragsteuer - {return_values['Kapitalertragsteuer']}€;\
                Solidaritätszuschlag {return_values['Solidaritätszuschlag']}"
        return tax, info

    @staticmethod
    def _parse_card_note(event_json: Dict[Any, Any]) -> Optional[str]:
        """Parses the note associated with card transactions

        Args:
            event_json (Dict[Any, Any]): _description_

        Returns:
            Optional[str]: note
        """
        if event_json.get("eventType", "").startswith("card_"):
            return event_json["eventType"]
