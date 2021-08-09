import os
import re

from concurrent.futures import as_completed
from requests_futures.sessions import FuturesSession

from pytr.utils import preview, Timeline, get_logger
from pytr.api import TradeRepublicError


class DL:
    def __init__(self, tr, output_path, filename_fmt, headers={'User-Agent': 'pytr'}):
        self.tr = tr
        self.output_path = output_path
        self.headers = headers
        self.filename_fmt = filename_fmt

        self.session = FuturesSession()
        self.futures = []

        self.docs_request = 0
        self.done = 0
        self.filepaths = []
        self.doc_urls = []
        self.tl = Timeline(self.tr)
        self.log = get_logger(__name__)

    async def dl_loop(self):
        await self.tl.get_next_timeline()

        while True:
            try:
                _subscription_id, subscription, response = await self.tr.recv()
            except TradeRepublicError as e:
                self.log.error(str(e))

            if subscription['type'] == 'timeline':
                await self.tl.get_next_timeline(response)
            elif subscription['type'] == 'timelineDetail':
                await self.tl.timelineDetail(response, self)
            else:
                self.log.warning(f"unmatched subscription of type '{subscription['type']}':\n{preview(response)}")

    def dl_doc(self, doc, titleText, subtitleText, subfolder=None):
        '''
        send asynchronous request, append future with filepath to self.futures
        '''
        doc_url = doc['action']['payload']

        date = doc['detail']
        iso_date = '-'.join(date.split('.')[::-1])

        # extract time from subtitleText
        time = re.findall('um (\\d+:\\d+) Uhr', subtitleText)
        if time == []:
            time = ''
        else:
            time = f' {time[0]}'

        if subfolder is not None:
            directory = os.path.join(self.output_path, subfolder)
        else:
            directory = self.output_path

        # If doc_type is something like 'Kosteninformation 2', then strip the 2 and save it in doc_type_num
        doc_type = doc['title'].rsplit(' ')
        if doc_type[-1].isnumeric() is True:
            doc_type_num = f' {doc_type.pop()}'
        else:
            doc_type_num = ''

        doc_type = ' '.join(doc_type)
        titleText = titleText.replace('\n', '').replace('/', '-')
        subtitleText = subtitleText.replace('\n', '').replace('/', '-')

        filename = self.filename_fmt.format(
            iso_date=iso_date, time=time, title=titleText, subtitle=subtitleText, doc_num=doc_type_num
        )
        if os.name == 'nt':
            badChars = ['/', '\n', ':', '@', '.']
            for badChar in badChars:
                filename = filename.replace(badChar, '')

        if doc_type in ['Kontoauszug', 'Depotauszug']:
            filepath = os.path.join(directory, 'Abschlüsse', f'{filename}', f'{doc_type}.pdf')
        else:
            filepath = os.path.join(directory, doc_type, f'{filename}.pdf')

        if filepath in self.filepaths:
            self.log.debug(f'File {filepath} already in queue. Skipping...')
            return
        else:
            self.filepaths.append(filepath)

        if os.path.isfile(filepath) is False:
            doc_url_base = doc_url.split('?')[0]
            if doc_url_base in self.doc_urls:
                self.log.warning(f'URL {doc_url_base} already in queue. Skipping...')
                return
            else:
                self.doc_urls.append(doc_url_base)

            future = self.session.get(doc_url)
            future.filepath = filepath
            self.futures.append(future)
        else:
            self.log.debug(f'file {filepath} already exists. Skipping...')

    def work_responses(self):
        '''
        process responses of async requests
        '''
        if len(self.doc_urls) == 0:
            self.log.info('Nothing to download')
            exit(0)

        self.log.info('Waiting for downloads to complete..')
        for future in as_completed(self.futures):
            if os.path.isfile(future.filepath) is True:
                self.log.debug(f'file {future.filepath} was already downloaded.')

            r = future.result()
            os.makedirs(os.path.dirname(future.filepath), exist_ok=True)
            with open(future.filepath, 'wb') as f:
                f.write(r.content)
                self.done += 1

                self.log.debug(f'{self.done:>3}/{len(self.doc_urls)} {os.path.basename(future.filepath)}')

                if self.done == len(self.doc_urls):
                    self.log.info('Done.')
                    exit(0)

    def dl_all(output_path):
        '''
        TODO
        '''
