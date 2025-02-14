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
            "Date": "2024-09-10",
            "Type": "Einlage",
            "Value": "3.000",
        }
    ]
    # "2024-09-10;Einlage;3.000;Vorname Nachname;;;;\n"


def test_buy():
    # Load the sample JSON file
    with open("tests/sample_buy.json", "r") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    event = Event.from_dict(sample_data)

    # Create an instance of EventCsvFormatter
    formatter = TransactionExporter(lang="de")

    # Format the event to CSV
    transactions = formatter.format(event)

    # Assert that the output is not an empty string
    assert transactions == [{}]
    # "2024-02-20;Kauf;-3.002,8;Euro Stoxx 50 EUR (Dist);IE00B4K6B022;60;-1;\n"
