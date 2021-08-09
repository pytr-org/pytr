#!/usr/bin/env python

import argparse
import asyncio
import signal


import shtab

from pytr.utils import get_logger
from pytr.dl import DL
from pytr.account import login
from pytr.portfolio import Portfolio
from pytr.alarms import Alarms
from pytr.details import Details


# async def my_loop(tr, dl):
#     # await tr.subscribe({'type': 'unsubscribeNews'})
#     # await tr.order_overview()

#     # await tr.timeline_detail('98d13dc6-5bd3-43c8-b74a-dae4e7728f4f')

#     # await tr.ticker('DE0007236101', 'LSX')
#     # await tr.ticker('DE0007100000', 'LSX')

#     while True:
#         _subscription_id, subscription, response = await tr.recv()

#         # Identify response by subscription_id:
#         #   if portfolio_subscription_id == subscription_id:

#         if subscription['type'] == 'orders':
#             print(f'Orders: {response}')

#         # Or identify response by subscription type:
#         elif subscription['type'] == 'ticker':
#             print(f'Current tick for {subscription['id']} is {response}')

#         else:
#             print(f'unmatched subscription of type '{subscription['type']}':\n{preview(response)}')


def get_main_parser():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    shtab.add_argument_to(parser, ['-s', '--print-completion'])  # magic!

    parser.add_argument(
        '-v', '--verbosity', help='Set verbosity level', choices=['warning', 'info', 'debug'], default='info'
    )
    subparsers = parser.add_subparsers(help='Desired action to perform', dest='command')

    # help
    subparsers.add_parser('help', help='Print this help message')

    # Create parent subparser for {dl_docs, check}-parsers with common arguments
    parent_parser = argparse.ArgumentParser(add_help=False, formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # Subparsers based on parent

    parser_login = subparsers.add_parser(
        'login',
        parents=[parent_parser],
        help='Check if credentials file exists. If not create it and ask for input.'
        + ' Try to login. Ask for device reset if needed',
    )
    parser_login.add_argument('-n', '--phone_no', help='TradeRepbulic phone number (international format)')
    parser_login.add_argument('-p', '--pin', help='TradeRepbulic pin')

    subparsers.add_parser('portfolio', parents=[parent_parser], help='Show current portfolio')

    parser_dl_docs = subparsers.add_parser(
        'dl_docs',
        parents=[parent_parser],
        help='Download all pdf documents from the timeline and sort them into folders',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_dl_docs.add_argument('output', help='Output directory', metavar='PATH')
    parser_dl_docs.add_argument(
        '--format',
        help='available variables:\tiso_date, time, title, doc_num, subtitle',
        metavar='FORMAT_STRING',
        default='{iso_date}{time} {title}{doc_num}',
    )

    parser_get_price_alarms = subparsers.add_parser(
        'get_price_alarms', parents=[parent_parser], help='Get overview of current price alarms'
    )
    parser_details = subparsers.add_parser('details', parents=[parent_parser], help='Get details for an ISIN')
    parser_details.add_argument('isin', help='ISIN of intrument')
    parser_set_price_alarms = subparsers.add_parser(
        'set_price_alarms', parents=[parent_parser], help='Set price alarms based on diff from current price'
    )
    parser_set_price_alarms.add_argument(
        '-p',
        '--percent',
        help='Percentage +/-',
        # choices=range(-1000, 1001),
        metavar='[-1000 ... 1000]',
        type=int,
        default=-10,
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

    if args.command == 'login':
        login(phone_no=args.phone_no, pin=args.pin)

    elif args.command == 'dl_docs':
        dl = DL(login(), args.output, args.format)
        asyncio.get_event_loop().run_until_complete(dl.dl_loop())
    elif args.command == 'set_price_alarms':
        # TODO
        print('Not implemented yet')
    elif args.command == 'get_price_alarms':
        Alarms(login()).get()
    elif args.command == 'details':
        Details(login(), args.isin).get()
    elif args.command == 'portfolio':
        Portfolio(login()).get()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
