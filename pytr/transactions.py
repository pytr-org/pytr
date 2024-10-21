import json
from locale import getdefaultlocale

from .event import Event
from .event_formatter import EventCsvFormatter
from .utils import get_logger


def export_transactions(input_path, output_path, lang="auto", sort=False):
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

    formatter = EventCsvFormatter(lang=lang)

    events = map(lambda x: Event.from_dict(x), timeline)
    if sort:
        events = sorted(events, key=lambda x: x.date)
    lines = map(lambda x: formatter.format(x), events)
    lines = formatter.format_header() + "".join(lines)

    # Write transactions into csv file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(lines)

    log.info("Deposit creation finished!")
