#!/usr/bin/env python

import argparse
import asyncio
import json
import shutil
import signal
from datetime import datetime, timedelta
from importlib.metadata import version
from pathlib import Path

import shtab

from pytr.account import login
from pytr.alarms import Alarms
from pytr.details import Details
from pytr.dl import DL
from pytr.event import Event
from pytr.portfolio import Portfolio
from pytr.transactions import SUPPORTED_LANGUAGES, TransactionExporter
from pytr.utils import check_version, get_logger


def get_main_parser():
    def formatter(prog):
        width = min(shutil.get_terminal_size().columns // 3, 80)
        return argparse.ArgumentDefaultsHelpFormatter(prog, max_help_position=width)

    parser = argparse.ArgumentParser(
        formatter_class=formatter,
        description='Use "%(prog)s command_name --help" to get detailed help to a specific command',
    )
    for grp in parser._action_groups:
        if grp.title == "options":
            grp.title = "Options"
        elif grp.title == "positional arguments":
            grp.title = "Commands"

    parser.add_argument(
        "-V",
        "--version",
        help="Print version information and quit",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        help="Set verbosity level (default: info)",
        choices=["warning", "info", "debug"],
        default="info",
    )
    parser.add_argument(
        "--debug-logfile",
        help="Dump debug logs to a file",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--debug-log-filter",
        help="Filter debug log types",
        default=None,
    )

    parser_cmd = parser.add_subparsers(help="Desired action to perform", dest="command")

    # help
    parser_cmd.add_parser(
        "help",
        help="Print this help message",
        description="Print help message",
        add_help=False,
    )

    # parent subparser with common login arguments
    parser_login_args = argparse.ArgumentParser(add_help=False)
    parser_login_args.add_argument("--applogin", help="Use app login instead of  web login", action="store_true")
    parser_login_args.add_argument("-n", "--phone_no", help="TradeRepublic phone number (international format)")
    parser_login_args.add_argument("-p", "--pin", help="TradeRepublic pin")
    parser_login_args.add_argument(
        "--store_credentials",
        help="Store credentials (Phone number, pin, cookies) for next usage",
        action="store_true",
        default=False,
    )

    # parent subparser for lang option
    parser_lang = argparse.ArgumentParser(add_help=False)
    parser_lang.add_argument(
        "-l",
        "--lang",
        help='Two letter language code or "auto" for system language.',
        choices=["auto", *sorted(SUPPORTED_LANGUAGES)],
        default="auto",
    )

    # parent subparser for date-with-time option
    parser_date_with_time = argparse.ArgumentParser(add_help=False)
    parser_date_with_time.add_argument(
        "--date-with-time",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether to include the timestamp in the date column.",
    )

    # parent subparser for decimal-localization option
    parser_decimal_localization = argparse.ArgumentParser(add_help=False)
    parser_decimal_localization.add_argument(
        "--decimal-localization",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Whether to localize decimal numbers.",
    )

    # parent subparser for sorting option
    parser_sort_export = argparse.ArgumentParser(add_help=False)
    parser_sort_export.add_argument(
        "-s",
        "--sort",
        help="Chronologically sort exported csv transactions",
        action="store_true",
    )

    # login
    info = (
        "Check if credentials file exists. If not create it and ask for input. Try to login."
        + " Ask for device reset if needed"
    )
    parser_cmd.add_parser(
        "login",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )

    # dl_docs
    info = (
        "Download all pdf documents from the timeline and sort them into folders."
        + " Also export account transactions (account_transactions.csv)"
        + " and JSON files with all events (events_with_documents.json and other_events.json)"
    )
    parser_dl_docs = parser_cmd.add_parser(
        "dl_docs",
        formatter_class=formatter,
        parents=[
            parser_login_args,
            parser_lang,
            parser_date_with_time,
            parser_decimal_localization,
            parser_sort_export,
        ],
        help=info,
        description=info,
    )

    parser_dl_docs.add_argument("output", help="Output directory", metavar="PATH", type=Path)
    parser_dl_docs.add_argument(
        "--format",
        help="available variables:\tiso_date, time, title, subtitle, doc_num, id",
        metavar="FORMAT_STRING",
        default="{iso_date} {time} {title}",
    )
    parser_dl_docs.add_argument(
        "--last_days",
        help="Number of last days to include (use 0 get all days)",
        metavar="DAYS",
        default=0,
        type=int,
    )
    parser_dl_docs.add_argument(
        "--workers",
        help="Number of workers for parallel downloading",
        default=8,
        type=int,
    )
    parser_dl_docs.add_argument("--universal", help="Platform independent file names", action="store_true")
    parser_dl_docs.add_argument(
        "--export-format",
        choices=("json", "csv"),
        default="csv",
        help="The output file format.",
    )

    # portfolio
    info = "Show current portfolio"
    parser_portfolio = parser_cmd.add_parser(
        "portfolio",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_portfolio.add_argument("-o", "--output", help="Output path of CSV file", type=Path)

    # details
    info = "Get details for an ISIN"
    parser_details = parser_cmd.add_parser(
        "details",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_details.add_argument("isin", help="ISIN of intrument")

    # get_price_alarms
    info = "Get current price alarms"
    parser_get_price_alarms = parser_cmd.add_parser(
        "get_price_alarms",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_get_price_alarms.add_argument(
        "input", nargs="*", help="Input data in the form of <ISIN1> <ISIN2> ...", default=[]
    )
    parser_get_price_alarms.add_argument(
        "--outputfile",
        help="Output file path",
        type=argparse.FileType("w", encoding="utf-8"),
        default="-",
        nargs="?",
    )

    # set_price_alarms
    info = "Set new price alarms"
    parser_set_price_alarms = parser_cmd.add_parser(
        "set_price_alarms",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_set_price_alarms.add_argument(
        "input", nargs="*", help="Input data in the form of <ISIN> <alarm1> <alarm2> ...", default=[]
    )
    parser_set_price_alarms.add_argument(
        "--remove-current-alarms",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether to remove current alarms.",
    )
    parser_set_price_alarms.add_argument(
        "--inputfile",
        help="Input file path",
        type=argparse.FileType("r", encoding="utf-8"),
        default="-",
        nargs="?",
    )

    # export_transactions
    info = "Create a CSV with the deposits and removals ready for importing into Portfolio Performance"
    parser_export_transactions = parser_cmd.add_parser(
        "export_transactions",
        formatter_class=formatter,
        parents=[parser_lang, parser_date_with_time, parser_decimal_localization, parser_sort_export],
        help=info,
        description=info,
    )
    parser_export_transactions.add_argument(
        "input",
        help="Input path to JSON (use all_events.json from dl_docs)",
        type=argparse.FileType("r", encoding="utf-8"),
    )
    parser_export_transactions.add_argument(
        "output",
        help="Output file path",
        type=argparse.FileType("w", encoding="utf-8"),
        default="-",
        nargs="?",
    )
    parser_export_transactions.add_argument(
        "--format",
        choices=("json", "csv"),
        default="csv",
        help="The output file format.",
    )

    info = "Print shell tab completion"
    parser_completion = parser_cmd.add_parser(
        "completion",
        formatter_class=formatter,
        help=info,
        description=info,
    )
    shtab.add_argument_to(parser_completion, "shell", parent=parser)
    return parser


def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in input when CTRL+C is pressed, and our signal handler is not re-entrant
    global original_sigint
    signal.signal(signal.SIGINT, original_sigint)

    try:
        if input("\nReally quit? (y/n)> ").lower().startswith("y"):
            exit(1)

    except KeyboardInterrupt:
        print("Ok ok, quitting")
        exit(1)

    # restore the exit gracefully handler here
    signal.signal(signal.SIGINT, exit_gracefully)


def main():
    # store the original SIGINT handler
    global original_sigint
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)

    parser = get_main_parser()
    args = parser.parse_args()
    # print(vars(args))

    log = get_logger(__name__, args.verbosity, args.debug_logfile, args.debug_log_filter)
    if args.verbosity.upper() == "DEBUG":
        log.debug("logging is set to debug")

    if args.command == "login":
        login(
            phone_no=args.phone_no,
            pin=args.pin,
            web=not args.applogin,
            store_credentials=args.store_credentials,
        )

    elif args.command == "dl_docs":
        if args.last_days == 0:
            since_timestamp = 0
        else:
            since_timestamp = (datetime.now().astimezone() - timedelta(days=args.last_days)).timestamp()
        dl = DL(
            login(
                phone_no=args.phone_no,
                pin=args.pin,
                web=not args.applogin,
                store_credentials=args.store_credentials,
            ),
            args.output,
            args.format,
            since_timestamp=since_timestamp,
            max_workers=args.workers,
            universal_filepath=args.universal,
            lang=args.lang,
            date_with_time=args.date_with_time,
            decimal_localization=args.decimal_localization,
            sort_export=args.sort,
            format_export=args.export_format,
        )
        asyncio.get_event_loop().run_until_complete(dl.dl_loop())
    elif args.command == "get_price_alarms":
        try:
            Alarms(
                login(
                    phone_no=args.phone_no,
                    pin=args.pin,
                    web=not args.applogin,
                    store_credentials=args.store_credentials,
                ),
                args.input,
                args.outputfile,
            ).get()
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "set_price_alarms":
        try:
            Alarms(
                login(
                    phone_no=args.phone_no,
                    pin=args.pin,
                    web=not args.applogin,
                    store_credentials=args.store_credentials,
                ),
                args.input,
                args.inputfile,
                args.remove_current_alarms,
            ).set()
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "details":
        Details(
            login(
                phone_no=args.phone_no,
                pin=args.pin,
                web=not args.applogin,
                store_credentials=args.store_credentials,
            ),
            args.isin,
        ).get()
    elif args.command == "portfolio":
        p = Portfolio(
            login(
                phone_no=args.phone_no,
                pin=args.pin,
                web=not args.applogin,
                store_credentials=args.store_credentials,
            )
        )
        p.get()
        if args.output is not None:
            p.portfolio_to_csv(args.output)
    elif args.command == "export_transactions":
        events = [Event.from_dict(item) for item in json.load(args.input)]
        TransactionExporter(
            lang=args.lang,
            date_with_time=args.date_with_time,
            decimal_localization=args.decimal_localization,
        ).export(
            fp=args.output,
            events=events,
            sort=args.sort,
            format=args.format,
        )
    elif args.version:
        installed_version = version("pytr")
        print(installed_version)
        check_version(installed_version)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
