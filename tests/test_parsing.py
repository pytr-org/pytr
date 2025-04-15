"""Testing the string parsing."""

from typing import Any, Dict

from pytr.event import Event


def test_event_float_from_detail():
    """Test parsing of values from strings found in real world examples."""

    def test(data: Dict[str, Any], number: float):
        assert number == Event._parse_float_from_detail(data)

    test(
        {
            "title": "Anteile",
            "detail": {
                "text": "9.400",
                "trend": None,
                "action": None,
                "type": "text",
            },
            "style": "plain",
        },
        9400.0,
    )

    test(
        {
            "title": "Anteile",
            "detail": {"text": "1,875", "trend": None, "action": None, "type": "text"},
            "style": "plain",
        },
        1.875,
    )

    test(
        {
            "title": "Aktien",
            "detail": {
                "text": "14.000000",
                "trend": None,
                "action": None,
                "type": "text",
            },
            "style": "plain",
        },
        14.0,
    )

    test(
        {
            "title": "Anteile",
            "detail": {"text": "50", "trend": None, "action": None, "type": "text"},
            "style": "plain",
        },
        50.0,
    )

    test(
        {
            "title": "Anteile",
            "detail": {
                "text": "5,928385",
                "trend": None,
                "action": None,
                "type": "text",
            },
            "style": "plain",
        },
        5.928385,
    )

    test(
        {
            "title": "Steuern",
            "style": "plain",
            "detail": {"text": "€11.14", "type": "text"},
        },
        11.14,
    )

    test(
        {
            "title": "Steuern",
            "detail": {
                "text": "17,77 €",
                "trend": None,
                "action": None,
                "type": "text",
            },
            "style": "plain",
        },
        17.77,
    )
