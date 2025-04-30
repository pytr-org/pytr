[![GitHub tag (with filter)](https://img.shields.io/github/v/tag/pytr-org/pytr?style=for-the-badge&link=https%3A%2F%2Fgithub.com%2Fmarzzzello%2Fpytr%2Ftags)](https://github.com/pytr-org/pytr/tags)
[![PyPI build and publish](https://img.shields.io/github/actions/workflow/status/pytr-org/pytr/publish-pypi.yml?link=https%3A%2F%2Fgithub.com%2Fmarzzzello%2Fpytr%2Factions%2Fworkflows%2Fpublish-pypi.yml&style=for-the-badge)](https://github.com/pytr-org/pytr/actions/workflows/publish-pypi.yml)
[![PyPI - Version](https://img.shields.io/pypi/v/pytr?link=https%3A%2F%2Fpypi.org%2Fproject%2Fpytr%2F&style=for-the-badge)](https://pypi.org/project/pytr/)

# pytr: Use TradeRepublic in terminal

This is a library for the private API of the Trade Republic online brokerage. It is not affiliated with Trade Republic
Bank GmbH.

__Table of Contents__

<!-- toc -->
* [Quickstart](#quickstart)
* [Usage](#usage)
* [Authentication](#authentication)
  * [Web login (default)](#web-login-default)
  * [App login](#app-login)
* [Development](#development)
  * [Setting Up a Development Environment](#setting-up-a-development-environment)
  * [Linting and Code Formatting](#linting-and-code-formatting)
  * [Release process](#release-process)
  * [Keep the readme updated](#keep-the-readme-updated)
* [License](#license)
<!-- end toc -->

## Quickstart

This is the right section for you if all you want to do is to "just run the thing". Whether you've never run a piece
of code before, or are new to Python, these steps will make it the easiest for you to run pytr.

We strongly recommend that you use [`uv`](https://docs.astral.sh/uv/#installation) to run pytr. Since pytr is written
in the Python programming language, you usually need to make sure you have an installation of Python on your computer
before you can run any Python program. However, uv will take care of installing an appropriate Python version for
you if you don't already have one.

To install uv on OSX/Linux, run:

```console
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows, run:

```console
> powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then, to run the latest released version of pytr:

```console
$ uvx pytr@latest
```

If you want to use the cutting-edge version, use this command instead:

```console
$ uvx --with git+https://github.com/pytr-org/pytr.git pytr
```

## Usage

<!-- runcmd code:console COLUMNS=120 uv run --python 3.13 pytr -->
```console
usage: pytr [-h] [-V] [-v {warning,info,debug}] [--debug-logfile DEBUG_LOGFILE] [--debug-log-filter DEBUG_LOG_FILTER]
            {help,login,dl_docs,portfolio,details,get_price_alarms,set_price_alarms,export_transactions,completion} ...

Use "pytr command_name --help" to get detailed help to a specific command

Commands:
  {help,login,dl_docs,portfolio,details,get_price_alarms,set_price_alarms,export_transactions,completion}
                                        Desired action to perform
    help                                Print this help message
    login                               Check if credentials file exists. If not create it and ask for input. Try to
                                        login. Ask for device reset if needed
    dl_docs                             Download all pdf documents from the timeline and sort them into folders. Also
                                        export account transactions (account_transactions.csv) and JSON files with all
                                        events (events_with_documents.json and other_events.json)
    portfolio                           Show current portfolio
    details                             Get details for an ISIN
    get_price_alarms                    Get current price alarms
    set_price_alarms                    Set new price alarms
    export_transactions                 Create a CSV with the deposits and removals ready for importing into Portfolio
                                        Performance
    completion                          Print shell tab completion

Options:
  -h, --help                            show this help message and exit
  -V, --version                         Print version information and quit (default: False)
  -v, --verbosity {warning,info,debug}  Set verbosity level (default: info) (default: info)
  --debug-logfile DEBUG_LOGFILE         Dump debug logs to a file (default: None)
  --debug-log-filter DEBUG_LOG_FILTER   Filter debug log types (default: None)
```
<!-- end runcmd -->

## Authentication

There are two authentication methods:

### Web login (default)

Web login is the newer method that uses the same login method as [app.traderepublic.com](https://app.traderepublic.com/),
meaning you receive a four-digit code in the TradeRepublic app or via SMS. This will keep you logged in your primary
device, but means that you may need to repeat entering a new four-digit code ever so often when runnnig `pytr`.

### App login

App login is the older method that uses the same login method as the TradeRepublic app. First you need to perform a
device reset - a private key will be generated that pins your "device". The private key is saved to your keyfile. This
procedure will log you out from your mobile device.

```sh
$ pytr login
$ # or
$ pytr login --phone_no +49123456789 --pin 1234
```

If no arguments are supplied pytr will look for them in the file `~/.pytr/credentials` (the first line must contain
the phone number, the second line the pin). If the file doesn't exist pytr will ask for for the phone number and pin.

## Development

### Setting Up a Development Environment

Clone the repository:

```console
$ git clone https://github.com/pytr-org/pytr.git
```

Install dependencies:

```console
$ uv sync
```

Run the tests to ensure everything is set up correctly:

```console
$ uv run pytest
```

### Linting and Code Formatting

This project uses [Ruff](https://astral.sh/ruff) for code linting and auto-formatting, as well as
[Mypy](https://www.mypy-lang.org/) for type checking.

You can auto-format the code with Ruff by running:

```bash
uv run ruff format            # Format code
uv run ruff check --fix-only  # Remove unneeded imports, order imports, etc.
```

You can check the typing of the code with Mypy by running:

```bash
uv run mypy .
```

Ruff and Mypy run as part of CI and your Pull Request cannot be merged unless it satisfies the linting, formatting
checks and type checks.

### Release process

1. Create a pull request that bumps the version number in `pyproject.toml`
2. After successfully merging the PR, [create a new release](https://github.com/pytr-org/pytr/releases/new) via GitHub
   and make use of the "Generate release notes" button. Tags are formatted as `vX.Y.Z`.
3. The package will be published to PyPI from CI.

### Keep the readme updated

This readme contains a few automatically generated bits. To keep them up to date, simply run the following command:

```console
$ uvx mksync@0.1.4 -i README.md
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.