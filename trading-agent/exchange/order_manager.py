"""
Order management functionality.
"""
from typing import Dict, Any, Optional
from datetime import datetime

from config.settings import settings
from database.operations import db_ops
from config.constants import (
    ACTION_OPEN, ACTION_CLOSE, ACTION_HOLD,
    EXECUTION_EXECUTED, EXECUTION_FAILED, EXECUTION_SKIPPED,
    EXIT_SIGNAL_REVERSAL
)
from exchange.exchange_factory import get_exchange_client
from core.cost_tracker import calculate_trading_fee
from utils.logger import get_logger, log_execution

logger = get_logger(__name__)


class OrderManager:
    """Manages order execution and tracking."""

    def __init__(self):
        """Initialize the order manager with appropriate client based on exchange settings."""
        # Use exchange_factory to get the correct client based on EXCHANGE setting
        # auto_connect=True ensures the client is connected and ready to execute trades
        self.client = get_exchange_client(auto_connect=True)
        self.is_paper_trading = settings.PAPER_TRADING or settings.ALPACA_PAPER_TRADING

        exchange_name = settings.EXCHANGE.lower()
        mode = "PAPER" if self.is_paper_trading else "LIVE"
        logger.info(f"OrderManager initialized in {mode} TRADING mode (Exchange: {exchange_name})")

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

            # Save trading fee
            try:
                trade_value = float(result.get("entry_price", 0)) * float(result.get("quantity", 0))
                actual_fee, estimated_fee = calculate_trading_fee(
                    trade_value_usd=trade_value,
                    is_paper=self.is_paper_trading
                )
                db_ops.save_trading_fee(
                    symbol=symbol,
                    trade_value_usd=trade_value,
                    fee_usd=actual_fee,
                    fee_type="taker",
                    estimated_fee_usd=estimated_fee
                )
                logger.debug(f"Saved open trading fee: ${actual_fee:.6f} (est. live: ${estimated_fee:.6f})")
            except Exception as e:
                logger.warning(f"Failed to save trading fee: {e}")

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

                # Save trading fee for close
                try:
                    qty = float(db_position.quantity) if hasattr(db_position, 'quantity') else 0
                    trade_value = float(result.get("exit_price", 0)) * qty
                    actual_fee, estimated_fee = calculate_trading_fee(
                        trade_value_usd=trade_value,
                        is_paper=self.is_paper_trading
                    )
                    db_ops.save_trading_fee(
                        symbol=symbol,
                        trade_value_usd=trade_value,
                        fee_usd=actual_fee,
                        fee_type="taker",
                        position_id=str(db_position.id) if hasattr(db_position, 'id') else None,
                        estimated_fee_usd=estimated_fee
                    )
                    logger.debug(f"Saved close trading fee: ${actual_fee:.6f} (est. live: ${estimated_fee:.6f})")
                except Exception as e:
                    logger.warning(f"Failed to save close trading fee: {e}")

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
