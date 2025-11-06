from concurrent.futures import as_completed
from pathlib import Path

from requests_futures.sessions import FuturesSession  # type: ignore[import-untyped]

from pytr.api import TradeRepublicError
from pytr.timeline import Timeline
from pytr.utils import get_logger, preview


class DlRaw:
    def __init__(
        self,
        tr,
        output_path,
        max_workers=8,
        lang="en",
        date_with_time=True,
        decimal_localization=False,
        sort_export=False,
        format_export="csv",
    ):
        """
        tr: api object
        output_path: name of the directory where the downloaded files are saved
        """
        self.tr = tr
        self.output_path = Path(output_path)
        self.lang = lang
        self.date_with_time = date_with_time
        self.decimal_localization = decimal_localization
        self.sort_export = sort_export
        self.format_export = format_export

        self.session = FuturesSession(max_workers=max_workers, session=self.tr._websession)
        self.futures = []

        self.docs_request = 0
        self.done = 0
        self.filepaths = []
        self.doc_urls = []
        self.doc_urls_history = []
        self.tl = Timeline(self.tr, 0)
        self.log = get_logger(__name__)

    async def dl_loop(self):
        await self.tl.get_next_timeline_transactions(None, self)

        while True:
            try:
                _, subscription, response = await self.tr.recv()
            except TradeRepublicError as e:
                self.log.error('Error response for subscription "%s". Re-subscribing...', e.subscription)
                await self.tr.subscribe(e.subscription)
                continue

            if subscription.get("type", "") == "timelineTransactions":
                await self.tl.get_next_timeline_transactions(response, self)
            elif subscription.get("type", "") == "timelineActivityLog":
                await self.tl.get_next_timeline_activity_log(response, self)
            elif subscription.get("type", "") == "timelineDetailV2":
                await self.tl.process_timelineDetail(response, self)
            else:
                self.log.warning("unmatched subscription of type '%s':\n%s", subscription["type"], preview(response))

    def dl_doc(self, doc, titleText=None, subfolder=None, doc_date=None):
        """
        send asynchronous request, append future with filepath to self.futures
        """
        doc_url = doc["action"]["payload"]
        doc_id = doc["id"]

        filepath = self.output_path / f"{doc_id}.pdf"

        if filepath in self.filepaths:
            self.log.debug("File %s already in queue. Append document id %s...", filepath, doc_id)

        doc["local_filepath"] = str(filepath)

        self.filepaths.append(filepath)

        if filepath.is_file() is False:
            doc_url_base = doc_url.split("?")[0]
            if doc_url_base in self.doc_urls:
                self.log.debug("URL %s already in queue. Skipping...", doc_url_base)
                return
            else:
                self.doc_urls.append(doc_url_base)

            future = self.session.get(doc_url)
            future.filepath = filepath
            future.doc_url_base = doc_url_base
            self.futures.append(future)
            self.log.debug("Added %s to queue", filepath)
        else:
            self.log.debug("file %s already exists. Skipping...", filepath)

    def work_responses(self):
        """
        process responses of async requests
        """
        if len(self.doc_urls) == 0:
            self.log.info("Nothing to download")
            exit(0)

        self.log.info("Waiting for downloads to complete..")
        for future in as_completed(self.futures):
            if future.filepath.is_file() is True:
                self.log.debug("file %s was already downloaded.", future.filepath)

            try:
                r = future.result()
            except Exception as e:
                self.log.fatal(str(e))

            future.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(future.filepath, "wb") as f:
                f.write(r.content)
                self.done += 1

                self.log.debug("%3d/%s %s", self.done, len(self.doc_urls), future.filepath.name)

            if self.done == len(self.doc_urls):
                self.log.info("Done.")
                exit(0)
