import pytest

from pytr.sanitize import sanitize


@pytest.mark.parametrize(
    "input_data, expected_fields",
    [
        ({"phone": "+1234567890", "pin": "1234"}, ["phone", "pin"]),
        ({"account": {"iban": "DE44500105175407324931"}}, ["account.iban"]),
        ({"security": {"isin": "US0378331005"}}, ["security.isin"]),
        ({"price": {"amount": 100.0, "currency": "USD"}}, ["price.amount", "price.currency"]),
    ],
)
def test_sanitize_basic(input_data, expected_fields):
    redacted = sanitize(input_data)
    # all sensitive fields replaced with <REDACTED>
    for field in expected_fields:
        keys = field.split('.')
        d = redacted
        for k in keys[:-1]:
            d = d[k]
        assert d[keys[-1]] == '<REDACTED>'


def test_sanitize_with_audit():
    data = {"pin": "0000"}
    result = sanitize(data, audit=True)
    assert "data" in result and "audit" in result and "summary" in result
    assert result["data"]["pin"] == '<REDACTED>'
    assert len(result["audit"]) == 1
    assert result["summary"].fields_redacted == ['pin']
