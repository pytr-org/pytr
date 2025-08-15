"""
In-memory fake TradeRepublic client for testing without network or credentials.
"""
import json
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from .models import (
    Paginated,
    Position,
    Transaction,
    CashBalance,
    Quote,
    InstrumentMetadata,
)


class FakeTradeRepublic:
    """
    Fake client mimicking TradeRepublic interface using sample JSON fixtures.

    Example usage:
        fake = FakeTradeRepublic(sample_dir=Path("tests"))
        positions = await fake.positions()
        txs = await fake.transactions(limit=10)
    """

    def __init__(self, sample_dir: Path):
        self.sample_dir = sample_dir

    async def positions(self, portfolio_id: Optional[str] = None, fresh: bool = False) -> List[Position]:
        data = json.loads((self.sample_dir / "sample_portfolio.json").read_text())
        return [Position(**item) for item in data]

    async def transactions(
        self, after: Optional[str] = None, limit: int = 100
    ) -> Paginated[Transaction]:
        data = json.loads((self.sample_dir / "sample_transactions.json").read_text())
        items = [Transaction(**item) for item in data]
        return Paginated(items=items[:limit], cursor=None)

    async def cash(self) -> CashBalance:
        data = json.loads((self.sample_dir / "sample_cash.json").read_text())
        return CashBalance(**data)

    async def quotes(self, isins: List[str]) -> Dict[str, Quote]:
        data = json.loads((self.sample_dir / "sample_quotes.json").read_text())
        return {item["isin"]: Quote(**item) for item in data if item["isin"] in isins}

    async def instrument_details(self, isin: str) -> InstrumentMetadata:
        data = json.loads((self.sample_dir / "sample_metadata.json").read_text())
        for item in data:
            if item.get("isin") == isin:
                return InstrumentMetadata(**item)
        raise KeyError(f"Metadata for ISIN {isin} not found")

    @property
    def stream(self) -> Any:
        """
        Fake streaming namespace (no-op).

        All async iterators immediately end.
        """
        class _EmptyStream:
            def __getattr__(self, name):
                async def _empty(*args, **kwargs):
                    return
                    yield  # make it an async generator
                return _empty

        return _EmptyStream()

    async def authenticate(self) -> Dict[str, Any]:
        return {"requires_otp": False, "otp_countdown": None}

    async def verify_otp(self, code: Optional[str] = None) -> None:
        pass

    def serialize_session(self) -> bytes:
        return b""

    async def resume_session(self, data: bytes) -> None:
        pass
