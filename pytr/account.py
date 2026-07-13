import json
import os
import sys
import time
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
    using_stored_phone = phone_no is None and CREDENTIALS_FILE.is_file()
    save_cookies = using_stored_phone or store_credentials

    if phone_no is None and CREDENTIALS_FILE.is_file():
        with open(CREDENTIALS_FILE) as f:
            lines = f.readlines()
        phone_no = lines[0].strip()
        if len(lines) > 1:
            fd = os.open(CREDENTIALS_FILE, os.O_WRONLY | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(phone_no + "\n")
            os.chmod(CREDENTIALS_FILE, 0o600)
            log.info("Removed the legacy stored PIN from the credentials file.")
        phone_no_masked = phone_no[:-8] + "********"
        log.info(f"Using phone number from file {CREDENTIALS_FILE}: {phone_no_masked}")
    else:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        if phone_no is None:
            print("Please enter your TradeRepublic phone number in the format +4912345678:")
            phone_no = input()

    if save_cookies:
        BASE_DIR.mkdir(parents=True, exist_ok=True)

    tr = TradeRepublicApi(phone_no=phone_no, pin=pin, save_cookies=save_cookies, waf_token=waf_token)

    # Use same login as app.traderepublic.com
    if not tr.resume_websession():
        if pin is None:
            print("Please enter your TradeRepublic pin:")
            pin = getpass(prompt="Pin (Input is hidden):")
            tr.pin = pin

        if store_credentials:
            fd = os.open(CREDENTIALS_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(phone_no + "\n")
            os.chmod(CREDENTIALS_FILE, 0o600)
            log.info(f"Storing phone number and session cookies in {BASE_DIR}; PIN is not stored")
        try:
            countdown = tr.initiate_weblogin()
        except ValueError as e:
            log.fatal(str(e))
            sys.exit(1)
        request_time = time.time()
        print("Enter the code you received to your mobile app as a notification.")
        print(f"Enter nothing if you want to receive the (same) code as SMS. (Countdown: {countdown})")
        code = input("Code: ")
        if code == "":
            countdown = countdown - (time.time() - request_time)
            for remaining in range(int(countdown)):
                print(
                    f"Need to wait {int(countdown - remaining)} seconds before requesting SMS...",
                    end="\r",
                )
                time.sleep(1)
            print()
            tr.resend_weblogin()
            code = input("SMS requested. Enter the confirmation code:")
        tr.complete_weblogin(code)
        log.info("Logged in.")

    log.debug("Account settings retrieved.")
    return tr
