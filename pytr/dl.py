import os
import re

from concurrent.futures import as_completed
from requests_futures.sessions import FuturesSession

from pytr.utils import preview, Timeline


class DL:
    def __init__(self, tr, output_path, headers={'User-Agent': 'pytr'}):
        self.tr = tr
        self.output_path = output_path
        self.headers = headers

        self.session = FuturesSession()
        self.futures = []

        self.docs_request = 0
        self.done = 0

        self.tl = Timeline(self.tr)

    async def dl_loop(self):
        await self.tl.get_next_timeline()

        while True:
            _subscription_id, subscription, response = await self.tr.recv()

            if subscription["type"] == "timeline":
                await self.tl.get_next_timeline(response)
            elif subscription["type"] == "timelineDetail":
                await self.tl.timelineDetail(response, self)
            else:
                print(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

    def dl_doc(self, doc, titleText, subtitleText, subfolder=None):
        """
        send asynchronous request, append future with filepath to self.futures
        """
        doc_url = doc["action"]["payload"]

        date = doc["detail"]
        iso_date = "-".join(date.split(".")[::-1])

        # extract time from subtitleText
        time = re.findall("um (\\d+:\\d+) Uhr", subtitleText)
        if time == []:
            time = ""
        else:
            time = f" {time[0]}"

        if subfolder is not None:
            directory = os.path.join(self.output_path, subfolder)
        else:
            directory = self.output_path

        # If doc_type is something like "Kosteninformation 2", then strip the 2 and save it in doc_type_num
        doc_type = doc['title'].rsplit(" ")
        if doc_type[-1].isnumeric() is True:
            doc_type_num = f" {doc_type.pop()}"
        else:
            doc_type_num = ""

        doc_type = " ".join(doc_type)
        filepath = os.path.join(directory, doc_type, f"{iso_date}{time} {titleText}{doc_type_num}.pdf")

        # if response['titleText'] == "Shopify":
        #    print(json.dumps(response))

        if os.path.isfile(filepath) is False:
            self.docs_request += 1
            future = self.session.get(doc_url)
            future.filepath = filepath
            self.futures.append(future)
        else:
            print("file {filepath} already exists. Skipping...")

    def work_responses(self):
        """
        process responses of async requests
        """
        for future in as_completed(self.futures):
            r = future.result()
            os.makedirs(os.path.dirname(future.filepath), exist_ok=True)
            with open(future.filepath, "wb") as f:
                f.write(r.content)
                self.done += 1

                print(f"done: {self.done:>3}/{self.docs_request} {os.path.basename(future.filepath)}")

                if self.done == self.docs_request:
                    print("Done.")
                    exit(0)

    def dl_all(output_path):
        """
        todo
        """
        pass
