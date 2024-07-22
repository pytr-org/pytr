import pathlib

home = pathlib.Path.home()
BASE_DIR = home / '.pytr'

CREDENTIALS_FILE = BASE_DIR / 'credentials'
KEY_FILE = BASE_DIR / 'keyfile.pem'
COOKIES_FILE = BASE_DIR / 'cookies.txt'

DESTINATION_CONFIG_FILE = BASE_DIR / 'file_destination_config.yaml'