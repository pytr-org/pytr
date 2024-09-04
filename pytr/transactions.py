from locale import getdefaultlocale
from babel.numbers import format_decimal
import json

from .event import Event
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
    _ = setup_translation(language=lang)

    # Read relevant deposit timeline entries
    with open(input_path, encoding="utf-8") as f:
        timeline = json.load(f)

    log.info("Write deposit entries")
    with open(output_path, "w", encoding="utf-8") as f:
        csv_fmt = "{date};{type};{value};{note};{isin};{shares}\n"
        header = csv_fmt.format(
            date=_("CSVColumn_Date"),
            type=_("CSVColumn_Type"),
            value=_("CSVColumn_Value"),
            note=_("CSVColumn_Note"),
            isin=_("CSVColumn_ISIN"),
            shares=_("CSVColumn_Shares"),
        )
        f.write(header)

        for event_json in timeline:
            event = Event(event_json)
            if not event.is_pp_relevant:
                continue

            amount = format_decimal(event.amount, locale=lang) if event.amount else ""
            note = (_(event.note) + " - " + event.title) if event.note else event.title
            shares = format_decimal(event.shares, locale=lang) if event.shares else ""

            f.write(
                csv_fmt.format(
                    date=event.date,
                    type=_(event.pp_type),
                    value=amount,
                    note=note,
                    isin=event.isin,
                    shares=shares,
                )
            )

    log.info("Deposit creation finished!")
