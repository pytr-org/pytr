from locale import getdefaultlocale
from babel.numbers import format_decimal
import json
import os
from datetime import datetime

from .event import Event
from .utils import get_logger
from .translation import setup_translation
# from event import Event
# from utils import get_logger
# from translation import setup_translation


def export_transactions(input_path, output_path, lang="auto"):
    """
    Create a CSV with the deposits and removals ready for importing into Portfolio Performance
    The CSV headers for PP are language dependend
    """
    log = get_logger(__name__)
    if lang == "auto":
        locale = getdefaultlocale()[0]
        if locale is None:
            lang = "en"
        else:
            lang = locale.split("_")[0]

    if lang not in [
        "cs",
        "da",
        "de",
        "en",
        "es",
        "fr",
        "it",
        "nl",
        "pl",
        "pt",
        "ru",
        "zh",
    ]:
        log.info(f"Language not yet supported {lang}")
        lang = "en"
    _ = setup_translation(language=lang)

    # Read relevant deposit timeline entries
    with open(input_path, encoding="utf-8") as f:
        timeline = json.load(f)

    log.info("Write deposit entries")
    with open(output_path, "w", encoding="utf-8") as f:
        csv_fmt = "{date};{type};{value};{note};{isin};{shares}\n"
        header = csv_fmt.format(
            date=_("CSVColumn_Date"),
            type=_("CSVColumn_Type"),
            value=_("CSVColumn_Value"),
            note=_("CSVColumn_Note"),
            isin=_("CSVColumn_ISIN"),
            shares=_("CSVColumn_Shares"),
        )
        f.write(header)

        for event_json in timeline:
            event = Event(event_json)
            if not event.is_pp_relevant:
                continue

            amount = format_decimal(event.amount, locale=lang, decimal_quantization=False) if event.amount else ""
            note = (_(event.note) + " - " + event.title) if event.note else event.title
            shares = format_decimal(event.shares, locale=lang, decimal_quantization=False) if event.shares else ""

            f.write(
                csv_fmt.format(
                    date=event.date,
                    type=_(event.pp_type),
                    value=amount,
                    note=note,
                    isin=event.isin,
                    shares=shares,
                )
            )

    log.info("Deposit creation finished!")

def export_banking4(input_path, output_path, lang='auto'):
    '''
    Create a CSV with most of transactions available for import in banking4
    '''
    log = get_logger(__name__)
    if lang == 'auto':
        locale = getdefaultlocale()[0]
        if locale is None:
            lang = 'en'
        else:
            lang = locale.split('_')[0]
    #Build Strings
    timeline1_loc = os.path.join(input_path,"other_events.json")
    timeline2_loc = os.path.join(input_path,"events_with_documents.json")

    # Read relevant deposit timeline entries
    with open(timeline1_loc, encoding='utf-8') as f:
        timeline1 = json.load(f)
    with open(timeline2_loc, encoding='utf-8') as f:
        timeline2 = json.load(f)    

    # Write deposit_transactions.csv file
    # date, transaction, shares, amount, total, fee, isin, name
    log.info('Write transaction entries')
    with open(output_path, 'w', encoding='utf-8') as f:
        # f.write('Datum;Typ;Stück;amount;Wert;Gebühren;ISIN;name\n')
        csv_fmt = '{date};{type};{value}\n'
        header = csv_fmt.format(date='date', type='type', value='value')
        f.write(header)

        for event in timeline1+timeline2:
            dateTime = datetime.fromisoformat(event['timestamp'][:19])
            date = dateTime.strftime('%Y-%m-%d')

            try:
                body = event['body']
            except KeyError:
                body = ''

            if 'storniert' in body:
                continue

            # SEPA inflows and outflows 
            if event["eventType"] in ["PAYMENT_INBOUND","INCOMING_TRANSFER","OUTGOING_TRANSFER","OUTGOING_TRANSFER_DELEGATION"]:
                 f.write(csv_fmt.format(date=date, type=clean_strings(event['eventType']), value=event['amount']["value"]))
            # Card refund, Buys, atm withdrawal, iterest payouts
            elif event["eventType"] in ["card_refund","TRADE_INVOICE","ORDER_EXECUTED","card_successful_atm_withdrawal","INTEREST_PAYOUT_CREATED","TAX_REFUND","INTEREST_PAYOUT","TRADE_CORRECTED"]:
                title = event['title']
                subtitle = event["subtitle"]
                if title is None:
                    title = 'no title'
                if subtitle is None:
                    subtitle = "no subtitle"
                f.write(csv_fmt.format(date=date, type=clean_strings(title+": "+subtitle), value=event['amount']["value"]))
            #Debit payments    
            elif event["eventType"] in ["card_successful_transaction"]:
                f.write(csv_fmt.format(date=date, type=clean_strings(event["eventType"]+": "+event['title'] ), value=event['amount']["value"]))
            #dividends
            elif event["eventType"] in ["ssp_corporate_action_invoice_cash","CREDIT"]:
                f.write(csv_fmt.format(date=date, type=clean_strings(event["subtitle"]+": "+event["title"]), value=event['amount']["value"]))
            #Saveback (creates a zero entry just for informational purposes)
            elif event["eventType"] in ["benefits_saveback_execution"]:
                f.write(csv_fmt.format(date=date, type=clean_strings(event["subtitle"]+": "+event["title"]+": "+str(-1*event["amount"]["value"])), value="0.00"))
            # Savingsplan
            elif event["eventType"] in ["SAVINGS_PLAN_EXECUTED","SAVINGS_PLAN_INVOICE_CREATED"]:
                f.write(csv_fmt.format(date=date, type=clean_strings(event["subtitle"]+": "+event["title"]), value=event['amount']["value"]))
            #Tax payments
            elif event["eventType"] in ["PRE_DETERMINED_TAX_BASE"]:
                f.write(csv_fmt.format(date=date, type=clean_strings(event["subtitle"]+": "+event["title"]), value=event['amount']["value"]))
            #Card order
            elif event["eventType"] in ["card_order_billed"]:
                f.write(csv_fmt.format(date=date, type=clean_strings(event["title"]), value=event['amount']["value"]))
            #Referral
            elif event["eventType"] in ["REFERRAL_FIRST_TRADE_EXECUTED_INVITER"]:
                f.write(csv_fmt.format(date=date, type=clean_strings(event["title"]+": "+event["subtitle"]),value=event['amount']["value"]))
            #Capital events (e.g. return of capital)
            elif event["eventType"] in ["SHAREBOOKING_TRANSACTIONAL"]:
                if (event["subtitle"]=="Reinvestierung"):
                    pass
                else:
                    f.write(csv_fmt.format(date=date, type=clean_strings(event["title"]+": "+event["subtitle"]),value=event['amount']["value"]))
            # Events that are not transactions tracked by this function
            elif event["eventType"] in ["EXEMPTION_ORDER_CHANGED","EXEMPTION_ORDER_CHANGE_REQUESTED","AML_SOURCE_OF_WEALTH_RESPONSE_EXECUTED","DEVICE_RESET",
                                        "REFERENCE_ACCOUNT_CHANGED","EXEMPTION_ORDER_CHANGE_REQUESTED_AUTOMATICALLY","CASH_ACCOUNT_CHANGED","ACCOUNT_TRANSFER_INCOMING",
                                        "card_failed_transaction","EMAIL_VALIDATED","PUK_CREATED","SECURITIES_ACCOUNT_CREATED","card_successful_verification",
                                        "ssp_dividend_option_customer_instruction","new_tr_iban","DOCUMENTS_ACCEPTED","EX_POST_COST_REPORT","INSTRUCTION_CORPORATE_ACTION",
                                        "SHAREBOOKING","GESH_CORPORATE_ACTION","GENERAL_MEETING","QUARTERLY_REPORT","DOCUMENTS_ACCEPTED","GENERAL_MEETING","INSTRUCTION_CORPORATE_ACTION",
                                        "DOCUMENTS_CHANGED","MATURITY","YEAR_END_TAX_REPORT","STOCK_PERK_REFUNDED","ORDER_CANCELED","ORDER_EXPIRED","DOCUMENTS_CREATED","CUSTOMER_CREATED",
                                        ]:
                pass
            else:
                print("ERROR: "+"Type: "+event["eventType"]+"  Title: "+event["title"])

    log.info('transaction creation finished!')

def clean_strings(text: str):
    return text.replace("\n", "")