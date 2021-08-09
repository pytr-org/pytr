import asyncio
from pytr.utils import preview


class Portfolio:
    def __init__(self, tr):
        self.tr = tr

    async def portfolio_loop(self):
        recv = 0
        await self.tr.portfolio()
        await self.tr.cash()
        # await self.tr.available_cash_for_payout()

        while True:
            _subscription_id, subscription, response = await self.tr.recv()

            if subscription['type'] == 'portfolio':
                recv += 1
                self.portfolio = response
            elif subscription['type'] == 'cash':
                recv += 1
                self.cash = response
            # elif subscription['type'] == 'availableCashForPayout':
            #     recv += 1
            #     self.payoutCash = response
            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

            if recv == 2:
                return

    def overview(self):
        for x in ['netValue', 'unrealisedProfit', 'unrealisedProfitPercent', 'unrealisedCost']:
            print(f'{x:24}: {self.portfolio[x]:>10.2f}')
        print()

        print('ISIN            avgCost *   quantity =    buyCost ->   netValue       diff   %-diff')
        totalBuyCost = 0.0
        totalNetValue = 0.0
        positions = self.portfolio['positions']
        for pos in sorted(positions, key=lambda x: x['netValue'], reverse=True):
            buyCost = pos['unrealisedAverageCost'] * pos['netSize']
            diff = pos['netValue'] - buyCost
            if buyCost == 0:
                diffP = 0.0
            else:
                diffP = ((pos['netValue'] / buyCost) - 1) * 100
            totalBuyCost += buyCost
            totalNetValue += pos['netValue']

            print(
                f"{pos['instrumentId']} {pos['unrealisedAverageCost']:>10.2f} * {pos['netSize']:>10.2f}"
                + f" = {buyCost:>10.2f} -> {pos['netValue']:>10.2f} {diff:>10.2f} {diffP:>7.1f}%"
            )

        print('ISIN            avgCost *   quantity =    buyCost ->   netValue       diff   %-diff')
        print()

        diff = totalNetValue - totalBuyCost
        if totalBuyCost == 0:
            diffP = 0.0
        else:
            diffP = ((totalNetValue / totalBuyCost) - 1) * 100
        print(f'Depot {totalBuyCost:>43.2f} -> {totalNetValue:>10.2f} {diff:>10.2f} {diffP:>7.1f}%')

        cash = self.cash[0]['amount']
        currency = self.cash[0]['currencyId']
        print(f'Cash {currency} {cash:>40.2f} -> {cash:>10.2f}')
        print(f'Total {cash+totalBuyCost:>43.2f} -> {cash+totalNetValue:>10.2f}')

    def get(self):
        asyncio.get_event_loop().run_until_complete(self.portfolio_loop())

        self.overview()
