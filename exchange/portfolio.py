"""
Portfolio management and tracking.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime

from exchange.hyperliquid_client import exchange_client
from database.operations import db_ops
from utils.logger import get_logger, log_portfolio_status

logger = get_logger(__name__)


class PortfolioManager:
    """Manages portfolio state and snapshots."""

    def __init__(self):
        """Initialize the portfolio manager."""
        self.client = exchange_client
        self._initial_equity = None

    def get_portfolio_state(self) -> Dict[str, Any]:
        """
        Get current portfolio state.

        Returns:
            Portfolio data including positions and balances
        """
        portfolio = self.client.fetch_portfolio()

        # Get open positions from database for additional tracking
        db_positions = db_ops.get_open_positions()

        # Format positions for display
        formatted_positions = []
        for pos in portfolio.get("positions", []):
            formatted_positions.append({
                "symbol": pos.get("symbol"),
                "direction": pos.get("direction"),
                "entry_price": pos.get("entry_price"),
                "quantity": pos.get("quantity"),
                "leverage": pos.get("leverage"),
                "unrealized_pnl": pos.get("unrealized_pnl"),
                "unrealized_pnl_pct": pos.get("unrealized_pnl_pct"),
                "liquidation_price": pos.get("liquidation_price"),
            })

        state = {
            "total_equity": portfolio.get("total_equity", 0),
            "available_balance": portfolio.get("available_balance", 0),
            "margin_used": portfolio.get("margin_used", 0),
            "exposure_pct": portfolio.get("exposure_pct", 0),
            "positions": formatted_positions,
            "open_positions_count": len(formatted_positions),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Calculate P&L if we have initial equity
        if self._initial_equity:
            total_pnl = state["total_equity"] - self._initial_equity
            total_pnl_pct = (total_pnl / self._initial_equity) * 100 if self._initial_equity > 0 else 0
            state["total_pnl"] = total_pnl
            state["total_pnl_pct"] = total_pnl_pct

        return state

    def save_snapshot(self) -> int:
        """
        Save current portfolio state to database.

        Returns:
            Snapshot ID
        """
        state = self.get_portfolio_state()

        snapshot_id = db_ops.save_portfolio_snapshot(
            total_equity=state.get("total_equity", 0),
            available_balance=state.get("available_balance", 0),
            margin_used=state.get("margin_used", 0),
            open_positions_count=state.get("open_positions_count", 0),
            exposure_pct=state.get("exposure_pct", 0),
            total_pnl=state.get("total_pnl"),
            total_pnl_pct=state.get("total_pnl_pct"),
            raw_data=state
        )

        log_portfolio_status(
            equity=state.get("total_equity", 0),
            available=state.get("available_balance", 0),
            exposure_pct=state.get("exposure_pct", 0),
            positions_count=state.get("open_positions_count", 0)
        )

        return snapshot_id

    def set_initial_equity(self, equity: float = None) -> None:
        """
        Set initial equity for P&L tracking.

        Args:
            equity: Initial equity value (fetches current if None)
        """
        if equity is None:
            portfolio = self.client.fetch_portfolio()
            equity = portfolio.get("total_equity", 0)

        self._initial_equity = equity
        logger.info(f"Set initial equity to ${equity:.2f}")

    def get_open_positions_formatted(self) -> List[Dict[str, Any]]:
        """
        Get open positions in a format suitable for LLM prompt.

        Returns:
            List of formatted position dictionaries
        """
        portfolio = self.client.fetch_portfolio()
        return portfolio.get("positions", [])

    def get_position_for_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position for a specific symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position data or None
        """
        return self.client.get_position(symbol)

    def can_open_new_position(
        self,
        size_pct: float,
        max_exposure_pct: float = 30.0
    ) -> bool:
        """
        Check if a new position can be opened.

        Args:
            size_pct: Position size as percentage
            max_exposure_pct: Maximum allowed exposure

        Returns:
            True if position can be opened
        """
        current_exposure = self.client.get_total_exposure()
        new_exposure = current_exposure + size_pct

        if new_exposure > max_exposure_pct:
            logger.warning(
                f"Cannot open position: exposure would be {new_exposure:.1f}% "
                f"(max: {max_exposure_pct}%)"
            )
            return False

        return True

    def get_available_for_trading(self) -> float:
        """
        Get available balance for trading.

        Returns:
            Available USDC balance
        """
        portfolio = self.client.fetch_portfolio()
        return portfolio.get("available_balance", 0)

    def get_trading_statistics(self) -> Dict[str, Any]:
        """
        Get trading statistics from database.

        Returns:
            Statistics dictionary
        """
        return db_ops.get_trading_stats()

    def get_equity_curve(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get equity curve data.

        Args:
            limit: Maximum number of points

        Returns:
            List of {timestamp, equity} points
        """
        snapshots = db_ops.get_portfolio_history(limit)

        return [
            {
                "timestamp": s.timestamp,
                "equity": float(s.total_equity_usdc),
                "pnl": float(s.total_pnl_usdc or 0),
            }
            for s in snapshots
        ]


# Global portfolio manager instance
portfolio_manager = PortfolioManager()
