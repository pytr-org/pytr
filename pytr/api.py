# MIT License

# Copyright (c) 2020 nborrmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import asyncio
import base64
import hashlib
import json
import pathlib
import ssl
import time
import urllib.parse
import uuid
from http.cookiejar import MozillaCookieJar
from typing import Any, Dict

import certifi
import requests
import websockets
from ecdsa import NIST256p, SigningKey  # type: ignore[import-untyped]
from ecdsa.util import sigencode_der  # type: ignore[import-untyped]

from pytr.utils import get_logger

home = pathlib.Path.home()
BASE_DIR = home / ".pytr"
CREDENTIALS_FILE = BASE_DIR / "credentials"
KEY_FILE = BASE_DIR / "keyfile.pem"
COOKIES_FILE = BASE_DIR / "cookies.txt"


class TradeRepublicApi:
    _default_headers = {"User-Agent": "TradeRepublic/Android 30/App Version 1.1.5534"}
    _default_headers_web = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36"
    }
    _host = "https://api.traderepublic.com"
    _weblogin = False

    _refresh_token = None
    _session_token = None
    _session_token_expires_at = None
    _process_id = None
    _web_session_token_expires_at = 0

    _ws = None
    _lock = asyncio.Lock()
    _subscription_id_counter = 1
    _previous_responses: Dict[str, str] = {}
    subscriptions: Dict[str, Dict[str, Any]] = {}

    _credentials_file = CREDENTIALS_FILE
    _cookies_file = COOKIES_FILE

    @property
    def session_token(self):
        if not self._refresh_token:
            self.login()
        elif self._refresh_token and time.time() > self._session_token_expires_at:
            self.refresh_access_token()
        return self._session_token

    @session_token.setter
    def session_token(self, val):
        self._session_token_expires_at = time.time() + 290
        self._session_token = val

    def __init__(
        self,
        phone_no=None,
        pin=None,
        keyfile=None,
        locale="de",
        save_cookies=False,
        credentials_file=None,
        cookies_file=None,
    ):
        self.log = get_logger(__name__)
        self._locale = locale
        self._save_cookies = save_cookies

        self._credentials_file = pathlib.Path(credentials_file) if credentials_file else CREDENTIALS_FILE

        if not (phone_no and pin):
            try:
                with open(self._credentials_file, "r") as f:
                    lines = f.readlines()
                self.phone_no = lines[0].strip()
                self.pin = lines[1].strip()
            except FileNotFoundError:
                raise ValueError(f"phone_no and pin must be specified explicitly or via {self._credentials_file}")
        else:
            self.phone_no = phone_no
            self.pin = pin

        self._cookies_file = pathlib.Path(cookies_file) if cookies_file else BASE_DIR / f"cookies.{self.phone_no}.txt"

        self.keyfile = keyfile if keyfile else KEY_FILE
        try:
            with open(self.keyfile, "rb") as f:
                self.sk = SigningKey.from_pem(f.read(), hashfunc=hashlib.sha512)
        except FileNotFoundError:
            pass

        self._websession = requests.Session()
        self._websession.headers = self._default_headers_web
        if self._save_cookies:
            self._websession.cookies = MozillaCookieJar(self._cookies_file)

    def initiate_device_reset(self):
        self.sk = SigningKey.generate(curve=NIST256p, hashfunc=hashlib.sha512)

        r = requests.post(
            f"{self._host}/api/v1/auth/account/reset/device",
            json={"phoneNumber": self.phone_no, "pin": self.pin},
            headers=self._default_headers,
        )

        self._process_id = r.json()["processId"]

    def complete_device_reset(self, token):
        if not self._process_id and not self.sk:
            raise ValueError("Initiate Device Reset first.")

        pubkey_bytes = self.sk.get_verifying_key().to_string("uncompressed")
        pubkey_string = base64.b64encode(pubkey_bytes).decode("ascii")

        r = requests.post(
            f"{self._host}/api/v1/auth/account/reset/device/{self._process_id}/key",
            json={"code": token, "deviceKey": pubkey_string},
            headers=self._default_headers,
        )
        if r.status_code == 200:
            with open(self.keyfile, "wb") as f:
                f.write(self.sk.to_pem())

    def login(self):
        self.log.info("Logging in")
        r = self._sign_request(
            "/api/v1/auth/login",
            payload={"phoneNumber": self.phone_no, "pin": self.pin},
        )
        self._refresh_token = r.json()["refreshToken"]
        self.session_token = r.json()["sessionToken"]

    def refresh_access_token(self):
        self.log.info("Refreshing access token")
        r = self._sign_request("/api/v1/auth/session", method="GET")
        self.session_token = r.json()["sessionToken"]
        self.save_websession()

    def _sign_request(self, url_path, payload=None, method="POST"):
        ts = int(time.time() * 1000)
        payload_string = json.dumps(payload) if payload else ""
        signature_payload = f"{ts}.{payload_string}"
        signature = self.sk.sign(
            bytes(signature_payload, "utf-8"),
            hashfunc=hashlib.sha512,
            sigencode=sigencode_der,
        )
        signature_string = base64.b64encode(signature).decode("ascii")

        headers = self._default_headers.copy()
        headers["X-Zeta-Timestamp"] = str(ts)
        headers["X-Zeta-Signature"] = signature_string
        headers["Content-Type"] = "application/json"

        if url_path == "/api/v1/auth/login":
            pass
        elif url_path == "/api/v1/auth/session":
            headers["Authorization"] = f"Bearer {self._refresh_token}"
        elif self.session_token:
            headers["Authorization"] = f"Bearer {self.session_token}"

        return requests.request(
            method=method,
            url=f"{self._host}{url_path}",
            data=payload_string,
            headers=headers,
        )

    def initiate_weblogin(self):
        r = self._websession.post(
            f"{self._host}/api/v1/auth/web/login",
            json={"phoneNumber": self.phone_no, "pin": self.pin},
        )
        j = r.json()
        try:
            self._process_id = j["processId"]
        except KeyError:
            err = j.get("errors")
            if err:
                raise ValueError(str(err))
            else:
                raise ValueError("processId not in reponse")
        return int(j["countdownInSeconds"]) + 1

    def resend_weblogin(self):
        r = self._websession.post(
            f"{self._host}/api/v1/auth/web/login/{self._process_id}/resend",
            headers=self._default_headers,
        )
        r.raise_for_status()

    def complete_weblogin(self, verify_code):
        if not self._process_id and not self._websession:
            raise ValueError("Initiate web login first.")

        r = self._websession.post(f"{self._host}/api/v1/auth/web/login/{self._process_id}/{verify_code}")
        r.raise_for_status()
        self.save_websession()
        self._weblogin = True

    def save_websession(self):
        # Saves session cookies too (expirydate=0).
        if self._save_cookies:
            self._websession.cookies.save(ignore_discard=True, ignore_expires=True)

    def resume_websession(self):
        """
        Use saved cookie file to resume web session
        return success
        """
        if self._save_cookies is False:
            return False

        # Only attempt to load if the cookie file exists.
        if self._cookies_file.exists():
            # Loads session cookies too (expirydate=0).
            self._websession.cookies.load(ignore_discard=True, ignore_expires=True)
            self._weblogin = True
            try:
                self.settings()
            except requests.exceptions.HTTPError:
                return False
                self._weblogin = False
            else:
                return True
        return False

    def _web_request(self, url_path, payload=None, method="GET"):
        if self._web_session_token_expires_at < time.time():
            r = self._websession.get(f"{self._host}/api/v1/auth/web/session")
            r.raise_for_status()
            self._web_session_token_expires_at = time.time() + 290
        return self._websession.request(method=method, url=f"{self._host}{url_path}", data=payload)

    async def _get_ws(self):
        if self._ws and self._ws.close_code is None:
            return self._ws

        self.log.info("Connecting to websocket...")
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        extra_headers = None
        connection_message = {"locale": self._locale}
        connect_id = 21

        if self._weblogin:
            # authenticate with cookies, set different connection message and connect ID
            cookie_str = ""
            for cookie in self._websession.cookies:
                if cookie.domain.endswith("traderepublic.com"):
                    cookie_str += f"{cookie.name}={cookie.value}; "
            extra_headers = {"Cookie": cookie_str.rstrip("; ")}

            connection_message = {
                "locale": self._locale,
                "platformId": "webtrading",
                "platformVersion": "chrome - 94.0.4606",
                "clientId": "app.traderepublic.com",
                "clientVersion": "5582",
            }
            connect_id = 31

        self._ws = await websockets.connect(
            "wss://api.traderepublic.com", ssl=ssl_context, additional_headers=extra_headers
        )
        await self._ws.send(f"connect {connect_id} {json.dumps(connection_message)}")
        response = await self._ws.recv()

        if not response == "connected":
            raise ValueError(f"Connection Error: {response}")

        self.log.info("Connected to websocket...")

        return self._ws

    async def _next_subscription_id(self):
        async with self._lock:
            subscription_id = self._subscription_id_counter
            self._subscription_id_counter += 1
            return str(subscription_id)

    async def subscribe(self, payload):
        subscription_id = await self._next_subscription_id()
        ws = await self._get_ws()
        self.log.debug(f"Subscribing: 'sub {subscription_id} {json.dumps(payload)}'")
        self.subscriptions[subscription_id] = payload

        payload_with_token = payload.copy()
        if not self._weblogin:
            payload_with_token["token"] = self.session_token

        await ws.send(f"sub {subscription_id} {json.dumps(payload_with_token)}")
        return subscription_id

    async def unsubscribe(self, subscription_id):
        ws = await self._get_ws()

        self.log.debug(f"Unsubscribing: {subscription_id}")
        await ws.send(f"unsub {subscription_id}")

        self.subscriptions.pop(subscription_id, None)
        self._previous_responses.pop(subscription_id, None)

    async def recv(self):
        ws = await self._get_ws()
        while True:
            response = await ws.recv()
            self.log.debug(f"Received message: {response!r}")

            subscription_id = response[: response.find(" ")]
            code = response[response.find(" ") + 1 : response.find(" ") + 2]
            payload_str = response[response.find(" ") + 2 :].lstrip()

            if subscription_id not in self.subscriptions:
                if code != "C":
                    self.log.debug(f"No active subscription for id {subscription_id}, dropping message")
                continue
            subscription = self.subscriptions[subscription_id]

            if code == "A":
                self._previous_responses[subscription_id] = payload_str
                payload = json.loads(payload_str) if payload_str else {}
                return subscription_id, subscription, payload

            elif code == "D":
                response = self._calculate_delta(subscription_id, payload_str)
                self.log.debug(f"Payload is {response}")

                self._previous_responses[subscription_id] = response
                return subscription_id, subscription, json.loads(response)

            if code == "C":
                self.subscriptions.pop(subscription_id, None)
                self._previous_responses.pop(subscription_id, None)
                continue

            elif code == "E":
                self.log.error(f"Received error message: {response!r}")

                await self.unsubscribe(subscription_id)

                payload = json.loads(payload_str) if payload_str else {}
                raise TradeRepublicError(subscription_id, subscription, payload)

    def _calculate_delta(self, subscription_id, delta_payload):
        previous_response = self._previous_responses[subscription_id]
        i, result = 0, []
        for diff in delta_payload.split("\t"):
            sign = diff[0]
            if sign == "+":
                result.append(urllib.parse.unquote_plus(diff).strip())
            elif sign == "-" or sign == "=":
                if sign == "=":
                    result.append(previous_response[i : i + int(diff[1:])])
                i += int(diff[1:])
        return "".join(result)

    async def _recv_subscription(self, subscription_id):
        while True:
            response_subscription_id, _, response = await self.recv()
            if response_subscription_id == subscription_id:
                return response

    async def _receive_one(self, fut, timeout):
        subscription_id = await fut

        try:
            return await asyncio.wait_for(self._recv_subscription(subscription_id), timeout)
        finally:
            await self.unsubscribe(subscription_id)

    def run_blocking(self, fut, timeout=5.0):
        return asyncio.run(self._receive_one(fut, timeout=timeout))

    async def portfolio(self):
        return await self.subscribe({"type": "portfolio"})

    async def portfolio_status(self):
        return await self.subscribe({"type": "portfolioStatus"})

    async def compact_portfolio(self):
        return await self.subscribe({"type": "compactPortfolio"})

    async def watchlist(self):
        return await self.subscribe({"type": "watchlist"})

    async def cash(self):
        return await self.subscribe({"type": "cash"})

    async def available_cash_for_payout(self):
        return await self.subscribe({"type": "availableCashForPayout"})

    async def portfolio_history(self, timeframe):
        return await self.subscribe({"type": "portfolioAggregateHistory", "range": timeframe})

    async def instrument_details(self, isin):
        return await self.subscribe({"type": "instrument", "id": isin})

    async def instrument_suitability(self, isin):
        return await self.subscribe({"type": "instrumentSuitability", "instrumentId": isin})

    async def stock_details(self, isin):
        return await self.subscribe({"type": "stockDetails", "id": isin})

    async def add_watchlist(self, isin):
        return await self.subscribe({"type": "addToWatchlist", "instrumentId": isin})

    async def remove_watchlist(self, isin):
        return await self.subscribe({"type": "removeFromWatchlist", "instrumentId": isin})

    async def ticker(self, isin, exchange="LSX"):
        return await self.subscribe({"type": "ticker", "id": f"{isin}.{exchange}"})

    async def performance(self, isin, exchange="LSX"):
        return await self.subscribe({"type": "performance", "id": f"{isin}.{exchange}"})

    async def performance_history(self, isin, timeframe, exchange="LSX", resolution=None):
        parameters = {
            "type": "aggregateHistory",
            "id": f"{isin}.{exchange}",
            "range": timeframe,
        }
        if resolution:
            parameters["resolution"] = resolution
        return await self.subscribe(parameters)

    async def experience(self):
        return await self.subscribe({"type": "experience"})

    async def motd(self):
        return await self.subscribe({"type": "messageOfTheDay"})

    async def neon_cards(self):
        return await self.subscribe({"type": "neonCards"})

    async def timeline(self, after=None):
        return await self.subscribe({"type": "timeline", "after": after})

    async def timeline_detail(self, timeline_id):
        return await self.subscribe({"type": "timelineDetail", "id": timeline_id})

    async def timeline_detail_order(self, order_id):
        return await self.subscribe({"type": "timelineDetail", "orderId": order_id})

    async def timeline_detail_savings_plan(self, savings_plan_id):
        return await self.subscribe({"type": "timelineDetail", "savingsPlanId": savings_plan_id})

    async def timeline_transactions(self, after=None):
        return await self.subscribe({"type": "timelineTransactions", "after": after})

    async def timeline_activity_log(self, after=None):
        return await self.subscribe({"type": "timelineActivityLog", "after": after})

    async def timeline_detail_v2(self, timeline_id):
        return await self.subscribe({"type": "timelineDetailV2", "id": timeline_id})

    async def search_tags(self):
        return await self.subscribe({"type": "neonSearchTags"})

    async def search_suggested_tags(self, query):
        return await self.subscribe({"type": "neonSearchSuggestedTags", "data": {"q": query}})

    async def search(
        self,
        query,
        asset_type="stock",
        page=1,
        page_size=20,
        aggregate=False,
        only_savable=False,
        filter_index=None,
        filter_country=None,
        filter_sector=None,
        filter_region=None,
    ):
        search_parameters = {
            "q": query,
            "filter": [{"key": "type", "value": asset_type}],
            "page": page,
            "pageSize": page_size,
        }
        if only_savable:
            search_parameters["filter"].append({"key": "attribute", "value": "savable"})
        if filter_index:
            search_parameters["filter"].append({"key": "index", "value": filter_index})
        if filter_country:
            search_parameters["filter"].append({"key": "country", "value": filter_country})
        if filter_region:
            search_parameters["filter"].append({"key": "region", "value": filter_region})
        if filter_sector:
            search_parameters["filter"].append({"key": "sector", "value": filter_sector})

        search_type = "neonSearch" if not aggregate else "neonSearchAggregations"
        return await self.subscribe({"type": search_type, "data": search_parameters})

    async def search_derivative(self, underlying_isin, product_type):
        return await self.subscribe(
            {
                "type": "derivatives",
                "underlying": underlying_isin,
                "productCategory": product_type,
            }
        )

    async def order_overview(self):
        return await self.subscribe({"type": "orders"})

    async def price_for_order(self, isin, exchange, order_type):
        return await self.subscribe(
            {
                "type": "priceForOrder",
                "parameters": {
                    "exchangeId": exchange,
                    "instrumentId": isin,
                    "type": order_type,
                },
            }
        )

    async def cash_available_for_order(self):
        return await self.subscribe({"type": "availableCash"})

    async def size_available_for_order(self, isin, exchange):
        return await self.subscribe(
            {
                "type": "availableSize",
                "parameters": {"exchangeId": exchange, "instrumentId": isin},
            }
        )

    async def limit_order(
        self,
        isin,
        exchange,
        order_type,
        size,
        limit,
        expiry,
        expiry_date=None,
        warnings_shown=None,
    ):
        parameters = {
            "type": "simpleCreateOrder",
            "clientProcessId": str(uuid.uuid4()),
            "warningsShown": warnings_shown if warnings_shown else [],
            "parameters": {
                "instrumentId": isin,
                "exchangeId": exchange,
                "expiry": {"type": expiry},
                "limit": limit,
                "mode": "limit",
                "size": size,
                "type": order_type,
            },
        }
        if expiry == "gtd" and expiry_date:
            parameters["parameters"]["expiry"]["value"] = expiry_date

        return await self.subscribe(parameters)

    async def market_order(
        self,
        isin,
        exchange,
        order_type,
        size,
        expiry,
        sell_fractions,
        expiry_date=None,
        warnings_shown=None,
    ):
        parameters = {
            "type": "simpleCreateOrder",
            "clientProcessId": str(uuid.uuid4()),
            "warningsShown": warnings_shown if warnings_shown else [],
            "parameters": {
                "instrumentId": isin,
                "exchangeId": exchange,
                "expiry": {"type": expiry},
                "mode": "market",
                "sellFractions": sell_fractions,
                "size": size,
                "type": order_type,
            },
        }
        if expiry == "gtd" and expiry_date:
            parameters["parameters"]["expiry"]["value"] = expiry_date

        return await self.subscribe(parameters)

    async def stop_market_order(
        self,
        isin,
        exchange,
        order_type,
        size,
        stop,
        expiry,
        expiry_date=None,
        warnings_shown=None,
    ):
        parameters = {
            "type": "simpleCreateOrder",
            "clientProcessId": str(uuid.uuid4()),
            "warningsShown": warnings_shown if warnings_shown else [],
            "parameters": {
                "instrumentId": isin,
                "exchangeId": exchange,
                "expiry": {"type": expiry},
                "mode": "stopMarket",
                "size": size,
                "stop": stop,
                "type": order_type,
            },
        }
        if expiry == "gtd" and expiry_date:
            parameters["parameters"]["expiry"]["value"] = expiry_date

        return await self.subscribe(parameters)

    async def cancel_order(self, order_id):
        return await self.subscribe({"type": "cancelOrder", "orderId": order_id})

    async def savings_plan_overview(self):
        return await self.subscribe({"type": "savingsPlans"})

    async def savings_plan_parameters(self, isin):
        return await self.subscribe({"type": "cancelSavingsPlan", "instrumentId": isin})

    async def create_savings_plan(
        self,
        isin,
        amount,
        interval,
        start_date,
        start_date_type,
        start_date_value,
        warnings_shown=None,
    ):
        parameters = {
            "type": "createSavingsPlan",
            "warningsShown": warnings_shown if warnings_shown else [],
            "parameters": {
                "amount": amount,
                "instrumentId": isin,
                "interval": interval,
                "startDate": {
                    "nextExecutionDate": start_date,
                    "type": start_date_type,
                    "value": start_date_value,
                },
            },
        }
        return await self.subscribe(parameters)

    async def change_savings_plan(
        self,
        savings_plan_id,
        isin,
        amount,
        interval,
        start_date,
        start_date_type,
        start_date_value,
        warnings_shown=None,
    ):
        parameters = {
            "id": savings_plan_id,
            "type": "createSavingsPlan",
            "warningsShown": warnings_shown if warnings_shown else [],
            "parameters": {
                "amount": amount,
                "instrumentId": isin,
                "interval": interval,
                "startDate": {
                    "nextExecutionDate": start_date,
                    "type": start_date_type,
                    "value": start_date_value,
                },
            },
        }
        return await self.subscribe(parameters)

    async def cancel_savings_plan(self, savings_plan_id):
        return await self.subscribe({"type": "cancelSavingsPlan", "id": savings_plan_id})

    async def price_alarm_overview(self):
        return await self.subscribe({"type": "priceAlarms"})

    async def create_price_alarm(self, isin, price):
        return await self.subscribe({"type": "createPriceAlarm", "instrumentId": isin, "targetPrice": price})

    async def cancel_price_alarm(self, price_alarm_id):
        return await self.subscribe({"type": "cancelPriceAlarm", "id": price_alarm_id})

    async def news(self, isin):
        return await self.subscribe({"type": "neonNews", "isin": isin})

    async def news_subscriptions(self):
        return await self.subscribe({"type": "newsSubscriptions"})

    async def subscribe_news(self, isin):
        return await self.subscribe({"type": "subscribeNews", "instrumentId": isin})

    async def unsubscribe_news(self, isin):
        return await self.subscribe({"type": "unsubscribeNews", "instrumentId": isin})

    def payout(self, amount):
        return self._sign_request("/api/v1/payout", {"amount": amount}).json()

    def confirm_payout(self, process_id, code):
        r = self._sign_request(f"/api/v1/payout/{process_id}/code", {"code": code})
        if r.status_code != 200:
            raise ValueError(f"Payout failed with response {r.text!r}")

    def settings(self):
        if self._weblogin:
            r = self._web_request("/api/v2/auth/account")
        else:
            r = self._sign_request("/api/v1/auth/account", method="GET")
        r.raise_for_status()
        return r.json()

    def order_cost(self, isin, exchange, order_mode, order_type, size, sell_fractions):
        url = (
            f"/api/v1/user/costtransparency?instrumentId={isin}&exchangeId={exchange}"
            f"&mode={order_mode}&type={order_type}&size={size}&sellFractions={sell_fractions}"
        )
        return self._sign_request(url, method="GET").text

    def savings_plan_cost(self, isin, amount, interval):
        url = f"/api/v1/user/savingsplancosttransparency?instrumentId={isin}&amount={amount}&interval={interval}"
        return self._sign_request(url, method="GET").text

    def __getattr__(self, name):
        if name[:9] == "blocking_":
            attr = object.__getattribute__(self, name[9:])
            if hasattr(attr, "__call__"):
                return lambda *args, **kwargs: self.run_blocking(
                    timeout=kwargs.pop("timeout", 5), fut=attr(*args, **kwargs)
                )
        return object.__getattribute__(self, name)


class TradeRepublicError(ValueError):
    def __init__(self, subscription_id, subscription, error_message):
        self.subscription_id = subscription_id
        self.subscription = subscription
        self.error = error_message
