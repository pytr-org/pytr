import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum, auto
from typing import Any, Dict, Optional

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
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


tr_event_type_mapping = {
    # Deposits
    "ACCOUNT_TRANSFER_INCOMING": PPEventType.DEPOSIT,
    "BANK_TRANSACTION_INCOMING": PPEventType.DEPOSIT,
    "CARD_REFUND": PPEventType.DEPOSIT,
    "CARD_SUCCESSFUL_OCT": PPEventType.DEPOSIT,
    "CARD_TR_REFUND": PPEventType.DEPOSIT,
    "INCOMING_TRANSFER": PPEventType.DEPOSIT,
    "INCOMING_TRANSFER_DELEGATION": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND_APPLE_PAY": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND_CREDIT_CARD": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND_GOOGLE_PAY": PPEventType.DEPOSIT,
    "PAYMENT_INBOUND_SEPA_DIRECT_DEBIT": PPEventType.DEPOSIT,
    "PAYMENT-SERVICE-IN-PAYMENT-DIRECT-DEBIT": PPEventType.DEPOSIT,
    # Dividends
    "CREDIT": PPEventType.DIVIDEND,
    # Interests
    "INTEREST_PAYOUT": PPEventType.INTEREST,
    "INTEREST_PAYOUT_CREATED": PPEventType.INTEREST,
    # Removals
    "BANK_TRANSACTION_OUTGOING": PPEventType.REMOVAL,
    "CARD_FAILED_TRANSACTION": PPEventType.REMOVAL,
    "CARD_ORDER_BILLED": PPEventType.REMOVAL,
    "CARD_SUCCESSFUL_ATM_WITHDRAWAL": PPEventType.REMOVAL,
    "CARD_SUCCESSFUL_TRANSACTION": PPEventType.REMOVAL,
    "CARD_TRANSACTION": PPEventType.REMOVAL,
    "JUNIOR_P2P_TRANSFER": PPEventType.REMOVAL,
    "OUTGOING_TRANSFER": PPEventType.REMOVAL,
    "OUTGOING_TRANSFER_DELEGATION": PPEventType.REMOVAL,
    "PAYMENT_OUTBOUND": PPEventType.REMOVAL,
    # Transfers
    "SSP_SECURITIES_TRANSFER_INCOMING": PPEventType.TRANSFER_IN,
    # Saveback
    "ACQUISITION_TRADE_PERK": ConditionalEventType.SAVEBACK,
    "BENEFITS_SAVEBACK_EXECUTION": ConditionalEventType.SAVEBACK,
    "SAVEBACK_AGGREGATE": ConditionalEventType.SAVEBACK,
    # Tax refunds
    "SSP_TAX_CORRECTION": PPEventType.TAX_REFUND,
    "SSP_TAX_CORRECTION_INVOICE": PPEventType.TAX_REFUND,
    "TAX_CORRECTION": PPEventType.TAX_REFUND,
    "TAX_REFUND": PPEventType.TAX_REFUND,
    # Trade invoices
    "BENEFITS_SPARE_CHANGE_EXECUTION": ConditionalEventType.TRADE_INVOICE,
    "IPO_TRADE_EXECUTED": ConditionalEventType.TRADE_INVOICE,
    "ORDER_EXECUTED": ConditionalEventType.TRADE_INVOICE,
    "SAVINGS_PLAN_EXECUTED": ConditionalEventType.TRADE_INVOICE,
    "SAVINGS_PLAN_INVOICE_CREATED": ConditionalEventType.TRADE_INVOICE,
    "SPARE_CHANGE_AGGREGATE": ConditionalEventType.TRADE_INVOICE,
    "TRADE_CORRECTED": ConditionalEventType.TRADE_INVOICE,
    "TRADE_INVOICE": ConditionalEventType.TRADE_INVOICE,
    "TRADING_SAVINGSPLAN_EXECUTED": ConditionalEventType.TRADE_INVOICE,
    "TRADING_TRADE_EXECUTED": ConditionalEventType.TRADE_INVOICE,
    # Private markets order
    "PRIVATE_MARKET_FUND_TRADE_EXECUTED": ConditionalEventType.PRIVATE_MARKETS_ORDER,
    "PRIVATE_MARKETS_ORDER_CREATED": ConditionalEventType.PRIVATE_MARKETS_ORDER,
    "PRIVATE_MARKETS_TRADE_EXECUTED": ConditionalEventType.PRIVATE_MARKETS_ORDER,
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
    # Transfers
    "Aktien erhalten": PPEventType.TRANSFER_IN,
    "Aktien übertragen": PPEventType.TRANSFER_OUT,
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
    # Transfers
    "Aktien erhalten": PPEventType.TRANSFER_IN,
    "Aktien übertragen": PPEventType.TRANSFER_OUT,
}

events_known_ignored = [
    "ADDRESS_CHANGED",
    "AML_SOURCE_OF_WEALTH_RESPONSE_EXECUTED",
    "CARD_FAILED_VERIFICATION",
    "CARD_SUCCESSFUL_VERIFICATION",
    "CARD_VERIFICATION",
    "CASH_ACCOUNT_CHANGED",
    "CREDIT_CANCELED",
    "CRYPTO_ANNUAL_STATEMENT",
    "CRYPTO_TNC_UPDATE_2025",
    "CSX_CHAT_ACTIVITY",
    "CURRENT_ACCOUNT_ACTIVATED",
    "CUSTOMER_CREATED",
    "DEVICE_RESET",
    "DOCUMENTS_ACCEPTED",
    "DOCUMENTS_CHANGED",
    "DOCUMENTS_CREATED",
    "EMAIL_VALIDATED",
    "EXEMPTION_ORDER_CHANGE_REQUESTED",
    "EXEMPTION_ORDER_CHANGE_REQUESTED_AUTOMATICALLY",
    "EXEMPTION_ORDER_CHANGED",
    "EX_POST_COST_REPORT",
    "EX_POST_COST_REPORT_CREATED",
    "GENERAL_MEETING",
    "GESH_CORPORATE_ACTION",
    "INPAYMENTS_SEPA_MANDATE_CREATED",
    "INSTRUCTION_CORPORATE_ACTION",
    "JUNIOR_ONBOARDING_GUARDIAN_B_CONSENT",
    "MATURITY",
    "NEW_TR_IBAN",
    "ORDER_CANCELED",
    "ORDER_CREATED",
    "ORDER_EXPIRED",
    "ORDER_REJECTED",
    "PRE_DETERMINED_TAX_BASE_EARNING",
    "PRIVATE_MARKET_FUND_ORDER_RECEIVED",
    "PRIVATE_MARKETS_SUITABILITY_QUIZ_COMPLETED",
    "PUK_CREATED",
    "QUARTERLY_NET_WORTH_STATEMENT_CREATED",
    "QUARTERLY_REPORT",
    "RDD_FLOW",
    "REFERENCE_ACCOUNT_CHANGED",
    "REFERRAL_FIRST_TRADE_EXECUTED_INVITEE",
    "SECURITIES_ACCOUNT_CREATED",
    "SHAREBOOKING",
    "SHAREBOOKING_TRANSACTIONAL",
    "SSP_CAPITAL_INCREASE_CUSTOMER_INSTRUCTION",
    "SSP_CORPORATE_ACTION_INFORMATIVE",
    "SSP_CORPORATE_ACTION_INFORMATIVE_NOTIFICATION",
    "SSP_CORPORATE_ACTION_INSTRUCTION",
    "SSP_CORPORATE_ACTION_UPCOMING",
    "SSP_DIVIDEND_OPTION_CUSTOMER_INSTRUCTION",
    "SSP_GENERAL_MEETING_CUSTOMER_INSTRUCTION",
    "SSP_TENDER_OFFER_CUSTOMER_INSTRUCTION",
    "STOCK_PERK_REFUNDED",
    "TAX_YEAR_END_REPORT",
    "TAX_YEAR_END_REPORT_CREATED",
    "TRADING_ORDER_CANCELLED",
    "TRADING_ORDER_CREATED",
    "TRADING_ORDER_EXPIRED",
    "TRADING_ORDER_REJECTED",
    "TRADING_SAVINGSPLAN_EXECUTION_FAILED",
    "VERIFICATION_TRANSFER_ACCEPTED",
    "YEAR_END_TAX_REPORT",
]

events_known_ignored_title = [
    "Auszahlungskonto",
    "Basisinformationen",
    "Crypto Jahresaufstellung",
    "E-Mail",
    "Eignungsprüfung",
    "Ex-Post Kosteninformation",
    "Jährlicher Steuerreport",
    "Neue IBAN",
    "Neues Gerät",
    "Persönliche Daten",
    "PUK versendet",
    "Rechtliche Dokumente",
    "Überprüfung der Identität",
    "Wertpapierdepot",
]

events_known_ignored_subtitle = [
    "Außerordentliche oder spezielle Hauptversammlung",
    "Cash oder Aktie",
    "Dividende. Cash oder Stockdividende?",
    "Erteilt",
    "Fall abgeschlossen",
    "Jährliche Hauptversammlung",
    "Kartenprüfung",
    "Kauf-Abrechnung storniert",
    "Kauforder abgelehnt",
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
    "Teilnehmen?",
    "Verkaufsorder abgelehnt",
]

_note_to_isin: dict[str, str] = {
    "BlackRock Funding": "US09290D1019",
    "BYD": "CNE100000296",
    "Chipotle": "US1696561059",
    "Eckert & Ziegler": "DE0005659700",
    "Enovix Corp. WTS 01.10.26": "US2935941318",
    "Gamestop Corp. WTS 30.10.26": "US36467W1172",
    "GLOBALSTAR INC. O.N.": "US3789735079",
    "HONEYWELL AEROSPACE INC.": "US43849R1059",
    "Magnum Ice Cream": "NL0015002MS2",
    "Netflix": "US64110L1061",
    "NVIDIA": "US67066G1040",
    "OHB": "DE000A41YFG5",
    "Orsted": "DK0060094928",
    "ORSTED A/S   -ANR-": "DK0064307839",
    "ORSTED A/S EM.09/25 DK 10": "DK0064307755",
    "ROCKET LAB CORP. O.N.": "US7731211089",
    "TKMS": "DE000TKMS001",
    "Unilever": "GB00BVZK7T90",
    "VERSANT MEDIA GRP A O.N.": "US9252831030",
    "Worldline": "FR0014015MS9",
}

# Overrides for SWAP events where the target ISIN differs from the spinoff case.
_swap_note_to_isin_overrides: dict[str, str] = {
    "Worldline": "FR0011981968",
}

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
        event_type: Optional[EventType] = None
        ts = event_dict["timestamp"]
        ts = ts[:-2] + ":" + ts[-2:]
        date: datetime = datetime.fromisoformat(ts)
        title: str = event_dict["title"]
        isin: Optional[str] = cls._parse_isin(event_dict)
        isin2: Optional[str] = None
        shares: Optional[float] = None
        shares2: Optional[float] = None
        value: Optional[float] = event_dict.get("amount", {}).get("value", None)
        fees: Optional[float] = None
        taxes: Optional[float] = None
        note: Optional[str] = None

        eventTypeStr = (event_dict.get("eventType") or "").upper()
        subtitle = event_dict["subtitle"]
        eventdesc = f"{title} {subtitle} ({event_dict['id']})"
        dump_dict = {"eventdesc": eventdesc, "id": event_dict["id"]}
        pref_locale = "de"
        ignoreEvent = False

        # Get sections and some special dicts from it
        (
            gesamt_dict,
            uebersicht_dict,
            shares_dict,
            shares_dict2,
            wertpapier_dict,
            wertpapier_dict2,
            quotation_dict,
            fees_dict,
            taxes_dict,
        ) = (None,) * 9
        sections = event_dict.get("details", {}).get("sections", [{}])
        transaction_dict = next(
            filter(lambda x: x.get("title") in ["Transaktion", "Geschäft", "Transaction"], sections), None
        )
        if transaction_dict:
            # old style event
            dump_dict["maintitle"] = transaction_dict["title"]
            data = transaction_dict.get("data", [{}])
            shares_dict = next(filter(lambda x: x["title"] in ["Aktien", "Anteile", "Shares"], data), None)
            fees_dict = next(filter(lambda x: x["title"] in ["Gebühr", "Fee"], data), None)
            taxes_dict = next(filter(lambda x: x["title"] in ["Steuer", "Steuern"], data), None)

        uebersicht_dict = next(
            filter(lambda x: x.get("title") in ["Überblick", "Übersicht", "Overview"], sections), None
        )
        if uebersicht_dict:
            # new style event
            for item in uebersicht_dict.get("data", []):
                ititle = item.get("title")
                if ititle == "Gesamt":
                    gesamt_dict = item
                elif ititle == "Gebühr" and not fees_dict:
                    fees_dict = item
                elif ititle in ["Steuer", "Steuern"] and not taxes_dict:
                    taxes_dict = item
                elif ititle in ["Vermögenswert", "Wertpapier", "Asset"] and not wertpapier_dict:
                    wertpapier_dict = item
                elif ititle in ["Vermögenswert", "Wertpapier", "Asset"] and wertpapier_dict and not wertpapier_dict2:
                    wertpapier_dict2 = item
                elif ititle in ["Aktien", "Aktien entfernt", "Aktien hinzugefügt", "Shares"] and not shares_dict:
                    shares_dict = item
                elif (
                    ititle in ["Aktien", "Aktien entfernt", "Aktien hinzugefügt", "Shares"]
                    and shares_dict
                    and not shares_dict2
                ):
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

        # Most Trade republic events have an EventType and can be directly mapped with it.
        event_type = tr_event_type_mapping.get(eventTypeStr, None)

        # We support some older eventType entries which might not exist any more in current TR data.
        # We could consider removing this if block some time in the future.
        if event_type is None:
            if eventTypeStr == "TIMELINE_LEGACY_MIGRATED_EVENTS":
                event_type = timeline_legacy_migrated_events_title_type_mapping.get(title)
                if event_type is None:
                    event_type = timeline_legacy_migrated_events_subtitle_type_mapping.get(subtitle)
                if event_type is None and subtitle != "Wertpapiertransfer":
                    for item in event_dict.get("details", {}).get("sections", []):
                        ititle = item.get("title", "")
                        if ititle.startswith("Du hast "):
                            if ititle.endswith(" erhalten") and "Angebot" not in ititle:
                                event_type = PPEventType.DEPOSIT
                                break
                            elif ititle.endswith(" gesendet"):
                                event_type = PPEventType.REMOVAL
                                break
            elif eventTypeStr == "SSP_CORPORATE_ACTION_INVOICE_SHARES":
                if subtitle in [
                    "Aktiendividende",
                    "Spin-off",
                    "Zwischenvertrieb von Wertpapieren",
                ]:
                    event_type = PPEventType.SPINOFF
                elif subtitle == "Bonusaktien":
                    event_type = PPEventType.SPLIT
                elif subtitle in [
                    "Reverse Split",
                    "Teilrückzahlung ohne Reduzierung des Poolfaktors",
                    "Zusammenschluss",
                ]:
                    event_type = PPEventType.SWAP
                elif subtitle == "Wertlos":
                    event_type = ConditionalEventType.TRADE_INVOICE
            elif eventTypeStr in ["SSP_CORPORATE_ACTION_INVOICE_CASH", "SSP_CORPORATE_ACTION_CASH"]:
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

        # Now try to deduct the event type from the title if we still don't have one
        if event_type is None and eventTypeStr not in events_known_ignored:
            event_type = title_event_type_mapping.get(title, None)

        # Now try to deduct the event type from the subtitle if we still don't have one
        if event_type is None and eventTypeStr not in events_known_ignored:
            event_type = subtitle_event_type_mapping.get(subtitle, None)

        # Handle "Wertpapiertransfer" which can be either TRANSFER_IN or TRANSFER_OUT
        if event_type is None and subtitle == "Wertpapiertransfer" and sections:
            for item in sections:
                ititle = item.get("title")
                if ititle is None:
                    continue
                if "Aktien erhalten" in ititle or "erhalten" in ititle:
                    event_type = PPEventType.TRANSFER_IN
                    break
                elif "Aktien gesendet" in ititle or "gesendet" in ititle:
                    event_type = PPEventType.TRANSFER_OUT
                    break

        # If still no event type, try to deduce it from the overview section
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
                            elif "erhalten" in ititle and "Angebot" not in ititle:
                                event_type = PPEventType.DEPOSIT
                elif ititle == "Event":
                    if item.get("detail", {}).get("text", "") == "Bonusaktien":
                        event_type = PPEventType.DIVIDEND

        # If still no event type, try to deduce it from the sections
        if event_type is None and sections:
            for item in sections:
                ititle = item.get("title")
                if ititle is None:
                    continue
                elif "Du hast" in ititle and "€" in ititle and "erhalten" in ititle and "Angebot" not in ititle:
                    event_type = PPEventType.DEPOSIT
                elif "Du hast" in ititle and "€" in ititle and "gesendet" in ititle:
                    event_type = PPEventType.REMOVAL

        # Some events can be TAX events sometimes
        if event_type is ConditionalEventType.PRIVATE_MARKETS_ORDER and subtitle == "Vorabpauschale":
            event_type = PPEventType.TAXES
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

        # Canceled Events should be ignored, even if they have an event type
        if event_type is not None:
            if event_dict.get("status", "").lower() == "canceled":
                event_type = None
                ignoreEvent = True
            elif sections:
                for section in sections:
                    if section.get("type") == "header":
                        header_status = section.get("data", {}).get("status", "").lower()
                        if header_status == "canceled":
                            event_type = None
                            ignoreEvent = True
                        break

        # Now print a warning if we still don't have an event type and the event is not known to be ignorable
        if (
            event_type is None
            and eventTypeStr not in events_known_ignored
            and title not in events_known_ignored_title
            and subtitle not in events_known_ignored_subtitle
            and not ignoreEvent
        ):
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

            if not ignoreEvent:
                get_event_logger().warning(f'Ignoring unknown event "{eventdesc}"')
                get_event_logger().debug("Unknown event %s: %s", eventdesc, json.dumps(event_dict, indent=4))

        # Return an empty Event object if we don't have an event type, as we can't parse the rest of the fields without it
        if event_type is None:
            return cls(event_type, date, title, isin, isin2, shares, shares2, value, fees, taxes, note)

        # parse shares
        if shares_dict:
            dump_dict["subtitle"] = shares_dict["title"]
            dump_dict["type"] = "shares"
            pref_locale = (
                "en"
                if (
                    event_type
                    in [
                        PPEventType.DIVIDEND,
                        ConditionalEventType.SAVEBACK,
                        PPEventType.SPINOFF,
                        PPEventType.TRANSFER_IN,
                        PPEventType.TRANSFER_OUT,
                    ]
                    or eventTypeStr
                    in [
                        "BENEFITS_SPARE_CHANGE_EXECUTION",
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
                and shares_dict["title"] in ["Aktien", "Aktien hinzugefügt", "Aktien entfernt", "Shares"]
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
        elif transaction_dict and quotation_dict:
            transaction = cls._parse_float_from_text_value(
                transaction_dict.get("detail", {}).get("text", ""), dump_dict
            )
            quotation = cls._parse_float_from_text_value(quotation_dict.get("detail", {}).get("text", ""), dump_dict)
            if transaction and quotation:
                shares = float(
                    (Decimal(transaction) / Decimal(quotation) * Decimal(100)).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                )
        elif (
            (
                event_type in [ConditionalEventType.SAVEBACK]
                or eventTypeStr in ["BENEFITS_SPARE_CHANGE_EXECUTION", "ACQUISITION_TRADE_PERK"]
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

        if (eventTypeStr == "ACQUISITION_TRADE_PERK" or title == "Aktien-Bonus") and shares is None:
            value = 0
            shares = 0

        if (event_type == PPEventType.SPINOFF or subtitle == "Wertlos") and value is None:
            value = 0

        if event_type in [PPEventType.SPLIT, PPEventType.SWAP, PPEventType.TRANSFER_IN] and value is None:
            value = 0

        if event_type in [PPEventType.SPINOFF, PPEventType.SWAP]:
            if wertpapier_dict2:
                note = wertpapier_dict2["detail"]["text"]
            elif wertpapier_dict:
                note = wertpapier_dict["detail"]["text"]

            if event_type == PPEventType.SPINOFF:
                isin2 = isin
                isin = _note_to_isin.get(note, isin2) if note else isin2
            elif event_type == PPEventType.SWAP:
                if note == "Honeywell International":
                    isin2 = isin
                    isin = "US4385161066"
                elif note == "MSCI World USD (Acc)" and isin == "LU1781541179":
                    isin2 = "IE000BI8OT95"
                else:
                    isin2 = (_swap_note_to_isin_overrides.get(note) or _note_to_isin.get(note, note)) if note else None

        # parse fees
        if fees_dict:
            dump_dict["subtitle"] = fees_dict["title"]
            dump_dict["type"] = "fees"
            fees = cls._parse_float_from_text_value(fees_dict.get("detail", {}).get("text", ""), dump_dict)

        # parse taxes
        if taxes_dict:
            dump_dict["subtitle"] = taxes_dict["title"]
            dump_dict["type"] = "taxes"
            taxes = cls._parse_float_from_text_value(taxes_dict.get("detail", {}).get("text", ""), dump_dict, "de")
            if taxes and taxes < 0:
                taxes = -taxes

        if event_type in [PPEventType.TRANSFER_IN, PPEventType.TRANSFER_OUT]:
            if transaction_dict:
                for item in transaction_dict.get("data", []):
                    if item.get("title") in ["Shares", "Aktien"]:
                        shares = cls._parse_float_from_text_value(item.get("detail", {}).get("text", ""), {}, "en")

            if shares is None and uebersicht_dict:
                for item in uebersicht_dict.get("data", []):
                    # "Aktien" for newer events, "Anteile" for older Wertpapiertransfer events
                    if item.get("title") in ["Aktien", "Shares", "Anteile"]:
                        shares = cls._parse_float_from_text_value(item.get("detail", {}).get("text", ""), {}, "en")
            value = 0  # Transfers have no monetary value

        if event_type in [PPEventType.DEPOSIT, PPEventType.REMOVAL]:
            if eventTypeStr is not None and eventTypeStr.startswith("CARD_"):
                note = eventTypeStr

            if uebersicht_dict:
                for item in uebersicht_dict.get("data", []):
                    if item.get("title") == "Kartenzahlung":
                        note = "card_successful_transaction"
                    elif item.get("title") == "Kartenerstattung":
                        note = "card_refund"

        if event_type == ConditionalEventType.PRIVATE_MARKETS_ORDER:
            if shares is None:
                if value is None:
                    shares = 0
                elif fees is not None:
                    shares = (abs(value) - abs(fees)) / 100
                else:
                    shares = abs(value) / 100
            subtitle_note = event_dict["subtitle"]
            if subtitle_note != "1 % Bonus" and isin == "LU3176111881":
                note = "EQT"
            elif subtitle_note != "1 % Bonus" and isin == "LU3170240538":
                note = "Apollo"
            else:
                note = subtitle_note

        if event_type == PPEventType.TAXES and subtitle == "Vorabpauschale":
            if isin == "LU3176111881":
                note = "EQT"
            elif isin == "LU3170240538":
                note = "Apollo"

        if event_type is PPEventType.SWAP and uebersicht_dict:
            foundentfernt = False
            for item in uebersicht_dict.get("data", []):
                ititle = item.get("title")
                if ititle == "Aktien entfernt":
                    foundentfernt = True
            if not foundentfernt:
                event_type = ConditionalEventType.TRADE_INVOICE
                isin2 = None
                if title == "WORLDLINE S.A. ANR":
                    title = "Worldline"
                    isin = "FR0011981968"
                    note = None

        if (
            subtitle == "Zusammenschluss"
            and title == "Deine Aktien waren von einer Kapitalmaßnahme betroffen"
            and wertpapier_dict
        ):
            title = wertpapier_dict["detail"]["text"]

        if (
            fees is None
            and event_type
            in [
                ConditionalEventType.PRIVATE_MARKETS_ORDER,
                ConditionalEventType.TRADE_INVOICE,
            ]
            and subtitle
            not in ["Wertlos", "Round up", "1 % Bonus", "Sparplan ausgeführt", "Aufruf von Zwischenpapieren"]
            and eventTypeStr not in ["BENEFITS_SPARE_CHANGE_EXECUTION"]
        ):
            get_event_logger().warning("Could not parse fees from %s", eventdesc)
            get_event_logger().debug("Failed to parse fees from %s", json.dumps(event_dict, indent=4))

        if (
            shares is None
            and event_type
            in [
                ConditionalEventType.PRIVATE_MARKETS_ORDER,
                ConditionalEventType.SAVEBACK,
                ConditionalEventType.TRADE_INVOICE,
                PPEventType.BUY,
                PPEventType.DIVIDEND,
                PPEventType.SELL,
                PPEventType.SPINOFF,
                PPEventType.SPLIT,
                PPEventType.SWAP,
                PPEventType.TRANSFER_IN,
                PPEventType.TRANSFER_OUT,
            ]
            and subtitle not in ["Aktienprämiendividende", "Bardividende korrigiert", "Dividende Wahlweise", "Tilgung"]
        ):
            get_event_logger().warning("Could not parse shares from %s", eventdesc)
            get_event_logger().debug("Failed to parse shares from: %s", json.dumps(event_dict, indent=4))

        return cls(event_type, date, title, isin, isin2, shares, shares2, value, fees, taxes, note)

    @staticmethod
    def _parse_isin(event_dict: Dict[Any, Any]) -> Optional[str]:
        """Parses the ISIN from a transfer or corporate-action event"""
        sections = event_dict.get("details", {}).get("sections", [{}])

        for section in sections:
            action = section.get("action", None)
            if action and action.get("type", {}) == "instrumentDetail":
                isin = action.get("payload")
                break
            if section.get("type", {}) == "header":
                isin = section.get("data", {}).get("icon")
                if isinstance(isin, dict):
                    isin = isin.get("asset", "")
                break
        else:
            isin = event_dict.get("icon", "")

        if not isin:
            return None

        isin = isin[isin.find("/") + 1 :]
        isin = isin.split("/", 1)[0]
        return isin if re.match(r"^[A-Z]{2}[A-Z0-9]{10}$", isin) else None

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
