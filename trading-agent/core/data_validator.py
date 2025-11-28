"""
Data Quality Validator - Valida completezza e qualità dei dati di mercato.

Questo modulo verifica che tutti i dati necessari per le decisioni trading
siano presenti, completi e non stale. Fornisce un report di qualità che
viene passato a DeepSeek per informarlo di eventuali limitazioni nei dati.
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta

from utils.logger import get_logger

logger = get_logger(__name__)


class DataQualityValidator:
    """Validates data quality and completeness."""

    # Required fields per ogni tipo di dato
    REQUIRED_FIELDS = {
        "market_data": ["price", "volume_24h", "bid", "ask"],
        "indicators": ["rsi", "macd", "macd_signal", "ema2", "ema20", "atr"],
        "pivot_points": ["pp", "r1", "r2", "s1", "s2"],
        "forecast": ["trend", "target_price", "change_pct"],
        "orderbook": ["bid_volume", "ask_volume", "ratio"],
        "sentiment": ["score", "label"],
        "whale_flow": ["net_flow", "interpretation"],
        "coingecko": ["global"]
    }

    # Max age in seconds prima che il dato sia considerato stale
    # Nota: per ora non implementato (assumiamo dati fresh dal ciclo)
    MAX_AGE = {
        "market_data": 60,     # 1 minuto
        "news": 600,           # 10 minuti
        "sentiment": 3600,     # 1 ora
        "whale_flow": 1800,    # 30 minuti
        "coingecko": 300       # 5 minuti
    }

    def validate_all_data(
        self,
        market_data: Dict,
        indicators: Dict,
        pivot_points: Dict,
        forecast: Dict,
        orderbook: Dict,
        sentiment: Dict,
        news: List,
        whale_flow: Dict,
        coingecko: Dict
    ) -> Dict[str, Any]:
        """
        Valida tutti i dati e ritorna report di qualità.

        Args:
            market_data: Market data dict
            indicators: Technical indicators dict
            pivot_points: Pivot points dict
            forecast: Prophet forecast dict
            orderbook: Order book dict
            sentiment: Market sentiment dict
            news: List of news items
            whale_flow: Whale capital flow dict
            coingecko: CoinGecko data dict

        Returns:
            Quality report con score aggregato, warnings e recommendation
        """
        completeness = {}
        staleness = {}
        warnings = []

        # Validate market data
        completeness["market_data"] = self._check_completeness(
            market_data, self.REQUIRED_FIELDS["market_data"], "market_data"
        )

        # Validate indicators
        completeness["indicators"] = self._check_completeness(
            indicators, self.REQUIRED_FIELDS["indicators"], "indicators"
        )

        # Validate pivot points
        completeness["pivot_points"] = self._check_completeness(
            pivot_points, self.REQUIRED_FIELDS["pivot_points"], "pivot_points"
        )

        # Validate forecast
        completeness["forecast"] = self._check_completeness(
            forecast, self.REQUIRED_FIELDS["forecast"], "forecast"
        )

        # Validate orderbook
        completeness["orderbook"] = self._check_completeness(
            orderbook, self.REQUIRED_FIELDS["orderbook"], "orderbook"
        )

        # Validate sentiment
        completeness["sentiment"] = self._check_completeness(
            sentiment, self.REQUIRED_FIELDS["sentiment"], "sentiment"
        )

        # Validate news (special case: count-based)
        if not news or len(news) < 3:
            completeness["news"] = {
                "complete": True,
                "score": 0.6 if news else 0.3,
                "note": f"Only {len(news)} news articles found"
            }
            if len(news) == 0:
                warnings.append("No news data available - sentiment analysis will be limited")
            else:
                warnings.append(f"Limited news data ({len(news)} articles) - sentiment analysis may be less reliable")
        else:
            completeness["news"] = {"complete": True, "score": 1.0}

        # Validate whale flow
        whale_complete = self._check_completeness(
            whale_flow, self.REQUIRED_FIELDS["whale_flow"], "whale_flow"
        )
        completeness["whale_flow"] = whale_complete

        if not whale_complete["complete"]:
            warnings.append("Whale flow data unavailable - decisions will proceed without whale analysis")

        # Validate CoinGecko
        cg_complete = self._check_completeness(
            coingecko, self.REQUIRED_FIELDS["coingecko"], "coingecko"
        )
        completeness["coingecko"] = cg_complete

        if not cg_complete["complete"]:
            warnings.append("CoinGecko data unavailable - market context will be limited")

        # Check staleness (implementazione futura)
        # Per ora assumiamo che tutti i dati siano fresh visto che vengono
        # fetchati nello stesso ciclo

        # Calculate overall quality score
        scores = [c.get("score", 0) for c in completeness.values()]
        overall_quality = sum(scores) / len(scores) if scores else 0

        # Recommendation
        if overall_quality >= 0.9:
            recommendation = "HIGH_QUALITY"
        elif overall_quality >= 0.7:
            recommendation = "ACCEPTABLE"
        else:
            recommendation = "LOW_QUALITY"
            warnings.append("Overall data quality is LOW - consider waiting for better data before trading")

        return {
            "overall_quality": round(overall_quality, 3),
            "completeness": completeness,
            "staleness": staleness,  # vuoto per ora
            "warnings": warnings,
            "recommendation": recommendation,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _check_completeness(
        self,
        data: Dict,
        required_fields: List[str],
        data_type: str
    ) -> Dict[str, Any]:
        """
        Check se tutti i campi richiesti sono presenti e validi.

        Args:
            data: Data dictionary da validare
            required_fields: Lista di campi required
            data_type: Nome tipo di dato (per logging)

        Returns:
            Completeness report con score e campi missing/invalid
        """
        if not data:
            logger.debug(f"Data validation: {data_type} is empty")
            return {
                "complete": False,
                "score": 0.0,
                "missing_fields": required_fields,
                "note": f"{data_type} is empty"
            }

        missing = []
        invalid = []

        for field in required_fields:
            value = data.get(field)

            if value is None:
                missing.append(field)
            elif isinstance(value, (int, float)):
                # Numeri: 0 potrebbe essere valido (es. MACD=0, net_flow=0)
                # Solo NaN o infinito sono invalidi
                if value != value or abs(value) == float('inf'):  # NaN check
                    invalid.append(field)
            elif isinstance(value, str) and not value:
                # Stringhe vuote sono invalide
                invalid.append(field)
            elif isinstance(value, dict) and not value:
                # Dict vuoti sono invalidi
                invalid.append(field)

        complete = len(missing) == 0 and len(invalid) == 0

        # Calculate score (percentage di campi validi)
        total_fields = len(required_fields)
        valid_fields = total_fields - len(missing) - len(invalid)
        score = valid_fields / total_fields if total_fields > 0 else 0.0

        result = {
            "complete": complete,
            "score": max(0.0, min(1.0, score))
        }

        if missing:
            result["missing_fields"] = missing
            logger.debug(f"Data validation: {data_type} missing fields: {missing}")

        if invalid:
            result["invalid_fields"] = invalid
            logger.debug(f"Data validation: {data_type} invalid fields: {invalid}")

        if not complete:
            result["note"] = f"{data_type} has {len(missing)} missing and {len(invalid)} invalid fields"

        return result

    def get_quality_summary(self, validation_result: Dict[str, Any]) -> str:
        """
        Get human-readable summary of data quality.

        Args:
            validation_result: Result from validate_all_data()

        Returns:
            Summary string
        """
        quality = validation_result.get("overall_quality", 0)
        recommendation = validation_result.get("recommendation", "UNKNOWN")
        warnings_count = len(validation_result.get("warnings", []))

        summary = f"Data Quality: {quality:.1%} ({recommendation})"
        if warnings_count > 0:
            summary += f" - {warnings_count} warning(s)"

        return summary

    def has_critical_issues(self, validation_result: Dict[str, Any]) -> bool:
        """
        Check se ci sono problemi critici che dovrebbero impedire trading.

        Args:
            validation_result: Result from validate_all_data()

        Returns:
            True se ci sono problemi critici
        """
        # Critico se:
        # 1. Overall quality < 0.5
        # 2. Market data o indicators incompleti
        quality = validation_result.get("overall_quality", 0)
        if quality < 0.5:
            return True

        completeness = validation_result.get("completeness", {})

        # Market data e indicators sono critici
        critical_components = ["market_data", "indicators"]
        for component in critical_components:
            comp_data = completeness.get(component, {})
            if not comp_data.get("complete", False):
                return True

        return False


# Global instance
data_validator = DataQualityValidator()
