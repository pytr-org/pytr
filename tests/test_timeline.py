import json

from pytr.timeline import get_customer_support_chat_action


def test__get_customer_support_chat_action() -> None:
    with open("tests/sample_event.json", "r") as file:
        sample_data = json.load(file)

    data = get_customer_support_chat_action(sample_data["details"])
    assert data is not None
    assert data == {
        "payload": {
            "contextParams": {
                "timelineEventId": "d8a5aa3d-12a4-465a-90ad-3fca36eff19a",
                "chat_flow_key": "NHC_0024_deposit_report_an_issue",
            },
            "contextCategory": "NHC",
        },
        "type": "customerSupportChat",
    }
