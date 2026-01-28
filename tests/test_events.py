import json

from pytr.event import ConditionalEventType, Event, PPEventType
from pytr.transactions import TransactionExporter


def test_events():
    test_data = [
        {
            "filename": "aktien_entfernt.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "ORSTED A/S   -ANR-",
            "isin": "DK0064307839",
            "shares": 0.285835,
            "value": 0,
            "transactions": [
                {
                    "Datum": "2025-10-28T15:46:46",
                    "Typ": "Verkauf",
                    "Wert": 0,
                    "Notiz": "ORSTED A/S   -ANR-",
                    "ISIN": "DK0064307839",
                    "Stück": 0.285835,
                }
            ],
        },
        {
            "filename": "aktien_entfernt_no_eventType.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "ORSTED A/S   -ANR-",
            "isin": "DK0064307839",
            "shares": 0.285835,
            "value": 0,
            "transactions": [
                {
                    "Datum": "2025-10-28T15:46:46",
                    "Typ": "Verkauf",
                    "Wert": 0,
                    "Notiz": "ORSTED A/S   -ANR-",
                    "ISIN": "DK0064307839",
                    "Stück": 0.285835,
                }
            ],
        },
        {
            "filename": "aktienbonus.json",
            "event_type": ConditionalEventType.SAVEBACK,
            "title": "Aktien-Bonus",
            "isin": "US2546871060",
            "shares": 0.105,
            "value": -10.03,
            "transactions": [
                {
                    "Datum": "2025-10-13T14:49:06",
                    "Typ": "Kauf",
                    "Wert": -10.03,
                    "Notiz": "Aktien-Bonus",
                    "ISIN": "US2546871060",
                    "Stück": 0.105,
                },
                {
                    "Datum": "2025-10-13T14:49:06",
                    "Typ": "Einlage",
                    "Wert": 10.03,
                    "Notiz": "Aktien-Bonus",
                },
            ],
        },
        {
            "filename": "aktienbonus_no_eventType.json",
            "event_type": ConditionalEventType.SAVEBACK,
            "title": "Aktien-Bonus",
            "isin": "US2546871060",
            "shares": 0.105,
            "value": -10.03,
            "transactions": [
                {
                    "Datum": "2025-10-13T14:49:06",
                    "Typ": "Kauf",
                    "Wert": -10.03,
                    "Notiz": "Aktien-Bonus",
                    "ISIN": "US2546871060",
                    "Stück": 0.105,
                },
                {
                    "Datum": "2025-10-13T14:49:06",
                    "Typ": "Einlage",
                    "Wert": 10.03,
                    "Notiz": "Aktien-Bonus",
                },
            ],
        },
        {
            "filename": "aktiendividende.json",
            "event_type": PPEventType.SPINOFF,
            "title": "Enovix",
            "isin": "US2935941078",
            "shares": 0.494370,
            "value": 0,
            "note": "Enovix Corp. WTS 01.10.26",
            "transactions": [
                {
                    "Datum": "2025-07-22T14:31:49",
                    "Typ": "Spinoff",
                    "Wert": 0,
                    "Notiz": "Enovix Corp. WTS 01.10.26",
                    "ISIN": "US2935941318",
                    "Stück": 0.494370,
                    "ISIN2": "US2935941078",
                }
            ],
        },
        {
            "filename": "aktiendividende_no_eventType.json",
            "event_type": PPEventType.SPINOFF,
            "title": "Enovix",
            "isin": "US2935941078",
            "shares": 0.494370,
            "value": 0,
            "note": "Enovix Corp. WTS 01.10.26",
            "transactions": [
                {
                    "Datum": "2025-07-22T14:31:49",
                    "Typ": "Spinoff",
                    "Wert": 0,
                    "Notiz": "Enovix Corp. WTS 01.10.26",
                    "ISIN": "US2935941318",
                    "Stück": 0.494370,
                    "ISIN2": "US2935941078",
                }
            ],
        },
        {
            "filename": "aktienpraemiendividende.json",
            "event_type": PPEventType.DIVIDEND,
            "title": "Glencore",
            "isin": "JE00B4T3BW64",
            "value": 3,
            "taxes": -1.15,
            "transactions": [
                {
                    "Datum": "2025-09-22T11:20:31",
                    "Typ": "Dividende",
                    "Wert": 3.0,
                    "Notiz": "Glencore",
                    "ISIN": "JE00B4T3BW64",
                    "Steuern": 1.15,
                }
            ],
        },
        {
            "filename": "aktienpraemiendividende_no_eventType.json",
            "event_type": PPEventType.DIVIDEND,
            "title": "Glencore",
            "isin": "JE00B4T3BW64",
            "value": 3,
            "taxes": -1.15,
            "transactions": [
                {
                    "Datum": "2025-09-22T11:20:31",
                    "Typ": "Dividende",
                    "Wert": 3.0,
                    "Notiz": "Glencore",
                    "ISIN": "JE00B4T3BW64",
                    "Steuern": 1.15,
                }
            ],
        },
        {
            "filename": "aktiensplit.json",
            "event_type": PPEventType.SPLIT,
            "title": "Chipotle Mexican Grill",
            "isin": "US1696561059",
            "shares": 49,
            "value": 0,
            "transactions": [
                {
                    "Datum": "2024-06-26T08:06:40",
                    "Typ": "Split",
                    "Wert": 0,
                    "Notiz": "Chipotle Mexican Grill",
                    "ISIN": "US1696561059",
                    "Stück": 49,
                }
            ],
        },
        {
            "filename": "aktiensplit_no_eventType.json",
            "event_type": PPEventType.SPLIT,
            "title": "Netflix",
            "isin": "US64110L1061",
            "shares": 2.743902,
            "value": 0,
            "transactions": [
                {
                    "Datum": "2025-11-17T06:07:56",
                    "Typ": "Split",
                    "Wert": 0,
                    "Notiz": "Netflix",
                    "ISIN": "US64110L1061",
                    "Stück": 2.743902,
                }
            ],
        },
        {
            "filename": "bardividende.json",
            "event_type": PPEventType.DIVIDEND,
            "title": "Comcast (A)",
            "isin": "US20030N1019",
            "shares": 10.640298,
            "value": 2.24,
            "taxes": -0.78,
            "transactions": [
                {
                    "Datum": "2025-10-23T14:19:56",
                    "Typ": "Dividende",
                    "Wert": 2.24,
                    "Notiz": "Comcast (A)",
                    "ISIN": "US20030N1019",
                    "Stück": 10.640298,
                    "Steuern": 0.78,
                }
            ],
        },
        {
            "filename": "bardividende_no_eventType.json",
            "event_type": PPEventType.DIVIDEND,
            "title": "Lowe's",
            "isin": "US5486611073",
            "shares": 1.189904,
            "value": 0.92,
            "taxes": -0.32,
            "transactions": [
                {
                    "Datum": "2025-11-05T18:31:19",
                    "Typ": "Dividende",
                    "Wert": 0.92,
                    "Notiz": "Lowe's",
                    "ISIN": "US5486611073",
                    "Stück": 1.189904,
                    "Steuern": 0.32,
                }
            ],
        },
        {
            "filename": "bardividende_korrigiert.json",
            "event_type": PPEventType.DIVIDEND,
            "title": "Medical Properties Trust",
            "isin": "US58463J3041",
            "shares": 40,
            "value": 4.01,
            "taxes": -1.53,
            "transactions": [
                {
                    "Datum": "2025-03-20T15:04:31",
                    "Typ": "Dividende",
                    "Wert": 4.01,
                    "Notiz": "Medical Properties Trust",
                    "ISIN": "US58463J3041",
                    "Stück": 40.0,
                    "Steuern": 1.53,
                }
            ],
        },
        {
            "filename": "bardividende_korrigiert_no_eventType.json",
            "event_type": PPEventType.DIVIDEND,
            "title": "Medical Properties Trust",
            "isin": "US58463J3041",
            "shares": 40,
            "value": 4.01,
            "taxes": -1.53,
            "transactions": [
                {
                    "Datum": "2025-03-20T15:04:31",
                    "Typ": "Dividende",
                    "Wert": 4.01,
                    "Notiz": "Medical Properties Trust",
                    "ISIN": "US58463J3041",
                    "Stück": 40.0,
                    "Steuern": 1.53,
                }
            ],
        },
        {
            "filename": "benefits_spare_change_execution.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "SuperDividend USD (Dist)",
            "isin": "IE00077FRP95",
            "shares": 0.383219,
            "value": -3.38,
            "transactions": [
                {
                    "Datum": "2024-10-02T15:05:40",
                    "Typ": "Kauf",
                    "Wert": -3.38,
                    "Notiz": "SuperDividend USD (Dist)",
                    "ISIN": "IE00077FRP95",
                    "Stück": 0.383219,
                }
            ],
        },
        {
            "filename": "benefits_spare_change_execution_no_eventType.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "SuperDividend USD (Dist)",
            "isin": "IE00077FRP95",
            "shares": 0.383219,
            "value": -3.38,
            "transactions": [
                {
                    "Datum": "2024-10-02T15:05:40",
                    "Typ": "Kauf",
                    "Wert": -3.38,
                    "Notiz": "SuperDividend USD (Dist)",
                    "ISIN": "IE00077FRP95",
                    "Stück": 0.383219,
                }
            ],
        },
        {
            "filename": "bonusaktien.json",
            "event_type": PPEventType.SPLIT,
            "title": "Eckert & Ziegler",
            "isin": "DE0005659700",
            "shares": 5.706536,
            "value": 0,
            "transactions": [
                {
                    "Datum": "2025-08-15T08:10:12",
                    "Typ": "Split",
                    "Wert": 0,
                    "Notiz": "Eckert & Ziegler",
                    "ISIN": "DE0005659700",
                    "Stück": 5.706536,
                }
            ],
        },
        {
            "filename": "bonusaktien_no_eventType.json",
            "event_type": PPEventType.SPLIT,
            "title": "Eckert & Ziegler",
            "isin": "DE0005659700",
            "shares": 5.706536,
            "value": 0,
            "transactions": [
                {
                    "Datum": "2025-08-15T08:10:12",
                    "Typ": "Split",
                    "Wert": 0,
                    "Notiz": "Eckert & Ziegler",
                    "ISIN": "DE0005659700",
                    "Stück": 5.706536,
                }
            ],
        },
        {
            "filename": "bonusaktien2.json",
            "event_type": PPEventType.TAXES,
            "title": "BYD",
            "isin": "CNE100000296",
            "value": -8.67,
            "taxes": -8.67,
            "transactions": [
                {
                    "Datum": "2025-08-15T14:53:09",
                    "Typ": "Steuern",
                    "Wert": -8.67,
                    "Notiz": "BYD",
                    "ISIN": "CNE100000296",
                    "Steuern": 8.67,
                }
            ],
        },
        {
            "filename": "bonusaktien2_no_eventType.json",
            "event_type": PPEventType.TAXES,
            "title": "BYD",
            "isin": "CNE100000296",
            "value": -8.67,
            "taxes": -8.67,
            "transactions": [
                {
                    "Datum": "2025-08-15T14:53:09",
                    "Typ": "Steuern",
                    "Wert": -8.67,
                    "Notiz": "BYD",
                    "ISIN": "CNE100000296",
                    "Steuern": 8.67,
                }
            ],
        },
        {
            "filename": "buy.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "Euro Stoxx 50 EUR (Dist)",
            "isin": "IE00B4K6B022",
            "shares": 60,
            "value": -3002.8,
            "fees": 1.0,
            "transactions": [
                {
                    "Datum": "2024-02-20T16:32:07",
                    "Typ": "Kauf",
                    "Wert": -3002.8,
                    "Notiz": "Euro Stoxx 50 EUR (Dist)",
                    "ISIN": "IE00B4K6B022",
                    "Stück": 60.0,
                    "Gebühren": -1.0,
                }
            ],
        },
        {
            "filename": "buy_no_eventType.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "Euro Stoxx 50 EUR (Dist)",
            "isin": "IE00B4K6B022",
            "shares": 60,
            "value": -3002.8,
            "fees": 1.0,
            "transactions": [
                {
                    "Datum": "2024-02-20T16:32:07",
                    "Typ": "Kauf",
                    "Wert": -3002.8,
                    "Notiz": "Euro Stoxx 50 EUR (Dist)",
                    "ISIN": "IE00B4K6B022",
                    "Stück": 60.0,
                    "Gebühren": -1.0,
                }
            ],
        },
        {
            "filename": "buy_new.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "NVIDIA",
            "isin": "US67066G1040",
            "shares": 0.685102,
            "value": -111,
            "fees": 1.0,
            "transactions": [
                {
                    "Datum": "2025-10-10T19:29:43",
                    "Typ": "Kauf",
                    "Wert": -111,
                    "Notiz": "NVIDIA",
                    "ISIN": "US67066G1040",
                    "Stück": 0.685102,
                    "Gebühren": -1.0,
                }
            ],
        },
        {
            "filename": "buy_new_no_eventType.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "NVIDIA",
            "isin": "US67066G1040",
            "shares": 0.685102,
            "value": -111,
            "fees": 1.0,
            "transactions": [
                {
                    "Datum": "2025-10-10T19:29:43",
                    "Typ": "Kauf",
                    "Wert": -111,
                    "Notiz": "NVIDIA",
                    "ISIN": "US67066G1040",
                    "Stück": 0.685102,
                    "Gebühren": -1.0,
                }
            ],
        },
        {
            "filename": "buy_new2.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "Rocket Lab Corp. Registered Shares DL-,0001",
            "isin": "US7731211089",
            "shares": 2,
            "value": -75.6,
            "fees": 1.0,
            "transactions": [
                {
                    "Datum": "2025-08-01T08:28:01",
                    "Typ": "Kauf",
                    "Wert": -75.6,
                    "Notiz": "Rocket Lab Corp. Registered Shares DL-,0001",
                    "ISIN": "US7731211089",
                    "Stück": 2,
                    "Gebühren": -1.0,
                }
            ],
        },
        {
            "filename": "buy_new2_no_eventType.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "Rocket Lab Corp. Registered Shares DL-,0001",
            "isin": "US7731211089",
            "shares": 2,
            "value": -75.6,
            "fees": 1.0,
            "transactions": [
                {
                    "Datum": "2025-08-01T08:28:01",
                    "Typ": "Kauf",
                    "Wert": -75.6,
                    "Notiz": "Rocket Lab Corp. Registered Shares DL-,0001",
                    "ISIN": "US7731211089",
                    "Stück": 2,
                    "Gebühren": -1.0,
                }
            ],
        },
        {
            "filename": "card_refund.json",
            "event_type": PPEventType.DEPOSIT,
            "title": "Decathlon",
            "value": 24.99,
            "note": "card_refund",
            "transactions": [
                {
                    "Datum": "2025-08-17T07:23:44",
                    "Typ": "Einlage",
                    "Wert": 24.99,
                    "Notiz": "Kartenerstattung - Decathlon",
                }
            ],
        },
        {
            "filename": "card_refund_no_eventType.json",
            "event_type": PPEventType.DEPOSIT,
            "title": "Decathlon",
            "value": 24.99,
            "note": "card_refund",
            "transactions": [
                {
                    "Datum": "2025-08-17T07:23:44",
                    "Typ": "Einlage",
                    "Wert": 24.99,
                    "Notiz": "Kartenerstattung - Decathlon",
                }
            ],
        },
        {
            "filename": "deposit.json",
            "event_type": PPEventType.DEPOSIT,
            "title": "My Name",
            "value": 200,
            "transactions": [
                {
                    "Datum": "2024-06-03T17:07:26",
                    "Typ": "Einlage",
                    "Wert": 200.0,
                    "Notiz": "My Name",
                }
            ],
        },
        {
            "filename": "deposit_no_eventType.json",
            "event_type": PPEventType.DEPOSIT,
            "title": "My Name",
            "value": 200,
            "transactions": [
                {
                    "Datum": "2024-06-03T17:07:26",
                    "Typ": "Einlage",
                    "Wert": 200.0,
                    "Notiz": "My Name",
                }
            ],
        },
        {
            "filename": "dividende_old.json",
            "event_type": PPEventType.DIVIDEND,
            "title": "MSCI World USD (Dist)",
            "isin": "LU0392494562",
            "shares": 32,
            "value": 30.21,
            "taxes": 6.83,
            "transactions": [
                {
                    "Datum": "2024-12-31T23:59:59",
                    "Typ": "Dividende",
                    "Wert": 30.21,
                    "Notiz": "MSCI World USD (Dist)",
                    "ISIN": "LU0392494562",
                    "Stück": 32.0,
                    "Steuern": -6.83,
                }
            ],
        },
        {
            "filename": "dividende_wahlweise.json",
            "event_type": PPEventType.DIVIDEND,
            "title": "National Grid",
            "isin": "GB00BDR05C01",
            "value": 3.37,
            "taxes": -1.28,
            "transactions": [
                {
                    "Datum": "2024-07-19T13:28:04",
                    "Typ": "Dividende",
                    "Wert": 3.37,
                    "Notiz": "National Grid",
                    "ISIN": "GB00BDR05C01",
                    "Steuern": 1.28,
                }
            ],
        },
        {
            "filename": "dividende_wahlweise_no_eventType.json",
            "event_type": PPEventType.DIVIDEND,
            "title": "National Grid",
            "isin": "GB00BDR05C01",
            "value": 3.37,
            "taxes": -1.28,
            "transactions": [
                {
                    "Datum": "2024-07-19T13:28:04",
                    "Typ": "Dividende",
                    "Wert": 3.37,
                    "Notiz": "National Grid",
                    "ISIN": "GB00BDR05C01",
                    "Steuern": 1.28,
                }
            ],
        },
        {
            "filename": "incoming_transfer.json",
            "event_type": PPEventType.DEPOSIT,
            "title": "Klaus Mustermann",
            "value": 88.04,
            "transactions": [
                {
                    "Datum": "2024-09-02T17:49:12",
                    "Typ": "Einlage",
                    "Wert": 88.04,
                    "Notiz": "Klaus Mustermann",
                }
            ],
        },
        {
            "filename": "incoming_transfer_no_eventType.json",
            "event_type": PPEventType.DEPOSIT,
            "title": "Klaus Mustermann",
            "value": 88.04,
            "transactions": [
                {
                    "Datum": "2024-09-02T17:49:12",
                    "Typ": "Einlage",
                    "Wert": 88.04,
                    "Notiz": "Klaus Mustermann",
                }
            ],
        },
        {
            "filename": "incoming_transfer_delegation.json",
            "event_type": PPEventType.DEPOSIT,
            "title": "Vorname Nachname",
            "value": 3000.0,
            "transactions": [
                {
                    "Datum": "2024-09-10T13:18:31",
                    "Typ": "Einlage",
                    "Wert": 3000.0,
                    "Notiz": "Vorname Nachname",
                }
            ],
        },
        {
            "filename": "incoming_transfer_delegation_no_eventType.json",
            "event_type": PPEventType.DEPOSIT,
            "title": "Vorname Nachname",
            "value": 3000.0,
            "transactions": [
                {
                    "Datum": "2024-09-10T13:18:31",
                    "Typ": "Einlage",
                    "Wert": 3000.0,
                    "Notiz": "Vorname Nachname",
                }
            ],
        },
        {
            "filename": "junior_p2p_transfer.json",
            "event_type": PPEventType.REMOVAL,
            "title": "Maria Mueller",
            "value": -50,
            "transactions": [
                {
                    "Datum": "2025-09-17T19:35:32",
                    "Typ": "Entnahme",
                    "Wert": -50.0,
                    "Notiz": "Maria Mueller",
                }
            ],
        },
        {
            "filename": "junior_p2p_transfer_no_eventType.json",
            "event_type": PPEventType.REMOVAL,
            "title": "Maria Mueller",
            "value": -50,
            "transactions": [
                {
                    "Datum": "2025-09-17T19:35:32",
                    "Typ": "Entnahme",
                    "Wert": -50.0,
                    "Notiz": "Maria Mueller",
                }
            ],
        },
        {
            "filename": "kartenzahlung.json",
            "event_type": PPEventType.REMOVAL,
            "title": "Coop Pronto",
            "value": -12.16,
            "note": "card_successful_transaction",
            "transactions": [
                {
                    "Datum": "2025-10-21T17:30:01",
                    "Typ": "Entnahme",
                    "Wert": -12.16,
                    "Notiz": "Kartentransaktion - Coop Pronto",
                }
            ],
        },
        {
            "filename": "kartenzahlung_no_eventType.json",
            "event_type": PPEventType.REMOVAL,
            "title": "Baecker",
            "value": -2,
            "note": "card_successful_transaction",
            "transactions": [
                {
                    "Datum": "2025-11-05T11:00:07",
                    "Typ": "Entnahme",
                    "Wert": -2.0,
                    "Notiz": "Kartentransaktion - Baecker",
                }
            ],
        },
        {
            "filename": "legacy_verkauforder_neu_abgerechnet.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "Marie Brizard Wine and Spirits",
            "isin": "FR0000060873",
            "shares": 27,
            "value": 91.34,
            "fees": 1,
            "transactions": [
                {
                    "Datum": "2025-02-21T11:14:54",
                    "Typ": "Verkauf",
                    "Wert": 91.34,
                    "Notiz": "Marie Brizard Wine and Spirits",
                    "ISIN": "FR0000060873",
                    "Stück": 27.0,
                    "Gebühren": -1.0,
                }
            ],
        },
        {
            "filename": "legacy_verkauforder_neu_abgerechnet_no_eventType.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "Marie Brizard Wine and Spirits",
            "isin": "FR0000060873",
            "shares": 27,
            "value": 91.34,
            "fees": 1,
            "transactions": [
                {
                    "Datum": "2025-02-21T11:14:54",
                    "Typ": "Verkauf",
                    "Wert": 91.34,
                    "Notiz": "Marie Brizard Wine and Spirits",
                    "ISIN": "FR0000060873",
                    "Stück": 27.0,
                    "Gebühren": -1.0,
                }
            ],
        },
        {
            "filename": "legacy_zinsen.json",
            "event_type": PPEventType.INTEREST,
            "title": "Zinsen",
            "value": 11.76,
            "taxes": 4.51,
            "transactions": [
                {
                    "Datum": "2024-09-01T16:39:48",
                    "Typ": "Zinsen",
                    "Wert": 11.76,
                    "Notiz": "Zinsen",
                    "Steuern": -4.51,
                }
            ],
        },
        {
            "filename": "legacy_zinsen_no_eventType.json",
            "event_type": PPEventType.INTEREST,
            "title": "Zinsen",
            "value": 11.76,
            "taxes": 4.51,
            "transactions": [
                {
                    "Datum": "2024-09-01T16:39:48",
                    "Typ": "Zinsen",
                    "Wert": 11.76,
                    "Notiz": "Zinsen",
                    "Steuern": -4.51,
                }
            ],
        },
        {
            "filename": "limit-sell-order.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "D-Wave Quantum",
            "isin": "US26740W1099",
            "shares": 11,
            "value": 114.91,
            "fees": 1,
            "taxes": 17.36,
            "transactions": [
                {
                    "Datum": "2025-05-20T08:03:45",
                    "Typ": "Verkauf",
                    "Wert": 114.91,
                    "Notiz": "D-Wave Quantum",
                    "ISIN": "US26740W1099",
                    "Stück": 11.0,
                    "Gebühren": -1.0,
                    "Steuern": -17.36,
                }
            ],
        },
        {
            "filename": "limit-sell-order_no_eventType.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "Teva Pharmaceutical Industries (ADR)",
            "isin": "US8816242098",
            "shares": 8,
            "value": 139.74,
            "fees": 1,
            "taxes": 7.66,
            "transactions": [
                {
                    "Datum": "2025-11-05T12:03:19",
                    "Typ": "Verkauf",
                    "Wert": 139.74,
                    "Notiz": "Teva Pharmaceutical Industries (ADR)",
                    "ISIN": "US8816242098",
                    "Stück": 8.0,
                    "Gebühren": -1.0,
                    "Steuern": -7.66,
                }
            ],
        },
        {
            "filename": "limit-sell-order_old.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "Daimler Truck Holding",
            "isin": "DE000DTR0CK8",
            "shares": 3,
            "value": 119.37,
            "fees": 1,
            "taxes": 0.14,
            "transactions": [
                {
                    "Datum": "2025-05-14T07:01:32",
                    "Typ": "Verkauf",
                    "Wert": 119.37,
                    "Notiz": "Daimler Truck Holding",
                    "ISIN": "DE000DTR0CK8",
                    "Stück": 3.0,
                    "Gebühren": -1.0,
                    "Steuern": -0.14,
                }
            ],
        },
        {
            "filename": "limit-sell-order_old_no_eventType.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "Daimler Truck Holding",
            "isin": "DE000DTR0CK8",
            "shares": 3,
            "value": 119.37,
            "fees": 1,
            "taxes": 0.14,
            "transactions": [
                {
                    "Datum": "2025-05-14T07:01:32",
                    "Typ": "Verkauf",
                    "Wert": 119.37,
                    "Notiz": "Daimler Truck Holding",
                    "ISIN": "DE000DTR0CK8",
                    "Stück": 3.0,
                    "Gebühren": -1.0,
                    "Steuern": -0.14,
                }
            ],
        },
        {
            "filename": "outgoing_transfer.json",
            "event_type": PPEventType.REMOVAL,
            "title": "Hans Mustermann",
            "value": -50.3,
            "transactions": [
                {
                    "Datum": "2024-07-21T09:35:47",
                    "Typ": "Entnahme",
                    "Wert": -50.3,
                    "Notiz": "Hans Mustermann",
                }
            ],
        },
        {
            "filename": "outgoing_transfer_no_eventType.json",
            "event_type": PPEventType.REMOVAL,
            "title": "Hans Mustermann",
            "value": -50.3,
            "transactions": [
                {
                    "Datum": "2024-07-21T09:35:47",
                    "Typ": "Entnahme",
                    "Wert": -50.3,
                    "Notiz": "Hans Mustermann",
                }
            ],
        },
        {
            "filename": "outgoing_transfer_delegation.json",
            "event_type": PPEventType.REMOVAL,
            "title": "Nina",
            "value": -67,
            "transactions": [
                {
                    "Datum": "2025-08-18T12:16:06",
                    "Typ": "Entnahme",
                    "Wert": -67.0,
                    "Notiz": "Nina",
                }
            ],
        },
        {
            "filename": "outgoing_transfer_delegation_no_eventType.json",
            "event_type": PPEventType.REMOVAL,
            "title": "Nina",
            "value": -67,
            "transactions": [
                {
                    "Datum": "2025-08-18T12:16:06",
                    "Typ": "Entnahme",
                    "Wert": -67.0,
                    "Notiz": "Nina",
                }
            ],
        },
        {
            "filename": "outgoing_transfer_legacy.json",
            "event_type": PPEventType.REMOVAL,
            "title": "My Name",
            "value": -750,
            "transactions": [
                {
                    "Datum": "2025-04-11T06:44:43",
                    "Typ": "Entnahme",
                    "Wert": -750.0,
                    "Notiz": "My Name",
                }
            ],
        },
        {
            "filename": "outgoing_transfer_legacy_no_eventType.json",
            "event_type": PPEventType.REMOVAL,
            "title": "My Name",
            "value": -750,
            "transactions": [
                {
                    "Datum": "2025-04-11T06:44:43",
                    "Typ": "Entnahme",
                    "Wert": -750.0,
                    "Notiz": "My Name",
                }
            ],
        },
        {
            "filename": "payment_inbound_credit_card.json",
            "event_type": PPEventType.DEPOSIT,
            "title": "Einzahlung",
            "value": 1000,
            "transactions": [
                {
                    "Datum": "2022-08-27T05:06:30",
                    "Typ": "Einlage",
                    "Wert": 1000.0,
                    "Notiz": "Einzahlung",
                }
            ],
        },
        {
            "filename": "payment_inbound_credit_card_no_eventType.json",
            "event_type": PPEventType.DEPOSIT,
            "title": "Einzahlung",
            "value": 1000,
            "transactions": [
                {
                    "Datum": "2022-08-27T05:06:30",
                    "Typ": "Einlage",
                    "Wert": 1000.0,
                    "Notiz": "Einzahlung",
                }
            ],
        },
        {
            "filename": "private_markets_order.json",
            "event_type": ConditionalEventType.PRIVATE_MARKETS_ORDER,
            "title": "Private Equity",
            "isin": "LU3176111881",
            "shares": 1,
            "value": -101,
            "fees": 1,
            "note": "Kauforder",
            "transactions": [
                {
                    "Datum": "2025-09-18T07:15:25",
                    "Typ": "Kauf",
                    "Wert": -101.0,
                    "Notiz": "EQT",
                    "ISIN": "LU3176111881",
                    "Stück": 1.0,
                    "Gebühren": -1.0,
                },
            ],
        },
        {
            "filename": "private_markets_order_no_eventType.json",
            "event_type": ConditionalEventType.PRIVATE_MARKETS_ORDER,
            "title": "Private Equity",
            "isin": "LU3176111881",
            "shares": 1,
            "value": -101,
            "fees": 1,
            "note": "Kauforder",
            "transactions": [
                {
                    "Datum": "2025-09-18T07:15:25",
                    "Typ": "Kauf",
                    "Wert": -101.0,
                    "Notiz": "EQT",
                    "ISIN": "LU3176111881",
                    "Stück": 1.0,
                    "Gebühren": -1.0,
                },
            ],
        },
        {
            "filename": "private_markets_order_bonus.json",
            "event_type": ConditionalEventType.PRIVATE_MARKETS_ORDER,
            "title": "Private Equity",
            "isin": "LU3176111881",
            "shares": 0.01,
            "value": -1,
            "note": "1 % Bonus",
            "transactions": [
                {
                    "Datum": "2025-09-18T07:15:25",
                    "Typ": "Kauf",
                    "Wert": -1.0,
                    "Notiz": "EQT",
                    "ISIN": "LU3176111881",
                    "Stück": 0.01,
                },
                {
                    "Datum": "2025-09-18T07:15:25",
                    "Typ": "Einlage",
                    "Wert": 1.0,
                    "Notiz": "EQT",
                },
            ],
        },
        {
            "filename": "private_markets_order_bonus_no_eventType.json",
            "event_type": ConditionalEventType.PRIVATE_MARKETS_ORDER,
            "title": "Private Equity",
            "isin": "LU3176111881",
            "shares": 0.01,
            "value": -1,
            "note": "1 % Bonus",
            "transactions": [
                {
                    "Datum": "2025-09-18T07:15:25",
                    "Typ": "Kauf",
                    "Wert": -1.0,
                    "Notiz": "EQT",
                    "ISIN": "LU3176111881",
                    "Stück": 0.01,
                },
                {
                    "Datum": "2025-09-18T07:15:25",
                    "Typ": "Einlage",
                    "Wert": 1.0,
                    "Notiz": "EQT",
                },
            ],
        },
        {
            "filename": "private_markets_trade.json",
            "event_type": ConditionalEventType.PRIVATE_MARKETS_ORDER,
            "title": "Private Equity",
            "isin": "LU3170240538",
            "shares": 1,
            "value": -101,
            "fees": 1,
            "note": "Kauforder",
            "transactions": [
                {
                    "Datum": "2025-09-18T07:14:56",
                    "Typ": "Kauf",
                    "Wert": -101.0,
                    "Notiz": "Apollo",
                    "ISIN": "LU3170240538",
                    "Stück": 1.0,
                    "Gebühren": -1.0,
                },
            ],
        },
        {
            "filename": "private_markets_trade_no_eventType.json",
            "event_type": ConditionalEventType.PRIVATE_MARKETS_ORDER,
            "title": "Private Equity",
            "isin": "LU3170240538",
            "shares": 1,
            "value": -101,
            "fees": 1,
            "note": "Kauforder",
            "transactions": [
                {
                    "Datum": "2025-09-18T07:14:56",
                    "Typ": "Kauf",
                    "Wert": -101.0,
                    "Notiz": "Apollo",
                    "ISIN": "LU3170240538",
                    "Stück": 1.0,
                    "Gebühren": -1.0,
                },
            ],
        },
        {
            "filename": "private_markets_trade_bonus.json",
            "event_type": ConditionalEventType.PRIVATE_MARKETS_ORDER,
            "isin": "LU3170240538",
            "title": "Private Equity",
            "shares": 0.01,
            "value": -1,
            "note": "1 % Bonus",
            "transactions": [
                {
                    "Datum": "2025-09-18T07:14:56",
                    "Typ": "Kauf",
                    "Wert": -1,
                    "Notiz": "Apollo",
                    "ISIN": "LU3170240538",
                    "Stück": 0.01,
                },
                {
                    "Datum": "2025-09-18T07:14:56",
                    "Typ": "Einlage",
                    "Wert": 1,
                    "Notiz": "Apollo",
                },
            ],
        },
        {
            "filename": "private_markets_trade_bonus_no_eventType.json",
            "event_type": ConditionalEventType.PRIVATE_MARKETS_ORDER,
            "isin": "LU3170240538",
            "title": "Private Equity",
            "shares": 0.01,
            "value": -1,
            "note": "1 % Bonus",
            "transactions": [
                {
                    "Datum": "2025-09-18T07:14:56",
                    "Typ": "Kauf",
                    "Wert": -1,
                    "Notiz": "Apollo",
                    "ISIN": "LU3170240538",
                    "Stück": 0.01,
                },
                {
                    "Datum": "2025-09-18T07:14:56",
                    "Typ": "Einlage",
                    "Wert": 1,
                    "Notiz": "Apollo",
                },
            ],
        },
        {
            "filename": "reverse_split.json",
            "event_type": PPEventType.SWAP,
            "title": "Globalstar",
            "isin": "US3789734080",
            "shares": 110.403067,
            "shares2": 7.360204,
            "value": 0,
            "note": "GLOBALSTAR INC. O.N.",
            "transactions": [
                {
                    "Datum": "2025-02-11T08:13:48",
                    "Typ": "Swap",
                    "Wert": 0,
                    "Notiz": "Globalstar",
                    "ISIN": "US3789734080",
                    "Stück": 110.403067,
                    "ISIN2": "US3789735079",
                    "Stück2": 7.360204,
                },
            ],
        },
        {
            "filename": "reverse_split_no_eventType.json",
            "event_type": PPEventType.SWAP,
            "title": "Globalstar",
            "isin": "US3789734080",
            "shares": 110.403067,
            "shares2": 7.360204,
            "value": 0,
            "note": "GLOBALSTAR INC. O.N.",
            "transactions": [
                {
                    "Datum": "2025-02-11T08:13:48",
                    "Typ": "Swap",
                    "Wert": 0,
                    "Notiz": "Globalstar",
                    "ISIN": "US3789734080",
                    "Stück": 110.403067,
                    "ISIN2": "US3789735079",
                    "Stück2": 7.360204,
                },
            ],
        },
        {
            "filename": "saveback.json",
            "event_type": ConditionalEventType.SAVEBACK,
            "title": "S&P 500 Information Tech USD (Acc)",
            "isin": "IE00B3WJKG14",
            "shares": 0.546348,
            "value": -15,
            "transactions": [
                {
                    "Datum": "2025-04-02T13:54:23",
                    "Typ": "Kauf",
                    "Wert": -15.0,
                    "Notiz": "S&P 500 Information Tech USD (Acc)",
                    "ISIN": "IE00B3WJKG14",
                    "Stück": 0.546348,
                },
                {
                    "Datum": "2025-04-02T13:54:23",
                    "Typ": "Einlage",
                    "Wert": 15.0,
                    "Notiz": "S&P 500 Information Tech USD (Acc)",
                },
            ],
        },
        {
            "filename": "saveback_no_eventType.json",
            "event_type": ConditionalEventType.SAVEBACK,
            "title": "Lockheed Martin",
            "isin": "US5398301094",
            "shares": 0.035252,
            "value": -15,
            "transactions": [
                {
                    "Datum": "2025-11-03T15:30:22",
                    "Typ": "Kauf",
                    "Wert": -15.0,
                    "Notiz": "Lockheed Martin",
                    "ISIN": "US5398301094",
                    "Stück": 0.035252,
                },
                {
                    "Datum": "2025-11-03T15:30:22",
                    "Typ": "Einlage",
                    "Wert": 15.0,
                    "Notiz": "Lockheed Martin",
                },
            ],
        },
        {
            "filename": "savingsplan.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "DroneShield",
            "isin": "AU000000DRO2",
            "shares": 6.921675,
            "value": -19,
            "transactions": [
                {
                    "Datum": "2025-10-23T08:26:13",
                    "Typ": "Kauf",
                    "Wert": -19.0,
                    "Notiz": "DroneShield",
                    "ISIN": "AU000000DRO2",
                    "Stück": 6.921675,
                }
            ],
        },
        {
            "filename": "savingsplan_no_eventType.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "TSMC (ADR)",
            "isin": "US8740391003",
            "shares": 0.037523,
            "value": -10,
            "transactions": [
                {
                    "Datum": "2025-11-03T15:58:11",
                    "Typ": "Kauf",
                    "Wert": -10.0,
                    "Notiz": "TSMC (ADR)",
                    "ISIN": "US8740391003",
                    "Stück": 0.037523,
                }
            ],
        },
        {
            "filename": "sell_stop.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "D-Wave Quantum",
            "isin": "US26740W1099",
            "shares": 17,
            "value": 94.76,
            "fees": 1,
            "taxes": 3.18,
            "transactions": [
                {
                    "Datum": "2025-03-14T07:03:14",
                    "Typ": "Verkauf",
                    "Wert": 94.76,
                    "Notiz": "D-Wave Quantum",
                    "ISIN": "US26740W1099",
                    "Gebühren": -1.0,
                    "Steuern": -3.18,
                    "Stück": 17.0,
                }
            ],
        },
        {
            "filename": "sell_stop_no_eventType.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "D-Wave Quantum",
            "isin": "US26740W1099",
            "shares": 17,
            "value": 94.76,
            "fees": 1,
            "taxes": 3.18,
            "transactions": [
                {
                    "Datum": "2025-03-14T07:03:14",
                    "Typ": "Verkauf",
                    "Wert": 94.76,
                    "Notiz": "D-Wave Quantum",
                    "ISIN": "US26740W1099",
                    "Gebühren": -1.0,
                    "Steuern": -3.18,
                    "Stück": 17.0,
                }
            ],
        },
        {
            "filename": "spinoff.json",
            "event_type": PPEventType.SPINOFF,
            "title": "ThyssenKrupp",
            "isin": "DE0007500001",
            "shares": 0.309986,
            "value": 0,
            "note": "TKMS",
            "transactions": [
                {
                    "Datum": "2025-10-20T11:25:29",
                    "Typ": "Spinoff",
                    "Wert": 0,
                    "Notiz": "TKMS",
                    "ISIN": "DE000TKMS001",
                    "Stück": 0.309986,
                    "ISIN2": "DE0007500001",
                }
            ],
        },
        {
            "filename": "spinoff_no_eventType.json",
            "event_type": PPEventType.SPINOFF,
            "title": "ThyssenKrupp",
            "isin": "DE0007500001",
            "shares": 0.309986,
            "value": 0,
            "note": "TKMS",
            "transactions": [
                {
                    "Datum": "2025-10-20T11:25:29",
                    "Typ": "Spinoff",
                    "Wert": 0,
                    "Notiz": "TKMS",
                    "ISIN": "DE000TKMS001",
                    "Stück": 0.309986,
                    "ISIN2": "DE0007500001",
                }
            ],
        },
        {
            "filename": "spinoff_only_taxes.json",
            "event_type": PPEventType.TAXES,
            "title": "Gamestop Corp. WTS 30.10.26",
            "isin": "US36467W1172",
            "value": -0.56,
            "taxes": -0.56,
            "transactions": [
                {
                    "Datum": "2025-12-19T15:24:37",
                    "Typ": "Steuern",
                    "Wert": -0.56,
                    "Notiz": "Gamestop Corp. WTS 30.10.26",
                    "ISIN": "US36467W1172",
                    "Steuern": 0.56,
                }
            ],
        },
        {
            "filename": "steuerkorrektur.json",
            "event_type": PPEventType.TAX_REFUND,
            "title": "Steuerkorrektur",
            "value": 2.87,
            "transactions": [
                {
                    "Datum": "2025-10-28T00:00:16",
                    "Typ": "Steuerrückerstattung",
                    "Wert": 2.87,
                    "Notiz": "Steuerkorrektur",
                }
            ],
        },
        {
            "filename": "steuerkorrektur_no_eventType.json",
            "event_type": PPEventType.TAX_REFUND,
            "title": "Steuerkorrektur",
            "value": 0.76,
            "transactions": [
                {
                    "Datum": "2025-11-04T23:31:58",
                    "Typ": "Steuerrückerstattung",
                    "Wert": 0.76,
                    "Notiz": "Steuerkorrektur",
                }
            ],
        },
        {
            "filename": "tausch_no_eventType.json",
            "title": "L'Oreal",
        },
        {
            "filename": "teilrueckzahlung.json",
            "event_type": PPEventType.SWAP,
            "title": "ORSTED A/S EM.09/25 DK 10",
            "isin": "DK0064307755",
            "shares": 17,
            "shares2": 17,
            "value": 0,
            "note": "Orsted",
            "transactions": [
                {
                    "Datum": "2025-10-23T14:46:49",
                    "Typ": "Swap",
                    "Wert": 0,
                    "Notiz": "ORSTED A/S EM.09/25 DK 10",
                    "ISIN": "DK0064307755",
                    "Stück": 17.0,
                    "ISIN2": "DK0060094928",
                    "Stück2": 17.0,
                },
            ],
        },
        {
            "filename": "teilrueckzahlung_no_eventType.json",
            "event_type": PPEventType.SWAP,
            "title": "ORSTED A/S EM.09/25 DK 10",
            "isin": "DK0064307755",
            "shares": 17,
            "shares2": 17,
            "value": 0,
            "note": "Orsted",
            "transactions": [
                {
                    "Datum": "2025-10-23T14:46:49",
                    "Typ": "Swap",
                    "Wert": 0,
                    "Notiz": "ORSTED A/S EM.09/25 DK 10",
                    "ISIN": "DK0064307755",
                    "Stück": 17.0,
                    "ISIN2": "DK0060094928",
                    "Stück2": 17.0,
                },
            ],
        },
        {
            "filename": "tilgung.json",
            "event_type": PPEventType.DIVIDEND,
            "title": "Long 1,2345 $",
            "isin": "DE000SX12345",
            "shares": 100,
            "value": 0.1,
            "transactions": [
                {
                    "Datum": "2025-01-10T10:00:00",
                    "Typ": "Dividende",
                    "Wert": 0.1,
                    "Notiz": "Long 1,2345 $",
                    "ISIN": "DE000SX12345",
                    "Stück": 100.0,
                }
            ],
        },
        {
            "filename": "tilgung_no_eventType.json",
            "event_type": PPEventType.DIVIDEND,
            "title": "Long 1,2345 $",
            "isin": "DE000SX12345",
            "shares": 100,
            "value": 0.1,
            "transactions": [
                {
                    "Datum": "2025-01-10T10:00:00",
                    "Typ": "Dividende",
                    "Wert": 0.1,
                    "Notiz": "Long 1,2345 $",
                    "ISIN": "DE000SX12345",
                    "Stück": 100.0,
                }
            ],
        },
        {
            "filename": "trade_perk.json",
            "event_type": ConditionalEventType.SAVEBACK,
            "title": "Aktien-Bonus",
            "isin": "US0378331005",
            "shares": 0.0487,
            "value": -10.03,
            "transactions": [
                {
                    "Datum": "2025-04-01T14:09:45",
                    "Typ": "Kauf",
                    "Wert": -10.03,
                    "Notiz": "Aktien-Bonus",
                    "ISIN": "US0378331005",
                    "Stück": 0.0487,
                },
                {
                    "Datum": "2025-04-01T14:09:45",
                    "Typ": "Einlage",
                    "Wert": 10.03,
                    "Notiz": "Aktien-Bonus",
                },
            ],
        },
        {
            "filename": "trade_perk_no_eventType.json",
            "event_type": ConditionalEventType.SAVEBACK,
            "title": "Aktien-Bonus",
            "isin": "US0378331005",
            "shares": 0.0487,
            "value": -10.03,
            "transactions": [
                {
                    "Datum": "2025-04-01T14:09:45",
                    "Typ": "Kauf",
                    "Wert": -10.03,
                    "Notiz": "Aktien-Bonus",
                    "ISIN": "US0378331005",
                    "Stück": 0.0487,
                },
                {
                    "Datum": "2025-04-01T14:09:45",
                    "Typ": "Einlage",
                    "Wert": 10.03,
                    "Notiz": "Aktien-Bonus",
                },
            ],
        },
        {
            "filename": "verkaufsorder.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "Tencent Holdings (ADR)",
            "isin": "US88032Q1094",
            "shares": 3.454506,
            "value": 200.93,
            "fees": 1,
            "taxes": 0.16,
            "transactions": [
                {
                    "Datum": "2025-05-12T18:38:36",
                    "Typ": "Verkauf",
                    "Wert": 200.93,
                    "Notiz": "Tencent Holdings (ADR)",
                    "ISIN": "US88032Q1094",
                    "Stück": 3.454506,
                    "Gebühren": -1.0,
                    "Steuern": -0.16,
                }
            ],
        },
        {
            "filename": "verkaufsorder_no_eventType.json",
            "event_type": ConditionalEventType.TRADE_INVOICE,
            "title": "Home Depot",
            "isin": "US4370761029",
            "shares": 0.305182,
            "value": 100,
            "fees": 1,
            "transactions": [
                {
                    "Datum": "2025-11-04T16:27:25",
                    "Typ": "Verkauf",
                    "Wert": 100.0,
                    "Notiz": "Home Depot",
                    "ISIN": "US4370761029",
                    "Stück": 0.305182,
                    "Gebühren": -1.0,
                }
            ],
        },
        {
            "filename": "vorabpauschale.json",
            "event_type": PPEventType.TAXES,
            "title": "MSCI China USD (Acc)",
            "isin": "IE00BJ5JPG56",
            "value": -0.19,
            "taxes": -0.19,
            "transactions": [
                {
                    "Datum": "2025-01-28T14:54:28",
                    "Typ": "Steuern",
                    "Wert": -0.19,
                    "Notiz": "MSCI China USD (Acc)",
                    "ISIN": "IE00BJ5JPG56",
                    "Steuern": 0.19,
                }
            ],
        },
        {
            "filename": "vorabpauschale_no_eventType.json",
            "event_type": PPEventType.TAXES,
            "title": "MSCI China USD (Acc)",
            "isin": "IE00BJ5JPG56",
            "value": -0.19,
            "taxes": -0.19,
            "transactions": [
                {
                    "Datum": "2025-01-28T14:54:28",
                    "Typ": "Steuern",
                    "Wert": -0.19,
                    "Notiz": "MSCI China USD (Acc)",
                    "ISIN": "IE00BJ5JPG56",
                    "Steuern": 0.19,
                }
            ],
        },
        {
            "filename": "zinsen.json",
            "event_type": PPEventType.INTEREST,
            "title": "Zinsen",
            "value": 4.87,
            "taxes": 1.87,
            "transactions": [
                {
                    "Datum": "2025-07-01T06:46:37",
                    "Typ": "Zinsen",
                    "Wert": 4.87,
                    "Notiz": "Zinsen",
                    "Steuern": -1.87,
                }
            ],
        },
        {
            "filename": "zinsen_no_eventType.json",
            "event_type": PPEventType.INTEREST,
            "title": "Zinsen",
            "value": 4.87,
            "taxes": 1.87,
            "transactions": [
                {
                    "Datum": "2025-07-01T06:46:37",
                    "Typ": "Zinsen",
                    "Wert": 4.87,
                    "Notiz": "Zinsen",
                    "Steuern": -1.87,
                }
            ],
        },
        {
            "filename": "zusammenschluss.json",
            "event_type": PPEventType.SWAP,
            "title": "Rocket Lab USA",
            "isin": "US7731221062",
            "shares": 5.943100,
            "shares2": 5.943100,
            "value": 0,
            "note": "ROCKET LAB CORP. O.N.",
            "transactions": [
                {
                    "Datum": "2025-05-29T13:04:58",
                    "Typ": "Swap",
                    "Wert": 0,
                    "Notiz": "Rocket Lab USA",
                    "ISIN": "US7731221062",
                    "Stück": 5.9431,
                    "ISIN2": "US7731211089",
                    "Stück2": 5.9431,
                },
            ],
        },
        {
            "filename": "zusammenschluss_no_eventType.json",
            "event_type": PPEventType.SWAP,
            "title": "Rocket Lab USA",
            "isin": "US7731221062",
            "shares": 5.943100,
            "shares2": 5.943100,
            "value": 0,
            "note": "ROCKET LAB CORP. O.N.",
            "transactions": [
                {
                    "Datum": "2025-05-29T13:04:58",
                    "Typ": "Swap",
                    "Wert": 0,
                    "Notiz": "Rocket Lab USA",
                    "ISIN": "US7731221062",
                    "Stück": 5.9431,
                    "ISIN2": "US7731211089",
                    "Stück2": 5.9431,
                },
            ],
        },
        {
            "filename": "zwischenpapiere.json",
            "event_type": PPEventType.SWAP,
            "title": "ORSTED A/S   -ANR-",
            "isin": "DK0064307839",
            "shares": 119,
            "shares2": 17,
            "value": -151.59,
            "note": "ORSTED A/S EM.09/25 DK 10",
            "transactions": [
                {
                    "Datum": "2025-10-21T07:39:39",
                    "Typ": "Swap",
                    "Wert": -151.59,
                    "ISIN": "DK0064307839",
                    "Notiz": "ORSTED A/S   -ANR-",
                    "Stück": 119.0,
                    "ISIN2": "DK0064307755",
                    "Stück2": 17.0,
                },
            ],
        },
        {
            "filename": "zwischenpapiere_no_eventType.json",
            "event_type": PPEventType.SWAP,
            "title": "ORSTED A/S   -ANR-",
            "isin": "DK0064307839",
            "shares": 119,
            "shares2": 17,
            "value": -151.59,
            "note": "ORSTED A/S EM.09/25 DK 10",
            "transactions": [
                {
                    "Datum": "2025-10-21T07:39:39",
                    "Typ": "Swap",
                    "Wert": -151.59,
                    "ISIN": "DK0064307839",
                    "Notiz": "ORSTED A/S   -ANR-",
                    "Stück": 119.0,
                    "ISIN2": "DK0064307755",
                    "Stück2": 17.0,
                },
            ],
        },
        {
            "filename": "zwischenvertrieb.json",
            "event_type": PPEventType.SPINOFF,
            "title": "Orsted",
            "isin": "DK0060094928",
            "shares": 119.285835,
            "value": 0,
            "note": "ORSTED A/S   -ANR-",
            "transactions": [
                {
                    "Datum": "2025-09-19T12:02:49",
                    "Typ": "Spinoff",
                    "Wert": 0,
                    "Notiz": "ORSTED A/S   -ANR-",
                    "ISIN": "DK0064307839",
                    "Stück": 119.285835,
                    "ISIN2": "DK0060094928",
                }
            ],
        },
        {
            "filename": "zwischenvertrieb_no_eventType.json",
            "event_type": PPEventType.SPINOFF,
            "title": "Orsted",
            "isin": "DK0060094928",
            "shares": 119.285835,
            "value": 0,
            "note": "ORSTED A/S   -ANR-",
            "transactions": [
                {
                    "Datum": "2025-09-19T12:02:49",
                    "Typ": "Spinoff",
                    "Wert": 0,
                    "Notiz": "ORSTED A/S   -ANR-",
                    "ISIN": "DK0064307839",
                    "Stück": 119.285835,
                    "ISIN2": "DK0060094928",
                }
            ],
        },
        {
            "filename": "transfer_out.json",
            "event_type": PPEventType.TRANSFER_OUT,
            "title": "Novo-Nordisk (B)",
            "isin": "DK0062498333",
            "shares": 42.0,
            "value": 0,
            "transactions": [
                {
                    "Datum": "2025-09-18T17:03:45",
                    "Typ": "Wertpapierübertrag (Ausgang)",
                    "Wert": 0,
                    "Notiz": "Novo-Nordisk (B)",
                    "ISIN": "DK0062498333",
                    "Stück": 42.0,
                }
            ],
        },
        {
            "filename": "transfer_in.json",
            "event_type": PPEventType.TRANSFER_IN,
            "title": "British American Tobacco",
            "isin": "GB0002875804",
            "shares": 1.0,
            "value": 0,
            "transactions": [
                {
                    "Datum": "2024-06-14T16:40:07",
                    "Typ": "Wertpapierübertrag (Eingang)",
                    "Wert": 0,
                    "Notiz": "British American Tobacco",
                    "ISIN": "GB0002875804",
                    "Stück": 1.0,
                }
            ],
        },
        {
            "filename": "wertpapiertransfer_in.json",
            "event_type": PPEventType.TRANSFER_IN,
            "title": "Metro",
            "isin": "DE000BFB0019",
            "shares": 76.0,
            "value": 0,
            "transactions": [
                {
                    "Datum": "2023-06-13T20:38:45",
                    "Typ": "Wertpapierübertrag (Eingang)",
                    "Wert": 0,
                    "Notiz": "Metro",
                    "ISIN": "DE000BFB0019",
                    "Stück": 76.0,
                }
            ],
        },
        {
            "filename": "wertpapiertransfer_out.json",
            "event_type": PPEventType.TRANSFER_OUT,
            "title": "Netflix",
            "isin": "US64110L1061",
            "shares": 4.0,
            "value": 0,
            "transactions": [
                {
                    "Datum": "2024-03-15T14:22:33",
                    "Typ": "Wertpapierübertrag (Ausgang)",
                    "Wert": 0,
                    "Notiz": "Netflix",
                    "ISIN": "US64110L1061",
                    "Stück": 4.0,
                }
            ],
        },
    ]

    # Create an instance of EventCsvFormatter
    formatter = TransactionExporter(lang="de")

    for row in test_data:
        # Load the sample JSON file
        with open("tests/" + row["filename"], "r", encoding="utf-8") as file:
            sample_data = json.load(file)

        # Parse the JSON data using the from_dict function
        event = Event.from_dict(sample_data)

        # Assert the expected values
        assert event.event_type == row.get("event_type")
        assert event.title == row.get("title")
        assert event.isin == row.get("isin")
        assert event.isin2 == row.get("isin2")
        assert event.shares == row.get("shares")
        assert event.shares2 == row.get("shares2")
        assert event.value == row.get("value")
        assert event.fees == row.get("fees")
        assert event.taxes == row.get("taxes")
        assert event.note == row.get("note")

        # Format the event to CSV
        transactions = list(formatter.from_event(event))

        # Assert that the output is not an empty string
        rowtransactions = row.get("transactions", [])
        for entry in rowtransactions:
            entry.setdefault("Datum", None)
            entry.setdefault("Typ", None)
            entry.setdefault("Wert", None)
            entry.setdefault("Notiz", None)
            entry.setdefault("ISIN", None)
            entry.setdefault("Stück", None)
            entry.setdefault("Gebühren", None)
            entry.setdefault("Steuern", None)
            entry.setdefault("ISIN2", None)
            entry.setdefault("Stück2", None)
        assert transactions == rowtransactions
