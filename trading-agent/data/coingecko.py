"""
CoinGecko API client for market data.
Free tier: 10-50 calls/minute without API key.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time

import httpx

from utils.logger import get_logger

logger = get_logger(__name__)

# Cache duration in seconds (5 minutes to respect rate limits)
CACHE_DURATION = 300

# Rate limit backoff time in seconds
RATE_LIMIT_BACKOFF = 60

# CoinGecko coin IDs mapping
COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
}


class CoinGeckoCollector:
    """Collects market data from CoinGecko API (free tier)."""

    BASE_URL = "https://api.coingecko.com/api/v3"
    TIMEOUT = 15.0

    def __init__(self):
        """Initialize the CoinGecko collector."""
        self._global_cache: Optional[Dict[str, Any]] = None
        self._global_cache_time: Optional[datetime] = None
        self._trending_cache: Optional[List[Dict[str, Any]]] = None
        self._trending_cache_time: Optional[datetime] = None
        self._market_cache: Dict[str, Dict[str, Any]] = {}
        self._market_cache_time: Dict[str, datetime] = {}
        self._rate_limited_until: Optional[datetime] = None

    def _is_rate_limited(self) -> bool:
        """Check if we're currently rate limited."""
        if self._rate_limited_until is None:
            return False
        if datetime.utcnow() >= self._rate_limited_until:
            self._rate_limited_until = None
            return False
        return True

    def _set_rate_limited(self):
        """Set rate limit backoff."""
        self._rate_limited_until = datetime.utcnow() + timedelta(seconds=RATE_LIMIT_BACKOFF)
        logger.warning(f"CoinGecko rate limited. Backing off for {RATE_LIMIT_BACKOFF}s")

    def _is_cache_valid(self, cache_time: Optional[datetime]) -> bool:
        """Check if cache is still valid."""
        if not cache_time:
            return False
        age = (datetime.utcnow() - cache_time).total_seconds()
        return age < CACHE_DURATION

    def get_global_data(self) -> Dict[str, Any]:
        """
        Get global crypto market data.

        Returns:
            Dictionary with total market cap, BTC dominance, etc.
        """
        if self._is_cache_valid(self._global_cache_time) and self._global_cache:
            logger.debug("Using cached global data")
            return self._global_cache

        # Check rate limit
        if self._is_rate_limited():
            logger.debug("CoinGecko rate limited, returning cached data")
            return self._global_cache if self._global_cache else self._default_global()

        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                response = client.get(f"{self.BASE_URL}/global")
                response.raise_for_status()

                data = response.json().get("data", {})

                result = {
                    "total_market_cap_usd": data.get("total_market_cap", {}).get("usd", 0),
                    "total_volume_24h_usd": data.get("total_volume", {}).get("usd", 0),
                    "btc_dominance": data.get("market_cap_percentage", {}).get("btc", 0),
                    "eth_dominance": data.get("market_cap_percentage", {}).get("eth", 0),
                    "market_cap_change_24h_pct": data.get("market_cap_change_percentage_24h_usd", 0),
                    "active_cryptocurrencies": data.get("active_cryptocurrencies", 0),
                    "markets": data.get("markets", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                }

                self._global_cache = result
                self._global_cache_time = datetime.utcnow()

                logger.info(f"CoinGecko Global: BTC Dom {result['btc_dominance']:.1f}% | "
                           f"MCap ${result['total_market_cap_usd']/1e12:.2f}T | "
                           f"Change {result['market_cap_change_24h_pct']:.2f}%")

                return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                self._set_rate_limited()
            else:
                logger.warning(f"CoinGecko API error: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.warning(f"CoinGecko timeout (>{self.TIMEOUT}s)")
        except Exception as e:
            logger.error(f"Error fetching CoinGecko global data: {e}")

        # Return cached or default
        if self._global_cache:
            return self._global_cache

        return self._default_global()

    def get_trending_coins(self) -> List[Dict[str, Any]]:
        """
        Get trending coins (top 7 most searched in last 24h).

        Returns:
            List of trending coins with rank, name, symbol
        """
        if self._is_cache_valid(self._trending_cache_time) and self._trending_cache:
            logger.debug("Using cached trending data")
            return self._trending_cache

        # Check rate limit
        if self._is_rate_limited():
            return self._trending_cache if self._trending_cache else []

        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                response = client.get(f"{self.BASE_URL}/search/trending")
                response.raise_for_status()

                data = response.json()
                coins = data.get("coins", [])

                trending = []
                for i, coin_data in enumerate(coins[:7]):
                    coin = coin_data.get("item", {})
                    trending.append({
                        "rank": i + 1,
                        "id": coin.get("id", ""),
                        "name": coin.get("name", ""),
                        "symbol": coin.get("symbol", "").upper(),
                        "market_cap_rank": coin.get("market_cap_rank", 0),
                        "price_btc": coin.get("price_btc", 0),
                        "score": coin.get("score", 0),
                    })

                self._trending_cache = trending
                self._trending_cache_time = datetime.utcnow()

                trending_symbols = [t["symbol"] for t in trending[:5]]
                logger.info(f"CoinGecko Trending: {', '.join(trending_symbols)}")

                return trending

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                self._set_rate_limited()
            else:
                logger.warning(f"CoinGecko trending API error: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.warning(f"CoinGecko trending timeout (>{self.TIMEOUT}s)")
        except Exception as e:
            logger.error(f"Error fetching CoinGecko trending: {e}")

        return self._trending_cache if self._trending_cache else []

    def get_market_data(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get market data for specific coins.

        Args:
            symbols: List of symbols (BTC, ETH, SOL)

        Returns:
            Dictionary mapping symbol to market data
        """
        # Convert symbols to CoinGecko IDs
        coin_ids = []
        symbol_to_id = {}
        for symbol in symbols:
            cg_id = COINGECKO_IDS.get(symbol.upper())
            if cg_id:
                coin_ids.append(cg_id)
                symbol_to_id[cg_id] = symbol.upper()

        if not coin_ids:
            return {}

        # Check if all requested coins are in cache
        all_cached = all(
            self._is_cache_valid(self._market_cache_time.get(s))
            for s in symbols
        )
        if all_cached:
            logger.debug("Using cached market data")
            return {s: self._market_cache.get(s, {}) for s in symbols}

        # Check rate limit
        if self._is_rate_limited():
            return {s: self._market_cache.get(s, {}) for s in symbols}

        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                params = {
                    "vs_currency": "usd",
                    "ids": ",".join(coin_ids),
                    "order": "market_cap_desc",
                    "per_page": 10,
                    "page": 1,
                    "sparkline": "false",
                    "price_change_percentage": "1h,24h,7d"
                }

                response = client.get(f"{self.BASE_URL}/coins/markets", params=params)
                response.raise_for_status()

                data = response.json()
                result = {}

                for coin in data:
                    symbol = symbol_to_id.get(coin.get("id"), coin.get("symbol", "").upper())

                    market_data = {
                        "symbol": symbol,
                        "name": coin.get("name", ""),
                        "current_price": coin.get("current_price", 0),
                        "market_cap": coin.get("market_cap", 0),
                        "market_cap_rank": coin.get("market_cap_rank", 0),
                        "total_volume": coin.get("total_volume", 0),
                        "high_24h": coin.get("high_24h", 0),
                        "low_24h": coin.get("low_24h", 0),
                        "price_change_24h": coin.get("price_change_24h", 0),
                        "price_change_percentage_1h": coin.get("price_change_percentage_1h_in_currency", 0),
                        "price_change_percentage_24h": coin.get("price_change_percentage_24h", 0),
                        "price_change_percentage_7d": coin.get("price_change_percentage_7d_in_currency", 0),
                        "market_cap_change_24h": coin.get("market_cap_change_24h", 0),
                        "market_cap_change_percentage_24h": coin.get("market_cap_change_percentage_24h", 0),
                        "circulating_supply": coin.get("circulating_supply", 0),
                        "total_supply": coin.get("total_supply", 0),
                        "ath": coin.get("ath", 0),
                        "ath_change_percentage": coin.get("ath_change_percentage", 0),
                        "ath_date": coin.get("ath_date", ""),
                        "atl": coin.get("atl", 0),
                        "atl_change_percentage": coin.get("atl_change_percentage", 0),
                        "timestamp": datetime.utcnow().isoformat(),
                    }

                    result[symbol] = market_data
                    self._market_cache[symbol] = market_data
                    self._market_cache_time[symbol] = datetime.utcnow()

                    logger.debug(f"CoinGecko {symbol}: ${market_data['current_price']:,.2f} | "
                               f"1h: {market_data['price_change_percentage_1h']:.2f}% | "
                               f"24h: {market_data['price_change_percentage_24h']:.2f}%")

                return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                self._set_rate_limited()
            else:
                logger.warning(f"CoinGecko market API error: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.warning(f"CoinGecko market timeout (>{self.TIMEOUT}s)")
        except Exception as e:
            logger.error(f"Error fetching CoinGecko market data: {e}")

        # Return cached data
        return {s: self._market_cache.get(s, {}) for s in symbols}

    def get_btc_dominance(self) -> float:
        """
        Get current BTC market dominance percentage.

        Returns:
            BTC dominance as percentage (e.g., 52.5)
        """
        global_data = self.get_global_data()
        return global_data.get("btc_dominance", 0)

    def get_market_summary(self, symbols: List[str] = None) -> Dict[str, Any]:
        """
        Get a complete market summary including global data, trending, and specific coins.
        Returns partial data if some API calls fail.

        Args:
            symbols: Optional list of symbols to include

        Returns:
            Complete market summary dictionary (may have empty sections on errors)
        """
        if symbols is None:
            symbols = ["BTC", "ETH", "SOL"]

        # Get each data source independently - failures don't affect others
        global_data = {}
        trending = []
        market_data = {}
        errors = []

        try:
            global_data = self.get_global_data()
            if global_data.get("error"):
                errors.append("global")
        except Exception as e:
            logger.warning(f"Failed to get global data: {e}")
            errors.append("global")
            global_data = self._default_global()

        try:
            trending = self.get_trending_coins()
        except Exception as e:
            logger.warning(f"Failed to get trending coins: {e}")
            errors.append("trending")
            trending = []

        try:
            market_data = self.get_market_data(symbols)
        except Exception as e:
            logger.warning(f"Failed to get market data: {e}")
            errors.append("market")
            market_data = {}

        # Check if any of our tracked symbols are trending
        tracked_trending = []
        trending_symbols = [t["symbol"] for t in trending]
        for symbol in symbols:
            if symbol in trending_symbols:
                tracked_trending.append(symbol)

        result = {
            "global": global_data,
            "trending": trending,
            "trending_symbols": trending_symbols,
            "tracked_trending": tracked_trending,
            "coins": market_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if errors:
            result["partial_errors"] = errors
            logger.debug(f"CoinGecko returned partial data. Failed: {errors}")

        return result

    def _default_global(self) -> Dict[str, Any]:
        """Return default global data when API fails."""
        return {
            "total_market_cap_usd": 0,
            "total_volume_24h_usd": 0,
            "btc_dominance": 0,
            "eth_dominance": 0,
            "market_cap_change_24h_pct": 0,
            "active_cryptocurrencies": 0,
            "markets": 0,
            "timestamp": datetime.utcnow().isoformat(),
            "error": "Data unavailable"
        }


# Global collector instance
coingecko_collector = CoinGeckoCollector()


def get_global_market_data() -> Dict[str, Any]:
    """Convenience function to get global market data."""
    return coingecko_collector.get_global_data()


def get_trending_coins() -> List[Dict[str, Any]]:
    """Convenience function to get trending coins."""
    return coingecko_collector.get_trending_coins()


def get_coin_market_data(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """Convenience function to get market data for specific coins."""
    return coingecko_collector.get_market_data(symbols)


def get_market_summary(symbols: List[str] = None) -> Dict[str, Any]:
    """Convenience function to get complete market summary."""
    return coingecko_collector.get_market_summary(symbols)
