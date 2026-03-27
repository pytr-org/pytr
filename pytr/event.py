import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum, auto
from typing import Any, Dict, Optional, Tuple

from babel.numbers import NumberFormatError, parse_decimal

from .utils import get_logger


class EventType(Enum):
    pass


class ConditionalEventType(EventType):
    """Events that conditionally map to None or one/multiple PPEventType events"""

    PRIVATE_MARKETS_ORDER = auto()
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
    SPINOFF = "SPINOFF"
    SPLIT = "SPLIT"
    SWAP = "SWAP"
    TAXES = "TAXES"
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
    "private_markets_trade_executed": ConditionalEventType.PRIVATE_MARKETS_ORDER,
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

title_event_type_mapping = {
    # Deposits
    "Einzahlung": PPEventType.DEPOSIT,
    # Saveback
    "Aktien-Bonus": ConditionalEventType.SAVEBACK,
    # Interests
    "Zinsen": PPEventType.INTEREST,
    # Tax refunds
    "Steuerkorrektur": PPEventType.TAX_REFUND,
    # Private markets order
    "Private Equity": ConditionalEventType.PRIVATE_MARKETS_ORDER,
}

subtitle_event_type_mapping = {
    # Dividends
    "Aktienprämiendividende": PPEventType.DIVIDEND,
    "Bardividende": PPEventType.DIVIDEND,
    "Bardividende korrigiert": PPEventType.DIVIDEND,
    "Dividende": PPEventType.DIVIDEND,
    "Dividende Wahlweise": PPEventType.DIVIDEND,
    "Tilgung": PPEventType.DIVIDEND,
    # Saveback
    "Saveback": ConditionalEventType.SAVEBACK,
    # Spinoff
    "Aktiendividende": PPEventType.SPINOFF,
    "Spin-off": PPEventType.SPINOFF,
    "Zwischenvertrieb von Wertpapieren": PPEventType.SPINOFF,
    # Split
    "Aktiensplit": PPEventType.SPLIT,
    "Bonusaktien": PPEventType.SPLIT,
    # Swap
    "Aufruf von Zwischenpapieren": PPEventType.SWAP,
    "Reverse Split": PPEventType.SWAP,
    "Teilrückzahlung ohne Reduzierung des Poolfaktors": PPEventType.SWAP,
    "Zusammenschluss": PPEventType.SWAP,
    # Taxes
    "Vorabpauschale": PPEventType.TAXES,
    # Trade invoices
    "Kauforder": ConditionalEventType.TRADE_INVOICE,
    "Limit-Buy-Order": ConditionalEventType.TRADE_INVOICE,
    "Limit-Sell-Order": ConditionalEventType.TRADE_INVOICE,
    "Limit Verkauf-Order neu abgerechnet": ConditionalEventType.TRADE_INVOICE,
    "Round up": ConditionalEventType.TRADE_INVOICE,
    "Sparplan ausgeführt": ConditionalEventType.TRADE_INVOICE,
    "Stop-Sell-Order": ConditionalEventType.TRADE_INVOICE,
    "Verkaufsorder": ConditionalEventType.TRADE_INVOICE,
    "Wertlos": ConditionalEventType.TRADE_INVOICE,
}

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
    "ssp_dividend_option_customer_instruction",
]

events_known_ignored_title = [
    "Crypto Jahresaufstellung",
    "Eignungsprüfung",
    "Ex-Post Kosteninformation",
    "Jährlicher Steuerreport",
    "Neue IBAN",
    "Persönliche Daten",
    "PUK versendet",
    "Rechtliche Dokumente",
    "Überprüfung der Identität",
]

events_known_ignored_subtitle = [
    "Cash oder Aktie",
    "Erteilt",
    "Jährliche Hauptversammlung",
    "Kartenprüfung",
    "Kauf-Abrechnung storniert",
    "Kauforder storniert",
    "Limit-Buy-Order abgelaufen",
    "Limit-Buy-Order erstellt",
    "Limit-Buy-Order storniert",
    "Limit Kauf-Abrechnung storniert",
    "Limit-Sell-Order abgelaufen",
    "Limit-Sell-Order abgelehnt",
    "Limit-Sell-Order erstellt",
    "Limit-Sell-Order storniert",
    "Limit Verkauf-Abrechnung storniert",
    "Sparplan fehlgeschlagen",
    "Stop-Market Verkauf-Abrechnung storniert",
    "Stop-Sell-Order storniert",
    "Verkaufsorder abgelehnt",
]

logger = None


def get_event_logger():
    global logger
    if logger is None:
        logger = get_logger(__name__)
    return logger


@dataclass
class Event:
    event_type: Optional[EventType]
    date: datetime
    title: str
    isin: Optional[str]
    isin2: Optional[str]
    shares: Optional[float]
    shares2: Optional[float]
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
        ts = event_dict["timestamp"]
        ts = ts[:-2] + ":" + ts[-2:]
        date: datetime = datetime.fromisoformat(ts)
        title: str = event_dict["title"]
        isin2: Optional[str] = None
        subtitle = event_dict["subtitle"]
        eventdesc = f"{title} {subtitle} ({event_dict['id']})"
        sections = event_dict.get("details", {}).get("sections", [{}])
        uebersicht_dict = next(filter(lambda x: x.get("title") in ["Übersicht"], sections), None)
        event_type: Optional[EventType] = None
        eventTypeStr = event_dict.get("eventType", "")
        if eventTypeStr == "timeline_legacy_migrated_events":
            event_type = timeline_legacy_migrated_events_title_type_mapping.get(title)
            if event_type is None:
                event_type = timeline_legacy_migrated_events_subtitle_type_mapping.get(subtitle)
            if event_type is None:
                for item in event_dict.get("details", {}).get("sections", []):
                    ititle = item.get("title", "")
                    if ititle.startswith("Du hast "):
                        if ititle.endswith(" erhalten"):
                            event_type = PPEventType.DEPOSIT
                            break
                        elif ititle.endswith(" gesendet"):
                            event_type = PPEventType.REMOVAL
                            break
            if event_type is None:
                print(f"unmatched timeline_legacy_migrated_events: {eventdesc}")
        elif eventTypeStr == "ssp_corporate_action_invoice_shares":
            if subtitle in [
                "Aktiendividende",
                "Spin-off",
                "Zwischenvertrieb von Wertpapieren",
            ]:
                event_type = PPEventType.SPINOFF
            elif subtitle == "Bonusaktien":
                event_type = PPEventType.SPLIT
            elif subtitle in ["Reverse Split", "Teilrückzahlung ohne Reduzierung des Poolfaktors", "Zusammenschluss"]:
                event_type = PPEventType.SWAP
            elif subtitle == "Wertlos":
                event_type = ConditionalEventType.TRADE_INVOICE
        elif eventTypeStr == "ssp_corporate_action_invoice_cash":
            if subtitle == "Aufruf von Zwischenpapieren":
                event_type = PPEventType.SWAP
            elif subtitle in [
                "Aktienprämiendividende",
                "Bardividende",
                "Bardividende korrigiert",
                "Dividende Wahlweise",
                "Tilgung",
            ]:
                event_type = PPEventType.DIVIDEND
            else:
                event_type = PPEventType.TAXES
        else:
            event_type = tr_event_type_mapping.get(eventTypeStr, None)
        if event_type is None:
            event_type = title_event_type_mapping.get(title, None)
        if event_type is None:
            event_type = subtitle_event_type_mapping.get(subtitle, None)
        if event_type is None and uebersicht_dict:
            for item in uebersicht_dict.get("data", []):
                ititle = item.get("title")
                if ititle == "Kartenzahlung":
                    event_type = PPEventType.REMOVAL
                elif ititle in ["Überweisung", "Kartenerstattung", "Überweisen"]:
                    if sections:
                        for item in sections:
                            ititle = item.get("title")
                            if ititle is None:
                                continue
                            if "gesendet" in ititle:
                                event_type = PPEventType.REMOVAL
                            elif "erhalten" in ititle:
                                event_type = PPEventType.DEPOSIT
                elif ititle == "Event":
                    if item.get("detail", {}).get("text", "") == "Bonusaktien":
                        event_type = PPEventType.DIVIDEND

        if event_type is None and sections:
            for item in sections:
                ititle = item.get("title")
                if ititle is None:
                    continue
                elif "Du hast" in ititle and "€" in ititle and "erhalten" in ititle:
                    event_type = PPEventType.DEPOSIT
                elif "Du hast" in ititle and "€" in ititle and "gesendet" in ititle:
                    event_type = PPEventType.REMOVAL

        if event_type is PPEventType.SPLIT and subtitle == "Bonusaktien" and uebersicht_dict:
            for item in uebersicht_dict.get("data", []):
                if item.get("title") == "Event" and item.get("detail", {}).get("text", "") == "Bonusaktien":
                    event_type = PPEventType.TAXES
        if event_type is PPEventType.SPINOFF and subtitle in ["Aktiendividende", "Spin-off"] and uebersicht_dict:
            for item in uebersicht_dict.get("data", []):
                if item.get("title") == "Event" and item.get("detail", {}).get("text", "") in [
                    "Aktiendividende",
                    "Spin-off",
                ]:
                    event_type = PPEventType.TAXES

        ignoreEvent = False
        if sections:
            for item in sections:
                ititle = item.get("title")
                if ititle is None:
                    continue
                if (
                    ititle
                    in [
                        "Deine Karte wurde verifiziert",
                        "Die Kartenüberprüfung ist fehlgeschlagen",
                        "Du hast dein Girokonto aktiviert",
                        "Du hast eine Kapitalma\u00dfnahme erhalten",
                        "You received an offer to participate in a capital increase",
                        "You're invited to a general meeting",
                    ]
                    or ititle.startswith("Du hast ein Angebot zum Verkauf von Aktien")
                    or ititle.startswith("You received an offer to sell shares")
                ):
                    ignoreEvent = True

        if title == "Auszahlungskonto" and subtitle == "Geändert":
            ignoreEvent = True
        if title == "Neues Gerät" and subtitle == "Gekoppelt":
            ignoreEvent = True
        if title == "Wertpapierdepot" and subtitle == "Eröffnet":
            ignoreEvent = True
        if title == "Basisinformationen" and subtitle == "Erhalten":
            ignoreEvent = True
        if title == "E-Mail" and subtitle == "Bestätigt":
            ignoreEvent = True

        if event_type is not None and event_dict.get("status", "").lower() == "canceled":
            event_type = None
        elif (
            event_type is None
            and eventTypeStr not in events_known_ignored
            and title not in events_known_ignored_title
            and subtitle not in events_known_ignored_subtitle
            and not ignoreEvent
        ):
            get_event_logger().warning(f'Ignoring unknown event "{eventdesc}"')
            get_event_logger().debug("Unknown event %s: %s", eventdesc, json.dumps(event_dict, indent=4))

        isin, shares, shares2, value, fees, taxes, note = cls._parse_type_dependent_params(event_type, event_dict)
        return cls(event_type, date, title, isin, isin2, shares, shares2, value, fees, taxes, note)

    @classmethod
    def _parse_type_dependent_params(
        cls, event_type: Optional[EventType], event_dict: Dict[Any, Any]
    ) -> Tuple[
        Optional[str],
        Optional[float],
        Optional[float],
        Optional[float],
        Optional[float],
        Optional[float],
        Optional[str],
    ]:
        """Parses the isin, shares, value, fees, taxes and note fields

        Args:
            event_type (EventType): _description_
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Tuple[Optional[Union[str, float]]]]: isin, shares, shares2, value, fees, taxes, note
        """
        isin, shares, shares2, value, fees, taxes, note = (None,) * 7

        if isinstance(event_type, ConditionalEventType) or event_type in [
            PPEventType.DIVIDEND,
            PPEventType.SPINOFF,
            PPEventType.SPLIT,
            PPEventType.SWAP,
            PPEventType.TAXES,
        ]:
            isin = cls._parse_isin(event_dict)
            shares, shares2, value, fees, taxes, note = cls._parse_shares_value_fees_taxes_note(event_type, event_dict)
        else:
            value = v if (v := event_dict.get("amount", {}).get("value", None)) is not None and v != 0.0 else None

            if event_type is PPEventType.INTEREST:
                taxes = cls._parse_taxes(event_dict)
            elif event_type in [PPEventType.DEPOSIT, PPEventType.REMOVAL]:
                note = cls._parse_card_note(event_dict)

        return isin, shares, shares2, value, fees, taxes, note

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
                if isinstance(isin2, dict):
                    isin2 = isin2.get("asset", "")
                isin2 = isin2[isin2.find("/") + 1 :]
                isin2 = isin2[: isin2.find("/")]
                break
        return isin2 if isin2 else isin

    @classmethod
    def _parse_shares_value_fees_taxes_note(
        cls, event_type: Optional[EventType], event_dict: Dict[Any, Any]
    ) -> Tuple[
        Optional[float],
        Optional[float],
        Optional[float],
        Optional[float],
        Optional[float],
        Optional[str],
    ]:
        """Parses the amount of shares, applicable fees and taxes

        Args:
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Tuple[Optional[float]]: shares, fees, taxes
        """
        (
            shares,
            shares2,
            fees,
            taxes,
            note,
            fees_dict,
            taxes_dict,
            gesamt_dict,
            uebersicht_dict,
            shares_dict,
            shares_dict2,
            wertpapier_dict,
            wertpapier_dict2,
            quotation_dict,
            order_dict,
        ) = (None,) * 15

        value: Optional[float] = v if (v := event_dict.get("amount", {}).get("value", None)) is not None else None

        title = event_dict["title"]
        subtitle = event_dict["subtitle"]
        eventdesc = f"{title} {subtitle} ({event_dict['id']})"
        eventTypeStr = event_dict.get("eventType", "")

        dump_dict = {"eventdesc": eventdesc}

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
                ititle = item.get("title")
                if ititle == "Gebühr" and not fees_dict:
                    fees_dict = item
                elif ititle == "Steuer" and not taxes_dict:
                    taxes_dict = item
                elif ititle == "Gesamt":
                    gesamt_dict = item
                elif ititle == "Aktien entfernt" and not shares_dict:
                    shares_dict = item
                elif ititle == "Wertpapier" and not wertpapier_dict:
                    wertpapier_dict = item
                elif ititle == "Wertpapier" and wertpapier_dict and not wertpapier_dict2:
                    wertpapier_dict2 = item
                elif ititle == "Aktien hinzugefügt" and not shares_dict:
                    shares_dict = item
                elif ititle == "Aktien hinzugefügt" and shares_dict and not shares_dict2:
                    shares_dict2 = item
                elif ititle == "Transaktion" and not transaction_dict:
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
                if (
                    event_type in [PPEventType.DIVIDEND, ConditionalEventType.SAVEBACK, PPEventType.SPINOFF]
                    or eventTypeStr
                    in [
                        "benefits_spare_change_execution",
                    ]
                    or subtitle
                    in [
                        "Wertlos",
                        "Aufruf von Zwischenpapieren",
                        "Round up",
                        "Aktiensplit",
                        "Bonusaktien",
                        "Reverse Split",
                        "Teilrückzahlung ohne Reduzierung des Poolfaktors",
                        "Zusammenschluss",
                    ]
                )
                and shares_dict["title"] in ["Aktien", "Aktien hinzugefügt", "Aktien entfernt"]
                else "de"
            )
            shares = cls._parse_float_from_text_value(
                shares_dict.get("detail", {}).get("text", ""), dump_dict, pref_locale
            )
            if shares_dict2:
                dump_dict["type"] = "shares2"
                shares2 = cls._parse_float_from_text_value(
                    shares_dict2.get("detail", {}).get("text", ""), dump_dict, pref_locale
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
            (
                event_type in [ConditionalEventType.SAVEBACK]
                or eventTypeStr in ["benefits_spare_change_execution", "ACQUISITION_TRADE_PERK"]
                or subtitle == "Round up"
                or title == "Aktien-Bonus"
            )
            and uebersicht_dict
            and transaction_dict
        ):
            shares = cls._parse_float_from_text_value(
                transaction_dict.get("detail", {}).get("displayValue", {}).get("prefix", ""), dump_dict, "en"
            )
            if (eventTypeStr == "ACQUISITION_TRADE_PERK" or title == "Aktien-Bonus") and gesamt_dict:
                value = cls._parse_float_from_text_value(gesamt_dict.get("detail", {}).get("text", ""), dump_dict)
                value = -value if value is not None else None
        elif (
            eventTypeStr
            not in [
                "ssp_corporate_action_invoice_cash",
                "private_markets_order_created",
                "private_markets_trade_executed",
            ]
            and title != "Private Equity"
            and subtitle != "Aktienprämiendividende"
            and event_type not in [PPEventType.DIVIDEND, PPEventType.TAXES]
        ):
            get_event_logger().warning("Could not parse shares from %s", eventdesc)
            get_event_logger().debug("Failed to parse shares from: %s", json.dumps(event_dict, indent=4))
            if eventTypeStr == "ACQUISITION_TRADE_PERK" or title == "Aktien-Bonus":
                value = 0
                shares = 0

        if fees_dict:
            dump_dict["subtitle"] = fees_dict["title"]
            dump_dict["type"] = "fees"
            fees = cls._parse_float_from_text_value(fees_dict.get("detail", {}).get("text", ""), dump_dict)
        elif (
            event_type not in [PPEventType.DIVIDEND, PPEventType.SPINOFF]
            and eventTypeStr
            not in [
                "ACQUISITION_TRADE_PERK",
                "ssp_corporate_action_invoice_cash",
                "ssp_corporate_action_invoice_shares",
            ]
            and title not in ["Aktien-Bonus"]
            and subtitle
            not in [
                "Aktiendividende",
                "Aktiensplit",
                "Aufruf von Zwischenpapieren",
                "Bonusaktien",
                "Reverse Split",
                "Spin-off",
                "Teilrückzahlung ohne Reduzierung des Poolfaktors",
                "Vorabpauschale",
                "Wertlos",
                "Zusammenschluss",
            ]
        ):
            get_event_logger().warning("Could not parse fees from %s", eventdesc)
            get_event_logger().debug("Failed to parse fees from %s", json.dumps(event_dict, indent=4))

        if taxes_dict:
            dump_dict["subtitle"] = taxes_dict["title"]
            dump_dict["type"] = "taxes"
            taxes = cls._parse_float_from_text_value(taxes_dict.get("detail", {}).get("text", ""), dump_dict)
        # no logging here because events may or may not have taxes

        if (
            eventTypeStr in ["private_markets_order_created", "private_markets_trade_executed"]
            or title == "Private Equity"
        ):
            if value is None:
                shares = 0
            else:
                shares = abs(value) / 100
            if fees is not None:
                shares = shares - (abs(fees) / 100)
            note = event_dict["subtitle"]

        if (event_type == PPEventType.SPINOFF or subtitle == "Wertlos") and value is None:
            value = 0

        if event_type in [PPEventType.SPLIT, PPEventType.SWAP] and value is None:
            value = 0

        if event_type in [PPEventType.SPINOFF, PPEventType.SWAP]:
            if wertpapier_dict2:
                note = wertpapier_dict2["detail"]["text"]
            elif wertpapier_dict:
                note = wertpapier_dict["detail"]["text"]

        return shares, shares2, value, fees, taxes, note

    @classmethod
    def _parse_taxes(cls, event_dict: Dict[Any, Any]) -> Optional[float]:
        """Parses the levied taxes

        Args:
            event_dict (Dict[Any, Any]): _description_

        Returns:
            Optional[float]: taxes
        """
        taxes, taxes_dict = None, None
        title = event_dict["title"]
        subtitle = event_dict["subtitle"]
        eventdesc = f"{title} {subtitle} ({event_dict['id']})"
        dump_dict = {"eventdesc": eventdesc, "id": event_dict["id"]}
        # pref_locale = "en" if event_dict.get("eventType", None) in [None, "INTEREST_PAYOUT"] else "de"
        pref_locale = "de"

        sections = event_dict.get("details", {}).get("sections", [{}])
        transaction_dict = next(filter(lambda x: x["title"] in ["Transaktion", "Geschäft"], sections), None)
        if transaction_dict:
            # Filter for taxes dicts
            dump_dict["maintitle"] = transaction_dict["title"]
            data = transaction_dict.get("data", [{}])
            taxes_dict = next(filter(lambda x: x["title"] in ["Steuer", "Steuern"], data), None)
            # if transaction_dict.get("action", {}).get("type", "") == "infoPage":
            #    pref_locale = "de"
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
        eventTypeStr = event_dict.get("eventType", "")
        if eventTypeStr.startswith("card_"):
            return eventTypeStr

        sections = event_dict.get("details", {}).get("sections", [{}])
        uebersicht_dict = next(filter(lambda x: x.get("title") in ["Übersicht"], sections), None)
        # Iterate over the top-level data list
        if uebersicht_dict:
            for item in uebersicht_dict.get("data", []):
                if item.get("title") == "Kartenzahlung":
                    return "card_successful_transaction"
                elif item.get("title") == "Kartenerstattung":
                    return "card_refund"

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
