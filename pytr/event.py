import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
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
    PRIVATE_MARKETS_ORDER = auto()


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
    "ACCOUNT_TRANSFER_INCOMING": PPEventType.DEPOSIT,
    "INCOMING_TRANSFER": PPEventType.DEPOSIT,
    "INCOMING_TRANSFER_DELEGATION": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND_APPLE_PAY": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND_GOOGLE_PAY": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND_SEPA_DIRECT_DEBIT": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND_CREDIT_CARD": PPEventType.DEPOSIT,
    "PAYMENT-SERVICE-IN-PAYMENT-DIRECT-DEBIT": PPEventType.DEPOSIT,
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
    "DIRECT_DEBIT_TRANSFER_DELEGATION": PPEventType.REMOVAL,
    "PAYMENT_OUTBOUND": PPEventType.REMOVAL,
    "card_failed_transaction": PPEventType.REMOVAL,
    "card_order_billed": PPEventType.REMOVAL,
    "card_successful_atm_withdrawal": PPEventType.REMOVAL,
    "card_successful_transaction": PPEventType.REMOVAL,
    "junior_p2p_transfer": PPEventType.REMOVAL,
    # Saveback
    "ACQUISITION_TRADE_PERK": ConditionalEventType.SAVEBACK,
    "benefits_saveback_execution": ConditionalEventType.SAVEBACK,
    # Tax refunds
    "TAX_CORRECTION": PPEventType.TAX_REFUND,
    "TAX_REFUND": PPEventType.TAX_REFUND,
    "ssp_tax_correction_invoice": PPEventType.TAX_REFUND,
    # Trade invoices
    "ORDER_EXECUTED": ConditionalEventType.TRADE_INVOICE,
    "SAVINGS_PLAN_EXECUTED": ConditionalEventType.TRADE_INVOICE,
    "SAVINGS_PLAN_INVOICE_CREATED": ConditionalEventType.TRADE_INVOICE,
    "TRADE_CORRECTED": ConditionalEventType.TRADE_INVOICE,
    "TRADE_INVOICE": ConditionalEventType.TRADE_INVOICE,
    "benefits_spare_change_execution": ConditionalEventType.TRADE_INVOICE,
    "trading_savingsplan_executed": ConditionalEventType.TRADE_INVOICE,
    "trading_trade_executed": ConditionalEventType.TRADE_INVOICE,
    # Private markets order
    "private_markets_order_created": ConditionalEventType.PRIVATE_MARKETS_ORDER,
}

timeline_legacy_migrated_events_title_type_mapping = {
    # Interests
    "Zinsen": PPEventType.INTEREST,
}

timeline_legacy_migrated_events_subtitle_type_mapping = {
    # Trade invoices
    "Kauforder": ConditionalEventType.TRADE_INVOICE,
    "Limit-Buy-Order": ConditionalEventType.TRADE_INVOICE,
    "Limit-Sell-Order": ConditionalEventType.TRADE_INVOICE,
    "Limit Verkauf-Order neu abgerechnet": ConditionalEventType.TRADE_INVOICE,
    "Sparplan ausgeführt": ConditionalEventType.TRADE_INVOICE,
    "Stop-Sell-Order": ConditionalEventType.TRADE_INVOICE,
    "Verkaufsorder": ConditionalEventType.TRADE_INVOICE,
}

logger = None


def get_event_logger():
    global logger
    if logger is None:
        logger = get_logger(__name__)
    return logger


events_known_ignored = [
    "AML_SOURCE_OF_WEALTH_RESPONSE_EXECUTED",
    "CASH_ACCOUNT_CHANGED",
    "CREDIT_CANCELED",
    "CUSTOMER_CREATED",
    "CRYPTO_ANNUAL_STATEMENT",
    "DEVICE_RESET",
    "DOCUMENTS_ACCEPTED",
    "DOCUMENTS_CHANGED",
    "DOCUMENTS_CREATED",
    "EMAIL_VALIDATED",
    "EX_POST_COST_REPORT",
    "EX_POST_COST_REPORT_CREATED",
    "EXEMPTION_ORDER_CHANGE_REQUESTED",
    "EXEMPTION_ORDER_CHANGE_REQUESTED_AUTOMATICALLY",
    "EXEMPTION_ORDER_CHANGED",
    "INPAYMENTS_SEPA_MANDATE_CREATED",
    "INSTRUCTION_CORPORATE_ACTION",
    "JUNIOR_ONBOARDING_GUARDIAN_B_CONSENT",
    "GENERAL_MEETING",
    "GESH_CORPORATE_ACTION",
    "MATURITY",
    "ORDER_CANCELED",
    "ORDER_CREATED",
    "ORDER_EXPIRED",
    "ORDER_REJECTED",
    "PRE_DETERMINED_TAX_BASE_EARNING",
    "PUK_CREATED",
    "QUARTERLY_REPORT",
    "RDD_FLOW",
    "REFERENCE_ACCOUNT_CHANGED",
    "REFERRAL_FIRST_TRADE_EXECUTED_INVITEE",
    "SECURITIES_ACCOUNT_CREATED",
    "SHAREBOOKING",
    "SHAREBOOKING_TRANSACTIONAL",
    "STOCK_PERK_REFUNDED",
    "TAX_YEAR_END_REPORT",
    "VERIFICATION_TRANSFER_ACCEPTED",
    "YEAR_END_TAX_REPORT",
    "card_failed_verification",
    "card_successful_verification",
    "crypto_annual_statement",
    "current_account_activated",
    "new_tr_iban",
    "private_markets_suitability_quiz_completed",
    "ssp_general_meeting_customer_instruction",
    "ssp_tender_offer_customer_instruction",
    "trading_order_cancelled",
    "trading_order_created",
    "trading_order_expired",
    "trading_order_rejected",
    "trading_savingsplan_execution_failed",
    "ssp_capital_increase_customer_instruction",
    "ssp_corporate_action_informative_notification",
    "ssp_corporate_action_invoice_shares",
    "ssp_dividend_option_customer_instruction",
]


@dataclass
class Event:
    date: datetime
    title: str
    event_type: Optional[EventType]
    isin: Optional[str]
    shares: Optional[float]
    value: Optional[float]
    fees: Optional[float]
    taxes: Optional[float]
    note: Optional[str]

    @classmethod
    def from_dict(cls, event_dict: Dict[Any, Any]):
        """Deserializes the event dictionary into an Event object

        Args:
            event_dict (json): _description_

        Returns:
            Event: Event object
        """
        date: datetime = datetime.fromisoformat(event_dict["timestamp"][:19])
        title: str = event_dict["title"]
        event_type: Optional[EventType] = cls._parse_type(event_dict)
        isin, shares, value, fees, taxes, note = cls._parse_type_dependent_params(event_type, event_dict)
        return cls(date, title, event_type, isin, shares, value, fees, taxes, note)

    @staticmethod
    def _parse_type(event_dict: Dict[Any, Any]) -> Optional[EventType]:
        eventTypeStr = event_dict.get("eventType", "")
        event_type: Optional[EventType] = None
        if eventTypeStr == "timeline_legacy_migrated_events":
            event_type = timeline_legacy_migrated_events_title_type_mapping.get(event_dict.get("title", ""), None)
            if event_type is None:
                event_type = timeline_legacy_migrated_events_subtitle_type_mapping.get(
                    event_dict.get("subtitle", ""), None
                )
            if event_type is None:
                for item in event_dict.get("details", {}).get("sections", []):
                    title = item.get("title", "")
                    if title.startswith("Du hast "):
                        if title.endswith(" erhalten"):
                            event_type = PPEventType.DEPOSIT
                            break
                        elif title.endswith(" gesendet"):
                            event_type = PPEventType.REMOVAL
                            break
            if event_type is None:
                print(
                    f"unmatched timeline_legacy_migrated_events: title={event_dict.get('title', '')} subtitle={event_dict.get('subtitle', '')}"
                )
        else:
            event_type = tr_event_type_mapping.get(eventTypeStr, None)
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
    ) -> Tuple[Optional[str], Optional[float], Optional[float], Optional[float], Optional[float], Optional[str]]:
        """Parses the fees, isin, note, shares and taxes fields

        Args:
            event_type (EventType): _description_
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Tuple[Optional[Union[str, float]]]]: fees, isin, note, shares, taxes
        """
        isin, shares, value, fees, taxes, note = (None,) * 6

        if isinstance(event_type, ConditionalEventType) or event_type is PPEventType.DIVIDEND:
            isin = cls._parse_isin(event_dict)
            shares, value, fees, taxes, note = cls._parse_shares_value_fees_taxes_note(event_dict)
        else:
            value = v if (v := event_dict.get("amount", {}).get("value", None)) is not None and v != 0.0 else None

            if event_type is PPEventType.INTEREST:
                taxes = cls._parse_taxes(event_dict)
            elif event_type in [PPEventType.DEPOSIT, PPEventType.REMOVAL]:
                note = cls._parse_card_note(event_dict)

        return isin, shares, value, fees, taxes, note

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
        isin2 = None
        for section in sections:
            action = section.get("action", None)
            if action and action.get("type", {}) == "instrumentDetail":
                isin2 = section.get("action", {}).get("payload")
                break
            if section.get("type", {}) == "header":
                isin2 = section.get("data", {}).get("icon")
                isin2 = isin2[isin2.find("/") + 1 :]
                isin2 = isin2[: isin2.find("/")]
                break
        return isin2 if isin2 else isin

    @classmethod
    def _parse_shares_value_fees_taxes_note(
        cls, event_dict: Dict[Any, Any]
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[str]]:
        """Parses the amount of shares, applicable fees and taxes

        Args:
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Tuple[Optional[float]]: shares, fees, taxes
        """
        (
            shares,
            fees,
            taxes,
            note,
            fees_dict,
            taxes_dict,
            gesamt_dict,
            uebersicht_dict,
            shares_dict,
            quotation_dict,
            order_dict,
        ) = (None,) * 11

        value: Optional[float] = (
            v if (v := event_dict.get("amount", {}).get("value", None)) is not None and v != 0.0 else None
        )

        dump_dict = {"eventType": event_dict["eventType"], "id": event_dict["id"]}

        sections = event_dict.get("details", {}).get("sections", [{}])

        transaction_dict = next(filter(lambda x: x.get("title") in ["Transaktion", "Geschäft"], sections), None)
        if transaction_dict:
            # old style event
            dump_dict["maintitle"] = transaction_dict["title"]
            data = transaction_dict.get("data", [{}])
            shares_dict = next(filter(lambda x: x["title"] in ["Aktien", "Anteile"], data), None)
            fees_dict = next(filter(lambda x: x["title"] == "Gebühr", data), None)
            taxes_dict = next(filter(lambda x: x["title"] in ["Steuer", "Steuern"], data), None)

        uebersicht_dict = next(filter(lambda x: x.get("title") in ["Übersicht"], sections), None)
        if uebersicht_dict:
            # new style event
            for item in uebersicht_dict.get("data", []):
                title = item.get("title")
                if title == "Gebühr" and not fees_dict:
                    fees_dict = item
                elif title == "Steuer" and not taxes_dict:
                    taxes_dict = item
                elif title == "Gesamt":
                    gesamt_dict = item
                elif title == "Aktien entfernt" and not shares_dict:
                    shares_dict = item
                elif title == "Transaktion" and not transaction_dict:
                    transaction_dict = item
                    sections = item.get("detail", {}).get("action", {}).get("payload", {}).get("sections", [])

                    for section in sections:
                        if section.get("type") == "table":
                            for subitem in section.get("data", []):
                                if subitem.get("title") == "Aktien" and not shares_dict:
                                    shares_dict = subitem
                                elif subitem.get("title") == "Quotation" and not quotation_dict:
                                    quotation_dict = subitem
                                elif subitem.get("title") == "Order" and not order_dict:
                                    order_dict = subitem

        if shares_dict:
            dump_dict["subtitle"] = shares_dict["title"]
            dump_dict["type"] = "shares"
            pref_locale = (
                "en"
                if event_dict["eventType"]
                in [
                    "benefits_saveback_execution",
                    "benefits_spare_change_execution",
                    "ssp_corporate_action_invoice_cash",
                ]
                and shares_dict["title"] == "Aktien"
                else "de"
            )
            shares = cls._parse_float_from_text_value(
                shares_dict.get("detail", {}).get("text", ""), dump_dict, pref_locale
            )
        elif order_dict and quotation_dict:
            order = cls._parse_float_from_text_value(order_dict.get("detail", {}).get("text", ""), dump_dict)
            quotation = cls._parse_float_from_text_value(quotation_dict.get("detail", {}).get("text", ""), dump_dict)
            if order and quotation:
                shares = float(
                    (Decimal(order) / Decimal(quotation) * Decimal(100)).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                )
        elif (
            event_dict["eventType"]
            in ["benefits_saveback_execution", "benefits_spare_change_execution", "ACQUISITION_TRADE_PERK"]
            and uebersicht_dict
            and transaction_dict
        ):
            shares = cls._parse_float_from_text_value(
                transaction_dict.get("detail", {}).get("displayValue", {}).get("prefix", ""), dump_dict, "en"
            )
            if event_dict["eventType"] == "ACQUISITION_TRADE_PERK" and gesamt_dict:
                value = cls._parse_float_from_text_value(gesamt_dict.get("detail", {}).get("text", ""), dump_dict)
        elif event_dict["eventType"] not in ["ssp_corporate_action_invoice_cash", "private_markets_order_created"]:
            get_event_logger().warning("Could not parse shares from %s", event_dict["eventType"])
            get_event_logger().debug("Failed to parse shares from: %s", json.dumps(event_dict, indent=4))

        if fees_dict:
            dump_dict["subtitle"] = fees_dict["title"]
            dump_dict["type"] = "fees"
            fees = cls._parse_float_from_text_value(fees_dict.get("detail", {}).get("text", ""), dump_dict)
        elif event_dict["eventType"] != "ssp_corporate_action_invoice_cash":
            get_event_logger().warning("Could not parse fees from %s", event_dict["eventType"])
            get_event_logger().debug("Failed to parse fees from %s", json.dumps(event_dict, indent=4))

        if taxes_dict:
            dump_dict["subtitle"] = taxes_dict["title"]
            dump_dict["type"] = "taxes"
            taxes = cls._parse_float_from_text_value(taxes_dict.get("detail", {}).get("text", ""), dump_dict)
        # no logging here because events may or may not have taxes

        if event_dict["eventType"] == "private_markets_order_created":
            if value is None:
                shares = 0
            else:
                shares = abs(value)
            if fees is not None:
                shares = shares - abs(fees)
            note = event_dict["subtitle"]

        return shares, value, fees, taxes, note

    @classmethod
    def _parse_taxes(cls, event_dict: Dict[Any, Any]) -> Optional[float]:
        """Parses the levied taxes

        Args:
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Optional[float]: taxes
        """
        taxes, taxes_dict = None, None
        dump_dict = {"eventType": event_dict["eventType"], "id": event_dict["id"]}
        pref_locale = "en" if event_dict["eventType"] in ["INTEREST_PAYOUT"] else "de"

        sections = event_dict.get("details", {}).get("sections", [{}])
        transaction_dict = next(filter(lambda x: x["title"] in ["Transaktion", "Geschäft"], sections), None)
        if transaction_dict:
            # Filter for taxes dicts
            dump_dict["maintitle"] = transaction_dict["title"]
            data = transaction_dict.get("data", [{}])
            taxes_dict = next(filter(lambda x: x["title"] in ["Steuer", "Steuern"], data), None)
        else:
            uebersicht_dict = next(filter(lambda x: x.get("title") in ["Übersicht"], sections), None)
            # Iterate over the top-level data list
            if uebersicht_dict:
                for item in uebersicht_dict.get("data", []):
                    if item.get("title") == "Steuer":
                        taxes_dict = item
                        break

        # Iterate over dicts containing tax information and parse each one
        if taxes_dict:
            dump_dict["subtitle"] = taxes_dict["title"]
            dump_dict["type"] = "taxes"
            taxes = cls._parse_float_from_text_value(
                taxes_dict.get("detail", {}).get("text", ""), dump_dict, pref_locale
            )
        # no logging here because events may or may not have taxes

        return taxes

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
    def _parse_float_from_text_value(
        unparsed_val: str,
        dump_dict={"eventType": "Unknown", "id": "Unknown", "type": "Unknown"},
        pref_locale="de",
    ) -> Optional[float]:
        """Parses a text value potentially containing a float in a certain locale format

        Args:
            str: unparsed value

        Returns:
            Optional[float]: parsed float value or None
        """
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
