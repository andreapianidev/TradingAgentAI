"""
Data Weighting Engine - Calcolo weighted scores per decisioni trading.

Questo modulo implementa un sistema di pesi adattivi che calcola score numerici
per ogni tipo di dato (indicatori tecnici, news, whale flow, ecc.) e li aggrega
in un composite score basato sul regime di mercato corrente.
"""
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WeightConfig:
    """Configuration per pesi adattivi basati sul regime di mercato."""
    technical_indicators: float
    pivot_points: float
    forecast: float
    whale_flow: float
    sentiment: float
    news: float
    coingecko: float

    def __post_init__(self):
        """Validate che i pesi sommino a 1.0."""
        total = sum([
            self.technical_indicators,
            self.pivot_points,
            self.forecast,
            self.whale_flow,
            self.sentiment,
            self.news,
            self.coingecko
        ])
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Weight config sum is {total:.3f}, expected 1.0")


# Configurazioni predefinite per diversi regimi di mercato
NORMAL_WEIGHTS = WeightConfig(
    technical_indicators=0.25,
    pivot_points=0.20,
    forecast=0.15,
    whale_flow=0.15,
    sentiment=0.10,
    news=0.10,
    coingecko=0.05
)

HIGH_VOLATILITY_WEIGHTS = WeightConfig(
    technical_indicators=0.30,  # ↑ ATR è critico
    pivot_points=0.25,          # ↑ S/R sono cruciali
    forecast=0.10,              # ↓ meno affidabile in volatilità
    whale_flow=0.20,            # ↑ movimenti grandi importanti
    sentiment=0.10,
    news=0.05,                  # ↓ spesso rumore
    coingecko=0.00              # ↓ non rilevante
)

TRENDING_WEIGHTS = WeightConfig(
    technical_indicators=0.20,
    pivot_points=0.15,
    forecast=0.15,
    whale_flow=0.10,
    sentiment=0.15,             # ↑ sentiment guida trend
    news=0.15,                  # ↑ news-driven spesso
    coingecko=0.10              # ↑ trending signal importante
)

RANGING_WEIGHTS = WeightConfig(
    technical_indicators=0.20,
    pivot_points=0.30,          # ↑ S/R molto importanti in range
    forecast=0.15,
    whale_flow=0.10,
    sentiment=0.10,
    news=0.10,
    coingecko=0.05
)


class DataWeightingEngine:
    """Engine per calcolo weighted scores da tutti i dati di mercato."""

    def __init__(self):
        """Initialize the weighting engine."""
        self.weight_configs = {
            "normal": NORMAL_WEIGHTS,
            "high_volatility": HIGH_VOLATILITY_WEIGHTS,
            "trending": TRENDING_WEIGHTS,
            "ranging": RANGING_WEIGHTS
        }

    def calculate_composite_score(
        self,
        symbol: str,
        indicators: Dict,
        pivot_points: Dict,
        forecast: Dict,
        whale_flow: Dict,
        sentiment: Dict,
        news_analysis: Dict,
        coingecko: Dict,
        market_regime: str = "normal"
    ) -> Dict[str, Any]:
        """
        Calcola composite score da tutti i dati.

        Args:
            symbol: Trading symbol (BTC, ETH, SOL)
            indicators: Technical indicators dict
            pivot_points: Pivot points dict
            forecast: Prophet forecast dict
            whale_flow: Whale capital flow dict
            sentiment: Market sentiment dict
            news_analysis: Advanced news analysis dict
            coingecko: CoinGecko market data dict
            market_regime: Market regime (normal, high_volatility, trending, ranging)

        Returns:
            Dictionary con composite score e breakdown completo
        """
        # Seleziona pesi in base al regime
        weights = self._get_weights_for_regime(market_regime)

        # Calcola score per ogni componente (0.0-1.0)
        tech_score = self._score_technical_indicators(indicators)
        pivot_score = self._score_pivot_points(pivot_points, indicators)
        forecast_score = self._score_forecast(forecast)
        whale_score = self._score_whale_flow(whale_flow)
        sentiment_score = self._score_sentiment(sentiment)
        news_score = news_analysis.get("overall_score", 0.5)  # già calcolato da news_analyzer
        cg_score = self._score_coingecko(symbol, coingecko)

        # Calcola composite score pesato
        composite = (
            tech_score * weights.technical_indicators +
            pivot_score * weights.pivot_points +
            forecast_score * weights.forecast +
            whale_score * weights.whale_flow +
            sentiment_score * weights.sentiment +
            news_score * weights.news +
            cg_score * weights.coingecko
        )

        # Calcola confidence (quanto sono allineati i segnali)
        all_scores = [tech_score, pivot_score, forecast_score, whale_score,
                      sentiment_score, news_score, cg_score]
        confidence = self._calculate_confidence(all_scores)

        return {
            "composite_score": round(composite, 3),
            "confidence": round(confidence, 3),
            "components": {
                "technical_indicators": {
                    "score": round(tech_score, 3),
                    "weight": weights.technical_indicators,
                    "contribution": round(tech_score * weights.technical_indicators, 3),
                    "details": self._get_tech_details(indicators)
                },
                "pivot_points": {
                    "score": round(pivot_score, 3),
                    "weight": weights.pivot_points,
                    "contribution": round(pivot_score * weights.pivot_points, 3),
                    "details": self._get_pivot_details(pivot_points, indicators)
                },
                "forecast": {
                    "score": round(forecast_score, 3),
                    "weight": weights.forecast,
                    "contribution": round(forecast_score * weights.forecast, 3),
                    "details": self._get_forecast_details(forecast)
                },
                "whale_flow": {
                    "score": round(whale_score, 3),
                    "weight": weights.whale_flow,
                    "contribution": round(whale_score * weights.whale_flow, 3),
                    "details": self._get_whale_details(whale_flow)
                },
                "sentiment": {
                    "score": round(sentiment_score, 3),
                    "weight": weights.sentiment,
                    "contribution": round(sentiment_score * weights.sentiment, 3),
                    "details": self._get_sentiment_details(sentiment)
                },
                "news": {
                    "score": round(news_score, 3),
                    "weight": weights.news,
                    "contribution": round(news_score * weights.news, 3),
                    "details": self._get_news_details(news_analysis)
                },
                "coingecko": {
                    "score": round(cg_score, 3),
                    "weight": weights.coingecko,
                    "contribution": round(cg_score * weights.coingecko, 3),
                    "details": self._get_coingecko_details(symbol, coingecko)
                }
            },
            "market_regime": market_regime,
            "weights_used": asdict(weights)
        }

    def _get_weights_for_regime(self, regime: str) -> WeightConfig:
        """Get weight configuration for market regime."""
        return self.weight_configs.get(regime, NORMAL_WEIGHTS)

    def _score_technical_indicators(self, indicators: Dict) -> float:
        """
        Score 0-1 per indicatori tecnici.

        Combina RSI, MACD, EMA per un score composito.
        Score alto (>0.7) = setup bullish forte
        Score basso (<0.3) = setup bearish o debole
        """
        scores = []

        # RSI scoring
        rsi = indicators.get("rsi", 50)
        if 30 <= rsi <= 70:
            rsi_score = 0.8  # zona neutrale è buona (non overbought/oversold)
        elif rsi < 30:
            rsi_score = 0.9  # oversold = opportunità long
        elif rsi > 70:
            rsi_score = 0.2  # overbought = rischio
        else:
            rsi_score = 0.5

        scores.append(rsi_score)

        # MACD scoring
        macd_bullish = indicators.get("macd_bullish", False)
        macd_hist_rising = indicators.get("macd_histogram_rising", False)

        if macd_bullish and macd_hist_rising:
            macd_score = 0.9  # forte momentum bullish
        elif macd_bullish or macd_hist_rising:
            macd_score = 0.7  # momentum moderato
        elif not macd_bullish and not macd_hist_rising:
            macd_score = 0.2  # bearish
        else:
            macd_score = 0.5  # neutro

        scores.append(macd_score)

        # EMA scoring
        price_above_ema20 = indicators.get("price_above_ema20", False)
        ema_score = 0.8 if price_above_ema20 else 0.3

        scores.append(ema_score)

        # Average dei tre indicatori
        return sum(scores) / len(scores)

    def _score_pivot_points(self, pivot_points: Dict, indicators: Dict) -> float:
        """
        Score basato su distanza da pivot e supporti/resistenze.

        Vicino a supporto = buono per long (score alto)
        Vicino a resistenza = non buono per long (score basso)
        """
        distance_pct = abs(pivot_points.get("distance_pct", 0))
        near_support = pivot_points.get("near_support", False)
        near_resistance = pivot_points.get("near_resistance", False)

        # Vicino a supporto = setup ottimale per long
        if near_support:
            return 0.85
        # Vicino a resistenza = setup rischioso per long
        elif near_resistance:
            return 0.30
        # Molto lontano da livelli chiave
        elif distance_pct > 2.0:
            return 0.50
        # Zona neutra
        else:
            return 0.65

    def _score_forecast(self, forecast: Dict) -> float:
        """
        Score basato su Prophet forecast.

        Trend rialzista + alta confidence = score alto
        """
        trend = forecast.get("trend", "LATERALE").upper()
        change_pct = forecast.get("change_pct", 0)
        confidence = forecast.get("confidence", 0.5)

        # Base score dal trend
        if trend == "RIALZISTA":
            base_score = 0.75
        elif trend == "RIBASSISTA":
            base_score = 0.25
        else:  # LATERALE
            base_score = 0.50

        # Adjust per magnitude del change
        if abs(change_pct) > 5:
            magnitude_boost = 0.15
        elif abs(change_pct) > 2:
            magnitude_boost = 0.10
        else:
            magnitude_boost = 0.0

        # Adjust per confidence
        confidence_multiplier = 0.5 + (confidence * 0.5)  # 0.5-1.0

        final_score = (base_score + magnitude_boost) * confidence_multiplier

        return min(1.0, max(0.0, final_score))

    def _score_whale_flow(self, whale_flow: Dict) -> float:
        """
        Score basato su whale capital flow.

        Outflow da exchange (accumulo) = bullish = score alto
        Inflow a exchange (distribuzione) = bearish = score basso
        """
        net_flow = whale_flow.get("net_flow", 0)

        # Net flow positivo = outflow da exchange = bullish
        if net_flow > 20_000_000:
            return 0.90  # Forte accumulo
        elif net_flow > 5_000_000:
            return 0.75  # Accumulo moderato
        elif net_flow > 0:
            return 0.60  # Leggero accumulo
        elif net_flow > -5_000_000:
            return 0.40  # Leggera distribuzione
        elif net_flow > -20_000_000:
            return 0.25  # Distribuzione moderata
        else:
            return 0.10  # Forte distribuzione

    def _score_sentiment(self, sentiment: Dict) -> float:
        """
        Score basato su Fear & Greed Index.

        Extreme Fear = opportunità = score alto
        Extreme Greed = rischio = score basso
        """
        score = sentiment.get("score", 50)
        label = sentiment.get("label", "NEUTRAL")

        # Fear = opportunità di acquisto
        if label == "EXTREME_FEAR" or score <= 10:
            return 0.85
        elif label == "FEAR" or score <= 30:
            return 0.70
        # Neutral
        elif 30 < score < 70:
            return 0.50
        # Greed = rischio
        elif label == "GREED" or score >= 70:
            return 0.30
        elif label == "EXTREME_GREED" or score >= 90:
            return 0.15
        else:
            return 0.50

    def _score_coingecko(self, symbol: str, coingecko: Dict) -> float:
        """
        Score basato su CoinGecko data.

        Factors:
        - Coin in trending
        - BTC dominance (per altcoin)
        - Market cap change
        """
        if not coingecko or not coingecko.get("global"):
            return 0.50

        score = 0.50  # base

        # Check se coin è trending
        tracked_trending = coingecko.get("tracked_trending", [])
        if symbol in tracked_trending:
            score += 0.25  # boost significativo

        # BTC dominance (solo per altcoin)
        if symbol != "BTC":
            global_data = coingecko.get("global", {})
            btc_dom = global_data.get("btc_dominance", 50)

            # BTC dominance alta = risk-off, prefer BTC
            # BTC dominance bassa = altcoin season
            if btc_dom < 45:
                score += 0.15  # altcoin favoriti
            elif btc_dom > 55:
                score -= 0.15  # BTC favorito

        # Market cap change 24h
        global_data = coingecko.get("global", {})
        mc_change = global_data.get("market_cap_change_24h_pct", 0)

        if mc_change > 2:
            score += 0.10  # mercato in crescita
        elif mc_change < -2:
            score -= 0.10  # mercato in calo

        return min(1.0, max(0.0, score))

    def _calculate_confidence(self, scores: List[float]) -> float:
        """
        Calcola confidence basato su alignment dei segnali.

        Se tutti i segnali sono allineati (tutti alti o tutti bassi) = alta confidence
        Se i segnali sono contrastanti = bassa confidence
        """
        if not scores:
            return 0.5

        # Calcola variance e mean
        mean = sum(scores) / len(scores)

        # Calcola deviazione standard
        variance = sum((x - mean) ** 2 for x in scores) / len(scores)
        std_dev = variance ** 0.5

        # Confidence alta quando std_dev è bassa (segnali allineati)
        # std_dev max teorica è ~0.5 (tutti 0 o tutti 1)
        confidence = 1.0 - (std_dev / 0.5)

        return max(0.0, min(1.0, confidence))

    def determine_market_regime(
        self,
        indicators: Dict,
        coingecko: Dict,
        whale_flow: Dict
    ) -> str:
        """
        Determina il regime di mercato corrente.

        Returns:
            "normal" | "high_volatility" | "trending" | "ranging"
        """
        volatility_ratio = indicators.get("volatility_ratio", 1.0)

        # Alta volatilità (priorità massima)
        if volatility_ratio > 1.3:
            logger.debug(f"Market regime: high_volatility (ratio={volatility_ratio:.2f})")
            return "high_volatility"

        # Trending (coin in trending CoinGecko)
        tracked_trending = coingecko.get("tracked_trending", [])
        if tracked_trending:
            logger.debug(f"Market regime: trending (coins: {tracked_trending})")
            return "trending"

        # Ranging (MACD flat, RSI neutro, bassa volatilità)
        rsi = indicators.get("rsi", 50)
        macd_hist = abs(indicators.get("macd_histogram", 0))
        if 40 <= rsi <= 60 and macd_hist < 0.0001 and volatility_ratio < 0.9:
            logger.debug(f"Market regime: ranging (RSI={rsi:.1f}, MACD_hist={macd_hist:.6f})")
            return "ranging"

        # Default: normal
        logger.debug(f"Market regime: normal (volatility_ratio={volatility_ratio:.2f})")
        return "normal"

    # Helper methods per details
    def _get_tech_details(self, indicators: Dict) -> Dict[str, Any]:
        """Get technical indicators details."""
        return {
            "rsi": f"{indicators.get('rsi', 50):.1f}",
            "macd_trend": "bullish" if indicators.get("macd_bullish") else "bearish",
            "price_vs_ema20": "above" if indicators.get("price_above_ema20") else "below"
        }

    def _get_pivot_details(self, pivot_points: Dict, indicators: Dict) -> Dict[str, Any]:
        """Get pivot points details."""
        price = indicators.get("ema20", 0)  # use EMA20 as proxy for current price
        return {
            "near_support": pivot_points.get("near_support", False),
            "near_resistance": pivot_points.get("near_resistance", False),
            "distance_from_pp": f"{pivot_points.get('distance_pct', 0):.2f}%"
        }

    def _get_forecast_details(self, forecast: Dict) -> Dict[str, Any]:
        """Get forecast details."""
        return {
            "trend": forecast.get("trend", "N/A"),
            "change": f"{forecast.get('change_pct', 0):+.2f}%",
            "confidence": f"{forecast.get('confidence', 0):.1%}"
        }

    def _get_whale_details(self, whale_flow: Dict) -> Dict[str, Any]:
        """Get whale flow details."""
        net = whale_flow.get("net_flow", 0)
        return {
            "net_flow": f"${net:,.0f}",
            "interpretation": whale_flow.get("interpretation", "N/A"),
            "alert_count": whale_flow.get("alert_count", 0)
        }

    def _get_sentiment_details(self, sentiment: Dict) -> Dict[str, Any]:
        """Get sentiment details."""
        return {
            "score": sentiment.get("score", 50),
            "label": sentiment.get("label", "NEUTRAL")
        }

    def _get_news_details(self, news_analysis: Dict) -> Dict[str, Any]:
        """Get news analysis details."""
        return {
            "aggregate_sentiment": news_analysis.get("aggregate_sentiment", "neutral"),
            "relevance": f"{news_analysis.get('relevance_score', 0):.2f}",
            "impact": f"{news_analysis.get('impact_score', 0):.2f}"
        }

    def _get_coingecko_details(self, symbol: str, coingecko: Dict) -> Dict[str, Any]:
        """Get CoinGecko details."""
        tracked_trending = coingecko.get("tracked_trending", [])
        is_trending = symbol in tracked_trending

        global_data = coingecko.get("global", {})
        btc_dom = global_data.get("btc_dominance", 0)

        return {
            "is_trending": is_trending,
            "btc_dominance": f"{btc_dom:.1f}%",
            "market_cap_change_24h": f"{global_data.get('market_cap_change_24h_pct', 0):+.2f}%"
        }


# Global instance
weighting_engine = DataWeightingEngine()
