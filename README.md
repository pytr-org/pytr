[![GitHub tag (with filter)](https://img.shields.io/github/v/tag/pytr-org/pytr?style=for-the-badge&link=https%3A%2F%2Fgithub.com%2Fmarzzzello%2Fpytr%2Ftags)](https://github.com/pytr-org/pytr/tags)
[![PyPI build and publish](https://img.shields.io/github/actions/workflow/status/pytr-org/pytr/publish-pypi.yml?link=https%3A%2F%2Fgithub.com%2Fmarzzzello%2Fpytr%2Factions%2Fworkflows%2Fpublish-pypi.yml&style=for-the-badge)](https://github.com/pytr-org/pytr/actions/workflows/publish-pypi.yml)
[![PyPI - Version](https://img.shields.io/pypi/v/pytr?link=https%3A%2F%2Fpypi.org%2Fproject%2Fpytr%2F&style=for-the-badge)](https://pypi.org/project/pytr/)

# pytr: Use TradeRepublic in terminal

This is a library for the private API of the Trade Republic online brokerage. I am not affiliated with Trade Republic Bank GmbH.

## Installation

Make sure Python and a Python package manager like pip or [pipx](https://pipx.pypa.io/) (recommended) is installed.

Install release from PyPI with: 
```sh
pipx install pytr
```

Or install from git repo like so:

```sh
pipx install git+https://github.com/pytr-org/pytr.git
```

### Update

```sh
pipx upgrade pytr
# or
pipx upgrade-all
```


## Usage

```
$ pytr help
usage: pytr [-h] [-v {warning,info,debug}] [-V]
            {help,login,dl_docs,portfolio,details,get_price_alarms,set_price_alarms,export_transactions,completion}
            ...

Use "pytr command_name --help" to get detailed help to a specific command

Commands:
  {help,login,dl_docs,portfolio,details,get_price_alarms,set_price_alarms,export_transactions,completion}
                         Desired action to perform
    help                 Print this help message
    login                Check if credentials file exists. If not create it
                         and ask for input. Try to login. Ask for device reset
                         if needed
    dl_docs              Download all pdf documents from the timeline and sort
                         them into folders. Also export account transactions
                         (account_transactions.csv) and JSON files with all
                         events (events_with_documents.json and
                         other_events.json). A folder path must be provided
                         as second argument.
    portfolio            Show current portfolio
    details              Get details for an ISIN
    get_price_alarms     Get overview of current price alarms
    set_price_alarms     Set price alarms based on diff from current price
    export_transactions  Create a CSV with the deposits and removals ready for
                         importing into Portfolio Performance
    completion           Print shell tab completion

Options:
  -h, --help             show this help message and exit
  -v {warning,info,debug}, --verbosity {warning,info,debug}
                         Set verbosity level (default: info)
  -V, --version          Print version information and quit

```

## Authentication

There are two authentication methods:

- Web login (default)
- App login

Web login is the newer method that uses the same login method as [app.traderepublic.com](https://app.traderepublic.com/), meaning you receive a token in the TradeRepublic app or via SMS.

App login is the older method that uses the same login method as the TradeRepublic app.
First you need to perform a device reset - a private key will be generated that pins your "device". The private key is saved to your keyfile. This procedure will log you out from your mobile device.

```sh
$ pytr login
$ # or
$ pytr login --phone_no +49123456789 --pin 1234
```

If no arguments are supplied pytr will look for them in the file `~/.pytr/credentials` (the first line must contain the phone number, the second line the pin). If the file doesn't exist pytr will ask for for the phone number and pin.

## Location and File names of the downloaded Documents
It is possible to use a custom configuration to setup the file path and file name. If the parameter `--use_destination_config True` is used during the first run of the 'dl_docs' command a config file is created in the user home directory `<home>/.pytr/file_destination_config.yaml`.
The file contains destination patterns which describe where the file should be located and how the file name should look like. If a event/document matches the defined pattern it will be located in that specific `path` with the specified `filename`.

There are three mandatory patterns defined at the top:
* `default` - Defines only `filename` and is used for all other patterns if no "filename" is provided
* `unknown` - Defines `filename` and `path`, this is used when no match can be found for the event and the given document.
* `multiple_match` - If there are multiple matching patterns and the destination would be ambiguous, the document will be stored in the given `path` with the given `filename`

The other pattern can be as you like but keep in mind that patterns `path` and `filenames` should result in unique document names. If you see something like this `<filename> (some strange string)` the document path + name was not unique. Which means there were multiple documents to be downloaded which have locally the same name and to avoid conflicts and not to override each other a string is appended to keep both files.

> Its also possible to copy the configuration file from `~/pytr/config/file_destination_config__template.yaml` to `<home>/.pytr/file_destination_config.yaml` and modify it before the first download to avoid that the download need to be performed a second time.
> It is also possible to delete the download folder and run the download again when you have changed the config file.


## Linting and Code Formatting

This project uses [black](https://github.com/psf/black) for code linting and auto-formatting. You can auto-format the code by running:

```bash
# Install black if not already installed
pip install black

# Auto-format code
black ./pytr
```

## Setting Up a Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/pytr-org/pytr.git
   ```

2. Install dependencies:
   ```bash
   pip install .
   ```

3. Run the tests to ensure everything is set up correctly:
   ```bash
   pytest
   ```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.