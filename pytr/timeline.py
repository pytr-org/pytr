import json
from datetime import datetime

from pytr.event import Event

from .transactions import TransactionExporter
from .utils import get_logger

MAX_EVENT_REQUEST_BATCH = 1000

event_subfolder_mapping = {
    "OUTGOING_TRANSFER_DELEGATION": "Auszahlungen",
    "OUTGOING_TRANSFER": "Auszahlungen",
    "CREDIT": "Dividende",
    "ssp_corporate_action_invoice_cash": "Dividende",
    "ACCOUNT_TRANSFER_INCOMING": "Einzahlungen",
    "INCOMING_TRANSFER_DELEGATION": "Einzahlungen",
    "INCOMING_TRANSFER": "Einzahlungen",
    "PAYMENT_INBOUND_GOOGLE_PAY": "Einzahlungen",
    "PAYMENT_INBOUND_SEPA_DIRECT_DEBIT": "Einzahlungen",
    "CREDIT_CANCELED": "Misc",
    "CRYPTO_ANNUAL_STATEMENT": "Misc",
    "CUSTOMER_CREATED": "Misc",
    "DOCUMENTS_ACCEPTED": "Misc",
    "DOCUMENTS_CHANGED": "Misc",
    "DOCUMENTS_CREATED": "Misc",
    "EX_POST_COST_REPORT": "Misc",
    "EX_POST_COST_REPORT_CREATED": "Misc",
    "GENERAL_MEETING": "Misc",
    "GESH_CORPORATE_ACTION": "Misc",
    "INPAYMENTS_SEPA_MANDATE_CREATED": "Misc",
    "INSTRUCTION_CORPORATE_ACTION": "Misc",
    "JUNIOR_ONBOARDING_GUARDIAN_B_CONSENT": "Misc",
    "PRE_DETERMINED_TAX_BASE_EARNING": "Misc",
    "QUARTERLY_REPORT": "Misc",
    "SHAREBOOKING": "Misc",
    "SHAREBOOKING_TRANSACTIONAL": "Misc",
    "STOCK_PERK_REFUNDED": "Misc",
    "TAX_YEAR_END_REPORT": "Misc",
    "YEAR_END_TAX_REPORT": "Misc",
    "crypto_annual_statement": "Misc",
    "private_markets_suitability_quiz_completed": "Misc",
    "ssp_capital_increase_customer_instruction": "Misc",
    "ssp_corporate_action_informative_notification": "Misc",
    "ssp_corporate_action_invoice_shares": "Misc",
    "ssp_dividend_option_customer_instruction": "Misc",
    "ssp_general_meeting_customer_instruction": "Misc",
    "ssp_tender_offer_customer_instruction": "Misc",
    "benefits_spare_change_execution": "RoundUp",
    "benefits_saveback_execution": "Saveback",
    "SAVINGS_PLAN_EXECUTED": "Sparplan",
    "SAVINGS_PLAN_INVOICE_CREATED": "Sparplan",
    "trading_savingsplan_executed": "Sparplan",
    "trading_savingsplan_execution_failed": "Sparplan",
    "TAX_CORRECTION": "Steuerkorrekturen",
    "TAX_REFUND": "Steuerkorrekturen",
    "ssp_tax_correction_invoice": "Steuerkorrekturen",
    "ORDER_CANCELED": "Trades",
    "ORDER_EXECUTED": "Trades",
    "ORDER_EXPIRED": "Trades",
    "ORDER_REJECTED": "Trades",
    "TRADE_CORRECTED": "Trades",
    "TRADE_INVOICE": "Trades",
    "private_markets_order_created": "Trades",
    "trading_order_cancelled": "Trades",
    "trading_order_created": "Trades",
    "trading_order_rejected": "Trades",
    "trading_trade_executed": "Trades",
    "trading_order_expired": "Trades",
    "ACQUISITION_TRADE_PERK": "Vorteil",
    "INTEREST_PAYOUT": "Zinsen",
    "INTEREST_PAYOUT_CREATED": "Zinsen",
}


class Timeline:
    def __init__(self, tr, max_age_timestamp):
        self.tr = tr
        self.log = get_logger(__name__)
        self.all_detail = 0
        self.requested_detail = 0
        self.received_detail = 0
        self.skipped_detail = 0
        self.detail_digits = 0
        self.events_without_docs = []
        self.events_with_docs = []
        self.num_timelines = 0
        self.timeline_events = {}
        self.max_age_timestamp = max_age_timestamp

    async def get_next_timeline_transactions(self, response, dl):
        """
        Get timelines transactions and save time in list timelines.
        Extract timeline transactions events and save them in list timeline_events

        """
        if response is None:
            # empty response / first timeline
            self.log.info("Timeline transactions: Subscribing to #1...")
            self.num_timelines = 0
            await self.tr.timeline_transactions()
        else:
            self.num_timelines += 1
            added_last_event = False
            for event in response["items"]:
                event_timestamp = datetime.fromisoformat(event["timestamp"][:19]).timestamp()
                if self.max_age_timestamp == 0 or event_timestamp >= self.max_age_timestamp:
                    event["source"] = "timelineTransaction"
                    self.timeline_events[event["id"]] = event
                    added_last_event = True
                else:
                    break

            after = response["cursors"].get("after")
            if (after is not None) and added_last_event:
                self.log.info(
                    f"Timeline transactions: Received #{self.num_timelines}, subscribing to #{self.num_timelines + 1}..."
                )
                await self.tr.timeline_transactions(after)
            else:
                # last timeline is reached
                self.log.info(f"Timeline transactions: Received #{self.num_timelines} (last relevant).")
                await self.get_next_timeline_activity_log(None, dl)

    async def get_next_timeline_activity_log(self, response, dl):
        """
        Get timelines acvtivity log and save time in list timelines.
        Extract timeline acvtivity log events and save them in list timeline_events

        """
        if response is None:
            # empty response / first timeline
            self.log.info("Timeline activity log: Subscribing to #1...")
            self.num_timelines = 0
            await self.tr.timeline_activity_log()
        else:
            self.num_timelines += 1
            added_last_event = False
            for event in response["items"]:
                event_timestamp = datetime.fromisoformat(event["timestamp"][:19]).timestamp()
                if self.max_age_timestamp == 0 or event_timestamp >= self.max_age_timestamp:
                    if event["id"] in self.timeline_events:
                        self.log.warning(f"Received duplicate event {event['id']}")
                    event["source"] = "timelineActivity"
                    self.timeline_events[event["id"]] = event
                    added_last_event = True
                else:
                    break

            after = response["cursors"].get("after")
            if (after is not None) and added_last_event:
                self.log.info(
                    f"Timeline activity log: Received #{self.num_timelines}, subscribing to #{self.num_timelines + 1}..."
                )
                await self.tr.timeline_activity_log(after)
            else:
                self.log.info(f"Timeline activity log: Received #{self.num_timelines} (last relevant).")
                self.request_timeline_details_generator = self._request_timeline_details(dl)
                try:
                    await self.request_timeline_details_generator.__anext__()
                except StopAsyncIteration:
                    pass

    async def _request_timeline_details(self, dl):
        """
        request timeline details
        """
        self.all_detail = len(self.timeline_events.values())
        self.detail_digits = len(str(self.all_detail))

        for event in self.timeline_events.values():
            action = event.get("action")
            msg = None
            if action is None:
                if event.get("actionLabel") is None:
                    msg = "Skip timeline detail: no action"
            elif action.get("type") != "timelineDetail":
                msg = f"Skip timeline detail: unmatched action type ({action['type']})"
            elif action.get("payload") != event["id"]:
                msg = f"Skip timeline detail: unmatched action payload ({action['payload']})"

            self.requested_detail += 1
            if msg is None:
                await self.tr.timeline_detail_v2(event["id"])
            else:
                self.received_detail += 1
                self.events_without_docs.append(event)
                self.log.info(
                    f"{self.received_detail + self.skipped_detail:>{self.detail_digits}}/{self.all_detail}: "
                    + f"{event['title']} -- {event['subtitle']} - {event['timestamp'][:19]}"
                )
                self.log.debug("%s: %s", msg, json.dumps(event, indent=4))

            if self.requested_detail % MAX_EVENT_REQUEST_BATCH == 0 and (
                (self.received_detail + self.skipped_detail) < self.requested_detail
            ):
                self.log.info(f"Requested {self.requested_detail}/{self.all_detail} timeline details.")
                yield

        self.log.info(f"Requested all timeline details ({self.requested_detail}/{self.all_detail}).")
        self.finish_if_done(dl)

    async def process_timelineDetail(self, response, dl):
        """
        process timeline details response
        download any associated docs
        create other_events.json, events_with_documents.json and account_transactions.csv
        """

        event = self.timeline_events.get(response["id"], None)
        if event is None:
            self.log.warning(f"Ignoring unrequested event response {json.dumps(response, indent=4)}")
            self.skipped_detail += 1
            self.finish_if_done(dl)
            return

        self.received_detail += 1
        event["details"] = response

        self.log.info(
            f"{self.received_detail + self.skipped_detail:>{self.detail_digits}}/{self.all_detail}: "
            + f"{event['title']} -- {event['subtitle']} - {event['timestamp'][:19]}"
        )

        event["has_docs"] = False
        for section in response["sections"]:
            if section["type"] != "documents":
                continue

            event["has_docs"] = True
            subfolder = None

            # Get eventType safely - it may not exist in newer API responses
            event_type = event.get("eventType")
            
            if event_type == "timeline_legacy_migrated_events" or event_type is None:
                # For legacy events or when eventType is missing, use heuristic based on title/subtitle
                subtitle = event.get("subtitle", "")
                title = event.get("title", "")
                
                if title == "Zinsen":
                    subfolder = "Zinsen"
                elif subtitle in [
                    "Kauforder",
                    "Limit-Buy-Order",
                    "Limit-Sell-Order",
                    "Limit Verkauf-Order neu abgerechnet",
                    "Sparplan ausgeführt",
                    "Stop-Sell-Order",
                    "Verkaufsorder",
                ]:
                    subfolder = "Trades"
                elif subtitle in ["Bardividende", "Dividende"]:
                    subfolder = "Dividende"
                elif subtitle in ["Einzahlung", "Geändert"] or "Einzahlung" in title:
                    subfolder = "Einzahlungen"
                elif subtitle in ["Auszahlung", "Gesendet"] or "Auszahlung" in title:
                    subfolder = "Auszahlungen"
                elif subtitle in ["Saveback"]:
                    subfolder = "Saveback"
                elif subtitle in ["Round Up", "Round up"]:
                    subfolder = "RoundUp"
                elif subtitle in ["2 % p.a.", "Zinsen"]:
                    subfolder = "Zinsen"
                else:
                    # Try to infer from title if no subtitle match
                    if "Dividende" in title or "Dividend" in title:
                        subfolder = "Dividende"
                    elif event_type is None and subtitle not in [None, "", "None", "Abgebrochen", "Kartenprüfung", "Bestätigt", "Eröffnet", "Erhalten", "Geändert", "Kommt in 2 Tagen"]:
                        # No eventType and couldn't infer from title/subtitle
                        # Only warn if it's not a known non-document event
                        self.log.warning(
                            f"no eventType and no mapping match: title={title} subtitle={subtitle}"
                        )
                        subfolder = "Misc"
                    elif event_type is None:
                        # Known non-document event types, don't create subfolder
                        subfolder = None
                    else:
                        self.log.warning(
                            f"no mapping for timeline_legacy_migrated_events: title={title} subtitle={subtitle}"
                        )
            else:
                subfolder = event_subfolder_mapping.get(event_type)

            if subfolder is None and event_type is not None:
                self.log.warning(f"no mapping for {event_type}")

            for doc in section["data"]:
                timestamp_str = event["timestamp"]
                if timestamp_str[-3] != ":":
                    timestamp_str = timestamp_str[:-2] + ":" + timestamp_str[-2:]
                try:
                    docdate = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    self.log.warning(f"no timestamp parseable from {timestamp_str}")
                    docdate = datetime.now()

                if self.max_age_timestamp == 0 or self.max_age_timestamp < docdate.timestamp():
                    title = f"{doc['title']} - {event['title']} - {event['subtitle']}"
                    dl.dl_doc(doc, title, subfolder, docdate)

        if event["has_docs"]:
            self.events_with_docs.append(event)
        else:
            self.events_without_docs.append(event)

        await self.request_more_timeline_details()
        self.finish_if_done(dl)

    async def request_more_timeline_details(self):
        if self.requested_detail == self.all_detail:
            return
        if (self.received_detail + self.skipped_detail) == self.requested_detail:
            try:
                await self.request_timeline_details_generator.__anext__()
            except StopAsyncIteration:
                pass

    def finish_if_done(self, dl):
        if self.requested_detail != self.all_detail:
            return
        if (self.received_detail + self.skipped_detail) == self.requested_detail:
            self.finish_timeline_details(dl)

    def finish_timeline_details(self, dl):
        self.log.info("Received all details")
        if self.skipped_detail > 0:
            self.log.warning(f"Skipped {self.skipped_detail} unsupported events")

        dl.output_path.mkdir(parents=True, exist_ok=True)
        with open(dl.output_path / "other_events.json", "w", encoding="utf-8") as f:
            json.dump(self.events_without_docs, f, ensure_ascii=False, indent=2)

        with open(dl.output_path / "events_with_documents.json", "w", encoding="utf-8") as f:
            json.dump(self.events_with_docs, f, ensure_ascii=False, indent=2)

        with open(dl.output_path / "all_events.json", "w", encoding="utf-8") as f:
            json.dump(
                self.events_without_docs + self.events_with_docs,
                f,
                ensure_ascii=False,
                indent=2,
            )

        with (dl.output_path / "account_transactions.csv").open("w", encoding="utf-8") as f:
            TransactionExporter(
                lang=dl.lang,
                date_with_time=dl.date_with_time,
                decimal_localization=dl.decimal_localization,
            ).export(
                f,
                [Event.from_dict(ev) for ev in self.events_without_docs + self.events_with_docs],
                sort=dl.sort_export,
                format=dl.format_export,
            )

        dl.work_responses()
