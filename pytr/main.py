#!/usr/bin/env python

import argparse
import asyncio
import shutil
import signal
import sys
from datetime import datetime, timedelta
from importlib.metadata import version
from pathlib import Path

import shtab

from pytr.account import login
from pytr.alarms import Alarms
from pytr.details import Details
from pytr.dl import DL
from pytr.event import Event
from pytr.portfolio import PORTFOLIO_COLUMNS, Portfolio
from pytr.timeline import Timeline
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
    parser_help = parser_cmd.add_parser(
        "help",
        help="Print this help message",
        description="Print help message",
        add_help=False,
    )
    parser_help.add_argument("--for-readme", action="store_true", help=argparse.SUPPRESS)

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

    # portfolio
    info = "Show current portfolio"
    parser_portfolio = parser_cmd.add_parser(
        "portfolio",
        formatter_class=formatter,
        parents=[parser_login_args, parser_lang, parser_decimal_localization],
        help=info,
        description=info,
    )
    parser_portfolio.add_argument(
        "--include-watchlist",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Include watchlist.",
    )
    parser_portfolio.add_argument("-o", "--output", help="Output path of CSV file", type=Path)
    parser_portfolio.add_argument(
        "--sort-by-column",
        type=str.lower,
        choices=[col.lower() for col in PORTFOLIO_COLUMNS],
        default=None,
        help="Sort results by column.",
    )
    parser_portfolio.add_argument(
        "--sort-ascending",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Whether to sort in ascending order.",
    )

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
        help="Include data from the last N days (0 = include all days, -1 = no update)",
        metavar="DAYS",
        default=0,
        type=int,
    )
    parser_dl_docs.add_argument(
        "--days_until",
        help="Include data up to N days ago (0 = include all days)",
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
        "--store-event-database",
        default=True,
        help="Write and maintain an event database file (all_events.json)",
        action=argparse.BooleanOptionalAction,
    )
    parser_dl_docs.add_argument(
        "--scan-for-duplicates",
        default=False,
        help="Scan for duplicate events",
        action=argparse.BooleanOptionalAction,
    )
    parser_dl_docs.add_argument(
        "--dump-raw-data",
        default=False,
        help="Dump more raw data in json format",
        action=argparse.BooleanOptionalAction,
    )
    parser_dl_docs.add_argument(
        "--export-transactions",
        default=True,
        help="Export transactions into a file, e.g. as csv into account_transactions.csv",
        action=argparse.BooleanOptionalAction,
    )
    parser_dl_docs.add_argument(
        "--export-format",
        choices=("json", "csv"),
        default="csv",
        help="The output file format for the transaction export",
    )
    parser_dl_docs.add_argument(
        "--flat",
        default=False,
        help="Do not sort documents into folders and keep their original filenames",
        action="store_true",
    )

    # export_transactions
    info = (
        "Read data from the TR timeline and export transactions into a file, e.g. as csv into account_transactions.csv."
    )
    parser_export_transactions = parser_cmd.add_parser(
        "export_transactions",
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
    parser_export_transactions.add_argument(
        "--last_days",
        help="Include data from the last N days (0 = include all days, -1 = no update)",
        metavar="DAYS",
        default=0,
        type=int,
    )
    parser_export_transactions.add_argument(
        "--days_until",
        help="Include data up to N days ago (0 = include all days)",
        metavar="DAYS",
        default=0,
        type=int,
    )
    parser_export_transactions.add_argument(
        "--store-event-database",
        default=True,
        help="Write and maintain an event database file (all_events.json)",
        action=argparse.BooleanOptionalAction,
    )
    parser_export_transactions.add_argument(
        "--scan-for-duplicates",
        default=False,
        help="Scan for duplicate events",
        action=argparse.BooleanOptionalAction,
    )
    parser_export_transactions.add_argument(
        "--dump-raw-data",
        default=False,
        help="Dump more raw data in json format",
        action=argparse.BooleanOptionalAction,
    )
    parser_export_transactions.add_argument(
        "--export-format",
        "--format",
        choices=("json", "csv"),
        default="csv",
        help="The output file format for the transaction export",
    )
    parser_export_transactions.add_argument(
        "--outputdir",
        help="Output directory",
        metavar="PATH",
        type=Path,
        default=Path("."),
    )
    parser_export_transactions.add_argument(
        "outputfile",
        help="Output file path (optional)",
        type=argparse.FileType("w", encoding="utf-8"),
        nargs="?",
    )

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

    # completion
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
            sys.exit(1)

    except KeyboardInterrupt:
        print("Ok ok, quitting")
        sys.exit(1)
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

    # Compute the timestamp range to get data for
    not_before = 0
    if hasattr(args, "last_days"):
        if args.last_days < 0:
            not_before = float(-1)
        elif args.last_days == 0:
            not_before = float(0)
        else:
            not_before = (datetime.now().astimezone() - timedelta(days=args.last_days)).timestamp()
    not_after = (
        (datetime.now().astimezone() - timedelta(days=args.days_until)).timestamp()
        if hasattr(args, "days_until") and args.days_until > 0
        else float("inf")
    )

    if args.command == "login":
        login(
            phone_no=args.phone_no,
            pin=args.pin,
            web=not args.applogin,
            store_credentials=args.store_credentials,
        )
    elif args.command == "portfolio":
        p = Portfolio(
            login(
                phone_no=args.phone_no,
                pin=args.pin,
                web=not args.applogin,
                store_credentials=args.store_credentials,
            ),
            args.include_watchlist,
            lang=args.lang,
            decimal_localization=args.decimal_localization,
            output=args.output,
            sort_by_column=args.sort_by_column,
            sort_descending=not args.sort_ascending,
        )
        p.get()
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
    elif args.command == "dl_docs":
        DL(
            login(
                phone_no=args.phone_no,
                pin=args.pin,
                web=not args.applogin,
                store_credentials=args.store_credentials,
            ),
            args.output,
            args.format,
            not_before,
            not_after,
            args.store_event_database,
            args.scan_for_duplicates,
            args.dump_raw_data,
            args.export_transactions,
            max_workers=args.workers,
            universal_filepath=args.universal,
            lang=args.lang,
            date_with_time=args.date_with_time,
            decimal_localization=args.decimal_localization,
            sort_export=args.sort,
            format_export=args.export_format,
            flat=args.flat,
        ).do_dl()
    elif args.command == "export_transactions":
        if args.outputfile is None and args.outputdir is None:
            print("No output argument given.")
            return -1

        tl = Timeline(
            login(
                phone_no=args.phone_no,
                pin=args.pin,
                web=not args.applogin,
                store_credentials=args.store_credentials,
            ),
            args.outputdir,
            not_before,
            not_after,
            args.store_event_database,
            args.scan_for_duplicates,
            args.dump_raw_data,
        )
        asyncio.run(tl.tl_loop())
        events = tl.events

        with (
            (args.outputdir / ("account_transactions." + args.export_format)).open("w", encoding="utf-8")
            if args.outputfile is None
            else args.outputfile as f
        ):
            TransactionExporter(
                lang=args.lang,
                date_with_time=args.date_with_time,
                decimal_localization=args.decimal_localization,
            ).export(
                f,
                [Event.from_dict(item) for item in events],
                sort=args.sort,
                format=args.export_format,
            )
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
    elif args.version:
        installed_version = version("pytr")
        print(installed_version)
        check_version(installed_version)
    else:
        if hasattr(args, "for_readme") and args.for_readme:
            parser.formatter_class = lambda prog: argparse.ArgumentDefaultsHelpFormatter(
                "pytr", max_help_position=40, width=120
            )
        parser.print_help()


if __name__ == "__main__":
    main()
