"""
Pivot Points calculation for support and resistance levels.
"""
from typing import Dict, Any, List
import pandas as pd

from config.constants import (
    PIVOT_NEAR_RESISTANCE_THRESHOLD,
    PIVOT_NEAR_SUPPORT_THRESHOLD
)
from utils.logger import get_logger

logger = get_logger(__name__)


class PivotPointsCalculator:
    """Calculate pivot points and support/resistance levels."""

    def __init__(self, ohlcv_data: List[List]):
        """
        Initialize with OHLCV data.

        Args:
            ohlcv_data: List of [timestamp, open, high, low, close, volume]
        """
        self.df = self._create_dataframe(ohlcv_data)

    def _create_dataframe(self, ohlcv_data: List[List]) -> pd.DataFrame:
        """Convert OHLCV list to pandas DataFrame."""
        if not ohlcv_data:
            return pd.DataFrame()

        df = pd.DataFrame(
            ohlcv_data,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def calculate_standard(self) -> Dict[str, Any]:
        """
        Calculate Standard Pivot Points.

        Uses the last completed candle for calculation.

        Returns:
            Dictionary with PP, R1, R2, S1, S2 and analysis
        """
        if len(self.df) < 2:
            return self._empty_pivots()

        # Use the second-to-last candle (last completed)
        last_candle = self.df.iloc[-2]
        current_price = float(self.df["close"].iloc[-1])

        high = float(last_candle["high"])
        low = float(last_candle["low"])
        close = float(last_candle["close"])

        # Calculate Pivot Point
        pp = (high + low + close) / 3

        # Calculate Resistance levels
        r1 = (2 * pp) - low
        r2 = pp + (high - low)

        # Calculate Support levels
        s1 = (2 * pp) - high
        s2 = pp - (high - low)

        # Calculate distance from PP
        distance_pct = ((current_price - pp) / pp) * 100 if pp > 0 else 0

        # Check proximity to levels
        near_resistance = self._check_near_resistance(current_price, r1, r2)
        near_support = self._check_near_support(current_price, s1, s2)

        # Determine position interpretation
        position = self._interpret_position(
            current_price, pp, r1, r2, s1, s2
        )

        return {
            "pp": pp,
            "r1": r1,
            "r2": r2,
            "s1": s1,
            "s2": s2,
            "current_price": current_price,
            "distance_pct": distance_pct,
            "near_resistance": near_resistance,
            "near_support": near_support,
            "position": position,
        }

    def calculate_fibonacci(self) -> Dict[str, Any]:
        """
        Calculate Fibonacci Pivot Points.

        Returns:
            Dictionary with PP and Fibonacci-based levels
        """
        if len(self.df) < 2:
            return self._empty_pivots()

        last_candle = self.df.iloc[-2]
        current_price = float(self.df["close"].iloc[-1])

        high = float(last_candle["high"])
        low = float(last_candle["low"])
        close = float(last_candle["close"])

        # Pivot Point
        pp = (high + low + close) / 3

        # Range
        range_hl = high - low

        # Fibonacci levels
        r1 = pp + (0.382 * range_hl)
        r2 = pp + (0.618 * range_hl)
        r3 = pp + range_hl

        s1 = pp - (0.382 * range_hl)
        s2 = pp - (0.618 * range_hl)
        s3 = pp - range_hl

        return {
            "pp": pp,
            "r1": r1,
            "r2": r2,
            "r3": r3,
            "s1": s1,
            "s2": s2,
            "s3": s3,
            "current_price": current_price,
        }

    def calculate_camarilla(self) -> Dict[str, Any]:
        """
        Calculate Camarilla Pivot Points.

        Returns:
            Dictionary with Camarilla pivot levels
        """
        if len(self.df) < 2:
            return self._empty_pivots()

        last_candle = self.df.iloc[-2]
        current_price = float(self.df["close"].iloc[-1])

        high = float(last_candle["high"])
        low = float(last_candle["low"])
        close = float(last_candle["close"])

        range_hl = high - low

        # Camarilla levels
        r4 = close + (range_hl * 1.1 / 2)
        r3 = close + (range_hl * 1.1 / 4)
        r2 = close + (range_hl * 1.1 / 6)
        r1 = close + (range_hl * 1.1 / 12)

        s1 = close - (range_hl * 1.1 / 12)
        s2 = close - (range_hl * 1.1 / 6)
        s3 = close - (range_hl * 1.1 / 4)
        s4 = close - (range_hl * 1.1 / 2)

        return {
            "r4": r4,
            "r3": r3,
            "r2": r2,
            "r1": r1,
            "s1": s1,
            "s2": s2,
            "s3": s3,
            "s4": s4,
            "current_price": current_price,
        }

    def _empty_pivots(self) -> Dict[str, Any]:
        """Return empty pivot values."""
        return {
            "pp": 0,
            "r1": 0,
            "r2": 0,
            "s1": 0,
            "s2": 0,
            "current_price": 0,
            "distance_pct": 0,
            "near_resistance": False,
            "near_support": False,
            "position": "unknown",
        }

    def _check_near_resistance(
        self,
        price: float,
        r1: float,
        r2: float
    ) -> bool:
        """Check if price is near resistance levels."""
        # Price is near R1 or R2 if within 1%
        near_r1 = price >= r1 * PIVOT_NEAR_RESISTANCE_THRESHOLD
        near_r2 = price >= r2 * PIVOT_NEAR_RESISTANCE_THRESHOLD

        return near_r1 or near_r2

    def _check_near_support(
        self,
        price: float,
        s1: float,
        s2: float
    ) -> bool:
        """Check if price is near support levels."""
        # Price is near S1 or S2 if within 1%
        near_s1 = price <= s1 * PIVOT_NEAR_SUPPORT_THRESHOLD
        near_s2 = price <= s2 * PIVOT_NEAR_SUPPORT_THRESHOLD

        return near_s1 or near_s2

    def _interpret_position(
        self,
        price: float,
        pp: float,
        r1: float,
        r2: float,
        s1: float,
        s2: float
    ) -> str:
        """
        Interpret current price position relative to pivot levels.

        Returns:
            Position description string
        """
        if price > r2:
            return "above_r2"
        elif price > r1:
            return "between_r1_r2"
        elif price > pp:
            return "between_pp_r1"
        elif price > s1:
            return "between_s1_pp"
        elif price > s2:
            return "between_s1_s2"
        else:
            return "below_s2"


def calculate_pivot_points(ohlcv_data: List[List]) -> Dict[str, Any]:
    """
    Convenience function to calculate standard pivot points.

    Args:
        ohlcv_data: OHLCV candlestick data

    Returns:
        Dictionary with pivot point values
    """
    calculator = PivotPointsCalculator(ohlcv_data)
    return calculator.calculate_standard()
