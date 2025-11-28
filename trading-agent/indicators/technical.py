"""
Technical indicators calculation using pandas.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from config.constants import (
    MACD_FAST_PERIOD, MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD,
    RSI_PERIOD, EMA_SHORT_PERIOD, EMA_LONG_PERIOD,
    VOLUME_SMA_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD
)
from utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """Calculate technical indicators from OHLCV data."""

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

        # Ensure numeric types
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def calculate_all(self) -> Dict[str, Any]:
        """
        Calculate all technical indicators.

        Returns:
            Dictionary with all indicator values
        """
        if self.df.empty:
            logger.warning("Empty DataFrame, cannot calculate indicators")
            return self._empty_indicators()

        try:
            macd = self.calculate_macd()
            rsi = self.calculate_rsi()
            ema2 = self.calculate_ema(EMA_SHORT_PERIOD)
            ema20 = self.calculate_ema(EMA_LONG_PERIOD)
            volume_sma = self.calculate_volume_sma()

            # Calculate ATR for volatility analysis
            atr_14 = self.calculate_atr(period=14)
            atr_30 = self.calculate_atr(period=30)

            # Get latest values
            latest_close = float(self.df["close"].iloc[-1])

            # Calculate ATR as percentage of price
            atr_pct = (atr_14 / latest_close * 100) if atr_14 > 0 and latest_close > 0 else None

            # Calculate volatility ratio (current vs average)
            volatility_ratio = (atr_14 / atr_30) if atr_14 > 0 and atr_30 > 0 else 1.0

            return {
                "macd": macd["macd"],
                "macd_signal": macd["signal"],
                "macd_histogram": macd["histogram"],
                "rsi": rsi,
                "ema2": ema2,
                "ema20": ema20,
                "volume_sma": volume_sma,
                "price": latest_close,
                # ATR volatility indicators
                "atr": atr_14,
                "atr_30": atr_30,
                "atr_pct": atr_pct,
                "volatility_ratio": volatility_ratio,
                # Additional analysis
                "macd_bullish": macd["macd"] > macd["signal"],
                "macd_histogram_rising": self._is_histogram_rising(macd),
                "rsi_overbought": rsi > RSI_OVERBOUGHT,
                "rsi_oversold": rsi < RSI_OVERSOLD,
                "price_above_ema20": latest_close > ema20 if ema20 else False,
            }

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return self._empty_indicators()

    def _empty_indicators(self) -> Dict[str, Any]:
        """Return empty indicator values - None indicates data not available."""
        return {
            "macd": None,
            "macd_signal": None,
            "macd_histogram": None,
            "rsi": None,  # None instead of fake 50 value
            "ema2": None,
            "ema20": None,
            "volume_sma": None,
            "price": None,
            "atr": None,
            "atr_30": None,
            "atr_pct": None,
            "volatility_ratio": 1.0,  # Default to 1.0 (normal)
            "macd_bullish": None,
            "macd_histogram_rising": None,
            "rsi_overbought": None,
            "rsi_oversold": None,
            "price_above_ema20": None,
        }

    def calculate_macd(
        self,
        fast: int = MACD_FAST_PERIOD,
        slow: int = MACD_SLOW_PERIOD,
        signal: int = MACD_SIGNAL_PERIOD
    ) -> Dict[str, Any]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Args:
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)

        Returns:
            Dictionary with macd, signal, histogram values (None if insufficient data)
        """
        if len(self.df) < slow:
            return {"macd": None, "signal": None, "histogram": None}

        close = self.df["close"]

        # Calculate EMAs
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()

        # MACD line
        macd_line = ema_fast - ema_slow

        # Signal line
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()

        # Histogram
        histogram = macd_line - signal_line

        return {
            "macd": float(macd_line.iloc[-1]),
            "signal": float(signal_line.iloc[-1]),
            "histogram": float(histogram.iloc[-1]),
            "macd_series": macd_line,
            "signal_series": signal_line,
            "histogram_series": histogram,
        }

    def _is_histogram_rising(self, macd_data: Dict) -> bool:
        """Check if MACD histogram is rising."""
        if "histogram_series" not in macd_data:
            return False

        histogram = macd_data["histogram_series"]
        if len(histogram) < 3:
            return False

        # Check last 3 values for rising trend
        return histogram.iloc[-1] > histogram.iloc[-2] > histogram.iloc[-3]

    def calculate_rsi(self, period: int = RSI_PERIOD) -> Optional[float]:
        """
        Calculate RSI (Relative Strength Index).

        Args:
            period: RSI period (default 14)

        Returns:
            RSI value (0-100) or None if insufficient data
        """
        if len(self.df) < period + 1:
            return None  # Return None instead of fake neutral value

        close = self.df["close"]

        # Calculate price changes
        delta = close.diff()

        # Separate gains and losses
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)

        # Calculate average gains and losses
        avg_gain = gains.rolling(window=period).mean()
        avg_loss = losses.rolling(window=period).mean()

        # Calculate RS
        rs = avg_gain / avg_loss

        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))

        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None

    def calculate_ema(self, period: int) -> float:
        """
        Calculate Exponential Moving Average.

        Args:
            period: EMA period

        Returns:
            EMA value
        """
        if len(self.df) < period:
            return float(self.df["close"].iloc[-1]) if len(self.df) > 0 else 0

        ema = self.df["close"].ewm(span=period, adjust=False).mean()
        return float(ema.iloc[-1])

    def calculate_sma(self, period: int) -> float:
        """
        Calculate Simple Moving Average.

        Args:
            period: SMA period

        Returns:
            SMA value
        """
        if len(self.df) < period:
            return float(self.df["close"].iloc[-1]) if len(self.df) > 0 else 0

        sma = self.df["close"].rolling(window=period).mean()
        return float(sma.iloc[-1])

    def calculate_volume_sma(self, period: int = VOLUME_SMA_PERIOD) -> float:
        """
        Calculate Volume Simple Moving Average.

        Args:
            period: SMA period

        Returns:
            Volume SMA value
        """
        if len(self.df) < period:
            return float(self.df["volume"].mean()) if len(self.df) > 0 else 0

        volume_sma = self.df["volume"].rolling(window=period).mean()
        return float(volume_sma.iloc[-1])

    def calculate_bollinger_bands(
        self,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, float]:
        """
        Calculate Bollinger Bands.

        Args:
            period: Moving average period
            std_dev: Standard deviation multiplier

        Returns:
            Dictionary with upper, middle, lower bands
        """
        if len(self.df) < period:
            price = float(self.df["close"].iloc[-1]) if len(self.df) > 0 else 0
            return {"upper": price, "middle": price, "lower": price}

        close = self.df["close"]
        sma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        return {
            "upper": float(upper.iloc[-1]),
            "middle": float(sma.iloc[-1]),
            "lower": float(lower.iloc[-1]),
        }

    def calculate_atr(self, period: int = 14) -> float:
        """
        Calculate Average True Range.

        Args:
            period: ATR period

        Returns:
            ATR value
        """
        if len(self.df) < period + 1:
            return 0

        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]

        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Calculate ATR
        atr = tr.rolling(window=period).mean()

        return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0

    def get_ohlcv_for_forecast(self) -> pd.DataFrame:
        """
        Get OHLCV data formatted for Prophet forecasting.

        Returns:
            DataFrame with 'ds' and 'y' columns
        """
        if self.df.empty:
            return pd.DataFrame(columns=["ds", "y"])

        forecast_df = pd.DataFrame({
            "ds": self.df.index,
            "y": self.df["close"].values
        })

        return forecast_df


def calculate_indicators(ohlcv_data: List[List]) -> Dict[str, Any]:
    """
    Convenience function to calculate all indicators.

    Args:
        ohlcv_data: OHLCV candlestick data

    Returns:
        Dictionary with all indicator values
    """
    calculator = TechnicalIndicators(ohlcv_data)
    return calculator.calculate_all()
