# pytr/utils/decorators.py

from functools import wraps
from typing import Any, Callable, Coroutine, Dict, Iterable, Type, TypeVar, Union

T = TypeVar("T")
Model = TypeVar("Model")

def safe_output(model_cls: Type[Model]):
    """
    Decorator for async client methods returning a single data‐dict or list of dicts.
    Converts dict → model_cls(**dict) via _safe_model.
    """
    def decorator(fn: Callable[..., Coroutine[Any, Any, Union[Dict, Iterable[Dict]]]]):
        @wraps(fn)
        async def wrapped(self, *args, **kwargs):
            raw = await fn(self, *args, **kwargs)
            safe = self._safe_model
            if isinstance(raw, dict):
                return safe(model_cls, raw)
            elif isinstance(raw, Iterable):
                return [safe(model_cls, item) for item in raw]
            else:
                # pass through non‑dict returns unchanged
                return raw
        return wrapped
    return decorator
