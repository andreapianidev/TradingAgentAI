"""
Prophet-based price forecasting.
"""
import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import warnings

import pandas as pd
import numpy as np

from config.constants import (
    PROPHET_FORECAST_PERIODS,
    PROPHET_RETRAIN_CYCLES,
    FORECAST_BULLISH_THRESHOLD,
    FORECAST_BEARISH_THRESHOLD
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Suppress Prophet warnings
warnings.filterwarnings("ignore", category=FutureWarning)


class ProphetForecaster:
    """Price forecasting using Meta's Prophet."""

    def __init__(self, symbol: str):
        """
        Initialize forecaster for a symbol.

        Args:
            symbol: Trading symbol (BTC, ETH, SOL)
        """
        self.symbol = symbol
        self.model = None
        self._cycle_count = 0
        self._last_train_time = None
        self._has_regressors = False
        self._model_dir = Path("models")
        self._model_dir.mkdir(exist_ok=True)

    def train(self, df: pd.DataFrame) -> bool:
        """
        Train Prophet model on historical data.

        Args:
            df: DataFrame with 'ds' (datetime) and 'y' (price) columns

        Returns:
            True if training successful
        """
        try:
            from prophet import Prophet

            if df.empty or len(df) < 30:
                logger.warning(f"Insufficient data for Prophet training: {len(df)} rows")
                return False

            # Initialize Prophet with optimized parameters for crypto
            self.model = Prophet(
                changepoint_prior_scale=0.05,  # More conservative
                seasonality_prior_scale=0.1,
                seasonality_mode='multiplicative',
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=False,  # Crypto doesn't have yearly patterns
                interval_width=0.95,  # 95% confidence interval
            )

            # Add custom seasonality for crypto (4-hour cycles are common)
            self.model.add_seasonality(
                name='intraday',
                period=0.25,  # 6 hours
                fourier_order=3
            )

            # Fit the model
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.model.fit(df)

            self._last_train_time = datetime.utcnow()
            self._cycle_count = 0

            logger.info(f"Prophet model trained for {self.symbol}")
            return True

        except ImportError:
            logger.error("Prophet not installed. Install with: pip install prophet")
            return False
        except Exception as e:
            logger.error(f"Error training Prophet model: {e}")
            return False

    def train_with_regressors(
        self,
        df: pd.DataFrame,
        volume: Optional[pd.Series] = None,
        volatility: Optional[pd.Series] = None,
        sentiment: Optional[pd.Series] = None
    ) -> bool:
        """
        Train Prophet model with external regressors.

        Args:
            df: DataFrame with 'ds' (datetime) and 'y' (price) columns
            volume: Normalized trading volume (optional)
            volatility: ATR or rolling std deviation (optional)
            sentiment: Fear & Greed score 0-100 (optional)

        Returns:
            True if training successful
        """
        try:
            from prophet import Prophet

            if df.empty or len(df) < 30:
                logger.warning(f"Insufficient data for Prophet training: {len(df)} rows")
                return False

            # Initialize Prophet with optimized parameters
            self.model = Prophet(
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=0.1,
                seasonality_mode='multiplicative',
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=False,
                interval_width=0.95,
            )

            # Add custom intraday seasonality
            self.model.add_seasonality(
                name='intraday',
                period=0.25,
                fourier_order=3
            )

            # Add regressors if provided
            train_df = df.copy()

            if volume is not None and len(volume) == len(df):
                # Normalize volume to 0-1 range
                vol_min, vol_max = volume.min(), volume.max()
                if vol_max > vol_min:
                    norm_volume = (volume - vol_min) / (vol_max - vol_min)
                else:
                    norm_volume = volume * 0
                train_df['volume'] = norm_volume.values
                self.model.add_regressor('volume', prior_scale=0.5, mode='multiplicative')
                logger.debug("Added volume regressor")

            if volatility is not None and len(volatility) == len(df):
                # Normalize volatility to 0-1 range
                vol_min, vol_max = volatility.min(), volatility.max()
                if vol_max > vol_min:
                    norm_volatility = (volatility - vol_min) / (vol_max - vol_min)
                else:
                    norm_volatility = volatility * 0
                train_df['volatility'] = norm_volatility.values
                self.model.add_regressor('volatility', prior_scale=0.3, mode='multiplicative')
                logger.debug("Added volatility regressor")

            if sentiment is not None and len(sentiment) == len(df):
                # Normalize sentiment (already 0-100, convert to 0-1)
                train_df['sentiment'] = (sentiment / 100).values
                self.model.add_regressor('sentiment', prior_scale=0.2, mode='additive')
                logger.debug("Added sentiment regressor")

            # Fit the model
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.model.fit(train_df)

            self._last_train_time = datetime.utcnow()
            self._cycle_count = 0
            self._has_regressors = any([
                volume is not None,
                volatility is not None,
                sentiment is not None
            ])

            logger.info(f"Prophet model with regressors trained for {self.symbol}")
            return True

        except ImportError:
            logger.error("Prophet not installed")
            return False
        except Exception as e:
            logger.error(f"Error training Prophet with regressors: {e}")
            return False

    def forecast_multi_horizon(
        self,
        current_price: Optional[float] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate forecasts for multiple time horizons.

        Returns forecasts for 1h, 4h, and 24h ahead.

        Args:
            current_price: Current price for reference (optional)

        Returns:
            Dictionary with forecasts for each horizon:
            {
                "1h": ForecastResult,
                "4h": ForecastResult,
                "24h": ForecastResult
            }
        """
        horizons = {
            "1h": 4,    # 4 periods of 15min = 1 hour
            "4h": 16,   # 16 periods = 4 hours
            "24h": 96   # 96 periods = 24 hours
        }

        results = {}

        if self.model is None:
            logger.warning("Prophet model not trained")
            for horizon in horizons:
                results[horizon] = self._empty_forecast()
            return results

        try:
            # Get maximum periods needed
            max_periods = max(horizons.values())

            # Create future dataframe
            future = self.model.make_future_dataframe(
                periods=max_periods,
                freq='15min'
            )

            # Generate forecast
            forecast = self.model.predict(future)

            # Get current price (last actual value)
            last_actual_idx = len(forecast) - max_periods - 1
            if last_actual_idx >= 0:
                base_price = float(forecast['yhat'].iloc[last_actual_idx])
            elif current_price:
                base_price = current_price
            else:
                base_price = float(forecast['yhat'].iloc[0])

            # Extract forecasts for each horizon
            for horizon_name, periods in horizons.items():
                forecast_idx = len(forecast) - max_periods + periods - 1
                horizon_forecast = forecast.iloc[forecast_idx]

                target_price = float(horizon_forecast['yhat'])
                lower_bound = float(horizon_forecast['yhat_lower'])
                upper_bound = float(horizon_forecast['yhat_upper'])

                # Calculate change percentage
                change_pct = ((target_price - base_price) / base_price) * 100

                # Determine trend
                if change_pct >= FORECAST_BULLISH_THRESHOLD:
                    trend = "RIALZISTA"
                elif change_pct <= FORECAST_BEARISH_THRESHOLD:
                    trend = "RIBASSISTA"
                else:
                    trend = "LATERALE"

                # Calculate confidence
                interval_width = upper_bound - lower_bound
                relative_width = interval_width / target_price if target_price > 0 else 1
                confidence = max(0.5, min(1.0, 1 - (relative_width / 2)))

                results[horizon_name] = {
                    "trend": trend,
                    "target_price": target_price,
                    "change_pct": change_pct,
                    "confidence": confidence,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "periods_ahead": periods,
                    "current_price": base_price,
                    "horizon": horizon_name
                }

            self._cycle_count += 1
            return results

        except Exception as e:
            logger.error(f"Error generating multi-horizon forecast: {e}")
            for horizon in horizons:
                results[horizon] = self._empty_forecast()
            return results

    def forecast(
        self,
        periods: int = PROPHET_FORECAST_PERIODS
    ) -> Dict[str, Any]:
        """
        Generate price forecast.

        Args:
            periods: Number of periods to forecast (default 16 = 4 hours)

        Returns:
            Forecast dictionary with trend, target, confidence
        """
        if self.model is None:
            logger.warning("Prophet model not trained")
            return self._empty_forecast()

        try:
            # Create future dataframe
            future = self.model.make_future_dataframe(
                periods=periods,
                freq='15min'  # Match trading timeframe
            )

            # Generate forecast
            forecast = self.model.predict(future)

            # Get the last forecasted values
            last_actual = float(forecast['yhat'].iloc[-periods-1])
            final_forecast = forecast.iloc[-1]

            target_price = float(final_forecast['yhat'])
            lower_bound = float(final_forecast['yhat_lower'])
            upper_bound = float(final_forecast['yhat_upper'])

            # Calculate change percentage
            change_pct = ((target_price - last_actual) / last_actual) * 100

            # Determine trend
            if change_pct >= FORECAST_BULLISH_THRESHOLD:
                trend = "RIALZISTA"
            elif change_pct <= FORECAST_BEARISH_THRESHOLD:
                trend = "RIBASSISTA"
            else:
                trend = "LATERALE"

            # Calculate confidence based on prediction interval width
            interval_width = upper_bound - lower_bound
            relative_width = interval_width / target_price if target_price > 0 else 1

            # Confidence: narrower interval = higher confidence
            # Map relative width to confidence (0.5 to 1.0)
            confidence = max(0.5, min(1.0, 1 - (relative_width / 2)))

            self._cycle_count += 1

            return {
                "trend": trend,
                "target_price": target_price,
                "change_pct": change_pct,
                "confidence": confidence,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "periods_ahead": periods,
                "current_price": last_actual,
            }

        except Exception as e:
            logger.error(f"Error generating forecast: {e}")
            return self._empty_forecast()

    def _empty_forecast(self) -> Dict[str, Any]:
        """Return empty forecast values."""
        return {
            "trend": "LATERALE",
            "target_price": 0,
            "change_pct": 0,
            "confidence": 0,
            "lower_bound": 0,
            "upper_bound": 0,
            "periods_ahead": PROPHET_FORECAST_PERIODS,
            "current_price": 0,
        }

    def should_retrain(self) -> bool:
        """
        Check if model should be retrained.

        Returns:
            True if retraining is needed
        """
        if self.model is None:
            return True

        # Retrain after X cycles
        if self._cycle_count >= PROPHET_RETRAIN_CYCLES:
            return True

        # Retrain after 1 hour
        if self._last_train_time:
            hours_since_train = (
                datetime.utcnow() - self._last_train_time
            ).total_seconds() / 3600

            if hours_since_train >= 1:
                return True

        return False

    def save_model(self) -> bool:
        """Save model to disk."""
        if self.model is None:
            return False

        try:
            model_path = self._model_dir / f"prophet_{self.symbol}.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(self.model, f)
            logger.debug(f"Saved Prophet model for {self.symbol}")
            return True
        except Exception as e:
            logger.error(f"Error saving Prophet model: {e}")
            return False

    def load_model(self) -> bool:
        """Load model from disk."""
        try:
            model_path = self._model_dir / f"prophet_{self.symbol}.pkl"
            if model_path.exists():
                with open(model_path, "rb") as f:
                    self.model = pickle.load(f)
                logger.debug(f"Loaded Prophet model for {self.symbol}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading Prophet model: {e}")
            return False


class ForecastManager:
    """Manages forecasters for multiple symbols."""

    def __init__(self):
        """Initialize the forecast manager."""
        self._forecasters: Dict[str, ProphetForecaster] = {}

    def get_forecaster(self, symbol: str) -> ProphetForecaster:
        """Get or create forecaster for a symbol."""
        if symbol not in self._forecasters:
            forecaster = ProphetForecaster(symbol)
            # Try to load existing model
            forecaster.load_model()
            self._forecasters[symbol] = forecaster

        return self._forecasters[symbol]

    def get_forecast(
        self,
        symbol: str,
        ohlcv_data: List[List]
    ) -> Dict[str, Any]:
        """
        Get forecast for a symbol, training if necessary.

        Args:
            symbol: Trading symbol
            ohlcv_data: OHLCV historical data

        Returns:
            Forecast dictionary
        """
        forecaster = self.get_forecaster(symbol)

        # Prepare data
        if ohlcv_data:
            df = pd.DataFrame(
                ohlcv_data,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["ds"] = pd.to_datetime(df["timestamp"], unit="ms")
            df["y"] = df["close"]
            df = df[["ds", "y"]]
        else:
            df = pd.DataFrame()

        # Train if needed
        if forecaster.should_retrain():
            if not df.empty:
                forecaster.train(df)
                forecaster.save_model()

        # Generate forecast
        return forecaster.forecast()


# Global forecast manager
forecast_manager = ForecastManager()


def get_price_forecast(symbol: str, ohlcv_data: List[List]) -> Dict[str, Any]:
    """
    Convenience function to get price forecast.

    Args:
        symbol: Trading symbol
        ohlcv_data: OHLCV historical data

    Returns:
        Forecast dictionary
    """
    return forecast_manager.get_forecast(symbol, ohlcv_data)
