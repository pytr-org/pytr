"""
pytr package-first async client entrypoint.
"""
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, TypeVar, Generic

from .api import TradeRepublicApi
from .models import (
    Position,
    Transaction,
    CashBalance,
    Quote,
    Paginated,
)

T = TypeVar("T")


class TradeRepublic:
    """
    Async-first, data-centric client for Trade Republic API.

    This class provides high-level methods returning typed data models
    rather than raw subscription IDs. Streaming APIs remain available
    under the .stream namespace.
    """

    def __init__(
        self,
        phone: str,
        pin: str,
        keyfile: Optional[str] = None,
        locale: str = "de",
        save_session: bool = True,
        credentials_file: Optional[str] = None,
        cookies_file: Optional[str] = None,
    ) -> None:
        """
        Initialize the TradeRepublic client with authentication credentials.

        :param phone: Phone number in international format (e.g. +4912345678).
        :param pin: PIN for login.
        :param keyfile: Path to ECDSA keyfile for device reset.
        :param locale: Locale code for event formatting.
        :param save_session: Persist web session cookies to disk.
        :param credentials_file: Override credentials file path.
        :param cookies_file: Override cookies file path.
        """
        self._api = TradeRepublicApi(
            phone_no=phone,
            pin=pin,
            keyfile=keyfile,
            locale=locale,
            save_cookies=save_session,
            credentials_file=credentials_file,
            cookies_file=cookies_file,
        )

    # High-level data-first methods for convenience (non-streaming APIs)
    async def positions(
        self,
        portfolio_id: Optional[str] = None,
        fresh: bool = False,
    ) -> List[Position]:
        """
        Fetch current portfolio positions as Position models.

        :param portfolio_id: Optional specific portfolio identifier.
        :param fresh: If True, bypass any cached session data.
        :returns: List of Position objects.
        """
        raise NotImplementedError

    async def transactions(
        self,
        after: Optional[str] = None,
        limit: int = 100,
    ) -> Paginated[Transaction]:
        """
        Retrieve past transactions with pagination support.

        :param after: Pagination cursor for continuation.
        :param limit: Maximum number of records to return.
        :returns: Paginated[Transaction] result.
        """
        raise NotImplementedError

    async def cash(self) -> CashBalance:
        """
        Fetch account cash balance.

        :returns: CashBalance object.
        """
        raise NotImplementedError

    async def quotes(self, isins: List[str]) -> Dict[str, Quote]:
        """
        Retrieve current market quotes for given instrument ISINs.

        :param isins: List of ISIN strings.
        :returns: Mapping from ISIN to Quote models.
        """
        raise NotImplementedError

    async def portfolio_summary(
        self,
        portfolio_id: Optional[str] = None,
    ) -> Position:
        """
        Fetch a summarized overview of the portfolio (positions + cash + total).

        :param portfolio_id: Optional specific portfolio identifier.
        :returns: Position object representing aggregated summary.
        """
        raise NotImplementedError

    # Authentication and session management
    async def authenticate(self) -> Dict[str, Any]:
        """
        Perform a web-based authentication flow.

        Initiates login or resumes an existing session transparently.

        :returns: A dict with authentication status and any OTP requirements:
            {
              'requires_otp': bool,
              'otp_countdown': Optional[int]
            }
        """
        if self._api.resume_websession():
            return {'requires_otp': False, 'otp_countdown': None}
        countdown = self._api.inititate_weblogin()
        return {'requires_otp': True, 'otp_countdown': countdown}

    async def verify_otp(self, code: Optional[str] = None) -> None:
        """
        Complete the OTP verification for web login.

        :param code: 4-digit code from app or SMS. If None, will request SMS resend.
        """
        if code is None:
            # resend on countdown expiry
            await self._api.resend_weblogin()
            return
        await self._api.complete_weblogin(code)

    def serialize_session(self) -> bytes:
        """
        Serialize the current authentication session (cookies + tokens) to opaque bytes.

        :returns: Serialized session data.
        """
        # Placeholder: implement secure serialization
        return b""

    async def resume_session(self, data: bytes) -> None:
        """
        Resume a previously serialized session.

        :param data: Opaque session bytes from serialize_session().
        """
        # Placeholder: implement secure deserialization
        pass

    @property
    def stream(self) -> _StreamFacade:
        """
        Low-level streaming namespace for real-time subscriptions.

        Usage:
            async for update in client.stream.timeline(after=cursor):
                handle(update)

        :returns: A facade exposing async iterators for websocket topics.
        """
        return _StreamFacade(self._api)

    async def iterate(
        self,
        method: Callable[..., Paginated[T]],
        *args: Any,
        max_pages: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[T]:
        """
        Generic paginator to asynchronously iterate over all pages of a Paginated result.

        :param method: Async method returning Paginated[T].
        :param args: Positional args for the method.
        :param max_pages: Maximum number of pages to fetch (None for unlimited).
        :param kwargs: Keyword args for the method.
        :yields: Individual items of type T across pages.
        """
        cursor: Optional[str] = None
        pages = 0
        while True:
            page: Paginated[T] = await method(*args, after=cursor, **kwargs)  # type: ignore
            for item in page.items:
                yield item
            cursor = page.cursor
            pages += 1
            if not cursor or (max_pages is not None and pages >= max_pages):
                break
