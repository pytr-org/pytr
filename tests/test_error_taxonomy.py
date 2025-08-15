import pytest

from pytr.models import (
    PytrError,
    AuthError,
    RateLimitError,
    TimeoutError,
    ApiShapeError,
    UnsupportedVersionError,
    OtpRequired,
    SessionExpired,
    NetworkError,
)


@pytest.mark.parametrize(
    "exc, base, retryable, backoff",
    [
        (AuthError, PytrError, False, None),
        (RateLimitError, PytrError, True, 30.0),
        (TimeoutError, PytrError, True, 1.0),
        (ApiShapeError, PytrError, False, None),
        (UnsupportedVersionError, PytrError, False, None),
        (OtpRequired, AuthError, False, None),
        (SessionExpired, AuthError, True, None),
        (NetworkError, PytrError, True, 1.0),
    ],
)
def test_error_classes(exc, base, retryable, backoff):
    err = exc()
    assert isinstance(err, base)
    assert err.retryable is retryable
    assert err.recommended_backoff == backoff
