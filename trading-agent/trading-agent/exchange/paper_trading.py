"""
Paper Trading Client - Simulates trading with real market data.
Uses real price data from configured exchange but executes orders virtually.
"""
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# File to persist paper trading state
PAPER_STATE_FILE = Path("paper_trading_data/paper_trading_state.json")


class PaperTradingClient:
    """
    Paper trading client that uses real market data but simulates order execution.
    Perfect for testing trading strategies without risking real money.
    """

    def __init__(self):
        """Initialize the paper trading client."""
        # Use configured exchange client for market data
        from exchange.exchange_factory import get_exchange_client
        self._real_client = get_exchange_client()
        self._connected = False

        # Virtual portfolio state
        self._initial_balance = settings.PAPER_TRADING_INITIAL_BALANCE
        self._balance = self._initial_balance
        self._margin_used = 0.0
        self._positions: Dict[str, Dict[str, Any]] = {}  # symbol -> position
        self._order_counter = 0
        self._trade_history: List[Dict[str, Any]] = []

        # Load persisted state if exists
        self._load_state()

    def connect(self) -> bool:
        """Connect to exchange for real market data."""
        try:
            if self._real_client.connect():
                self._connected = True
                logger.info("=" * 60)
                logger.info("PAPER TRADING MODE ACTIVE")
                logger.info(f"Initial Balance: ${self._balance:,.2f} USDC")
                logger.info("Real market data - Virtual execution")
                logger.info("=" * 60)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to connect paper trading client: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect and save state."""
        self._save_state()
        self._real_client.disconnect()
        self._connected = False
        logger.info("Paper trading client disconnected")

    # ================== MARKET DATA (Real) ==================

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch real ticker data."""
        return self._real_client.fetch_ticker(symbol)

    def fetch_ohlcv(self, symbol: str, timeframe: str = "15m", limit: int = 200) -> List[List]:
        """Fetch real OHLCV data."""
        return self._real_client.fetch_ohlcv(symbol, timeframe, limit)

    def fetch_order_book(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """Fetch real order book data."""
        return self._real_client.fetch_order_book(symbol, limit)

    # ================== PORTFOLIO (Simulated) ==================

    def fetch_portfolio(self) -> Dict[str, Any]:
        """
        Fetch simulated portfolio state with real-time P&L calculation.
        """
        # Calculate unrealized P&L for open positions
        total_unrealized_pnl = 0.0
        positions_with_pnl = []

        for symbol, pos in self._positions.items():
            ticker = self.fetch_ticker(symbol)
            current_price = ticker.get("price", pos["entry_price"])

            # Calculate unrealized P&L
            if pos["direction"] == "long":
                pnl = (current_price - pos["entry_price"]) * pos["quantity"]
                pnl_pct = ((current_price / pos["entry_price"]) - 1) * 100 * pos["leverage"]
            else:
                pnl = (pos["entry_price"] - current_price) * pos["quantity"]
                pnl_pct = ((pos["entry_price"] / current_price) - 1) * 100 * pos["leverage"]

            total_unrealized_pnl += pnl

            positions_with_pnl.append({
                "symbol": symbol,
                "direction": pos["direction"],
                "entry_price": pos["entry_price"],
                "quantity": pos["quantity"],
                "notional": pos["quantity"] * current_price,
                "leverage": pos["leverage"],
                "unrealized_pnl": pnl,
                "unrealized_pnl_pct": pnl_pct,
                "liquidation_price": pos.get("liquidation_price", 0),
                "stop_loss_price": pos.get("stop_loss_price"),
                "take_profit_price": pos.get("take_profit_price"),
                "current_price": current_price,
            })

        # Calculate total equity
        total_equity = self._balance + total_unrealized_pnl

        # Calculate exposure
        exposure = 0.0
        if total_equity > 0:
            for pos in positions_with_pnl:
                exposure += abs(pos["notional"]) / total_equity

        return {
            "total_equity": total_equity,
            "available_balance": self._balance - self._margin_used,
            "margin_used": self._margin_used,
            "exposure_pct": exposure * 100,
            "positions": positions_with_pnl,
            "unrealized_pnl": total_unrealized_pnl,
            "mode": "PAPER",
        }

    def _fetch_positions_internal(self) -> List[Dict[str, Any]]:
        """Return current positions."""
        portfolio = self.fetch_portfolio()
        return portfolio.get("positions", [])

    # ================== TRADING (Simulated) ==================

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage (simulated - just logs)."""
        logger.info(f"[PAPER] Set leverage to {leverage}x for {symbol}")
        return True

    def open_position(
        self,
        symbol: str,
        direction: str,
        size_pct: float,
        leverage: int,
        stop_loss_pct: float = None,
        take_profit_pct: float = None
    ) -> Dict[str, Any]:
        """
        Open a simulated position using real market price.
        """
        try:
            # Check if already has position
            if symbol in self._positions:
                logger.warning(f"[PAPER] Already has position for {symbol}")
                return {"success": False, "error": "Position already exists"}

            # Get real current price
            ticker = self.fetch_ticker(symbol)
            current_price = ticker.get("price", 0)

            if current_price <= 0:
                return {"success": False, "error": f"Invalid price for {symbol}"}

            # Calculate position size
            available = self._balance - self._margin_used
            position_value = available * (size_pct / 100)
            margin_required = position_value / leverage
            quantity = position_value / current_price

            if margin_required > available:
                return {"success": False, "error": "Insufficient margin"}

            # Calculate SL/TP prices
            sl_price = None
            tp_price = None

            if stop_loss_pct:
                if direction == "long":
                    sl_price = current_price * (1 - stop_loss_pct / 100)
                else:
                    sl_price = current_price * (1 + stop_loss_pct / 100)

            if take_profit_pct:
                if direction == "long":
                    tp_price = current_price * (1 + take_profit_pct / 100)
                else:
                    tp_price = current_price * (1 - take_profit_pct / 100)

            # Calculate liquidation price (simplified)
            liq_distance = 1 / leverage * 0.9  # 90% of margin
            if direction == "long":
                liquidation_price = current_price * (1 - liq_distance)
            else:
                liquidation_price = current_price * (1 + liq_distance)

            # Generate order ID
            self._order_counter += 1
            order_id = f"PAPER-{self._order_counter:06d}"

            # Store position
            self._positions[symbol] = {
                "symbol": symbol,
                "direction": direction,
                "entry_price": current_price,
                "quantity": quantity,
                "leverage": leverage,
                "margin": margin_required,
                "stop_loss_price": sl_price,
                "take_profit_price": tp_price,
                "liquidation_price": liquidation_price,
                "opened_at": datetime.utcnow().isoformat(),
                "order_id": order_id,
            }

            # Update margin used
            self._margin_used += margin_required

            # Log trade
            self._trade_history.append({
                "type": "OPEN",
                "symbol": symbol,
                "direction": direction,
                "price": current_price,
                "quantity": quantity,
                "leverage": leverage,
                "order_id": order_id,
                "timestamp": datetime.utcnow().isoformat(),
            })

            # Save state
            self._save_state()

            logger.info(
                f"[PAPER] Opened {direction.upper()} position: {symbol} @ ${current_price:,.2f} "
                f"| Qty: {quantity:.6f} | Leverage: {leverage}x | Margin: ${margin_required:,.2f}"
            )

            return {
                "success": True,
                "order_id": order_id,
                "entry_price": current_price,
                "quantity": quantity,
                "direction": direction,
                "leverage": leverage,
                "stop_loss_price": sl_price,
                "take_profit_price": tp_price,
            }

        except Exception as e:
            logger.error(f"[PAPER] Failed to open position: {e}")
            return {"success": False, "error": str(e)}

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Close a simulated position using real market price.
        """
        try:
            if symbol not in self._positions:
                logger.warning(f"[PAPER] No position to close for {symbol}")
                return {"success": False, "error": "No position found"}

            position = self._positions[symbol]

            # Get real current price
            ticker = self.fetch_ticker(symbol)
            exit_price = ticker.get("price", position["entry_price"])

            # Calculate P&L
            entry_price = position["entry_price"]
            quantity = position["quantity"]
            leverage = position["leverage"]
            direction = position["direction"]

            if direction == "long":
                pnl = (exit_price - entry_price) * quantity
                pnl_pct = ((exit_price / entry_price) - 1) * 100 * leverage
            else:
                pnl = (entry_price - exit_price) * quantity
                pnl_pct = ((entry_price / exit_price) - 1) * 100 * leverage

            # Update balance
            self._balance += pnl
            self._margin_used -= position["margin"]

            # Log trade
            self._trade_history.append({
                "type": "CLOSE",
                "symbol": symbol,
                "direction": direction,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "quantity": quantity,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "timestamp": datetime.utcnow().isoformat(),
            })

            # Remove position
            del self._positions[symbol]

            # Save state
            self._save_state()

            logger.info(
                f"[PAPER] Closed {direction.upper()} position: {symbol} @ ${exit_price:,.2f} "
                f"| PnL: ${pnl:,.2f} ({pnl_pct:+.2f}%)"
            )

            return {
                "success": True,
                "exit_price": exit_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
            }

        except Exception as e:
            logger.error(f"[PAPER] Failed to close position: {e}")
            return {"success": False, "error": str(e)}

    def check_stop_loss_take_profit(self) -> List[Dict[str, Any]]:
        """
        Check if any positions hit their SL/TP levels.
        Call this periodically to simulate SL/TP execution.

        Returns:
            List of closed positions
        """
        closed = []
        symbols_to_close = []

        for symbol, pos in self._positions.items():
            ticker = self.fetch_ticker(symbol)
            current_price = ticker.get("price", 0)

            if current_price <= 0:
                continue

            sl_price = pos.get("stop_loss_price")
            tp_price = pos.get("take_profit_price")
            direction = pos["direction"]

            # Check stop loss
            if sl_price:
                if direction == "long" and current_price <= sl_price:
                    symbols_to_close.append((symbol, "stop_loss"))
                elif direction == "short" and current_price >= sl_price:
                    symbols_to_close.append((symbol, "stop_loss"))

            # Check take profit
            if tp_price:
                if direction == "long" and current_price >= tp_price:
                    symbols_to_close.append((symbol, "take_profit"))
                elif direction == "short" and current_price <= tp_price:
                    symbols_to_close.append((symbol, "take_profit"))

            # Check liquidation
            liq_price = pos.get("liquidation_price")
            if liq_price:
                if direction == "long" and current_price <= liq_price:
                    symbols_to_close.append((symbol, "liquidation"))
                elif direction == "short" and current_price >= liq_price:
                    symbols_to_close.append((symbol, "liquidation"))

        # Close positions that hit SL/TP/Liquidation
        for symbol, reason in symbols_to_close:
            result = self.close_position(symbol)
            if result.get("success"):
                result["close_reason"] = reason
                closed.append(result)
                logger.info(f"[PAPER] Position {symbol} closed due to {reason}")

        return closed

    # ================== HELPER METHODS ==================

    def get_total_exposure(self) -> float:
        """Get total exposure as percentage."""
        portfolio = self.fetch_portfolio()
        return portfolio.get("exposure_pct", 0)

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get position for a specific symbol."""
        if symbol not in self._positions:
            return None

        portfolio = self.fetch_portfolio()
        for pos in portfolio.get("positions", []):
            if pos["symbol"] == symbol:
                return pos
        return None

    def has_open_position(self, symbol: str) -> bool:
        """Check if there's an open position for a symbol."""
        return symbol in self._positions

    def get_trade_history(self) -> List[Dict[str, Any]]:
        """Get complete trade history."""
        return self._trade_history.copy()

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for paper trading session."""
        portfolio = self.fetch_portfolio()

        # Calculate stats from trade history
        total_trades = len([t for t in self._trade_history if t["type"] == "CLOSE"])
        winning_trades = len([t for t in self._trade_history if t["type"] == "CLOSE" and t.get("pnl", 0) > 0])
        losing_trades = len([t for t in self._trade_history if t["type"] == "CLOSE" and t.get("pnl", 0) < 0])

        total_pnl = sum(t.get("pnl", 0) for t in self._trade_history if t["type"] == "CLOSE")

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        return {
            "mode": "PAPER TRADING",
            "initial_balance": self._initial_balance,
            "current_equity": portfolio["total_equity"],
            "total_pnl": total_pnl,
            "total_pnl_pct": ((portfolio["total_equity"] / self._initial_balance) - 1) * 100,
            "unrealized_pnl": portfolio["unrealized_pnl"],
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "open_positions": len(self._positions),
        }

    def reset_paper_trading(self) -> None:
        """Reset paper trading to initial state."""
        self._balance = self._initial_balance
        self._margin_used = 0.0
        self._positions = {}
        self._trade_history = []
        self._order_counter = 0
        self._save_state()
        logger.info(f"[PAPER] Reset paper trading. Balance: ${self._balance:,.2f}")

    # ================== STATE PERSISTENCE ==================

    def _save_state(self) -> None:
        """Save paper trading state to file."""
        try:
            PAPER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

            state = {
                "balance": self._balance,
                "margin_used": self._margin_used,
                "positions": self._positions,
                "trade_history": self._trade_history,
                "order_counter": self._order_counter,
                "initial_balance": self._initial_balance,
                "last_updated": datetime.utcnow().isoformat(),
            }

            with open(PAPER_STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"[PAPER] Failed to save state: {e}")

    def _load_state(self) -> None:
        """Load paper trading state from file."""
        try:
            if PAPER_STATE_FILE.exists():
                with open(PAPER_STATE_FILE, "r") as f:
                    state = json.load(f)

                self._balance = state.get("balance", self._initial_balance)
                self._margin_used = state.get("margin_used", 0.0)
                self._positions = state.get("positions", {})
                self._trade_history = state.get("trade_history", [])
                self._order_counter = state.get("order_counter", 0)

                logger.info(f"[PAPER] Loaded state. Balance: ${self._balance:,.2f}, Positions: {len(self._positions)}")
        except Exception as e:
            logger.warning(f"[PAPER] Could not load state: {e}")


def get_trading_client():
    """
    Factory function to get the appropriate trading client based on settings.

    Returns:
        PaperTradingClient if PAPER_TRADING is True, else HyperliquidClient
    """
    if settings.PAPER_TRADING:
        logger.info("Using PAPER TRADING mode")
        return PaperTradingClient()
    else:
        logger.info("Using LIVE TRADING mode")
        return HyperliquidClient()


# Global client instance - uses factory
paper_client = PaperTradingClient()
