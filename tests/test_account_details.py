import json

from pytr.accountdetails import AccountDetails


def test_account_details_from_dict():
    # Load the sample JSON file
    with open("tests/sample_account_details.json", "r") as file:
        sample_data = json.load(file)

    # Parse the JSON data using the from_dict function
    ad = AccountDetails.from_dict(sample_data)

    # Assert the expected values
    assert ad["phoneNumber"] == "+491xxxx"
    assert ad["name"]["first"] == "xxfirstnamexx"
    assert ad["taxExemptionOrder"]["current"] == 111
