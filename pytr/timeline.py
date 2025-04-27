import json
from datetime import datetime

from pytr.event import Event

from .transactions import TransactionExporter
from .utils import get_logger


class UnsupportedEventError(Exception):
    pass


class Timeline:
    def __init__(self, tr, max_age_timestamp):
        self.tr = tr
        self.log = get_logger(__name__)
        self.received_detail = 0
        self.requested_detail = 0
        self.skipped_detail = 0
        self.events_without_docs = []
        self.events_with_docs = []
        self.num_timelines = 0
        self.timeline_events = {}
        self.max_age_timestamp = max_age_timestamp

    async def get_next_timeline_transactions(self, response=None):
        """
        Get timelines transactions and save time in list timelines.
        Extract timeline transactions events and save them in list timeline_events

        """
        if response is None:
            # empty response / first timeline
            self.log.info("Subscribing to #1 timeline transactions")
            self.num_timelines = 0
            await self.tr.timeline_transactions()
        else:
            self.num_timelines += 1
            added_last_event = True
            for event in response["items"]:
                if (
                    self.max_age_timestamp == 0
                    or datetime.fromisoformat(event["timestamp"][:19]).timestamp() >= self.max_age_timestamp
                ):
                    event["source"] = "timelineTransaction"
                    self.timeline_events[event["id"]] = event
                else:
                    added_last_event = False
                    break

            self.log.info(f"Received #{self.num_timelines:<2} timeline transactions")
            after = response["cursors"].get("after")
            if (after is not None) and added_last_event:
                self.log.info(f"Subscribing #{self.num_timelines + 1:<2} timeline transactions")
                await self.tr.timeline_transactions(after)
            else:
                # last timeline is reached
                self.log.info("Received last relevant timeline transaction")
                await self.get_next_timeline_activity_log()

    async def get_next_timeline_activity_log(self, response=None):
        """
        Get timelines acvtivity log and save time in list timelines.
        Extract timeline acvtivity log events and save them in list timeline_events

        """
        if response is None:
            # empty response / first timeline
            self.log.info("Awaiting #1  timeline activity log")
            self.num_timelines = 0
            await self.tr.timeline_activity_log()
        else:
            self.num_timelines += 1
            added_last_event = False
            for event in response["items"]:
                if (
                    self.max_age_timestamp == 0
                    or datetime.fromisoformat(event["timestamp"][:19]).timestamp() >= self.max_age_timestamp
                ):
                    if event["id"] in self.timeline_events:
                        self.log.warning(f"Received duplicate event {event['id']}")
                    else:
                        added_last_event = True
                    event["source"] = "timelineActivity"
                    self.timeline_events[event["id"]] = event
                else:
                    break

            self.log.info(f"Received #{self.num_timelines:<2} timeline activity log")
            after = response["cursors"].get("after")
            if (after is not None) and added_last_event:
                self.log.info(f"Subscribing #{self.num_timelines + 1:<2} timeline activity log")
                await self.tr.timeline_activity_log(after)
            else:
                self.log.info("Received last relevant timeline activity log")
                await self._get_timeline_details()

    async def _get_timeline_details(self):
        """
        request timeline details
        """
        for event in self.timeline_events.values():
            action = event.get("action")
            msg = ""
            if action is None:
                if event.get("actionLabel") is None:
                    msg += "Skip: no action"
            elif action.get("type") != "timelineDetail":
                msg += f"Skip: action type unmatched ({action['type']})"
            elif action.get("payload") != event["id"]:
                msg += f"Skip: payload unmatched ({action['payload']})"

            if msg != "":
                self.events_without_docs.append(event)
                self.log.debug(f"{msg} {event['title']}: {event.get('body')} ")
            else:
                self.requested_detail += 1
                await self.tr.timeline_detail_v2(event["id"])
        self.log.info("All timeline details requested")
        return False

    def process_timelineDetail(self, response, dl):
        """
        process timeline details response
        download any associated docs
        create other_events.json, events_with_documents.json and account_transactions.csv
        """

        event = self.timeline_events.get(response["id"], None)
        if event is None:
            raise UnsupportedEventError(response["id"])

        self.received_detail += 1
        event["details"] = response

        max_details_digits = len(str(self.requested_detail))
        self.log.info(
            f"{self.received_detail:>{max_details_digits}}/{self.requested_detail}: "
            + f"{event['title']} -- {event['subtitle']} - {event['timestamp'][:19]}"
        )

        event["has_docs"] = False
        for section in response["sections"]:
            if section["type"] != "documents":
                continue

            event["has_docs"] = True
            subfolder = {
                "OUTGOING_TRANSFER_DELEGATION": "Auszahlungen",
                "OUTGOING_TRANSFER": "Auszahlungen",
                "CREDIT": "Dividende",
                "ssp_corporate_action_invoice_cash": "Dividende",
                "INCOMING_TRANSFER_DELEGATION": "Einzahlungen",
                "INCOMING_TRANSFER": "Einzahlungen",
                "CUSTOMER_CREATED": "Misc",
                "DOCUMENTS_ACCEPTED": "Misc",
                "DOCUMENTS_CREATED": "Misc",
                "TAX_YEAR_END_REPORT": "Misc",
                "crypto_annual_statement": "Misc",
                "ssp_corporate_action_informative_notification": "Misc",
                "ssp_corporate_action_invoice_shares": "Misc",
                "ssp_dividend_option_customer_instruction": "Misc",
                "benefits_spare_change_execution": "RoundUp",
                "benefits_saveback_execution": "Saveback",
                "SAVINGS_PLAN_EXECUTED": "Sparplan",
                "SAVINGS_PLAN_INVOICE_CREATED": "Sparplan",
                "trading_savingsplan_executed": "Sparplan",
                "trading_savingsplan_execution_failed": "Sparplan",
                "ssp_tax_correction_invoice": "Steuerkorrekturen",
                "ORDER_CANCELED": "Trades",
                "ORDER_EXECUTED": "Trades",
                "ORDER_EXPIRED": "Trades",
                "ORDER_REJECTED": "Trades",
                "TRADE_CORRECTED": "Trades",
                "TRADE_INVOICE": "Trades",
                "trading_order_cancelled": "Trades",
                "trading_order_created": "Trades",
                "trading_order_rejected": "Trades",
                "trading_trade_executed": "Trades",
                "INTEREST_PAYOUT": "Zinsen",
                "INTEREST_PAYOUT_CREATED": "Zinsen",
            }.get(event["eventType"])
            if subfolder is None:
                print(f"no mapping for {event['eventType']}")

            for doc in section["data"]:
                timestamp_str = event["timestamp"]
                if timestamp_str[-3] != ":":
                    timestamp_str = timestamp_str[:-2] + ":" + timestamp_str[-2:]
                try:
                    docdate = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    print(f"no timestamp parseable from {timestamp_str}")
                    docdate = datetime.now()

                if self.max_age_timestamp == 0 or self.max_age_timestamp < docdate.timestamp():
                    title = f"{doc['title']} - {event['title']} - {event['subtitle']}"
                    dl.dl_doc(doc, title, subfolder, docdate)

        if event["has_docs"]:
            self.events_with_docs.append(event)
        else:
            self.events_without_docs.append(event)

        self.check_if_done(dl)

    def check_if_done(self, dl):
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
