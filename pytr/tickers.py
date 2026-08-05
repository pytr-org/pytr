import asyncio
import re
from decimal import Decimal
from locale import getdefaultlocale
from typing import Optional

from babel.numbers import format_decimal

from .utils import get_logger

SUPPORTED_LANGUAGES = {
    "cs",
    "da",
    "de",
    "en",
    "es",
    "fr",
    "it",
    "nl",
    "pl",
    "pt",
    "ru",
    "zh",
}

bond_pattern = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December|Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\.?\s+20\d{2}",
    re.IGNORECASE,
)

_log = get_logger(__name__)


def normalize_lang(lang: str) -> str:
    """Resolve 'auto' to the system locale language, fall back to 'en' if unsupported."""
    if lang == "auto":
        detected = getdefaultlocale()[0]
        lang = detected.split("_")[0] if detected else "en"
    if lang not in SUPPORTED_LANGUAGES:
        _log.info(f'Language not yet supported "{lang}", defaulting to "en"')
        lang = "en"
    return lang


def decimal_format(
    value,
    precision: int = 2,
    decimal_localization: bool = False,
    lang: str = "en",
) -> Optional[str]:
    if value is None:
        return None
    if decimal_localization:
        fmt = "#,##0." + ("#" * precision)
        return format_decimal(value, format=fmt, locale=lang)
    return f"{float(value):.{precision}f}".rstrip("0").rstrip(".")


async def fetch_instrument_details(tr, positions: list[dict]) -> None:
    """Populate pos['name'] and pos['exchangeIds'] for each position in-place."""
    subscriptions = {}
    for pos in positions:
        sub_id = await tr.instrument_details(pos["instrumentId"])
        subscriptions[sub_id] = pos

    while subscriptions:
        sub_id, subscription, response = await tr.recv()
        if subscription["type"] == "instrument":
            await tr.unsubscribe(sub_id)
            pos = subscriptions.pop(sub_id)
            pos["name"] = response.get("shortName", pos["instrumentId"])
            pos["exchangeIds"] = response.get("exchangeIds", [])
        else:
            _log.debug(f"Unexpected subscription type: {subscription['type']}")


async def fetch_tickers(tr, positions: list[dict], timeout: float = 5.0) -> list[dict]:
    """Fetch ticker prices for positions that have exchangeIds.

    Populates pos['price'] and pos['ask'] in-place. Bond prices are divided by 100.
    Returns the list of positions for which no price was received.
    """
    subscriptions = {}
    for pos in positions:
        if pos.get("exchangeIds"):
            sub_id = await tr.ticker(pos["instrumentId"], exchange=pos["exchangeIds"][0])
            subscriptions[sub_id] = pos
        else:
            _log.warning(f"No exchange found for {pos['instrumentId']}, skipping.")

    while subscriptions:
        try:
            sub_id, subscription, response = await asyncio.wait_for(tr.recv(), timeout)
        except asyncio.TimeoutError:
            _log.warning(f"Timed out waiting for tickers: {list(subscriptions.values())}")
            break

        if subscription["type"] == "ticker":
            await tr.unsubscribe(sub_id)
            pos = subscriptions.pop(sub_id)
            pos["price"] = response["last"]["price"]
            if bond_pattern.search(pos.get("name", "")):
                pos["price"] = Decimal(pos["price"]) / 100
            pos["ask"] = response.get("ask", {}).get("price")
        else:
            _log.debug(f"Unexpected subscription type: {subscription['type']}")

    missing = [pos for pos in positions if "price" not in pos]
    return missing
