import json

from pytr.event import Event, PPEventType


def test_event_from_dict():
    # Load the sample JSON file
    with open("tests/sample_event.json", "r") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Assert the expected values
    assert event.event_type == PPEventType.DEPOSIT
    assert event.value == 3000.0
