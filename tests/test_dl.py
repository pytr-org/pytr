"""Tests for pytr.dl.DL.dl_callback document download handling."""

from pytr.dl import DL


class FakeLogger:
    def __init__(self):
        self.warnings = []
        self.debugs = []

    def warning(self, msg):
        self.warnings.append(msg)

    def debug(self, msg):
        self.debugs.append(msg)


def make_event(payload):
    """Minimal timeline detail event with a single document, based on a real-world sample."""
    return {
        "id": "0598f7a7-cabe-454b-a520-3579999d49e8",
        "title": "Portfolioauszug Q2 2026",
        "subtitle": None,
        "timestamp": "2026-07-29T13:06:13+02:00",
        "details": {
            "sections": [
                {
                    "title": "Portfolioauszug Q2 2026",
                    "data": {
                        "icon": {"asset": "logos/timeline_document/v2", "badge": None},
                        "subtitleText": "29 Juli · 13:06",
                        "status": "executed",
                    },
                    "type": "header",
                },
                {
                    "title": "Dokumente",
                    "data": [
                        {
                            "title": "Portfolioauszug",
                            "action": {"payload": payload, "type": "deeplink"},
                            "id": "3069857f-7eb4-3c12-a821-ac5f01dbe882",
                            "postboxType": "",
                        }
                    ],
                    "type": "documents",
                },
            ]
        },
    }


def make_dl():
    dl = DL.__new__(DL)
    dl.log = FakeLogger()
    dl.events_with_docs = []
    dl.events_without_docs = []
    dl.filepaths = []
    dl.doc_urls = []
    dl.doc_urls_history = []
    return dl


def test_deeplink_payload_without_path_does_not_crash():
    """A dict payload without a 'path' key (e.g. an app deeplink) must not raise KeyError."""
    dl = make_dl()
    event = make_event({"link": "traderepublic://update-app-dialog"})

    dl.dl_callback(event)

    assert any("unsupported action payload" in w for w in dl.log.warnings)
    assert "traderepublic://update-app-dialog" in " ".join(dl.log.warnings)
    assert event in dl.events_without_docs
    assert dl.events_with_docs == []


def test_api_path_payload_logs_new_api_path_warning():
    """A dict payload containing a 'path' key keeps the existing 'new API-Path' warning."""
    dl = make_dl()
    event = make_event({"path": "/api/v1/portfolio-statements/12345"})

    dl.dl_callback(event)

    assert any("new API-Path URL" in w for w in dl.log.warnings)
    assert any("/api/v1/portfolio-statements/12345" in w for w in dl.log.warnings)
    assert event in dl.events_without_docs
    assert dl.events_with_docs == []


def test_string_payload_queues_document(tmp_path):
    """A plain string payload is a download URL and queues the document for download."""
    dl = make_dl()
    dl.flat = False
    dl.output_path = tmp_path
    dl.filename_fmt = "{iso_date} - {title} - {subtitle} - {doc_num} - {id}"
    dl.universal_filepath = False
    doc_url = "/api/v1/documents/12345?type=portfolio"
    dl.doc_urls_history = [doc_url.split("?")[0]]

    event = make_event(doc_url)
    dl.dl_callback(event)

    assert event in dl.events_with_docs
    assert dl.events_without_docs == []
    assert dl.filepaths == [event["details"]["sections"][1]["data"][0]["local_filepath"]]
    assert any("already in history" in d for d in dl.log.debugs)
