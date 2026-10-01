"""Pin how pytr reaches an account of the login other than its own, e.g. a company account."""

import asyncio
import json as jsonlib
from typing import Any

import pytest
import requests

import pytr.account as account_module
from pytr.api import TradeRepublicApi
from pytr.main import get_main_parser

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
    "accountState": "ACTIVE",
    "accountType": "ADULT",
}
COMPANY = {
    "customerId": "id-company",
    "relationshipType": "LEGAL_ENTITY_ACTOR",
    "accountState": "ACTIVE",
    "accountType": "LEGAL_ENTITY",
    "accountName": "Mustermann Holding GmbH",
}
SECOND_COMPANY = {**COMPANY, "customerId": "id-second", "accountName": "Mustermann Immobilien UG"}
BOTH = {"relationships": [SELF, COMPANY]}


class _Response:
    def __init__(self, payload: Any = None, status_code: int = 200):
        self.status_code = status_code
        self._payload = {} if payload is None else payload

    def __bool__(self) -> bool:
        # Like requests.Response: falsy for 4xx and 5xx.
        return self.status_code < 400

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error", response=self)  # type: ignore[arg-type]

    def json(self) -> Any:
        return self._payload


class _Session:
    """Records requests instead of sending them. Replies come from a queue; an unexpected request fails."""

    def __init__(self, replies: list[Any]):
        self.calls: list[dict[str, Any]] = []
        self.replies = list(replies)
        self.headers = dict(TradeRepublicApi._default_headers)

    def _record(self, method: str, url: str, json: Any = None, headers: Any = None) -> _Response:
        self.calls.append({"method": method, "url": url, "json": json, "headers": headers or {}})
        assert self.replies, f"unexpected request: {method} {url}"
        reply = self.replies.pop(0)
        status, payload = reply if isinstance(reply, tuple) else (200, reply)
        return _Response(payload, status)

    def post(self, url, json=None, headers=None):
        return self._record("POST", url, json, headers)

    def get(self, url, headers=None):
        return self._record("GET", url, None, headers)

    def request(self, method, url, data=None):
        return self._record(method, url, data, None)


class _Websocket:
    """Answers each subscription with the messages listed for its topic: (code, topic answered, payload)."""

    close_code = None

    def __init__(self, answers: dict[str, list[tuple[str, str, Any]]]):
        self.sent: list[str] = []
        self._answers = answers
        self._ids: dict[str, str] = {}
        self._inbox: asyncio.Queue[str] = asyncio.Queue()

    async def send(self, message: str) -> None:
        self.sent.append(message)
        command, subscription_id, *payload = message.split(" ", 2)
        if command != "sub":
            return
        topic = jsonlib.loads(payload[0])["type"]
        self._ids[topic] = subscription_id
        for code, answered_topic, body in self._answers.get(topic, []):
            await self._inbox.put(f"{self._ids[answered_topic]} {code} {jsonlib.dumps(body)}")

    async def recv(self) -> str:
        return await self._inbox.get()

    def subscriptions(self) -> list[dict[str, Any]]:
        return [jsonlib.loads(m.split(" ", 2)[2]) for m in self.sent if m.startswith("sub ")]


def _api(replies, session_is_fresh=True):
    tr = TradeRepublicApi(phone_no="+490000000000", pin="0000", waf_token=None, save_cookies=False)
    tr._websession = _Session(replies)
    # These are class attributes; keep what one test subscribes to out of the next.
    tr.subscriptions = {}
    tr._previous_responses = {}
    tr._subscription_id_counter = 1
    if session_is_fresh:
        tr._session_expires_at = float("inf")
    return tr


def _switched(extra_replies=()):
    """An API whose session acts for the company account."""
    tr = _api([BOTH, {}, *extra_replies])
    tr.switch_account("LEGAL_ENTITY")
    tr._websession.calls.clear()
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
    tr = _api([BOTH])

    assert tr.relationships() == [SELF, COMPANY]
    assert _calls(tr) == [("GET", RELATIONSHIPS)]


@pytest.mark.parametrize("payload", [{}, {"relationships": None}])
def test_relationships_of_a_login_without_any_is_empty(payload):
    assert _api([payload]).relationships() == []


# --- switching -----------------------------------------------------------------------


def test_switch_account_asks_for_a_session_acting_for_the_other_customer():
    tr = _api([BOTH, {}])
    tr._sec_acc_no = "own-depot"

    chosen = tr.switch_account("LEGAL_ENTITY")

    assert chosen == COMPANY
    assert _calls(tr) == [("GET", RELATIONSHIPS), ("POST", SESSION_V2)]
    assert tr._websession.calls[1]["json"] == {"subjectId": "id-company"}
    assert tr._subject_id == "id-company"
    # The securities account of the own account must not leak into the other one.
    assert tr._sec_acc_no is None


def test_switch_account_sends_the_headers_of_the_v2_login_calls():
    tr = _api([BOTH, {}])

    tr.switch_account("LEGAL_ENTITY")

    for header in ("X-TR-Device-Info", "X-TR-App-Version", "X-Tr-Platform"):
        assert tr._websession.calls[1]["headers"].get(header)


def test_switch_account_saves_the_new_cookies():
    tr = _api([BOTH, {}])
    saved = []
    tr.save_websession = lambda: saved.append(tr._subject_id)

    tr.switch_account("LEGAL_ENTITY")

    assert saved == ["id-company"]


@pytest.mark.parametrize(
    "account",
    ["id-company", "legal_entity", "LEGAL_ENTITY_ACTOR", "mustermann holding gmbh", "  Mustermann Holding GmbH "],
)
def test_switch_account_finds_the_account_by_id_type_or_name(account):
    tr = _api([BOTH, {}])

    assert tr.switch_account(account) == COMPANY


@pytest.mark.parametrize("account", ["Erika", "erika mustermann", "ADULT", "self"])
def test_switch_account_finds_a_person_by_first_or_full_name(account):
    tr = _api([BOTH, {}])

    assert tr.switch_account(account) == SELF


@pytest.mark.parametrize("account", ["Mustermann", "Holding", "LEGAL", "id-", ""])
def test_switch_account_does_not_match_on_parts_of_a_name(account):
    tr = _api([BOTH])

    with pytest.raises(ValueError, match="was not found"):
        tr.switch_account(account)


def test_switch_account_without_a_name_returns_to_the_own_account():
    tr = _switched([BOTH, {}])

    assert tr.switch_account() == SELF
    assert tr._websession.calls[1]["json"] == {"subjectId": "id-self"}
    assert tr._subject_id is None


def test_switch_account_reports_a_login_without_an_own_account():
    tr = _api([{"relationships": [COMPANY]}])

    with pytest.raises(ValueError, match="Your own account was not found"):
        tr.switch_account()


def test_switch_account_rejects_an_unknown_account_and_names_the_known_ones():
    tr = _api([BOTH])

    with pytest.raises(ValueError, match="'nope' was not found.*LEGAL_ENTITY \\(Mustermann Holding GmbH\\)"):
        tr.switch_account("nope")

    assert _calls(tr) == [("GET", RELATIONSHIPS)]


def test_switch_account_rejects_an_ambiguous_account_until_given_its_id():
    """Two companies share their type, so the type alone does not say which one is meant."""
    accounts = {"relationships": [SELF, COMPANY, SECOND_COMPANY]}
    tr = _api([accounts, accounts, {}])

    with pytest.raises(ValueError, match="more than one account, use its customer id"):
        tr.switch_account("LEGAL_ENTITY")

    assert tr.switch_account("id-second") == SECOND_COMPANY


def test_switch_account_rejects_an_account_without_a_customer_id():
    tr = _api([{"relationships": [SELF, {"accountType": "LEGAL_ENTITY", "accountName": "Nameless"}]}])

    with pytest.raises(ValueError, match="was not found"):
        tr.switch_account("LEGAL_ENTITY")


def test_switch_account_copes_with_fields_that_are_not_text():
    odd = {"customerId": 42, "firstName": 1, "lastName": None, "relationshipType": "LEGAL_ENTITY_ACTOR"}
    tr = _api([{"relationships": [SELF, odd]}, {}])

    assert tr.switch_account("42") == odd


def test_a_refused_switch_leaves_the_session_as_it_was():
    tr = _api([BOTH, (403, {})])
    tr._sec_acc_no = "own-depot"
    tr._session_expires_at = expires_at = 10**10
    tr.save_websession = lambda: pytest.fail("must not save the cookies of a refused switch")

    with pytest.raises(requests.HTTPError):
        tr.switch_account("LEGAL_ENTITY")

    assert (tr._subject_id, tr._sec_acc_no, tr._session_expires_at) == (None, "own-depot", expires_at)


def test_switch_account_refuses_while_the_websocket_is_connected():
    """An open websocket keeps answering for the account it was authenticated with."""
    tr = _api([])
    tr._ws = _Websocket({})

    with pytest.raises(ValueError, match="websocket"):
        tr.switch_account("LEGAL_ENTITY")

    assert tr._websession.calls == []


# --- keeping the session on the chosen account ---------------------------------------


def test_the_switch_counts_as_a_session_refresh():
    tr = _api([BOTH, {}, {}])
    tr._session_expires_at = 10**10  # far enough ahead that only the switch can have moved it

    tr.switch_account("LEGAL_ENTITY")
    tr._web_request("/api/v1/whatever")

    assert tr._session_expires_at < 10**10
    assert _calls(tr) == [("GET", RELATIONSHIPS), ("POST", SESSION_V2), ("GET", f"{HOST}/api/v1/whatever")]


def test_session_refresh_stays_on_the_chosen_account():
    """A refresh without the subject would silently return the session to the own account."""
    tr = _switched([{}, {}])
    tr._session_expires_at = 0

    tr._web_request("/api/v1/whatever")

    assert _calls(tr) == [("POST", SESSION_V2), ("GET", f"{HOST}/api/v1/whatever")]
    assert tr._websession.calls[0]["json"] == {"subjectId": "id-company"}


def test_a_new_process_starts_on_the_own_account():
    """Its first request refreshes without a subject, whatever account the saved cookies act for."""
    tr = _api([{}, {}], session_is_fresh=False)

    tr.settings()

    assert _calls(tr) == [("GET", SESSION_V1), ("GET", ACCOUNT)]


# --- portfolio -----------------------------------------------------------------------

PAIRS = {
    "authAccountId": "id-company",
    "accounts": [
        {"securitiesAccountNumber": "depot-other", "cashAccountNumber": "cash-other", "productType": "OTHER"},
        {"securitiesAccountNumber": "depot-company", "cashAccountNumber": "cash-company", "productType": "DEFAULT"},
    ],
}


def test_compact_portfolio_reads_the_securities_account_from_account_pairs_after_a_switch():
    tr = _switched()
    ws = _with_websocket(tr, {"accountPairs": [("A", "accountPairs", PAIRS)]})

    asyncio.run(tr.compact_portfolio())

    assert ws.subscriptions() == [
        {"type": "accountPairs"},
        {"type": "compactPortfolioByType", "secAccNo": "depot-company"},
    ]
    # The account settings are refused for this account, so they are not asked for.
    assert _calls(tr) == []
    assert "unsub 1" in ws.sent


def test_compact_portfolio_takes_the_first_pair_when_none_is_the_default_product():
    tr = _switched()
    pairs = {"accounts": [{"cashAccountNumber": "c"}, {"securitiesAccountNumber": "depot-a", "productType": "X"}]}
    ws = _with_websocket(tr, {"accountPairs": [("A", "accountPairs", pairs)]})

    asyncio.run(tr.compact_portfolio())

    assert ws.subscriptions()[-1]["secAccNo"] == "depot-a"


def test_compact_portfolio_keeps_the_answers_to_other_subscriptions():
    """Looking up the securities account must not swallow what the caller subscribed to before."""
    tr = _switched()
    _with_websocket(
        tr,
        {
            "cash": [],
            "accountPairs": [("A", "cash", [{"amount": 1}]), ("A", "accountPairs", PAIRS)],
            "compactPortfolioByType": [("A", "compactPortfolioByType", {"categories": []})],
        },
    )

    async def cash_then_portfolio():
        await tr.cash()
        await tr.compact_portfolio()
        return [await tr.recv(), await tr.recv()]

    received = asyncio.run(asyncio.wait_for(cash_then_portfolio(), 5))

    assert [(subscription["type"], payload) for _, subscription, payload in received] == [
        ("cash", [{"amount": 1}]),
        ("compactPortfolioByType", {"categories": []}),
    ]


@pytest.mark.parametrize(
    "answers",
    [
        [],  # no answer at all
        [("A", "accountPairs", {"authAccountId": "id-company", "accounts": []})],
        [("A", "accountPairs", {"authAccountId": "id-company", "accounts": None})],
    ],
)
def test_compact_portfolio_reports_a_missing_securities_account_after_a_switch(answers, monkeypatch):
    tr = _switched()
    ws = _with_websocket(tr, {"accountPairs": answers})
    lookup = tr._sec_acc_no_from_account_pairs
    monkeypatch.setattr(tr, "_sec_acc_no_from_account_pairs", lambda: lookup(timeout=0.05))

    with pytest.raises(ValueError, match="securities account number from account pairs"):
        asyncio.run(tr.compact_portfolio())

    assert "unsub 1" in ws.sent


def test_compact_portfolio_is_unchanged_for_the_own_account():
    tr = _api([{"securitiesAccountNumber": "own-depot"}])
    ws = _with_websocket(tr, {})

    asyncio.run(tr.compact_portfolio())

    assert _calls(tr) == [("GET", ACCOUNT)]
    assert ws.subscriptions() == [{"type": "compactPortfolioByType", "secAccNo": "own-depot"}]


def test_compact_portfolio_still_reports_account_settings_without_a_securities_account():
    tr = _api([{}])
    ws = _with_websocket(tr, {})

    with pytest.raises(ValueError, match="securities account number from account settings"):
        asyncio.run(tr.compact_portfolio())

    assert ws.sent == []


# --- pytr accounts -------------------------------------------------------------------


def test_get_accounts_prints_what_account_accepts():
    tr = _api([{"relationships": [SELF, COMPANY, {"customerId": "id-bare"}]}])

    assert account_module.get_accounts(tr).splitlines() == [
        "ADULT         Erika Mustermann         id-self     your own account",
        "LEGAL_ENTITY  Mustermann Holding GmbH  id-company  ACTIVE",
        "UNKNOWN                                id-bare",
    ]


def test_get_accounts_of_a_login_without_relationships_is_empty():
    assert account_module.get_accounts(_api([{}])) == ""


def test_the_accounts_command_exists_and_takes_the_login_arguments():
    args = get_main_parser().parse_args(["accounts", "--v2"])

    assert (args.command, args.v2, args.account) == ("accounts", True, None)


def test_every_command_that_logs_in_takes_an_account():
    parser = get_main_parser()

    for command in (["login"], ["portfolio"], ["details", "DE0000000000"], ["dl_docs", "out"], ["get_price_alarms"]):
        assert parser.parse_args([*command, "--account", "LEGAL_ENTITY"]).account == "LEGAL_ENTITY"


# --- login() -------------------------------------------------------------------------


class _LoggedIn:
    """Stands in for a TradeRepublicApi whose saved session could be resumed."""

    def __init__(self, switch_error=None):
        self._switch_error = switch_error
        self.events: list[Any] = []

    def resume_websession(self):
        return True

    def settings(self):
        self.events.append("settings")
        return {}

    def switch_account(self, account=None):
        self.events.append(("switch", account))
        if self._switch_error:
            raise self._switch_error


def _login(monkeypatch, tmp_path, tr, **kwargs):
    # login() creates the directory it stores credentials in; keep it off the real one.
    monkeypatch.setattr(account_module, "BASE_DIR", tmp_path / "pytr")
    monkeypatch.setattr(account_module, "CREDENTIALS_FILE", tmp_path / "pytr" / "credentials")
    monkeypatch.setattr(account_module, "TradeRepublicApi", lambda **_: tr)
    return account_module.login(phone_no="+490000000000", pin="0000", **kwargs)


def test_login_does_not_switch_by_default(monkeypatch, tmp_path):
    tr = _LoggedIn()

    assert _login(monkeypatch, tmp_path, tr) is tr
    assert tr.events == ["settings"]


def test_login_switches_to_the_requested_account(monkeypatch, tmp_path):
    tr = _LoggedIn()

    assert _login(monkeypatch, tmp_path, tr, account="LEGAL_ENTITY") is tr
    # The settings are read first: they are refused once the session acts for the other account.
    assert tr.events == ["settings", ("switch", "LEGAL_ENTITY")]


@pytest.mark.parametrize(
    "error",
    [ValueError("'nope' was not found"), requests.HTTPError("403", response=_Response({}, 403))],  # type: ignore[arg-type]
)
def test_login_exits_when_the_account_cannot_be_used(monkeypatch, tmp_path, error):
    with pytest.raises(SystemExit) as excinfo:
        _login(monkeypatch, tmp_path, _LoggedIn(switch_error=error), account="nope")

    assert excinfo.value.code == 1
