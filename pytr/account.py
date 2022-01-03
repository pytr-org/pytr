import json
import sys
from pygments import highlight, lexers, formatters
from requests import HTTPError
import time

from pytr.api import TradeRepublicApi, CREDENTIALS_FILE
from pytr.utils import get_logger


def get_settings(tr):
    formatted_json = json.dumps(tr.settings(), indent=2)
    if sys.stdout.isatty():
        colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter())
        return colorful_json
    else:
        return formatted_json


def login(phone_no=None, pin=None, web=True):
    '''
    If web is true, use web login method as else simulate app login.
    Check if credentials file exists else create it.
    If no parameters are set but are needed then ask for input
    '''
    log = get_logger(__name__)

    if phone_no is None and CREDENTIALS_FILE.is_file():
        log.info('Found credentials file')
        with open(CREDENTIALS_FILE) as f:
            lines = f.readlines()
        phone_no = lines[0].strip()
        pin = lines[1].strip()
        phone_no_masked = phone_no[:-8] + '********'
        pin_masked = len(pin) * '*'
        log.info(f'Phone: {phone_no_masked}, PIN: {pin_masked}')
    else:
        CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if phone_no is None:
            log.info('Credentials file not found')
            print('Please enter your TradeRepbulic phone number in the format +4912345678:')
            phone_no = input()
        else:
            log.info('Phone number provided as argument')

        if pin is None:
            print('Please enter your TradeRepbulic pin:')
            pin = input()

        print('Save credentials? Type "y" to save credentials:')
        save = input()
        if save == 'y':
            with open(CREDENTIALS_FILE, 'w') as f:
                f.writelines([phone_no + '\n', pin + '\n'])

            log.info(f'Saved credentials in {CREDENTIALS_FILE}')

        else:
            log.info('Credentials not saved')

    tr = TradeRepublicApi(phone_no=phone_no, pin=pin)

    if web:
        # Use same login as app.traderepublic.com
        if tr.resume_websession():
            log.info('Web session resumed')
        else:
            countdown = tr.inititate_weblogin()
            request_time = time.time()
            print('Enter the code you received to your mobile app as a notification.')
            print(f'Enter nothing if you want to receive the code as SMS instead. (Countdown: {countdown})')
            code = input()
            if code == '':
                countdown = countdown - (time.time() - request_time)
                for remaining in range(countdown):
                    print(f'Need to wait {countdown-remaining} seconds...', end='\r')
                    time.sleep(1)
                tries = 0
                while tries <= 3:
                    try:
                        tries += 1
                        tr.resend_weblogin()
                    except HTTPError as e:
                        if e.response.status_code == 429:
                            errors = e.response.json()['errors']
                            if errors[0]['errorCode'] == 'TOO_MANY_REQUESTS':
                                towait = errors[0]['meta']['nextAttemptInSeconds']
                                for x in range(towait + 1):
                                    print(f'Too many requests: need to wait {towait-x} seconds', end='\r')
                                    time.sleep(1)
                                print()
                            else:
                                print('Error: {errors}')

                print('SMS requested. Enter the confirmation code:')
                code = input()
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
