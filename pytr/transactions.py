from locale import getdefaultlocale
from babel.numbers import format_decimal
import json

from .event import Event
from .event_formatter import EventCsvFormatter
from .utils import get_logger
from .translation import setup_translation


def export_transactions(input_path, output_path, lang="auto"):
    """
    Create a CSV with the deposits and removals ready for importing into Portfolio Performance
    The CSV headers for PP are language dependend
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
    with open(output_path, "w", encoding="utf-8") as f:

        formatter = EventCsvFormatter(lang=lang)
        f.write(formatter.format_header())
        
        for event_json in timeline:

            event = Event.from_json(event_json)
            generator = formatter.format(event)
        
            for line in generator:
                f.write(line)

    log.info("Deposit creation finished!")
