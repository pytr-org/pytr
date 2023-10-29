import asyncio

from pytr.utils import preview


class Portfolio:
    def __init__(self, tr):
        self.tr = tr

    async def portfolio_loop(self):
        recv = 0
        # await self.tr.portfolio()
        # recv += 1
        await self.tr.compact_portfolio()
        recv += 1
        await self.tr.cash()
        recv += 1
        # await self.tr.available_cash_for_payout()
        # recv += 1

        while recv > 0:
            subscription_id, subscription, response = await self.tr.recv()

            if subscription['type'] == 'portfolio':
                recv -= 1
                self.portfolio = response
            elif subscription['type'] == 'compactPortfolio':
                recv -= 1
                self.portfolio = response
            elif subscription['type'] == 'cash':
                recv -= 1
                self.cash = response
            # elif subscription['type'] == 'availableCashForPayout':
            #     recv -= 1
            #     self.payoutCash = response
            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

            await self.tr.unsubscribe(subscription_id)

        # Populate netValue for each ISIN
        positions = self.portfolio['positions']
        subscriptions = {}
        for pos in sorted(positions, key=lambda x: x['netSize'], reverse=True):
            isin = pos['instrumentId']
            # subscription_id = await self.tr.instrument_details(pos['instrumentId'])
            subscription_id = await self.tr.ticker(isin, exchange='LSX')
            subscriptions[subscription_id] = pos

        while len(subscriptions) > 0:
            subscription_id, subscription, response = await self.tr.recv()

            if subscription['type'] == 'ticker':
                await self.tr.unsubscribe(subscription_id)
                pos = subscriptions[subscription_id]
                subscriptions.pop(subscription_id, None)
                pos['netValue'] = response['last']['price'] * pos['netSize']
            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

        # Populate name for each ISIN
        subscriptions = {}
        for pos in sorted(positions, key=lambda x: x['netSize'], reverse=True):
            isin = pos['instrumentId']
            subscription_id = await self.tr.instrument_details(pos['instrumentId'])
            subscriptions[subscription_id] = pos

        while len(subscriptions) > 0:
            subscription_id, subscription, response = await self.tr.recv()

            if subscription['type'] == 'instrument':
                await self.tr.unsubscribe(subscription_id)
                pos = subscriptions[subscription_id]
                subscriptions.pop(subscription_id, None)
                pos['name'] = response['shortName']
            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

    def overview(self):
        # for x in ['netValue', 'unrealisedProfit', 'unrealisedProfitPercent', 'unrealisedCost']:
        #     print(f'{x:24}: {self.portfolio[x]:>10.2f}')
        # print()

        print('Name                      ISIN            avgCost *   quantity =    buyCost ->   netValue       diff   %-diff')
        totalBuyCost = 0.0
        totalNetValue = 0.0
        positions = self.portfolio['positions']
        for pos in sorted(positions, key=lambda x: x['netSize'], reverse=True):
            # pos['netValue'] = 0 # TODO: Update the value from each Stock request
            buyCost = pos['averageBuyIn'] * pos['netSize']
            diff = pos['netValue'] - buyCost
            if buyCost == 0:
                diffP = 0.0
            else:
                diffP = ((pos['netValue'] / buyCost) - 1) * 100
            totalBuyCost += buyCost
            totalNetValue += pos['netValue']

            print(
                f"{pos['name']:<25} {pos['instrumentId']} {pos['averageBuyIn']:>10.2f} * {pos['netSize']:>10.2f}"
                + f" = {buyCost:>10.2f} -> {pos['netValue']:>10.2f} {diff:>10.2f} {diffP:>7.1f}%"
            )

        print('Name                      ISIN            avgCost *   quantity =    buyCost ->   netValue       diff   %-diff')
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
