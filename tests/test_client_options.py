import pytest

from pytr import TradeRepublic


@pytest.mark.parametrize("timeout,debug", [
    (5.0, False),
    (2.5, True),
])
def test_constructor_timeout_debug(timeout, debug):
    client = TradeRepublic("123", "0000", timeout=timeout, debug=debug)
    assert client.timeout == timeout
    assert client.debug is debug
    # underlying api should also receive timeout/debug attributes if available
    assert hasattr(client._api, "timeout")
    assert hasattr(client._api, "debug")
    assert client._api.timeout == timeout
    assert client._api.debug is debug
