import json
from locale import getdefaultlocale
from logging import Logger
from pathlib import Path
from typing import Any, List, Union

from .event import Event
from .event_formatter import EventCsvFormatter
from .utils import get_logger


def export_transactions(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    lang: str = "auto",
    sort: bool = False
) -> None:
    """
    Create a CSV with the deposits and removals ready for importing into Portfolio Performance
    The CSV headers for PP are language dependent

    Args:
        input_path: Path to input JSON file
        output_path: Path to output CSV file
        lang: Language code or "auto" for system language
        sort: Whether to sort events chronologically
    """
    log = get_logger(__name__)
    if lang == "auto":
        locale = getdefaultlocale()[0]
        if locale is None:
            lang = "en"
        else:
            lang = locale.split("_")[0]

    if lang not in [
        "cs",
        "da",
        "de",
        "en",
        "es",
        "fr",
        "it",
        "nl",
        "pl",
        "pt",
        "ru",
        "zh",
    ]:
        log.info(f"Language not yet supported {lang}")
        lang = "en"

    # Read relevant deposit timeline entries
    with open(input_path, encoding="utf-8") as f:
        timeline = json.load(f)

    log.info("Write deposit entries")

    formatter = EventCsvFormatter(lang=lang)

    events = [Event.from_dict(x) for x in timeline]
    if sort:
        events.sort(key=lambda x: x.date)

    lines = formatter.format_header() + "".join(
        formatter.format(event) for event in events
    )

    # Write transactions into csv file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(lines)

    log.info("Deposit creation finished!")
