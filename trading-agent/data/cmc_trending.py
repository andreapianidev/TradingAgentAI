"""
CoinMarketCap Trending Coins API client.
Fetches trending cryptocurrencies and filters for Alpaca-supported symbols.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx

from config.settings import settings
from config.constants import CACHE_SENTIMENT_DURATION
from utils.logger import get_logger

logger = get_logger(__name__)

# Alpaca supported crypto symbols (as of 2025)
# Source: https://alpaca.markets/support/what-are-the-supported-coins-pairs
ALPACA_SUPPORTED_CRYPTO = {
    "AAVE", "AVAX", "BAT", "BCH", "BTC", "CRV", "DOGE", "DOT",
    "ETH", "GRT", "LINK", "LTC", "PEPE", "SHIB", "SKY", "SOL",
    "SUSHI", "TRUMP", "UNI", "USDC", "USDG", "USDT", "XRP", "XTZ", "YFI"
}

# Core portfolio symbols (always monitored)
CORE_SYMBOLS = {"BTC", "ETH", "SOL"}


class CMCTrendingCollector:
    """Collects trending cryptocurrency data from CoinMarketCap."""

    def __init__(self):
        """Initialize the trending collector."""
        self.api_key = settings.COINMARKETCAP_API_KEY
        self.base_url = "https://pro-api.coinmarketcap.com"
        self._cache: List[Dict[str, Any]] = []
        self._cache_time: Optional[datetime] = None

    def get_trending_coins(
        self,
        limit: int = 50,
        analyze_top: int = 10
    ) -> Dict[str, Any]:
        """
        Get trending coins from CoinMarketCap API.

        Args:
            limit: Max number of trending coins to fetch (default 50)
            analyze_top: How many of the top trending to analyze (default 10)

        Returns:
            Dictionary with trending data and filtered results
        """
        # Check cache
        if self._is_cache_valid():
            logger.debug("Using cached trending data")
            return self._format_response(self._cache, analyze_top)

        # Fetch new data
        try:
            trending = self._fetch_trending(limit)
            if trending:
                self._cache = trending
                self._cache_time = datetime.utcnow()
                return self._format_response(trending, analyze_top)
        except Exception as e:
            logger.error(f"Error fetching trending coins: {e}")

        # Return cached or empty
        if self._cache:
            return self._format_response(self._cache, analyze_top)

        return self._empty_response()

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_time or not self._cache:
            return False

        age = (datetime.utcnow() - self._cache_time).total_seconds()
        return age < CACHE_SENTIMENT_DURATION

    def _fetch_trending(self, limit: int) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch trending coins from CoinMarketCap API.

        Uses /v1/cryptocurrency/trending/most-visited endpoint.
        """
        if not self.api_key:
            logger.warning("No CoinMarketCap API key configured")
            return self._fetch_fallback_trending(limit)

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.base_url}/v1/cryptocurrency/trending/most-visited",
                    headers={
                        "X-CMC_PRO_API_KEY": self.api_key,
                        "Accept": "application/json"
                    },
                    params={"limit": limit}
                )
                response.raise_for_status()

                data = response.json()
                trending_list = data.get("data", [])

                logger.info(f"Fetched {len(trending_list)} trending coins from CMC")
                return trending_list

        except httpx.HTTPStatusError as e:
            logger.error(f"CMC API error: {e.response.status_code} - {e.response.text}")
            return self._fetch_fallback_trending(limit)
        except Exception as e:
            logger.error(f"Error fetching CMC trending: {e}")
            return self._fetch_fallback_trending(limit)

    def _fetch_fallback_trending(self, limit: int) -> Optional[List[Dict[str, Any]]]:
        """
        Fallback: Fetch trending from CoinMarketCap public listings API.

        This endpoint doesn't require authentication but has rate limits.
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.base_url}/v1/cryptocurrency/listings/latest",
                    headers={
                        "X-CMC_PRO_API_KEY": self.api_key,
                        "Accept": "application/json"
                    },
                    params={
                        "limit": limit,
                        "sort": "volume_24h",  # Sort by 24h volume as proxy for trending
                        "sort_dir": "desc"
                    }
                )
                response.raise_for_status()

                data = response.json()
                listings = data.get("data", [])

                logger.info(f"Fetched {len(listings)} coins from CMC listings (fallback)")
                return listings

        except Exception as e:
            logger.error(f"Error fetching CMC listings: {e}")
            return None

    def _format_response(
        self,
        trending: List[Dict[str, Any]],
        analyze_top: int
    ) -> Dict[str, Any]:
        """
        Format trending data and filter for Alpaca-supported symbols.

        Args:
            trending: Raw trending data from API
            analyze_top: Number of top coins to analyze

        Returns:
            Formatted response with filtered coins
        """
        # Extract and filter for Alpaca support
        alpaca_supported = []
        all_trending_symbols = []

        for coin in trending[:analyze_top]:
            symbol = coin.get("symbol", "")
            all_trending_symbols.append(symbol)

            if symbol in ALPACA_SUPPORTED_CRYPTO:
                # Enrich with additional flags
                is_core = symbol in CORE_SYMBOLS

                coin_data = {
                    "symbol": symbol,
                    "name": coin.get("name", ""),
                    "rank": coin.get("cmc_rank", 0),
                    "price": coin.get("quote", {}).get("USD", {}).get("price", 0),
                    "volume_24h": coin.get("quote", {}).get("USD", {}).get("volume_24h", 0),
                    "percent_change_24h": coin.get("quote", {}).get("USD", {}).get("percent_change_24h", 0),
                    "market_cap": coin.get("quote", {}).get("USD", {}).get("market_cap", 0),
                    "is_core": is_core,
                    "is_alpaca_supported": True,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                alpaca_supported.append(coin_data)

        logger.info(f"Found {len(alpaca_supported)} Alpaca-supported coins in top {analyze_top} trending")
        logger.info(f"Alpaca-supported trending: {[c['symbol'] for c in alpaca_supported]}")

        return {
            "trending_coins": alpaca_supported,
            "total_analyzed": analyze_top,
            "alpaca_supported_count": len(alpaca_supported),
            "all_trending_symbols": all_trending_symbols,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _empty_response(self) -> Dict[str, Any]:
        """Return empty response when no data available."""
        return {
            "trending_coins": [],
            "total_analyzed": 0,
            "alpaca_supported_count": 0,
            "all_trending_symbols": [],
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_alpaca_supported_symbols(self) -> List[str]:
        """Get list of all Alpaca-supported crypto symbols."""
        return sorted(list(ALPACA_SUPPORTED_CRYPTO))

    def is_alpaca_supported(self, symbol: str) -> bool:
        """Check if a symbol is supported by Alpaca."""
        return symbol.upper() in ALPACA_SUPPORTED_CRYPTO


# Global trending collector
cmc_trending_collector = CMCTrendingCollector()


def get_trending_coins(limit: int = 50, analyze_top: int = 10) -> Dict[str, Any]:
    """Convenience function to get trending coins."""
    return cmc_trending_collector.get_trending_coins(limit, analyze_top)


def get_alpaca_supported_symbols() -> List[str]:
    """Get list of all Alpaca-supported crypto symbols."""
    return cmc_trending_collector.get_alpaca_supported_symbols()
