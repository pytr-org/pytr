import asyncio
import json
from concurrent.futures import Future, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal

from pathvalidate import sanitize_filepath
from requests import Response
from requests_futures.sessions import FuturesSession  # type: ignore[import-untyped]

from .event import Event
from .timeline import Timeline
from .transactions import TransactionExporter
from .utils import get_logger

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
    "TRADING_ORDER_CANCELLED": "Trades",
    "TRADING_ORDER_CREATED": "Trades",
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

title_subfolder_mapping = {
    "Aktien-Bonus": "Misc",
    "Basisinformationen": "Misc",
    "Crypto Jahresaufstellung": "Misc",
    "Eignungsprüfung": "Misc",
    "Jährlicher Steuerreport": "Misc",
    "Rechtliche Dokumente": "Misc",
    "Private Equity": "Private Equity",
    "Steuerkorrektur": "Steuerkorrekturen",
    "Ex-Post Kosteninformation": "Trades",
    "Zinsen": "Zinsen",
}

subtitle_subfolder_mapping = {
    "Aktiendividende": "Dividende",
    "Bardividende": "Dividende",
    "Cash oder Aktie": "Dividende",
    "Dividende Wahlweise": "Dividende",
    "Aktienprämiendividende": "Misc",
    "Aktiensplit": "Misc",
    "Aufruf von Zwischenpapieren": "Misc",
    "Bardividende korrigiert": "Misc",
    "Bonusaktien": "Misc",
    "Erteilt": "Misc",
    "Jährliche Hauptversammlung": "Misc",
    "Spin-off": "Misc",
    "Teilnehmen?": "Misc",
    "Vorabpauschale": "Misc",
    "Zwischenvertrieb von Wertpapieren": "Misc",
    "Saveback": "Saveback",
    "Kauforder": "Trades",
    "Kauforder storniert": "Trades",
    "Limit-Buy-Order": "Trades",
    "Limit-Buy-Order abgelaufen": "Trades",
    "Limit-Buy-Order erstellt": "Trades",
    "Limit-Buy-Order storniert": "Trades",
    "Limit-Sell-Order": "Trades",
    "Limit-Sell-Order abgelaufen": "Trades",
    "Limit-Sell-Order abgelehnt": "Trades",
    "Limit-Sell-Order erstellt": "Trades",
    "Limit-Sell-Order storniert": "Trades",
    "Limit Verkauf-Order neu abgerechnet": "Trades",
    "Round up": "RoundUp",
    "Sparplan ausgeführt": "Trades",
    "Sparplan fehlgeschlagen": "Trades",
    "Stop-Sell-Order": "Trades",
    "Stop-Sell-Order storniert": "Trades",
    "Verkaufsorder": "Trades",
    "Verkaufsorder abgelehnt": "Trades",
}


class DL:
    def __init__(
        self,
        tr,
        output_path,
        filename_fmt,
        not_before=float(0),
        not_after=float("inf"),
        store_event_database=True,
        scan_for_duplicates=False,
        dump_raw_data=False,
        export_transactions=True,
        history_file="pytr_history",
        max_workers=8,
        universal_filepath=False,
        lang="en",
        date_with_time=True,
        decimal_localization=False,
        sort_export=False,
        format_export: Literal["json", "csv"] = "csv",
        flat=False,
    ):
        """
        tr: api object
        output_path: name of the directory where the downloaded files are saved
        filename_fmt: format string to customize the file names
        """
        self.tr = tr
        self.output_path = Path(output_path)
        self.filename_fmt = filename_fmt
        self.dump_raw_data = dump_raw_data
        self.export_transactions = export_transactions
        self.history_file = self.output_path / history_file
        self.universal_filepath = universal_filepath
        self.lang = lang
        self.date_with_time = date_with_time
        self.decimal_localization = decimal_localization
        self.sort_export = sort_export
        self.format_export: Literal["json", "csv"] = format_export
        self.flat = flat

        self.tl = Timeline(
            self.tr,
            self.output_path,
            not_before,
            not_after,
            store_event_database,
            scan_for_duplicates,
            dump_raw_data,
            self.dl_callback,
        )

        self.session = FuturesSession(max_workers=max_workers, session=self.tr._websession)
        self.futures: list[Future[Response]] = []

        self.events_without_docs: List[Dict[str, Any]] = []
        self.events_with_docs: List[Dict[str, Any]] = []

        self.docs_request = 0
        self.done = 0
        self.filepaths: List[str] = []
        self.doc_urls: List[str] = []
        self.doc_urls_history: List[str] = []

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

    def do_dl(self):
        asyncio.run(self.tl.tl_loop())

        if self.dump_raw_data:
            with open(self.output_path / "events_with_documents.json", "w", encoding="utf-8") as f:
                json.dump(self.events_with_docs, f, ensure_ascii=False, indent=2)

            with open(self.output_path / "other_events.json", "w", encoding="utf-8") as f:
                json.dump(self.events_without_docs, f, ensure_ascii=False, indent=2)

        if self.export_transactions:
            with (self.output_path / "account_transactions.csv").open("w", encoding="utf-8") as f:
                TransactionExporter(
                    lang=self.lang,
                    date_with_time=self.date_with_time,
                    decimal_localization=self.decimal_localization,
                ).export(
                    f,
                    [Event.from_dict(ev) for ev in self.tl.events],
                    sort=self.sort_export,
                    format=self.format_export,
                )

        self.work_responses()

    def dl_callback(self, event):
        has_docs = False
        for section in event["details"]["sections"]:
            if section["type"] != "documents":
                continue

            subfolder = None
            eventType = event.get("eventType", None)
            title = event.get("title", "")
            subtitle = event.get("subtitle", "")
            eventdesc = f"{title} {subtitle} ({event['id']})"
            sections = event.get("details", {}).get("sections", [{}])
            uebersicht_dict = next(filter(lambda x: x.get("title") in ["Übersicht"], sections), None)
            if eventType in ["timeline_legacy_migrated_events", None]:
                subfolder = title_subfolder_mapping.get(title)
                if subfolder is None:
                    subfolder = subtitle_subfolder_mapping.get(subtitle)
            else:
                subfolder = event_subfolder_mapping.get(eventType)

            if subfolder is None and uebersicht_dict:
                for item in uebersicht_dict.get("data", []):
                    ititle = item.get("title", "")
                    if ititle == "Überweisung":
                        subfolder = "Einzahlungen"

            if subfolder is None and sections:
                for item in sections:
                    ititle = item.get("title", "")
                    if (
                        ititle.startswith("Du hast ") and (ititle.endswith(" erhalten") or ititle.endswith(" gesendet"))
                    ) or (
                        ititle
                        in [
                            "You received an offer to participate in a capital increase",
                            "Deine Aktien waren von einer Kapitalmaßnahme betroffen",
                            "Aktien wurden im Rahmen einer Kapitalmaßnahme entfernt",
                        ]
                    ):
                        subfolder = "Misc"
                        break

            if subfolder is None:
                self.log.warning(f"no subfolder mapping for {eventdesc}")

            for doc in section["data"]:
                if isinstance(doc["action"]["payload"], dict):
                    self.log.warning(
                        f'Download of document with new API-Path URL "{doc["action"]["payload"]["path"]}" is not possible. (yet?)'
                    )
                    continue
                has_docs = True
                timestamp_str = event["timestamp"]
                if timestamp_str[-3] != ":":
                    timestamp_str = timestamp_str[:-2] + ":" + timestamp_str[-2:]
                try:
                    docdate = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    self.log.warning(f"no timestamp parseable from {timestamp_str}")
                    docdate = datetime.now()

                title = f"{doc['title']} - {event['title']} - {event['subtitle']}"
                self.dl_doc(doc, title, subfolder, docdate)

        if has_docs:
            self.events_with_docs.append(event)
        else:
            self.events_without_docs.append(event)

    def dl_doc(self, doc, titleText, subfolder, doc_date):
        """
        send asynchronous request, append future with filepath to self.futures
        """
        doc_url = doc["action"]["payload"]
        if isinstance(doc_url, dict):
            doc_url = f"https://api.traderepublic.com/{doc_url['path']}"

        if self.flat:
            doc_url_base = doc_url.split("?")[0]
            filename = doc_url_base.split("/")[-1]
            filepath = self.output_path / filename
        else:
            subtitleText = doc.get("detail")
            if subtitleText is None:
                subtitleText = ""

            doc_id = doc["id"]
            iso_date = doc_date.strftime("%Y-%m-%d")
            time = doc_date.strftime("%H:%M")

            if subfolder is not None:
                directory = self.output_path / subfolder
            else:
                directory = self.output_path

            # If doc_type is something like 'Kosteninformation 2', then strip the 2 and save it in doc_type_num
            doc_type = doc["title"].rsplit(" ")
            if doc_type[-1].isnumeric() is True:
                doc_type_num = doc_type.pop()
            else:
                doc_type_num = ""

            doc_type = " ".join(doc_type)
            if doc_type == "Abrechnung Ausführung" or doc_type == "Abrechnungsausführung":
                doc_type = "Abrechnung"
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

            # In case, the filename already ends with the doc id, we remove it to avoid a duplicate id in the name
            filename_with_doc_id = filename.removesuffix(doc_id).rstrip() + f" ({doc_id})"

            if doc_type in ["Kontoauszug", "Depotauszug"]:
                filepath = directory / "Abschlüsse" / f"{filename}" / f"{doc_type}.pdf"
                filepath_with_doc_id = directory / "Abschlüsse" / f"{filename_with_doc_id}" / f"{doc_type}.pdf"
            else:
                filepath = directory / doc_type / f"{filename}.pdf"
                filepath_with_doc_id = directory / doc_type / f"{filename_with_doc_id}.pdf"

            if self.universal_filepath:
                filepath = sanitize_filepath(filepath, "_", "universal")
                filepath_with_doc_id = sanitize_filepath(filepath_with_doc_id, "_", "universal")
            else:
                filepath = sanitize_filepath(filepath, "_", "auto")
                filepath_with_doc_id = sanitize_filepath(filepath_with_doc_id, "_", "auto")

            if filepath in self.filepaths:
                self.log.debug(f"File {filepath} already in queue. Append document id {doc_id}...")
                if filepath_with_doc_id in self.filepaths:
                    self.log.debug(f"File {filepath_with_doc_id} already in queue. Skipping...")
                    return
                else:
                    filepath = filepath_with_doc_id

        doc["local_filepath"] = str(filepath)
        self.filepaths.append(str(filepath))

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
            future.filepath = filepath  # type: ignore[attr-defined]
            future.doc_url_base = doc_url_base  # type: ignore[attr-defined]
            self.futures.append(future)  # type: ignore[arg-type]
            self.log.debug(f"Added {filepath} to queue")
        else:
            self.log.debug(f"file {filepath} already exists. Skipping...")

    def work_responses(self):
        """
        process responses of async download requests
        """
        if len(self.doc_urls) == 0:
            self.log.info("Nothing to download.")
            return

        with self.history_file.open("a") as history_file:
            self.log.info("Waiting for downloads to complete...")
            for future in as_completed(self.futures):
                if future.filepath.is_file() is True:  # type: ignore[attr-defined]
                    self.log.debug(f"file {future.filepath} was already downloaded.")  # type: ignore[attr-defined]

                try:
                    r = future.result()
                except Exception as e:
                    self.log.fatal(str(e))
                    continue

                future.filepath.parent.mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]
                with open(future.filepath, "wb") as f:  # type: ignore[attr-defined]
                    f.write(r.content)
                    self.done += 1
                    history_file.write(f"{future.doc_url_base}\n")  # type: ignore[attr-defined]

                    self.log.debug(f"{self.done:>3}/{len(self.doc_urls)} {future.filepath.name}")  # type: ignore[attr-defined]

                if self.done == len(self.doc_urls):
                    self.log.info("Done.")
                    return
