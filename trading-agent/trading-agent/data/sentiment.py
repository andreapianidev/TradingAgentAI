"""
Market sentiment data from CoinMarketCap and other sources.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

import httpx

from config.settings import settings
from config.constants import (
    CACHE_SENTIMENT_DURATION,
    SENTIMENT_FEAR_MAX,
    SENTIMENT_NEUTRAL_MAX
)
from utils.logger import get_logger

logger = get_logger(__name__)


class SentimentCollector:
    """Collects market sentiment data."""

    def __init__(self):
        """Initialize the sentiment collector."""
        self.api_key = settings.COINMARKETCAP_API_KEY
        self.base_url = "https://pro-api.coinmarketcap.com"
        self._cache: Dict[str, Any] = {}
        self._cache_time: Optional[datetime] = None

    def get_fear_greed_index(self) -> Dict[str, Any]:
        """
        Get Fear & Greed Index from CoinMarketCap.

        Returns:
            Sentiment data dictionary
        """
        # Check cache
        if self._is_cache_valid():
            logger.debug("Using cached sentiment data")
            return self._cache

        # Fetch new data
        try:
            sentiment = self._fetch_fear_greed()
            if sentiment:
                self._cache = sentiment
                self._cache_time = datetime.utcnow()
                return sentiment
        except Exception as e:
            logger.error(f"Error fetching sentiment: {e}")

        # Return cached or default
        if self._cache:
            return self._cache

        return self._default_sentiment()

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_time or not self._cache:
            return False

        age = (datetime.utcnow() - self._cache_time).total_seconds()
        return age < CACHE_SENTIMENT_DURATION

    def _fetch_fear_greed(self) -> Optional[Dict[str, Any]]:
        """Fetch Fear & Greed Index from API."""
        if not self.api_key:
            logger.warning("No CoinMarketCap API key configured")
            return self._fetch_alternative_sentiment()

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.base_url}/v3/fear-and-greed/latest",
                    headers={"X-CMC_PRO_API_KEY": self.api_key}
                )
                response.raise_for_status()

                data = response.json()
                fg_data = data.get("data", {})

                value = fg_data.get("value", 50)
                classification = fg_data.get("value_classification", "Neutral")

                return self._format_sentiment(value, classification)

        except httpx.HTTPStatusError as e:
            logger.error(f"CMC API error: {e.response.status_code}")
            return self._fetch_alternative_sentiment()
        except Exception as e:
            logger.error(f"Error fetching CMC sentiment: {e}")
            return self._fetch_alternative_sentiment()

    def _fetch_alternative_sentiment(self) -> Optional[Dict[str, Any]]:
        """Fetch sentiment from Alternative.me (free API)."""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    "https://api.alternative.me/fng/?limit=1"
                )
                response.raise_for_status()

                data = response.json()
                if data.get("data"):
                    fg = data["data"][0]
                    value = int(fg.get("value", 50))
                    classification = fg.get("value_classification", "Neutral")

                    return self._format_sentiment(value, classification)

        except Exception as e:
            logger.error(f"Error fetching alternative sentiment: {e}")

        return None

    def _format_sentiment(
        self,
        value: int,
        classification: str
    ) -> Dict[str, Any]:
        """Format sentiment data."""
        # Determine label
        if value <= SENTIMENT_FEAR_MAX:
            label = "FEAR"
            interpretation = "Il mercato è in fase di paura, possibile opportunità di acquisto"
        elif value <= SENTIMENT_NEUTRAL_MAX:
            label = "NEUTRAL"
            interpretation = "Il mercato è neutro, nessun sentiment dominante"
        else:
            label = "GREED"
            interpretation = "Il mercato è in fase di avidità, possibile eccesso di ottimismo"

        # Extreme cases
        if value <= 10:
            label = "EXTREME_FEAR"
            interpretation = "Paura estrema nel mercato, possibile capitolazione"
        elif value >= 90:
            label = "EXTREME_GREED"
            interpretation = "Avidità estrema, rischio di correzione elevato"

        return {
            "score": value,
            "label": label,
            "classification": classification,
            "interpretation": interpretation,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _default_sentiment(self) -> Dict[str, Any]:
        """Return default neutral sentiment."""
        return {
            "score": 50,
            "label": "NEUTRAL",
            "classification": "Neutral",
            "interpretation": "Dati sentiment non disponibili",
            "timestamp": datetime.utcnow().isoformat(),
        }


# Global sentiment collector
sentiment_collector = SentimentCollector()


def get_market_sentiment() -> Dict[str, Any]:
    """Convenience function to get market sentiment."""
    return sentiment_collector.get_fear_greed_index()
