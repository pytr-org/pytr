import pickle
import asyncio

from pytr import TradeRepublic


def test_session_serialize_resume():
    client = TradeRepublic("+100", "1234")
    # simulate login tokens and a cookie
    client._api._refresh_token = "rtoken"
    client._api._session_token = "stoken"
    client._api._session_token_expires_at = 123456.0
    # add a dummy cookie
    from http.cookiejar import Cookie
    dummy = Cookie(
        version=0,
        name="k",
        value="v",
        port=None,
        port_specified=False,
        domain="example.com",
        domain_specified=True,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )
    client._api._websession.cookies.set_cookie(dummy)


    data = client.serialize_session()
    # datason.dumps returns a JSON-compatible dict
    assert isinstance(data, dict)
    state = data
    assert state["refresh_token"] == "rtoken"
    assert state["session_token"] == "stoken"
    assert state["session_token_expires_at"] == 123456.0
    assert isinstance(state.get("cookies"), dict)

    # resume into new client and check restoration
    new_client = TradeRepublic("+100", "1234")
    asyncio.run(new_client.resume_session(data))
    assert new_client._api._refresh_token == "rtoken"
    assert new_client._api._session_token == "stoken"
    assert new_client._api._session_token_expires_at == 123456.0
    # restored cookiejar has the dummy cookie
    cj = new_client._api._websession.cookies
    assert cj.get("k") == "v"
