import json

from pytr.event import Event
from pytr.transactions import TransactionExporter


def test_incoming_transfer_delegation():
    # Load the sample JSON file
    with open("tests/incoming_transfer_delegation.json", "r", encoding="utf-8") as file:
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
    with open("tests/buy.json", "r", encoding="utf-8") as file:
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


def test_private_markets_trade_bonus():
    # Load the sample JSON file
    with open("tests/private_markets_trade_bonus.json", "r", encoding="utf-8") as file:
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
            "Datum": "2025-09-18T07:14:56",
            "Typ": "Kauf",
            "Wert": -1,
            "Notiz": "Apollo",
            "ISIN": "LU3170240538",
            "Stück": 0.01,
            "Gebühren": None,
            "Steuern": None,
        },
        {
            "Datum": "2025-09-18T07:14:56",
            "Typ": "Einlage",
            "Wert": 1,
            "Notiz": "Apollo",
            "ISIN": None,
            "Stück": None,
            "Gebühren": None,
            "Steuern": None,
        },
    ]


def test_private_markets_trade_bonus_no_eventType():
    # Load the sample JSON file
    with open("tests/private_markets_trade_bonus_no_eventType.json", "r", encoding="utf-8") as file:
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
            "Datum": "2025-09-18T07:14:56",
            "Typ": "Kauf",
            "Wert": -1.0,
            "Notiz": "Apollo",
            "ISIN": "LU3170240538",
            "Stück": 0.01,
            "Gebühren": None,
            "Steuern": None,
        },
        {
            "Datum": "2025-09-18T07:14:56",
            "Typ": "Einlage",
            "Wert": 1,
            "Notiz": "Apollo",
            "ISIN": None,
            "Stück": None,
            "Gebühren": None,
            "Steuern": None,
        },
    ]
