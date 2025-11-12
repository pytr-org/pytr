import json

from pytr.event import ConditionalEventType, Event, PPEventType


def test_incoming_transfer():
    # Load the sample JSON file
    with open("tests/incoming_transfer.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DEPOSIT
    assert event.title == "Klaus Mustermann"
    assert event.value == 88.04


def test_incoming_transfer_no_eventType():
    # Load the sample JSON file
    with open("tests/incoming_transfer_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DEPOSIT
    assert event.title == "Klaus Mustermann"
    assert event.value == 88.04


def test_incoming_transfer_delegation():
    # Load the sample JSON file
    with open("tests/incoming_transfer_delegation.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DEPOSIT
    assert event.title == "Vorname Nachname"
    assert event.value == 3000.0


def test_incoming_transfer_delegation_no_eventType():
    # Load the sample JSON file
    with open("tests/incoming_transfer_delegation_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DEPOSIT
    assert event.title == "Vorname Nachname"
    assert event.value == 3000.0


def test_ueberweisung_no_eventType():
    # Load the sample JSON file
    with open("tests/ueberweisung_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DEPOSIT
    assert event.title == "Jens Mueller"
    assert event.value == 14.41


def test_deposit():
    # Load the sample JSON file
    with open("tests/deposit.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DEPOSIT
    assert event.value == 200


def test_card_refund():
    # Load the sample JSON file
    with open("tests/card_refund.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DEPOSIT
    assert event.title == "Decathlon"
    assert event.value == 24.99
    assert event.note == "card_refund"


def test_card_refund_no_eventType():
    # Load the sample JSON file
    with open("tests/card_refund_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DEPOSIT
    assert event.title == "Decathlon"
    assert event.value == 24.99
    assert event.note == "card_refund"


def test_saveback_new():
    # Load the sample JSON file
    with open("tests/saveback_new.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SAVEBACK
    assert event.isin == "IE00B3WJKG14"
    assert event.title == "S&P 500 Information Tech USD (Acc)"
    assert event.shares == 0.546348
    assert event.value == -15
    assert event.taxes is None


def test_saveback_no_eventType():
    # Load the sample JSON file
    with open("tests/saveback_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SAVEBACK
    assert event.isin == "US5398301094"
    assert event.title == "Lockheed Martin"
    assert event.shares == 0.035252
    assert event.value == -15
    assert event.taxes is None


def test_trade_perk():
    # Load the sample JSON file
    with open("tests/trade_perk.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SAVEBACK
    assert event.isin == "US0378331005"
    assert event.title == "Aktien-Bonus"
    assert event.shares == 0.0487
    assert event.value == -10.03
    assert event.taxes is None


def test_aktienbonus():
    # Load the sample JSON file
    with open("tests/aktienbonus.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SAVEBACK
    assert event.isin == "US2546871060"
    assert event.title == "Aktien-Bonus"
    assert event.shares == 0.105
    assert event.value == -10.03
    assert event.taxes is None


def test_aktienbonus_no_eventType():
    # Load the sample JSON file
    with open("tests/aktienbonus_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SAVEBACK
    assert event.isin == "US2546871060"
    assert event.title == "Aktien-Bonus"
    assert event.shares == 0.105
    assert event.value == -10.03
    assert event.taxes is None


def test_old_sell_event():
    # Load the sample JSON file
    with open("tests/sell_old.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "DE000DTR0CK8"
    assert event.isin2 is None
    assert event.title == "Daimler Truck Holding"
    assert event.shares == 3
    assert event.shares2 is None
    assert event.value == 119.37
    assert event.taxes == 0.14


def test_new_sell_event():
    # Load the sample JSON file
    with open("tests/sell_new.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "US26740W1099"
    assert event.isin2 is None
    assert event.title == "D-Wave Quantum"
    assert event.shares == 11
    assert event.shares2 is None
    assert event.value == 114.91
    assert event.taxes == 17.36


def test_sell_stop():
    # Load the sample JSON file
    with open("tests/sell_stop.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "US26740W1099"
    assert event.isin2 is None
    assert event.title == "D-Wave Quantum"
    assert event.shares == 17
    assert event.shares2 is None
    assert event.value == 94.76
    assert event.taxes == 3.18


def test_sell_stop_no_eventType():
    # Load the sample JSON file
    with open("tests/sell_stop_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "US26740W1099"
    assert event.isin2 is None
    assert event.title == "D-Wave Quantum"
    assert event.shares == 17
    assert event.shares2 is None
    assert event.value == 94.76
    assert event.taxes == 3.18


def test_legacy_verkauforder_neu_abgerechnet():
    # Load the sample JSON file
    with open("tests/legacy_verkauforder_neu_abgerechnet.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "FR0000060873"
    assert event.isin2 is None
    assert event.title == "Marie Brizard Wine and Spirits"
    assert event.shares == 27
    assert event.shares2 is None
    assert event.value == 91.34
    assert event.taxes is None


def test_legacy_verkauforder_neu_abgerechnet_no_eventType():
    # Load the sample JSON file
    with open("tests/legacy_verkauforder_neu_abgerechnet_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "FR0000060873"
    assert event.isin2 is None
    assert event.title == "Marie Brizard Wine and Spirits"
    assert event.shares == 27
    assert event.shares2 is None
    assert event.value == 91.34
    assert event.taxes is None


def test_buy_event():
    # Load the sample JSON file
    with open("tests/buy.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "IE00B4K6B022"
    assert event.isin2 is None
    assert event.title == "Euro Stoxx 50 EUR (Dist)"
    assert event.shares == 60
    assert event.shares2 is None
    assert event.value == -3002.8
    assert event.taxes is None


def test_new_buy_event():
    # Load the sample JSON file
    with open("tests/buy_new.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "US67066G1040"
    assert event.isin2 is None
    assert event.title == "NVIDIA"
    assert event.shares == 0.685102
    assert event.shares2 is None
    assert event.value == -111
    assert event.taxes is None


def test_new_buy_event2():
    # Load the sample JSON file
    with open("tests/buy_new2.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "US7731211089"
    assert event.isin2 is None
    assert event.title == "Rocket Lab Corp. Registered Shares DL-,0001"
    assert event.shares == 2
    assert event.shares2 is None
    assert event.value == -75.6
    assert event.taxes is None


def test_new_buy_event2_no_eventType():
    # Load the sample JSON file
    with open("tests/buy_new2_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "US7731211089"
    assert event.isin2 is None
    assert event.title == "Rocket Lab Corp. Registered Shares DL-,0001"
    assert event.shares == 2
    assert event.shares2 is None
    assert event.value == -75.6
    assert event.taxes is None


def test_new_buy_event_no_eventType():
    # Load the sample JSON file
    with open("tests/buy_new_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "US67066G1040"
    assert event.isin2 is None
    assert event.title == "NVIDIA"
    assert event.shares == 0.685102
    assert event.shares2 is None
    assert event.value == -111
    assert event.taxes is None


def test_benefits_spare_change_execution():
    # Load the sample JSON file
    with open("tests/benefits_spare_change_execution.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "IE00077FRP95"
    assert event.isin2 is None
    assert event.title == "SuperDividend USD (Dist)"
    assert event.shares == 0.383219
    assert event.shares2 is None
    assert event.value == -3.38
    assert event.taxes is None


def test_benefits_spare_change_execution_no_eventType():
    # Load the sample JSON file
    with open("tests/benefits_spare_change_execution_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "IE00077FRP95"
    assert event.isin2 is None
    assert event.title == "SuperDividend USD (Dist)"
    assert event.shares == 0.383219
    assert event.shares2 is None
    assert event.value == -3.38
    assert event.taxes is None


def test_private_markets_order():
    # Load the sample JSON file
    with open("tests/private_markets_order.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.PRIVATE_MARKETS_ORDER
    assert event.isin == "LU3176111881"
    assert event.isin2 is None
    assert event.title == "Private Equity"
    assert event.shares == 1
    assert event.shares2 is None
    assert event.value == -101
    assert event.taxes is None


def test_private_markets_order_bonus():
    # Load the sample JSON file
    with open("tests/private_markets_order_bonus.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.PRIVATE_MARKETS_ORDER
    assert event.isin == "LU3176111881"
    assert event.isin2 is None
    assert event.title == "Private Equity"
    assert event.shares == 0.01
    assert event.shares2 is None
    assert event.value == -1
    assert event.taxes is None


def test_private_markets_trade():
    # Load the sample JSON file
    with open("tests/private_markets_trade.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.PRIVATE_MARKETS_ORDER
    assert event.isin == "LU3170240538"
    assert event.isin2 is None
    assert event.title == "Private Equity"
    assert event.shares == 1
    assert event.shares2 is None
    assert event.value == -101
    assert event.taxes is None


def test_private_markets_trade_bonus():
    # Load the sample JSON file
    with open("tests/private_markets_trade_bonus.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.PRIVATE_MARKETS_ORDER
    assert event.isin == "LU3170240538"
    assert event.isin2 is None
    assert event.title == "Private Equity"
    assert event.shares == 0.01
    assert event.shares2 is None
    assert event.value == -1
    assert event.taxes is None
    assert event.note == "1 % Bonus"


def test_private_markets_trade_bonus_no_eventType():
    # Load the sample JSON file
    with open("tests/private_markets_trade_bonus_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.PRIVATE_MARKETS_ORDER
    assert event.isin == "LU3170240538"
    assert event.isin2 is None
    assert event.title == "Private Equity"
    assert event.shares == 0.01
    assert event.shares2 is None
    assert event.value == -1
    assert event.taxes is None
    assert event.note == "1 % Bonus"


def test_bardividende_no_eventType():
    # Load the sample JSON file
    with open("tests/bardividende_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.isin == "US5486611073"
    assert event.title == "Lowe's"
    assert event.shares == 1.189904
    assert event.value == 0.92
    assert event.taxes == -0.32


def test_dividende_no_eventType():
    # Load the sample JSON file
    with open("tests/dividende_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.isin == "LU0392494562"
    assert event.title == "MSCI World USD (Dist)"
    assert event.shares == 32
    assert event.value == 30.21
    assert event.taxes == 6.83


def test_dividend_sell_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_sell_dividend.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.isin == "DE000SX12345"
    assert event.shares == 100
    assert event.value == 0.1


def test_aktienpraemiendividende():
    # Load the sample JSON file
    with open("tests/aktienpraemiendividende.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.isin == "JE00B4T3BW64"
    assert event.title == "Glencore"
    assert event.shares is None
    assert event.value == 3
    assert event.taxes == -1.15


def test_aktienpraemiendividende_no_eventType():
    # Load the sample JSON file
    with open("tests/aktienpraemiendividende_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.isin == "JE00B4T3BW64"
    assert event.title == "Glencore"
    assert event.shares is None
    assert event.value == 3
    assert event.taxes == -1.15


def test_bardividende_korrigiert():
    # Load the sample JSON file
    with open("tests/bardividende_korrigiert.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.isin == "US58463J3041"
    assert event.title == "Medical Properties Trust"
    assert event.shares == 40
    assert event.value == 4.01
    assert event.taxes == -1.53


def test_bardividende_korrigiert_no_eventType():
    # Load the sample JSON file
    with open("tests/bardividende_korrigiert_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.isin == "US58463J3041"
    assert event.title == "Medical Properties Trust"
    assert event.shares == 40
    assert event.value == 4.01
    assert event.taxes == -1.53


def test_dividende_wahlweise():
    # Load the sample JSON file
    with open("tests/dividende_wahlweise.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.isin == "GB00BDR05C01"
    assert event.title == "National Grid"
    assert event.shares is None
    assert event.value == 3.37
    assert event.taxes == -1.28


def test_dividende_wahlweise_no_eventType():
    # Load the sample JSON file
    with open("tests/dividende_wahlweise_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.isin == "GB00BDR05C01"
    assert event.title == "National Grid"
    assert event.shares is None
    assert event.value == 3.37
    assert event.taxes == -1.28


def test_vorabpauschale():
    # Load the sample JSON file
    with open("tests/vorabpauschale.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.isin == "IE00BJ5JPG56"
    assert event.title == "MSCI China USD (Acc)"
    assert event.shares is None
    assert event.value == -0.19
    assert event.taxes == -0.19


def test_vorabpauschale_no_eventType():
    # Load the sample JSON file
    with open("tests/vorabpauschale_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.isin == "IE00BJ5JPG56"
    assert event.title == "MSCI China USD (Acc)"
    assert event.shares is None
    assert event.value == -0.19
    assert event.taxes == -0.19


def test_kartenzahlung_no_eventType():
    # Load the sample JSON file
    with open("tests/kartenzahlung_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.REMOVAL
    assert event.title == "Baecker"
    assert event.value == -2
    assert event.note == "card_successful_transaction"


def test_kartenzahlung_with_eventType():
    # Load the sample JSON file
    with open("tests/kartenzahlung_w_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.REMOVAL
    assert event.title == "Coop Pronto"
    assert event.value == -12.16
    assert event.note == "card_successful_transaction"


def test_new_removal_from_dict():
    # Load the sample JSON file
    with open("tests/sample_removal_new.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.REMOVAL
    assert event.value == -750


def test_outgoing_transfer():
    # Load the sample JSON file
    with open("tests/outgoing_transfer.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.REMOVAL
    assert event.title == "Hans Mustermann"
    assert event.value == -50.3


def test_outgoing_transfer_no_eventType():
    # Load the sample JSON file
    with open("tests/outgoing_transfer_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.REMOVAL
    assert event.title == "Hans Mustermann"
    assert event.value == -50.3


def test_outgoing_transfer_delegation():
    # Load the sample JSON file
    with open("tests/outgoing_transfer_delegation.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.REMOVAL
    assert event.title == "Nina"
    assert event.value == -67


def test_outgoing_transfer_delegation_no_eventType():
    # Load the sample JSON file
    with open("tests/outgoing_transfer_delegation_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.REMOVAL
    assert event.title == "Nina"
    assert event.value == -67


def test_junior_p2p_transfer():
    # Load the sample JSON file
    with open("tests/junior_p2p_transfer.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.REMOVAL
    assert event.title == "Maria Mueller"
    assert event.value == -50


def test_junior_p2p_transfer_no_eventType():
    # Load the sample JSON file
    with open("tests/junior_p2p_transfer_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.REMOVAL
    assert event.title == "Maria Mueller"
    assert event.value == -50


def test_steuerkorrektur_no_eventType():
    # Load the sample JSON file
    with open("tests/steuerkorrektur_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.TAX_REFUND
    assert event.title == "Steuerkorrektur"
    assert event.value == 0.76


def test_zinsen():
    # Load the sample JSON file
    with open("tests/zinsen.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.INTEREST
    assert event.title == "Zinsen"
    assert event.value == 4.87
    assert event.taxes == 1.87


def test_zinsen_no_eventType():
    # Load the sample JSON file
    with open("tests/zinsen_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.INTEREST
    assert event.title == "Zinsen"
    assert event.value == 4.87
    assert event.taxes == 1.87


def test_legacy_zinsen():
    # Load the sample JSON file
    with open("tests/legacy_zinsen.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.INTEREST
    assert event.title == "Zinsen"
    assert event.value == 11.76
    assert event.taxes == 4.51


def test_legacy_zinsen_no_eventType():
    # Load the sample JSON file
    with open("tests/legacy_zinsen_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.INTEREST
    assert event.title == "Zinsen"
    assert event.value == 11.76
    assert event.taxes == 4.51


def test_tausch_no_eventType():
    # Load the sample JSON file
    with open("tests/tausch_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type is None


def test_limit_sell_order_no_eventType():
    # Load the sample JSON file
    with open("tests/limit-sell-order_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "US8816242098"
    assert event.title == "Teva Pharmaceutical Industries (ADR)"
    assert event.shares == 8
    assert event.value == 139.74
    assert event.taxes == 7.66


def test_verkaufsorder_no_eventType():
    # Load the sample JSON file
    with open("tests/verkaufsorder_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "US4370761029"
    assert event.title == "Home Depot"
    assert event.shares == 0.305182
    assert event.value == 100
    assert event.taxes is None


def test_savingsplan_no_eventType():
    # Load the sample JSON file
    with open("tests/savingsplan_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "US8740391003"
    assert event.title == "TSMC (ADR)"
    assert event.shares == 0.037523
    assert event.value == -10
    assert event.taxes is None


def test_aktiensplit():
    # Load the sample JSON file
    with open("tests/aktiensplit.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "US1696561059"
    assert event.isin2 == "Chipotle"
    assert event.title == "Chipotle Mexican Grill"
    assert event.shares == 49
    assert event.shares2 is None
    assert event.value == 0
    assert event.taxes is None


def test_aktiensplit_no_eventType():
    # Load the sample JSON file
    with open("tests/aktiensplit_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "US64110L1061"
    assert event.isin2 == "Netflix"
    assert event.title == "Netflix"
    assert event.shares == 2.743902
    assert event.shares2 is None
    assert event.value == 0
    assert event.taxes is None


def test_bonusaktien():
    # Load the sample JSON file
    with open("tests/bonusaktien.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "DE0005659700"
    assert event.isin2 == "Eckert & Ziegler"
    assert event.title == "Eckert & Ziegler"
    assert event.shares == 5.706536
    assert event.shares2 is None
    assert event.value == 0
    assert event.taxes is None


def test_bonusaktien_no_eventType():
    # Load the sample JSON file
    with open("tests/bonusaktien_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "DE0005659700"
    assert event.isin2 == "Eckert & Ziegler"
    assert event.title == "Eckert & Ziegler"
    assert event.shares == 5.706536
    assert event.shares2 is None
    assert event.value == 0
    assert event.taxes is None


def test_bonusaktien2():
    # Load the sample JSON file
    with open("tests/bonusaktien2.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.isin == "CNE100000296"
    assert event.isin2 == "BYD"
    assert event.title == "BYD"
    assert event.shares is None
    assert event.shares2 is None
    assert event.value == -8.67
    assert event.taxes == -8.67


def test_bonusaktien2_no_eventType():
    # Load the sample JSON file
    with open("tests/bonusaktien2_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.isin == "CNE100000296"
    assert event.isin2 == "BYD"
    assert event.title == "BYD"
    assert event.shares is None
    assert event.shares2 is None
    assert event.value == -8.67
    assert event.taxes == -8.67


def test_aktien_entfernt():
    # Load the sample JSON file
    with open("tests/aktien_entfernt.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "DK0064307839"
    assert event.isin2 == "ORSTED A/S   -ANR-"
    assert event.title == "ORSTED A/S   -ANR-"
    assert event.shares == 0.285835
    assert event.shares2 is None
    assert event.value == 0
    assert event.taxes is None


def test_aktien_entfernt_no_eventType():
    # Load the sample JSON file
    with open("tests/aktien_entfernt_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "DK0064307839"
    assert event.isin2 == "ORSTED A/S   -ANR-"
    assert event.title == "ORSTED A/S   -ANR-"
    assert event.shares == 0.285835
    assert event.shares2 is None
    assert event.value == 0
    assert event.taxes is None


def test_teilrueckzahlung():
    # Load the sample JSON file
    with open("tests/teilrueckzahlung.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "DK0064307755"
    assert event.isin2 == "Orsted"
    assert event.title == "ORSTED A/S EM.09/25 DK 10"
    assert event.shares == 17
    assert event.shares2 == 17
    assert event.value == 0
    assert event.taxes is None


def test_teilrueckzahlung_no_eventType():
    # Load the sample JSON file
    with open("tests/teilrueckzahlung_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "DK0064307755"
    assert event.isin2 == "Orsted"
    assert event.title == "ORSTED A/S EM.09/25 DK 10"
    assert event.shares == 17
    assert event.shares2 == 17
    assert event.value == 0
    assert event.taxes is None


def test_spinoff():
    # Load the sample JSON file
    with open("tests/spinoff.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "DE0007500001"
    assert event.isin2 == "TKMS"
    assert event.title == "ThyssenKrupp"
    assert event.shares == 0.309986
    assert event.shares2 is None
    assert event.value == 0
    assert event.taxes is None


def test_spinoff_no_eventType():
    # Load the sample JSON file
    with open("tests/spinoff_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "DE0007500001"
    assert event.isin2 == "TKMS"
    assert event.title == "ThyssenKrupp"
    assert event.shares == 0.309986
    assert event.shares2 is None
    assert event.value == 0
    assert event.taxes is None


def test_zwischenpapiere():
    # Load the sample JSON file
    with open("tests/zwischenpapiere.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "DK0064307839"
    assert event.isin2 == "ORSTED A/S EM.09/25 DK 10"
    assert event.title == "ORSTED A/S   -ANR-"
    assert event.shares == 119
    assert event.shares2 == 17
    assert event.value == -151.59
    assert event.taxes is None


def test_zwischenvertrieb():
    # Load the sample JSON file
    with open("tests/zwischenvertrieb.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "DK0060094928"
    assert event.isin2 == "ORSTED A/S   -ANR-"
    assert event.title == "Orsted"
    assert event.shares == 119.285835
    assert event.shares2 is None
    assert event.value == 0
    assert event.taxes is None


def test_zwischenvertrieb_no_eventType():
    # Load the sample JSON file
    with open("tests/zwischenvertrieb_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "DK0060094928"
    assert event.isin2 == "ORSTED A/S   -ANR-"
    assert event.title == "Orsted"
    assert event.shares == 119.285835
    assert event.shares2 is None
    assert event.value == 0
    assert event.taxes is None


def test_zwischenpapiere_no_eventType():
    # Load the sample JSON file
    with open("tests/zwischenpapiere_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.isin == "DK0064307839"
    assert event.isin2 == "ORSTED A/S EM.09/25 DK 10"
    assert event.title == "ORSTED A/S   -ANR-"
    assert event.shares == 119
    assert event.shares2 == 17
    assert event.value == -151.59
    assert event.taxes is None


def test_aktiendividende():
    # Load the sample JSON file
    with open("tests/aktiendividende.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "US2935941078"
    assert event.isin2 == "Enovix Corp. WTS 01.10.26"
    assert event.title == "Enovix"
    assert event.shares == 0.494370
    assert event.shares2 is None
    assert event.value == 0
    assert event.taxes is None


def test_aktiendividende_no_eventType():
    # Load the sample JSON file
    with open("tests/aktiendividende_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "US2935941078"
    assert event.isin2 == "Enovix Corp. WTS 01.10.26"
    assert event.title == "Enovix"
    assert event.shares == 0.494370
    assert event.shares2 is None
    assert event.value == 0
    assert event.taxes is None


def test_zusammenschluss():
    # Load the sample JSON file
    with open("tests/zusammenschluss.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "US7731221062"
    assert event.isin2 == "ROCKET LAB CORP. O.N."
    assert event.title == "Rocket Lab USA"
    assert event.shares == 5.943100
    assert event.shares2 == 5.943100
    assert event.value == 0
    assert event.taxes is None


def test_zusammenschluss_no_eventType():
    # Load the sample JSON file
    with open("tests/zusammenschluss_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "US7731221062"
    assert event.isin2 == "ROCKET LAB CORP. O.N."
    assert event.title == "Rocket Lab USA"
    assert event.shares == 5.943100
    assert event.shares2 == 5.943100
    assert event.value == 0
    assert event.taxes is None


def test_reverse_split():
    # Load the sample JSON file
    with open("tests/reverse_split.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "US3789734080"
    assert event.isin2 == "GLOBALSTAR INC. O.N."
    assert event.title == "Globalstar"
    assert event.shares == 110.403067
    assert event.shares2 == 7.360204
    assert event.value == 0
    assert event.taxes is None


def test_reverse_split_no_eventType():
    # Load the sample JSON file
    with open("tests/reverse_split_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SPINOFF
    assert event.isin == "US3789734080"
    assert event.isin2 == "GLOBALSTAR INC. O.N."
    assert event.title == "Globalstar"
    assert event.shares == 110.403067
    assert event.shares2 == 7.360204
    assert event.value == 0
    assert event.taxes is None
