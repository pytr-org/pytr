"""
Sort and organize PDF files based on metadata from Trade Republic events.

This module processes PDF files in a specified directory by:
- Matching filenames with events in all_events.json
- Extracting metadata (postboxType, title, subtitle, timestamp)
- Organizing files into categorized subdirectories
- Renaming files with timestamps and descriptive names
It requires PDF files and all_events.json being downloaded with pytr dl_raw!
"""

import json
from datetime import datetime
from enum import Enum, auto
from pathlib import Path

from pathvalidate import sanitize_filename

from pytr.utils import get_logger

logger = get_logger(__name__)


class _FilenamePattern(Enum):
    """Patterns for generating PDF filenames."""

    EVENTTITLE = auto()
    EVENTSUBTITLE = auto()
    DOCTITLE = auto()
    EVENTTITLE_EVENTSUBTITLE = auto()
    DOCTITLE_EVENTTITLE = auto()


_known_postbox_types = [
    "BASE_INFO",
    "CA_INCOME_INVOICE",
    "CA_VOPA_INVOICE",
    "CASH_ACCOUNT_STATEMENT_V2",
    "CONFIRM_ORDER_DELETE_V2",
    "COSTS_INFO_BUY_V2",
    "CRYPTO_DEPOSIT_STATEMENT_V2",
    "DOCUMENTS_ACCEPTED",
    "DOCUMENTS_CREATED",
    "EX_POST_COST_REPORT",
    "EX_POST_COST_REPORT_V2",
    "GENERAL_CORPACTION_V2",
    "GENERAL_MEETING",
    "INCOME",
    "INCOMING_TRANSFER",
    "INFO",
    "INFORMATIVE_CA",
    "INTEREST_PAYOUT_INVOICE",
    "OUTGOING_TRANSFER",
    "PAYMENT_INBOUND_INVOICE",
    "PRE_DETERMINED_TAX_BASE_EARNING_V2",
    "SAVINGS_PLAN_EXECUTED_V2",
    "SECURITIES_ACCOUNT_STATEMENT_V2",
    "SECURITIES_SETTLEMENT",
    "SECURITIES_SETTLEMENT_SAVINGS_PLAN",
    "SEPA_DIRECT_DEBIT_MANDATE_CREATED",
    "SHAREBOOKING",
    "YEAR_END_TAX_REPORT",
    "yearlyTaxReport",
]


def _find_event_by_filename(events, filename):
    """
    Search corresponding event for the filename.
    Returns (event, document_item) tuple or (None, None) if not found.
    """
    for event in events:
        # Only check events that have documents
        if not event.get("has_docs", False):
            continue

        # Check sections for documents
        sections = event.get("details", {}).get("sections", [])
        for section in sections:
            if section.get("type") != "documents":
                continue

            # Check each document in the data list
            data = section.get("data", [])
            if not isinstance(data, list):
                continue

            for item in data:
                payload = item.get("action", {}).get("payload", "")
                if filename in str(payload):
                    return event, item

    return None, None


def _move_to_subfolder(pdf_file: Path, new_filename: str, subfolder: str):
    """
    Move and rename a PDF file to a subfolder.

    Args:
        pdf_file: The original PDF file path
        new_filename: The new filename for the PDF
        subfolder: The subfolder name to move the file to
    """

    safe_filename = sanitize_filename(new_filename, replacement_text="_")

    new_filepath = pdf_file.parent / subfolder / safe_filename
    new_filepath.parent.mkdir(parents=True, exist_ok=True)
    pdf_file.rename(new_filepath)
    logger.debug("Moved '%s' to subfolder '%s'", new_filename, subfolder)


def post_sort(target_directory: Path):
    """
    Process PDF files from the specified directory:
    - Requires PDF files and all_events.json being downloaded with pytr dl_raw!
    - Search corresponding event for the filename in all_events.json
    - Retrieve meta data from that event
    - Rename and sort files accordingly
    """
    events_file = Path(target_directory, "all_events.json")

    # Check if directory exists
    if not target_directory.exists():
        logger.error("Directory '%s' does not exist", target_directory)
        return

    # Check if events file exists
    if not events_file.exists():
        logger.error("File '%s' does not exist", events_file)
        return

    # Load all events
    logger.info("Loading events from '%s'...", events_file)
    with open(events_file, "r", encoding="utf-8") as f:
        events = json.load(f)

    logger.info("Loaded %d events", len(events))

    # Process all PDF files
    pdf_files = list(target_directory.glob("*.pdf"))
    logger.info("Found %d PDF files in '%s'", len(pdf_files), target_directory)

    if not pdf_files:
        logger.warning("No PDF files found")
        return

    matched_count = 0
    not_found_count = 0
    sorted_count = 0
    not_sorted_count = 0

    for pdf_file in pdf_files:
        filename = pdf_file.name

        # Find the event and document item
        event, document_item = _find_event_by_filename(events, filename)

        if event and document_item:
            matched_count += 1

            # Extract metadata
            postbox_type = document_item.get("postboxType")
            if not postbox_type:
                logger.error("No postboxType found for '%s'", filename)
                continue

            if postbox_type not in _known_postbox_types:
                logger.warning("Unknown postboxType '%s' for '%s'", postbox_type, filename)

            subfolder = None
            document_title = document_item.get("title", "")
            event_timestamp = event.get("timestamp", "")
            time_str = datetime.fromisoformat(event_timestamp).strftime("%Y%m%d %H%M%S")
            event_title = event.get("title", "")
            event_subtitle = event.get("subtitle", "")

            logger.debug(
                "%s;%s;%s;%s;%s",
                filename,
                postbox_type,
                document_title,
                event_subtitle,
                event_title,
            )

            # Routing rules: Check postbox_type and optionally other conditions
            # to determine subfolder and filename pattern
            result = None

            # Simple mappings: postbox_type -> (subfolder, filename_pattern)
            simple_rules = {
                ("CA_INCOME_INVOICE", "INCOME"): (
                    "Dividenden",
                    _FilenamePattern.EVENTTITLE,
                ),
                ("INTEREST_PAYOUT_INVOICE",): ("Zinsen", _FilenamePattern.EVENTTITLE),
                ("GENERAL_MEETING",): (
                    "Hauptversammlungen",
                    _FilenamePattern.EVENTTITLE,
                ),
                ("SECURITIES_SETTLEMENT",): (
                    "Wertpapierabrechnungen",
                    _FilenamePattern.DOCTITLE,
                ),
                ("COSTS_INFO_BUY_V2",): (
                    "Kosteninformationen",
                    _FilenamePattern.DOCTITLE,
                ),
                ("BASE_INFO", "INFO"): ("Basisinformationen", _FilenamePattern.DOCTITLE),
                ("SAVINGS_PLAN_EXECUTED_V2", "SECURITIES_SETTLEMENT_SAVINGS_PLAN"): (
                    "Sparplanausführungen",
                    _FilenamePattern.EVENTTITLE,
                ),
                ("EX_POST_COST_REPORT_V2", "EX_POST_COST_REPORT"): (
                    "Ex-Post Kosteninformationen",
                    _FilenamePattern.DOCTITLE,
                ),
                ("yearlyTaxReport", "YEAR_END_TAX_REPORT"): (
                    "Jährlicher Steuerreport",
                    _FilenamePattern.DOCTITLE,
                ),
                ("CA_VOPA_INVOICE", "PRE_DETERMINED_TAX_BASE_EARNING_V2"): (
                    "Vorabpauschale",
                    _FilenamePattern.EVENTTITLE,
                ),
                ("DOCUMENTS_CREATED", "DOCUMENTS_ACCEPTED"): (
                    "Rechtliche Dokumente",
                    _FilenamePattern.DOCTITLE,
                ),
                ("OUTGOING_TRANSFER",): (
                    "Ausgehende Überweisungen",
                    _FilenamePattern.DOCTITLE,
                ),
                ("CONFIRM_ORDER_DELETE_V2",): (
                    "Löschbestätigungen",
                    _FilenamePattern.EVENTTITLE_EVENTSUBTITLE,
                ),
                ("INCOMING_TRANSFER",): (
                    "Eingehende Überweisungen",
                    _FilenamePattern.DOCTITLE,
                ),
                ("SECURITIES_ACCOUNT_STATEMENT_V2",): (
                    "Depotauszüge",
                    _FilenamePattern.EVENTTITLE,
                ),
                ("PAYMENT_INBOUND_INVOICE",): (
                    "Einzahlungen",
                    _FilenamePattern.DOCTITLE,
                ),
                ("SEPA_DIRECT_DEBIT_MANDATE_CREATED",): (
                    "SEPA-Mandate",
                    _FilenamePattern.DOCTITLE,
                ),
                ("CRYPTO_DEPOSIT_STATEMENT_V2",): (
                    "Cryptoauszüge",
                    _FilenamePattern.EVENTTITLE,
                ),
                ("CASH_ACCOUNT_STATEMENT_V2",): (
                    "Kontoauszüge",
                    _FilenamePattern.EVENTTITLE,
                ),
            }

            # Check simple rules
            for types, (subfolder, pattern) in simple_rules.items():
                if postbox_type in types:
                    result = (subfolder, pattern)
                    break

            # Complex rules requiring additional conditions
            if postbox_type == "SHAREBOOKING":
                if document_title == "Abrechnung":
                    result = (
                        "Depotübertrag eingehend",
                        _FilenamePattern.EVENTTITLE_EVENTSUBTITLE,
                    )
                elif document_title == "Ausführungsanzeige" and event_subtitle == "Steuerlicher Umtausch":
                    result = ("Steuerlicher Umtausch", _FilenamePattern.EVENTTITLE)

            elif postbox_type == "GENERAL_CORPACTION_V2":
                if event_subtitle == "Unternehmensmeldung":
                    result = (
                        "Unternehmensmeldungen",
                        _FilenamePattern.DOCTITLE_EVENTTITLE,
                    )
                elif event_subtitle == "Gesellschaftshinweis":
                    result = (
                        "Gesellschaftshinweise",
                        _FilenamePattern.DOCTITLE_EVENTTITLE,
                    )

            elif postbox_type == "INFORMATIVE_CA":
                if event_subtitle == "Jährliche Hauptversammlung":
                    result = ("Hauptversammlungen", _FilenamePattern.EVENTTITLE)
                elif event_subtitle == "Information":
                    result = ("Informationen", _FilenamePattern.EVENTTITLE)
                elif event_subtitle == "Wechsel":
                    result = ("Wechsel", _FilenamePattern.EVENTTITLE)

            # Apply the result if a rule matched
            if result:
                subfolder, pattern = result

                # Build filename based on pattern
                if pattern == _FilenamePattern.EVENTTITLE:
                    new_filename = f"{time_str} - {event_title}.pdf"
                elif pattern == _FilenamePattern.DOCTITLE:
                    new_filename = f"{time_str} - {document_title}.pdf"
                elif pattern == _FilenamePattern.EVENTTITLE_EVENTSUBTITLE:
                    new_filename = f"{time_str} - {event_title} - {event_subtitle}.pdf"
                elif pattern == _FilenamePattern.DOCTITLE_EVENTTITLE:
                    new_filename = f"{time_str} - {document_title} - {event_title}.pdf"
                else:
                    logger.error("Unknown filename pattern '%s'", pattern)
                    not_sorted_count += 1
                    continue

                _move_to_subfolder(pdf_file, new_filename, subfolder)
                sorted_count += 1
                continue

            not_sorted_count += 1

        else:
            not_found_count += 1
            logger.error("No event found for %s", pdf_file.name)

    logger.info("Files without matching event: %d", not_found_count)
    logger.info("Files with matching event: %d", matched_count)
    logger.info("Sorted files: %d", sorted_count)
    logger.info("Not sorted files: %d", not_sorted_count)
