import json

from pytr.event import Event
from pytr.transactions import TransactionExporter


def test_event_csv_formatter():
    # Load the sample JSON file
    with open("tests/sample_event.json", "r") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Create an instance of EventCsvFormatter
    formatter = TransactionExporter(lang="de")

    # Format the event to CSV
    transactions = list(formatter.from_event(event))

    # Assert that the output is not an empty string
    assert transactions == [
        {
            "Datum": "2024-09-10T13:18:31",
            "Gebühren": None,
            "ISIN": None,
            "Notiz": "Vorname Nachname",
            "Steuern": None,
            "Stück": None,
            "Typ": "Einlage",
            "Wert": 3000.0,
        }
    ]


def test_buy():
    # Load the sample JSON file
    with open("tests/sample_buy.json", "r") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Create an instance of EventCsvFormatter
    formatter = TransactionExporter(lang="de")

    # Format the event to CSV
    transactions = list(formatter.from_event(event))

    # Assert that the output is not an empty string
    assert transactions == [
        {
            "Datum": "2024-02-20T16:32:07",
            "Gebühren": -1.0,
            "ISIN": "IE00B4K6B022",
            "Notiz": "Euro Stoxx 50 EUR (Dist)",
            "Steuern": None,
            "Stück": 60.0,
            "Typ": "Kauf",
            "Wert": -3002.8,
        }
    ]
