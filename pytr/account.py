import json
import sys
import time
from getpass import getpass

from pygments import formatters, highlight, lexers

from pytr.api import CREDENTIALS_FILE, TradeRepublicApi
from pytr.utils import get_logger


def get_settings(tr):
    formatted_json = json.dumps(tr.settings(), indent=2)
    if sys.stdout.isatty():
        colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter())
        return colorful_json
    else:
        return formatted_json


def login(phone_no=None, pin=None, web=True, store_credentials=False):
    """
    If web is true, use web login method, else simulate app login.
    Handle credentials parameters and store to credentials file if requested.
    If no parameters are set but are needed then ask for input
    """
    log = get_logger(__name__)
    save_cookies = True

    if phone_no is None and CREDENTIALS_FILE.is_file():
        log.info("Found credentials file")
        with open(CREDENTIALS_FILE) as f:
            lines = f.readlines()
        phone_no = lines[0].strip()
        pin = lines[1].strip()
        phone_no_masked = phone_no[:-8] + "********"
        pin_masked = len(pin) * "*"
        log.info(f"Phone: {phone_no_masked}, PIN: {pin_masked}")
    else:
        CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if phone_no is None:
            log.info("Credentials file not found")
            print("Please enter your TradeRepublic phone number in the format +4912345678:")
            phone_no = input()
        else:
            log.info("Phone number provided as argument")

        if pin is None:
            print("Please enter your TradeRepublic pin:")
            pin = getpass(prompt="Pin (Input is hidden):")

        if store_credentials:
            with open(CREDENTIALS_FILE, "w") as f:
                f.writelines([phone_no + "\n", pin + "\n"])

            log.info(f"Saved credentials in {CREDENTIALS_FILE}")
        else:
            save_cookies = False

    tr = TradeRepublicApi(phone_no=phone_no, pin=pin, save_cookies=save_cookies)

    if web:
        # Use same login as app.traderepublic.com
        if tr.resume_websession():
            log.info("Web session resumed")
        else:
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
    else:
        # Try to login. Ask for device reset if needed
        try:
            tr.login()
        except (KeyError, AttributeError):
            # old keyfile or no keyfile
            print("Error logging in. Reset device? (y)")
            confirmation = input()
            if confirmation == "y":
                tr.initiate_device_reset()
                print("You should have received a SMS with a token. Please type it in:")
                token = input()
                tr.complete_device_reset(token)
                print("Reset done")
            else:
                print("Cancelling reset")
                sys.exit(1)

    log.info("Logged in")
    # log.debug(get_settings(tr))
    return tr
