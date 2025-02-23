import json
from locale import getdefaultlocale
from babel.numbers import format_decimal
import json

from .event import Event
from .event_formatter import EventCsvFormatter
from .utils import get_logger


def export_transactions(input_path, output_path, lang="auto", sort=False, date_isoformat: bool = False):
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

    # Read relevant deposit timeline entries
    with open(input_path, encoding="utf-8") as f:
        timeline = json.load(f)

    log.info("Write deposit entries")

    formatter = EventCsvFormatter(lang=lang)
    if date_isoformat:
        formatter.date_fmt = "ISO8601"

    events: Iterable[Event] = map(lambda x: Event.from_dict(x), timeline)
    if sort:
        events = sorted(events, key=lambda x: x.date)
    lines: Iterable[str] = map(lambda x: formatter.format(x), events)
    lines = formatter.format_header() + "".join(lines)

    # Write transactions into csv file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(lines)

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
            elif event["eventType"] in ["card_refund","TRADE_INVOICE","ORDER_EXECUTED","card_successful_atm_withdrawal","INTEREST_PAYOUT_CREATED","TAX_REFUND","INTEREST_PAYOUT","TRADE_CORRECTED","ssp_tax_correction_invoice"]:
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
            elif event["eventType"] in ["ssp_corporate_action_invoice_cash","CREDIT",]:
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
                                        "DOCUMENTS_CHANGED","MATURITY","YEAR_END_TAX_REPORT","STOCK_PERK_REFUNDED","ORDER_CANCELED","ORDER_EXPIRED","DOCUMENTS_CREATED","CUSTOMER_CREATED","card_failed_verification",
                                        ]:
                pass
            else:
                print("ERROR: "+"Type: "+event["eventType"]+"  Title: "+event["title"])

    log.info('transaction creation finished!')

def clean_strings(text: str):
    return text.replace("\n", "")