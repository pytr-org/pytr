import builtins
import logging
import os

from pytr import account


def test_login_does_not_store_pin(monkeypatch, tmp_path):
    credentials_file = tmp_path / "credentials"
    monkeypatch.setattr(account, "BASE_DIR", tmp_path)
    monkeypatch.setattr(account, "CREDENTIALS_FILE", credentials_file)
    monkeypatch.setattr(account, "TradeRepublicApi", lambda **kwargs: FakeApi(**kwargs))
    monkeypatch.setattr(account, "getpass", lambda prompt: "1234")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "123456")
    monkeypatch.setattr(account, "time", FakeTime)

    account.login(phone_no="+4912345678", store_credentials=True, waf_token="token")

    assert credentials_file.read_text() == "+4912345678\n"
    assert credentials_file.read_text().splitlines() == ["+4912345678"]
    assert os.stat(credentials_file).st_mode & 0o777 == 0o600


def test_legacy_credentials_are_migrated(monkeypatch, tmp_path):
    credentials_file = tmp_path / "credentials"
    credentials_file.write_text("+4912345678\n1234\n")
    monkeypatch.setattr(account, "BASE_DIR", tmp_path)
    monkeypatch.setattr(account, "CREDENTIALS_FILE", credentials_file)
    monkeypatch.setattr(account, "TradeRepublicApi", lambda **kwargs: FakeApi(**kwargs))
    monkeypatch.setattr(account, "getpass", lambda prompt: "5678")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "123456")
    monkeypatch.setattr(account, "time", FakeTime)

    account.login(waf_token="token")

    assert credentials_file.read_text() == "+4912345678\n"


def test_debug_log_does_not_include_response_payload(caplog):
    logger = logging.getLogger("security-test")
    logger.setLevel(logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="security-test"):
        logger.debug("Web login response received.")

    assert "1234" not in caplog.text
    assert "pin" not in caplog.text.lower()


class FakeApi:
    def __init__(self, **kwargs):
        self.pin = kwargs["pin"]

    def resume_websession(self):
        return False

    def initiate_weblogin(self):
        return 0

    def complete_weblogin(self, code):
        assert self.pin == "1234" or self.pin == "5678"


class FakeTime:
    @staticmethod
    def time():
        return 0

    @staticmethod
    def sleep(seconds):
        return None
