# Trade Republic API

This is a documentation of some parts of the private API of the Trade Republic Online Brokerage. Not affiliated with Trade Republic Bank GmbH.

## How to use it

First you need to perform a device reset - a private key will be generated that pins your "device". The private key is saved to your keyfile. This procedure will log you out from your mobile device.

```python
from trade_republic import TradeRepublic
tr = TradeRepublic(phone_no="+4900000000000", pin="0000", keyfile='keyfile.pem')
tr.initiate_device_reset()
tr.complete_device_reset("0000") # Substitute the 2FA token that is sent to you via SMS.
```

After this has been performed, you can login:

```python
from trade_republic import TradeRepublic
tr = TradeRepublic(phone_no="+4900000000000", pin="0000", keyfile='keyfile.pem')
tr.login()
```

Now you can talk to the asynchronous Trade Republic API via Websockets: 

```python
import asyncio

async def my_loop():
    await tr.request_cash()
    await tr.request_watchlist()
    await tr.request_portfolio()
    await tr.request_ticker("DE0007236101.LSX")

    while True:
        _, request, _, response = await tr.recv()
        print(response)

asyncio.get_event_loop().run_until_complete(asyncio.gather(my_loop()))
```


## How it works

Details of how the API works

### Request Signing

All requests to the REST API are pinned to a device by signing requests using a private key which is generated on the device and stored in the secure storage of the device. To login, we first have to generate a private key, register it and verify the key using 2FA (SMS).

Generate your private key (Make sure to save this somewhere using `sk.to_pem()`):
```python
from ecdsa import NIST256p, SigningKey
import hashlib
import base64
sk = SigningKey.generate(curve=NIST256p, hashfunc=hashlib.sha512)

pubkey_bytes = sk.get_verifying_key().to_string('uncompressed')
pubkey = base64.b64encode(pubkey_bytes).decode('ascii')
```

Initiate the device reset:

```python
import requests
default_headers = {'User-Agent': 'TradeRepublic/Android 24/App Version 1.1.2875'}

phone_number = "Phone number in format +4900000000"
pin = "Pin in format 0000"
r = requests.post("https://api.traderepublic.com/api/v1/auth/account/reset/device",
                  json={"phoneNumber": phone_number, "pin": pin},
                  headers=default_headers)
process_id = r.json()['processId']
```

By this point, Trade Republic should have sent you an SMS with a confirmation code. Confirm the device reset using this code. (This logs you out from your mobile device, to login on mobile, you need to verify your mobile device again using the SMS 2FA flow.)

```python
code = "2FA code from SMS in format 0000"
r = requests.post(f"https://api.traderepublic.com/api/v1/auth/account/reset/device/{process_id}/key",
                  json={"code": code, "deviceKey": pubkey},
                  headers=default_headers)
```

Now we can perform the login:

```python
from ecdsa.util import sigencode_der
import time
import json

payload = json.dumps({"phoneNumber": "+4900000000", "pin": "0000"})

ts = int(time.time() * 1000)
signature_payload = f"{ts}.{payload}"
signature = sk.sign(bytes(signature_payload, "utf-8"), hashfunc=hashlib.sha512, sigencode=sigencode_der)

headers = default_headers.copy()
headers["X-Zeta-Timestamp"] = str(ts)
headers["X-Zeta-Signature"] = base64.b64encode(signature).decode('ascii')
headers['Content-Type'] = 'application/json'

r = requests.post("https://api.traderepublic.com/api/v1/auth/login", data=payload, headers=headers)
refresh_token = r.json()['refreshToken']
session_token = r.json()['sessionToken']
```

This gives us two tokens to authorize requests. The `session_token` needs to be added to requests as a bearer token: `headers['Authorization'] = f'Bearer {token}'`, the requests still need to be signed using the method demonstrated above.

After some time the session token expires and we need to request a new one using the refresh token, or just login again.

### Websocket Connection

There's not a lot we can do with the REST Api - basically only authorization and onboarding. For anything else we need to connect to their websocket.

```python
import websocket

ws = websocket.WebSocket()
ws.connect("wss://api.traderepublic.com")
ws.send("connect 21 {}")
print(ws.recv())
```

Now we can send requests over the websocket. Authorization is performed by adding the session token to the request payload. We also need to add a unique Id (incremental counter) to each request. Responses to each request will be prefixed with the respective Id.

```python
msg = {"type": "cash", "token": session_token}
i = 1 # Unique Id for each request you send over the websocket
ws.send(f"sub {i} {json.dumps(msg)}")
print(ws.recv())

msg = {"type": "timeline", "token": session_token}
i = 2
ws.send(f"sub {i} {json.dumps(msg)}")
print(ws.recv())
```

An (incomplete) list of possible websocket requests:

```
# Timeline:
{"type": "timeline", "after": after}
{"type": "timelineDetail", "id": id}
{"type": "timelineDetail", "orderId": orderId}
{"type": "timelineDetail", "savingsPlanId": savingsPlanId}
{"type": "timelineActions"}

# Portfolio:
{"type": "cash"}
{"type": "messageOfTheDay"}
{"type": "neonCards"}
{"type": "portfolio"}
{"type": "portfolioStatus"}
{"type": "portfolioAggregateHistory", "range": range} 
# range is something from ["1d", "5d", "1m", "3m", "6m", "1y", "5y", "max"]
{"type": "availableCashForPayout"}

# Watchlist:
{"type": "watchlist"}
{"type": "addToWatchlist", "instrumentId": instrumentId}
{"type": "removeFromWatchlist", "instrumentId": instrumentId}

# Trade Experience:
{"type": "experience"}

# Instruments:
{type="instrument", "id": instrumentId}
{type="stockDetails", "id": instrumentId}
{type="instrumentSuitability", "instrumentId": instrumentId}

# Instrument Search:
{"type": "neonSearch", "data": {"q": query, "filter": [{"key": value}], "sorting": s, "page": int, "pageSize": int}}
{"type": "neonSearchTags"}
{"type": "neonSearchSuggestedTags", "data": {"q": query}}
{"type": "neonSearchAggregations", "data": {"q": query, "filter": [{"key": value}], "sorting": s, "page": int, "pageSize": int}}

# Derivative Search:
{"underlying": isin, "productCategory": productCategory, "type": "derivatives"}

# Exchanges:
{"type": "homeInstrumentExchange", "id": instrumentId}
```




















