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
    InstrumentMetadata,
)
from .utils.decorators import safe_output
from .errors import ApiShapeError, redact_sensitive_data
from pydantic import ValidationError

T = TypeVar("T")


class _StreamFacade:
    """
    Facade for async streaming subscriptions.
    Provides async iterators over websocket topics with auto-unsubscribe.
    """
    def __init__(self, api: TradeRepublicApi):
        self._api = api

    async def timeline(self, after: Optional[str] = None) -> AsyncIterator[Any]:
        sub_id = await self._api.timeline_transactions(after)
        try:
            while True:
                _, _, resp = await self._api.recv()
                yield resp
        finally:
            await self._api.unsubscribe(sub_id)

    async def ticker(self, isin: str, exchange: str = "LSX") -> AsyncIterator[Any]:
        sub_id = await self._api.ticker(isin, exchange)
        try:
            while True:
                _, _, resp = await self._api.recv()
                yield resp
        finally:
            await self._api.unsubscribe(sub_id)

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
        *,
        timeout: float = 10.0,
        debug: bool = False,
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
        self.timeout = timeout
        self.debug = debug
        self._api = TradeRepublicApi(
            phone_no=phone,
            pin=pin,
            keyfile=keyfile,
            locale=locale,
            save_cookies=save_session,
            credentials_file=credentials_file,
            cookies_file=cookies_file,
            timeout=timeout,
            debug=debug,
        )

    def _safe_model(self, model_cls, data):
        try:
            return model_cls(**data)
        except ValidationError as e:
            redacted_data = redact_sensitive_data(data)
            raise ApiShapeError(
                f"Failed to instantiate {model_cls.__name__} from API data",
                data=redacted_data
            )

    # High-level data-first methods for convenience (non-streaming APIs)
    @safe_output(Position)
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
        # reuse Portfolio helper for fetching positions
        from .portfolio import Portfolio as _PortfolioHelper
        # retrieve cash for currency context
        cb = await self.cash()
        helper = _PortfolioHelper(self._api)
        await helper.portfolio_loop()
        result: List[Dict] = []
        for pos in helper.portfolio:
            result.append(
                {
                    "isin": pos["instrumentId"],
                    "name": pos.get("name"),
                    "quantity": float(pos.get("netSize", 0)),
                    "average_buy_in": float(pos.get("averageBuyIn", 0)),
                    "current_price": float(pos.get("price", 0)),
                    "market_value": float(pos.get("netValue", 0)),
                    "currency": cb.currency,
                    "updated_at": None,
                }
            )
        return result

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
        # collect timeline transactions and convert to models
        from .timeline import Timeline
        from .transactions import TransactionExporter
        from .event import Event

        tl = Timeline(self._api, since_timestamp=None)
        await tl.get_next_timeline_transactions(None, self)
        events = [Event.from_dict(ev) for ev in tl.timeline_events.values()]
        exporter = TransactionExporter()
        txns = exporter.to_list(events, sort=True)
        items = [self._safe_model(Transaction, txn) for txn in txns[:limit]]
        return Paginated(items=items, cursor=None)

    @safe_output(CashBalance)
    async def cash(self) -> CashBalance:
        """
        Fetch account cash balance.

        :returns: CashBalance object.
        """
        # subscribe to cash topic
        sub_id = await self._api.cash()
        _, _, resp = await self._api.recv()
        await self._api.unsubscribe(sub_id)
        entry = resp[0]
        return {
            "value": float(entry.get("amount", 0)),
            "currency": entry.get("currencyId", ""),
            "updated_at": None,
        }

    async def quotes(self, isins: List[str]) -> Dict[str, Quote]:
        """
        Retrieve current market quotes for given instrument ISINs.

        :param isins: List of ISIN strings.
        :returns: Mapping from ISIN to Quote models.
        """
        result: Dict[str, Quote] = {}
        for isin in isins:
            sub_id = await self._api.ticker(isin)
            _, _, resp = await self._api.recv()
            await self._api.unsubscribe(sub_id)
            payload = {
                "isin": isin,
                "price": float(resp.get("last", {}).get("price", 0)),
                "currency": resp.get("last", {}).get("currencyId", ""),
                "ts": resp.get("last", {}).get("timestamp"),
            }
            result[isin] = self._safe_model(Quote, payload)
        return result

    async def portfolio_summary(
        self,
        portfolio_id: Optional[str] = None,
    ) -> Position:
        """
        Fetch a summarized overview of the portfolio (positions + cash + total).

        :param portfolio_id: Optional specific portfolio identifier.
        :returns: Position object representing aggregated summary.
        """
        positions = await self.positions(portfolio_id)
        cash = await self.cash()
        total = sum(p.market_value or 0 for p in positions) + cash.value
        return Position(
            isin="",
            name="Summary",
            quantity=0,
            average_buy_in=None,
            current_price=None,
            market_value=total,
            currency=cash.currency,
            updated_at=None,
        )

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
        """
        Serialize current session state (tokens and cookies) to opaque bytes.
        """
        """
        Serialize current session state to opaque bytes using datason (fallback to pickle).
        """
        try:
            import datason
        except ImportError as e:
            raise ImportError("datason is required for session serialization") from e
        dumps = datason.dumps
        try:
            from requests.utils import dict_from_cookiejar
        except ImportError:
            dict_from_cookiejar = None
        state: dict = {
            "refresh_token": getattr(self._api, '_refresh_token', None),
            "session_token": getattr(self._api, '_session_token', None),
            "session_token_expires_at": getattr(self._api, '_session_token_expires_at', None),
        }
        if dict_from_cookiejar:
            state["cookies"] = dict_from_cookiejar(
                getattr(self._api._websession, 'cookies', None)
            )
        return dumps(state)

    async def resume_session(self, data: bytes) -> None:
        """
        Resume a previously serialized session.

        :param data: Opaque session bytes from serialize_session().
        """
        """
        Resume a previously serialized session state.
        """
        """
        Resume a previously serialized session state using datason (fallback to pickle).
        """
        try:
            import datason
        except ImportError as e:
            raise ImportError("datason is required for session deserialization") from e
        loads = datason.loads
        try:
            from requests.utils import cookiejar_from_dict
        except ImportError:
            cookiejar_from_dict = None
        # If already a dict (from datason.dumps), use directly; else deserialize
        state = data if isinstance(data, dict) else loads(data)
        # restore tokens
        for key in ('_refresh_token', '_session_token', '_session_token_expires_at'):
            if key[1:] in state:
                setattr(self._api, key, state.get(key[1:]))
        # restore cookies
        if cookiejar_from_dict and state.get('cookies') is not None:
            self._api._websession.cookies = cookiejar_from_dict(state['cookies'])

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

    @safe_output(InstrumentMetadata)
    async def instrument_details(self, isin: str) -> InstrumentMetadata:
        """
        Fetch rich metadata for a given instrument ISIN.

        :param isin: Instrument ISIN code.
        :returns: InstrumentMetadata object.
        """
        sub_id = await self._api.instrument_details(isin)
        _, _, resp = await self._api.recv()
        await self._api.unsubscribe(sub_id)
        return resp
