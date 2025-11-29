"""
Unit tests for CryptoEvaluator - Multi-criteria cryptocurrency scoring system.

Tests cover:
- Scoring algorithm (30/15/20/15/10/10 weights)
- Technical score calculation
- Sentiment scoring (Fear & Greed)
- Trending score (CMC data)
- Liquidity scoring
- Volatility control
- News sentiment integration
- Opportunity level classification
- Criteria validation
- Edge cases (zero scores, missing data, division by zero)
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCryptoEvaluatorTechnicalScore:
    """Test technical indicator scoring (30% weight)."""

    def test_technical_score_bullish_signals(self):
        """Test technical score with strong bullish signals."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        technical_data = {
            "rsi": 45,  # Neutral, not oversold
            "macd": 100,  # Positive
            "macd_signal": 50,  # MACD > signal (bullish)
            "ema_20": 90000,
            "current_price": 95000,  # Price above EMA20 (bullish)
            "atr_pct": 5.0  # Low volatility (good)
        }

        result = evaluator._calculate_technical_score(technical_data)

        assert result >= 70  # Should be high score
        assert result <= 100

    def test_technical_score_oversold_rsi(self):
        """Test RSI oversold gives bonus points."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        technical_data = {
            "rsi": 25,  # Oversold (<30)
            "macd": 10,
            "macd_signal": 5,
            "ema_20": 90000,
            "current_price": 88000,
            "atr_pct": 8.0
        }

        result = evaluator._calculate_technical_score(technical_data)

        assert result >= 50  # RSI oversold should boost score

    def test_technical_score_overbought_rsi(self):
        """Test RSI overbought reduces score."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        technical_data = {
            "rsi": 75,  # Overbought (>70)
            "macd": -10,
            "macd_signal": 5,
            "ema_20": 90000,
            "current_price": 85000,
            "atr_pct": 12.0
        }

        result = evaluator._calculate_technical_score(technical_data)

        assert result <= 50  # Overbought should lower score

    def test_technical_score_high_volatility_penalty(self):
        """Test high volatility (ATR >15%) penalizes score."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        technical_data = {
            "rsi": 50,
            "macd": 10,
            "macd_signal": 5,
            "ema_20": 90000,
            "current_price": 92000,
            "atr_pct": 18.0  # Very high volatility
        }

        result = evaluator._calculate_technical_score(technical_data)

        assert result <= 60  # High volatility should reduce score

    def test_technical_score_missing_data(self):
        """Test handles missing technical data gracefully."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        technical_data = {
            "rsi": None,
            "macd": None,
            "current_price": 90000
        }

        result = evaluator._calculate_technical_score(technical_data)

        assert result >= 0
        assert result <= 100


class TestCryptoEvaluatorSentimentScore:
    """Test sentiment scoring (15% weight) - Fear & Greed Index."""

    def test_sentiment_extreme_fear(self):
        """Test EXTREME_FEAR sentiment (contrarian buy signal)."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        sentiment_data = {
            "label": "EXTREME_FEAR",
            "score": 15
        }

        result = evaluator._calculate_sentiment_score(sentiment_data)

        assert result >= 85  # Extreme fear = high opportunity score (contrarian)

    def test_sentiment_fear(self):
        """Test FEAR sentiment (buy signal)."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        sentiment_data = {
            "label": "FEAR",
            "score": 35
        }

        result = evaluator._calculate_sentiment_score(sentiment_data)

        assert result >= 70
        assert result <= 85

    def test_sentiment_neutral(self):
        """Test NEUTRAL sentiment."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        sentiment_data = {
            "label": "NEUTRAL",
            "score": 50
        }

        result = evaluator._calculate_sentiment_score(sentiment_data)

        assert result == 50

    def test_sentiment_extreme_greed(self):
        """Test EXTREME_GREED sentiment (contrarian sell signal)."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        sentiment_data = {
            "label": "EXTREME_GREED",
            "score": 90
        }

        result = evaluator._calculate_sentiment_score(sentiment_data)

        assert result <= 20  # Extreme greed = low opportunity score


class TestCryptoEvaluatorTrendingScore:
    """Test trending data scoring (20% weight) - CMC data."""

    def test_trending_top_10_ranking(self):
        """Test top 10 CMC trending gets high score."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        trending_data = {
            "rank": 5,  # Top 10
            "volume_24h": 600_000_000,  # >$500M
            "percent_change_24h": 12.5  # >10% gain
        }

        result = evaluator._calculate_trending_score(trending_data)

        assert result >= 80  # High ranking + volume + gain

    def test_trending_moderate_ranking(self):
        """Test ranking 11-25 gets moderate score."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        trending_data = {
            "rank": 20,  # Top 25
            "volume_24h": 200_000_000,
            "percent_change_24h": 5.0
        }

        result = evaluator._calculate_trending_score(trending_data)

        assert result >= 40
        assert result <= 70

    def test_trending_no_data(self):
        """Test missing trending data returns default score."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()

        result = evaluator._calculate_trending_score(None)

        assert result == 50  # Default neutral score


class TestCryptoEvaluatorLiquidityScore:
    """Test liquidity scoring (15% weight) - 24h volume."""

    def test_liquidity_excellent(self):
        """Test excellent liquidity (>$200M volume)."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        volume_24h = 500_000_000  # $500M

        result = evaluator._calculate_liquidity_score(volume_24h)

        assert result == 100

    def test_liquidity_good(self):
        """Test good liquidity ($50M-$200M)."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        volume_24h = 100_000_000  # $100M

        result = evaluator._calculate_liquidity_score(volume_24h)

        assert result >= 70
        assert result < 100

    def test_liquidity_moderate(self):
        """Test moderate liquidity ($10M-$50M)."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        volume_24h = 30_000_000  # $30M

        result = evaluator._calculate_liquidity_score(volume_24h)

        assert result >= 40
        assert result < 70

    def test_liquidity_poor(self):
        """Test poor liquidity (<$10M)."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        volume_24h = 5_000_000  # $5M

        result = evaluator._calculate_liquidity_score(volume_24h)

        assert result <= 30


class TestCryptoEvaluatorVolatilityScore:
    """Test volatility scoring (10% weight) - ATR percentage."""

    def test_volatility_very_low(self):
        """Test very low volatility (<5% ATR)."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        atr_pct = 3.5

        result = evaluator._calculate_volatility_score(atr_pct)

        assert result >= 85

    def test_volatility_moderate(self):
        """Test moderate volatility (5-10% ATR)."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        atr_pct = 7.5

        result = evaluator._calculate_volatility_score(atr_pct)

        assert result >= 50
        assert result < 85

    def test_volatility_high(self):
        """Test high volatility (>15% ATR) - risky."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()
        atr_pct = 18.0

        result = evaluator._calculate_volatility_score(atr_pct)

        assert result <= 30


class TestCryptoEvaluatorWeightedScoring:
    """Test weighted scoring algorithm (30/15/20/15/10/10)."""

    def test_overall_score_calculation(self):
        """Test overall weighted score combines all factors correctly."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()

        technical_data = {
            "rsi": 45,
            "macd": 50,
            "macd_signal": 30,
            "ema_20": 90000,
            "current_price": 95000,
            "atr_pct": 6.0
        }
        sentiment_data = {"label": "FEAR", "score": 35}
        trending_data = {
            "rank": 8,
            "volume_24h": 600_000_000,
            "percent_change_24h": 8.0
        }
        news_analysis = {"sentiment_score": 0.5, "confidence": 0.8}

        result = evaluator.evaluate_opportunity(
            symbol="BTC",
            technical_data=technical_data,
            sentiment_data=sentiment_data,
            trending_data=trending_data,
            news_analysis=news_analysis
        )

        assert "opportunity_score" in result
        assert result["opportunity_score"] >= 0
        assert result["opportunity_score"] <= 100
        assert "opportunity_level" in result
        assert "criteria_met" in result

    def test_score_within_bounds(self):
        """Test all scores remain within 0-100 range."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()

        # Extreme positive values
        technical_data = {
            "rsi": 20,  # Very oversold
            "macd": 200,
            "macd_signal": 50,
            "ema_20": 80000,
            "current_price": 100000,
            "atr_pct": 2.0
        }
        sentiment_data = {"label": "EXTREME_FEAR", "score": 10}
        trending_data = {
            "rank": 1,
            "volume_24h": 1_000_000_000,
            "percent_change_24h": 20.0
        }

        result = evaluator.evaluate_opportunity(
            symbol="BTC",
            technical_data=technical_data,
            sentiment_data=sentiment_data,
            trending_data=trending_data
        )

        assert result["opportunity_score"] <= 100


class TestCryptoEvaluatorOpportunityLevels:
    """Test opportunity level classification."""

    def test_opportunity_level_excellent(self):
        """Test EXCELLENT level (score >= 75)."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()

        # Mock high-score scenario
        with patch.object(evaluator, '_calculate_technical_score', return_value=85):
            with patch.object(evaluator, '_calculate_sentiment_score', return_value=90):
                with patch.object(evaluator, '_calculate_trending_score', return_value=80):
                    with patch.object(evaluator, '_calculate_liquidity_score', return_value=100):
                        with patch.object(evaluator, '_calculate_volatility_score', return_value=85):
                            technical_data = {"rsi": 50, "atr_pct": 5.0}
                            sentiment_data = {"label": "FEAR"}

                            result = evaluator.evaluate_opportunity(
                                symbol="BTC",
                                technical_data=technical_data,
                                sentiment_data=sentiment_data
                            )

                            assert result["opportunity_level"] == "EXCELLENT"

    def test_opportunity_level_good(self):
        """Test GOOD level (score 60-74)."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()

        with patch.object(evaluator, '_calculate_technical_score', return_value=65):
            with patch.object(evaluator, '_calculate_sentiment_score', return_value=60):
                with patch.object(evaluator, '_calculate_trending_score', return_value=70):
                    with patch.object(evaluator, '_calculate_liquidity_score', return_value=75):
                        with patch.object(evaluator, '_calculate_volatility_score', return_value=60):
                            technical_data = {"rsi": 50, "atr_pct": 8.0}
                            sentiment_data = {"label": "NEUTRAL"}

                            result = evaluator.evaluate_opportunity(
                                symbol="ETH",
                                technical_data=technical_data,
                                sentiment_data=sentiment_data
                            )

                            assert result["opportunity_level"] == "GOOD"

    def test_opportunity_level_poor(self):
        """Test POOR level (score < 30)."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()

        with patch.object(evaluator, '_calculate_technical_score', return_value=20):
            with patch.object(evaluator, '_calculate_sentiment_score', return_value=15):
                with patch.object(evaluator, '_calculate_trending_score', return_value=25):
                    with patch.object(evaluator, '_calculate_liquidity_score', return_value=20):
                        with patch.object(evaluator, '_calculate_volatility_score', return_value=10):
                            technical_data = {"rsi": 80, "atr_pct": 20.0}
                            sentiment_data = {"label": "EXTREME_GREED"}

                            result = evaluator.evaluate_opportunity(
                                symbol="SHIB",
                                technical_data=technical_data,
                                sentiment_data=sentiment_data
                            )

                            assert result["opportunity_level"] == "POOR"


class TestCryptoEvaluatorCriteria:
    """Test criteria validation flags."""

    def test_criteria_all_met(self):
        """Test all criteria can be met."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()

        technical_data = {
            "rsi": 50,
            "macd": 50,
            "macd_signal": 30,
            "ema_20": 90000,
            "current_price": 95000,
            "atr_pct": 8.0  # <15%
        }
        sentiment_data = {"label": "FEAR", "score": 35}
        trending_data = {
            "rank": 5,
            "volume_24h": 200_000_000,  # >$10M
            "percent_change_24h": 8.0
        }

        result = evaluator.evaluate_opportunity(
            symbol="BTC",
            technical_data=technical_data,
            sentiment_data=sentiment_data,
            trending_data=trending_data
        )

        criteria = result["criteria_met"]
        assert criteria["min_liquidity"] is True
        assert criteria["volatility_controlled"] is True

    def test_criteria_high_volatility_fails(self):
        """Test volatility_controlled fails with ATR >15%."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()

        technical_data = {
            "rsi": 50,
            "atr_pct": 18.0  # >15%
        }
        sentiment_data = {"label": "NEUTRAL"}

        result = evaluator.evaluate_opportunity(
            symbol="BTC",
            technical_data=technical_data,
            sentiment_data=sentiment_data
        )

        assert result["criteria_met"]["volatility_controlled"] is False


class TestCryptoEvaluatorEdgeCases:
    """Test edge cases and error handling."""

    def test_division_by_zero_protection(self):
        """Test handles zero values without crashing."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()

        technical_data = {
            "rsi": 0,
            "macd": 0,
            "current_price": 0,
            "atr_pct": 0
        }
        sentiment_data = {"score": 0}

        result = evaluator.evaluate_opportunity(
            symbol="BTC",
            technical_data=technical_data,
            sentiment_data=sentiment_data
        )

        assert "opportunity_score" in result
        assert result["opportunity_score"] >= 0

    def test_all_scores_zero(self):
        """Test when all sub-scores are zero."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()

        with patch.object(evaluator, '_calculate_technical_score', return_value=0):
            with patch.object(evaluator, '_calculate_sentiment_score', return_value=0):
                with patch.object(evaluator, '_calculate_trending_score', return_value=0):
                    with patch.object(evaluator, '_calculate_liquidity_score', return_value=0):
                        with patch.object(evaluator, '_calculate_volatility_score', return_value=0):
                            with patch.object(evaluator, '_calculate_news_score', return_value=0):
                                technical_data = {"rsi": 50}
                                sentiment_data = {"label": "NEUTRAL"}

                                result = evaluator.evaluate_opportunity(
                                    symbol="BTC",
                                    technical_data=technical_data,
                                    sentiment_data=sentiment_data
                                )

                                assert result["opportunity_score"] == 0
                                assert result["opportunity_level"] == "POOR"

    def test_missing_all_optional_data(self):
        """Test with only required data (technical + sentiment)."""
        from core.crypto_evaluator import CryptoEvaluator

        evaluator = CryptoEvaluator()

        technical_data = {"rsi": 50, "atr_pct": 10.0}
        sentiment_data = {"label": "NEUTRAL", "score": 50}

        result = evaluator.evaluate_opportunity(
            symbol="BTC",
            technical_data=technical_data,
            sentiment_data=sentiment_data,
            trending_data=None,
            news_analysis=None,
            coingecko_data=None
        )

        assert "opportunity_score" in result
        assert result["opportunity_score"] > 0
