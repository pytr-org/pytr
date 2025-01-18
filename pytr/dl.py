import re

from concurrent.futures import as_completed
from pathlib import Path
from requests_futures.sessions import FuturesSession

from pathvalidate import sanitize_filepath

from pytr.utils import preview, get_logger
from pytr.api import TradeRepublicError
from pytr.timeline import Timeline


class DL:
    def __init__(
        self,
        tr,
        output_path,
        filename_fmt,
        since_timestamp=0,
        history_file="pytr_history",
        max_workers=8,
        universal_filepath=False,
        sort_export=False,
    ):
        """
        tr: api object
        output_path: name of the directory where the downloaded files are saved
        filename_fmt: format string to customize the file names
        since_timestamp: downloaded files since this date (unix timestamp)
        """
        self.tr = tr
        self.output_path = Path(output_path)
        self.history_file = self.output_path / history_file
        self.filename_fmt = filename_fmt
        self.since_timestamp = since_timestamp
        self.universal_filepath = universal_filepath
        self.sort_export = sort_export

        self.session = FuturesSession(
            max_workers=max_workers, session=self.tr._websession
        )
        self.futures = []

        self.docs_request = 0
        self.done = 0
        self.filepaths = []
        self.doc_urls = []
        self.doc_urls_history = []
        self.tl = Timeline(self.tr, self.since_timestamp)
        self.log = get_logger(__name__)
        self.load_history()

    def load_history(self):
        """
        Read history file with URLs if it exists, otherwise create empty file
        """
        if self.history_file.exists():
            with self.history_file.open() as f:
                self.doc_urls_history = f.read().splitlines()
            self.log.info(f"Found {len(self.doc_urls_history)} lines in history file")
        else:
            self.history_file.parent.mkdir(exist_ok=True, parents=True)
            self.history_file.touch()
            self.log.info("Created history file")

    async def dl_loop(self):
        await self.tl.get_next_timeline_transactions()

        while True:
            try:
                _, subscription, response = await self.tr.recv()
            except TradeRepublicError as e:
                self.log.error(
                    f'Error response for subscription "{e.subscription}". Re-subscribing...'
                )
                await self.tr.subscribe(e.subscription)
                continue

            if subscription.get("type", "") == "timelineTransactions":
                await self.tl.get_next_timeline_transactions(response)
            elif subscription.get("type", "") == "timelineActivityLog":
                await self.tl.get_next_timeline_activity_log(response)
            elif subscription.get("type", "") == "timelineDetailV2":
                await self.tl.process_timelineDetail(response, self)
            else:
                self.log.warning(
                    f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}"
                )

    def dl_doc(self, doc, titleText, subtitleText, subfolder=None):
        """
        send asynchronous request, append future with filepath to self.futures
        """
        doc_url = doc["action"]["payload"]
        if subtitleText is None:
            subtitleText = ""

        try:
            date = doc["detail"]
            iso_date = "-".join(date.split(".")[::-1])
        except KeyError:
            date = ""
            iso_date = ""
        doc_id = doc["id"]

        # extract time from subtitleText
        try:
            time = re.findall("um (\\d+:\\d+) Uhr", subtitleText)
            if time == []:
                time = ""
            else:
                time = f" {time[0]}"
        except TypeError:
            time = ""

        if subfolder is not None:
            directory = self.output_path / subfolder
        else:
            directory = self.output_path

        # If doc_type is something like 'Kosteninformation 2', then strip the 2 and save it in doc_type_num
        doc_type = doc["title"].rsplit(" ")
        if doc_type[-1].isnumeric() is True:
            doc_type_num = f" {doc_type.pop()}"
        else:
            doc_type_num = ""

        doc_type = " ".join(doc_type)
        titleText = titleText.replace("\n", "").replace("/", "-")
        subtitleText = subtitleText.replace("\n", "").replace("/", "-")

        filename = self.filename_fmt.format(
            iso_date=iso_date,
            time=time,
            title=titleText,
            subtitle=subtitleText,
            doc_num=doc_type_num,
            id=doc_id,
        )

        filename_with_doc_id = filename + f" ({doc_id})"

        if doc_type in ["Kontoauszug", "Depotauszug"]:
            filepath = directory / "Abschlüsse" / f"{filename}" / f"{doc_type}.pdf"
            filepath_with_doc_id = (
                directory / "Abschlüsse" / f"{filename_with_doc_id}" / f"{doc_type}.pdf"
            )
        else:
            filepath = directory / doc_type / f"{filename}.pdf"
            filepath_with_doc_id = directory / doc_type / f"{filename_with_doc_id}.pdf"

        if self.universal_filepath:
            filepath = sanitize_filepath(filepath, "_", "universal")
            filepath_with_doc_id = sanitize_filepath(
                filepath_with_doc_id, "_", "universal"
            )
        else:
            filepath = sanitize_filepath(filepath, "_", "auto")
            filepath_with_doc_id = sanitize_filepath(filepath_with_doc_id, "_", "auto")

        if filepath in self.filepaths:
            self.log.debug(
                f"File {filepath} already in queue. Append document id {doc_id}..."
            )
            if filepath_with_doc_id in self.filepaths:
                self.log.debug(
                    f"File {filepath_with_doc_id} already in queue. Skipping..."
                )
                return
            else:
                filepath = filepath_with_doc_id
        doc["local_filepath"] = str(filepath)
        self.filepaths.append(filepath)

        if filepath.is_file() is False:
            doc_url_base = doc_url.split("?")[0]
            if doc_url_base in self.doc_urls:
                self.log.debug(f"URL {doc_url_base} already in queue. Skipping...")
                return
            elif doc_url_base in self.doc_urls_history:
                self.log.debug(f"URL {doc_url_base} already in history. Skipping...")
                return
            else:
                self.doc_urls.append(doc_url_base)

            future = self.session.get(doc_url)
            future.filepath = filepath
            future.doc_url_base = doc_url_base
            self.futures.append(future)
            self.log.debug(f"Added {filepath} to queue")
        else:
            self.log.debug(f"file {filepath} already exists. Skipping...")

    def work_responses(self):
        """
        process responses of async requests
        """
        if len(self.doc_urls) == 0:
            self.log.info("Nothing to download")
            exit(0)

        with self.history_file.open("a") as history_file:
            self.log.info("Waiting for downloads to complete..")
            for future in as_completed(self.futures):
                if future.filepath.is_file() is True:
                    self.log.debug(f"file {future.filepath} was already downloaded.")

                try:
                    r = future.result()
                except Exception as e:
                    self.log.fatal(str(e))

                future.filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(future.filepath, "wb") as f:
                    f.write(r.content)
                    self.done += 1
                    history_file.write(f"{future.doc_url_base}\n")

                    self.log.debug(
                        f"{self.done:>3}/{len(self.doc_urls)} {future.filepath.name}"
                    )

                if self.done == len(self.doc_urls):
                    self.log.info("Done.")
                    exit(0)
