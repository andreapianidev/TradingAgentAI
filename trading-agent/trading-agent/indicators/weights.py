"""
Indicator weights and signal scoring system.
"""
from typing import Dict, Any

from config.constants import INDICATOR_WEIGHTS
from utils.logger import get_logger

logger = get_logger(__name__)


class SignalScorer:
    """Score trading signals based on weighted indicators."""

    def __init__(self, weights: Dict[str, float] = None):
        """
        Initialize with indicator weights.

        Args:
            weights: Custom weights (defaults to INDICATOR_WEIGHTS)
        """
        self.weights = weights or INDICATOR_WEIGHTS

    def score_bullish_signals(
        self,
        indicators: Dict[str, Any],
        pivot_points: Dict[str, Any],
        forecast: Dict[str, Any],
        orderbook: Dict[str, Any],
        sentiment: Dict[str, Any]
    ) -> float:
        """
        Calculate bullish signal score.

        Returns:
            Score from 0 to 1 indicating bullish strength
        """
        scores = []

        # MACD Signal (weight: 0.7)
        macd_score = 0
        if indicators.get("macd_bullish"):
            macd_score = 0.7
        if indicators.get("macd_histogram_rising"):
            macd_score = min(1.0, macd_score + 0.3)
        scores.append(("macd", macd_score, self.weights["macd"]))

        # RSI Signal (weight: 0.7)
        rsi = indicators.get("rsi", 50)
        rsi_score = 0
        if rsi < 30:  # Oversold = bullish
            rsi_score = 1.0
        elif rsi < 50:
            rsi_score = 0.6
        elif rsi < 70:
            rsi_score = 0.3
        # RSI > 70 = overbought, not bullish
        scores.append(("rsi", rsi_score, self.weights["rsi"]))

        # Pivot Points Signal (weight: 0.8)
        pivot_score = 0
        if pivot_points.get("near_support"):
            pivot_score = 0.9  # Near support is bullish
        elif pivot_points.get("position") in ["between_s1_pp", "between_pp_r1"]:
            pivot_score = 0.5
        scores.append(("pivot_points", pivot_score, self.weights["pivot_points"]))

        # Forecast Signal (weight: 0.6)
        forecast_score = 0
        if forecast.get("trend") == "RIALZISTA":
            confidence = forecast.get("confidence", 0)
            forecast_score = confidence
        elif forecast.get("trend") == "LATERALE":
            forecast_score = 0.3
        scores.append(("forecast", forecast_score, self.weights["forecast"]))

        # Order Book Signal (weight: 0.5)
        orderbook_score = 0
        ratio = orderbook.get("ratio", 1.0)
        if ratio > 1.2:
            orderbook_score = 0.8
        elif ratio > 1.0:
            orderbook_score = 0.5
        scores.append(("orderbook", orderbook_score, self.weights["orderbook"]))

        # Sentiment Signal (weight: 0.4)
        sentiment_score = 0
        sent_label = sentiment.get("label", "NEUTRAL")
        if sent_label == "FEAR":
            sentiment_score = 0.7  # Contrarian: fear can be bullish
        elif sent_label == "NEUTRAL":
            sentiment_score = 0.4
        scores.append(("sentiment", sentiment_score, self.weights["sentiment"]))

        # Calculate weighted average
        total_weight = sum(w for _, _, w in scores)
        weighted_sum = sum(score * weight for _, score, weight in scores)

        return weighted_sum / total_weight if total_weight > 0 else 0

    def score_bearish_signals(
        self,
        indicators: Dict[str, Any],
        pivot_points: Dict[str, Any],
        forecast: Dict[str, Any],
        orderbook: Dict[str, Any],
        sentiment: Dict[str, Any]
    ) -> float:
        """
        Calculate bearish signal score.

        Returns:
            Score from 0 to 1 indicating bearish strength
        """
        scores = []

        # MACD Signal
        macd_score = 0
        if not indicators.get("macd_bullish"):
            macd_score = 0.7
        if indicators.get("macd_histogram", 0) < 0:
            histogram = indicators.get("macd_histogram", 0)
            if histogram < -0.1:  # Negative and decreasing
                macd_score = min(1.0, macd_score + 0.3)
        scores.append(("macd", macd_score, self.weights["macd"]))

        # RSI Signal
        rsi = indicators.get("rsi", 50)
        rsi_score = 0
        if rsi > 70:  # Overbought = bearish
            rsi_score = 1.0
        elif rsi > 50:
            rsi_score = 0.6
        elif rsi > 30:
            rsi_score = 0.3
        scores.append(("rsi", rsi_score, self.weights["rsi"]))

        # Pivot Points Signal
        pivot_score = 0
        if pivot_points.get("near_resistance"):
            pivot_score = 0.9  # Near resistance is bearish
        elif pivot_points.get("position") in ["between_r1_r2", "above_r2"]:
            pivot_score = 0.5
        scores.append(("pivot_points", pivot_score, self.weights["pivot_points"]))

        # Forecast Signal
        forecast_score = 0
        if forecast.get("trend") == "RIBASSISTA":
            confidence = forecast.get("confidence", 0)
            forecast_score = confidence
        elif forecast.get("trend") == "LATERALE":
            forecast_score = 0.3
        scores.append(("forecast", forecast_score, self.weights["forecast"]))

        # Order Book Signal
        orderbook_score = 0
        ratio = orderbook.get("ratio", 1.0)
        if ratio < 0.8:
            orderbook_score = 0.8
        elif ratio < 1.0:
            orderbook_score = 0.5
        scores.append(("orderbook", orderbook_score, self.weights["orderbook"]))

        # Sentiment Signal
        sentiment_score = 0
        sent_label = sentiment.get("label", "NEUTRAL")
        if sent_label == "GREED":
            sentiment_score = 0.7  # Contrarian: greed can be bearish
        elif sent_label == "NEUTRAL":
            sentiment_score = 0.4
        scores.append(("sentiment", sentiment_score, self.weights["sentiment"]))

        # Calculate weighted average
        total_weight = sum(w for _, _, w in scores)
        weighted_sum = sum(score * weight for _, score, weight in scores)

        return weighted_sum / total_weight if total_weight > 0 else 0

    def get_signal_summary(
        self,
        indicators: Dict[str, Any],
        pivot_points: Dict[str, Any],
        forecast: Dict[str, Any],
        orderbook: Dict[str, Any],
        sentiment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get comprehensive signal summary.

        Returns:
            Summary with bullish/bearish scores and recommendation
        """
        bullish_score = self.score_bullish_signals(
            indicators, pivot_points, forecast, orderbook, sentiment
        )
        bearish_score = self.score_bearish_signals(
            indicators, pivot_points, forecast, orderbook, sentiment
        )

        # Determine net signal
        net_score = bullish_score - bearish_score

        if net_score > 0.2:
            direction = "bullish"
            strength = bullish_score
        elif net_score < -0.2:
            direction = "bearish"
            strength = bearish_score
        else:
            direction = "neutral"
            strength = max(bullish_score, bearish_score)

        return {
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "net_score": net_score,
            "direction": direction,
            "strength": strength,
        }


# Global scorer instance
signal_scorer = SignalScorer()
