from datetime import datetime 

i18n = {
    "card transaction": {
        "cs": 'Platba kartou',
        "de": 'Kartentransaktion',
        "en": 'Card Transaction',
        "es": 'Transacción con tarjeta',
        "fr": 'Transaction par carte',
        "it": 'Transazione con carta',
        "nl": 'Kaarttransactie',
        "pt": 'Transakcja kartą',
        "ru": '\u041e\u043f\u0435\u0440\u0430\u0446\u0438\u044f\u0020\u043f\u043e\u0020\u043a\u0430\u0440\u0442\u0435',
    },
    "card_successful_atm_withdrawal": {
        "cs": 'Výběr hotovosti',
        "de": 'Barabhebung',
        "en": 'ATM withdrawal',
        "es": 'Retiradas de efectivo',
        "fr": 'Retrait en espèces',
        "it": 'Prelievo di contanti',
        "nl": 'Geldopname',
        "pt": 'Levantamento de dinheiro',
        "ru": '\u0412\u044b\u0434\u0430\u0447\u0430\u0020\u043d\u0430\u043b\u0438\u0447\u043d\u044b\u0445',
    },
    "card_order_billed": {
        "cs": 'Poplatek za kartu',
        "de": 'Kartengebühr',
        "en": 'Card fee',
        "es": 'Transacción con tarjeta',
        "fr": 'Frais de carte',
        "it": 'Tassa sulla carta',
        "nl": 'Kosten kaart',
        "pt": 'Taxa do cartão',
        "ru": '\u041f\u043b\u0430\u0442\u0430\u0020\u0437\u0430\u0020\u043e\u0431\u0441\u043b\u0443\u0436\u0438\u0432\u0430\u043d\u0438\u0435\u0020\u043a\u0430\u0440\u0442\u044b',
    },
    "card_refund": {
        "cs": "Vrácení peněz na kartu",
        "de": "Kartenerstattung",
        "en": "Card refund",
        "es": "Reembolso de tarjeta",
        "fr": "Remboursement par carte",
        "it": "Rimborso sulla carta",
        "nl": "Terugbetaling op kaart",
        "pt": "Reembolso do cartão",
        "ru": "\u0412\u043e\u0437\u0432\u0440\u0430\u0442\u0020\u043d\u0430\u0020\u043a\u0430\u0440\u0442\u0443"
    },
    "decimal dot": {
        "cs": ',',
        "de": ',',
        "en": '.',
        "es": ',',
        "fr": ',',
        "it": ',',
        "nl": ',',
        "pt": ',',
        "ru": ',',
    }
}


tr_eventType_to_pp_type = {
    'CREDIT': 'DIVIDENDS',
    "ssp_corporate_action_invoice_cash": 'DIVIDENDS',
    'TRADE_INVOICE': 'TRADE_INVOICE',
    'SAVINGS_PLAN_EXECUTED': 'TRADE_INVOICE',
    'ORDER_EXECUTED': 'TRADE_INVOICE',
    "PAYMENT_INBOUND": 'DEPOSIT',
    "PAYMENT_INBOUND_SEPA_DIRECT_DEBIT": 'DEPOSIT',
    "PAYMENT_OUTBOUND": 'REMOVAL',
    "INTEREST_PAYOUT_CREATED": 'INTEREST',
    "card_successful_transaction": 'REMOVAL',
    "card_successful_atm_withdrawal": 'REMOVAL',
    "card_order_billed": 'REMOVAL',
    "card_refund": 'DEPOSIT'
}


class Event:
    def __init__(self, event_json):
        self.event = event_json
        self.shares = ''
        self.isin = ''
        
        self.pp_type = tr_eventType_to_pp_type.get(self.event["eventType"],'')
        self.body = self.event.get('body', '')
        self.process_event()

    @property
    def date(self):
        dateTime = datetime.fromisoformat(self.event['timestamp'][:19])
        return dateTime.strftime('%Y-%m-%d')

    @property
    def is_pp_relevant(self):
        return self.pp_type != ''
    
    @property
    def amount(self):
        return str(self.event['amount']['value'])

    @property
    def note(self):
        if self.event["eventType"].find('card_')== 0:
            return self.event["eventType"]
        else:
            return ''

    @property
    def title(self):
        return self.event['title']
        

    def determine_pp_type(self):
        if self.pp_type == "TRADE_INVOICE":
            if self.event['amount']['value'] < 0:
                self.pp_type = "BUY"
            else:
                self.pp_type = "SELL"
            

    def determine_shares(self):
        if self.pp_type == "TRADE_INVOICE":
            sections = self.event.get("details", {}).get("sections", [{}])
            for section in sections:
                if section.get("title") == "Transaktion":
                    self.shares = section.get("data", [{}])[0]['detail']['text'].replace(",", ".")

    def determine_isin(self):
        if self.pp_type in ("DIVIDENDS", "TRADE_INVOICE"):
            sections = self.event.get("details", {}).get("sections", [{}])
            self.isin = self.event.get("icon", '')
            self.isin = self.isin[self.isin.find('/') + 1:]
            self.isin = self.isin[:self.isin.find('/')]
            isin2 = self.isin
            for section in sections:
                action = section.get("action", None)
                if action and action.get("type", {}) == "instrumentDetail":
                    isin2 = section.get("action", {}).get("payload")
            if self.isin != isin2:
                self.isin = isin2
    
    def process_event(self):
        self.determine_shares()
        self.determine_isin()
        self.determine_pp_type()
