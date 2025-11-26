"""
Forecast Performance Tracker.

Tracks and evaluates Prophet forecast accuracy over time.
Stores predictions and actual outcomes for model improvement.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ForecastRecord:
    """Record of a forecast prediction."""
    symbol: str
    horizon: str  # '1h', '4h', '24h'
    predicted_price: float
    prediction_timestamp: datetime
    hyperparameters: Dict[str, Any]
    current_price: float
    predicted_direction: str  # 'up', 'down', 'sideways'


class ForecastTracker:
    """
    Tracks forecast predictions and evaluates accuracy.

    Stores predictions in database and evaluates them when
    actual prices become available.
    """

    def __init__(self, supabase_client=None):
        """
        Initialize forecast tracker.

        Args:
            supabase_client: Optional Supabase client for persistence
        """
        self.supabase = supabase_client
        self._pending_evaluations: List[ForecastRecord] = []

    def record_prediction(
        self,
        symbol: str,
        horizon: str,
        predicted_price: float,
        current_price: float,
        hyperparameters: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Record a new forecast prediction.

        Args:
            symbol: Trading symbol (BTC, ETH, SOL)
            horizon: Forecast horizon ('1h', '4h', '24h')
            predicted_price: Predicted price at horizon
            current_price: Current price at prediction time
            hyperparameters: Prophet parameters used

        Returns:
            Record ID if saved to database
        """
        now = datetime.utcnow()

        # Determine predicted direction
        change_pct = ((predicted_price - current_price) / current_price) * 100
        if change_pct > 0.5:
            predicted_direction = 'up'
        elif change_pct < -0.5:
            predicted_direction = 'down'
        else:
            predicted_direction = 'sideways'

        record = ForecastRecord(
            symbol=symbol,
            horizon=horizon,
            predicted_price=predicted_price,
            prediction_timestamp=now,
            hyperparameters=hyperparameters or {},
            current_price=current_price,
            predicted_direction=predicted_direction
        )

        self._pending_evaluations.append(record)

        # Save to database if available
        if self.supabase:
            return self._save_to_db(record)

        return None

    def _save_to_db(self, record: ForecastRecord) -> Optional[str]:
        """Save prediction record to database."""
        try:
            data = {
                'symbol': record.symbol,
                'forecast_horizon': record.horizon,
                'predicted_price': record.predicted_price,
                'prediction_timestamp': record.prediction_timestamp.isoformat(),
                'hyperparameters': record.hyperparameters
            }

            result = self.supabase.table('trading_forecast_performance').insert(
                data
            ).execute()

            if result.data:
                return result.data[0].get('id')

            return None

        except Exception as e:
            logger.error(f"Error saving forecast prediction: {e}")
            return None

    def evaluate_prediction(
        self,
        prediction_id: str,
        actual_price: float
    ) -> Dict[str, Any]:
        """
        Evaluate a prediction against actual outcome.

        Args:
            prediction_id: ID of the prediction record
            actual_price: Actual price at the predicted time

        Returns:
            Evaluation results with MAPE and direction accuracy
        """
        if not self.supabase:
            return {'error': 'No database connection'}

        try:
            # Fetch the prediction
            result = self.supabase.table('trading_forecast_performance').select(
                '*'
            ).eq('id', prediction_id).execute()

            if not result.data:
                return {'error': 'Prediction not found'}

            prediction = result.data[0]
            predicted_price = float(prediction['predicted_price'])

            # Calculate MAPE (Mean Absolute Percentage Error)
            mape = abs(predicted_price - actual_price) / actual_price * 100

            # Determine if direction was correct
            predicted_change = predicted_price - float(prediction.get('current_price', predicted_price))
            actual_change = actual_price - float(prediction.get('current_price', actual_price))

            direction_correct = (
                (predicted_change > 0 and actual_change > 0) or
                (predicted_change < 0 and actual_change < 0) or
                (abs(predicted_change) < 0.5 and abs(actual_change) < 0.5)
            )

            # Update record with evaluation
            update_data = {
                'actual_price': actual_price,
                'evaluation_timestamp': datetime.utcnow().isoformat(),
                'mape': mape,
                'direction_correct': direction_correct
            }

            self.supabase.table('trading_forecast_performance').update(
                update_data
            ).eq('id', prediction_id).execute()

            return {
                'prediction_id': prediction_id,
                'predicted_price': predicted_price,
                'actual_price': actual_price,
                'mape': mape,
                'direction_correct': direction_correct,
                'error_amount': abs(predicted_price - actual_price)
            }

        except Exception as e:
            logger.error(f"Error evaluating prediction: {e}")
            return {'error': str(e)}

    def evaluate_pending(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Evaluate all pending predictions that have reached their horizon.

        Args:
            current_prices: Dictionary of current prices by symbol

        Returns:
            List of evaluation results
        """
        results = []
        now = datetime.utcnow()

        horizon_durations = {
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '24h': timedelta(hours=24)
        }

        remaining = []

        for record in self._pending_evaluations:
            horizon_duration = horizon_durations.get(record.horizon, timedelta(hours=4))
            evaluation_time = record.prediction_timestamp + horizon_duration

            if now >= evaluation_time:
                # Time to evaluate
                actual_price = current_prices.get(record.symbol)

                if actual_price:
                    mape = abs(record.predicted_price - actual_price) / actual_price * 100

                    predicted_change = record.predicted_price - record.current_price
                    actual_change = actual_price - record.current_price

                    direction_correct = (
                        (predicted_change > 0 and actual_change > 0) or
                        (predicted_change < 0 and actual_change < 0)
                    )

                    results.append({
                        'symbol': record.symbol,
                        'horizon': record.horizon,
                        'predicted_price': record.predicted_price,
                        'actual_price': actual_price,
                        'mape': mape,
                        'direction_correct': direction_correct
                    })
            else:
                remaining.append(record)

        self._pending_evaluations = remaining
        return results

    def get_performance_summary(
        self,
        symbol: Optional[str] = None,
        horizon: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get performance summary for forecasts.

        Args:
            symbol: Filter by symbol (optional)
            horizon: Filter by horizon (optional)
            days: Number of days to look back

        Returns:
            Summary statistics
        """
        if not self.supabase:
            return {'error': 'No database connection'}

        try:
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

            query = self.supabase.table('trading_forecast_performance').select(
                '*'
            ).gte('prediction_timestamp', cutoff).not_.is_('actual_price', 'null')

            if symbol:
                query = query.eq('symbol', symbol)
            if horizon:
                query = query.eq('forecast_horizon', horizon)

            result = query.execute()

            if not result.data:
                return {
                    'total_predictions': 0,
                    'avg_mape': None,
                    'direction_accuracy': None
                }

            predictions = result.data
            total = len(predictions)

            mapes = [p['mape'] for p in predictions if p.get('mape') is not None]
            directions = [p['direction_correct'] for p in predictions if p.get('direction_correct') is not None]

            avg_mape = sum(mapes) / len(mapes) if mapes else None
            direction_accuracy = (sum(directions) / len(directions) * 100) if directions else None

            return {
                'total_predictions': total,
                'evaluated_predictions': len(mapes),
                'avg_mape': round(avg_mape, 2) if avg_mape else None,
                'direction_accuracy': round(direction_accuracy, 1) if direction_accuracy else None,
                'best_mape': min(mapes) if mapes else None,
                'worst_mape': max(mapes) if mapes else None
            }

        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {'error': str(e)}

    def get_accuracy_by_horizon(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """
        Get accuracy breakdown by forecast horizon.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with stats for each horizon
        """
        horizons = ['1h', '4h', '24h']
        results = {}

        for horizon in horizons:
            results[horizon] = self.get_performance_summary(horizon=horizon, days=days)

        return results


# Global tracker instance
forecast_tracker = ForecastTracker()
