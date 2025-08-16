# Backoff and retry utilities for retryable operations.
import asyncio
import random
from typing import AsyncIterator, Callable, Optional, TypeVar

T = TypeVar("T")

async def backoff_intervals(
    initial: float = 1.0,
    max_delay: float = 60.0,
    factor: float = 2.0,
    max_attempts: Optional[int] = None,
    jitter: bool = True,
) -> AsyncIterator[float]:
    """
    Asynchronously yield exponential backoff intervals, with optional jitter.

    :param initial: Initial delay in seconds.
    :param max_delay: Maximum delay in seconds.
    :param factor: Exponential factor between retries.
    :param max_attempts: Stop after this many intervals (None for unlimited).
    :param jitter: Apply jitter multiplier in [0.5, 1.5].
    """
    attempt = 0
    while True:
        delay = min(initial * (factor ** attempt), max_delay)
        if jitter:
            delay = delay * random.uniform(0.5, 1.5)
        yield delay
        attempt += 1
        if max_attempts is not None and attempt >= max_attempts:
            break

async def retry_async(
    func: Callable[..., T],
    *args,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    factor: float = 2.0,
    jitter: bool = True,
) -> T:
    """
    Retry an async function on exception with exponential backoff.

    :param func: Awaitable function to call.
    :param args: Positional arguments for func.
    :param max_attempts: Maximum number of attempts (including first call).
    :param initial_delay: Initial backoff delay.
    :param max_delay: Maximum backoff delay.
    :param factor: Exponential growth factor.
    :param jitter: Whether to apply jitter to delays.
    :raises Exception: The last exception if all attempts fail.
    """
    last_exc = None
    intervals = backoff_intervals(initial_delay, max_delay, factor, max_attempts - 1, jitter)
    async for delay in intervals:
        try:
            return await func(*args)
        except Exception as e:
            last_exc = e
            await asyncio.sleep(delay)
    # final attempt
    return await func(*args)
