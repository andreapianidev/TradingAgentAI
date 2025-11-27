"""
Tests for the advanced news analyzer module.

Tests cover:
- Basic sentiment analysis (keyword-based fallback)
- DeepSeek response parsing (JSON extraction)
- Cache with TTL
- Freshness filtering
- Symbol sentiment calculation
- Aggregated sentiment with weights
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta, timezone
import json
import time

from data.news_analyzer import (
    NewsAnalyzer,
    DeepSeekNewsClient,
    ArticleScraper,
    SYMBOL_KEYWORDS,
    HIGH_IMPACT_KEYWORDS,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def news_analyzer():
    """Create a news analyzer instance with mocked clients."""
    analyzer = NewsAnalyzer()
    # Don't actually call DeepSeek or scrape
    analyzer.deepseek = MagicMock()
    analyzer.deepseek.is_configured.return_value = False
    analyzer.scraper = MagicMock()
    analyzer.scraper.scrape_article.return_value = None
    return analyzer


@pytest.fixture
def deepseek_client():
    """Create a DeepSeek client for testing response parsing."""
    with patch('data.news_analyzer.settings') as mock_settings:
        mock_settings.DEEPSEEK_NEWS_API_KEY = ""
        mock_settings.DEEPSEEK_BASE_URL = "https://api.deepseek.com"
        mock_settings.MODEL_NAME = "deepseek-chat"
        client = DeepSeekNewsClient()
    return client


@pytest.fixture
def sample_news_items():
    """Sample news items for testing."""
    now = datetime.now(timezone.utc)
    return [
        {
            "title": "Bitcoin ETF Approval Sends BTC Surging to New Highs",
            "url": "https://example.com/btc-etf",
            "summary": "The SEC has approved multiple Bitcoin ETFs, leading to institutional adoption.",
            "published_at": (now - timedelta(hours=1)).isoformat(),
            "source": "CryptoNews",
        },
        {
            "title": "Ethereum Network Upgrade Improves Scalability",
            "url": "https://example.com/eth-upgrade",
            "summary": "The latest Ethereum upgrade brings significant performance improvements.",
            "published_at": (now - timedelta(hours=2)).isoformat(),
            "source": "CoinDesk",
        },
        {
            "title": "Solana Faces Network Issues After Hack",
            "url": "https://example.com/sol-hack",
            "summary": "A major hack has caused concerns about Solana's security.",
            "published_at": (now - timedelta(hours=3)).isoformat(),
            "source": "Decrypt",
        },
        {
            "title": "Old News About Crypto",
            "url": "https://example.com/old-news",
            "summary": "This is stale news that should be filtered out.",
            "published_at": (now - timedelta(hours=10)).isoformat(),
            "source": "OldSource",
        },
    ]


# ============================================================================
# Basic Sentiment Tests
# ============================================================================

class TestBasicSentiment:
    """Tests for keyword-based sentiment analysis."""

    def test_bullish_sentiment_detection(self, news_analyzer):
        """Test that bullish keywords produce positive sentiment."""
        result = news_analyzer._basic_sentiment(
            title="Bitcoin ETF Approval Sparks Rally",
            content="The approval of Bitcoin ETF has led to surge in institutional adoption and record growth."
        )

        assert result["sentiment"] in ["bullish", "very_bullish"]
        assert result["sentiment_score"] > 0
        assert "BTC" in result["affected_symbols"]

    def test_bearish_sentiment_detection(self, news_analyzer):
        """Test that bearish keywords produce negative sentiment."""
        result = news_analyzer._basic_sentiment(
            title="Major Crypto Exchange Hacked",
            content="A massive hack has caused crash in prices with liquidation of positions and fear spreading."
        )

        assert result["sentiment"] in ["bearish", "very_bearish"]
        assert result["sentiment_score"] < 0

    def test_neutral_sentiment_detection(self, news_analyzer):
        """Test that balanced content produces neutral sentiment."""
        result = news_analyzer._basic_sentiment(
            title="Crypto Market Analysis",
            content="The market shows mixed signals with no clear direction."
        )

        assert result["sentiment"] == "neutral"
        assert -0.3 <= result["sentiment_score"] <= 0.3

    def test_high_impact_keyword_detection(self, news_analyzer):
        """Test that high impact keywords are detected."""
        result = news_analyzer._basic_sentiment(
            title="SEC Announces New ETF Ruling",
            content="The SEC has made a decision regarding Bitcoin ETF applications."
        )

        assert result["impact_level"] in ["high", "medium"]

    def test_symbol_detection_btc(self, news_analyzer):
        """Test Bitcoin-related keywords detection."""
        result = news_analyzer._basic_sentiment(
            title="Bitcoin Mining Difficulty Increases",
            content="BTC miners face new challenges after the halving event."
        )

        assert "BTC" in result["affected_symbols"]

    def test_symbol_detection_eth(self, news_analyzer):
        """Test Ethereum-related keywords detection."""
        result = news_analyzer._basic_sentiment(
            title="Ethereum Layer 2 Networks Gain Traction",
            content="Optimism and Arbitrum see increased activity on ETH network."
        )

        assert "ETH" in result["affected_symbols"]

    def test_symbol_detection_sol(self, news_analyzer):
        """Test Solana-related keywords detection."""
        result = news_analyzer._basic_sentiment(
            title="Solana DeFi Ecosystem Expands",
            content="Jupiter and Raydium protocols on SOL see new milestones."
        )

        assert "SOL" in result["affected_symbols"]


# ============================================================================
# DeepSeek Response Parsing Tests
# ============================================================================

class TestDeepSeekParsing:
    """Tests for DeepSeek response JSON parsing."""

    def test_parse_valid_json(self, deepseek_client):
        """Test parsing valid JSON response."""
        response = '''
        {
            "summary": "Bitcoin price increases",
            "sentiment": "bullish",
            "sentiment_score": 0.75,
            "impact_level": "high",
            "affected_symbols": ["BTC"],
            "key_points": ["ETF approved", "Institutional buying"],
            "market_implications": "Positive outlook"
        }
        '''

        result = deepseek_client._parse_deepseek_response(response)

        assert result is not None
        assert result["sentiment"] == "bullish"
        assert result["sentiment_score"] == 0.75
        assert result["impact_level"] == "high"

    def test_parse_json_with_markdown(self, deepseek_client):
        """Test parsing JSON wrapped in markdown code blocks."""
        response = '''
        Here is the analysis:

        ```json
        {
            "summary": "Market update",
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "impact_level": "low",
            "affected_symbols": ["BTC", "ETH"],
            "key_points": ["No major news"],
            "market_implications": "Sideways expected"
        }
        ```
        '''

        result = deepseek_client._parse_deepseek_response(response)

        assert result is not None
        assert result["sentiment"] == "neutral"
        assert "BTC" in result["affected_symbols"]

    def test_parse_invalid_json(self, deepseek_client):
        """Test handling of invalid JSON."""
        response = "This is not JSON at all, just plain text."

        result = deepseek_client._parse_deepseek_response(response)

        assert result is None

    def test_parse_missing_required_fields(self, deepseek_client):
        """Test handling of JSON with missing fields - should add defaults."""
        response = '''
        {
            "summary": "Some news"
        }
        '''

        result = deepseek_client._parse_deepseek_response(response)

        # Should add defaults for missing required fields
        assert result is not None
        assert result["sentiment"] == "neutral"
        assert result["sentiment_score"] == 0.0
        assert result["impact_level"] == "low"

    def test_parse_nested_json_objects(self, deepseek_client):
        """Test parsing JSON with nested objects."""
        response = '''
        {
            "summary": "Complex analysis",
            "sentiment": "bearish",
            "sentiment_score": -0.5,
            "impact_level": "medium",
            "affected_symbols": ["SOL"],
            "key_points": ["Network issues", "User concerns"],
            "market_implications": "Short-term negative",
            "additional_data": {
                "volume": "high",
                "trend": "down"
            }
        }
        '''

        result = deepseek_client._parse_deepseek_response(response)

        assert result is not None
        assert result["sentiment"] == "bearish"
        assert result["sentiment_score"] == -0.5


# ============================================================================
# Cache TTL Tests
# ============================================================================

class TestCacheTTL:
    """Tests for cache with TTL expiration."""

    def test_cache_stores_data(self, news_analyzer):
        """Test that cache stores data correctly."""
        cache_key = "test_key"
        test_data = {"title": "Test", "sentiment": "neutral"}

        news_analyzer._set_cache(cache_key, test_data)
        result = news_analyzer._get_from_cache(cache_key)

        assert result is not None
        assert result["title"] == "Test"

    def test_cache_returns_none_for_missing_key(self, news_analyzer):
        """Test that missing keys return None."""
        result = news_analyzer._get_from_cache("nonexistent_key")
        assert result is None

    def test_cache_expiration(self, news_analyzer):
        """Test that expired cache entries are removed."""
        cache_key = "expiring_key"
        test_data = {"title": "Expiring", "sentiment": "neutral"}

        # Set cache with very short TTL
        news_analyzer._cache_ttl = timedelta(milliseconds=1)
        news_analyzer._set_cache(cache_key, test_data)

        # Wait for expiration
        time.sleep(0.01)

        result = news_analyzer._get_from_cache(cache_key)
        assert result is None

    def test_cache_cleanup(self, news_analyzer):
        """Test cache cleanup removes expired entries."""
        # Set very short TTL
        news_analyzer._cache_ttl = timedelta(milliseconds=1)

        # Add some entries
        news_analyzer._set_cache("key1", {"data": "1"})
        news_analyzer._set_cache("key2", {"data": "2"})

        # Wait for expiration
        time.sleep(0.01)

        # Cleanup
        removed = news_analyzer._cleanup_expired_cache()

        assert removed == 2
        assert len(news_analyzer._cache) == 0


# ============================================================================
# Freshness Filter Tests
# ============================================================================

class TestFreshnessFilter:
    """Tests for news freshness filtering."""

    def test_fresh_news_passes_filter(self, news_analyzer):
        """Test that recent news passes the freshness filter."""
        now = datetime.now(timezone.utc)
        fresh_date = (now - timedelta(hours=2)).isoformat()

        assert news_analyzer._is_fresh(fresh_date) is True

    def test_stale_news_filtered(self, news_analyzer):
        """Test that old news is filtered out."""
        now = datetime.now(timezone.utc)
        stale_date = (now - timedelta(hours=10)).isoformat()

        assert news_analyzer._is_fresh(stale_date) is False

    def test_unparseable_date_passes(self, news_analyzer):
        """Test that unparseable dates pass (conservative approach)."""
        assert news_analyzer._is_fresh("not a date") is True
        assert news_analyzer._is_fresh("") is True

    def test_age_calculation(self, news_analyzer):
        """Test age calculation in hours."""
        now = datetime.now(timezone.utc)
        three_hours_ago = (now - timedelta(hours=3)).isoformat()

        age = news_analyzer._calculate_age_hours(three_hours_ago)

        assert 2.9 <= age <= 3.1  # Allow small margin

    def test_batch_analysis_filters_stale(self, news_analyzer, sample_news_items):
        """Test that batch analysis filters stale news."""
        # Mock the analysis method
        news_analyzer._analyze_single_item = MagicMock(return_value={
            "title": "Test",
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "impact_level": "low",
            "affected_symbols": ["BTC"],
        })

        result = news_analyzer.analyze_news_batch(sample_news_items)

        # Should have filtered the stale news (>4 hours old by default)
        assert result["stale_filtered"] >= 1
        assert result["fresh_count"] < len(sample_news_items)


# ============================================================================
# Symbol Sentiment Tests
# ============================================================================

class TestSymbolSentiment:
    """Tests for per-symbol sentiment calculation."""

    def test_symbol_sentiment_calculation(self, news_analyzer):
        """Test calculation of per-symbol sentiment."""
        articles = [
            {
                "affected_symbols": ["BTC"],
                "sentiment": "bullish",
                "sentiment_score": 0.8
            },
            {
                "affected_symbols": ["BTC", "ETH"],
                "sentiment": "bullish",
                "sentiment_score": 0.6
            },
            {
                "affected_symbols": ["ETH"],
                "sentiment": "bearish",
                "sentiment_score": -0.4
            },
            {
                "affected_symbols": ["SOL"],
                "sentiment": "neutral",
                "sentiment_score": 0.0
            },
        ]

        result = news_analyzer._calculate_symbol_sentiments(articles)

        # BTC: (0.8 + 0.6) / 2 = 0.7
        assert 0.65 <= result["BTC"]["score"] <= 0.75
        assert result["BTC"]["article_count"] == 2
        assert result["BTC"]["label"] == "bullish"

        # ETH: (0.6 + -0.4) / 2 = 0.1
        assert 0.05 <= result["ETH"]["score"] <= 0.15
        assert result["ETH"]["article_count"] == 2
        assert result["ETH"]["label"] == "neutral"

        # SOL: 0.0
        assert result["SOL"]["score"] == 0.0
        assert result["SOL"]["article_count"] == 1
        assert result["SOL"]["label"] == "neutral"

    def test_symbol_with_no_articles(self, news_analyzer):
        """Test symbol with no related articles."""
        articles = [
            {
                "affected_symbols": ["BTC"],
                "sentiment": "bullish",
                "sentiment_score": 0.5
            },
        ]

        result = news_analyzer._calculate_symbol_sentiments(articles)

        # ETH and SOL should have no articles
        assert result["ETH"]["article_count"] == 0
        assert result["SOL"]["article_count"] == 0


# ============================================================================
# Aggregated Sentiment Tests
# ============================================================================

class TestAggregatedSentiment:
    """Tests for aggregated sentiment calculation with weights."""

    def test_aggregated_sentiment_basic(self, news_analyzer):
        """Test basic aggregated sentiment calculation."""
        articles = [
            {"sentiment": "bullish", "sentiment_score": 0.6, "impact_level": "low", "age_hours": 1},
            {"sentiment": "bullish", "sentiment_score": 0.4, "impact_level": "low", "age_hours": 2},
        ]

        result = news_analyzer._calculate_aggregated_sentiment(articles)

        assert result["score"] > 0
        assert result["label"] in ["bullish", "very_bullish"]
        assert result["total_articles"] == 2

    def test_high_impact_weight(self, news_analyzer):
        """Test that high impact news has more weight."""
        articles = [
            {"sentiment": "bearish", "sentiment_score": -0.8, "impact_level": "high", "age_hours": 1},
            {"sentiment": "bullish", "sentiment_score": 0.3, "impact_level": "low", "age_hours": 1},
            {"sentiment": "bullish", "sentiment_score": 0.3, "impact_level": "low", "age_hours": 1},
        ]

        result = news_analyzer._calculate_aggregated_sentiment(articles)

        # High impact bearish should outweigh two low impact bullish
        assert result["score"] < 0
        assert result["label"] in ["bearish", "very_bearish"]

    def test_freshness_weight(self, news_analyzer):
        """Test that fresher news has more weight."""
        articles = [
            {"sentiment": "bullish", "sentiment_score": 0.5, "impact_level": "medium", "age_hours": 0.5},
            {"sentiment": "bearish", "sentiment_score": -0.5, "impact_level": "medium", "age_hours": 3.5},
        ]

        result = news_analyzer._calculate_aggregated_sentiment(articles)

        # Fresher bullish news should have more weight
        assert result["score"] > 0

    def test_empty_articles(self, news_analyzer):
        """Test handling of empty article list."""
        result = news_analyzer._calculate_aggregated_sentiment([])

        assert result["score"] == 0.0
        assert result["label"] == "neutral"
        assert result["confidence"] == 0.0

    def test_sentiment_breakdown(self, news_analyzer):
        """Test sentiment breakdown counts."""
        articles = [
            {"sentiment": "bullish", "sentiment_score": 0.5, "impact_level": "low", "age_hours": 1},
            {"sentiment": "bullish", "sentiment_score": 0.6, "impact_level": "low", "age_hours": 1},
            {"sentiment": "neutral", "sentiment_score": 0.0, "impact_level": "low", "age_hours": 1},
            {"sentiment": "bearish", "sentiment_score": -0.4, "impact_level": "low", "age_hours": 1},
        ]

        result = news_analyzer._calculate_aggregated_sentiment(articles)

        assert result["breakdown"]["bullish"] == 2
        assert result["breakdown"]["neutral"] == 1
        assert result["breakdown"]["bearish"] == 1

    def test_confidence_calculation(self, news_analyzer):
        """Test confidence based on sentiment consistency."""
        # All bullish = high confidence
        consistent_articles = [
            {"sentiment": "bullish", "sentiment_score": 0.5, "impact_level": "low", "age_hours": 1},
            {"sentiment": "bullish", "sentiment_score": 0.6, "impact_level": "low", "age_hours": 1},
            {"sentiment": "bullish", "sentiment_score": 0.7, "impact_level": "low", "age_hours": 1},
        ]

        result = news_analyzer._calculate_aggregated_sentiment(consistent_articles)
        assert result["confidence"] == 1.0  # All same sentiment

        # Mixed = lower confidence
        mixed_articles = [
            {"sentiment": "bullish", "sentiment_score": 0.5, "impact_level": "low", "age_hours": 1},
            {"sentiment": "bearish", "sentiment_score": -0.5, "impact_level": "low", "age_hours": 1},
            {"sentiment": "neutral", "sentiment_score": 0.0, "impact_level": "low", "age_hours": 1},
        ]

        result = news_analyzer._calculate_aggregated_sentiment(mixed_articles)
        assert result["confidence"] < 0.5


# ============================================================================
# Score to Label Tests
# ============================================================================

class TestScoreToLabel:
    """Tests for sentiment score to label conversion."""

    def test_very_bullish(self, news_analyzer):
        assert news_analyzer._score_to_label(0.7) == "very_bullish"
        assert news_analyzer._score_to_label(1.0) == "very_bullish"

    def test_bullish(self, news_analyzer):
        assert news_analyzer._score_to_label(0.3) == "bullish"
        assert news_analyzer._score_to_label(0.4) == "bullish"

    def test_neutral(self, news_analyzer):
        assert news_analyzer._score_to_label(0.0) == "neutral"
        assert news_analyzer._score_to_label(0.1) == "neutral"
        assert news_analyzer._score_to_label(-0.1) == "neutral"

    def test_bearish(self, news_analyzer):
        assert news_analyzer._score_to_label(-0.3) == "bearish"
        assert news_analyzer._score_to_label(-0.4) == "bearish"

    def test_very_bearish(self, news_analyzer):
        assert news_analyzer._score_to_label(-0.7) == "very_bearish"
        assert news_analyzer._score_to_label(-1.0) == "very_bearish"


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for the news analyzer."""

    def test_empty_result_structure(self, news_analyzer):
        """Test that empty result has correct structure."""
        result = news_analyzer._empty_result()

        assert "analyzed_articles" in result
        assert "aggregated_sentiment" in result
        assert "symbol_sentiments" in result
        assert "high_impact_news" in result
        assert result["total_analyzed"] == 0

    def test_llm_summary_format(self, news_analyzer):
        """Test get_news_summary_for_llm output format."""
        analysis_result = {
            "analyzed_articles": [
                {
                    "title": "Test Article",
                    "url": "https://example.com",
                    "summary": "Test summary",
                    "sentiment": "bullish",
                    "sentiment_score": 0.5,
                    "impact_level": "high",
                    "age_hours": 1,
                    "source": "TestSource",
                    "affected_symbols": ["BTC"],
                    "key_points": ["Point 1", "Point 2"],
                }
            ],
            "aggregated_sentiment": {
                "score": 0.5,
                "label": "bullish",
            },
            "symbol_sentiments": {
                "BTC": {"score": 0.5, "article_count": 1, "label": "bullish"},
            },
            "high_impact_news": [],
            "total_analyzed": 1,
        }

        result = news_analyzer.get_news_summary_for_llm(analysis_result)

        assert "total_analyzed" in result
        assert "aggregated_sentiment" in result
        assert "articles" in result
        assert len(result["articles"]) == 1
        assert result["articles"][0]["title"] == "Test Article"

    def test_llm_summary_symbol_filter(self, news_analyzer):
        """Test LLM summary filters by symbol."""
        analysis_result = {
            "analyzed_articles": [
                {
                    "title": "BTC Article",
                    "affected_symbols": ["BTC"],
                    "sentiment": "bullish",
                    "sentiment_score": 0.5,
                    "impact_level": "low",
                    "age_hours": 1,
                    "source": "Test",
                    "key_points": [],
                },
                {
                    "title": "ETH Article",
                    "affected_symbols": ["ETH"],
                    "sentiment": "bearish",
                    "sentiment_score": -0.5,
                    "impact_level": "low",
                    "age_hours": 1,
                    "source": "Test",
                    "key_points": [],
                },
            ],
            "aggregated_sentiment": {},
            "symbol_sentiments": {
                "BTC": {"score": 0.5},
                "ETH": {"score": -0.5},
            },
            "high_impact_news": [],
            "total_analyzed": 2,
        }

        result = news_analyzer.get_news_summary_for_llm(analysis_result, symbol="BTC")

        assert len(result["articles"]) == 1
        assert result["articles"][0]["title"] == "BTC Article"
