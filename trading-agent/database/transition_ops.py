"""
Database operations for exchange transitions.
Handles all CRUD operations for the trading_exchange_transitions table.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from utils.logger import get_logger, log_error_with_context

logger = get_logger(__name__)


class TransitionOperations:
    """Manages all database operations for exchange transitions."""

    def __init__(self, supabase_client):
        """
        Initialize transition operations.

        Args:
            supabase_client: Supabase client instance
        """
        self.client = supabase_client

    def create_transition(
        self,
        from_exchange: str,
        to_exchange: str,
        strategy: str,
        position_ids: List[str],
        trading_mode: str
    ) -> Optional[str]:
        """
        Create a new transition record.

        Args:
            from_exchange: Source exchange (alpaca/hyperliquid)
            to_exchange: Target exchange (alpaca/hyperliquid)
            strategy: Transition strategy (IMMEDIATE/PROFITABLE/WAIT_PROFIT/MANUAL)
            position_ids: List of position symbols to transition
            trading_mode: Trading mode (paper/live)

        Returns:
            Transition ID if successful, None otherwise
        """
        try:
            data = {
                "from_exchange": from_exchange,
                "to_exchange": to_exchange,
                "transition_strategy": strategy,
                "status": "pending",
                "total_positions": len(position_ids),
                "positions_remaining": len(position_ids),
                "positions_closed": 0,
                "positions_in_profit": 0,
                "positions_in_loss": 0,
                "position_ids": position_ids,
                "started_at": datetime.utcnow().isoformat(),
                "trading_mode": trading_mode,
                "transition_log": [],
                "manual_override_required": (strategy == "MANUAL")
            }

            result = self.client.table("trading_exchange_transitions").insert(data).execute()

            if not result.data:
                logger.error("Failed to create transition record")
                return None

            transition_id = result.data[0]["id"]
            logger.info(f"Created transition: {transition_id} ({from_exchange} → {to_exchange}, {strategy})")

            # Mark all positions as in_transition
            if position_ids:
                self.client.table("trading_positions") \
                    .update({"in_transition": True, "transition_id": transition_id}) \
                    .in_("symbol", position_ids) \
                    .eq("status", "open") \
                    .execute()

            return transition_id

        except Exception as e:
            log_error_with_context(e, "create_transition", {
                "from_exchange": from_exchange,
                "to_exchange": to_exchange,
                "strategy": strategy
            })
            return None

    def get_active_transition(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently active transition.

        Returns:
            Transition dict if found, None otherwise
        """
        try:
            result = self.client.table("trading_exchange_transitions") \
                .select("*") \
                .in_("status", ["pending", "in_progress"]) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()

            if result.data:
                return result.data[0]

            return None

        except Exception as e:
            log_error_with_context(e, "get_active_transition")
            return None

    def get_transition_by_id(self, transition_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific transition by ID.

        Args:
            transition_id: Transition UUID

        Returns:
            Transition dict if found, None otherwise
        """
        try:
            result = self.client.table("trading_exchange_transitions") \
                .select("*") \
                .eq("id", transition_id) \
                .single() \
                .execute()

            return result.data if result.data else None

        except Exception as e:
            log_error_with_context(e, "get_transition_by_id", {"transition_id": transition_id})
            return None

    def update_transition(self, transition_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update transition fields.

        Args:
            transition_id: Transition UUID
            updates: Dictionary of fields to update

        Returns:
            True if successful
        """
        try:
            # updated_at is handled by trigger
            self.client.table("trading_exchange_transitions") \
                .update(updates) \
                .eq("id", transition_id) \
                .execute()

            logger.debug(f"Updated transition {transition_id}: {list(updates.keys())}")
            return True

        except Exception as e:
            log_error_with_context(e, "update_transition", {
                "transition_id": transition_id,
                "updates": updates
            })
            return False

    def get_transition_positions(self, transition_id: str) -> List[Dict[str, Any]]:
        """
        Get all open positions belonging to a transition.

        Args:
            transition_id: Transition UUID

        Returns:
            List of position dicts
        """
        try:
            result = self.client.table("trading_positions") \
                .select("*") \
                .eq("transition_id", transition_id) \
                .eq("status", "open") \
                .execute()

            return result.data or []

        except Exception as e:
            log_error_with_context(e, "get_transition_positions", {"transition_id": transition_id})
            return []

    def mark_position_closed_in_transition(
        self,
        transition_id: str,
        position_symbol: str
    ) -> bool:
        """
        Update transition when a position closes.

        Args:
            transition_id: Transition UUID
            position_symbol: Symbol of closed position

        Returns:
            True if successful
        """
        try:
            # Get current transition
            transition = self.get_transition_by_id(transition_id)
            if not transition:
                logger.warning(f"Transition {transition_id} not found")
                return False

            # Update counts
            new_closed = transition["positions_closed"] + 1
            new_remaining = transition["positions_remaining"] - 1

            updates = {
                "positions_closed": new_closed,
                "positions_remaining": new_remaining,
                "last_check_at": datetime.utcnow().isoformat()
            }

            # If all positions closed, mark as in_progress (will be completed in next cycle)
            if new_remaining == 0:
                updates["status"] = "in_progress"

            self.update_transition(transition_id, updates)

            logger.info(f"Marked {position_symbol} as closed in transition ({new_closed}/{transition['total_positions']})")
            return True

        except Exception as e:
            log_error_with_context(e, "mark_position_closed_in_transition", {
                "transition_id": transition_id,
                "position_symbol": position_symbol
            })
            return False

    def update_positions_status(
        self,
        transition_id: str,
        positions_in_profit: int,
        positions_in_loss: int
    ) -> bool:
        """
        Update profit/loss counts for positions in transition.

        Args:
            transition_id: Transition UUID
            positions_in_profit: Count of positions currently in profit
            positions_in_loss: Count of positions currently in loss

        Returns:
            True if successful
        """
        try:
            updates = {
                "positions_in_profit": positions_in_profit,
                "positions_in_loss": positions_in_loss,
                "last_check_at": datetime.utcnow().isoformat()
            }

            return self.update_transition(transition_id, updates)

        except Exception as e:
            log_error_with_context(e, "update_positions_status", {
                "transition_id": transition_id
            })
            return False

    def add_transition_log(
        self,
        transition_id: str,
        message: str,
        level: str = "INFO"
    ) -> bool:
        """
        Append a log entry to transition_log.

        Args:
            transition_id: Transition UUID
            message: Log message
            level: Log level (INFO/WARNING/ERROR)

        Returns:
            True if successful
        """
        try:
            # Get current log
            transition = self.get_transition_by_id(transition_id)
            if not transition:
                return False

            current_log = transition.get("transition_log", [])

            # Append new entry
            new_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": level,
                "message": message
            }
            current_log.append(new_entry)

            # Keep only last 100 entries to avoid excessive growth
            if len(current_log) > 100:
                current_log = current_log[-100:]

            # Update
            return self.update_transition(transition_id, {"transition_log": current_log})

        except Exception as e:
            log_error_with_context(e, "add_transition_log", {
                "transition_id": transition_id,
                "message": message
            })
            return False

    def complete_transition(
        self,
        transition_id: str,
        total_pnl: float,
        total_pnl_pct: float
    ) -> bool:
        """
        Mark transition as completed.

        Args:
            transition_id: Transition UUID
            total_pnl: Total realized P&L in dollars
            total_pnl_pct: Total realized P&L in percentage

        Returns:
            True if successful
        """
        try:
            updates = {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "total_pnl": total_pnl,
                "total_pnl_pct": total_pnl_pct
            }

            self.update_transition(transition_id, updates)

            # Clear in_transition flags
            self.client.table("trading_positions") \
                .update({"in_transition": False}) \
                .eq("transition_id", transition_id) \
                .execute()

            logger.info(f"Completed transition {transition_id}: P&L ${total_pnl:.2f} ({total_pnl_pct:+.2f}%)")
            return True

        except Exception as e:
            log_error_with_context(e, "complete_transition", {
                "transition_id": transition_id
            })
            return False

    def cancel_transition(self, transition_id: str, reason: str) -> bool:
        """
        Cancel an active transition.

        Args:
            transition_id: Transition UUID
            reason: Cancellation reason

        Returns:
            True if successful
        """
        try:
            updates = {
                "status": "cancelled",
                "last_error": reason,
                "completed_at": datetime.utcnow().isoformat()
            }

            self.update_transition(transition_id, updates)

            # Clear in_transition flags
            self.client.table("trading_positions") \
                .update({"in_transition": False}) \
                .eq("transition_id", transition_id) \
                .execute()

            logger.warning(f"Cancelled transition {transition_id}: {reason}")
            return True

        except Exception as e:
            log_error_with_context(e, "cancel_transition", {
                "transition_id": transition_id,
                "reason": reason
            })
            return False

    def fail_transition(self, transition_id: str, error: str) -> bool:
        """
        Mark transition as failed.

        Args:
            transition_id: Transition UUID
            error: Error message

        Returns:
            True if successful
        """
        try:
            transition = self.get_transition_by_id(transition_id)
            if not transition:
                return False

            updates = {
                "status": "failed",
                "last_error": error,
                "error_count": transition.get("error_count", 0) + 1,
                "completed_at": datetime.utcnow().isoformat()
            }

            self.update_transition(transition_id, updates)

            # Clear in_transition flags
            self.client.table("trading_positions") \
                .update({"in_transition": False}) \
                .eq("transition_id", transition_id) \
                .execute()

            logger.error(f"Failed transition {transition_id}: {error}")
            return True

        except Exception as e:
            log_error_with_context(e, "fail_transition", {
                "transition_id": transition_id,
                "error": error
            })
            return False

    def set_retry_after(self, transition_id: str, minutes: int) -> bool:
        """
        Set retry_after timestamp for exponential backoff.

        Args:
            transition_id: Transition UUID
            minutes: Minutes to wait before retry

        Returns:
            True if successful
        """
        try:
            retry_after = datetime.utcnow() + timedelta(minutes=minutes)
            return self.update_transition(transition_id, {
                "retry_after": retry_after.isoformat()
            })

        except Exception as e:
            log_error_with_context(e, "set_retry_after", {
                "transition_id": transition_id,
                "minutes": minutes
            })
            return False

    def approve_manual_transition(self, transition_id: str, approved_by: str = "dashboard_user") -> bool:
        """
        Approve a manual transition.

        Args:
            transition_id: Transition UUID
            approved_by: User who approved

        Returns:
            True if successful
        """
        try:
            updates = {
                "manual_override_approved": True,
                "manual_override_at": datetime.utcnow().isoformat(),
                "manual_override_by": approved_by
            }

            self.update_transition(transition_id, updates)
            self.add_transition_log(transition_id, f"Manually approved by {approved_by}", "INFO")

            logger.info(f"Manual transition {transition_id} approved by {approved_by}")
            return True

        except Exception as e:
            log_error_with_context(e, "approve_manual_transition", {
                "transition_id": transition_id
            })
            return False

    def get_last_completed_transition(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent completed transition.
        Used to detect exchange changes.

        Returns:
            Transition dict if found, None otherwise
        """
        try:
            result = self.client.table("trading_exchange_transitions") \
                .select("*") \
                .eq("status", "completed") \
                .order("completed_at", desc=True) \
                .limit(1) \
                .execute()

            if result.data:
                return result.data[0]

            return None

        except Exception as e:
            log_error_with_context(e, "get_last_completed_transition")
            return None


# This will be imported by database/operations.py
# Usage: from database.transition_ops import TransitionOperations
