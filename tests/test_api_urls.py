"""Pin the web login endpoints, their required headers and the login process state machine."""

import base64
import json as jsonlib
import re
from typing import Any

import pytest
import requests

from pytr.api import TradeRepublicApi

LOGIN = "https://api.traderepublic.com/api/v2/auth/web/login"
PROCESS = "https://api.traderepublic.com/api/v2/auth/web/login/processes/pid-1"


def _error(code: str) -> dict[str, Any]:
    return {"errors": [{"errorCode": code, "errorMessage": None, "meta": None}]}


class _Response:
    def __init__(self, url: str, payload: Any = None, status_code: int = 200):
        self.url = url
        self.status_code = status_code
        self._payload = {} if payload is None else payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            # Mirrors requests: the message carries the URL, and with it the process id.
            raise requests.HTTPError(f"{self.status_code} Client Error for url: {self.url}")

    def json(self) -> Any:
        return self._payload


class _Session:
    """Records requests instead of sending them. Replies come from a queue."""

    def __init__(self, replies: list[Any]):
        self.calls: list[dict[str, Any]] = []
        self._replies = list(replies)
        self.cookies = None
        self.headers = dict(TradeRepublicApi._default_headers)

    def _record(self, method: str, url: str, json: Any = None, headers: Any = None) -> _Response:
        self.calls.append({"method": method, "url": url, "json": json, "headers": headers or {}})
        reply = self._replies.pop(0) if self._replies else {}
        status, payload = reply if isinstance(reply, tuple) else (200, reply)
        return _Response(url, payload, status)

    def post(self, url, json=None, headers=None):
        return self._record("POST", url, json, headers)

    def get(self, url, headers=None):
        return self._record("GET", url, None, headers)

    def request(self, method, url, data=None):
        return self._record(method, url, None, None)


def _api(replies):
    tr = TradeRepublicApi(phone_no="+490000000000", pin="0000", waf_token=None, use_v2_login=True)
    tr._websession = _Session(replies)
    return tr


def _urls(tr):
    return [c["url"] for c in tr._websession.calls]


# --- initiate_weblogin ---------------------------------------------------------------


def test_initiate_weblogin_uses_v2():
    tr = _api([{"processId": "pid-1", "countdownInSeconds": 60}, {"status": "PENDING"}])

    countdown = tr.initiate_weblogin()

    assert tr._websession.calls[0]["url"] == LOGIN
    assert tr._websession.calls[0]["json"] == {"phoneNumber": "+490000000000", "pin": "0000"}
    assert tr._process_id == "pid-1"
    assert countdown == 61


def test_initiate_weblogin_without_countdown_defaults_to_120():
    tr = _api([{"processId": "pid-1"}, {"status": "PENDING"}])

    assert tr.initiate_weblogin() == 121


def test_initiate_weblogin_reads_required_action_from_the_process():
    """The second factor sits on the login process, not in the login response."""
    tr = _api([{"processId": "pid-1"}, {"requiredAction": "AUTHENTICATOR_VERIFICATION"}])

    tr.initiate_weblogin()

    assert _urls(tr)[1] == PROCESS
    assert tr.weblogin_needs_authenticator is True


def test_initiate_weblogin_falls_back_to_in_app_when_process_unreadable():
    tr = _api([{"processId": "pid-1"}, (500, _error("UNKNOWN_ERROR"))])

    tr.initiate_weblogin()

    assert tr.weblogin_needs_authenticator is False


def test_initiate_weblogin_rejects_a_null_process_id():
    tr = _api([{"processId": None}])

    with pytest.raises(ValueError, match="without a confirmation step"):
        tr.initiate_weblogin()


# --- complete_weblogin ---------------------------------------------------------------


def test_complete_weblogin_posts_code_to_authenticator_verification():
    tr = _api([{}])
    tr._process_id = "pid-1"
    tr._required_action = "AUTHENTICATOR_VERIFICATION"

    tr.complete_weblogin("123456")

    call = tr._websession.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == f"{PROCESS}/authenticator-verification"
    assert call["json"] == {"code": "123456"}


def test_complete_weblogin_requires_a_code_when_authenticator_is_needed():
    tr = _api([])
    tr._process_id = "pid-1"
    tr._required_action = "AUTHENTICATOR_VERIFICATION"

    with pytest.raises(ValueError, match="authenticator app"):
        tr.complete_weblogin(None)


def test_complete_weblogin_polls_the_process_for_in_app_confirmation():
    tr = _api([{"status": "PENDING"}, {"status": "CONFIRMED"}])
    tr._process_id = "pid-1"

    tr.complete_weblogin(None)

    assert [c["method"] for c in tr._websession.calls] == ["GET", "GET"]
    assert set(_urls(tr)) == {PROCESS}


# --- login process state machine -----------------------------------------------------


@pytest.mark.parametrize("status", ["CONFIRMED", "COMPLETED"])
def test_poll_accepts_both_terminal_states(status):
    tr = _api([{"status": status}])
    tr._process_id = "pid-1"

    tr._await_weblogin_confirmation(interval=0)


def test_poll_reports_a_rejected_login():
    tr = _api([(410, _error("ALREADY_PROCESSED"))])
    tr._process_id = "pid-1"

    with pytest.raises(ValueError, match="rejected"):
        tr._await_weblogin_confirmation(interval=0)


def test_poll_reports_an_expired_login():
    tr = _api([(410, _error("PROCESS_GONE"))])
    tr._process_id = "pid-1"

    with pytest.raises(ValueError, match="expired"):
        tr._await_weblogin_confirmation(interval=0)


def test_poll_times_out_at_the_server_side_expiry():
    tr = _api([{"status": "PENDING", "expiresAt": "2020-01-01T00:00:00Z"}])
    tr._process_id = "pid-1"

    with pytest.raises(TimeoutError):
        tr._await_weblogin_confirmation(interval=0)


def test_deadline_prefers_expires_at_over_the_fallback():
    tr = _api([])

    assert tr._weblogin_deadline({"expiresAt": "2999-01-01T00:00:00Z"}) > tr._weblogin_deadline({}) + 60


def test_login_errors_do_not_leak_the_process_id():
    """raise_for_status() would put the URL, and with it the process id, into the message."""
    tr = _api([(410, _error("PROCESS_GONE"))])
    tr._process_id = "pid-1"

    with pytest.raises(ValueError) as excinfo:
        tr._await_weblogin_confirmation(interval=0)

    assert "pid-1" not in str(excinfo.value)
    assert "http" not in str(excinfo.value)


def test_resend_weblogin_warns_instead_of_calling_a_removed_endpoint():
    tr = _api([])

    tr.resend_weblogin()

    assert tr._websession.calls == []


# --- required headers ----------------------------------------------------------------

REQUIRED_HEADERS = ("X-TR-Device-Info", "X-TR-App-Version", "X-Tr-Platform")


def _every_login_call():
    """Every v2 login call pytr makes: start, poll, authenticator verification."""
    poll = _api([{"processId": "pid-1"}, {"status": "PENDING"}, {"status": "CONFIRMED"}])
    poll.initiate_weblogin()
    poll.complete_weblogin(None)

    verify = _api([{}])
    verify._process_id = "pid-1"
    verify._required_action = "AUTHENTICATOR_VERIFICATION"
    verify.complete_weblogin("123456")

    return poll._websession.calls + verify._websession.calls


def test_every_v2_login_call_sends_the_required_headers():
    """Without them Trade Republic answers 400 MISSING_REQUIRED_HEADER."""
    calls = _every_login_call()

    assert [c["url"] for c in calls] == [LOGIN, PROCESS, PROCESS, f"{PROCESS}/authenticator-verification"]
    for call in calls:
        for header in REQUIRED_HEADERS:
            assert call["headers"].get(header), f"{header} missing on {call['method']} {call['url']}"


def test_device_info_is_base64_encoded_json():
    device = jsonlib.loads(base64.b64decode(_api([])._login_headers()["X-TR-Device-Info"]))

    # The frontend hashes a canvas fingerprint with SHA-512; same length, same alphabet.
    assert re.fullmatch(r"[0-9a-f]{128}", device["stableDeviceId"])
    assert device["browser"] == "Chrome"
    # Taken from the User-Agent, so the two cannot drift apart.
    assert device["browserVersion"] in TradeRepublicApi._default_headers["User-Agent"]


def test_device_info_is_the_same_for_every_login():
    """The frontend builds it once per page load; ours must not wander between runs."""
    assert _api([])._login_headers()["X-TR-Device-Info"] == _api([])._login_headers()["X-TR-Device-Info"]


def test_app_version_and_platform_come_from_the_web_frontend():
    headers = _api([])._login_headers()

    # A build version of the frontend, not a pytr version.
    assert re.fullmatch(r"\d+\.\d+\.\d+", headers["X-TR-App-Version"])
    assert headers["X-Tr-Platform"] == "web-pro"


# --- endpoints that must NOT move ----------------------------------------------------


def test_settings_stays_on_v2_account_and_v1_session():
    """Neither endpoint was part of the v1 login removal."""
    tr = _api([{}, {}])
    tr._session_expires_at = 0

    tr.settings()

    assert _urls(tr) == [
        "https://api.traderepublic.com/api/v1/auth/web/session",
        "https://api.traderepublic.com/api/v2/auth/account",
    ]
