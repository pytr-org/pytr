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
    "BANK_TRANSACTION_OUTGOING": "Auszahlungen",
    "CREDIT": "Dividende",
    "SSP_CORPORATE_ACTION_INVOICE_CASH": "Dividende",
    "SSP_CORPORATE_ACTION_CASH": "Dividende",
    "SSP_CORPORATE_ACTION_CASH_AND_STOCK": "Dividende",
    "ACCOUNT_TRANSFER_INCOMING": "Einzahlungen",
    "INCOMING_TRANSFER_DELEGATION": "Einzahlungen",
    "INCOMING_TRANSFER": "Einzahlungen",
    "PAYMENT_INBOUND_GOOGLE_PAY": "Einzahlungen",
    "PAYMENT_INBOUND_SEPA_DIRECT_DEBIT": "Einzahlungen",
    "BANK_TRANSACTION_INCOMING": "Einzahlungen",
    "PAYMENT_INBOUND": "Einzahlungen",
    "JUNIOR_P2P_TRANSFER": "Einzahlungen",
    "CARD_TRANSACTION": "Karte",
    "CARD_REFUND": "Karte",
    "CARD_VERIFICATION": "Karte",
    "CREDIT_CANCELED": "Misc",
    "CRYPTO_ANNUAL_STATEMENT": "Misc",
    "CRYPTO_TNC_UPDATE_2025": "Misc",
    "CSX_CHAT_ACTIVITY": "Misc",
    "CUSTOMER_CREATED": "Misc",
    "DEVICE_RESET": "Misc",
    "DOCUMENTS_ACCEPTED": "Misc",
    "DOCUMENTS_CHANGED": "Misc",
    "DOCUMENTS_CREATED": "Misc",
    "EMAIL_VALIDATED": "Misc",
    "EXEMPTION_ORDER_CHANGED": "Misc",
    "EX_POST_COST_REPORT": "Misc",
    "EX_POST_COST_REPORT_CREATED": "Misc",
    "GENERAL_MEETING": "Misc",
    "GESH_CORPORATE_ACTION": "Misc",
    "INPAYMENTS_SEPA_MANDATE_CREATED": "Misc",
    "INSTRUCTION_CORPORATE_ACTION": "Misc",
    "JUNIOR_ONBOARDING_GUARDIAN_B_CONSENT": "Misc",
    "PRE_DETERMINED_TAX_BASE_EARNING": "Misc",
    "PRIVATE_MARKETS_SUITABILITY_QUIZ_COMPLETED": "Misc",
    "PUK_CREATED": "Misc",
    "QUARTERLY_NET_WORTH_STATEMENT_CREATED": "Misc",
    "QUARTERLY_REPORT": "Misc",
    "REFERENCE_ACCOUNT_CHANGED": "Misc",
    "SECURITIES_ACCOUNT_CREATED": "Misc",
    "SHAREBOOKING": "Misc",
    "SHAREBOOKING_TRANSACTIONAL": "Misc",
    "SPARE_CHANGE_AGGREGATE": "RoundUp",
    "SSP_CAPITAL_INCREASE_CUSTOMER_INSTRUCTION": "Misc",
    "SSP_CORPORATE_ACTION_ACTIVITY": "Misc",
    "SSP_CORPORATE_ACTION_CASH_NON_DIVIDEND": "Misc",
    "SSP_CORPORATE_ACTION_INFORMATIVE": "Misc",
    "SSP_CORPORATE_ACTION_INFORMATIVE_NOTIFICATION": "Misc",
    "SSP_CORPORATE_ACTION_INSTRUCTION": "Misc",
    "SSP_CORPORATE_ACTION_INVOICE_SHARES": "Misc",
    "SSP_CORPORATE_ACTION_NO_CASH": "Misc",
    "SSP_CORPORATE_ACTION_UPCOMING": "Misc",
    "SSP_DIVIDEND_OPTION_CUSTOMER_INSTRUCTION": "Misc",
    "SSP_GENERAL_MEETING_CUSTOMER_INSTRUCTION": "Misc",
    "SSP_TENDER_OFFER_CUSTOMER_INSTRUCTION": "Misc",
    "STOCK_PERK_REFUNDED": "Misc",
    "TAX_YEAR_END_REPORT": "Misc",
    "TAX_YEAR_END_REPORT_CREATED": "Misc",
    "VERIFICATION_TRANSFER_ACCEPTED": "Misc",
    "YEAR_END_TAX_REPORT": "Misc",
    "BENEFITS_SPARE_CHANGE_EXECUTION": "RoundUp",
    "BENEFITS_SAVEBACK_EXECUTION": "Saveback",
    "SAVEBACK_AGGREGATE": "Saveback",
    "SAVINGS_PLAN_EXECUTED": "Sparplan",
    "SAVINGS_PLAN_INVOICE_CREATED": "Sparplan",
    "TRADING_SAVINGSPLAN_EXECUTED": "Sparplan",
    "TRADING_SAVINGSPLAN_EXECUTION_FAILED": "Sparplan",
    "SSP_TAX_CORRECTION": "Steuerkorrekturen",
    "SSP_TAX_CORRECTION_INVOICE": "Steuerkorrekturen",
    "TAX_CORRECTION": "Steuerkorrekturen",
    "TAX_REFUND": "Steuerkorrekturen",
    "IPO_TRADE_EXECUTED": "Trades",
    "ORDER_CANCELED": "Trades",
    "ORDER_EXECUTED": "Trades",
    "ORDER_EXPIRED": "Trades",
    "ORDER_REJECTED": "Trades",
    "PRIVATE_MARKET_FUND_TRADE_EXECUTED": "Trades",
    "PRIVATE_MARKETS_TRADE_EXECUTED": "Trades",
    "PRIVATE_MARKETS_ORDER_CREATED": "Trades",
    "TRADE_CORRECTED": "Trades",
    "TRADE_INVOICE": "Trades",
    "TRADING_ORDER_CANCELLED": "Trades",
    "TRADING_ORDER_CREATED": "Trades",
    "TRADING_ORDER_EXPIRED": "Trades",
    "TRADING_ORDER_REJECTED": "Trades",
    "TRADING_TRADE_EXECUTED": "Trades",
    "ACQUISITION_TRADE_PERK": "Misc",
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
    "Dividende. Cash oder Stockdividende?": "Dividende",
    "Aktienprämiendividende": "Dividende",
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
        max_workers=8,
        universal_filepath=False,
        lang="en",
        date_with_time=True,
        decimal_localization=False,
        sort_export=False,
        format_export: Literal["json", "csv"] = "csv",
        flat=False,
        load_event_database=None,
        dry_run=False,
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
        self.universal_filepath = universal_filepath
        self.lang = lang
        self.date_with_time = date_with_time
        self.decimal_localization = decimal_localization
        self.sort_export = sort_export
        self.format_export: Literal["json", "csv"] = format_export
        self.flat = flat
        self.dry_run = dry_run

        self.tl = Timeline(
            self.tr,
            self.output_path,
            not_before,
            not_after,
            store_event_database,
            scan_for_duplicates,
            dump_raw_data,
            self.dl_callback,
            load_event_database=load_event_database,
        )

        self.session = (
            FuturesSession(max_workers=max_workers, session=self.tr._websession) if self.tr is not None else None
        )
        self.futures: list[Future[Response]] = []

        self.events_without_docs: List[Dict[str, Any]] = []
        self.events_with_docs: List[Dict[str, Any]] = []

        self.docs_request = 0
        self.done = 0
        self.filepaths: List[str] = []
        self.doc_urls: List[str] = []
        self.events_processed = 0

        self.log = get_logger(__name__)
        if load_event_database is not None:
            self.dry_run = True

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
        if hasattr(self, "tl") and not self.tl.fetch_from_tr:
            self.events_processed += 1
            if self.events_processed % 1000 == 0:
                self.log.info(f"Processing events: {self.events_processed}/{self.tl.all_detail}")
        has_docs = False
        for section in event["details"]["sections"]:
            if section["type"] != "documents":
                continue

            subfolder = None
            eventType = (event.get("eventType") or "").upper() or None
            title = event.get("title", "")
            subtitle = event.get("subtitle", "")
            eventdesc = f"{title} {subtitle} ({event['id']})"
            sections = event.get("details", {}).get("sections", [{}])
            uebersicht_dict = next(filter(lambda x: x.get("title") in ["Übersicht"], sections), None)
            if eventType in ["TIMELINE_LEGACY_MIGRATED_EVENTS", None]:
                subfolder = title_subfolder_mapping.get(title)
                if subfolder is None:
                    subfolder = subtitle_subfolder_mapping.get(subtitle)
            else:
                subfolder = event_subfolder_mapping.get(eventType)
                if subfolder == "Misc":
                    subtitle_override = subtitle_subfolder_mapping.get(subtitle)
                    if subtitle_override is not None:
                        subfolder = subtitle_override

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

            doc_type_counts = {}
            for doc in section["data"]:
                if not isinstance(doc["action"]["payload"], dict):
                    t = doc["title"].rsplit(" ")
                    t = " ".join(t[:-1] if t[-1].isnumeric() else t)
                    doc_type_counts[t] = doc_type_counts.get(t, 0) + 1
            doc_type_seen = {}

            for idx, doc in enumerate(section["data"]):
                if isinstance(doc["action"]["payload"], dict):
                    # self.log.warning(
                    #     f'Download of document with new API-Path URL "{doc["action"]["payload"]["path"]}" is not possible. (yet?)'
                    # )
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

                t = doc["title"].rsplit(" ")
                has_num = t[-1].isnumeric()
                t = " ".join(t[:-1] if has_num else t)
                doc_type_seen[t] = doc_type_seen.get(t, 0) + 1
                if not has_num and doc_type_counts[t] > 1 and doc_type_seen[t] > 1:
                    suffix = f" {doc_type_seen[t]}" if t == "Dokumente" else f" - {doc_type_seen[t] - 1}"
                else:
                    suffix = ""
                title = f"{doc['title']} - {event['title']} - {event['subtitle']}{suffix}"

                self.dl_doc(
                    doc,
                    title,
                    subfolder,
                    docdate,
                    event.get("subtitle") or "",
                    subdir_override=event["title"] if eventType == "ACQUISITION_TRADE_PERK" else None,
                )

        if has_docs:
            self.events_with_docs.append(event)
        else:
            self.events_without_docs.append(event)

    def dl_doc(self, doc, titleText, subfolder, doc_date, subtitle="", subdir_override=None):
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
            if doc_type == "Bestätigung eines Ausführungsfehlers":
                doc_type = "Ausführungsfehler"
            titleText = titleText.replace("\n", "").replace("/", "-")
            if doc_type == "Dokumente" or doc_type == "Steuerabrechnung":
                titleText = titleText.removeprefix("Dokumente - ").removeprefix("Steuerabrechnung - ")
                if subtitle and subfolder == "Misc":
                    titleText = titleText.removesuffix(f" - {subtitle}")
            else:
                titleText = (
                    titleText.replace("Abrechnung Ausführung - ", "Abrechnung - ")
                    .replace("Abrechnungsausführung - ", "Abrechnung - ")
                    .replace("Bestätigung eines Ausführungsfehlers - ", "Ausführungsfehler - ")
                    .replace(" - Teilnehmen?", "")
                )
            titleText = titleText.removesuffix(" - None")
            subtitleText = subtitleText.replace("\n", "").replace("/", "-")

            filename = self.filename_fmt.format(
                iso_date=iso_date,
                time=time,
                title=titleText,
                subtitle=subtitleText,
                doc_num=doc_type_num,
                id=doc_id,
            )
            filename = filename.rstrip("?")
            # In case, the filename already ends with the doc id, we remove it to avoid a duplicate id in the name
            filename_with_doc_id = filename.removesuffix(doc_id).rstrip() + f" ({doc_id})"

            if doc_type in ["Kontoauszug", "Depotauszug"]:
                filepath = directory / "Abschlüsse" / f"{filename}" / f"{doc_type}.pdf"
                filepath_with_doc_id = directory / "Abschlüsse" / f"{filename_with_doc_id}" / f"{doc_type}.pdf"
            elif (
                doc_type in ["Dokumente", "Steuerabrechnung", "Dividende Wahlweise", "Dividendenbeleg"]
                or (doc_type == "Transaktionsbestätigung" and subfolder in ["Einzahlungen", "Auszahlungen"])
                or (subfolder == "Zinsen")
                or (doc_type == "Abrechnung" and subfolder in ["RoundUp", "Saveback", "Sparplan", "Trades"])
            ):
                if subtitle and subfolder == "Misc":
                    filepath = directory / subtitle / f"{filename}.pdf"
                    filepath_with_doc_id = directory / subtitle / f"{filename_with_doc_id}.pdf"
                else:
                    filepath = directory / f"{filename}.pdf"
                    filepath_with_doc_id = directory / f"{filename_with_doc_id}.pdf"
            else:
                subdir = subdir_override if subdir_override is not None else doc_type
                filepath = directory / subdir / f"{filename}.pdf"
                filepath_with_doc_id = directory / subdir / f"{filename_with_doc_id}.pdf"

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

        if self.dry_run:
            if not filepath.exists():
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.touch()
                self.log.debug(f"[dry-run] Created placeholder {filepath}")
            else:
                self.log.debug(f"[dry-run] Already exists {filepath}")
            return

        if filepath.is_file() is False:
            doc_url_base = doc_url.split("?")[0]
            if doc_url_base in self.doc_urls:
                self.log.debug(f"URL {doc_url_base} already in queue. Skipping...")
                return
            else:
                self.doc_urls.append(doc_url_base)

            future = self.session.get(doc_url)  # type: ignore[union-attr]
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
            if self.done % 500 == 0:
                self.log.info(f"Downloading: {self.done}/{len(self.doc_urls)}")
            self.log.debug(f"{self.done:>3}/{len(self.doc_urls)} {future.filepath.name}")  # type: ignore[attr-defined]

            if self.done == len(self.doc_urls):
                self.log.info("Done.")
                return
