import argparse
import asyncio
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from pytr.rates import ISIN_RE

DEFAULT_TIMEOUT = 5


class FundDetailsError(ValueError):
    """A concise, user-facing error while reading fund details."""


def normalize_isin(value: str) -> str:
    """Normalize and validate one ISIN without doing any I/O."""
    isin = value.upper()
    if not ISIN_RE.fullmatch(isin):
        raise ValueError(f"Invalid ISIN: {value}")
    return isin


def parse_isin(value: str) -> str:
    """argparse type for the fund-details ISIN argument."""
    try:
        return normalize_isin(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None


@dataclass(frozen=True)
class FundDetailsResult:
    metadata: Mapping[str, Any]
    exchange: str
    bid: Decimal | None
    ask: Decimal | None
    quote_status: str
    quote_timestamp: Any = None

    @property
    def quote_available(self) -> bool:
        """Compatibility view for callers that only need the fully available state."""
        return self.quote_status == "available"

    @property
    def spread(self) -> Decimal | None:
        if self.quote_status != "available" or self.bid is None or self.ask is None:
            return None
        if (
            not self.bid.is_finite()
            or not self.ask.is_finite()
            or self.bid < 0
            or self.ask < 0
            or self.ask < self.bid
        ):
            return None
        return self.ask - self.bid


def _path(data: Mapping[str, Any], *keys: str) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return number if number.is_finite() else None


def _quote_value(payload: Mapping[str, Any], side: str) -> Any:
    value = payload.get(side)
    if isinstance(value, Mapping):
        return value.get("price")
    return value


def _quote_timestamp(payload: Mapping[str, Any]) -> Any:
    for side in ("bid", "ask", "last"):
        value = payload.get(side)
        if isinstance(value, Mapping) and "time" in value and value["time"] not in (None, ""):
            return value["time"]
    return None


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _percentage(value: Any, fraction: bool = False) -> str:
    number = _decimal(value)
    if number is None:
        return "n/a"
    if fraction:
        number *= Decimal("100")
    return f"{_decimal_text(number)}%"


async def _receive_matching(tr, subscription_id: Any, subscription_type: str, timeout: Any) -> Any:
    async def receive() -> Any:
        while True:
            response_id, subscription, response = await tr.recv()
            if response_id != subscription_id:
                continue
            if not isinstance(subscription, Mapping) or subscription.get("type") != subscription_type:
                raise FundDetailsError("Unexpected subscription response.")
            return response

    return await asyncio.wait_for(receive(), timeout=timeout)


async def fetch_fund_details(
    tr,
    isin: str,
    exchange: str | None = None,
    timeout: Any = DEFAULT_TIMEOUT,
) -> FundDetailsResult:
    """Read instrument metadata and one exchange ticker, without other API calls."""
    normalized_isin = normalize_isin(isin)
    try:
        timeout_value = Decimal(str(timeout))
    except (InvalidOperation, ValueError, TypeError):
        timeout_value = None
    if timeout_value is None or not timeout_value.is_finite() or timeout_value <= 0:
        raise ValueError("The timeout must be finite and greater than zero.")

    metadata_subscription_id: str | None = None
    ticker_subscription_id: str | None = None
    try:
        try:
            metadata_subscription_id = await tr.instrument_details(normalized_isin)
            metadata = await _receive_matching(
                tr,
                metadata_subscription_id,
                "instrument",
                timeout,
            )
        except FundDetailsError:
            raise
        except Exception as error:
            raise FundDetailsError("Could not fetch instrument metadata.") from error

        if not isinstance(metadata, Mapping):
            raise FundDetailsError("Could not fetch instrument metadata.")

        exchange_ids = metadata.get("exchangeIds")
        if not isinstance(exchange_ids, list) or not exchange_ids or not all(isinstance(item, str) for item in exchange_ids):
            raise FundDetailsError("Instrument metadata contains no exchange.")

        selected_exchange = exchange if exchange is not None else exchange_ids[0]
        if selected_exchange not in exchange_ids:
            raise FundDetailsError(f"Unknown exchange: {selected_exchange}")

        bid: Decimal | None = None
        ask: Decimal | None = None
        quote_status = "unavailable"
        quote_timestamp: Any = None
        try:
            ticker_subscription_id = await tr.ticker(normalized_isin, exchange=selected_exchange)
            ticker = await _receive_matching(tr, ticker_subscription_id, "ticker", timeout)
            if isinstance(ticker, Mapping):
                bid = _decimal(_quote_value(ticker, "bid"))
                ask = _decimal(_quote_value(ticker, "ask"))
                quote_timestamp = _quote_timestamp(ticker)
            if bid is not None and ask is not None and bid >= 0 and ask >= 0 and ask >= bid:
                quote_status = "available"
            else:
                quote_status = "partial"
        except Exception:
            # Metadata is still useful when the quote subscription times out or fails.
            bid = None
            ask = None
            quote_status = "unavailable"
            quote_timestamp = None

        return FundDetailsResult(metadata, selected_exchange, bid, ask, quote_status, quote_timestamp)
    finally:
        try:
            for subscription_id in (ticker_subscription_id, metadata_subscription_id):
                if subscription_id is not None:
                    try:
                        await tr.unsubscribe(subscription_id)
                    except Exception:
                        # Cleanup must not prevent the websocket from being closed.
                        pass
        finally:
            await tr.close()


def _display(value: Any) -> str:
    if value is None or value == "":
        return "n/a"
    return str(value)


def _market_cap(metadata: Mapping[str, Any]) -> str:
    value = _path(metadata, "marketCap", "value")
    if value is None or value == "":
        return "n/a"
    currency = _path(metadata, "marketCap", "currencyId")
    return f"{value} {currency}" if currency not in (None, "") else str(value)


def _ytm_note(metadata: Mapping[str, Any]) -> str | None:
    description = metadata.get("description")
    if not isinstance(description, str):
        return None
    if not re.search(r"\b(?:ytm|yield[\s-]+to[\s-]+maturity)\b", description, re.IGNORECASE):
        return None
    normalized = " ".join(description.split())
    return normalized or None


def format_fund_details(result: FundDetailsResult) -> str:
    """Render a stable, deliberately small view of the approved response fields."""
    metadata = result.metadata
    fund_info = metadata.get("fundInfo")
    lines = [
        f"Name: {_display(metadata.get('name'))}",
        f"Short name: {_display(metadata.get('shortName'))}",
        f"Type: {_display(metadata.get('typeId'))}",
        f"WKN: {_display(metadata.get('wkn'))}",
        f"ISIN: {_display(metadata.get('isin'))}",
        f"Exchange: {_display(result.exchange)}",
        f"YTM: {_percentage(_path(fund_info, 'weightedAvgYieldToMaturity') if isinstance(fund_info, Mapping) else None, fraction=True)}",
        f"TER: {_percentage(_path(fund_info, 'ter') if isinstance(fund_info, Mapping) else None)}",
        f"Net asset value: {_display(_path(fund_info, 'netAssetValue') if isinstance(fund_info, Mapping) else None)}",
        f"Net asset value date: {_display(_path(fund_info, 'netAssetValueDate') if isinstance(fund_info, Mapping) else None)}",
        f"Duration: {_display(_path(fund_info, 'duration') if isinstance(fund_info, Mapping) else None)}",
        f"Maturity date: {_display(_path(fund_info, 'maturityDate') if isinstance(fund_info, Mapping) else None)}",
        f"Use of profits: {_display(_path(fund_info, 'useOfProfitsDisplayName') if isinstance(fund_info, Mapping) else None)}",
        f"Market cap: {_market_cap(metadata)}",
        f"Bid: {_display(result.bid)}",
        f"Ask: {_display(result.ask)}",
        f"Spread: {_display(result.spread)}",
        f"Quote timestamp: {_display(result.quote_timestamp)}",
        f"Quote status: {result.quote_status}",
    ]
    note = _ytm_note(metadata)
    if note is not None:
        lines.insert(13, f"YTM note: {note}")
    return "\n".join(lines)


class FundDetails:
    def __init__(self, tr, isin: str, exchange: str | None = None, timeout: Any = DEFAULT_TIMEOUT):
        self.tr = tr
        self.isin = isin
        self.exchange = exchange
        self.timeout = timeout

    async def details_loop(self) -> FundDetailsResult:
        self.result = await fetch_fund_details(self.tr, self.isin, self.exchange, self.timeout)
        return self.result

    def get(self) -> FundDetailsResult:
        result = asyncio.run(self.details_loop())
        print(format_fund_details(result))
        return result
