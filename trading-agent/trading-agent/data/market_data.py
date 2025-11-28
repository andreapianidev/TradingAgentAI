"""
Market data collection from exchange.
"""
from typing import Dict, Any, List

from exchange.exchange_factory import get_exchange_client
from config.constants import OHLCV_LIMIT
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class MarketDataCollector:
    """Collects market data from exchange."""

    def __init__(self):
        """Initialize the collector."""
        self.client = get_exchange_client()
        self.timeframe = settings.TIMEFRAME
        logger.info(f"MarketDataCollector using {settings.EXCHANGE} exchange")

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get current ticker data.

        Args:
            symbol: Trading symbol

        Returns:
            Ticker data dictionary
        """
        return self.client.fetch_ticker(symbol)

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = None,
        limit: int = OHLCV_LIMIT
    ) -> List[List]:
        """
        Get OHLCV candlestick data.

        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            limit: Number of candles

        Returns:
            List of OHLCV data
        """
        tf = timeframe or self.timeframe
        return self.client.fetch_ohlcv(symbol, tf, limit)

    def get_order_book(self, symbol: str) -> Dict[str, Any]:
        """
        Get order book data.

        Args:
            symbol: Trading symbol

        Returns:
            Order book data
        """
        return self.client.fetch_order_book(symbol)

    def get_complete_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get all market data for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Complete market data dictionary
        """
        logger.info(f"Collecting market data for {symbol}...")

        ticker = self.get_ticker(symbol)
        ohlcv = self.get_ohlcv(symbol)
        orderbook = self.get_order_book(symbol)

        return {
            "symbol": symbol,
            "ticker": ticker,
            "ohlcv": ohlcv,
            "orderbook": orderbook,
            "price": ticker.get("price", 0),
            "change_24h": ticker.get("change_24h", 0),
            "volume_24h": ticker.get("volume_24h", 0),
            "bid": ticker.get("bid", 0),
            "ask": ticker.get("ask", 0),
        }


# Global collector instance
market_data_collector = MarketDataCollector()
