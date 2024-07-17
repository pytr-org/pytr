from locale import getdefaultlocale
import json

from .event import Event
from .utils import get_logger
from .translation import setup_translation


def export_transactions(input_path, output_path, lang="auto"):
    """
    Create a CSV with the deposits and removals ready for importing into Portfolio Performance
    The CSV headers for PP are language dependend

    i18n source from Portfolio Performance:
    https://github.com/buchen/portfolio/blob/93b73cf69a00b1b7feb136110a51504bede737aa/name.abuchen.portfolio/src/name/abuchen/portfolio/messages_de.properties
    https://github.com/buchen/portfolio/blob/effa5b7baf9a918e1b5fe83942ddc480e0fd48b9/name.abuchen.portfolio/src/name/abuchen/portfolio/model/labels_de.properties

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

            f.write(
                csv_fmt.format(
                    date=event.date,
                    type=_(event.pp_type),
                    value=event.amount,
                    note=(_(event.note) + " " + event.title),
                    isin=event.isin,
                    shares=event.shares,
                )
            )

    log.info("Deposit creation finished!")
