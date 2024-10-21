import gettext
import os

from .utils import get_logger

log = get_logger(__name__)


def setup_translation(language="en"):
    """Set up translations for the specified language.

    i18n source from Portfolio Performance:
    https://github.com/buchen/portfolio/blob/93b73cf69a00b1b7feb136110a51504bede737aa/name.abuchen.portfolio/src/name/abuchen/portfolio/messages_de.properties
    https://github.com/buchen/portfolio/blob/effa5b7baf9a918e1b5fe83942ddc480e0fd48b9/name.abuchen.portfolio/src/name/abuchen/portfolio/model/labels_de.properties

    """
    # Get the absolute path of the locale directory
    locale_dir = os.path.join(
        os.path.dirname(__file__), ".", "locale"
    )  # Works only with pip install -e .
    # Set the locale directory and the language
    lang = gettext.translation(
        "messages", localedir=locale_dir, languages=[language], fallback=True
    )
    lang.install()
    return lambda x: lang.gettext(x) if len(x) > 0 else ""
