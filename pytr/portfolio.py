import asyncio
import locale
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Optional

from .tickers import (
    decimal_format,
    fetch_instrument_details,
    fetch_tickers,
    normalize_lang,
)
from .utils import get_logger, preview

PORTFOLIO_COLUMNS = {
    "Name",
    "ISIN",
    "quantity",
    "price",
    "avgCost",
    "netValue",
}


class Portfolio:
    def __init__(
        self,
        tr,
        include_watchlist: bool = False,
        instruments_to_ignore: Optional[list[str]] = None,
        output=None,
        lang: str = "en",
        decimal_localization: bool = False,
        sort_by_column: Optional[str] = "netValue",
        sort_descending: bool = True,
    ):
        self.tr = tr
        self.include_watchlist = include_watchlist
        self.instruments_to_ignore = instruments_to_ignore or []
        self.output = output
        self.lang = normalize_lang(lang)
        self.decimal_localization = decimal_localization
        self.sort_by_column = sort_by_column
        self.sort_descending = sort_descending

        self.watchlist: list[dict] = []

        self._log = get_logger(__name__)

    def _decimal_format(self, value, precision: int = 2):
        return decimal_format(value, precision, self.decimal_localization, self.lang)

    async def portfolio_loop(self):
        self._log.info("Querying portfolio...")
        recv = 0
        await self.tr.compact_portfolio()
        recv += 1
        await self.tr.cash()
        recv += 1
        if self.include_watchlist:
            await self.tr.watchlist()
            recv += 1

        while recv > 0:
            subscription_id, subscription, response = await self.tr.recv()

            if subscription["type"] == "compactPortfolioByType":
                recv -= 1
                # New format: positions are grouped in categories[].positions
                # Flatten all categories and normalize the field name: new API uses
                # "isin" where the old "compactPortfolio" used "instrumentId".
                self.positions = []
                for cat in response.get("categories", []):
                    for pos in cat.get("positions", []):
                        if "isin" in pos and "instrumentId" not in pos:
                            pos["instrumentId"] = pos["isin"]
                        self.positions.append(pos)
            elif subscription["type"] == "cash":
                recv -= 1
                self.cash = response
            elif subscription["type"] == "watchlist":
                recv -= 1
                self.watchlist = response
            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

            await self.tr.unsubscribe(subscription_id)

        isins = set()
        positions = list()
        for pos in self.positions:
            if pos["instrumentId"] not in self.instruments_to_ignore:
                positions.append(pos)
                isins.add(pos["instrumentId"])
        self.positions = positions

        # extend portfolio with watchlist elements
        for pos in self.watchlist:
            if pos["instrumentId"] not in isins and pos["instrumentId"] not in self.instruments_to_ignore:
                isins.add(pos["instrumentId"])
                self.positions.append(pos)

        self._log.info("Subscribing to tickers...")
        await fetch_instrument_details(self.tr, self.positions)
        missing = await fetch_tickers(self.tr, self.positions)
        for pos in missing:
            print(
                f"Missing price for {pos.get('name', pos['instrumentId'])} ({pos['instrumentId']}), removing from result."
            )

        self.positions = [pos for pos in self.positions if "price" in pos]

        # Compute netValue from price and netSize (netSize comes from the portfolio, not tickers)
        for pos in self.positions:
            # watchlist positions don't have size/value
            if "netSize" not in pos:
                pos["netSize"] = "0"
                pos["averageBuyIn"] = pos["price"]
            pos["netValue"] = (Decimal(pos["price"]) * Decimal(pos["netSize"])).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

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
            case "quantity":
                return lambda x: Decimal(x["netSize"])
            case "price":
                return lambda x: Decimal(x["price"])
            case "avgCost":
                return lambda x: Decimal(x["averageBuyIn"])
            case "netValue":
                return lambda x: Decimal(x["netValue"])
            case _ as m:
                print(f"Column {m} does not exist for portfolio list, reverting to default sorting by netValue.")
                return lambda x: Decimal(x["netValue"])

    def write_csv(self):
        if self.output is None:
            return

        csv_lines = []
        for pos in sorted(self.positions, key=self._get_sort_func(), reverse=self.sort_descending):
            csv_lines.append(
                f"{pos['name']};"
                f"{pos['instrumentId']};"
                f"{self._decimal_format(pos['netSize'], precision=6)};"
                f"{self._decimal_format(pos['price'], precision=4)};"
                f"{self._decimal_format(pos['averageBuyIn'], precision=4)};"
                f"{self._decimal_format(pos['netValue'])}"
            )

        Path(self.output).parent.mkdir(parents=True, exist_ok=True)
        with open(self.output, "w", encoding="utf-8") as f:
            f.write("Name;ISIN;quantity;price;avgCost;netValue\n")
            f.write("\n".join(csv_lines) + ("\n" if csv_lines else ""))

        print(f"Wrote {len(csv_lines) + 1} lines to {self.output}")

    def overview(self):
        totalBuyCost = Decimal("0")
        totalNetValue = Decimal("0")

        if not self.output:
            print(
                "Name                      ISIN            avgCost *   quantity =    buyCost ->   netValue      price       diff   %-diff"
            )

        for pos in sorted(self.positions, key=self._get_sort_func(), reverse=self.sort_descending):
            buyCost = (Decimal(pos["averageBuyIn"]) * Decimal(pos["netSize"])).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            diff = pos["netValue"] - buyCost
            diffP = 0.0 if buyCost == 0 else ((pos["netValue"] / buyCost) - 1) * 100
            totalBuyCost = totalBuyCost + buyCost
            totalNetValue = totalNetValue + pos["netValue"]

            if not self.output:
                print(
                    f"{pos['name']:<25.25} "
                    f"{pos['instrumentId']} "
                    f"{Decimal(pos['averageBuyIn']):>10.2f} * "
                    f"{Decimal(pos['netSize']):>10.6f} = "
                    f"{buyCost:>10.2f} -> "
                    f"{pos['netValue']:>10.2f} "
                    f"{Decimal(pos['price']):>10.2f} "
                    f"{diff:>10.2f} "
                    f"{diffP:>7.1f}%"
                )

        if not self.output:
            print(
                "Name                      ISIN            avgCost *   quantity =    buyCost ->   netValue      price       diff   %-diff"
            )
            print()

        diff = totalNetValue - totalBuyCost
        diffP = 0.0 if totalBuyCost == 0 else ((totalNetValue / totalBuyCost) - 1) * 100
        cash = Decimal(self.cash[0]["amount"])
        print(f"Depot {totalBuyCost:>43.2f} -> {totalNetValue:>10.2f} {diff:>10.2f} {diffP:>7.1f}%")
        print(f"Cash {self.cash[0]['currencyId']} {cash:>40.2f}")
        print(f"Total {cash + totalBuyCost:>43.2f} -> {cash + totalNetValue:>10.2f}")

    def get(self):
        asyncio.run(self.portfolio_loop())

        self.overview()
        self.write_csv()
