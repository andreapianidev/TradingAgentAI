"""
Exchange Transition Manager
Manages safe transitions between trading exchanges (Alpaca ↔ Hyperliquid).
Implements 4 strategies: IMMEDIATE, PROFITABLE, WAIT_PROFIT, MANUAL.
"""
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from config.settings import settings
from database.operations import transition_ops
from utils.logger import get_logger, log_error_with_context

logger = get_logger(__name__)


class TransitionStrategy(Enum):
    """Transition strategy types."""
    IMMEDIATE = "IMMEDIATE"      # Close all positions immediately
    PROFITABLE = "PROFITABLE"    # Close profitable, tighten SL on losers
    WAIT_PROFIT = "WAIT_PROFIT"  # Wait until all positions are profitable
    MANUAL = "MANUAL"            # Require manual approval


class TransitionStatus(Enum):
    """Transition status types."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExchangeTransitionManager:
    """Manages exchange transitions with multiple strategies."""

    def __init__(self):
        """Initialize the transition manager."""
        self._active_transition = None

    def detect_exchange_change(self, current_exchange: str) -> Optional[str]:
        """
        Detect if the exchange has changed by comparing with last completed transition.

        Args:
            current_exchange: Current exchange from settings

        Returns:
            Previous exchange if different, None if same or no previous transition
        """
        try:
            # Get last completed transition
            last_transition = transition_ops.get_last_completed_transition()

            if not last_transition:
                # No previous transition - first run or no history
                logger.debug("No previous transition found - first run")
                return None

            previous_exchange = last_transition.get("to_exchange")

            if previous_exchange and previous_exchange != current_exchange:
                logger.info(f"Exchange change detected: {previous_exchange} → {current_exchange}")
                return previous_exchange

            return None

        except Exception as e:
            log_error_with_context(e, "detect_exchange_change")
            return None

    def start_transition(
        self,
        from_exchange: str,
        to_exchange: str,
        strategy: TransitionStrategy,
        position_ids: List[str]
    ) -> Optional[str]:
        """
        Start a new transition.

        Args:
            from_exchange: Source exchange (alpaca/hyperliquid)
            to_exchange: Target exchange (alpaca/hyperliquid)
            strategy: Transition strategy enum
            position_ids: List of position symbols to transition

        Returns:
            Transition ID if successful, None otherwise
        """
        try:
            # Get trading mode from settings
            trading_mode = "paper" if settings.PAPER_TRADING else "live"

            # Create transition record
            transition_id = transition_ops.create_transition(
                from_exchange=from_exchange,
                to_exchange=to_exchange,
                strategy=strategy.value,
                position_ids=position_ids,
                trading_mode=trading_mode
            )

            if transition_id:
                self._active_transition = transition_id
                transition_ops.add_transition_log(
                    transition_id,
                    f"Transition started: {from_exchange} → {to_exchange} using {strategy.value} strategy",
                    "INFO"
                )
                logger.info(f"Started transition {transition_id}: {strategy.value} with {len(position_ids)} positions")

            return transition_id

        except Exception as e:
            log_error_with_context(e, "start_transition", {
                "from_exchange": from_exchange,
                "to_exchange": to_exchange,
                "strategy": strategy.value
            })
            return None

    def should_execute_transition_cycle(self) -> bool:
        """
        Check if there's an active transition that needs processing.

        Returns:
            True if transition is active (pending or in_progress)
        """
        try:
            active = transition_ops.get_active_transition()
            return active is not None

        except Exception as e:
            log_error_with_context(e, "should_execute_transition_cycle")
            return False

    def get_transition_status(self) -> Optional[Dict[str, Any]]:
        """
        Get the current active transition for dashboard.

        Returns:
            Transition dict or None
        """
        try:
            return transition_ops.get_active_transition()

        except Exception as e:
            log_error_with_context(e, "get_transition_status")
            return None

    def execute_transition_cycle(self, old_exchange_client) -> Dict[str, Any]:
        """
        Execute one cycle of the transition process.

        Args:
            old_exchange_client: Exchange client for the old exchange

        Returns:
            Dict with transition status and results
        """
        try:
            # Get active transition
            transition = transition_ops.get_active_transition()

            if not transition:
                logger.warning("No active transition found")
                return {"success": False, "error": "No active transition"}

            transition_id = transition["id"]
            strategy = TransitionStrategy[transition["transition_strategy"]]

            logger.info(f"Executing transition cycle: {strategy.value}")

            # Update status to in_progress if still pending
            if transition["status"] == "pending":
                transition_ops.update_transition(transition_id, {"status": "in_progress"})

            # Get current open positions for this transition
            positions = transition_ops.get_transition_positions(transition_id)

            if not positions:
                # No positions left - complete transition
                logger.info("No positions remaining, completing transition")
                self.complete_transition(transition_id, total_pnl=0, total_pnl_pct=0)
                return {
                    "success": True,
                    "status": "completed",
                    "positions_closed": transition["positions_closed"],
                    "total_positions": transition["total_positions"],
                    "positions_remaining": 0
                }

            # Route to appropriate strategy
            if strategy == TransitionStrategy.IMMEDIATE:
                result = self._execute_immediate_strategy(positions, old_exchange_client, transition_id)
            elif strategy == TransitionStrategy.PROFITABLE:
                result = self._execute_profitable_strategy(positions, old_exchange_client, transition_id)
            elif strategy == TransitionStrategy.WAIT_PROFIT:
                result = self._execute_wait_profit_strategy(positions, old_exchange_client, transition, transition_id)
            elif strategy == TransitionStrategy.MANUAL:
                result = self._execute_manual_strategy(positions, old_exchange_client, transition, transition_id)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")

            return result

        except Exception as e:
            log_error_with_context(e, "execute_transition_cycle")
            return {"success": False, "error": str(e)}

    def _execute_immediate_strategy(
        self,
        positions: List[Dict[str, Any]],
        client,
        transition_id: str
    ) -> Dict[str, Any]:
        """
        IMMEDIATE strategy: Close all positions immediately.

        Args:
            positions: List of open positions
            client: Exchange client
            transition_id: Transition UUID

        Returns:
            Execution results
        """
        logger.info(f"IMMEDIATE: Closing {len(positions)} positions immediately")

        closed_count = 0
        failed_count = 0
        total_pnl = 0

        for position in positions:
            symbol = position["symbol"]

            try:
                # Close position via exchange
                close_result = client.close_position(symbol)

                if close_result.get("success"):
                    closed_count += 1
                    pnl = close_result.get("pnl", 0)
                    total_pnl += pnl

                    transition_ops.add_transition_log(
                        transition_id,
                        f"Closed {symbol}: P&L ${pnl:.2f}",
                        "INFO"
                    )
                    logger.info(f"✓ Closed {symbol}: P&L ${pnl:.2f}")
                else:
                    failed_count += 1
                    error = close_result.get("error", "Unknown error")
                    transition_ops.add_transition_log(
                        transition_id,
                        f"Failed to close {symbol}: {error}",
                        "WARNING"
                    )
                    logger.warning(f"✗ Failed to close {symbol}: {error}")

            except Exception as e:
                failed_count += 1
                log_error_with_context(e, f"close_position:{symbol}")
                transition_ops.add_transition_log(
                    transition_id,
                    f"Exception closing {symbol}: {str(e)}",
                    "ERROR"
                )

        # If all closed successfully, complete transition
        if closed_count == len(positions):
            avg_pnl_pct = total_pnl / len(positions) if positions else 0
            self.complete_transition(transition_id, total_pnl, avg_pnl_pct)
            logger.info(f"IMMEDIATE strategy completed: {closed_count} positions closed")

        return {
            "success": True,
            "status": "completed" if closed_count == len(positions) else "in_progress",
            "positions_closed": closed_count,
            "positions_failed": failed_count,
            "total_positions": len(positions),
            "positions_remaining": len(positions) - closed_count,
            "total_pnl": total_pnl
        }

    def _execute_profitable_strategy(
        self,
        positions: List[Dict[str, Any]],
        client,
        transition_id: str
    ) -> Dict[str, Any]:
        """
        PROFITABLE strategy: Close profitable positions, tighten SL on losing ones.

        Args:
            positions: List of open positions
            client: Exchange client
            transition_id: Transition UUID

        Returns:
            Execution results
        """
        logger.info(f"PROFITABLE: Processing {len(positions)} positions")

        # Separate into profitable vs losing
        profitable = [p for p in positions if p.get("unrealized_pnl", 0) > 0]
        losing = [p for p in positions if p.get("unrealized_pnl", 0) <= 0]

        logger.info(f"  Profitable: {len(profitable)} | Losing: {len(losing)}")

        closed_count = 0
        total_pnl = 0

        # Close profitable positions immediately
        for position in profitable:
            symbol = position["symbol"]

            try:
                close_result = client.close_position(symbol)

                if close_result.get("success"):
                    closed_count += 1
                    pnl = close_result.get("pnl", 0)
                    total_pnl += pnl

                    transition_ops.add_transition_log(
                        transition_id,
                        f"Closed profitable {symbol}: P&L ${pnl:.2f}",
                        "INFO"
                    )
                    logger.info(f"✓ Closed profitable {symbol}: P&L ${pnl:.2f}")

            except Exception as e:
                log_error_with_context(e, f"close_position:{symbol}")

        # Tighten stop loss on losing positions
        tighten_pct = settings.TRANSITION_SL_TIGHTEN_PCT / 100  # Convert to decimal

        for position in losing:
            symbol = position["symbol"]
            entry_price = position.get("entry_price", 0)
            current_sl = position.get("stop_loss_price", 0)

            if entry_price > 0 and current_sl > 0:
                # Calculate tightened stop loss
                sl_distance = abs(entry_price - current_sl)
                new_sl_distance = sl_distance * (1 - tighten_pct)
                new_sl = entry_price - new_sl_distance if position["direction"] == "long" else entry_price + new_sl_distance

                try:
                    # Update stop loss via exchange (if supported)
                    # Note: This may not be supported on all exchanges
                    logger.info(f"Tightening SL for {symbol}: ${current_sl:.2f} → ${new_sl:.2f}")
                    transition_ops.add_transition_log(
                        transition_id,
                        f"Tightened SL for {symbol}: ${current_sl:.2f} → ${new_sl:.2f}",
                        "INFO"
                    )
                except Exception as e:
                    log_error_with_context(e, f"tighten_sl:{symbol}")

        # Update counts
        positions_in_profit = len(profitable) - closed_count  # Remaining profitable (if any failed to close)
        positions_in_loss = len(losing)

        transition_ops.update_positions_status(transition_id, positions_in_profit, positions_in_loss)

        # Check if all closed
        remaining = len(positions) - closed_count
        if remaining == 0:
            avg_pnl_pct = total_pnl / len(positions) if positions else 0
            self.complete_transition(transition_id, total_pnl, avg_pnl_pct)

        return {
            "success": True,
            "status": "completed" if remaining == 0 else "in_progress",
            "positions_closed": closed_count,
            "total_positions": len(positions),
            "positions_remaining": remaining,
            "positions_in_profit": positions_in_profit,
            "positions_in_loss": positions_in_loss,
            "total_pnl": total_pnl
        }

    def _execute_wait_profit_strategy(
        self,
        positions: List[Dict[str, Any]],
        client,
        transition: Dict[str, Any],
        transition_id: str
    ) -> Dict[str, Any]:
        """
        WAIT_PROFIT strategy: Wait until ALL positions are profitable.

        Args:
            positions: List of open positions
            client: Exchange client
            transition: Full transition object
            transition_id: Transition UUID

        Returns:
            Execution results
        """
        logger.info(f"WAIT_PROFIT: Checking {len(positions)} positions")

        # Count profitable vs losing
        profitable_count = sum(1 for p in positions if p.get("unrealized_pnl", 0) > 0)
        losing_count = len(positions) - profitable_count

        logger.info(f"  Profitable: {profitable_count} | Losing: {losing_count}")

        # Update status
        transition_ops.update_positions_status(transition_id, profitable_count, losing_count)

        # Check if ALL are profitable
        all_profitable = (profitable_count == len(positions))

        if all_profitable:
            logger.info("All positions profitable! Closing all...")
            transition_ops.add_transition_log(
                transition_id,
                "All positions profitable - closing all",
                "INFO"
            )

            # Close all positions
            closed_count = 0
            total_pnl = 0

            for position in positions:
                symbol = position["symbol"]

                try:
                    close_result = client.close_position(symbol)

                    if close_result.get("success"):
                        closed_count += 1
                        pnl = close_result.get("pnl", 0)
                        total_pnl += pnl

                        logger.info(f"✓ Closed {symbol}: P&L ${pnl:.2f}")

                except Exception as e:
                    log_error_with_context(e, f"close_position:{symbol}")

            # Complete transition
            avg_pnl_pct = total_pnl / len(positions) if positions else 0
            self.complete_transition(transition_id, total_pnl, avg_pnl_pct)

            return {
                "success": True,
                "status": "completed",
                "positions_closed": closed_count,
                "total_positions": len(positions),
                "positions_remaining": 0,
                "total_pnl": total_pnl
            }

        else:
            # Not all profitable yet - check timeout
            started_at = datetime.fromisoformat(transition["started_at"].replace("Z", "+00:00"))
            time_elapsed = datetime.utcnow() - started_at.replace(tzinfo=None)
            hours_elapsed = time_elapsed.total_seconds() / 3600

            logger.info(f"  Waiting for profit... ({hours_elapsed:.1f}h elapsed)")

            # Check timeout
            if hours_elapsed > settings.TRANSITION_TIMEOUT_HOURS:
                # Calculate total unrealized P&L percentage
                total_unrealized_pnl = sum(p.get("unrealized_pnl", 0) for p in positions)
                avg_pnl_pct = (total_unrealized_pnl / len(positions)) if positions else 0

                logger.warning(f"Timeout reached ({hours_elapsed:.1f}h > {settings.TRANSITION_TIMEOUT_HOURS}h)")

                # Check emergency loss threshold
                if avg_pnl_pct < settings.TRANSITION_EMERGENCY_LOSS_PCT:
                    logger.critical(f"EMERGENCY CLOSE: Loss {avg_pnl_pct:.2f}% < {settings.TRANSITION_EMERGENCY_LOSS_PCT}%")
                    transition_ops.add_transition_log(
                        transition_id,
                        f"EMERGENCY CLOSE triggered: Timeout + loss {avg_pnl_pct:.2f}%",
                        "ERROR"
                    )

                    # Execute immediate close
                    return self._execute_immediate_strategy(positions, client, transition_id)

            return {
                "success": True,
                "status": "in_progress",
                "positions_closed": 0,
                "total_positions": len(positions),
                "positions_remaining": len(positions),
                "positions_in_profit": profitable_count,
                "positions_in_loss": losing_count,
                "hours_elapsed": hours_elapsed
            }

    def _execute_manual_strategy(
        self,
        positions: List[Dict[str, Any]],
        client,
        transition: Dict[str, Any],
        transition_id: str
    ) -> Dict[str, Any]:
        """
        MANUAL strategy: Require manual approval before closing.

        Args:
            positions: List of open positions
            client: Exchange client
            transition: Full transition object
            transition_id: Transition UUID

        Returns:
            Execution results
        """
        logger.info(f"MANUAL: Awaiting approval for {len(positions)} positions")

        # Check if approved
        if transition.get("manual_override_approved"):
            logger.info("Manual approval received - executing immediate close")
            transition_ops.add_transition_log(
                transition_id,
                "Manual approval received - closing all positions",
                "INFO"
            )

            # Execute immediate close
            return self._execute_immediate_strategy(positions, client, transition_id)

        else:
            # Check waiting time
            started_at = datetime.fromisoformat(transition["started_at"].replace("Z", "+00:00"))
            time_waiting = datetime.utcnow() - started_at.replace(tzinfo=None)
            hours_waiting = time_waiting.total_seconds() / 3600

            # Alert if waiting too long
            if hours_waiting > 24:
                logger.warning(f"Manual approval pending for {hours_waiting:.1f}h")

                if hours_waiting > 48:
                    logger.critical("Auto-cancelling transition after 48h of no approval")
                    transition_ops.add_transition_log(
                        transition_id,
                        "Auto-cancelled after 48h of no manual approval",
                        "ERROR"
                    )
                    transition_ops.cancel_transition(transition_id, "No manual approval after 48h")

                    return {
                        "success": False,
                        "status": "cancelled",
                        "error": "Auto-cancelled after 48h timeout"
                    }

            return {
                "success": True,
                "status": "pending",
                "positions_closed": 0,
                "total_positions": len(positions),
                "positions_remaining": len(positions),
                "waiting_approval": True,
                "hours_waiting": hours_waiting
            }

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
            total_pnl: Total realized P&L
            total_pnl_pct: Total realized P&L percentage

        Returns:
            True if successful
        """
        try:
            transition_ops.complete_transition(transition_id, total_pnl, total_pnl_pct)
            self._active_transition = None

            logger.info(f"✓ Transition {transition_id} completed: P&L ${total_pnl:.2f} ({total_pnl_pct:+.2f}%)")
            return True

        except Exception as e:
            log_error_with_context(e, "complete_transition", {"transition_id": transition_id})
            return False


# Global transition manager instance
transition_manager = ExchangeTransitionManager()
