"""
Exchange factory for selecting between different trading platforms.
Supports Hyperliquid and Alpaca with a unified interface.
"""
from typing import Union, Protocol, Dict, List, Optional, Any

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class ExchangeClient(Protocol):
    """Protocol defining the interface all exchange clients must implement."""

    def connect(self) -> bool:
        """Establish connection to the exchange."""
        ...

    def disconnect(self) -> None:
        """Close the connection."""
        ...

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch current ticker data."""
        ...

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List[List]:
        """Fetch OHLCV candlestick data."""
        ...

    def fetch_portfolio(self) -> Dict[str, Any]:
        """Fetch portfolio information."""
        ...

    def fetch_order_book(self, symbol: str, limit: int) -> Dict[str, Any]:
        """Fetch order book data."""
        ...

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for a symbol."""
        ...

    def open_position(
        self,
        symbol: str,
        direction: str,
        size_pct: float,
        leverage: int,
        stop_loss_pct: float,
        take_profit_pct: float
    ) -> Dict[str, Any]:
        """Open a new position."""
        ...

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """Close an existing position."""
        ...

    def get_total_exposure(self) -> float:
        """Get total exposure as percentage."""
        ...

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current position for a symbol."""
        ...

    def has_open_position(self, symbol: str) -> bool:
        """Check if there's an open position."""
        ...


# Supported exchanges
SUPPORTED_EXCHANGES = ["hyperliquid", "alpaca"]


def get_exchange_client() -> Union['HyperliquidClient', 'AlpacaClient']:
    """
    Factory function to get the appropriate exchange client based on settings.

    Returns:
        Exchange client instance (HyperliquidClient or AlpacaClient)

    Raises:
        ValueError: If unsupported exchange is configured
    """
    exchange_name = settings.EXCHANGE.lower()

    if exchange_name not in SUPPORTED_EXCHANGES:
        raise ValueError(
            f"Unsupported exchange: {exchange_name}. "
            f"Supported exchanges: {', '.join(SUPPORTED_EXCHANGES)}"
        )

    if exchange_name == "hyperliquid":
        from exchange.hyperliquid_client import HyperliquidClient
        logger.info("Using Hyperliquid exchange")
        return HyperliquidClient()

    elif exchange_name == "alpaca":
        from exchange.alpaca_client import AlpacaClient
        logger.info("Using Alpaca exchange")
        return AlpacaClient()


def create_exchange_client(exchange_name: str) -> Union['HyperliquidClient', 'AlpacaClient']:
    """
    Create a specific exchange client by name.

    Args:
        exchange_name: Name of the exchange ("hyperliquid" or "alpaca")

    Returns:
        Exchange client instance

    Raises:
        ValueError: If unsupported exchange name
    """
    exchange_name = exchange_name.lower()

    if exchange_name not in SUPPORTED_EXCHANGES:
        raise ValueError(
            f"Unsupported exchange: {exchange_name}. "
            f"Supported exchanges: {', '.join(SUPPORTED_EXCHANGES)}"
        )

    if exchange_name == "hyperliquid":
        from exchange.hyperliquid_client import HyperliquidClient
        return HyperliquidClient()

    elif exchange_name == "alpaca":
        from exchange.alpaca_client import AlpacaClient
        return AlpacaClient()


def get_exchange_info(exchange_name: str) -> Dict[str, Any]:
    """
    Get information about a specific exchange.

    Args:
        exchange_name: Name of the exchange

    Returns:
        Dictionary with exchange information
    """
    exchange_name = exchange_name.lower()

    info = {
        "hyperliquid": {
            "name": "Hyperliquid",
            "type": "DEX",
            "asset_types": ["crypto_perpetuals"],
            "supports_leverage": True,
            "max_leverage": 50,
            "supports_short": True,
            "paper_trading": "testnet",
            "base_currency": "USDC",
            "description": "Decentralized perpetual futures exchange",
            "website": "https://hyperliquid.xyz",
        },
        "alpaca": {
            "name": "Alpaca Markets",
            "type": "Broker",
            "asset_types": ["stocks", "crypto"],
            "supports_leverage": False,  # For crypto
            "max_leverage": 1,
            "supports_short": True,
            "paper_trading": "native",
            "base_currency": "USD",
            "description": "Commission-free trading API for stocks and crypto",
            "website": "https://alpaca.markets",
        },
    }

    return info.get(exchange_name, {"error": "Unknown exchange"})


def list_supported_exchanges() -> List[Dict[str, Any]]:
    """
    Get list of all supported exchanges with their info.

    Returns:
        List of exchange information dictionaries
    """
    return [
        {
            "id": exchange,
            **get_exchange_info(exchange)
        }
        for exchange in SUPPORTED_EXCHANGES
    ]


# Global exchange client instance (lazy loaded)
_exchange_client = None


def get_client() -> Union['HyperliquidClient', 'AlpacaClient']:
    """
    Get the global exchange client instance.
    Creates it on first call (lazy loading).

    Returns:
        Exchange client instance
    """
    global _exchange_client
    if _exchange_client is None:
        _exchange_client = get_exchange_client()
    return _exchange_client


def reset_client() -> None:
    """Reset the global exchange client (useful for switching exchanges)."""
    global _exchange_client
    if _exchange_client is not None:
        try:
            _exchange_client.disconnect()
        except Exception:
            pass
    _exchange_client = None
