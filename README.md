# Trade Republic API

This is a library for the private API of the Trade Republic online brokerage. I am not affiliated with Trade Republic Bank GmbH.

## Installation

```
pip install py-tr
```

## Authentication

First you need to perform a device reset - a private key will be generated that pins your "device". The private key is saved to your keyfile. This procedure will log you out from your mobile device.

```python
from py_tr import TradeRepublicApi
tr = TradeRepublicApi(phone_no="+4900000000000", pin="0000", keyfile='keyfile.pem')
tr.initiate_device_reset()
tr.complete_device_reset("0000") # Substitute the 2FA token that is sent to you via SMS.
```

## Api Subscriptions

The Trade Republic API works fully asynchronously via Websocket. You subscribe to a 'topic', by sending a request using the `tr.subscribe(payload)` call (or any of the helper methods provided by the library). This will return a `subscription_id`, that you can use to identify responses belonging to this subscription. 

After subscribing you will get one initial response on that subscription and an update whenever the response changes. E.g. market data subscriptions can update multiple times per second, but also the portfolio or watchlist subscriptions will receive an update if the positions change. 

To receive the next response on the websocket, call `tr.recv()`. This will return a tuple consisting of 
1. the `subscription_id` that this response belongs to
1. a dictionary that contains all the subscription parameters
1. the response dictionary

If the Api replies with an error, a `TradeRepublicError` (also containing all three values) will be raised.

To unsubscribe from a topic, call `tr.unsubscribe(subscription_id)`.

The library does bookkeeping on current subscriptions in the `tr.subscriptions` dictionary, mapping `subscription_id` to a dictionary of the subscription parameters. 

Sample code:

```python
import asyncio
from py_tr import TradeRepublicApi

tr = TradeRepublicApi(phone_no="+4900000000000", pin="0000", keyfile='keyfile.pem')

async def my_loop():
    cash_subscription_id = await tr.cash()
    await tr.ticker("DE0007236101", "LSX")
    await tr.ticker("DE0007100000", "LSX")

    while True:
        subscription_id, subscription, response = await tr.recv()

        # Identify response by subscription_id:
        if cash_subscription_id == subscription_id:
            print(f"Cash balance is {response}")

        # Or identify response by subscription type:
        if subscription["type"] == "ticker":
            print(f"Current tick for {subscription['id']} is {response}")

asyncio.get_event_loop().run_until_complete(my_loop())
```

## Blocking Api Calls

For convenience the library provides a helper function that communicates in a blocking manner:

```python
portfolio = tr.run_blocking(tr.portfolio(), timeout=5.0)
```

This will subscribe to a topic, return the first response and immediately unsubscribe. If no response is returned this 
will time out after a default of five seconds. Warning: `tr.run_blocking()` will silently drop all messages belonging to different subscriptions, therefore do not use both approaches at the same time.

## All Subscriptions

The following subscriptions are supported by this library:

### Portfolio
```python
tr.portfolio()
tr.cash()
tr.available_cash_for_payout()
tr.portfolio_status()
tr.portfolio_history(timeframe)
tr.experience()
```
### Watchlist
```python
tr.watchlist()
tr.add_watchlist(isin)
tr.remove_watchlist(isin)
```
### Market Data
```python
tr.instrument_details(isin)
tr.instrument_suitability(isin)
tr.stock_details(isin)
tr.ticker(isin, exchange="LSX")
tr.performance(isin, exchange="LSX")
tr.performance_history(isin, timeframe, exchange="LSX", resolution=None)
```
### Timeline
```python
tr.timeline(after=None)
tr.timeline_detail(timeline_id)
tr.timeline_detail_order(order_id)
tr.timeline_detail_savings_plan(savings_plan_id)
```
### Search
```python
tr.search_tags()
tr.search_suggested_tags(query)
tr.search(query, asset_type="stock", page=1, page_size=20, aggregate=False, only_savable=False,
              filter_index=None, filter_country=None, filter_sector=None, filter_region=None)
tr.search_derivative(underlying_isin, product_type)
```
### Orders

Be careful, these methods can create actual live trades.

```python
tr.order_overview()
tr.cash_available_for_order()
tr.size_available_for_order(isin, exchange)
tr.price_for_order(isin, exchange, order_type)
tr.market_order(isin, exchange, order_type, size, expiry, sell_fractions, expiry_date=None, warnings_shown=None)
tr.limit_order(isin, exchange, order_type, size, limit, expiry, expiry_date=None, warnings_shown=None)
tr.stop_market_order(isin, exchange, order_type, size, stop, expiry, expiry_date=None, warnings_shown=None)
tr.cancel_order(order_id)
```
### Savings Plans
```python
tr.savings_plan_overview()
tr.savings_plan_parameters(isin)
tr.create_savings_plan(isin, amount, interval, start_date, start_date_type, start_date_value)
tr.change_savings_plan(savings_plan_id, isin, amount, interval, start_date, start_date_type, start_date_value)
tr.cancel_savings_plan(savings_plan_id)
```
### Price Alarms
```python
tr.price_alarm_overview()
tr.create_price_alarm(isin, price)
tr.cancel_price_alarm(price_alarm_id)
```
### News
```python
tr.news(isin)
tr.news_subscriptions()
tr.subscribe_news(isin)
tr.unsubscribe_news(isin)
```
### Other
```python
tr.motd()
tr.neon_cards()
```
### REST calls
These Api calls are not asynchronous, but plain old rest calls. 
```python
tr.settings()
tr.order_cost(isin, exchange, order_mode, order_type, size, sell_fractions)
tr.savings_plan_cost(isin, amount, interval)
tr.payout(amount)
tr.confirm_payout(process_id, code)
```
Payouts need two-factor-authentication: the `payout()` call will respond with a process_id and trigger an SMS with a code. Confirm the payout by calling `confirm_payout()` with the process_id and code.

### Parameters
* **isin** `string`: the *International Securities Identification Number* 
* **timeframe** `string`: allowed values are `"1d"`, `"5d"`, `"1m"`, `"3m"`, `"6m"`, `"1y"`, `"5y"`, `"max"` 
* **exchange** `string`: identifies a stock exchange, usually `"LSX"` for *Lang & Schwarz Exchange*, other allowed values can be seen in the `instrument_details()` call 
* **resolution** `int` (optional): resolution for timeseries in milliseconds, minimum seems to be 60,000 
* **asset_type** `string`: allowed values are `"stock"`, `"fund"`, `"derivative"`
* **order_type** `string`: allowed values are `"buy"` or `"sell"` 
* **size** `int`: how many shares to trade 
* **sell_fractions** `bool`: sell remaining fractional shares
* **limit** `float`: limit price 
* **stop** `float`: stop price 
* **expiry** `string`: allowed values are `"gfd"` (good for day), `"gtd"` (good till date) and `"gtc"` (good till cancelled)
* **expiry_date** `string` (optional): if expiry is `"gtd"`, specify a date in the format `"yyyy-mm-dd"`
* **warnings_shown** `list of strings` (optional): may contain one or more of the following values: `"targetMarket"`, `"userExperience"`, `"unknown"` - however an empty list also seems to always be accepted
* **amount** `int` savings plan amount in euro
* **interval** `string` interval for savings plan execution, allowed values are `"everySecondWeek"`, `"weekly"`, `"twoPerMonth"`, `"monthly"`, `"quarterly"`
* **start_date** `string` first execution date for savings plans, in format `"yyyy-mm-dd"`
* **start_date_type** `string` allowed values are `"dayOfMonth"`, `"weekday"`
* **start_date_value** `int` either the day of month (0-30) on which to execute the savings plan, or the weekday (0-6)

Allowed values for search filters can be found using the `search_tags()` call.
