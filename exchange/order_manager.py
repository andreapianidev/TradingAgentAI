"""
Order management functionality.
"""
from typing import Dict, Any, Optional
from datetime import datetime

from exchange.hyperliquid_client import exchange_client
from database.operations import db_ops
from config.constants import (
    ACTION_OPEN, ACTION_CLOSE, ACTION_HOLD,
    EXECUTION_EXECUTED, EXECUTION_FAILED, EXECUTION_SKIPPED,
    EXIT_SIGNAL_REVERSAL
)
from utils.logger import get_logger, log_execution

logger = get_logger(__name__)


class OrderManager:
    """Manages order execution and tracking."""

    def __init__(self):
        """Initialize the order manager."""
        self.client = exchange_client

    def execute_decision(
        self,
        decision: Dict[str, Any],
        context_id: int
    ) -> Dict[str, Any]:
        """
        Execute a trading decision from the LLM.

        Args:
            decision: LLM decision dictionary
            context_id: ID of the market context

        Returns:
            Execution result
        """
        action = decision.get("action")
        symbol = decision.get("symbol")

        logger.info(f"Executing decision: {action} {symbol}")

        if action == ACTION_HOLD:
            return self._handle_hold(decision, context_id)
        elif action == ACTION_OPEN:
            return self._handle_open(decision, context_id)
        elif action == ACTION_CLOSE:
            return self._handle_close(decision, context_id)
        else:
            logger.warning(f"Unknown action: {action}")
            return {"success": False, "error": f"Unknown action: {action}"}

    def _handle_hold(
        self,
        decision: Dict[str, Any],
        context_id: int
    ) -> Dict[str, Any]:
        """Handle a HOLD decision."""
        symbol = decision.get("symbol")

        # Save decision to database
        trade_id = db_ops.save_trade_decision(
            context_id=context_id,
            symbol=symbol,
            decision=decision,
            execution_status=EXECUTION_SKIPPED
        )

        logger.info(f"HOLD decision for {symbol} - no action taken")

        return {
            "success": True,
            "action": "hold",
            "trade_id": trade_id,
            "message": "No action taken"
        }

    def _handle_open(
        self,
        decision: Dict[str, Any],
        context_id: int
    ) -> Dict[str, Any]:
        """Handle an OPEN position decision."""
        symbol = decision.get("symbol")
        direction = decision.get("direction")
        leverage = decision.get("leverage", 3)
        size_pct = decision.get("position_size_pct", 2.0)
        stop_loss_pct = decision.get("stop_loss_pct", 3.0)
        take_profit_pct = decision.get("take_profit_pct", 5.0)

        # Check if already has position
        if self.client.has_open_position(symbol):
            logger.warning(f"Already has open position for {symbol}, skipping")
            trade_id = db_ops.save_trade_decision(
                context_id=context_id,
                symbol=symbol,
                decision=decision,
                execution_status=EXECUTION_SKIPPED
            )
            return {
                "success": False,
                "error": "Position already exists",
                "trade_id": trade_id
            }

        # Save decision first
        trade_id = db_ops.save_trade_decision(
            context_id=context_id,
            symbol=symbol,
            decision=decision,
            execution_status="pending"
        )

        # Execute the order
        result = self.client.open_position(
            symbol=symbol,
            direction=direction,
            size_pct=size_pct,
            leverage=leverage,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )

        if result.get("success"):
            # Update trade decision with execution details
            db_ops.update_trade_execution(
                trade_id=trade_id,
                status=EXECUTION_EXECUTED,
                entry_price=result.get("entry_price"),
                entry_quantity=result.get("quantity"),
                order_id=result.get("order_id"),
                details=result
            )

            # Create position record in database
            db_ops.create_position(
                symbol=symbol,
                direction=direction,
                entry_price=result.get("entry_price"),
                quantity=result.get("quantity"),
                leverage=leverage,
                stop_loss_price=result.get("stop_loss_price"),
                take_profit_price=result.get("take_profit_price"),
                entry_trade_id=trade_id
            )

            log_execution(
                symbol=symbol,
                action=f"OPEN {direction.upper()}",
                price=result.get("entry_price"),
                quantity=result.get("quantity"),
                order_id=result.get("order_id", "N/A")
            )

            return {
                "success": True,
                "action": "open",
                "trade_id": trade_id,
                "result": result
            }
        else:
            # Update as failed
            db_ops.update_trade_execution(
                trade_id=trade_id,
                status=EXECUTION_FAILED,
                details={"error": result.get("error")}
            )

            return {
                "success": False,
                "error": result.get("error"),
                "trade_id": trade_id
            }

    def _handle_close(
        self,
        decision: Dict[str, Any],
        context_id: int
    ) -> Dict[str, Any]:
        """Handle a CLOSE position decision."""
        symbol = decision.get("symbol")

        # Check if has position to close
        if not self.client.has_open_position(symbol):
            logger.warning(f"No open position for {symbol} to close")
            trade_id = db_ops.save_trade_decision(
                context_id=context_id,
                symbol=symbol,
                decision=decision,
                execution_status=EXECUTION_SKIPPED
            )
            return {
                "success": False,
                "error": "No position to close",
                "trade_id": trade_id
            }

        # Get the database position record
        db_position = db_ops.get_position_by_symbol(symbol)

        # Save decision first
        trade_id = db_ops.save_trade_decision(
            context_id=context_id,
            symbol=symbol,
            decision=decision,
            execution_status="pending"
        )

        # Execute the close
        result = self.client.close_position(symbol)

        if result.get("success"):
            # Update trade decision
            db_ops.update_trade_execution(
                trade_id=trade_id,
                status=EXECUTION_EXECUTED,
                entry_price=result.get("exit_price"),
                details=result
            )

            # Close position in database
            if db_position:
                db_ops.close_position(
                    position_id=db_position.id,
                    exit_price=result.get("exit_price"),
                    exit_reason=EXIT_SIGNAL_REVERSAL,
                    exit_trade_id=trade_id
                )

            log_execution(
                symbol=symbol,
                action="CLOSE",
                price=result.get("exit_price"),
                quantity=0,  # Already closed
                order_id="N/A"
            )

            return {
                "success": True,
                "action": "close",
                "trade_id": trade_id,
                "result": result
            }
        else:
            # Update as failed
            db_ops.update_trade_execution(
                trade_id=trade_id,
                status=EXECUTION_FAILED,
                details={"error": result.get("error")}
            )

            return {
                "success": False,
                "error": result.get("error"),
                "trade_id": trade_id
            }


# Global order manager instance
order_manager = OrderManager()
