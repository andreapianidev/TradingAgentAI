"""
News feed parser for crypto news.
"""
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from xml.etree import ElementTree

import httpx

from config.settings import settings
from config.constants import CACHE_NEWS_DURATION
from utils.logger import get_logger

logger = get_logger(__name__)

# Keywords to filter crypto-relevant news
CRYPTO_KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "solana", "sol",
    "crypto", "cryptocurrency", "blockchain", "defi",
    "altcoin", "trading", "exchange", "wallet",
    "bull", "bear", "rally", "crash", "pump", "dump"
]


class NewsFeedCollector:
    """Collects and parses crypto news from RSS feeds."""

    def __init__(self):
        """Initialize the news collector."""
        self.feed_url = settings.NEWS_FEED_URL
        self._cache: List[Dict[str, Any]] = []
        self._cache_time: Optional[datetime] = None
        # Default feeds if not configured
        self.default_feeds = [
            "https://cointelegraph.com/rss",
            "https://bitcoinmagazine.com/.rss/full/",
        ]

    def get_recent_news(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent crypto news.

        Args:
            limit: Maximum number of news items

        Returns:
            List of news items
        """
        # Check cache
        if self._is_cache_valid():
            logger.debug("Using cached news data")
            return self._cache[:limit]

        # Fetch new news
        news = self._fetch_news()

        if news:
            self._cache = news
            self._cache_time = datetime.utcnow()
            return news[:limit]

        # Return cached if available
        if self._cache:
            return self._cache[:limit]

        return []

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_time or not self._cache:
            return False

        age = (datetime.utcnow() - self._cache_time).total_seconds()
        return age < CACHE_NEWS_DURATION

    def _fetch_news(self) -> List[Dict[str, Any]]:
        """Fetch news from configured feeds."""
        all_news = []

        # Use configured feed or defaults
        feeds = [self.feed_url] if self.feed_url else self.default_feeds

        for feed_url in feeds:
            if not feed_url:
                continue

            try:
                news = self._parse_feed(feed_url)
                all_news.extend(news)
            except Exception as e:
                logger.warning(f"Error fetching feed {feed_url}: {e}")

        # Sort by date and filter
        all_news = self._filter_relevant_news(all_news)
        all_news.sort(key=lambda x: x.get("published_at", ""), reverse=True)

        return all_news

    def _parse_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """Parse an RSS/Atom feed."""
        news_items = []

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(feed_url)
                response.raise_for_status()

                root = ElementTree.fromstring(response.content)

                # Try RSS format
                items = root.findall(".//item")
                if not items:
                    # Try Atom format
                    items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

                for item in items[:20]:  # Limit per feed
                    news_item = self._parse_item(item)
                    if news_item:
                        news_items.append(news_item)

        except Exception as e:
            logger.error(f"Error parsing feed: {e}")

        return news_items

    def _parse_item(self, item: ElementTree.Element) -> Optional[Dict[str, Any]]:
        """Parse a single news item from XML."""
        try:
            # Try RSS format first
            title = self._get_element_text(item, "title")
            link = self._get_element_text(item, "link")
            description = self._get_element_text(item, "description")
            pub_date = self._get_element_text(item, "pubDate")

            # Try Atom format if RSS elements not found
            if not title:
                title = self._get_element_text(
                    item, "{http://www.w3.org/2005/Atom}title"
                )
            if not link:
                link_elem = item.find("{http://www.w3.org/2005/Atom}link")
                if link_elem is not None:
                    link = link_elem.get("href", "")
            if not description:
                description = self._get_element_text(
                    item, "{http://www.w3.org/2005/Atom}summary"
                )
            if not pub_date:
                pub_date = self._get_element_text(
                    item, "{http://www.w3.org/2005/Atom}published"
                )

            if not title:
                return None

            # Clean description
            if description:
                description = self._clean_html(description)[:500]

            # Analyze sentiment
            sentiment = self._analyze_sentiment(title, description)

            return {
                "title": title,
                "summary": description,
                "url": link,
                "published_at": pub_date or datetime.utcnow().isoformat(),
                "sentiment": sentiment,
                "source": "RSS Feed",
            }

        except Exception as e:
            logger.debug(f"Error parsing item: {e}")
            return None

    def _get_element_text(
        self,
        parent: ElementTree.Element,
        tag: str
    ) -> Optional[str]:
        """Get text content of an XML element."""
        elem = parent.find(tag)
        if elem is not None and elem.text:
            return elem.text.strip()
        return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        clean = re.sub(r'<[^>]+>', '', text)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()

    def _filter_relevant_news(
        self,
        news: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filter news to only crypto-relevant items."""
        relevant = []

        for item in news:
            title = item.get("title", "").lower()
            summary = item.get("summary", "").lower()
            text = f"{title} {summary}"

            # Check for crypto keywords
            if any(kw in text for kw in CRYPTO_KEYWORDS):
                relevant.append(item)

        return relevant

    def _analyze_sentiment(
        self,
        title: str,
        description: str = ""
    ) -> str:
        """
        Simple sentiment analysis based on keywords.

        Returns:
            "positive", "negative", or "neutral"
        """
        text = f"{title} {description}".lower()

        positive_words = [
            "rally", "surge", "gain", "rise", "bullish", "growth",
            "adoption", "breakthrough", "milestone", "partnership",
            "launch", "upgrade", "record", "high", "pump"
        ]

        negative_words = [
            "crash", "fall", "drop", "bearish", "decline", "loss",
            "hack", "scam", "fraud", "ban", "regulation", "dump",
            "warning", "concern", "fear", "sell-off", "liquidation"
        ]

        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        else:
            return "neutral"


# Global news collector
news_collector = NewsFeedCollector()


def get_recent_news(limit: int = 5) -> List[Dict[str, Any]]:
    """Convenience function to get recent news."""
    return news_collector.get_recent_news(limit)
