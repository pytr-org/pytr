"""
Core data models for package-first pytr API.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class Position(BaseModel):
    isin: str
    ticker: Optional[str] = None
    name: Optional[str] = None
    quantity: float
    average_buy_in: Optional[float] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    currency: Optional[str] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    updated_at: Optional[datetime] = None


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    DIVIDEND = "DIVIDEND"


class TransactionStatus(str, Enum):
    EXECUTED = "EXECUTED"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"


class Transaction(BaseModel):
    id: str
    isin: Optional[str] = None
    type: TransactionType
    status: Optional[TransactionStatus] = None
    amount: float
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    currency: Optional[str] = None
    timestamp: datetime


class CashBalance(BaseModel):
    value: float
    currency: str
    updated_at: Optional[datetime] = None


class Quote(BaseModel):
    isin: str
    price: float
    currency: str
    ts: datetime


class Paginated(BaseModel, Generic[T]):
    items: List[T] = Field(..., description="Page of results")
    cursor: Optional[str] = Field(None, description="Cursor for next page, or None if last page")


# Error base for client
class PytrError(Exception):
    """
    Base exception for pytr client errors.

    :ivar retryable: Whether the operation may be retried.
    :ivar recommended_backoff: Suggested backoff interval in seconds if retryable.
    """
    retryable: bool = False
    recommended_backoff: Optional[float] = None


class AuthError(PytrError):
    "Authentication or session-related errors." 
    retryable = False


class RateLimitError(PytrError):
    "Raised when API rate limit is exceeded." 
    retryable = True
    recommended_backoff = 30.0


class TimeoutError(PytrError):
    "Raised when an API request or receive operation times out." 
    retryable = True
    recommended_backoff = 1.0


class ApiShapeError(PytrError):
    "Raised when API response shape does not match expected model." 
    retryable = False


class UnsupportedVersionError(PytrError):
    "Raised when the client library version is incompatible with server API." 
    retryable = False


class OtpRequired(AuthError):
    "Raised when an OTP is required to continue authentication."  
    retryable = False


class SessionExpired(AuthError):
    "Raised when the session has expired and needs re-authentication."  
    retryable = True


class NetworkError(PytrError):
    "Raised when a network error occurs (e.g. DNS failure, connection timeout)."
    retryable = True
    recommended_backoff = 1.0
