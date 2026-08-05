import pytest

import pytr.utils as pytr_utils


@pytest.fixture(autouse=True)
def suppress_info_logs(monkeypatch):
    # pytr loggers call coloredlogs.install(level=log_level, ...) with propagate=False,
    # bypassing pytest's capture. Setting log_level to "warning" before tests run
    # makes all subsequently created loggers install at WARNING level.
    monkeypatch.setattr(pytr_utils, "log_level", "warning")
    # Also raise the level on handlers already installed on existing loggers.
    import logging

    for lg in logging.root.manager.loggerDict.values():
        if isinstance(lg, logging.Logger):
            for handler in lg.handlers:
                handler.setLevel(logging.WARNING)
    yield
