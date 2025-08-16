import pytest

from pytr.client import TradeRepublic
from pytr.errors import ApiShapeError


@pytest.mark.asyncio
async def test_quotes_shape_drift(tmp_path, monkeypatch):
    # patch TradeRepublicApi to avoid real websocket and simulate missing 'last'
    class DummyAPI:
        def __init__(self, *args, **kwargs):
            pass
        async def ticker(self, isin):
            return 'sub'
        async def recv(self):
            return None, None, {}
        async def unsubscribe(self, sub):
            pass
    import pytr.client as _client_mod
    monkeypatch.setattr(_client_mod, 'TradeRepublicApi', DummyAPI)
    client = TradeRepublic("+100", "0000")
    # expecting ApiShapeError with debug payload
    with pytest.raises(ApiShapeError) as excinfo:
        await client.quotes(['US0378331005'])
    err = excinfo.value
    assert hasattr(err, 'data')
    dbg = err.data
    assert 'US0378331005' not in dbg or 'price' not in dbg['US0378331005'] or dbg['US0378331005']['price'] == '<REDACTED>'


@pytest.mark.asyncio
async def test_quotes_normal_flow(monkeypatch):
    # patch TradeRepublicApi for normal flow
    class DummyAPI2:
        def __init__(self, *args, **kwargs):
            pass
        async def ticker(self, isin):
            return 'sub'
        async def recv(self):
            return None, None, {'last': {'price': 42.5, 'currencyId': 'EUR', 'timestamp': '2024-01-01T12:00:00Z'}}
        async def unsubscribe(self, sub):
            pass
    import pytr.client as _client_mod
    monkeypatch.setattr(_client_mod, 'TradeRepublicApi', DummyAPI2)
    client = TradeRepublic("+100", "0000")
    quotes = await client.quotes(['US0378331005'])
    assert isinstance(quotes, dict)
    q = quotes['US0378331005']
    from pytr.models import Quote
    assert isinstance(q, Quote)
    assert q.isin == 'US0378331005'
    assert q.price == 42.5
    assert q.currency == 'EUR'
