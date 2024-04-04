import json
import sys
from pygments import highlight, lexers, formatters
import time
import pathlib

from pytr.api import TradeRepublicApi, CREDENTIALS_FILE, COOKIES_FILE
from pytr.utils import get_logger


def get_settings(tr):
    formatted_json = json.dumps(tr.settings(), indent=2)
    if sys.stdout.isatty():
        colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter())
        return colorful_json
    else:
        return formatted_json


def login(phone_no=None, pin=None, web=True, save_credentials=False, credentials_file=None, save_cookies=True, cookies_file=None):
    '''
    If web is true, use web login method as else simulate app login.
    Check if credentials file exists else create it.
    If no parameters are set but are needed then ask for input
    '''
    log = get_logger(__name__)
    credentials_file = pathlib.Path(credentials_file) if credentials_file else CREDENTIALS_FILE

    if credentials_file.is_file():
        log.info('Found credentials file')
        with open(credentials_file) as f:
            lines = f.readlines()
        phone_no_cf = lines[0].strip()
        pin_cf = lines[1].strip()
        phone_no_masked = phone_no_cf[:-8] + '********'
        pin_masked = len(pin_cf) * '*'
        log.info(f'Phone: {phone_no_masked}, PIN: {pin_masked}')
    else:
        phone_no_cf = None
        pin_cf = None

    different_account = False
    if phone_no is not None and phone_no_cf is not None and phone_no != phone_no_cf:
        log.info('Phone number different from credential files. Assuming different account.')
        different_account = True

    if phone_no is None and phone_no_cf is None:
        credentials_file.parent.mkdir(parents=True, exist_ok=True)
        if phone_no is None:
            log.info('Credentials file not found')
            print('Please enter your TradeRepublic phone number in the format +4912345678:')
            phone_no = input()
        else:
            log.info('Phone number provided as argument')

        if pin is None:
            print('Please enter your TradeRepublic pin:')
            pin = input()

    if save_credentials:
        with open(credentials_file, 'w') as f:
            f.writelines([phone_no + '\n', pin + '\n'])
        log.info(f'Saved credentials in {credentials_file}')
    else:
        if different_account:
            save_cookies = False
        log.info('Credentials not saved')

    tr = TradeRepublicApi(phone_no=phone_no, pin=pin, save_cookies=save_cookies,
                          credentials_file=credentials_file, cookies_file=cookies_file)

    if web:
        # Use same login as app.traderepublic.com
        if not different_account and tr.resume_websession():
            log.info('Web session resumed')
        else:
            try:
                countdown = tr.inititate_weblogin()
            except ValueError as e:
                log.fatal(str(e))
                exit(1)
            request_time = time.time()
            print('Enter the code you received to your mobile app as a notification.')
            print(f'Enter nothing if you want to receive the (same) code as SMS. (Countdown: {countdown})')
            code = input('Code: ')
            if code == '':
                countdown = countdown - (time.time() - request_time)
                for remaining in range(int(countdown)):
                    print(f'Need to wait {int(countdown-remaining)} seconds before requesting SMS...', end='\r')
                    time.sleep(1)
                print()
                tr.resend_weblogin()
                code = input('SMS requested. Enter the confirmation code:')
            tr.complete_weblogin(code)
    else:
        # Try to login. Ask for device reset if needed
        try:
            tr.login()
        except (KeyError, AttributeError):
            # old keyfile or no keyfile
            print('Error logging in. Reset device? (y)')
            confirmation = input()
            if confirmation == 'y':
                tr.initiate_device_reset()
                print('You should have received a SMS with a token. Please type it in:')
                token = input()
                tr.complete_device_reset(token)
                print('Reset done')
            else:
                print('Cancelling reset')
                exit(1)

    log.info('Logged in')
    # log.debug(get_settings(tr))
    return tr
