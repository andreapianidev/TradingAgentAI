"""
CryptoEvaluator: Multi-criteria scoring system for cryptocurrency opportunities.

Evaluates cryptocurrencies based on:
- Technical indicators (RSI, MACD, ATR volatility)
- Market sentiment (Fear & Greed, news)
- Trending data (CMC volume, social interest)
- Liquidity (24h volume)
- Volatility control (ATR within limits)
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)

# Scoring thresholds
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_NEUTRAL_LOW = 40
RSI_NEUTRAL_HIGH = 60

MIN_VOLUME_24H_USD = 10_000_000  # $10M minimum daily volume
MAX_ATR_PCT = 15.0  # Maximum 15% ATR for volatility control


class CryptoEvaluator:
    """Evaluates cryptocurrency opportunities using multi-criteria scoring."""

    def __init__(self):
        """Initialize the evaluator."""
        pass

    def evaluate_opportunity(
        self,
        symbol: str,
        technical_data: Dict[str, Any],
        sentiment_data: Dict[str, Any],
        trending_data: Optional[Dict[str, Any]] = None,
        news_analysis: Optional[Dict[str, Any]] = None,
        coingecko_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a cryptocurrency opportunity with multi-criteria scoring.

        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")
            technical_data: Technical indicators (RSI, MACD, ATR, etc.)
            sentiment_data: Market sentiment (Fear & Greed Index)
            trending_data: CMC trending data (rank, volume, price change)
            news_analysis: News sentiment analysis
            coingecko_data: CoinGecko market data

        Returns:
            Dictionary with scores, overall score, and reasoning
        """
        scores = {}
        reasoning = []

        # 1. Technical Score (0-100)
        technical_score, tech_reasoning = self._score_technical(symbol, technical_data)
        scores["technical"] = technical_score
        reasoning.extend(tech_reasoning)

        # 2. Sentiment Score (0-100)
        sentiment_score, sent_reasoning = self._score_sentiment(sentiment_data)
        scores["sentiment"] = sentiment_score
        reasoning.extend(sent_reasoning)

        # 3. Trending Score (0-100)
        trending_score, trend_reasoning = self._score_trending(trending_data)
        scores["trending"] = trending_score
        reasoning.extend(trend_reasoning)

        # 4. Liquidity Score (0-100)
        liquidity_score, liq_reasoning = self._score_liquidity(trending_data, coingecko_data)
        scores["liquidity"] = liquidity_score
        reasoning.extend(liq_reasoning)

        # 5. Volatility Score (0-100, higher is better = lower volatility)
        volatility_score, vol_reasoning = self._score_volatility(technical_data)
        scores["volatility"] = volatility_score
        reasoning.extend(vol_reasoning)

        # 6. News Score (0-100)
        news_score, news_reasoning = self._score_news(news_analysis)
        scores["news"] = news_score
        reasoning.extend(news_reasoning)

        # Calculate weighted overall score
        # Weights: Technical 30%, Sentiment 15%, Trending 20%, Liquidity 15%, Volatility 10%, News 10%
        overall_score = (
            technical_score * 0.30 +
            sentiment_score * 0.15 +
            trending_score * 0.20 +
            liquidity_score * 0.15 +
            volatility_score * 0.10 +
            news_score * 0.10
        )

        # Determine opportunity level
        if overall_score >= 75:
            opportunity_level = "EXCELLENT"
        elif overall_score >= 60:
            opportunity_level = "GOOD"
        elif overall_score >= 45:
            opportunity_level = "MODERATE"
        elif overall_score >= 30:
            opportunity_level = "WEAK"
        else:
            opportunity_level = "POOR"

        return {
            "symbol": symbol,
            "overall_score": round(overall_score, 2),
            "opportunity_level": opportunity_level,
            "scores": {k: round(v, 2) for k, v in scores.items()},
            "reasoning": reasoning,
            "timestamp": datetime.utcnow().isoformat(),
            "criteria_met": self._check_criteria(scores, technical_data),
        }

    def _score_technical(
        self,
        symbol: str,
        indicators: Dict[str, Any]
    ) -> tuple[float, List[str]]:
        """
        Score based on technical indicators.

        Returns:
            (score 0-100, reasoning list)
        """
        if not indicators:
            return 0.0, ["No technical data available"]

        score = 50.0  # Start neutral
        reasoning = []

        # RSI analysis
        rsi = indicators.get("rsi")
        if rsi is not None:
            if rsi < RSI_OVERSOLD:
                score += 15
                reasoning.append(f"RSI oversold ({rsi:.1f}) - strong buy signal")
            elif rsi < RSI_NEUTRAL_LOW:
                score += 8
                reasoning.append(f"RSI below neutral ({rsi:.1f}) - mild buy signal")
            elif rsi > RSI_OVERBOUGHT:
                score -= 15
                reasoning.append(f"RSI overbought ({rsi:.1f}) - avoid buying")
            elif rsi > RSI_NEUTRAL_HIGH:
                score -= 8
                reasoning.append(f"RSI above neutral ({rsi:.1f}) - mild sell pressure")
            else:
                reasoning.append(f"RSI neutral ({rsi:.1f})")

        # MACD analysis
        macd_bullish = indicators.get("macd_bullish")
        macd_histogram_rising = indicators.get("macd_histogram_rising")

        if macd_bullish:
            score += 10
            reasoning.append("MACD bullish crossover")
        else:
            score -= 5
            reasoning.append("MACD bearish")

        if macd_histogram_rising:
            score += 5
            reasoning.append("MACD histogram rising (momentum building)")

        # Price vs EMA20
        price_above_ema20 = indicators.get("price_above_ema20")
        if price_above_ema20:
            score += 8
            reasoning.append("Price above EMA20 (uptrend)")
        elif price_above_ema20 is False:
            score -= 8
            reasoning.append("Price below EMA20 (downtrend)")

        # Volatility ratio (favor normal to slightly elevated)
        volatility_ratio = indicators.get("volatility_ratio", 1.0)
        if volatility_ratio < 0.8:
            score += 5
            reasoning.append(f"Low volatility ({volatility_ratio:.2f}) - stable")
        elif volatility_ratio > 1.5:
            score -= 10
            reasoning.append(f"Extreme volatility ({volatility_ratio:.2f}) - risky")

        # Clamp score to 0-100
        score = max(0, min(100, score))

        return score, reasoning

    def _score_sentiment(self, sentiment_data: Dict[str, Any]) -> tuple[float, List[str]]:
        """
        Score based on market sentiment (Fear & Greed Index).

        Returns:
            (score 0-100, reasoning list)
        """
        if not sentiment_data:
            return 50.0, ["No sentiment data available"]

        fg_score = sentiment_data.get("score", 50)
        label = sentiment_data.get("label", "NEUTRAL")

        # Contrarian approach: Fear = Opportunity, Greed = Caution
        if label == "EXTREME_FEAR":
            score = 90
            reasoning = [f"Extreme fear ({fg_score}) - strong contrarian buy opportunity"]
        elif label == "FEAR":
            score = 75
            reasoning = [f"Fear ({fg_score}) - good buy opportunity"]
        elif label == "NEUTRAL":
            score = 50
            reasoning = [f"Neutral sentiment ({fg_score})"]
        elif label == "GREED":
            score = 30
            reasoning = [f"Greed ({fg_score}) - be cautious"]
        elif label == "EXTREME_GREED":
            score = 10
            reasoning = [f"Extreme greed ({fg_score}) - avoid buying, high correction risk"]
        else:
            score = 50
            reasoning = [f"Sentiment: {label} ({fg_score})"]

        return score, reasoning

    def _score_trending(self, trending_data: Optional[Dict[str, Any]]) -> tuple[float, List[str]]:
        """
        Score based on CMC trending data.

        Returns:
            (score 0-100, reasoning list)
        """
        if not trending_data:
            return 50.0, ["No trending data available"]

        score = 50.0
        reasoning = []

        # Rank in trending (lower rank = higher score)
        rank = trending_data.get("rank", 1000)
        if rank <= 10:
            score += 25
            reasoning.append(f"Top 10 trending (rank {rank})")
        elif rank <= 25:
            score += 15
            reasoning.append(f"Top 25 trending (rank {rank})")
        elif rank <= 50:
            score += 8
            reasoning.append(f"Top 50 trending (rank {rank})")

        # 24h volume change (if available)
        volume_24h = trending_data.get("volume_24h", 0)
        if volume_24h > 500_000_000:  # $500M+
            score += 10
            reasoning.append(f"High volume (${volume_24h/1e6:.1f}M)")
        elif volume_24h > 100_000_000:  # $100M+
            score += 5
            reasoning.append(f"Good volume (${volume_24h/1e6:.1f}M)")

        # 24h price change
        percent_change_24h = trending_data.get("percent_change_24h", 0)
        if percent_change_24h > 10:
            score += 8
            reasoning.append(f"Strong 24h gain (+{percent_change_24h:.1f}%)")
        elif percent_change_24h > 5:
            score += 5
            reasoning.append(f"Moderate 24h gain (+{percent_change_24h:.1f}%)")
        elif percent_change_24h < -10:
            score -= 8
            reasoning.append(f"Large 24h drop ({percent_change_24h:.1f}%)")

        # Clamp score
        score = max(0, min(100, score))

        return score, reasoning

    def _score_liquidity(
        self,
        trending_data: Optional[Dict[str, Any]],
        coingecko_data: Optional[Dict[str, Any]]
    ) -> tuple[float, List[str]]:
        """
        Score based on liquidity (24h volume).

        Returns:
            (score 0-100, reasoning list)
        """
        volume_24h = 0

        if trending_data:
            volume_24h = trending_data.get("volume_24h", 0)
        elif coingecko_data:
            volume_24h = coingecko_data.get("total_volume", 0)

        if volume_24h == 0:
            return 50.0, ["No liquidity data available"]

        # Score based on volume thresholds
        if volume_24h < MIN_VOLUME_24H_USD:
            score = 20
            reasoning = [f"Low liquidity (${volume_24h/1e6:.1f}M) - risky"]
        elif volume_24h < 50_000_000:
            score = 50
            reasoning = [f"Moderate liquidity (${volume_24h/1e6:.1f}M)"]
        elif volume_24h < 200_000_000:
            score = 75
            reasoning = [f"Good liquidity (${volume_24h/1e6:.1f}M)"]
        else:
            score = 100
            reasoning = [f"Excellent liquidity (${volume_24h/1e6:.1f}M)"]

        return score, reasoning

    def _score_volatility(self, indicators: Dict[str, Any]) -> tuple[float, List[str]]:
        """
        Score based on volatility (ATR). Higher score = lower volatility = safer.

        Returns:
            (score 0-100, reasoning list)
        """
        if not indicators:
            return 50.0, ["No volatility data available"]

        atr_pct = indicators.get("atr_pct")
        if atr_pct is None:
            return 50.0, ["ATR data unavailable"]

        # Lower ATR% = higher score (more stable)
        if atr_pct > MAX_ATR_PCT:
            score = 20
            reasoning = [f"Very high volatility (ATR {atr_pct:.1f}%) - dangerous"]
        elif atr_pct > 10:
            score = 50
            reasoning = [f"High volatility (ATR {atr_pct:.1f}%)"]
        elif atr_pct > 5:
            score = 75
            reasoning = [f"Moderate volatility (ATR {atr_pct:.1f}%)"]
        else:
            score = 90
            reasoning = [f"Low volatility (ATR {atr_pct:.1f}%) - stable"]

        return score, reasoning

    def _score_news(self, news_analysis: Optional[Dict[str, Any]]) -> tuple[float, List[str]]:
        """
        Score based on news sentiment analysis.

        Returns:
            (score 0-100, reasoning list)
        """
        if not news_analysis:
            return 50.0, ["No news analysis available"]

        overall_score = news_analysis.get("overall_score", 0)
        aggregate_sentiment = news_analysis.get("aggregate_sentiment", "NEUTRAL")
        confidence = news_analysis.get("confidence", 0)

        # Convert -1 to +1 score to 0-100 scale
        # Positive news = higher score
        normalized_score = (overall_score + 1) * 50  # Maps -1→0, 0→50, +1→100

        # Adjust by confidence
        final_score = normalized_score * confidence + 50 * (1 - confidence)

        reasoning = [f"News sentiment: {aggregate_sentiment} (score {overall_score:.2f}, confidence {confidence:.0%})"]

        return final_score, reasoning

    def _check_criteria(
        self,
        scores: Dict[str, float],
        technical_data: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Check if specific criteria are met.

        Returns:
            Dictionary of criteria pass/fail
        """
        criteria = {}

        # Minimum liquidity
        criteria["min_liquidity"] = scores.get("liquidity", 0) >= 50

        # Volatility within limits
        atr_pct = technical_data.get("atr_pct", 0)
        criteria["volatility_controlled"] = atr_pct <= MAX_ATR_PCT if atr_pct else True

        # Favorable technicals
        criteria["technical_favorable"] = scores.get("technical", 0) >= 55

        # Positive trend
        criteria["trending_positive"] = scores.get("trending", 0) >= 50

        # Overall quality
        overall = (
            scores.get("technical", 0) * 0.3 +
            scores.get("sentiment", 0) * 0.15 +
            scores.get("trending", 0) * 0.2 +
            scores.get("liquidity", 0) * 0.15 +
            scores.get("volatility", 0) * 0.1 +
            scores.get("news", 0) * 0.1
        )
        criteria["overall_quality"] = overall >= 60

        return criteria


# Global evaluator
crypto_evaluator = CryptoEvaluator()


def evaluate_crypto_opportunity(
    symbol: str,
    technical_data: Dict[str, Any],
    sentiment_data: Dict[str, Any],
    trending_data: Optional[Dict[str, Any]] = None,
    news_analysis: Optional[Dict[str, Any]] = None,
    coingecko_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Convenience function to evaluate a crypto opportunity."""
    return crypto_evaluator.evaluate_opportunity(
        symbol, technical_data, sentiment_data, trending_data, news_analysis, coingecko_data
    )
