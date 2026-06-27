import asyncio
import locale
import re
from decimal import Decimal
from pathlib import Path
from typing import Optional

from .tickers import (
    decimal_format,
    fetch_instrument_details,
    fetch_tickers,
    normalize_lang,
)
from .utils import get_logger


class Rates:
    def __init__(
        self,
        tr,
        isins: list[str],
        output=None,
        lang: str = "en",
        decimal_localization: bool = False,
        sort_by_column: Optional[str] = "name",
        sort_descending: bool = False,
    ):
        self.tr = tr
        self.isins = isins
        self.output = output
        self.lang = normalize_lang(lang)
        self.decimal_localization = decimal_localization
        self.sort_by_column = sort_by_column
        self.sort_descending = sort_descending

        self._log = get_logger(__name__)

    def _decimal_format(self, value, precision: int = 4):
        return decimal_format(value, precision, self.decimal_localization, self.lang)

    async def rates_loop(self):
        if not self.isins:
            self._log.warning("No ISINs provided.")
            return

        self.positions = [{"instrumentId": isin} for isin in self.isins]

        self._log.info("Subscribing to tickers...")
        await fetch_instrument_details(self.tr, self.positions)
        missing = await fetch_tickers(self.tr, self.positions)
        for pos in missing:
            self._log.warning(
                f"Missing price for {pos.get('name', pos['instrumentId'])} ({pos['instrumentId']}), removing from result."
            )

        self.positions = [pos for pos in self.positions if "price" in pos]

        await self.tr.close()

    def _get_sort_func(self):
        match self.sort_by_column:
            case "name":
                if self.lang == "de":
                    locale.setlocale(locale.LC_COLLATE, "de_DE.UTF-8")
                return lambda x: locale.strxfrm(x["name"].lower())
            case "isin":
                if self.lang == "de":
                    locale.setlocale(locale.LC_COLLATE, "de_DE.UTF-8")
                return lambda x: locale.strxfrm(x["instrumentId"].lower())
            case "ask":
                return lambda x: Decimal(x["ask"]) if x.get("ask") is not None else Decimal(0)
            case "price":
                return lambda x: Decimal(x["price"])
            case _ as m:
                print(f"Column {m} does not exist for portfolio list, reverting to default sorting by price.")
                return lambda x: Decimal(x["price"])

    def overview(self):
        print(f"{'Name':<30.30} {'ISIN':<12}  {'price':>10}  {'ask':>10}")
        for p in sorted(self.positions, key=self._get_sort_func(), reverse=self.sort_descending):
            print(
                f"{p['name']:<30.30} "
                f"{p['instrumentId']:<12}  "
                f"{self._decimal_format(p['price']):>10}  "
                f"{self._decimal_format(p.get('ask')):>10}"
            )

    def write_csv(self):
        lines = [
            f"{p['name']};{p['instrumentId']};{self._decimal_format(p['price'])};{self._decimal_format(p.get('ask'))}"
            for p in sorted(self.positions, key=self._get_sort_func(), reverse=self.sort_descending)
        ]
        header = "name;ISIN;price;ask"
        content = header + "\n" + "\n".join(lines) + ("\n" if lines else "")
        Path(self.output).parent.mkdir(parents=True, exist_ok=True)
        with open(self.output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Wrote {len(lines) + 1} lines to {self.output}")

    def get(self):
        asyncio.run(self.rates_loop())
        if self.output is None:
            self.overview()
        else:
            self.write_csv()


ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")


def _extract_isins(tokens: list[str]) -> list[str]:
    return [t for t in tokens if ISIN_RE.match(t)]


def _split_isin_text(text: str) -> list[str]:
    """Split text on commas, semicolons, or whitespace and return non-empty tokens."""
    return [t.strip() for t in re.split(r"[,;\s]+", text) if t.strip()]


def parse_isin_input(input_list: list[str], fileobj) -> list[str]:
    """Return ISINs from input_list (preferred) or from a file/stdin.

    Tokens may be comma, semicolon, or whitespace/newline separated.
    """
    if input_list:
        tokens = _split_isin_text(" ".join(input_list))
        return _extract_isins(tokens)

    if fileobj is None:
        return []

    content = fileobj.read()
    if not content.strip():
        return []

    return _extract_isins(_split_isin_text(content))
