from datetime import datetime
import re


tr_eventType_to_pp_type = {
    "CREDIT": "DIVIDENDS",
    "ssp_corporate_action_invoice_cash": "DIVIDENDS",
    "TRADE_INVOICE": "TRADE_INVOICE",
    "SAVINGS_PLAN_EXECUTED": "TRADE_INVOICE",
    "SAVINGS_PLAN_INVOICE_CREATED": "TRADE_INVOICE",
    "ORDER_EXECUTED": "TRADE_INVOICE",
    "PAYMENT_INBOUND": "DEPOSIT",
    "PAYMENT_INBOUND_SEPA_DIRECT_DEBIT": "DEPOSIT",
    "INCOMING_TRANSFER": "DEPOSIT",
    "PAYMENT_INBOUND_GOOGLE_PAY": "DEPOSIT",
    "PAYMENT_OUTBOUND": "REMOVAL",
    "INTEREST_PAYOUT_CREATED": "INTEREST",
    "card_successful_transaction": "REMOVAL",
    "card_successful_atm_withdrawal": "REMOVAL",
    "card_order_billed": "REMOVAL",
    "card_refund": "DEPOSIT",
    "card_failed_transaction": "REMOVAL",
}


class Event:
    def __init__(self, event_json):
        self.event = event_json
        self.shares = ""
        self.isin = ""

        self.pp_type = tr_eventType_to_pp_type.get(self.event["eventType"], "")
        self.body = self.event.get("body", "")
        self.process_event()

    @property
    def date(self):
        dateTime = datetime.fromisoformat(self.event["timestamp"][:19])
        return dateTime.strftime("%Y-%m-%d")

    @property
    def is_pp_relevant(self):
        if self.event["eventType"] == "card_failed_transaction":
            if self.event["status"] == "CANCELED":
                return False
        return self.pp_type != ""

    @property
    def amount(self):
        return str(self.event["amount"]["value"])

    @property
    def note(self):
        if self.event["eventType"].find("card_") == 0:
            return self.event["eventType"]
        else:
            return ""

    @property
    def title(self):
        return self.event["title"]

    def determine_pp_type(self):
        if self.pp_type == "TRADE_INVOICE":
            if self.event["amount"]["value"] < 0:
                self.pp_type = "BUY"
            else:
                self.pp_type = "SELL"

    def determine_shares(self):
        if self.pp_type == "TRADE_INVOICE":
            sections = self.event.get("details", {}).get("sections", [{}])
            for section in sections:
                if section.get("title") == "Transaktion":
                    amount = section.get("data", [{}])[0]["detail"]["text"]
                    amount = re.sub("[^\,\d-]", "", amount)
                    self.shares = amount.replace(",", ".")

    def determine_isin(self):
        if self.pp_type in ("DIVIDENDS", "TRADE_INVOICE"):
            sections = self.event.get("details", {}).get("sections", [{}])
            self.isin = self.event.get("icon", "")
            self.isin = self.isin[self.isin.find("/") + 1 :]
            self.isin = self.isin[: self.isin.find("/")]
            isin2 = self.isin
            for section in sections:
                action = section.get("action", None)
                if action and action.get("type", {}) == "instrumentDetail":
                    isin2 = section.get("action", {}).get("payload")
                    break
            if self.isin != isin2:
                self.isin = isin2

    def process_event(self):
        self.determine_shares()
        self.determine_isin()
        self.determine_pp_type()
