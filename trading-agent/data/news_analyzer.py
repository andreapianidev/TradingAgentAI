"""
Advanced News Analyzer with DeepSeek AI.

This module provides comprehensive news analysis:
- Full article scraping (not just RSS summaries)
- DeepSeek-powered sentiment analysis and summarization
- Freshness filtering (only recent news)
- Symbol-specific relevance scoring
- Aggregated market sentiment calculation
- Rate limiting and retry logic for API calls
- Cache with TTL for analyzed articles
"""
import re
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

import httpx
from bs4 import BeautifulSoup

from config.settings import settings
from config.constants import (
    CACHE_NEWS_ANALYSIS_TTL,
    HTTP_TIMEOUT_SCRAPE,
    HTTP_TIMEOUT_DEEPSEEK,
    NEWS_ANALYSIS_MAX_WORKERS,
    NEWS_ANALYSIS_MAX_RETRIES,
    NEWS_ANALYSIS_RETRY_DELAY,
)
from utils.logger import get_logger
from utils.rate_limiter import deepseek_rate_limiter

logger = get_logger(__name__)

# Use settings for configurable values, constants for fixed values
MAX_NEWS_AGE_HOURS = settings.NEWS_MAX_AGE_HOURS
MAX_ARTICLES_TO_ANALYZE = settings.NEWS_MAX_ARTICLES_TO_ANALYZE

# Minimum article length to be considered valid (characters)
MIN_ARTICLE_LENGTH = 200

# Symbol keywords for relevance scoring
SYMBOL_KEYWORDS = {
    "BTC": ["bitcoin", "btc", "satoshi", "lightning network", "halving"],
    "ETH": ["ethereum", "eth", "vitalik", "erc-20", "erc20", "layer 2", "l2", "optimism", "arbitrum", "base"],
    "SOL": ["solana", "sol", "phantom", "raydium", "jupiter", "jito"],
}

# Impact keywords that increase importance
HIGH_IMPACT_KEYWORDS = [
    "hack", "exploit", "breach", "stolen", "security",
    "sec", "regulation", "lawsuit", "ban", "illegal",
    "etf", "approval", "institutional", "adoption",
    "crash", "surge", "all-time high", "ath", "record",
    "fed", "interest rate", "inflation", "recession",
    "blackrock", "fidelity", "grayscale", "microstrategy",
]

# Sentiment analysis prompt for DeepSeek
NEWS_ANALYSIS_PROMPT = """Sei un analista finanziario esperto di criptovalute. Analizza questa notizia crypto e fornisci:

TITOLO: {title}

CONTENUTO ARTICOLO:
{content}

Rispondi SOLO con un JSON valido in questo formato:
{{
    "summary": "Riassunto in 2-3 frasi focalizzato sull'impatto sul mercato crypto",
    "sentiment": "very_bullish" | "bullish" | "neutral" | "bearish" | "very_bearish",
    "sentiment_score": -1.0 a 1.0 (dove -1 = molto bearish, 0 = neutrale, 1 = molto bullish),
    "impact_level": "high" | "medium" | "low",
    "affected_symbols": ["BTC", "ETH", "SOL"] (lista di crypto direttamente impattate),
    "key_points": ["punto 1", "punto 2", "punto 3"] (max 3 punti chiave),
    "market_implications": "Breve analisi delle implicazioni per il trading"
}}

REGOLE:
- Sii oggettivo e basati sui fatti dell'articolo
- Se la notizia riguarda regolamentazioni negative, hack o ban -> bearish
- Se riguarda adozione istituzionale, ETF, nuovi investimenti -> bullish
- Notizie tecniche/aggiornamenti -> generalmente neutral a meno che non siano breakthrough
- Considera l'impatto a breve termine (24-48 ore) per il trading"""


class DeepSeekNewsClient:
    """Client for DeepSeek API specifically for news analysis with rate limiting and retry."""

    def __init__(self):
        """Initialize the DeepSeek news client."""
        self.api_key = settings.DEEPSEEK_NEWS_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.MODEL_NAME
        self._client: Optional[httpx.Client] = None
        self.rate_limiter = deepseek_rate_limiter

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=HTTP_TIMEOUT_DEEPSEEK)
        return self._client

    def is_configured(self) -> bool:
        """Check if the news API key is configured."""
        return bool(self.api_key and self.api_key != "your_deepseek_news_api_key")

    def _parse_deepseek_response(self, content_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse DeepSeek response with robust JSON extraction.

        Args:
            content_text: Raw response text from DeepSeek

        Returns:
            Parsed JSON dictionary or None if parsing fails
        """
        # Remove markdown code blocks if present
        content_text = re.sub(r'```json\s*', '', content_text)
        content_text = re.sub(r'```\s*', '', content_text)
        content_text = content_text.strip()

        # Try to find JSON object
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content_text)
        if not json_match:
            # Fallback: try greedy match for nested objects
            json_match = re.search(r'\{[\s\S]*\}', content_text)

        if not json_match:
            logger.warning(f"No JSON found in DeepSeek response: {content_text[:200]}")
            return None

        try:
            data = json.loads(json_match.group())

            # Validate required fields
            required_fields = ["sentiment", "sentiment_score", "impact_level"]
            missing = [f for f in required_fields if f not in data]
            if missing:
                logger.warning(f"Missing required fields in DeepSeek response: {missing}")
                # Try to provide defaults for missing fields
                if "sentiment" not in data:
                    data["sentiment"] = "neutral"
                if "sentiment_score" not in data:
                    data["sentiment_score"] = 0.0
                if "impact_level" not in data:
                    data["impact_level"] = "low"

            return data

        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}. Content: {json_match.group()[:200]}")
            return None

    def analyze_article(
        self,
        title: str,
        content: str,
        max_retries: int = NEWS_ANALYSIS_MAX_RETRIES
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a single article using DeepSeek with retry logic.

        Args:
            title: Article title
            content: Full article content
            max_retries: Maximum number of retry attempts

        Returns:
            Analysis result dictionary or None on error
        """
        if not self.is_configured():
            logger.warning("DeepSeek News API key not configured, using basic sentiment")
            return None

        # Truncate very long articles
        max_content_length = 4000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        prompt = NEWS_ANALYSIS_PROMPT.format(title=title, content=content)

        for attempt in range(max_retries + 1):
            try:
                # Apply rate limiting before each request
                wait_time = self.rate_limiter.wait()
                if wait_time > 0:
                    logger.debug(f"Rate limiter: waited {wait_time:.2f}s before DeepSeek call")

                response = self.client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "Sei un analista finanziario crypto. Rispondi SOLO in JSON valido."},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 800,
                    },
                )
                response.raise_for_status()

                # Signal success to adaptive rate limiter
                self.rate_limiter.on_success()

                data = response.json()
                content_text = data["choices"][0]["message"]["content"].strip()

                # Use robust JSON parsing
                analysis = self._parse_deepseek_response(content_text)
                if analysis:
                    return analysis

                # If parsing failed but no exception, don't retry
                logger.warning(f"Could not parse DeepSeek response for: {title[:50]}")
                return None

            except httpx.TimeoutException:
                if attempt < max_retries:
                    delay = NEWS_ANALYSIS_RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"DeepSeek timeout (attempt {attempt + 1}/{max_retries + 1}), "
                                  f"retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                logger.error(f"DeepSeek timeout after {max_retries + 1} attempts")
                return None

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code

                if status_code == 429:  # Rate limit
                    # Signal rate limit to adaptive limiter
                    new_interval = self.rate_limiter.on_rate_limit_error()
                    if attempt < max_retries:
                        delay = max(5.0, new_interval * 2)
                        logger.warning(f"DeepSeek rate limit hit (attempt {attempt + 1}), "
                                      f"backing off {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    logger.error("DeepSeek rate limit exceeded after retries")
                    return None

                elif status_code in (500, 502, 503, 504):  # Server errors
                    if attempt < max_retries:
                        delay = NEWS_ANALYSIS_RETRY_DELAY * (2 ** attempt)
                        logger.warning(f"DeepSeek server error {status_code} (attempt {attempt + 1}), "
                                      f"retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        continue

                # Non-retriable error
                logger.error(f"DeepSeek API error: {status_code}")
                return None

            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error in DeepSeek response: {e}")
                return None

            except Exception as e:
                logger.error(f"Error analyzing article with DeepSeek: {e}")
                return None

        return None

    def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            self._client.close()


class ArticleScraper:
    """Scrapes full article content from news URLs."""

    def __init__(self):
        """Initialize the article scraper."""
        self._client: Optional[httpx.Client] = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=HTTP_TIMEOUT_SCRAPE, follow_redirects=True)
        return self._client

    def scrape_article(self, url: str) -> Optional[str]:
        """
        Scrape full article content from a URL.

        Args:
            url: Article URL to scrape

        Returns:
            Article text content or None on error
        """
        try:
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove unwanted elements
            for element in soup.find_all(["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript"]):
                element.decompose()

            # Try common article content selectors
            article_selectors = [
                "article",
                '[class*="article-body"]',
                '[class*="article-content"]',
                '[class*="post-content"]',
                '[class*="entry-content"]',
                '[class*="story-body"]',
                '[class*="content-body"]',
                "main",
                '[role="main"]',
            ]

            content = None
            for selector in article_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element
                    break

            if not content:
                # Fallback to body
                content = soup.body

            if not content:
                return None

            # Extract paragraphs
            paragraphs = content.find_all("p")
            if paragraphs:
                text = " ".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            else:
                text = content.get_text(separator=" ", strip=True)

            # Clean up text
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()

            if len(text) < MIN_ARTICLE_LENGTH:
                logger.debug(f"Article too short ({len(text)} chars): {url}")
                return None

            return text

        except httpx.TimeoutException:
            logger.debug(f"Timeout scraping: {url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.debug(f"HTTP error scraping {url}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.debug(f"Error scraping {url}: {e}")
            return None

    def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            self._client.close()


class NewsAnalyzer:
    """
    Advanced news analyzer that combines scraping with AI analysis.

    Features:
    - Full article scraping
    - DeepSeek-powered analysis
    - Freshness filtering
    - Symbol-specific relevance
    - Aggregated sentiment calculation
    - Cache with TTL for analyzed articles
    """

    def __init__(self):
        """Initialize the news analyzer."""
        self.deepseek = DeepSeekNewsClient()
        self.scraper = ArticleScraper()
        # Cache with TTL: {cache_key: (timestamp, data)}
        self._cache: Dict[str, Tuple[datetime, Dict[str, Any]]] = {}
        self._cache_ttl = timedelta(seconds=CACHE_NEWS_ANALYSIS_TTL)

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get item from cache if not expired.

        Args:
            cache_key: Cache key to look up

        Returns:
            Cached data if valid, None if expired or not found
        """
        if cache_key not in self._cache:
            return None

        timestamp, data = self._cache[cache_key]
        now = datetime.now(timezone.utc)

        if now - timestamp < self._cache_ttl:
            return data

        # Expired - remove from cache
        del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """
        Store item in cache with current timestamp.

        Args:
            cache_key: Cache key
            data: Data to cache
        """
        self._cache[cache_key] = (datetime.now(timezone.utc), data)

    def _cleanup_expired_cache(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        now = datetime.now(timezone.utc)
        expired_keys = [
            key for key, (timestamp, _) in self._cache.items()
            if now - timestamp >= self._cache_ttl
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats to datetime."""
        if not date_str:
            return None

        # Common date formats
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822
            "%a, %d %b %Y %H:%M:%S %Z",  # RFC 2822 with timezone name
            "%Y-%m-%dT%H:%M:%S%z",       # ISO 8601
            "%Y-%m-%dT%H:%M:%SZ",        # ISO 8601 UTC
            "%Y-%m-%d %H:%M:%S",         # Common format
            "%Y-%m-%d",                   # Date only
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                # Ensure timezone awareness
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        # Try parsing with dateutil as fallback
        try:
            from dateutil import parser
            dt = parser.parse(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

        return None

    def _is_fresh(self, published_at: str) -> bool:
        """Check if news is within the freshness window."""
        pub_date = self._parse_date(published_at)
        if not pub_date:
            # If we can't parse date, assume it might be recent
            return True

        now = datetime.now(timezone.utc)
        age = now - pub_date
        max_age = timedelta(hours=MAX_NEWS_AGE_HOURS)

        return age <= max_age

    def _calculate_age_hours(self, published_at: str) -> float:
        """Calculate the age of news in hours."""
        pub_date = self._parse_date(published_at)
        if not pub_date:
            return 0.0

        now = datetime.now(timezone.utc)
        age = now - pub_date
        return age.total_seconds() / 3600

    def _basic_sentiment(self, title: str, content: str = "") -> Dict[str, Any]:
        """
        Fallback basic sentiment analysis when DeepSeek is unavailable.

        Args:
            title: Article title
            content: Article content

        Returns:
            Basic sentiment analysis
        """
        text = f"{title} {content}".lower()

        # Sentiment word lists
        bullish_words = [
            "surge", "rally", "gain", "rise", "bullish", "growth", "adoption",
            "breakthrough", "milestone", "partnership", "launch", "upgrade",
            "record", "high", "pump", "approval", "etf", "institutional",
            "invest", "support", "optimism", "recovery"
        ]

        bearish_words = [
            "crash", "fall", "drop", "bearish", "decline", "loss", "hack",
            "scam", "fraud", "ban", "regulation", "dump", "warning", "concern",
            "fear", "sell-off", "liquidation", "reject", "lawsuit", "investigation"
        ]

        bullish_count = sum(1 for word in bullish_words if word in text)
        bearish_count = sum(1 for word in bearish_words if word in text)

        # Calculate score
        if bullish_count + bearish_count == 0:
            score = 0.0
            sentiment = "neutral"
        else:
            score = (bullish_count - bearish_count) / (bullish_count + bearish_count)
            if score > 0.3:
                sentiment = "bullish" if score < 0.7 else "very_bullish"
            elif score < -0.3:
                sentiment = "bearish" if score > -0.7 else "very_bearish"
            else:
                sentiment = "neutral"

        # Check for high impact keywords
        impact = "low"
        for keyword in HIGH_IMPACT_KEYWORDS:
            if keyword in text:
                impact = "high" if keyword in ["hack", "etf", "sec", "crash", "surge"] else "medium"
                break

        # Determine affected symbols
        affected = []
        for symbol, keywords in SYMBOL_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                affected.append(symbol)

        return {
            "summary": title[:200],
            "sentiment": sentiment,
            "sentiment_score": round(score, 2),
            "impact_level": impact,
            "affected_symbols": affected if affected else ["BTC", "ETH", "SOL"],
            "key_points": [title[:100]],
            "market_implications": "Analisi automatica basata su keyword",
            "analysis_method": "basic"
        }

    def analyze_news_batch(
        self,
        news_items: List[Dict[str, Any]],
        max_items: int = MAX_ARTICLES_TO_ANALYZE
    ) -> Dict[str, Any]:
        """
        Analyze a batch of news items with full scraping and AI analysis.

        Args:
            news_items: List of news items from RSS feeds
            max_items: Maximum number of items to analyze

        Returns:
            Comprehensive analysis result with:
            - analyzed_articles: List of analyzed articles
            - aggregated_sentiment: Overall market sentiment
            - symbol_sentiments: Per-symbol sentiment breakdown
            - high_impact_news: List of high-impact news items
        """
        start_time = time.time()
        logger.info(f"Starting advanced news analysis for {len(news_items)} items...")

        # Step 1: Filter for freshness
        fresh_news = [
            item for item in news_items
            if self._is_fresh(item.get("published_at", ""))
        ]

        stale_count = len(news_items) - len(fresh_news)
        if stale_count > 0:
            logger.info(f"Filtered out {stale_count} stale news (>{MAX_NEWS_AGE_HOURS}h old)")

        if not fresh_news:
            logger.warning("No fresh news found within the time window")
            return self._empty_result()

        # Limit items to analyze
        items_to_analyze = fresh_news[:max_items]
        logger.info(f"Analyzing {len(items_to_analyze)} fresh news articles...")

        # Step 2: Scrape and analyze articles
        analyzed_articles = []
        high_impact_news = []

        # Use threading for parallel scraping (limited workers to respect rate limits)
        with ThreadPoolExecutor(max_workers=NEWS_ANALYSIS_MAX_WORKERS) as executor:
            # Submit scraping tasks
            future_to_item = {
                executor.submit(self._analyze_single_item, item): item
                for item in items_to_analyze
            }

            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    if result:
                        analyzed_articles.append(result)
                        if result.get("impact_level") == "high":
                            high_impact_news.append(result)
                except Exception as e:
                    logger.debug(f"Error analyzing article: {e}")

        logger.info(f"Successfully analyzed {len(analyzed_articles)} articles")

        # Step 3: Calculate aggregated sentiment
        aggregated = self._calculate_aggregated_sentiment(analyzed_articles)

        # Step 4: Calculate per-symbol sentiment
        symbol_sentiments = self._calculate_symbol_sentiments(analyzed_articles)

        elapsed = time.time() - start_time
        logger.info(f"News analysis completed in {elapsed:.2f}s | "
                   f"Overall sentiment: {aggregated['label']} ({aggregated['score']:.2f})")

        return {
            "analyzed_articles": analyzed_articles,
            "aggregated_sentiment": aggregated,
            "symbol_sentiments": symbol_sentiments,
            "high_impact_news": high_impact_news,
            "total_analyzed": len(analyzed_articles),
            "fresh_count": len(fresh_news),
            "stale_filtered": stale_count,
            "analysis_time_seconds": round(elapsed, 2),
        }

    def _analyze_single_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze a single news item."""
        url = item.get("url", "")
        title = item.get("title", "")
        rss_summary = item.get("summary", "")

        if not url or not title:
            return None

        # Check cache first (with TTL)
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.debug(f"Using cached analysis for: {title[:50]}")
            return cached_result

        # Scrape full article
        full_content = self.scraper.scrape_article(url)
        content_to_analyze = full_content or rss_summary

        if not content_to_analyze:
            logger.debug(f"No content available for: {title[:50]}")
            # Use basic analysis on title only
            analysis = self._basic_sentiment(title)
        else:
            # Try DeepSeek analysis
            analysis = self.deepseek.analyze_article(title, content_to_analyze)
            if not analysis:
                # Fallback to basic
                analysis = self._basic_sentiment(title, content_to_analyze)

        # Enrich with metadata
        result = {
            **analysis,
            "title": title,
            "url": url,
            "source": item.get("source", "Unknown"),
            "published_at": item.get("published_at", ""),
            "age_hours": round(self._calculate_age_hours(item.get("published_at", "")), 1),
            "has_full_content": bool(full_content),
            "content_length": len(content_to_analyze) if content_to_analyze else 0,
        }

        # Cache the result with TTL
        self._set_cache(cache_key, result)

        return result

    def _calculate_aggregated_sentiment(
        self,
        articles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate aggregated sentiment from all analyzed articles.

        Uses weighted average based on:
        - Impact level (high = 3x, medium = 2x, low = 1x)
        - Freshness (newer = higher weight)
        """
        if not articles:
            return {
                "score": 0.0,
                "label": "neutral",
                "interpretation": "Nessuna news analizzata",
                "confidence": 0.0,
            }

        total_weight = 0.0
        weighted_score = 0.0
        sentiment_counts = {"very_bullish": 0, "bullish": 0, "neutral": 0, "bearish": 0, "very_bearish": 0}

        for article in articles:
            # Impact weight
            impact_weights = {"high": 3.0, "medium": 2.0, "low": 1.0}
            impact_weight = impact_weights.get(article.get("impact_level", "low"), 1.0)

            # Freshness weight (exponential decay)
            age_hours = article.get("age_hours", 0)
            freshness_weight = max(0.5, 1.0 - (age_hours / MAX_NEWS_AGE_HOURS) * 0.5)

            # Combined weight
            weight = impact_weight * freshness_weight

            # Score
            score = article.get("sentiment_score", 0.0)
            weighted_score += score * weight
            total_weight += weight

            # Count sentiments
            sentiment = article.get("sentiment", "neutral")
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1

        # Calculate final score
        final_score = weighted_score / total_weight if total_weight > 0 else 0.0
        final_score = max(-1.0, min(1.0, final_score))  # Clamp to [-1, 1]

        # Determine label
        if final_score >= 0.5:
            label = "very_bullish"
            interpretation = "Sentiment news molto positivo - forte ottimismo nel mercato"
        elif final_score >= 0.2:
            label = "bullish"
            interpretation = "Sentiment news positivo - moderato ottimismo"
        elif final_score <= -0.5:
            label = "very_bearish"
            interpretation = "Sentiment news molto negativo - forte pessimismo nel mercato"
        elif final_score <= -0.2:
            label = "bearish"
            interpretation = "Sentiment news negativo - moderato pessimismo"
        else:
            label = "neutral"
            interpretation = "Sentiment news neutro - nessuna direzione dominante"

        # Calculate confidence based on consistency
        dominant_count = max(sentiment_counts.values())
        total_articles = len(articles)
        confidence = dominant_count / total_articles if total_articles > 0 else 0.0

        return {
            "score": round(final_score, 3),
            "label": label,
            "interpretation": interpretation,
            "confidence": round(confidence, 2),
            "breakdown": sentiment_counts,
            "total_articles": total_articles,
        }

    def _calculate_symbol_sentiments(
        self,
        articles: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate sentiment breakdown per symbol."""
        symbol_data: Dict[str, List[float]] = {
            "BTC": [],
            "ETH": [],
            "SOL": [],
        }

        for article in articles:
            affected = article.get("affected_symbols", [])
            score = article.get("sentiment_score", 0.0)

            for symbol in affected:
                if symbol in symbol_data:
                    symbol_data[symbol].append(score)

        result = {}
        for symbol, scores in symbol_data.items():
            if scores:
                avg_score = sum(scores) / len(scores)
                result[symbol] = {
                    "score": round(avg_score, 3),
                    "article_count": len(scores),
                    "label": self._score_to_label(avg_score),
                }
            else:
                result[symbol] = {
                    "score": 0.0,
                    "article_count": 0,
                    "label": "neutral",
                }

        return result

    def _score_to_label(self, score: float) -> str:
        """Convert sentiment score to label."""
        if score >= 0.5:
            return "very_bullish"
        elif score >= 0.2:
            return "bullish"
        elif score <= -0.5:
            return "very_bearish"
        elif score <= -0.2:
            return "bearish"
        return "neutral"

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty analysis result."""
        return {
            "analyzed_articles": [],
            "aggregated_sentiment": {
                "score": 0.0,
                "label": "neutral",
                "interpretation": "Nessuna news recente disponibile",
                "confidence": 0.0,
            },
            "symbol_sentiments": {
                "BTC": {"score": 0.0, "article_count": 0, "label": "neutral"},
                "ETH": {"score": 0.0, "article_count": 0, "label": "neutral"},
                "SOL": {"score": 0.0, "article_count": 0, "label": "neutral"},
            },
            "high_impact_news": [],
            "total_analyzed": 0,
            "fresh_count": 0,
            "stale_filtered": 0,
        }

    def get_news_summary_for_llm(
        self,
        analysis_result: Dict[str, Any],
        symbol: str = None,
        max_articles: int = 10
    ) -> Dict[str, Any]:
        """
        Format news analysis for LLM consumption.

        Args:
            analysis_result: Result from analyze_news_batch
            symbol: Optional symbol to filter for
            max_articles: Maximum articles to include

        Returns:
            Formatted summary for LLM prompt
        """
        articles = analysis_result.get("analyzed_articles", [])
        aggregated = analysis_result.get("aggregated_sentiment", {})
        symbol_sentiments = analysis_result.get("symbol_sentiments", {})
        high_impact = analysis_result.get("high_impact_news", [])

        # Filter by symbol if specified
        if symbol and symbol in SYMBOL_KEYWORDS:
            articles = [
                a for a in articles
                if symbol in a.get("affected_symbols", [])
            ]

        # Sort by impact and freshness
        articles = sorted(
            articles,
            key=lambda x: (
                {"high": 3, "medium": 2, "low": 1}.get(x.get("impact_level", "low"), 0),
                -x.get("age_hours", 99)
            ),
            reverse=True
        )[:max_articles]

        return {
            "total_analyzed": analysis_result.get("total_analyzed", 0),
            "aggregated_sentiment": aggregated,
            "symbol_sentiment": symbol_sentiments.get(symbol, {}) if symbol else symbol_sentiments,
            "high_impact_count": len(high_impact),
            "articles": [
                {
                    "title": a.get("title", "")[:100],
                    "summary": a.get("summary", "")[:200],
                    "sentiment": a.get("sentiment", "neutral"),
                    "sentiment_score": a.get("sentiment_score", 0.0),
                    "impact": a.get("impact_level", "low"),
                    "age_hours": a.get("age_hours", 0),
                    "source": a.get("source", "Unknown"),
                    "key_points": a.get("key_points", [])[:2],
                }
                for a in articles
            ],
        }

    def close(self):
        """Close all clients."""
        self.deepseek.close()
        self.scraper.close()


# Global instance
news_analyzer = NewsAnalyzer()


def analyze_news(news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convenience function to analyze news."""
    return news_analyzer.analyze_news_batch(news_items)


def get_news_for_llm(
    analysis_result: Dict[str, Any],
    symbol: str = None
) -> Dict[str, Any]:
    """Convenience function to get formatted news for LLM."""
    return news_analyzer.get_news_summary_for_llm(analysis_result, symbol)
