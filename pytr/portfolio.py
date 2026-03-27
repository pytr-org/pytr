import asyncio
import locale
import re
from decimal import ROUND_HALF_UP, Decimal
from locale import getdefaultlocale
from pathlib import Path
from typing import Optional, Union

from babel.numbers import format_decimal

from .utils import get_logger, preview

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

PORTFOLIO_COLUMNS = {
    "Name",
    "ISIN",
    "quantity",
    "price",
    "avgCost",
    "netValue",
}

bond_pattern = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December|Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\.?\s+20\d{2}",
    re.IGNORECASE,
)


class Portfolio:
    def __init__(
        self,
        tr,
        include_watchlist=False,
        lang="en",
        decimal_localization=False,
        output=None,
        sort_by_column=None,
        sort_descending=True,
    ):
        self.tr = tr
        self.include_watchlist = include_watchlist
        self.lang = lang
        self.decimal_localization = decimal_localization
        self.output = output
        self.sort_by_column = sort_by_column
        self.sort_descending = sort_descending

        self.watchlist = None

        self._log = get_logger(__name__)

        if self.lang == "auto":
            locale = getdefaultlocale()[0]
            if locale is None:
                self.lang = "en"
            else:
                self.lang = locale.split("_")[0]

        if self.lang not in SUPPORTED_LANGUAGES:
            self._log.info(f'Language not yet supported "{self.lang}", defaulting to "en"')
            self.lang = "en"

    def _decimal_format(self, value: Optional[float], precision: int = 2) -> Union[str, None]:
        if value is None:
            return None
        if self.decimal_localization:
            format = "#,##0." + ("#" * precision)
            return format_decimal(value, format=format, locale=self.lang)
        else:
            return f"{float(value):.{precision}f}".rstrip("0").rstrip(".")

    async def portfolio_loop(self):
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

            if subscription["type"] == "compactPortfolio":
                recv -= 1
                self.portfolio = response["positions"]
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
        for pos in self.portfolio:
            isins.add(pos["instrumentId"])

        # extend portfolio with watchlist elements
        if self.watchlist:
            for pos in self.watchlist:
                isin = pos["instrumentId"]
                if isin not in isins:
                    isins.add(isin)
                    self.portfolio.append(pos)

        # Populate name for each ISIN
        subscriptions = {}
        for pos in self.portfolio:
            isin = pos["instrumentId"]
            subscription_id = await self.tr.instrument_details(isin)
            subscriptions[subscription_id] = pos

        while len(subscriptions) > 0:
            subscription_id, subscription, response = await self.tr.recv()

            if subscription["type"] == "instrument":
                await self.tr.unsubscribe(subscription_id)
                pos = subscriptions.pop(subscription_id, None)
                pos["name"] = response["shortName"]
                pos["exchangeIds"] = response["exchangeIds"]
            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

        # Get tickers and populate netValue for each ISIN
        self._log.info("Subscribing to tickers...")
        subscriptions = {}
        for pos in self.portfolio:
            isin = pos["instrumentId"]
            if len(pos["exchangeIds"]) > 0:
                subscription_id = await self.tr.ticker(isin, exchange=pos["exchangeIds"][0])
                subscriptions[subscription_id] = pos

        self._log.info("Waiting for tickers...")
        while len(subscriptions) > 0:
            try:
                subscription_id, subscription, response = await asyncio.wait_for(self.tr.recv(), 5)
            except asyncio.TimeoutError:
                print("Timed out waiting for tickers")
                print(f"Remaining subscriptions: {subscriptions}")
                break

            if subscription["type"] == "ticker":
                await self.tr.unsubscribe(subscription_id)
                pos = subscriptions.pop(subscription_id, None)
                pos["price"] = response["last"]["price"]
                # Bond handling
                # Identify bonds by parsing the name - bond names are like "... month year"
                if bond_pattern.search(pos["name"]):
                    # Bond prices are per €100 face value
                    pos["price"] = Decimal(pos["price"]) / 100

                # watchlist positions don't have size/value
                if "netSize" not in pos:
                    pos["netSize"] = "0"
                    pos["averageBuyIn"] = pos["price"]
                pos["netValue"] = (Decimal(pos["price"]) * Decimal(pos["netSize"])).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

        # sanitize - it can happen that we get no price, e.g. we ran into a timeout above or some instrument
        # does not deliver a price. Then we kick it out of the list and log this.
        portfolionew = []
        for pos in self.portfolio:
            if "price" not in pos:
                print(f"Missing price for {pos['name']} ({pos['instrumentId']}), removing from result.")
            else:
                portfolionew.append(pos)
        self.portfolio = portfolionew

    def _get_sort_func(self):
        if self.sort_by_column:
            match self.sort_by_column.lower():
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
        else:
            return lambda x: Decimal(x["netValue"])

    def portfolio_to_csv(self):
        if self.output is None:
            return

        csv_lines = []
        for pos in sorted(self.portfolio, key=self._get_sort_func(), reverse=self.sort_descending):
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

        for pos in sorted(self.portfolio, key=self._get_sort_func(), reverse=self.sort_descending):
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
        self.portfolio_to_csv()
