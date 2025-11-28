"""
Drawdown Manager.

Monitors and enforces drawdown limits to protect capital.
Implements automatic trading halt when limits are exceeded.

Limiti MODERATI (default):
- Max daily drawdown: 5%
- Max weekly drawdown: 10%
"""
from typing import Dict, Tuple, Optional, Any
from datetime import datetime, date, timedelta
from decimal import Decimal

from utils.logger import get_logger

logger = get_logger(__name__)


class DrawdownManager:
    """
    Manages drawdown limits and trading permissions.

    Tracks daily and weekly P&L to enforce risk limits.
    Automatically halts trading when limits are exceeded.
    """

    def __init__(
        self,
        max_daily_drawdown_pct: float = 5.0,
        max_weekly_drawdown_pct: float = 10.0,
        supabase_client=None
    ):
        """
        Initialize drawdown manager.

        Args:
            max_daily_drawdown_pct: Maximum allowed daily drawdown (default 5%)
            max_weekly_drawdown_pct: Maximum allowed weekly drawdown (default 10%)
            supabase_client: Optional Supabase client for persistence
        """
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.max_weekly_drawdown_pct = max_weekly_drawdown_pct
        self.supabase = supabase_client

        # In-memory tracking
        self._daily_starting_equity: Optional[float] = None
        self._weekly_starting_equity: Optional[float] = None
        self._current_date: Optional[date] = None
        self._week_start_date: Optional[date] = None
        self._trading_halted: bool = False
        self._halt_reason: Optional[str] = None

    def initialize_day(self, current_equity: float) -> None:
        """
        Initialize tracking for a new trading day.

        Args:
            current_equity: Current portfolio equity
        """
        today = date.today()

        # Check if it's a new day
        if self._current_date != today:
            self._current_date = today
            self._daily_starting_equity = current_equity

            # Check if it's a new week (Monday)
            if today.weekday() == 0 or self._week_start_date is None:
                self._week_start_date = today
                self._weekly_starting_equity = current_equity

            logger.info(
                f"Drawdown tracking initialized for {today}: "
                f"daily_start={current_equity:.2f}, "
                f"weekly_start={self._weekly_starting_equity:.2f}"
            )

        # Reset halt if new day
        if self._trading_halted:
            self._trading_halted = False
            self._halt_reason = None
            logger.info("Trading halt reset for new day")

    def update_equity(self, current_equity: float) -> Dict[str, Any]:
        """
        Update current equity and calculate drawdowns.

        Args:
            current_equity: Current portfolio equity

        Returns:
            Dictionary with current drawdown status
        """
        # Initialize if needed
        if self._daily_starting_equity is None:
            self.initialize_day(current_equity)

        # Calculate daily drawdown
        daily_pnl = current_equity - self._daily_starting_equity
        daily_drawdown_pct = 0.0
        if self._daily_starting_equity > 0:
            daily_drawdown_pct = (
                (self._daily_starting_equity - current_equity)
                / self._daily_starting_equity
            ) * 100

        # Calculate weekly drawdown
        weekly_pnl = current_equity - self._weekly_starting_equity
        weekly_drawdown_pct = 0.0
        if self._weekly_starting_equity > 0:
            weekly_drawdown_pct = (
                (self._weekly_starting_equity - current_equity)
                / self._weekly_starting_equity
            ) * 100

        # Check if limits exceeded
        if daily_drawdown_pct >= self.max_daily_drawdown_pct:
            self._trading_halted = True
            self._halt_reason = (
                f"Daily drawdown limit exceeded: "
                f"{daily_drawdown_pct:.2f}% >= {self.max_daily_drawdown_pct}%"
            )
            logger.warning(self._halt_reason)

        if weekly_drawdown_pct >= self.max_weekly_drawdown_pct:
            self._trading_halted = True
            self._halt_reason = (
                f"Weekly drawdown limit exceeded: "
                f"{weekly_drawdown_pct:.2f}% >= {self.max_weekly_drawdown_pct}%"
            )
            logger.warning(self._halt_reason)

        return {
            'date': self._current_date,
            'daily_starting_equity': self._daily_starting_equity,
            'weekly_starting_equity': self._weekly_starting_equity,
            'current_equity': current_equity,
            'daily_pnl': daily_pnl,
            'weekly_pnl': weekly_pnl,
            'daily_drawdown_pct': max(0, daily_drawdown_pct),
            'weekly_drawdown_pct': max(0, weekly_drawdown_pct),
            'trading_halted': self._trading_halted,
            'halt_reason': self._halt_reason
        }

    def check_can_trade(self) -> Tuple[bool, str]:
        """
        Check if trading is currently allowed.

        Returns:
            Tuple of (can_trade, reason)
        """
        if self._trading_halted:
            return False, self._halt_reason or "Trading halted due to drawdown limits"

        return True, "Trading allowed"

    def get_allowed_risk_multiplier(self, current_equity: float) -> float:
        """
        Get risk multiplier based on current drawdown.

        Returns a value between 0.0 and 1.0.
        - 1.0 = full risk allowed
        - 0.5 = half risk
        - 0.0 = no risk (trading halted)

        Args:
            current_equity: Current portfolio equity

        Returns:
            Risk multiplier (0.0 to 1.0)
        """
        if self._daily_starting_equity is None:
            return 1.0

        if self._trading_halted:
            return 0.0

        # Calculate current daily drawdown
        daily_drawdown_pct = 0.0
        if self._daily_starting_equity > 0:
            daily_drawdown_pct = max(0, (
                (self._daily_starting_equity - current_equity)
                / self._daily_starting_equity
            ) * 100)

        # Scale down risk as we approach the limit
        # At 0% drawdown = 1.0 multiplier
        # At 50% of limit = 0.75 multiplier
        # At 80% of limit = 0.5 multiplier
        # At 100% of limit = 0.0 multiplier

        drawdown_ratio = daily_drawdown_pct / self.max_daily_drawdown_pct

        if drawdown_ratio >= 1.0:
            return 0.0
        elif drawdown_ratio >= 0.8:
            # Rapid reduction from 0.5 to 0
            return 0.5 * (1 - (drawdown_ratio - 0.8) / 0.2)
        elif drawdown_ratio >= 0.5:
            # Gradual reduction from 0.75 to 0.5
            return 0.75 - 0.25 * ((drawdown_ratio - 0.5) / 0.3)
        else:
            # Minor reduction from 1.0 to 0.75
            return 1.0 - 0.25 * (drawdown_ratio / 0.5)

    def get_status(self) -> Dict[str, Any]:
        """
        Get current drawdown manager status.

        Returns:
            Dictionary with status information
        """
        return {
            'max_daily_drawdown_pct': self.max_daily_drawdown_pct,
            'max_weekly_drawdown_pct': self.max_weekly_drawdown_pct,
            'current_date': self._current_date,
            'week_start_date': self._week_start_date,
            'daily_starting_equity': self._daily_starting_equity,
            'weekly_starting_equity': self._weekly_starting_equity,
            'trading_halted': self._trading_halted,
            'halt_reason': self._halt_reason
        }

    def reset_halt(self) -> None:
        """Manually reset trading halt (use with caution)."""
        self._trading_halted = False
        self._halt_reason = None
        logger.info("Trading halt manually reset")

    async def save_to_database(self, current_equity: float) -> Optional[str]:
        """
        Save current drawdown tracking to database.

        Args:
            current_equity: Current portfolio equity

        Returns:
            Record ID if saved, None otherwise
        """
        if not self.supabase:
            return None

        try:
            status = self.update_equity(current_equity)

            record = {
                'date': str(self._current_date),
                'starting_equity': self._daily_starting_equity,
                'current_equity': current_equity,
                'daily_pnl': status['daily_pnl'],
                'daily_drawdown_pct': status['daily_drawdown_pct'],
                'weekly_drawdown_pct': status['weekly_drawdown_pct'],
                'trading_halted': self._trading_halted,
                'halt_reason': self._halt_reason
            }

            # Upsert by date
            result = self.supabase.table('trading_drawdown_tracking').upsert(
                record,
                on_conflict='date'
            ).execute()

            if result.data:
                return result.data[0].get('id')

            return None

        except Exception as e:
            logger.error(f"Error saving drawdown tracking: {e}")
            return None

    async def load_from_database(self) -> bool:
        """
        Load today's drawdown tracking from database.

        Returns:
            True if loaded successfully
        """
        if not self.supabase:
            return False

        try:
            today = str(date.today())

            result = self.supabase.table('trading_drawdown_tracking').select(
                '*'
            ).eq('date', today).execute()

            if result.data:
                record = result.data[0]
                self._daily_starting_equity = record.get('starting_equity')
                self._current_date = date.today()
                self._trading_halted = record.get('trading_halted', False)
                self._halt_reason = record.get('halt_reason')

                logger.info(f"Loaded drawdown tracking for {today}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error loading drawdown tracking: {e}")
            return False


# Global instance with moderate limits
drawdown_manager = DrawdownManager(
    max_daily_drawdown_pct=5.0,
    max_weekly_drawdown_pct=10.0
)
