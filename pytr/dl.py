import re

from concurrent.futures import as_completed
from pathlib import Path
from requests_futures.sessions import FuturesSession

from pathvalidate import sanitize_filepath

from pytr.utils import preview, Timeline, get_logger
from pytr.api import TradeRepublicError


class DL:
    def __init__(self, tr, output_path, filename_fmt, since_timestamp=0, history_file='pytr_history'):
        '''
        tr: api object
        output_path: name of the directory where the downloaded files are saved
        filename_fmt: format string to customize the file names
        since_timestamp: downloaded files since this date (unix timestamp)
        '''
        self.tr = tr
        self.output_path = Path(output_path)
        self.history_file = self.output_path / history_file
        self.filename_fmt = filename_fmt
        self.since_timestamp = since_timestamp

        self.session = FuturesSession()
        self.futures = []

        self.docs_request = 0
        self.done = 0
        self.filepaths = []
        self.doc_urls = []
        self.doc_urls_history = []
        self.tl = Timeline(self.tr)
        self.log = get_logger(__name__)
        self.load_history()

    def load_history(self):
        '''
        Read history file with URLs if it exists, otherwise create empty file
        '''
        if self.history_file.exists():
            with self.history_file.open() as f:
                self.doc_urls_history = f.read().splitlines()
            self.log.info(f'Found {len(self.doc_urls_history)} lines in history file')
        else:
            self.history_file.parent.mkdir(exist_ok=True, parents=True)
            self.history_file.touch()
            self.log.info('Created history file')

    async def dl_loop(self):
        await self.tl.get_next_timeline(max_age_timestamp=self.since_timestamp)

        while True:
            try:
                _subscription_id, subscription, response = await self.tr.recv()
            except TradeRepublicError as e:
                self.log.fatal(str(e))

            if subscription['type'] == 'timeline':
                await self.tl.get_next_timeline(response, max_age_timestamp=self.since_timestamp)
            elif subscription['type'] == 'timelineDetail':
                await self.tl.timelineDetail(response, self, max_age_timestamp=self.since_timestamp)
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
            directory = self.output_path / subfolder
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
        if doc_type in ['Kontoauszug', 'Depotauszug']:
            filepath = directory / 'Abschlüsse' / f'{filename}' / f'{doc_type}.pdf'
        else:
            filepath = directory / doc_type / f'{filename}.pdf'

        filepath = sanitize_filepath(filepath, '_', 'auto')

        if filepath in self.filepaths:
            self.log.debug(f'File {filepath} already in queue. Skipping...')
            return
        else:
            self.filepaths.append(filepath)

        if filepath.is_file() is False:
            doc_url_base = doc_url.split('?')[0]
            if doc_url_base in self.doc_urls:
                self.log.debug(f'URL {doc_url_base} already in queue. Skipping...')
                return
            elif doc_url_base in self.doc_urls_history:
                self.log.debug(f'URL {doc_url_base} already in history. Skipping...')
                return
            else:
                self.doc_urls.append(doc_url_base)

            future = self.session.get(doc_url)
            future.filepath = filepath
            future.doc_url_base = doc_url_base
            self.futures.append(future)
            self.log.debug(f'Added {filepath} to queue')
        else:
            self.log.debug(f'file {filepath} already exists. Skipping...')

    def work_responses(self):
        '''
        process responses of async requests
        '''
        if len(self.doc_urls) == 0:
            self.log.info('Nothing to download')
            exit(0)

        with self.history_file.open('a') as history_file:
            self.log.info('Waiting for downloads to complete..')
            for future in as_completed(self.futures):
                if future.filepath.is_file() is True:
                    self.log.debug(f'file {future.filepath} was already downloaded.')

                r = future.result()
                future.filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(future.filepath, 'wb') as f:
                    f.write(r.content)
                    self.done += 1
                    history_file.write(f'{future.doc_url_base}\n')

                    self.log.debug(f'{self.done:>3}/{len(self.doc_urls)} {future.filepath.name}')

                if self.done == len(self.doc_urls):
                    self.log.info('Done.')
                    exit(0)
