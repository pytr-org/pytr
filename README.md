# pytr: Use TradeRepublic in terminal

This is a library for the private API of the Trade Republic online brokerage. I am not affiliated with Trade Republic Bank GmbH.

## Installation

Install with `pip install pytr`

Or you can clone the repo like so:

```sh
git clone https://github.com/marzzzello/pytr.git
cd pytr
pip install .
```

## Usage

```
$ pytr help
usage: pytr [-h] [-s {bash,zsh,tcsh}] [-v {warning,info,debug}] [--applogin] [-V]
            {help,login,dl_docs,portfolio,details,get_price_alarms,set_price_alarms,export_transactions}

positional arguments:
  {help,login,dl_docs,portfolio,details,get_price_alarms,set_price_alarms,export_transactions}
                         Desired action to perform
    help                 Print this help message
    login                Check if credentials file exists. If not create it
                         and ask for input. Try to login. Ask for device reset
                         if needed
    dl_docs              Download all pdf documents from the timeline and sort
                         them into folders
    portfolio            Show current portfolio
    details              Get details for an ISIN
    get_price_alarms     Get overview of current price alarms
    set_price_alarms     Set price alarms based on diff from current price
    export_transactions  Create a CSV with the deposits and removals ready for
                         importing into Portfolio Performance

options:
  -h, --help             show this help message and exit
  -s {bash,zsh,tcsh}, --print-completion {bash,zsh,tcsh}
                         print shell completion script
  -v {warning,info,debug}, --verbosity {warning,info,debug}
                         Set verbosity level (default: info)
  --applogin             Use app login instead of web login
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
