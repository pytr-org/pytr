"""Pin how pytr reaches accounts other than the login's own: company and child accounts."""

import asyncio
import json as jsonlib
from typing import Any

import pytest
import requests

import pytr.account as account_module
from pytr.api import TradeRepublicApi

HOST = "https://api.traderepublic.com"
SESSION_V1 = f"{HOST}/api/v1/auth/web/session"
SESSION_V2 = f"{HOST}/api/v2/auth/web/session"
RELATIONSHIPS = f"{HOST}/api/v1/customer/relationships/detailed"
ACCOUNT = f"{HOST}/api/v2/auth/account"

SELF = {
    "customerId": "id-self",
    "firstName": "Erika",
    "lastName": "Mustermann",
    "relationshipType": "SELF",
    "accountType": "ADULT",
}
COMPANY = {
    "customerId": "id-company",
    "relationshipType": "LEGAL_ENTITY_ACTOR",
    "accountType": "LEGAL_ENTITY",
    "accountName": "Mustermann Holding GmbH",
}
CHILD_A = {"customerId": "id-a", "firstName": "Max", "relationshipType": "PARENT", "accountType": "CHILD"}
CHILD_B = {"customerId": "id-b", "firstName": "Mia", "relationshipType": "PARENT", "accountType": "CHILD"}

# What /api/v2/auth/account answers while the session acts for another account.
OTHER_ACCOUNT = (400, {"errors": [{"errorCode": "INVALID_AUTH_ACCOUNT_STATE", "errorMessage": None, "meta": None}]})


class _Response:
    def __init__(self, payload: Any = None, status_code: int = 200):
        self.status_code = status_code
        self._payload = {} if payload is None else payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error", response=self)  # type: ignore[arg-type]

    def json(self) -> Any:
        return self._payload


class _Session:
    """Records requests instead of sending them. Replies come from a queue."""

    def __init__(self, replies: list[Any]):
        self.calls: list[dict[str, Any]] = []
        self._replies = list(replies)
        self.headers = dict(TradeRepublicApi._default_headers)

    def _record(self, method: str, url: str, json: Any = None, headers: Any = None) -> _Response:
        self.calls.append({"method": method, "url": url, "json": json, "headers": headers or {}})
        reply = self._replies.pop(0) if self._replies else {}
        status, payload = reply if isinstance(reply, tuple) else (200, reply)
        return _Response(payload, status)

    def post(self, url, json=None, headers=None):
        return self._record("POST", url, json, headers)

    def get(self, url, headers=None):
        return self._record("GET", url, None, headers)

    def request(self, method, url, data=None):
        return self._record(method, url, None, None)


class _Websocket:
    """Answers subscriptions from a table of topic -> payload."""

    close_code = None

    def __init__(self, answers: dict[str, Any]):
        self.sent: list[str] = []
        self._answers = answers
        self._inbox: asyncio.Queue[str] = asyncio.Queue()

    async def send(self, message: str) -> None:
        self.sent.append(message)
        command, subscription_id, *payload = message.split(" ", 2)
        if command == "sub":
            topic = jsonlib.loads(payload[0])["type"]
            if topic in self._answers:
                await self._inbox.put(f"{subscription_id} A {jsonlib.dumps(self._answers[topic])}")

    async def recv(self) -> str:
        return await self._inbox.get()

    def subscriptions(self) -> list[dict[str, Any]]:
        return [jsonlib.loads(m.split(" ", 2)[2]) for m in self.sent if m.startswith("sub ")]


def _api(replies, session_is_fresh=True):
    tr = TradeRepublicApi(phone_no="+490000000000", pin="0000", waf_token=None, save_cookies=False)
    tr._websession = _Session(replies)
    if session_is_fresh:
        tr._session_expires_at = float("inf")
    return tr


def _with_websocket(tr, answers):
    ws = _Websocket(answers)

    async def get_ws():
        return ws

    tr._get_ws = get_ws
    return ws


def _calls(tr):
    return [(c["method"], c["url"]) for c in tr._websession.calls]


# --- listing the accounts ------------------------------------------------------------


def test_relationships_lists_the_accounts_of_the_login():
    tr = _api([{"relationships": [SELF, COMPANY]}])

    assert tr.relationships() == [SELF, COMPANY]
    assert _calls(tr) == [("GET", RELATIONSHIPS)]


# --- switching -----------------------------------------------------------------------


def test_switch_account_asks_for_a_session_acting_for_the_other_customer():
    tr = _api([{"relationships": [SELF, COMPANY]}, {}])
    tr._sec_acc_no = "own-depot"

    chosen = tr.switch_account("LEGAL_ENTITY")

    assert chosen == COMPANY
    assert _calls(tr) == [("GET", RELATIONSHIPS), ("POST", SESSION_V2)]
    assert tr._websession.calls[1]["json"] == {"subjectId": "id-company"}
    # The securities account of the own account must not leak into the other one.
    assert tr._sec_acc_no is None


def test_switch_account_sends_the_headers_the_v2_auth_endpoints_require():
    tr = _api([{"relationships": [SELF, COMPANY]}, {}])

    tr.switch_account("LEGAL_ENTITY")

    for header in ("X-TR-Device-Info", "X-TR-App-Version", "X-Tr-Platform"):
        assert tr._websession.calls[1]["headers"].get(header)


@pytest.mark.parametrize(
    "account",
    ["id-company", "legal_entity", "LEGAL_ENTITY_ACTOR", "mustermann holding gmbh", "  Mustermann Holding GmbH "],
)
def test_switch_account_finds_the_account_by_id_type_or_name(account):
    tr = _api([{"relationships": [SELF, COMPANY]}, {}])

    assert tr.switch_account(account) == COMPANY


def test_switch_account_without_a_name_returns_to_the_own_account():
    tr = _api([{"relationships": [SELF, COMPANY]}, {}])
    tr._subject_id = "id-company"

    assert tr.switch_account() == SELF
    assert tr._websession.calls[1]["json"] == {"subjectId": "id-self"}
    assert tr._subject_id is None


def test_switch_account_rejects_an_unknown_account_and_names_the_known_ones():
    tr = _api([{"relationships": [SELF, COMPANY]}])

    with pytest.raises(ValueError, match="does not match any account.*LEGAL_ENTITY \\(Mustermann Holding GmbH\\)"):
        tr.switch_account("nope")

    assert _calls(tr) == [("GET", RELATIONSHIPS)]


def test_switch_account_rejects_an_ambiguous_account():
    """Two children share their type, so the type alone does not say which one is meant."""
    tr = _api([{"relationships": [SELF, CHILD_A, CHILD_B]}, {"relationships": [SELF, CHILD_A, CHILD_B]}, {}])

    with pytest.raises(ValueError, match="more than one account"):
        tr.switch_account("CHILD")

    assert tr.switch_account("Mia") == CHILD_B


def test_switch_account_reports_a_refused_switch():
    tr = _api([{"relationships": [SELF, COMPANY]}, (403, {})])

    with pytest.raises(requests.HTTPError):
        tr.switch_account("LEGAL_ENTITY")

    assert tr._subject_id is None


def test_switch_account_refuses_while_the_websocket_is_connected():
    """An open websocket keeps answering for the account it was authenticated with."""
    tr = _api([{"relationships": [SELF, COMPANY]}, {}])
    tr._ws = _Websocket({})

    with pytest.raises(ValueError, match="websocket"):
        tr.switch_account("LEGAL_ENTITY")

    assert tr._websession.calls == []


# --- keeping the session on the chosen account ---------------------------------------


def test_session_refresh_stays_on_the_chosen_account():
    tr = _api([{"relationships": [SELF, COMPANY]}, {}, {}, {}])
    tr.switch_account("LEGAL_ENTITY")
    tr._session_expires_at = 0

    tr._web_request("/api/v1/whatever")

    assert _calls(tr)[2] == ("POST", SESSION_V2)
    assert tr._websession.calls[2]["json"] == {"subjectId": "id-company"}


def test_session_refresh_is_unchanged_for_the_own_account():
    tr = _api([{}, {}], session_is_fresh=False)

    tr._web_request("/api/v1/whatever")

    assert _calls(tr)[0] == ("GET", SESSION_V1)


def _resumable(tmp_path, replies):
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n")
    tr = TradeRepublicApi(
        phone_no="+490000000000", pin="0000", waf_token=None, save_cookies=True, cookies_file=str(cookies)
    )
    jar = tr._websession.cookies
    tr._websession = _Session(replies)
    tr._websession.cookies = jar  # type: ignore[attr-defined]
    return tr


def test_resume_accepts_cookies_saved_while_acting_for_another_account(tmp_path):
    """Those cookies are valid; only the account settings are not served for them."""
    tr = _resumable(tmp_path, [{}, OTHER_ACCOUNT])

    assert tr.resume_websession() is True


def test_resume_still_rejects_an_expired_session(tmp_path):
    tr = _resumable(tmp_path, [(401, {})])

    assert tr.resume_websession() is False


# --- portfolio -----------------------------------------------------------------------

PAIRS = {
    "authAccountId": "id-company",
    "accounts": [
        {"securitiesAccountNumber": "depot-other", "cashAccountNumber": "cash-other", "productType": "OTHER"},
        {"securitiesAccountNumber": "depot-company", "cashAccountNumber": "cash-company", "productType": "DEFAULT"},
    ],
}


def test_compact_portfolio_reads_the_securities_account_from_account_pairs_after_a_switch():
    tr = _api([{"relationships": [SELF, COMPANY]}, {}])
    tr.switch_account("LEGAL_ENTITY")
    ws = _with_websocket(tr, {"accountPairs": PAIRS})

    asyncio.run(tr.compact_portfolio())

    assert ws.subscriptions() == [
        {"type": "accountPairs"},
        {"type": "compactPortfolioByType", "secAccNo": "depot-company"},
    ]
    # The account settings are not served for this account, so they are not asked for.
    assert ("GET", ACCOUNT) not in _calls(tr)


def test_compact_portfolio_falls_back_to_account_pairs_when_the_settings_are_refused():
    tr = _api([OTHER_ACCOUNT])
    ws = _with_websocket(tr, {"accountPairs": PAIRS})

    asyncio.run(tr.compact_portfolio())

    assert ws.subscriptions()[-1] == {"type": "compactPortfolioByType", "secAccNo": "depot-company"}


def test_compact_portfolio_still_uses_the_account_settings_for_the_own_account():
    tr = _api([{"securitiesAccountNumber": "own-depot"}])
    ws = _with_websocket(tr, {})

    asyncio.run(tr.compact_portfolio())

    assert ws.subscriptions() == [{"type": "compactPortfolioByType", "secAccNo": "own-depot"}]


def test_compact_portfolio_does_not_hide_other_errors_of_the_settings_call():
    tr = _api([(500, {})])
    _with_websocket(tr, {"accountPairs": PAIRS})

    with pytest.raises(requests.HTTPError):
        asyncio.run(tr.compact_portfolio())


def test_compact_portfolio_reports_a_missing_securities_account():
    tr = _api([{}])
    _with_websocket(tr, {"accountPairs": {"authAccountId": "id-self", "accounts": []}})

    with pytest.raises(ValueError, match="securities account number"):
        asyncio.run(tr.compact_portfolio())


# --- pytr accounts -------------------------------------------------------------------


def test_get_accounts_prints_what_account_accepts():
    tr = _api([{"relationships": [SELF, {**COMPANY, "accountState": "ACTIVE"}, CHILD_B]}])

    assert account_module.get_accounts(tr).splitlines() == [
        "ADULT         Erika Mustermann         your own account",
        "LEGAL_ENTITY  Mustermann Holding GmbH  ACTIVE",
        "CHILD         Mia",
    ]


def test_get_accounts_of_a_login_without_relationships_is_empty():
    assert account_module.get_accounts(_api([{}])) == ""


def test_the_accounts_command_exists_and_takes_the_login_arguments():
    from pytr.main import get_main_parser

    args = get_main_parser().parse_args(["accounts", "--v2"])

    assert (args.command, args.v2, args.account) == ("accounts", True, None)


# --- login() -------------------------------------------------------------------------


class _LoggedIn:
    """Stands in for a TradeRepublicApi whose saved session could be resumed."""

    def __init__(self, settings_reply):
        self._settings_reply = settings_reply
        self.switched_to: list[Any] = []

    def resume_websession(self):
        return True

    def settings(self):
        status, payload = self._settings_reply
        response = _Response(payload, status)
        response.raise_for_status()
        return payload

    _acts_for_other_account = staticmethod(TradeRepublicApi._acts_for_other_account)

    def switch_account(self, account=None):
        self.switched_to.append(account)


def _login(monkeypatch, settings_reply, **kwargs):
    tr = _LoggedIn(settings_reply)
    monkeypatch.setattr(account_module, "TradeRepublicApi", lambda **_: tr)
    assert account_module.login(phone_no="+490000000000", pin="0000", **kwargs) is tr
    return tr


def test_login_does_not_switch_by_default(monkeypatch):
    assert _login(monkeypatch, (200, {})).switched_to == []


def test_login_switches_to_the_requested_account(monkeypatch):
    assert _login(monkeypatch, (200, {}), account="LEGAL_ENTITY").switched_to == ["LEGAL_ENTITY"]


def test_login_stays_on_the_requested_account_when_the_cookies_already_act_for_it(monkeypatch):
    assert _login(monkeypatch, OTHER_ACCOUNT, account="LEGAL_ENTITY").switched_to == ["LEGAL_ENTITY"]


def test_login_returns_to_the_own_account_when_none_is_requested(monkeypatch):
    """Cookies saved by a run with --account must not make the next plain run use that account."""
    assert _login(monkeypatch, OTHER_ACCOUNT).switched_to == [None]
