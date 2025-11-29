"""
CoinMarketCap Trending Coins API client.
Fetches trending cryptocurrencies and filters for Alpaca-supported symbols.

Features:
- Exponential backoff retry (3 attempts)
- Rate limit monitoring (90% threshold alert)
- Fallback to listings API if trending fails
- 1-hour caching to reduce API calls
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx

from config.settings import settings
from config.constants import CACHE_SENTIMENT_DURATION
from utils.logger import get_logger
from utils.retry import exponential_backoff, RateLimitTracker

logger = get_logger(__name__)

# Rate limit tracker for CMC API (333 calls/day free tier)
_rate_limit_tracker = RateLimitTracker("CoinMarketCap")

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
        self.rate_tracker = _rate_limit_tracker

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

    @exponential_backoff(
        max_retries=3,
        base_delay=2.0,
        retry_on=(httpx.RequestError, httpx.HTTPStatusError)
    )
    def _fetch_trending(self, limit: int) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch trending coins from CoinMarketCap API with retry logic.

        Uses /v1/cryptocurrency/trending/most-visited endpoint.
        Retries up to 3 times with exponential backoff (2s, 4s, 8s).
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

                # Record API call
                is_rate_limited = response.status_code == 429
                self.rate_tracker.record_call(
                    success=response.status_code < 400,
                    rate_limited=is_rate_limited
                )

                # Check rate limit threshold (90% of 333 calls/day)
                self.rate_tracker.check_threshold(threshold_pct=90.0, daily_quota=333)

                response.raise_for_status()

                data = response.json()
                trending_list = data.get("data", [])

                logger.info(f"Fetched {len(trending_list)} trending coins from CMC")
                return trending_list

        except httpx.HTTPStatusError as e:
            self.rate_tracker.record_call(success=False, rate_limited=(e.response.status_code == 429))
            logger.error(f"CMC API error: {e.response.status_code} - {e.response.text}")

            # If endpoint not supported (403) or other non-rate-limit errors, use fallback
            if e.response.status_code in [403, 404]:
                logger.info("Trending endpoint not available, using fallback listings API")
                return self._fetch_fallback_trending(limit)
            elif e.response.status_code != 429:  # Don't retry on rate limit
                return self._fetch_fallback_trending(limit)
            raise  # Re-raise to trigger retry decorator

        except Exception as e:
            self.rate_tracker.record_call(success=False)
            logger.error(f"Error fetching CMC trending: {e}")
            raise  # Re-raise to trigger retry decorator

    @exponential_backoff(
        max_retries=2,
        base_delay=1.0,
        retry_on=(httpx.RequestError, httpx.HTTPStatusError)
    )
    def _fetch_fallback_trending(self, limit: int) -> Optional[List[Dict[str, Any]]]:
        """
        Fallback: Fetch trending from CoinMarketCap listings API with retry.

        Sorts by 24h volume as proxy for trending.
        Retries up to 2 times with exponential backoff.
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

                # Record fallback API call
                self.rate_tracker.record_call(
                    success=response.status_code < 400,
                    rate_limited=response.status_code == 429
                )

                response.raise_for_status()

                data = response.json()
                listings = data.get("data", [])

                logger.info(f"Fetched {len(listings)} coins from CMC listings (fallback)")
                return listings

        except Exception as e:
            self.rate_tracker.record_call(success=False)
            logger.error(f"Error fetching CMC listings: {e}")
            raise  # Re-raise to trigger retry

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

    def get_rate_limit_stats(self) -> dict:
        """
        Get rate limit usage statistics.

        Returns:
            Dictionary with API usage stats
        """
        return self.rate_tracker.get_stats()

    def log_rate_limit_stats(self):
        """Log current rate limit statistics."""
        self.rate_tracker.log_stats()


# Global trending collector
cmc_trending_collector = CMCTrendingCollector()


def get_trending_coins(limit: int = 50, analyze_top: int = 10) -> Dict[str, Any]:
    """Convenience function to get trending coins."""
    return cmc_trending_collector.get_trending_coins(limit, analyze_top)


def get_alpaca_supported_symbols() -> List[str]:
    """Get list of all Alpaca-supported crypto symbols."""
    return cmc_trending_collector.get_alpaca_supported_symbols()
