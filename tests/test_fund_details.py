import argparse
import asyncio
import sys
from decimal import Decimal

import pytest

from pytr import main as main_module
from pytr.fund_details import (
    FundDetailsError,
    FundDetailsResult,
    fetch_fund_details,
    format_fund_details,
    parse_isin,
)
from pytr.main import get_main_parser

ISIN = "IE00B4L5Y983"


METADATA = {
    "name": "Example Fund",
    "shortName": "Example",
    "typeId": "fund",
    "wkn": "A0TEST",
    "isin": ISIN,
    "exchangeIds": ["XETRA", "LSX"],
    "marketCap": {"value": "123456789.00", "currencyId": "EUR"},
    "description": "YTM is indicative.\nIt is not a guarantee.",
    "fundInfo": {
        "weightedAvgYieldToMaturity": "0.0435",
        "ter": "0.120000",
        "netAssetValue": "101.2300",
        "netAssetValueDate": "2026-10-06",
        "duration": "5.500",
        "maturityDate": "2030-01-01",
        "useOfProfitsDisplayName": "Accumulating",
    },
}


class FakeTradeRepublic:
    def __init__(self, ticker_response=None, ticker_error=None):
        self.calls = []
        self.unsubscribed = []
        self.closed = False
        self.metadata_sent = False
        self.ticker_response = ticker_response
        self.ticker_error = ticker_error

    async def instrument_details(self, isin):
        self.calls.append(("instrument_details", isin))
        return "instrument-subscription"

    async def ticker(self, isin, exchange):
        self.calls.append(("ticker", isin, exchange))
        if self.ticker_error is not None:
            raise self.ticker_error
        return "ticker-subscription"

    async def recv(self):
        if not self.metadata_sent:
            self.metadata_sent = True
            return "instrument-subscription", {"type": "instrument"}, METADATA
        if self.ticker_response is not None:
            response = self.ticker_response
            self.ticker_response = None
            return "ticker-subscription", {"type": "ticker"}, response
        await asyncio.Event().wait()

    async def unsubscribe(self, subscription_id):
        self.calls.append(("unsubscribe", subscription_id))
        self.unsubscribed.append(subscription_id)

    async def close(self):
        self.calls.append(("close",))
        self.closed = True


def test_success_uses_only_metadata_and_selected_ticker_and_formats_decimal_spread(capsys):
    tr = FakeTradeRepublic(
        {
            "bid": {"price": "10.1234", "time": 1720000000123},
            "ask": {"price": "10.2468", "time": 1720000000123},
        }
    )

    result = asyncio.run(fetch_fund_details(tr, ISIN.lower(), timeout=1))
    print(format_fund_details(result))

    assert tr.calls == [
        ("instrument_details", ISIN),
        ("ticker", ISIN, "XETRA"),
        ("unsubscribe", "ticker-subscription"),
        ("unsubscribe", "instrument-subscription"),
        ("close",),
    ]
    assert tr.unsubscribed == ["ticker-subscription", "instrument-subscription"]
    assert tr.closed
    output = capsys.readouterr().out
    assert "Name: Example Fund" in output
    assert "ISIN: IE00B4L5Y983" in output
    assert "Exchange: XETRA" in output
    assert "YTM: 4.35%" in output
    assert "TER: 0.12%" in output
    assert "Net asset value: 101.2300" in output
    assert "Market cap: 123456789.00 EUR" in output
    assert "Bid: 10.1234" in output
    assert "Ask: 10.2468" in output
    assert "Spread: 0.1234" in output
    assert "Quote timestamp: 1720000000123" in output
    assert "Quote status: available" in output
    assert "YTM note: YTM is indicative. It is not a guarantee." in output


def test_ticker_timeout_keeps_metadata_and_marks_quote_unavailable(capsys):
    tr = FakeTradeRepublic()

    result = asyncio.run(fetch_fund_details(tr, ISIN, timeout=0.001))
    print(format_fund_details(result))

    assert tr.calls == [
        ("instrument_details", ISIN),
        ("ticker", ISIN, "XETRA"),
        ("unsubscribe", "ticker-subscription"),
        ("unsubscribe", "instrument-subscription"),
        ("close",),
    ]
    assert tr.unsubscribed == ["ticker-subscription", "instrument-subscription"]
    assert tr.closed
    output = capsys.readouterr().out
    assert "Name: Example Fund" in output
    assert "Bid: n/a" in output
    assert "Ask: n/a" in output
    assert "Spread: n/a" in output
    assert "Quote timestamp: n/a" in output
    assert "Quote status: unavailable" in output


def test_unknown_exchange_does_not_subscribe_to_ticker():
    tr = FakeTradeRepublic({"bid": {"price": "1"}, "ask": {"price": "2"}})

    with pytest.raises(FundDetailsError, match="Unknown exchange: NASDAQ"):
        asyncio.run(fetch_fund_details(tr, ISIN, exchange="NASDAQ", timeout=1))

    assert tr.calls == [
        ("instrument_details", ISIN),
        ("unsubscribe", "instrument-subscription"),
        ("close",),
    ]
    assert tr.unsubscribed == ["instrument-subscription"]
    assert tr.closed


def test_ticker_error_is_metadata_only_and_no_other_api_is_used():
    tr = FakeTradeRepublic(ticker_error=RuntimeError("ticker unavailable"))

    result = asyncio.run(fetch_fund_details(tr, ISIN, timeout=1))

    assert result.bid is None
    assert result.ask is None
    assert tr.calls == [
        ("instrument_details", ISIN),
        ("ticker", ISIN, "XETRA"),
        ("unsubscribe", "instrument-subscription"),
        ("close",),
    ]
    assert tr.unsubscribed == ["instrument-subscription"]
    assert tr.closed


def test_invalid_isin_is_rejected_by_parser_before_login(monkeypatch):
    login_calls = []

    def login_must_not_run(*args, **kwargs):
        login_calls.append((args, kwargs))

    monkeypatch.setattr(main_module, "login", login_must_not_run)
    monkeypatch.setattr(sys, "argv", ["pytr", "fund_details", "not-an-isin"])
    with pytest.raises(SystemExit):
        main_module.main()

    assert login_calls == []
    with pytest.raises(SystemExit):
        get_main_parser().parse_args(["fund_details", "not-an-isin"])

    assert parse_isin(ISIN.lower()) == ISIN
    with pytest.raises(argparse.ArgumentTypeError):
        parse_isin("not-an-isin")


def test_spread_is_only_calculated_when_ask_is_at_least_bid():
    tr = FakeTradeRepublic({"bid": {"price": "2.00"}, "ask": {"price": "1.99"}})

    result = asyncio.run(fetch_fund_details(tr, ISIN, timeout=1))

    assert result.spread is None
    assert result.bid == Decimal("2.00")
    assert result.ask == Decimal("1.99")
    assert result.quote_status == "partial"


def test_ticker_with_one_valid_side_is_partial_and_preserves_that_side():
    tr = FakeTradeRepublic({"bid": {"price": "10.1234", "time": 1720000000123}})

    result = asyncio.run(fetch_fund_details(tr, ISIN, timeout=1))

    assert result.quote_status == "partial"
    assert result.bid == Decimal("10.1234")
    assert result.ask is None
    assert result.spread is None
    assert result.quote_timestamp == 1720000000123


def test_crossed_ticker_is_partial_and_preserves_both_sides():
    tr = FakeTradeRepublic(
        {
            "bid": {"price": "10.00", "time": 1720000000123},
            "ask": {"price": "9.00", "time": 1720000000124},
        }
    )

    result = asyncio.run(fetch_fund_details(tr, ISIN, timeout=1))

    assert result.quote_status == "partial"
    assert result.bid == Decimal("10.00")
    assert result.ask == Decimal("9.00")
    assert result.spread is None


def test_malformed_percentage_fields_render_as_missing():
    metadata = dict(METADATA)
    metadata["fundInfo"] = dict(METADATA["fundInfo"], weightedAvgYieldToMaturity="bad", ter="bad")

    output = format_fund_details(FundDetailsResult(metadata, "XETRA", None, None, "unavailable"))

    assert "YTM: n/a" in output
    assert "TER: n/a" in output
