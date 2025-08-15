import asyncio
import random

import pytest

from pytr.backoff import backoff_intervals, retry_async


def test_backoff_intervals_no_jitter():
    seq = []
    # extract 4 intervals without jitter
    async def collect():
        async for d in backoff_intervals(initial=1.0, max_delay=10.0, factor=2.0, max_attempts=4, jitter=False):
            seq.append(d)
    asyncio.run(collect())
    assert seq == [1.0, 2.0, 4.0, 8.0]


def test_backoff_intervals_with_jitter(monkeypatch):
    # fix random.uniform to constant 1.0
    monkeypatch.setattr(random, 'uniform', lambda a, b: 1.0)
    seq = []
    async def collect():
        async for d in backoff_intervals(initial=1.0, max_delay=5.0, factor=3.0, max_attempts=3, jitter=True):
            seq.append(d)
    asyncio.run(collect())
    # delays: 1*1=1, 3*1=3, 5 (capped)
    assert pytest.approx(seq) == [1.0, 3.0, 5.0]


@pytest.mark.asyncio
async def test_retry_async_success_first_try(monkeypatch):
    async def dummy(x):
        return x * 2
    res = await retry_async(dummy, 5, max_attempts=3, initial_delay=0.1, jitter=False)
    assert res == 10


@pytest.mark.asyncio
async def test_retry_async_retries_and_succeeds(monkeypatch):
    calls = []
    async def flaky(x):
        calls.append(x)
        if len(calls) < 3:
            raise ValueError("fail")
        return x

    # monkeypatch sleep to avoid delay
    async def _dummy_sleep(_):
        return None
    monkeypatch.setattr(asyncio, 'sleep', _dummy_sleep)
    res = await retry_async(flaky, 7, max_attempts=5, initial_delay=0.01, jitter=False)
    assert res == 7
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_retry_async_all_fail(monkeypatch):
    async def always_fail():
        raise RuntimeError("oops")

    async def _dummy_sleep(_):
        return None
    monkeypatch.setattr(asyncio, 'sleep', _dummy_sleep)
    with pytest.raises(RuntimeError):
        await retry_async(always_fail, max_attempts=2, initial_delay=0.01, jitter=False)
