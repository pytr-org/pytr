"""
pytr package-first async client entrypoint.
"""
from typing import Any, Dict, List, Optional

from .api import TradeRepublicApi
from .models import (
    Position,
    Transaction,
    CashBalance,
    Quote,
    Paginated,
)


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
        timeout: float = 10.0,
        debug: bool = False,
        save_session: bool = True,
    ) -> None:
        """
        Initialize the TradeRepublic client.

        :param phone: Phone number for authentication.
        :param pin: PIN code for authentication.
        :param timeout: Default timeout for API calls.
        :param debug: Enable debug logging.
        :param save_session: Persist web session cookies.
        """
        self._api = TradeRepublicApi(
            phone_no=phone,
            pin=pin,
            save_cookies=save_session,
        )
        # TODO: apply timeout, debug flags to underlying API

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

    # Streaming namespace placeholder
    @property
    def stream(self) -> Any:
        """
        Low-level streaming interface for subscriptions (advanced).

        E.g., client.stream.timeline(), client.stream.ticker(isin)
        """
        return self._api  # placeholder until streaming facade is built
