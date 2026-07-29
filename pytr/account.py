import json
import os
import sys
from getpass import getpass

from pygments import formatters, highlight, lexers

from .api import BASE_DIR, CREDENTIALS_FILE, TradeRepublicApi
from .utils import get_logger


def get_settings(tr):
    formatted_json = json.dumps(tr.settings(), indent=2)
    if sys.stdout.isatty():
        colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter())
        return colorful_json
    else:
        return formatted_json


def login(phone_no=None, pin=None, store_credentials=False, waf_token="playwright"):
    """
    Handle credentials parameters and store to credentials file if requested.
    If no parameters are set but are needed then ask for input
    """
    log = get_logger(__name__)
    save_cookies = True

    if phone_no is None and CREDENTIALS_FILE.is_file():
        with open(CREDENTIALS_FILE) as f:
            lines = f.readlines()
        phone_no = lines[0].strip()
        pin = lines[1].strip()
        phone_no_masked = phone_no[:-8] + "********"
        pin_masked = len(pin) * "*"
        log.info(f"Using credentials from file {CREDENTIALS_FILE}. Phone: {phone_no_masked}, PIN: {pin_masked}")
    else:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        if phone_no is None:
            print("Please enter your TradeRepublic phone number in the format +4912345678:")
            phone_no = input()

        if pin is None:
            print("Please enter your TradeRepublic pin:")
            pin = getpass(prompt="Pin (Input is hidden):")

        if store_credentials:
            with open(CREDENTIALS_FILE, "w") as f:
                f.writelines([phone_no + "\n", pin + "\n"])
            os.chmod(CREDENTIALS_FILE, 0o600)

            log.info(f"Storing credentials/cookies in {BASE_DIR}")
        else:
            save_cookies = False

    tr = TradeRepublicApi(phone_no=phone_no, pin=pin, save_cookies=save_cookies, waf_token=waf_token)

    # Use same login as app.traderepublic.com
    if not tr.resume_websession():
        try:
            countdown = tr.initiate_weblogin()
        except ValueError as e:
            log.fatal(str(e))
            sys.exit(1)
        if tr.weblogin_needs_authenticator:
            code = input("Enter the code from your authenticator app: ")
        else:
            print(f"Confirm the login in your Trade Republic app. (Countdown: {countdown})")
            code = None
        tr.complete_weblogin(code)
        log.info("Logged in.")

    log.debug(get_settings(tr))
    return tr
