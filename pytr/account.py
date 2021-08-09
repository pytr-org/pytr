import json
import os
import pathlib
import sys

from pygments import highlight, lexers, formatters

from pytr.api import TradeRepublicApi
from pytr.utils import get_logger


def get_settings(tr):
    formatted_json = json.dumps(tr.settings(), indent=2)
    if sys.stdout.isatty():
        colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter())
        return colorful_json
    else:
        return formatted_json


def reset(tr):
    tr.initiate_device_reset()
    print('You should have received a SMS with a token. Please type it in:')
    token = input()
    tr.complete_device_reset(token)
    print('Reset done')


def login(phone_no=None, pin=None):
    '''
    Check if credentials file exists else create it.
    If no parameters are set but are needed then ask for input
    Try to login. Ask for device reset if needed
    '''
    home = pathlib.Path.home()
    credentials_file = os.path.join(home, '.pytr', 'credentials')
    log = get_logger(__name__)

    if os.path.isfile(credentials_file):
        log.info('Found credentials file')
        with open(credentials_file) as f:
            lines = f.readlines()
        phone_no = lines[0].strip()
        pin = lines[1].strip()
        log.info(f'Phone: {phone_no}, PIN: {pin}')
    else:
        log.info('Credentials file not found')
        os.makedirs(os.path.dirname(credentials_file), exist_ok=True)
        if phone_no is None:
            print('Please enter your TradeRepbulic phone number in the format +49123456678:')
            phone_no = input()
        if pin is None:
            print('Please enter your TradeRepbulic pin:')
            pin = input()

        with open(credentials_file, 'w') as f:
            f.writelines([phone_no + '\n', pin + '\n'])

        log.info(f'Saved credentials in {credentials_file}')

    # use ~/.pytr/credentials and ~/.pytr/keyfile.pem
    tr = TradeRepublicApi()

    try:
        tr.login()
    except (KeyError, AttributeError):
        # old keyfile or no keyfile
        print('Error logging in. Reset device? (y)')
        confirmation = input()
        if confirmation == 'y':
            reset(tr)
        else:
            print('Cancelling reset')
            exit(1)
    log.info('Logged in')
    log.debug(get_settings(tr))
    return tr
