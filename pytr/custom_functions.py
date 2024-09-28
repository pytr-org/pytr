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

            # inflows
            if event["eventType"] in ["PAYMENT_INBOUND","INCOMING_TRANSFER"]:
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
            #Saveback
            elif event["eventType"] in ["SAVINGS_PLAN_EXECUTED","SAVINGS_PLAN_INVOICE_CREATED","benefits_saveback_execution"]:
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
            else:
                print("error"+str(event["eventType"]))

    log.info('transaction creation finished!')

def clean_strings(text: str):
    return text.replace("\n", "")