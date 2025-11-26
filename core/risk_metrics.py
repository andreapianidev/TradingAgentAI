"""
Risk Metrics Calculator.

Calculates trading performance metrics:
- Sharpe Ratio
- Sortino Ratio
- Max Drawdown
- Win Rate
- Profit Factor
- Calmar Ratio
"""
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from utils.logger import get_logger

logger = get_logger(__name__)


class RiskMetricsCalculator:
    """Calculate risk and performance metrics for trading."""

    def __init__(self, risk_free_rate: float = 0.0):
        """
        Initialize risk metrics calculator.

        Args:
            risk_free_rate: Annual risk-free rate (default 0 for crypto)
        """
        self.risk_free_rate = risk_free_rate

    def calculate_returns(self, equity_curve: pd.Series) -> pd.Series:
        """
        Calculate percentage returns from equity curve.

        Args:
            equity_curve: Series of equity values with datetime index

        Returns:
            Series of percentage returns
        """
        if equity_curve.empty or len(equity_curve) < 2:
            return pd.Series(dtype=float)

        returns = equity_curve.pct_change().dropna()
        return returns

    def calculate_sharpe_ratio(
        self,
        returns: pd.Series,
        periods_per_year: int = 35040  # 15-min intervals per year
    ) -> float:
        """
        Calculate Sharpe Ratio.

        Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
        Annualized based on trading frequency.

        Args:
            returns: Series of percentage returns
            periods_per_year: Number of trading periods per year

        Returns:
            Annualized Sharpe ratio
        """
        if returns.empty or len(returns) < 2:
            return 0.0

        try:
            mean_return = returns.mean()
            std_return = returns.std()

            if std_return == 0:
                return 0.0

            # Convert annual risk-free rate to period rate
            period_rf = self.risk_free_rate / periods_per_year

            # Calculate Sharpe
            sharpe = (mean_return - period_rf) / std_return

            # Annualize
            annualized_sharpe = sharpe * np.sqrt(periods_per_year)

            return float(annualized_sharpe)

        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0

    def calculate_sortino_ratio(
        self,
        returns: pd.Series,
        periods_per_year: int = 35040
    ) -> float:
        """
        Calculate Sortino Ratio.

        Sortino = (Mean Return - Risk Free Rate) / Downside Std Dev
        Uses only negative returns for denominator.

        Args:
            returns: Series of percentage returns
            periods_per_year: Number of trading periods per year

        Returns:
            Annualized Sortino ratio
        """
        if returns.empty or len(returns) < 2:
            return 0.0

        try:
            mean_return = returns.mean()

            # Calculate downside deviation (only negative returns)
            negative_returns = returns[returns < 0]

            if negative_returns.empty:
                # No negative returns = infinite Sortino (cap it)
                return 10.0

            downside_std = negative_returns.std()

            if downside_std == 0:
                return 0.0

            # Convert annual risk-free rate to period rate
            period_rf = self.risk_free_rate / periods_per_year

            # Calculate Sortino
            sortino = (mean_return - period_rf) / downside_std

            # Annualize
            annualized_sortino = sortino * np.sqrt(periods_per_year)

            return float(annualized_sortino)

        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {e}")
            return 0.0

    def calculate_max_drawdown(
        self,
        equity_curve: pd.Series
    ) -> Tuple[float, Optional[datetime], Optional[datetime]]:
        """
        Calculate Maximum Drawdown.

        Max Drawdown = (Peak - Trough) / Peak

        Args:
            equity_curve: Series of equity values

        Returns:
            Tuple of (max_drawdown_pct, peak_date, trough_date)
        """
        if equity_curve.empty or len(equity_curve) < 2:
            return 0.0, None, None

        try:
            # Calculate running maximum
            running_max = equity_curve.cummax()

            # Calculate drawdown series
            drawdown = (running_max - equity_curve) / running_max

            # Find maximum drawdown
            max_dd = drawdown.max()
            max_dd_idx = drawdown.idxmax()

            # Find peak date (where running max equals the value before drawdown)
            # Look backwards from trough to find the peak
            trough_date = max_dd_idx
            peak_value = running_max.loc[trough_date]
            peak_candidates = equity_curve[equity_curve == peak_value]

            if not peak_candidates.empty:
                peak_date = peak_candidates.index[0]
            else:
                peak_date = None

            return float(max_dd * 100), peak_date, trough_date

        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0, None, None

    def calculate_calmar_ratio(
        self,
        returns: pd.Series,
        equity_curve: pd.Series,
        periods_per_year: int = 35040
    ) -> float:
        """
        Calculate Calmar Ratio.

        Calmar = Annualized Return / Max Drawdown

        Args:
            returns: Series of percentage returns
            equity_curve: Series of equity values
            periods_per_year: Number of trading periods per year

        Returns:
            Calmar ratio
        """
        if returns.empty or equity_curve.empty:
            return 0.0

        try:
            # Calculate annualized return
            total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
            n_periods = len(equity_curve)

            if n_periods < 2:
                return 0.0

            # Annualize return
            periods_elapsed = n_periods
            annualization_factor = periods_per_year / periods_elapsed
            annualized_return = (1 + total_return) ** annualization_factor - 1

            # Get max drawdown
            max_dd, _, _ = self.calculate_max_drawdown(equity_curve)

            if max_dd == 0:
                return 0.0

            calmar = (annualized_return * 100) / max_dd

            return float(calmar)

        except Exception as e:
            logger.error(f"Error calculating Calmar ratio: {e}")
            return 0.0

    def calculate_win_rate(self, trades: List[Dict[str, Any]]) -> float:
        """
        Calculate Win Rate.

        Win Rate = Winning Trades / Total Trades

        Args:
            trades: List of trade dictionaries with 'realized_pnl' or 'pnl' key

        Returns:
            Win rate as percentage (0-100)
        """
        if not trades:
            return 0.0

        try:
            winning_trades = 0
            total_trades = 0

            for trade in trades:
                pnl = trade.get('realized_pnl') or trade.get('pnl', 0)
                if pnl is not None:
                    total_trades += 1
                    if pnl > 0:
                        winning_trades += 1

            if total_trades == 0:
                return 0.0

            win_rate = (winning_trades / total_trades) * 100
            return round(win_rate, 1)

        except Exception as e:
            logger.error(f"Error calculating win rate: {e}")
            return 0.0

    def calculate_profit_factor(self, trades: List[Dict[str, Any]]) -> float:
        """
        Calculate Profit Factor.

        Profit Factor = Gross Profit / Gross Loss

        Args:
            trades: List of trade dictionaries with 'realized_pnl' or 'pnl' key

        Returns:
            Profit factor (>1 is profitable)
        """
        if not trades:
            return 0.0

        try:
            gross_profit = 0.0
            gross_loss = 0.0

            for trade in trades:
                pnl = trade.get('realized_pnl') or trade.get('pnl', 0)
                if pnl is not None:
                    if pnl > 0:
                        gross_profit += pnl
                    else:
                        gross_loss += abs(pnl)

            if gross_loss == 0:
                return 10.0 if gross_profit > 0 else 0.0

            profit_factor = gross_profit / gross_loss
            return round(profit_factor, 2)

        except Exception as e:
            logger.error(f"Error calculating profit factor: {e}")
            return 0.0

    def calculate_avg_win_loss(
        self,
        trades: List[Dict[str, Any]]
    ) -> Tuple[float, float, float]:
        """
        Calculate average win, average loss, and win/loss ratio.

        Args:
            trades: List of trade dictionaries

        Returns:
            Tuple of (avg_win, avg_loss, win_loss_ratio)
        """
        if not trades:
            return 0.0, 0.0, 0.0

        try:
            wins = []
            losses = []

            for trade in trades:
                pnl = trade.get('realized_pnl') or trade.get('pnl', 0)
                if pnl is not None:
                    if pnl > 0:
                        wins.append(pnl)
                    elif pnl < 0:
                        losses.append(abs(pnl))

            avg_win = np.mean(wins) if wins else 0.0
            avg_loss = np.mean(losses) if losses else 0.0

            if avg_loss == 0:
                ratio = 10.0 if avg_win > 0 else 0.0
            else:
                ratio = avg_win / avg_loss

            return float(avg_win), float(avg_loss), round(ratio, 2)

        except Exception as e:
            logger.error(f"Error calculating avg win/loss: {e}")
            return 0.0, 0.0, 0.0

    def calculate_trade_stats(
        self,
        trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive trade statistics.

        Args:
            trades: List of trade dictionaries

        Returns:
            Dictionary with trade statistics
        """
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'win_loss_ratio': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0,
                'total_pnl': 0.0,
                'avg_trade_pnl': 0.0
            }

        pnls = []
        for trade in trades:
            pnl = trade.get('realized_pnl') or trade.get('pnl', 0)
            if pnl is not None:
                pnls.append(pnl)

        if not pnls:
            return self.calculate_trade_stats([])

        winning = len([p for p in pnls if p > 0])
        losing = len([p for p in pnls if p < 0])
        total = len(pnls)

        avg_win, avg_loss, ratio = self.calculate_avg_win_loss(trades)

        return {
            'total_trades': total,
            'winning_trades': winning,
            'losing_trades': losing,
            'win_rate': self.calculate_win_rate(trades),
            'profit_factor': self.calculate_profit_factor(trades),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'win_loss_ratio': ratio,
            'best_trade': max(pnls) if pnls else 0.0,
            'worst_trade': min(pnls) if pnls else 0.0,
            'total_pnl': sum(pnls),
            'avg_trade_pnl': np.mean(pnls) if pnls else 0.0
        }

    def calculate_all_metrics(
        self,
        equity_curve: pd.Series,
        trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate all risk and performance metrics.

        Args:
            equity_curve: Series of equity values with datetime index
            trades: List of trade dictionaries

        Returns:
            Dictionary with all metrics
        """
        returns = self.calculate_returns(equity_curve)
        max_dd, peak_date, trough_date = self.calculate_max_drawdown(equity_curve)
        trade_stats = self.calculate_trade_stats(trades)

        return {
            # Risk metrics
            'sharpe_ratio': self.calculate_sharpe_ratio(returns),
            'sortino_ratio': self.calculate_sortino_ratio(returns),
            'calmar_ratio': self.calculate_calmar_ratio(returns, equity_curve),
            'max_drawdown_pct': max_dd,
            'max_drawdown_peak': peak_date,
            'max_drawdown_trough': trough_date,

            # Trade metrics
            **trade_stats,

            # Summary
            'total_return_pct': float(
                (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100
            ) if len(equity_curve) >= 2 else 0.0
        }


# Global instance
risk_metrics = RiskMetricsCalculator()
