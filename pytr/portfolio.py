import asyncio

from pytr.utils import preview


class Portfolio:
    def __init__(self, tr):
        self.tr = tr

    async def portfolio_loop(self):
        recv = 0
        await self.tr.compact_portfolio()
        recv += 1
        await self.tr.cash()
        recv += 1

        while recv > 0:
            subscription_id, subscription, response = await self.tr.recv()

            if subscription["type"] == "portfolio":
                recv -= 1
                self.portfolio = response
            elif subscription["type"] == "compactPortfolio":
                recv -= 1
                self.portfolio = response
            elif subscription["type"] == "cash":
                recv -= 1
                self.cash = response
            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

            await self.tr.unsubscribe(subscription_id)

        # Populate name for each ISIN
        subscriptions = {}
        positions = self.portfolio["positions"]
        for pos in sorted(positions, key=lambda x: x["netSize"], reverse=True):
            isin = pos["instrumentId"]
            subscription_id = await self.tr.instrument_details(pos["instrumentId"])
            subscriptions[subscription_id] = pos

        while len(subscriptions) > 0:
            subscription_id, subscription, response = await self.tr.recv()

            if subscription["type"] == "instrument":
                await self.tr.unsubscribe(subscription_id)
                pos = subscriptions.pop(subscription_id)
                pos["name"] = response["shortName"]
                pos["exchangeIds"] = response["exchangeIds"]
            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

        # Populate netValue for each ISIN
        subscriptions = {}
        for pos in sorted(positions, key=lambda x: x["netSize"], reverse=True):
            isin = pos["instrumentId"]
            if len(pos["exchangeIds"]) > 0:
                subscription_id = await self.tr.ticker(isin, exchange=pos["exchangeIds"][0])
                subscriptions[subscription_id] = pos
            else:
                pos["netValue"] = float(pos["averageBuyIn"]) * float(pos["netSize"])

        while len(subscriptions) > 0:
            subscription_id, subscription, response = await self.tr.recv()

            if subscription["type"] == "ticker":
                await self.tr.unsubscribe(subscription_id)
                pos = subscriptions.pop(subscription_id)
                pos["netValue"] = float(response["last"]["price"]) * float(pos["netSize"])
            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

    def portfolio_to_csv(self, output_path):
        positions = self.portfolio["positions"]
        csv_lines = []
        for pos in sorted(positions, key=lambda x: x["netSize"], reverse=True):
            csv_lines.append(
                f"{pos['name']};{pos['instrumentId']};{pos['netSize']};{pos['averageBuyIn']};{float(pos['netValue']):.2f}"
            )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Name;ISIN;quantity;avgCost;netValue\n")
            f.write("\n".join(csv_lines) + ("\n" if csv_lines else ""))

        print(f"Wrote {len(csv_lines) + 1} lines to {output_path}")

    def overview(self):
        print(
            "Name                      ISIN            avgCost *   quantity =    buyCost ->   netValue       diff   %-diff"
        )
        totalBuyCost = 0.0
        totalNetValue = 0.0
        positions = self.portfolio["positions"]
        for pos in sorted(positions, key=lambda x: x["netSize"], reverse=True):
            buyCost = float(pos["averageBuyIn"]) * float(pos["netSize"])
            diff = float(pos["netValue"]) - buyCost
            if buyCost == 0:
                diffP = 0.0
            else:
                diffP = ((pos["netValue"] / buyCost) - 1) * 100
            totalBuyCost += buyCost
            totalNetValue += float(pos["netValue"])

            print(
                f"{pos['name']:<25.25} {pos['instrumentId']} {float(pos['averageBuyIn']):>10.2f} * {float(pos['netSize']):>10.3f}"
                + f" = {float(buyCost):>10.2f} -> {float(pos['netValue']):>10.2f} {diff:>10.2f} {diffP:>7.1f}%"
            )

        print(
            "Name                      ISIN            avgCost *   quantity =    buyCost ->   netValue       diff   %-diff"
        )
        print()

        diff = totalNetValue - totalBuyCost
        if totalBuyCost == 0:
            diffP = 0.0
        else:
            diffP = ((totalNetValue / totalBuyCost) - 1) * 100
        print(f"Depot {totalBuyCost:>43.2f} -> {totalNetValue:>10.2f} {diff:>10.2f} {diffP:>7.1f}%")

        cash = float(self.cash[0]["amount"])
        currency = self.cash[0]["currencyId"]
        print(f"Cash {currency} {cash:>40.2f} -> {cash:>10.2f}")
        print(f"Total {cash + totalBuyCost:>43.2f} -> {cash + totalNetValue:>10.2f}")

    def get(self):
        asyncio.get_event_loop().run_until_complete(self.portfolio_loop())

        self.overview()
