import gettext
import os

from .utils import get_logger

log = get_logger(__name__)


def setup_translation(language="en"):
    """Set up translations for the specified language."""
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
