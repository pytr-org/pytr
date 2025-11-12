import json

from pytr.event import ConditionalEventType, Event, PPEventType


def test_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_event.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DEPOSIT
    assert event.value == 3000.0


def test_new_saveback_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_saveback_new.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SAVEBACK
    assert event.value == -15.0
    assert event.shares == 0.546348


def test_trade_perk_from_dict():
    # Load the sample JSON file
    with open("tests/sample_trade_perk.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SAVEBACK
    assert event.value == 10.03
    assert event.shares == 0.0487


def test_new_sell_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_sell_new.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.value == 114.91
    assert event.shares == 11


def test_old_sell_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_sell_old.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.value == 119.37
    assert event.shares == 3


def test_buy_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_buy.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.value == -3002.8
    assert event.shares == 60


def test_new_deposit_from_dict():
    # Load the sample JSON file
    with open("tests/sample_deposit_new.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DEPOSIT
    assert event.value == 200


def test_new_removal_from_dict():
    # Load the sample JSON file
    with open("tests/sample_removal_new.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.REMOVAL
    assert event.value == -750


def test_dividend_sell_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_sell_dividend.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.value == 0.1
    assert event.shares == 100
    assert event.isin == "DE000SX12345"


def test_private_markets_buy_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_private_markets_order.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.PRIVATE_MARKETS_ORDER
    assert event.value == -101
    assert event.shares == 100


def test_private_markets_bonus_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_private_markets_bonus_order.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.PRIVATE_MARKETS_ORDER
    assert event.value == -1
    assert event.shares == 1


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


def test_zinsen_no_eventType():
    # Load the sample JSON file
    with open("tests/zinsen_no_eventType.json", "r", encoding="utf-8") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.INTEREST
    assert event.title == "Zinsen"
    assert event.value == 3.6
    assert event.taxes == 0.2


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
