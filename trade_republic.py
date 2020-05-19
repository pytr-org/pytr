import requests
import time
import json
import hashlib
from ecdsa import NIST256p, SigningKey
import base64
import websockets
from ecdsa.util import sigencode_der
import asyncio
import urllib.parse


class TradeRepublic:
    default_headers = {'User-Agent': 'TradeRepublic/Android 24/App Version 1.1.2875'}
    ws = None
    msg_id_counter = 1
    lock = asyncio.Lock()
    msg_id_mapping = {}
    previous_responses = {}

    def __init__(self, phone_no, pin, keyfile=None):
        self.phone_no = phone_no
        self.pin = pin
        self.keyfile = keyfile
        if keyfile:
            with open('keyfile.pem', 'rb') as f:
                data = f.read()
            self.sk = SigningKey.from_pem(data, hashfunc=hashlib.sha512)

    def initiate_device_reset(self):
        self.sk = SigningKey.generate(curve=NIST256p, hashfunc=hashlib.sha512)

        r = requests.post("https://api.traderepublic.com/api/v1/auth/account/reset/device",
                          json={"phoneNumber": self.phone_no, "pin": self.pin},
                          headers=self.default_headers)

        self.process_id = r.json()['processId']

    def complete_device_reset(self, token):
        if not self.process_id and not self.sk:
            raise ValueError("Initiate Device Reset first.")

        pubkey_bytes = self.sk.get_verifying_key().to_string('uncompressed')
        pubkey_string = base64.b64encode(pubkey_bytes).decode('ascii')

        r = requests.post(f"https://api.traderepublic.com/api/v1/auth/account/reset/device/{self.process_id}/key",
                          json={"code": token, "deviceKey": pubkey_string},
                          headers=self.default_headers)
        if r.status_code == 200:
            with open('keyfile.pem', 'wb') as f:
                f.write(self.sk.to_pem())

    def login(self):
        payload = json.dumps({"phoneNumber": self.phone_no, "pin": self.pin})

        ts = int(time.time() * 1000)
        signature_payload = f"{ts}.{payload}"
        signature = self.sk.sign(bytes(signature_payload, "utf-8"), hashfunc=hashlib.sha512, sigencode=sigencode_der)

        headers = self.default_headers.copy()
        headers["X-Zeta-Timestamp"] = str(ts)
        headers["X-Zeta-Signature"] = base64.b64encode(signature).decode('ascii')
        headers['Content-Type'] = 'application/json'

        r = requests.post("https://api.traderepublic.com/api/v1/auth/login", data=payload, headers=headers)
        self.refresh_token = r.json()['refreshToken']
        self.session_token = r.json()['sessionToken']

    async def _get_ws(self):
        if self.ws and self.ws.open:
            return self.ws

        self.ws = await websockets.connect("wss://api.traderepublic.com")
        connection_message = {'locale': "de"}
        await self.ws.send(f"connect 21 {json.dumps(connection_message)}")
        response = await self.ws.recv()

        if not response == 'connected':
            raise ValueError(f"Connection Error: {response}")
        return self.ws

    async def _get_msg_id(self):
        async with self.lock:
            msg_id = self.msg_id_counter
            self.msg_id_counter += 1
            return msg_id

    async def _subscribe(self, payload):
        payload["token"] = self.session_token
        msg_id = await self._get_msg_id()
        self.msg_id_mapping[str(msg_id)] = payload

        ws = await self._get_ws()
        await ws.send(f"sub {msg_id} {json.dumps(payload)}")

    async def recv(self):
        ws = await self._get_ws()
        response = await ws.recv()

        msg_id = response[:response.find(" ")]
        code = response[response.find(" ") + 1 : response.find(" ") + 2]
        subscription = self.msg_id_mapping[msg_id]

        if code == 'C':
            return subscription["type"], subscription, code, {}
        if code == 'A':
            payload_str = response.split(' ', maxsplit=2)[2]
            self.previous_responses[msg_id] = payload_str
            payload = json.loads(payload_str)
            return subscription["type"], subscription, code, payload
        elif code == 'D':
            payload_str = response.split(' ', maxsplit=2)[2]
            response = self._calculate_delta(msg_id, payload_str)
            self.previous_responses[msg_id] = response
            return subscription["type"], subscription, code, json.loads(response)

    def _calculate_delta(self, msg_id, delta_payload):
        previous_response = self.previous_responses[msg_id]
        i, result = 0, []
        for diff in delta_payload.split('\t'):
            sign = diff[0]
            if sign == '+':
                result.append(urllib.parse.unquote_plus(diff).strip())
            elif sign == '-' or sign == '=':
                if sign == '=':
                    result.append(previous_response[i:i + int(diff[1:])])
                i += int(diff[1:])
        return "".join(result)

    async def request_portfolio(self):
        await self._subscribe({"type": "portfolio"})

    async def request_watchlist(self):
        await self._subscribe({"type": "watchlist"})

    async def request_cash(self):
        await self._subscribe({"type": "cash"})

    async def request_instrument_details(self, isin):
        await self._subscribe({"type": "instrument", "id": isin})

    async def request_stock_details(self, isin):
        await self._subscribe({"type": "stockDetails", "id": isin})

    async def request_portfolio_status(self):
        await self._subscribe({"type": "portfolioStatus"})

    async def request_add_watchlist(self, isin):
        await self._subscribe({"type": "addToWatchlist", "instrumentId": isin})

    async def request_remove_watchlist(self, isin):
        await self._subscribe({"type": "removeFromWatchlist", "instrumentId": isin})

    async def request_ticker(self, isin):
        await self._subscribe({"type": "ticker", "id": isin})
