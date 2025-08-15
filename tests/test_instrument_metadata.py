import pytest
import json
from pathlib import Path

import pytest

from pytr.fake import FakeTradeRepublic
from pytr.models import InstrumentMetadata


@pytest.mark.asyncio
async def test_fake_instrument_details(tmp_path):
    sample_dir = Path(__file__).parent
    fake = FakeTradeRepublic(sample_dir)

    md = await fake.instrument_details("US0378331005")
    assert isinstance(md, InstrumentMetadata)
    assert md.ticker == "AAPL"
    assert md.name == "Apple Inc"
    assert md.sector == "Technology"
    assert md.country == "US"
    assert md.updated_at.isoformat() == "2024-01-01T12:00:00"

    md2 = await fake.instrument_details("US0231351067")
    assert md2.ticker == "AMZN"

    with pytest.raises(KeyError):
        await fake.instrument_details("UNKNOWN")
