import asyncio
from pathlib import Path

import pytest

from pytr.fake import FakeTradeRepublic
from pytr.models import Position, Transaction, CashBalance, Quote


@pytest.mark.asyncio
async def test_fake_positions():
    fake = FakeTradeRepublic(sample_dir=Path(__file__).parent)
    positions = await fake.positions()
    assert isinstance(positions, list)
    assert positions, "Expected at least one position"
    assert isinstance(positions[0], Position)


@pytest.mark.asyncio
async def test_fake_transactions():
    fake = FakeTradeRepublic(sample_dir=Path(__file__).parent)
    paginated = await fake.transactions(limit=1)
    assert hasattr(paginated, 'items')
    items = paginated.items
    assert len(items) == 1
    assert isinstance(items[0], Transaction)


@pytest.mark.asyncio
async def test_fake_cash():
    fake = FakeTradeRepublic(sample_dir=Path(__file__).parent)
    cash = await fake.cash()
    assert isinstance(cash, CashBalance)
    assert cash.value >= 0


@pytest.mark.asyncio
async def test_fake_quotes():
    fake = FakeTradeRepublic(sample_dir=Path(__file__).parent)
    positions = await fake.positions()
    isins = [p.isin for p in positions]
    quotes = await fake.quotes(isins)
    assert isinstance(quotes, dict)
    for isin, quote in quotes.items():
        assert isinstance(quote, Quote)

