"""pytr: programmatic Python interface to Trade Republic."""

# Package-level API for programmatic access
from .account import login
from .api import TradeRepublicApi
from .client import TradeRepublic
from .portfolio import Portfolio
from .transactions import TransactionExporter
from .timeline import Timeline
from .dl import DL
from .fake import FakeTradeRepublic
