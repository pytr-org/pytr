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
from typing import Any, Dict, Optional, Union

import certifi
import requests
import websockets
from ecdsa import NIST256p, SigningKey  # type: ignore[import-untyped]
from ecdsa.util import sigencode_der  # type: ignore[import-untyped]
from requests.cookies import RequestsCookieJar
from websockets.legacy.client import WebSocketClientProtocol

from pytr.utils import get_logger

home = pathlib.Path.home()
BASE_DIR = home / ".pytr"
CREDENTIALS_FILE = BASE_DIR / "credentials"
KEY_FILE = BASE_DIR / "keyfile.pem"
COOKIES_FILE = BASE_DIR / "cookies.txt"


class TradeRepublicApi:
    _default_headers: dict[str, str] = {"User-Agent": "TradeRepublic/Android 30/App Version 1.1.5534"}
    _default_headers_web: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36"
    }
    _host: str = "https://api.traderepublic.com"
    _weblogin: bool = False

    _refresh_token: Optional[str] = None
    _session_token: Optional[str] = None
    _session_token_expires_at: Optional[float] = None
    _process_id: Optional[str] = None
    _web_session_token_expires_at: float = 0.0

    _ws: Optional[websockets.WebSocketClientProtocol] = None
    _lock: asyncio.Lock = asyncio.Lock()
    _subscription_id_counter: int = 1
    _previous_responses: dict[str, str] = {}
    subscriptions: dict[str, dict[str, Any]] = {}

    _credentials_file: pathlib.Path = CREDENTIALS_FILE
    _cookies_file: pathlib.Path = COOKIES_FILE

    @property
    def session_token(self) -> Optional[str]:
        if not self._refresh_token:
            self.login()
        elif (self._refresh_token and self._session_token_expires_at is not None
              and time.time() > self._session_token_expires_at):
            self.refresh_access_token()
        return self._session_token

    @session_token.setter
    def session_token(self, val: Optional[str]) -> None:
        self._session_token_expires_at = time.time() + 290
        self._session_token = val

    def __init__(
        self,
        phone_no: Optional[str] = None,
        pin: Optional[str] = None,
        keyfile: Optional[Union[str, pathlib.Path]] = None,
        locale: str = "de",
        save_cookies: bool = False,
        credentials_file: Optional[Union[str, pathlib.Path]] = None,
        cookies_file: Optional[Union[str, pathlib.Path]] = None,
    ) -> None:
        self.log = get_logger(__name__)
        self._locale = locale
        self._save_cookies = save_cookies

        self._credentials_file = (
            pathlib.Path(credentials_file) if credentials_file else CREDENTIALS_FILE
        )

        if not (phone_no and pin):
            try:
                with open(self._credentials_file, "r") as f:
                    lines = f.readlines()
                self.phone_no = lines[0].strip()
                self.pin = lines[1].strip()
            except FileNotFoundError:
                raise ValueError(
                    f"phone_no and pin must be specified explicitly or via {self._credentials_file}"
                )
        else:
            self.phone_no = phone_no
            self.pin = pin

        self._cookies_file = (
            pathlib.Path(cookies_file)
            if cookies_file
            else BASE_DIR / f"cookies.{self.phone_no}.txt"
        )

        self.keyfile = keyfile if keyfile else KEY_FILE
        try:
            with open(self.keyfile, "rb") as f:
                self.sk = SigningKey.from_pem(f.read(), hashfunc=hashlib.sha512)
        except FileNotFoundError:
            pass

        self._websession = requests.Session()
        self._websession.headers.update(self._default_headers_web)
        if self._save_cookies:
            self._websession.cookies = RequestsCookieJar()
            cookie_jar = MozillaCookieJar(str(self._cookies_file))
            if self._cookies_file.exists():
                cookie_jar.load(ignore_discard=True, ignore_expires=True)
            for cookie in cookie_jar:
                self._websession.cookies.set_cookie(cookie)

    def initiate_device_reset(self) -> None:
        self.sk = SigningKey.generate(curve=NIST256p, hashfunc=hashlib.sha512)

        r = requests.post(
            f"{self._host}/api/v1/auth/account/reset/device",
            json={"phoneNumber": self.phone_no, "pin": self.pin},
            headers=self._default_headers,
        )

        self._process_id = r.json()["processId"]

    def complete_device_reset(self, token: str) -> None:
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

    def login(self) -> None:
        self.log.info("Logging in")
        r = self._sign_request(
            "/api/v1/auth/login",
            payload={"phoneNumber": self.phone_no, "pin": self.pin},
        )
        response = r.json()
        self._refresh_token = response["refreshToken"]
        self.session_token = response["sessionToken"]

    def refresh_access_token(self) -> None:
        self.log.info("Refreshing access token")
        r = self._sign_request("/api/v1/auth/session", method="GET")
        response = r.json()
        self.session_token = response["sessionToken"]
        self.save_websession()

    def _sign_request(
        self,
        url_path: str,
        payload: Optional[Dict[str, Any]] = None,
        method: str = "POST"
    ) -> requests.Response:
        ts = int(time.time() * 1000)
        payload_string = json.dumps(payload) if payload else ""
        signature_payload = f"{ts}.{payload_string}"
        signature = self.sk.sign(
            signature_payload.encode("utf-8"),
            hashfunc=hashlib.sha512,
            sigencode=sigencode_der,
        )
        signature_string = base64.b64encode(signature).decode("ascii")

        headers: Dict[str, str] = self._default_headers.copy()
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

    def inititate_weblogin(self) -> int:
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
                raise ValueError("processId not in response")
        return int(j["countdownInSeconds"]) + 1

    def resend_weblogin(self) -> None:
        r = self._websession.post(
            f"{self._host}/api/v1/auth/web/login/{self._process_id}/resend",
            headers=self._default_headers,
        )
        r.raise_for_status()

    def complete_weblogin(self, verify_code: str) -> None:
        if not self._process_id and not self._websession:
            raise ValueError("Initiate web login first.")

        r = self._websession.post(
            f"{self._host}/api/v1/auth/web/login/{self._process_id}/{verify_code}"
        )
        r.raise_for_status()
        self.save_websession()
        self._weblogin = True

    def save_websession(self) -> None:
        # Saves session cookies too (expirydate=0).
        if self._save_cookies:
            cookie_jar = MozillaCookieJar(str(self._cookies_file))
            for cookie in self._websession.cookies:
                cookie_jar.set_cookie(cookie)
            cookie_jar.save(ignore_discard=True, ignore_expires=True)

    def resume_websession(self) -> bool:
        """
        Use saved cookie file to resume web session
        Returns:
            bool: True if session was successfully resumed, False otherwise
        """
        if not self._save_cookies:
            return False

        # Only attempt to load if the cookie file exists.
        if self._cookies_file.exists():
            # Load cookies from file into a MozillaCookieJar first
            cookie_jar = MozillaCookieJar(str(self._cookies_file))
            cookie_jar.load(ignore_discard=True, ignore_expires=True)

            # Clear and update the session's RequestsCookieJar
            self._websession.cookies.clear()
            for cookie in cookie_jar:
                self._websession.cookies.set_cookie(cookie)

            self._weblogin = True
            try:
                self.settings()
            except requests.exceptions.HTTPError:
                self._weblogin = False
                return False
            else:
                return True
        return False

    def _web_request(
        self,
        url_path: str,
        payload: Optional[Dict[str, Any]] = None,
        method: str = "GET"
    ) -> requests.Response:
        if self._web_session_token_expires_at < time.time():
            r = self._websession.get(f"{self._host}/api/v1/auth/web/session")
            r.raise_for_status()
            self._web_session_token_expires_at = time.time() + 290
        return self._websession.request(
            method=method, url=f"{self._host}{url_path}", data=payload
        )

    async def _get_ws(self) -> WebSocketClientProtocol:
        if self._ws and self._ws.open:
            return self._ws

        self.log.info("Connecting to websocket ...")
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
            "wss://api.traderepublic.com", ssl=ssl_context, extra_headers=extra_headers
        )
        connect_msg = f"connect {connect_id} {json.dumps(connection_message)}"
        await self._ws.send(connect_msg)
        response = await self._ws.recv()

        if response != "connected":
            raise ValueError(f"Connection Error: {response!r}")

        self.log.info("Connected to websocket ...")

        return self._ws

    async def _next_subscription_id(self) -> str:
        async with self._lock:
            subscription_id = self._subscription_id_counter
            self._subscription_id_counter += 1
            return str(subscription_id)

    async def subscribe(self, payload: Dict[str, Any]) -> str:
        subscription_id = await self._next_subscription_id()
        ws = await self._get_ws()
        self.log.debug(f"Subscribing: 'sub {subscription_id} {json.dumps(payload)}'")
        self.subscriptions[subscription_id] = payload

        payload_with_token = payload.copy()
        if not self._weblogin:
            payload_with_token["token"] = self.session_token

        await ws.send(f"sub {subscription_id} {json.dumps(payload_with_token)}")
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> None:
        ws = await self._get_ws()

        self.log.debug(f"Unsubscribing: {subscription_id}")
        await ws.send(f"unsub {subscription_id}")

        self.subscriptions.pop(subscription_id, None)
        self._previous_responses.pop(subscription_id, None)

    async def recv(self) -> tuple[str, Dict[str, Any], Dict[str, Any]]:
        ws = await self._get_ws()
        while True:
            response = await ws.recv()
            self.log.debug(f"Received message: {response!r}")

            response_str = response.decode('utf-8') if isinstance(response, bytes) else response
            space_idx = response_str.find(" ")
            subscription_id = response_str[:space_idx]
            code = response_str[space_idx + 1:space_idx + 2]
            payload_str = response_str[space_idx + 2:].lstrip()

            if subscription_id not in self.subscriptions:
                if code != "C":
                    self.log.debug(
                        f"No active subscription for id {subscription_id}, dropping message"
                    )
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

    def _calculate_delta(self, subscription_id: str, delta_payload: str) -> str:
        previous_response = self._previous_responses[subscription_id]
        i = 0
        result = []
        for diff in delta_payload.split("\t"):
            sign = diff[0]
            if sign == "+":
                result.append(urllib.parse.unquote_plus(diff).strip())
            elif sign == "-" or sign == "=":
                if sign == "=":
                    result.append(previous_response[i : i + int(diff[1:])])
                i += int(diff[1:])
        return "".join(result)

    async def _recv_subscription(self, subscription_id: str) -> Dict[str, Any]:
        while True:
            response_subscription_id, _, response = await self.recv()
            if response_subscription_id == subscription_id:
                return response

    async def _receive_one(
        self, fut: asyncio.Future[str], timeout: float
    ) -> Dict[str, Any]:
        subscription_id = await fut

        try:
            return await asyncio.wait_for(
                self._recv_subscription(subscription_id), timeout
            )
        finally:
            await self.unsubscribe(subscription_id)

    def run_blocking(self, fut: asyncio.Future[str], timeout: float = 5.0) -> Dict[str, Any]:
        return asyncio.get_event_loop().run_until_complete(
            self._receive_one(fut, timeout=timeout)
        )

    async def portfolio(self) -> str:
        return await self.subscribe({"type": "portfolio"})

    async def compact_portfolio(self) -> str:
        return await self.subscribe({"type": "compactPortfolio"})

    async def watchlist(self) -> str:
        return await self.subscribe({"type": "watchlist"})

    async def cash(self) -> str:
        return await self.subscribe({"type": "cash"})

    async def available_cash_for_payout(self) -> str:
        return await self.subscribe({"type": "availableCashForPayout"})

    async def portfolio_status(self) -> str:
        return await self.subscribe({"type": "portfolioStatus"})

    async def portfolio_history(self, timeframe: str) -> str:
        return await self.subscribe(
            {"type": "portfolioAggregateHistory", "range": timeframe}
        )

    async def instrument_details(self, isin: str) -> str:
        return await self.subscribe({"type": "instrument", "id": isin})

    async def instrument_suitability(self, isin: str) -> str:
        return await self.subscribe(
            {"type": "instrumentSuitability", "instrumentId": isin}
        )

    async def stock_details(self, isin: str) -> str:
        return await self.subscribe({"type": "stockDetails", "id": isin})

    async def add_watchlist(self, isin: str) -> str:
        return await self.subscribe({"type": "addToWatchlist", "instrumentId": isin})

    async def remove_watchlist(self, isin: str) -> str:
        return await self.subscribe(
            {"type": "removeFromWatchlist", "instrumentId": isin}
        )

    async def ticker(self, isin: str, exchange: str = "LSX") -> str:
        return await self.subscribe({"type": "ticker", "id": f"{isin}.{exchange}"})

    async def performance(self, isin: str, exchange: str = "LSX") -> str:
        return await self.subscribe({"type": "performance", "id": f"{isin}.{exchange}"})

    async def performance_history(
        self,
        isin: str,
        timeframe: str,
        exchange: str = "LSX",
        resolution: Optional[str] = None
    ) -> str:
        parameters = {
            "type": "aggregateHistory",
            "id": f"{isin}.{exchange}",
            "range": timeframe,
        }
        if resolution:
            parameters["resolution"] = resolution
        return await self.subscribe(parameters)

    async def experience(self) -> str:
        return await self.subscribe({"type": "experience"})

    async def motd(self) -> str:
        return await self.subscribe({"type": "messageOfTheDay"})

    async def neon_cards(self) -> str:
        return await self.subscribe({"type": "neonCards"})

    async def timeline(self, after: Optional[str] = None) -> str:
        return await self.subscribe({"type": "timeline", "after": after})

    async def timeline_detail(self, timeline_id: str) -> str:
        return await self.subscribe({"type": "timelineDetail", "id": timeline_id})

    async def timeline_detail_order(self, order_id: str) -> str:
        return await self.subscribe({"type": "timelineDetail", "orderId": order_id})

    async def timeline_detail_savings_plan(self, savings_plan_id: str) -> str:
        return await self.subscribe(
            {"type": "timelineDetail", "savingsPlanId": savings_plan_id}
        )

    async def timeline_transactions(self, after: Optional[str] = None) -> str:
        return await self.subscribe({"type": "timelineTransactions", "after": after})

    async def timeline_activity_log(self, after: Optional[str] = None) -> str:
        return await self.subscribe({"type": "timelineActivityLog", "after": after})

    async def timeline_detail_v2(self, timeline_id: str) -> str:
        return await self.subscribe({"type": "timelineDetailV2", "id": timeline_id})

    async def search_tags(self) -> str:
        return await self.subscribe({"type": "neonSearchTags"})

    async def search_suggested_tags(self, query: str) -> str:
        return await self.subscribe(
            {"type": "neonSearchSuggestedTags", "data": {"q": query}}
        )

    async def search(
        self,
        query: str,
        asset_type: str = "stock",
        page: int = 1,
        page_size: int = 20,
        aggregate: bool = False,
        only_savable: bool = False,
        filter_index: Optional[str] = None,
        filter_country: Optional[str] = None,
        filter_sector: Optional[str] = None,
        filter_region: Optional[str] = None,
    ) -> str:
        filters = [{"key": "type", "value": asset_type}]
        if only_savable:
            filters.append({"key": "attribute", "value": "savable"})
        if filter_index:
            filters.append({"key": "index", "value": filter_index})
        if filter_country:
            filters.append({"key": "country", "value": filter_country})
        if filter_region:
            filters.append({"key": "region", "value": filter_region})
        if filter_sector:
            filters.append({"key": "sector", "value": filter_sector})

        search_parameters = {
            "q": query,
            "filter": filters,
            "page": page,
            "pageSize": page_size,
        }

        search_type = "neonSearch" if not aggregate else "neonSearchAggregations"
        return await self.subscribe({"type": search_type, "data": search_parameters})

    async def search_derivative(self, underlying_isin: str, product_type: str) -> str:
        return await self.subscribe(
            {
                "type": "derivatives",
                "underlying": underlying_isin,
                "productCategory": product_type,
            }
        )

    async def order_overview(self) -> str:
        return await self.subscribe({"type": "orders"})

    async def price_for_order(
        self,
        isin: str,
        exchange: str,
        order_type: str
    ) -> str:
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

    async def cash_available_for_order(self) -> str:
        return await self.subscribe({"type": "availableCash"})

    async def size_available_for_order(self, isin: str, exchange: str) -> str:
        return await self.subscribe(
            {
                "type": "availableSize",
                "parameters": {"exchangeId": exchange, "instrumentId": isin},
            }
        )

    async def limit_order(
        self,
        isin: str,
        exchange: str,
        order_type: str,
        size: float,
        limit: float,
        expiry: str,
        expiry_date: Optional[str] = None,
        warnings_shown: Optional[list[str]] = None,
    ) -> str:
        expiry_dict = {"type": expiry}
        if expiry == "gtd" and isinstance(expiry_date, str):
            expiry_dict["value"] = expiry_date

        parameters = {
            "type": "simpleCreateOrder",
            "clientProcessId": str(uuid.uuid4()),
            "warningsShown": list(warnings_shown) if warnings_shown else [],
            "parameters": {
                "instrumentId": isin,
                "exchangeId": exchange,
                "expiry": expiry_dict,
                "limit": limit,
                "mode": "limit",
                "size": size,
                "type": order_type,
            },
        }

        return await self.subscribe(parameters)

    async def market_order(
        self,
        isin: str,
        exchange: str,
        order_type: str,
        size: float,
        expiry: str,
        sell_fractions: bool,
        expiry_date: Optional[str] = None,
        warnings_shown: Optional[list[str]] = None,
    ) -> str:
        expiry_dict = {"type": expiry}
        if expiry == "gtd" and isinstance(expiry_date, str):
            expiry_dict["value"] = expiry_date

        parameters = {
            "type": "simpleCreateOrder",
            "clientProcessId": str(uuid.uuid4()),
            "warningsShown": list(warnings_shown) if warnings_shown else [],
            "parameters": {
                "instrumentId": isin,
                "exchangeId": exchange,
                "expiry": expiry_dict,
                "mode": "market",
                "sellFractions": sell_fractions,
                "size": size,
                "type": order_type,
            },
        }

        return await self.subscribe(parameters)

    async def stop_market_order(
        self,
        isin: str,
        exchange: str,
        order_type: str,
        size: float,
        stop: float,
        expiry: str,
        expiry_date: Optional[str] = None,
        warnings_shown: Optional[list[str]] = None,
    ) -> str:
        expiry_dict = {"type": expiry}
        if expiry == "gtd" and isinstance(expiry_date, str):
            expiry_dict["value"] = expiry_date

        parameters = {
            "type": "simpleCreateOrder",
            "clientProcessId": str(uuid.uuid4()),
            "warningsShown": list(warnings_shown) if warnings_shown else [],
            "parameters": {
                "instrumentId": isin,
                "exchangeId": exchange,
                "expiry": expiry_dict,
                "mode": "stopMarket",
                "size": size,
                "stop": stop,
                "type": order_type,
            },
        }

        return await self.subscribe(parameters)

    async def cancel_order(self, order_id: str) -> str:
        return await self.subscribe({"type": "cancelOrder", "orderId": order_id})

    async def savings_plan_overview(self) -> str:
        return await self.subscribe({"type": "savingsPlans"})

    async def savings_plan_parameters(self, isin: str) -> str:
        return await self.subscribe({"type": "cancelSavingsPlan", "instrumentId": isin})

    async def create_savings_plan(
        self,
        isin: str,
        amount: float,
        interval: str,
        start_date: str,
        start_date_type: str,
        start_date_value: str,
        warnings_shown: Optional[list[str]] = None,
    ) -> str:
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
        savings_plan_id: str,
        isin: str,
        amount: float,
        interval: str,
        start_date: str,
        start_date_type: str,
        start_date_value: str,
        warnings_shown: Optional[list[str]] = None,
    ) -> str:
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

    async def cancel_savings_plan(self, savings_plan_id: str) -> str:
        return await self.subscribe(
            {"type": "cancelSavingsPlan", "id": savings_plan_id}
        )

    async def price_alarm_overview(self) -> str:
        return await self.subscribe({"type": "priceAlarms"})

    async def create_price_alarm(self, isin: str, price: float) -> str:
        return await self.subscribe(
            {"type": "createPriceAlarm", "instrumentId": isin, "targetPrice": price}
        )

    async def cancel_price_alarm(self, price_alarm_id: str) -> str:
        return await self.subscribe({"type": "cancelPriceAlarm", "id": price_alarm_id})

    async def news(self, isin: str) -> str:
        return await self.subscribe({"type": "neonNews", "isin": isin})

    async def news_subscriptions(self) -> str:
        return await self.subscribe({"type": "newsSubscriptions"})

    async def subscribe_news(self, isin: str) -> str:
        return await self.subscribe({"type": "subscribeNews", "instrumentId": isin})

    async def unsubscribe_news(self, isin: str) -> str:
        return await self.subscribe({"type": "unsubscribeNews", "instrumentId": isin})

    def payout(self, amount: float) -> Dict[str, Any]:
        response = self._sign_request("/api/v1/payout", {"amount": amount})
        response.raise_for_status()
        return Dict[str, Any](response.json())

    def confirm_payout(self, process_id: str, code: str) -> None:
        r = self._sign_request(f"/api/v1/payout/{process_id}/code", {"code": code})
        if r.status_code != 200:
            raise ValueError(f"Payout failed with response {r.text!r}")

    def settings(self) -> Dict[str, Any]:
        if self._weblogin:
            r = self._web_request("/api/v2/auth/account")
        else:
            r = self._sign_request("/api/v1/auth/account", method="GET")
        r.raise_for_status()
        return Dict[str, Any](r.json())

    def order_cost(
        self,
        isin: str,
        exchange: str,
        order_mode: str,
        order_type: str,
        size: float,
        sell_fractions: bool
    ) -> str:
        url = (
            f"/api/v1/user/costtransparency?instrumentId={isin}&exchangeId={exchange}"
            f"&mode={order_mode}&type={order_type}&size={size}&sellFractions={sell_fractions}"
        )
        return self._sign_request(url, method="GET").text

    def savings_plan_cost(self, isin: str, amount: float, interval: str) -> str:
        url = f"/api/v1/user/savingsplancosttransparency?instrumentId={isin}&amount={amount}&interval={interval}"
        return self._sign_request(url, method="GET").text

    def __getattr__(self, name: str) -> Any:
        if name[:9] == "blocking_":
            attr = object.__getattribute__(self, name[9:])
            if hasattr(attr, "__call__"):
                return lambda *args, **kwargs: self.run_blocking(
                    timeout=kwargs.pop("timeout", 5), fut=attr(*args, **kwargs)
                )
        return object.__getattribute__(self, name)

class TradeRepublicError(ValueError):
    def __init__(
        self,
        subscription_id: str,
        subscription: Dict[str, Any],
        error_message: Dict[str, Any]
    ) -> None:
        super().__init__(f"Error in subscription {subscription_id}: {error_message}")
        self.subscription_id = subscription_id
        self.subscription = subscription
        self.error = error_message

