"""
Tests for export_transactions via --load-event-database (no TR login or connection).
Uses tests/all_events_test.json with 5 events: buy, sell, dividend, deposit, split.
"""

import asyncio
import csv
import io
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from pytr.event import Event
from pytr.timeline import Timeline
from pytr.transactions import TransactionExporter

ALL_EVENTS_FILE = Path(__file__).parent / "all_events_test.json"
GOLDEN_CSV = Path(__file__).parent / "all_events_test_golden.csv"


def load_events(output_dir):
    tl = Timeline(
        tr=None,
        output_path=output_dir,
        store_event_database=False,
        load_event_database=ALL_EVENTS_FILE,
    )
    asyncio.run(tl.tl_loop())
    return tl.events


def export_csv(events):
    parsed = [Event.from_dict(e) for e in events]
    buf = io.StringIO()
    TransactionExporter(lang="de").export(buf, parsed, sort=True, format="csv")
    buf.seek(0)
    return list(csv.DictReader(buf, delimiter=";"))


def test_no_tr_connection(tmp_path, monkeypatch):
    """Timeline must not touch self.tr at all when load_event_database is set."""
    import pytr.timeline as tl_module

    original_init = tl_module.Timeline.__init__
    connection_attempted = []

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)

        class NoConnection:
            def __getattr__(self, name):
                connection_attempted.append(name)
                raise AssertionError(f"TR connection attempted: tr.{name}()")

        self.tr = NoConnection()

    monkeypatch.setattr(tl_module.Timeline, "__init__", patched_init)

    tl = tl_module.Timeline(
        tr=None,
        output_path=tmp_path,
        store_event_database=False,
        load_event_database=ALL_EVENTS_FILE,
    )
    asyncio.run(tl.tl_loop())

    assert not connection_attempted, f"TR was contacted via: {connection_attempted}"


def test_all_events_loaded(tmp_path):
    """All 5 events from the file are loaded into tl.events."""
    events = load_events(tmp_path)
    assert len(events) == 5


def test_events_sorted_by_timestamp(tmp_path):
    """Events are returned in chronological order."""
    events = load_events(tmp_path)
    timestamps = [datetime.fromisoformat(e["timestamp"][:19]) for e in events]
    assert timestamps == sorted(timestamps)


def test_no_database_written(tmp_path):
    """No all_events.json is written to output_dir when loading from an external file."""
    load_events(tmp_path)
    assert not (tmp_path / "all_events.json").exists()


def test_csv_row_count(tmp_path):
    """CSV contains at least one row per event."""
    rows = export_csv(load_events(tmp_path))
    assert len(rows) >= 5


def test_csv_transaction_types(tmp_path):
    """CSV contains the expected transaction types for all 5 event kinds."""
    rows = export_csv(load_events(tmp_path))
    types = {r["Typ"] for r in rows}
    assert "Kauf" in types
    assert "Verkauf" in types
    assert "Dividende" in types
    assert "Einlage" in types


def test_csv_buy_row(tmp_path):
    """BUY row has correct ISIN, shares, value and fees."""
    rows = export_csv(load_events(tmp_path))
    buy = next(r for r in rows if r["Typ"] == "Kauf")
    assert buy["ISIN"] == "IE00B4K6B022"
    assert float(buy["Stück"].replace(",", ".")) == 60.0
    assert float(buy["Wert"].replace(",", ".")) == -3002.8
    assert float(buy["Gebühren"].replace(",", ".")) == 1.0


def test_csv_sell_row(tmp_path):
    """SELL row has correct ISIN, shares, value, fees and taxes."""
    rows = export_csv(load_events(tmp_path))
    sell = next(r for r in rows if r["Typ"] == "Verkauf")
    assert sell["ISIN"] == "US26740W1099"
    assert float(sell["Stück"].replace(",", ".")) == 17.0
    assert float(sell["Wert"].replace(",", ".")) == 94.76
    assert float(sell["Gebühren"].replace(",", ".")) == 1.0
    assert float(sell["Steuern"].replace(",", ".")) == 3.18


def test_csv_dividend_row(tmp_path):
    """DIVIDEND row has correct ISIN, shares, value and taxes."""
    rows = export_csv(load_events(tmp_path))
    div = next(r for r in rows if r["Typ"] == "Dividende")
    assert div["ISIN"] == "US20030N1019"
    assert float(div["Wert"].replace(",", ".")) == 2.24
    assert float(div["Steuern"].replace(",", ".")) == 0.78


def test_csv_deposit_row(tmp_path):
    """DEPOSIT row has correct value."""
    rows = export_csv(load_events(tmp_path))
    deposit = next(r for r in rows if r["Typ"] == "Einlage")
    assert float(deposit["Wert"].replace(",", ".")) == 200.0


def test_cli_golden(tmp_path):
    """CLI output matches the golden CSV exactly."""
    out_file = tmp_path / "account_transactions.csv"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytr",
            "export_transactions",
            "--load-event-database",
            str(ALL_EVENTS_FILE),
            "-l",
            "de",
            "--decimal-localization",
            "-s",
            str(out_file),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"pytr exited with {result.returncode}:\n{result.stderr}"
    actual = out_file.read_text(encoding="utf-8")
    expected = GOLDEN_CSV.read_text(encoding="utf-8")
    assert actual == expected
