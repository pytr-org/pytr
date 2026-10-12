"""
Tests for export_transactions via --load-event-database (no TR login or connection).
Uses tests/all_events_test.json with 5 events: buy, sell, dividend, deposit, split.
"""

import asyncio
import csv
import io
import subprocess
import sys
from datetime import datetime, timedelta, timezone
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


# ---------------------------------------------------------------------------
# Timestamp / cutoff filtering tests
#
# Event timestamps in all_events_test.json (all UTC):
#   buy      2024-02-20T16:32:07
#   deposit  2024-06-03T17:07:26
#   split    2024-06-26T08:06:40
#   sell     2025-03-14T07:03:14
#   dividend 2025-10-23T14:19:56
# ---------------------------------------------------------------------------

UTC = timezone.utc


def _ts(iso_utc: str) -> float:
    """Parse an ISO string with explicit UTC offset to a POSIX timestamp."""
    return datetime.fromisoformat(iso_utc).timestamp()


def load_events_filtered(output_dir, not_before=0.0, not_after=float("inf")):
    tl = Timeline(
        tr=None,
        output_path=output_dir,
        store_event_database=False,
        load_event_database=ALL_EVENTS_FILE,
        not_before=not_before,
        not_after=not_after,
    )
    asyncio.run(tl.tl_loop())
    return tl.events


def event_ids(events):
    return {e["id"] for e in events}


def test_not_before_utc_excludes_early_events(tmp_path):
    """not_before after deposit cuts buy and deposit, keeps split/sell/dividend."""
    # 2024-06-03T18:00:00Z is after deposit (17:07 UTC) and buy (Feb)
    not_before = _ts("2024-06-03T18:00:00+00:00")
    events = load_events_filtered(tmp_path, not_before=not_before)
    ids = event_ids(events)
    assert "12345678" not in ids  # buy  (2024-02-20)
    assert "deposit-001" not in ids  # deposit (2024-06-03 17:07)
    assert "e230be28-286a-31b6-879f-5c97f8a9d85a" in ids  # split
    assert "5b0f491f-7bad-40b1-8cd1-56d83729afd4" in ids  # sell
    assert "88008da6-da94-3e0e-8ea5-e3878643f5ab" in ids  # dividend


def test_not_after_utc_excludes_late_events(tmp_path):
    """not_after before 2025 cuts sell and dividend, keeps buy/deposit/split."""
    not_after = _ts("2025-01-01T00:00:00+00:00")
    events = load_events_filtered(tmp_path, not_after=not_after)
    ids = event_ids(events)
    assert "12345678" in ids  # buy
    assert "deposit-001" in ids  # deposit
    assert "e230be28-286a-31b6-879f-5c97f8a9d85a" in ids  # split
    assert "5b0f491f-7bad-40b1-8cd1-56d83729afd4" not in ids  # sell (2025)
    assert "88008da6-da94-3e0e-8ea5-e3878643f5ab" not in ids  # dividend (2025)


def test_not_before_and_not_after_bracket(tmp_path):
    """Bracket to 2024 only: buy, deposit, split in; sell, dividend out."""
    not_before = _ts("2024-01-01T00:00:00+00:00")
    not_after = _ts("2024-12-31T23:59:59+00:00")
    events = load_events_filtered(tmp_path, not_before=not_before, not_after=not_after)
    ids = event_ids(events)
    assert "12345678" in ids  # buy
    assert "deposit-001" in ids  # deposit
    assert "e230be28-286a-31b6-879f-5c97f8a9d85a" in ids  # split
    assert "5b0f491f-7bad-40b1-8cd1-56d83729afd4" not in ids  # sell
    assert "88008da6-da94-3e0e-8ea5-e3878643f5ab" not in ids  # dividend


def test_last_days_cutoff(tmp_path):
    """last_days computed the same way main.py does: cuts old events, keeps recent ones.

    The newest event is dividend at 2025-10-23. We pick last_days so that the
    cutoff falls between the sell (2025-03-14) and dividend (2025-10-23), i.e.
    relative to 'now' we keep only the dividend. We calculate not_before the
    same way main.py does to stay timezone-independent.
    """
    # Anchor: dividend is at 2025-10-23T14:19:56 UTC.
    # We want not_before to land between sell (2025-03-14) and dividend (2025-10-23).
    # Use a fixed reference: 2026-10-12 (today) minus 400 days → 2025-09-07, which is
    # after sell but before dividend.
    reference_now = datetime(2026, 10, 12, tzinfo=UTC)
    not_before = (reference_now - timedelta(days=400)).timestamp()

    events = load_events_filtered(tmp_path, not_before=not_before)
    ids = event_ids(events)
    assert "88008da6-da94-3e0e-8ea5-e3878643f5ab" in ids  # dividend (2025-10-23, after cutoff)
    assert "5b0f491f-7bad-40b1-8cd1-56d83729afd4" not in ids  # sell (2025-03-14, before cutoff)
    assert "12345678" not in ids  # buy (2024, before cutoff)


def test_from_timestamp_naive_vs_utc_offset(tmp_path):
    """A naive ISO string (local time) and the same instant as +HH:MM produce the same POSIX value.

    This mirrors the main.py conversion:  datetime.fromisoformat(s).astimezone().timestamp()
    We pick a UTC instant, convert to local time for the naive string, and assert both paths
    give the same POSIX timestamp.
    """
    utc_instant = datetime(2025, 3, 14, 7, 3, 14, tzinfo=UTC)
    posix_utc = utc_instant.timestamp()

    # Path 1: explicit UTC offset string (as a user would pass --from_timestamp 2025-03-14T07:03:14+00:00)
    from_utc_str = "2025-03-14T07:03:14+00:00"
    posix_from_utc = datetime.fromisoformat(from_utc_str).astimezone().timestamp()
    assert posix_from_utc == posix_utc

    # Path 2: naive local-time string (user passes local clock reading of the same instant)
    local_dt = utc_instant.astimezone()  # convert to local TZ
    naive_local_str = local_dt.strftime("%Y-%m-%dT%H:%M:%S")  # drop tzinfo, as a user would type
    posix_from_naive = datetime.fromisoformat(naive_local_str).astimezone().timestamp()
    assert posix_from_naive == posix_utc
