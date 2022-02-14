#!/usr/bin/env python

import argparse
import asyncio
import signal
import time

import shtab

from importlib.metadata import version
from pathlib import Path

from pytr.utils import get_logger, check_version, export_transactions
from pytr.dl import DL
from pytr.account import login
from pytr.portfolio import Portfolio
from pytr.alarms import Alarms
from pytr.details import Details


def get_main_parser():
    def formatter(prog):
        return argparse.HelpFormatter(prog, max_help_position=25)

    parser = argparse.ArgumentParser(formatter_class=formatter)
    shtab.add_argument_to(parser, ['-s', '--print-completion'])  # magic!

    parser.add_argument(
        '-v',
        '--verbosity',
        help='Set verbosity level (default: info)',
        choices=['warning', 'info', 'debug'],
        default='info',
    )
    parser.add_argument('--applogin', help='Use app login instead of  web login', action='store_true')
    parser.add_argument('-V', '--version', help='Print version information and quit', action='store_true')
    parser_cmd = parser.add_subparsers(help='Desired action to perform', dest='command')

    # help
    parser_cmd.add_parser('help', help='Print this help message')

    # Create parent subparser with common login arguments
    parser_login_args = argparse.ArgumentParser(add_help=False)
    parser_login_args.add_argument('-n', '--phone_no', help='TradeRepbulic phone number (international format)')
    parser_login_args.add_argument('-p', '--pin', help='TradeRepbulic pin')

    # login
    parser_login = parser_cmd.add_parser(
        'login',
        parents=[parser_login_args],
        help='Check if credentials file exists. If not create it and ask for input.'
        + ' Try to login. Ask for device reset if needed',
    )
    # dl_docs
    parser_dl_docs = parser_cmd.add_parser(
        'dl_docs',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[parser_login_args],
        help='Download all pdf documents from the timeline and sort them into folders',
    )
    parser_dl_docs.add_argument('output', help='Output directory', metavar='PATH', type=Path)
    parser_dl_docs.add_argument(
        '--format',
        help='available variables:\tiso_date, time, title, doc_num, subtitle',
        metavar='FORMAT_STRING',
        default='{iso_date}{time} {title}{doc_num}',
    )
    parser_dl_docs.add_argument(
        '--last_days', help='Number of last days to include (use 0 get all days)', metavar='DAYS', default=0, type=int
    )
    # portfolio
    parser_cmd.add_parser('portfolio', parents=[parser_login_args], help='Show current portfolio')
    parser_details = parser_cmd.add_parser('details', parents=[parser_login_args], help='Get details for an ISIN')
    # details
    parser_details.add_argument('isin', help='ISIN of intrument')
    # get_price_alarms
    parser_get_price_alarms = parser_cmd.add_parser(
        'get_price_alarms',
        parents=[parser_login_args],
        help='Get overview of current price alarms',
    )
    # set_price_alarms
    parser_set_price_alarms = parser_cmd.add_parser(
        'set_price_alarms',
        parents=[parser_login_args],
        help='Set price alarms based on diff from current price',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_set_price_alarms.add_argument(
        '-%', '--percent', help='Percentage +/-', metavar='[-1000 ... 1000]', type=int, default=-10
    )
    # export_transactions
    parser_export_transactions = parser_cmd.add_parser(
        'export_transactions',
        help='Create a CSV with the deposits and removals ready for importing into Portfolio Performance',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_export_transactions.add_argument(
        'input', help='Input path to JSON (use other_events.json from dl_docs)', metavar='INPUT', type=Path
    )
    parser_export_transactions.add_argument('output', help='Output path of CSV file', metavar='OUTPUT', type=Path)
    parser_export_transactions.add_argument(
        '-l', '--lang', help='Two letter language code or "auto" for system language', default='auto'
    )

    return parser


def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in input when CTRL+C is pressed, and our signal handler is not re-entrant
    global original_sigint
    signal.signal(signal.SIGINT, original_sigint)

    try:
        if input('\nReally quit? (y/n)> ').lower().startswith('y'):
            exit(1)

    except KeyboardInterrupt:
        print('Ok ok, quitting')
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

    log = get_logger(__name__, args.verbosity)
    log.setLevel(args.verbosity.upper())
    log.debug('logging is set to debug')
    weblogin = not args.applogin

    if args.command == 'login':
        login(phone_no=args.phone_no, pin=args.pin, web=weblogin)

    elif args.command == 'dl_docs':
        if args.last_days == 0:
            since_timestamp = 0
        else:
            since_timestamp = (time.time() - (24 * 3600 * args.last_days)) * 1000

        dl = DL(
            login(phone_no=args.phone_no, pin=args.pin, web=weblogin),
            args.output,
            args.format,
            since_timestamp=since_timestamp,
        )
        asyncio.get_event_loop().run_until_complete(dl.dl_loop())
    elif args.command == 'set_price_alarms':
        # TODO
        print('Not implemented yet')
    elif args.command == 'get_price_alarms':
        Alarms(login(phone_no=args.phone_no, pin=args.pin, web=weblogin)).get()
    elif args.command == 'details':
        Details(login(phone_no=args.phone_no, pin=args.pin, web=weblogin), args.isin).get()
    elif args.command == 'portfolio':
        Portfolio(login(phone_no=args.phone_no, pin=args.pin, web=weblogin)).get()
    elif args.command == 'export_transactions':
        export_transactions(args.input, args.output, args.lang)
    elif args.version:
        installed_version = version('pytr')
        print(installed_version)
        check_version(installed_version)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
