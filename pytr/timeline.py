import json
from datetime import datetime

from .api import TradeRepublicError
from .utils import get_logger, preview

MAX_EVENT_REQUEST_BATCH = 1000


def is_likely_same_but_newer(event, old_event):
    if event["title"] != old_event["title"]:
        return False

    if (
        event["subtitle"] != "Limit-Sell-Order"
        and event["subtitle"] != "Limit-Buy-Order"
        and event["subtitle"] != "Sparplan ausgeführt"
    ):
        return False

    if event["subtitle"] != old_event["subtitle"]:
        return False

    # Check timestamps
    fmt = "%Y-%m-%dT%H:%M:%S.%f%z"
    date_new = datetime.strptime(event["timestamp"], fmt)
    date_old = datetime.strptime(old_event["timestamp"], fmt)

    if date_new < date_old:
        return False

    return abs((date_new - date_old).total_seconds() * 1000) <= 500


class Timeline:
    def __init__(
        self,
        tr,
        output_path,
        not_before=float(0),
        not_after=float(0),
        store_event_database=True,
        dump_raw_data=False,
        event_callback=lambda *a, **kw: None,
    ):
        self.tr = tr
        self.output_path = output_path
        self.not_before = not_before
        self.not_after = not_after
        self.store_event_database = store_event_database
        self.dump_raw_data = dump_raw_data
        self.event_callback = event_callback
        self.log = get_logger(__name__)
        self.dl_done = False
        self.error_counts = {}
        self.num_timelines = 0
        self.all_detail = 0
        self.requested_detail = 0
        self.received_detail = 0
        self.skipped_detail = 0
        self.detail_digits = 0
        self.timeline_transactions = {}
        self.timeline_activities = {}
        self.timeline_details = {}
        self.events = []

        output_path.mkdir(parents=True, exist_ok=True)

    async def tl_loop(self):
        await self.get_next_timeline_transactions(None)

        while not self.dl_done:
            try:
                _, subscription, response = await self.tr.recv()
            except TradeRepublicError as e:
                self.log.error(f'Error response for subscription "{e.subscription}".')
                subscriptionid = e.subscription["id"]
                curct = self.error_counts.get(subscriptionid, 0)
                self.log.error(f'Errorcount for subscription {subscriptionid} is {curct}".')
                if curct < 3:
                    self.log.error(f'Error count for subscription {subscriptionid} is {curct}". Re-subscribing...')
                    self.error_counts[subscriptionid] = curct + 1
                    await self.tr.subscribe(e.subscription)
                    continue
                else:
                    self.log.error(
                        f'Error count for subscription {subscriptionid} is {curct}". Continuing with failure...'
                    )
                    subscription = e.subscription
                    response = {}

            if subscription.get("type", "") == "timelineTransactions":
                await self.get_next_timeline_transactions(response)
            elif subscription.get("type", "") == "timelineActivityLog":
                await self.get_next_timeline_activity_log(response)
            elif subscription.get("type", "") == "timelineDetailV2":
                await self.process_timelineDetail(response)
            else:
                self.log.warning(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

    async def get_next_timeline_transactions(self, response):
        """
        Get timeline transactions and store them in list timeline_transactions
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
                if self.not_before == 0 or event_timestamp >= self.not_before:
                    if self.not_after == 0 or event_timestamp <= self.not_after:
                        event["source"] = "timelineTransaction"
                        self.timeline_transactions[event["id"]] = event
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
                if self.dump_raw_data:
                    with (self.output_path / "timeline_transactions.json").open("w") as f:
                        json.dump(self.timeline_transactions, f, indent=4)
                await self.get_next_timeline_activity_log(None)

    async def get_next_timeline_activity_log(self, response):
        """
        Get timeline acvtivity log events and store them in list timeline_activities
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
                if self.not_before == 0 or event_timestamp >= self.not_before:
                    if self.not_after == 0 or event_timestamp <= self.not_after:
                        event["source"] = "timelineActivity"
                        self.timeline_activities[event["id"]] = event
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
                if self.dump_raw_data:
                    with (self.output_path / "timeline_activities.json").open("w") as f:
                        json.dump(self.timeline_activities, f, indent=4)

                duplicates = set(self.timeline_transactions) & set(self.timeline_activities)
                if duplicates:
                    self.log.warning(f"Received duplicate events: {', '.join(duplicates)}")

                self.timeline_details = {**self.timeline_transactions, **self.timeline_activities}

                self.request_timeline_details_generator = self._request_timeline_details()
                try:
                    await self.request_timeline_details_generator.__anext__()
                except StopAsyncIteration:
                    pass

    async def _request_timeline_details(self):
        """
        request timeline details
        """
        self.all_detail = len(self.timeline_details.values())
        self.detail_digits = len(str(self.all_detail))

        for event in self.timeline_details.values():
            msg = None
            action = event.get("action")
            if action is None:
                if event.get("actionLabel") is None:
                    msg = "Skip timeline detail: No action/actionLabel section"
            elif action.get("type") != "timelineDetail":
                msg = f"Skip timeline detail: Action type {action['type']} is not timelineDetail"
            elif action.get("payload") != event["id"]:
                msg = f"Skip timeline detail: Action payload {action['payload']} does not match id {event['id']}"

            self.requested_detail += 1
            if msg is None:
                await self.tr.timeline_detail_v2(event["id"])
            else:
                self.received_detail += 1
                self.events.append(event)
                self.log.warning(
                    f"{self.received_detail + self.skipped_detail:>{self.detail_digits}}/{self.all_detail}: "
                    + f"{event['title']} -- {event['subtitle']} - {event['timestamp'][:19]} {msg}"
                )
                self.log.debug("%s: %s", msg, json.dumps(event, indent=4))

            if self.requested_detail % MAX_EVENT_REQUEST_BATCH == 0 and (
                (self.received_detail + self.skipped_detail) < self.requested_detail
            ):
                self.log.info(f"Requested {self.requested_detail}/{self.all_detail} timeline details.")
                yield

        self.log.info(f"Requested all timeline details ({self.requested_detail}/{self.all_detail}).")
        self.finish_if_done()

    async def request_more_timeline_details(self):
        if self.requested_detail == self.all_detail:
            return
        if (self.received_detail + self.skipped_detail) == self.requested_detail:
            try:
                await self.request_timeline_details_generator.__anext__()
            except StopAsyncIteration:
                pass

    async def process_timelineDetail(self, response):
        """
        process timeline details response
        """

        event = self.timeline_details.get(response.get("id", "dummy"), None)
        if event is None:
            self.log.warning(f"Ignoring unrequested event response {json.dumps(response, indent=4)}")
            self.skipped_detail += 1
            self.finish_if_done()
            return

        self.received_detail += 1
        event["details"] = response

        self.log.info(
            f"{self.received_detail + self.skipped_detail:>{self.detail_digits}}/{self.all_detail}: "
            + f"{event['title']} -- {event['subtitle']} - {event['timestamp'][:19]}"
        )
        self.events.append(event)
        self.event_callback(event)

        await self.request_more_timeline_details()
        self.finish_if_done()

    def finish_if_done(self):
        if self.requested_detail != self.all_detail:
            return
        if (self.received_detail + self.skipped_detail) == self.requested_detail:
            self.finish_timeline_details()

    def finish_timeline_details(self):
        self.log.info("Received all event details.")
        if self.skipped_detail > 0:
            self.log.warning(f"Skipped {self.skipped_detail} unsupported events")

        if self.store_event_database:
            self.log.info("Updating event database...")

            # read old events from all_events.json
            old_events = []
            all_events_path = self.output_path / "all_events.json"
            if (self.not_before != 0 or self.not_after != 0) and all_events_path.exists():
                with open(all_events_path, "r", encoding="utf-8") as f:
                    old_events = json.load(f)
                    for i in range(len(old_events) - 1, -1, -1):
                        ts = datetime.fromisoformat(old_events[i]["timestamp"][:19]).timestamp()
                        if (self.not_before == 0 or ts > self.not_before) and (
                            self.not_after == 0 or ts < self.not_after
                        ):
                            del old_events[i]

            # merge new and old events
            if old_events:
                cur_events = {}

                # drop duplicates in old events
                for event in old_events:
                    idtodel = None
                    for id in cur_events:
                        cur_event = cur_events[id]
                        if is_likely_same_but_newer(event, cur_event):
                            self.log.warning(
                                f"Dropping potential duplicate event {id} from {cur_event['timestamp']} due to newer event {event['id']} from {event['timestamp']}."
                            )
                            idtodel = id
                            break
                    if idtodel is not None:
                        cur_events.pop(idtodel)
                    cur_events[event["id"]] = event

                # add new events
                for event in self.events:
                    idtodel = None
                    for id in cur_events:
                        cur_event = cur_events[id]
                        if event["id"] != id and is_likely_same_but_newer(event, cur_event):
                            self.log.warning(
                                f"Dropping existing event {id} from {cur_event['timestamp']} due to newer event {event['id']} from {event['timestamp']}."
                            )
                            idtodel = id
                            break
                    if idtodel is not None:
                        cur_events.pop(idtodel)
                    cur_events[event["id"]] = event

                self.events = list(cur_events.values())

            self.events.sort(key=lambda value: datetime.fromisoformat(value["timestamp"][:19]))

            with open(all_events_path, "w", encoding="utf-8") as f:
                json.dump(self.events, f, ensure_ascii=False, indent=2, default=str)

            self.log.info("Updated event database.")

        self.dl_done = True
