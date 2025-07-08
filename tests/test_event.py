import json

from pytr.event import ConditionalEventType, Event, PPEventType


def test_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_event.json", "r") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DEPOSIT
    assert event.value == 3000.0


def test_new_saveback_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_saveback_new.json", "r") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.SAVEBACK
    assert event.value == -15.0
    assert event.shares == 0.546348


def test_new_sell_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_sell_new.json", "r") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.value == 114.91
    assert event.shares == 11


def test_old_sell_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_sell_old.json", "r") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == ConditionalEventType.TRADE_INVOICE
    assert event.value == 119.37
    assert event.shares == 3


def test_dividend_sell_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_sell_dividend.json", "r") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DIVIDEND
    assert event.value == 0.1
    assert event.shares == 100
    assert event.isin == "DE000SX12345"
