"""
CCXT wrapper for Hyperliquid exchange integration.
"""
import time
from typing import Dict, List, Optional, Any
from decimal import Decimal

import ccxt

from config.settings import settings
from config.constants import (
    HYPERLIQUID_SYMBOLS, MAX_RETRIES, RETRY_DELAY_BASE,
    ORDERBOOK_DEPTH
)
from utils.logger import get_logger, log_error_with_context

logger = get_logger(__name__)


class HyperliquidClient:
    """Client for interacting with Hyperliquid exchange via CCXT."""

    def __init__(self):
        """Initialize the Hyperliquid client."""
        self.exchange = None
        self._connected = False

    def connect(self) -> bool:
        """
        Establish connection to Hyperliquid.

        Returns:
            True if connection successful
        """
        try:
            self.exchange = ccxt.hyperliquid({
                'apiKey': settings.HYPERLIQUID_API_KEY,
                'secret': settings.HYPERLIQUID_SECRET,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',  # Perpetual futures
                }
            })

            # Set testnet if configured
            if settings.HYPERLIQUID_TESTNET:
                self.exchange.set_sandbox_mode(True)
                logger.info("Connected to Hyperliquid TESTNET")
            else:
                logger.info("Connected to Hyperliquid MAINNET")

            # Load markets
            self.exchange.load_markets()
            self._connected = True
            return True

        except Exception as e:
            log_error_with_context(e, "HyperliquidClient.connect")
            return False

    def disconnect(self) -> None:
        """Close the exchange connection."""
        self._connected = False
        logger.info("Disconnected from Hyperliquid")

    def _get_symbol(self, symbol: str) -> str:
        """Convert short symbol to exchange format."""
        return HYPERLIQUID_SYMBOLS.get(symbol, f"{symbol}/USDC:USDC")

    def _retry_request(self, func, *args, **kwargs) -> Any:
        """Execute a request with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except ccxt.RateLimitExceeded:
                wait_time = RETRY_DELAY_BASE ** (attempt + 1)
                logger.warning(f"Rate limit exceeded, waiting {wait_time}s...")
                time.sleep(wait_time)
            except ccxt.NetworkError as e:
                wait_time = RETRY_DELAY_BASE ** (attempt + 1)
                logger.warning(f"Network error: {e}, retrying in {wait_time}s...")
                time.sleep(wait_time)
            except Exception as e:
                log_error_with_context(e, "HyperliquidClient._retry_request")
                raise
        raise Exception(f"Max retries ({MAX_RETRIES}) exceeded")

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current ticker data for a symbol.

        Args:
            symbol: Trading symbol (BTC, ETH, SOL)

        Returns:
            Ticker data with price, volume, changes
        """
        try:
            exchange_symbol = self._get_symbol(symbol)
            ticker = self._retry_request(self.exchange.fetch_ticker, exchange_symbol)

            return {
                "symbol": symbol,
                "price": ticker.get("last", 0),
                "bid": ticker.get("bid", 0),
                "ask": ticker.get("ask", 0),
                "volume_24h": ticker.get("quoteVolume", 0),
                "change_24h": ticker.get("percentage", 0),
                "high_24h": ticker.get("high", 0),
                "low_24h": ticker.get("low", 0),
                "timestamp": ticker.get("timestamp"),
            }

        except Exception as e:
            log_error_with_context(e, "fetch_ticker", {"symbol": symbol})
            return {
                "symbol": symbol,
                "price": 0,
                "bid": 0,
                "ask": 0,
                "volume_24h": 0,
                "change_24h": 0,
            }

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "15m",
        limit: int = 200
    ) -> List[List]:
        """
        Fetch OHLCV candlestick data.

        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch

        Returns:
            List of [timestamp, open, high, low, close, volume]
        """
        try:
            exchange_symbol = self._get_symbol(symbol)
            ohlcv = self._retry_request(
                self.exchange.fetch_ohlcv,
                exchange_symbol,
                timeframe,
                limit=limit
            )
            logger.debug(f"Fetched {len(ohlcv)} candles for {symbol}")
            return ohlcv

        except Exception as e:
            log_error_with_context(e, "fetch_ohlcv", {"symbol": symbol})
            return []

    def fetch_portfolio(self) -> Dict[str, Any]:
        """
        Fetch current portfolio information.

        Returns:
            Portfolio data with balance, margin, positions
        """
        try:
            balance = self._retry_request(self.exchange.fetch_balance)

            # Extract USDC balance
            usdc = balance.get("USDC", {})
            total_equity = float(usdc.get("total", 0))
            available = float(usdc.get("free", 0))
            margin_used = float(usdc.get("used", 0))

            # Fetch positions
            positions = self._fetch_positions_internal()

            # Calculate total exposure
            exposure = 0
            if total_equity > 0 and positions:
                for pos in positions:
                    position_value = abs(float(pos.get("notional", 0)))
                    exposure += position_value / total_equity

            return {
                "total_equity": total_equity,
                "available_balance": available,
                "margin_used": margin_used,
                "exposure_pct": exposure * 100,
                "positions": positions,
            }

        except Exception as e:
            log_error_with_context(e, "fetch_portfolio")
            return {
                "total_equity": 0,
                "available_balance": 0,
                "margin_used": 0,
                "exposure_pct": 0,
                "positions": [],
            }

    def _fetch_positions_internal(self) -> List[Dict[str, Any]]:
        """Fetch open positions from exchange."""
        try:
            positions = self._retry_request(self.exchange.fetch_positions)
            open_positions = []

            for pos in positions:
                contracts = float(pos.get("contracts", 0))
                if contracts != 0:
                    # Extract symbol from the position info
                    symbol_info = pos.get("symbol", "")
                    # Convert from exchange format to short format
                    short_symbol = symbol_info.split("/")[0] if "/" in symbol_info else symbol_info

                    open_positions.append({
                        "symbol": short_symbol,
                        "direction": "long" if pos.get("side") == "long" else "short",
                        "entry_price": float(pos.get("entryPrice", 0)),
                        "quantity": abs(contracts),
                        "notional": float(pos.get("notional", 0)),
                        "leverage": int(pos.get("leverage", 1)),
                        "unrealized_pnl": float(pos.get("unrealizedPnl", 0)),
                        "unrealized_pnl_pct": float(pos.get("percentage", 0)),
                        "liquidation_price": float(pos.get("liquidationPrice", 0) or 0),
                    })

            return open_positions

        except Exception as e:
            log_error_with_context(e, "_fetch_positions_internal")
            return []

    def fetch_order_book(
        self,
        symbol: str,
        limit: int = ORDERBOOK_DEPTH
    ) -> Dict[str, Any]:
        """
        Fetch order book data.

        Args:
            symbol: Trading symbol
            limit: Number of levels to fetch

        Returns:
            Order book with bids, asks, and analysis
        """
        try:
            exchange_symbol = self._get_symbol(symbol)
            orderbook = self._retry_request(
                self.exchange.fetch_order_book,
                exchange_symbol,
                limit
            )

            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            # Calculate total volumes
            bid_volume = sum(b[1] for b in bids[:limit])
            ask_volume = sum(a[1] for a in asks[:limit])

            # Calculate ratio
            ratio = bid_volume / ask_volume if ask_volume > 0 else 1.0

            # Interpret
            if ratio > 1.2:
                interpretation = "Forte pressione acquisto"
            elif ratio < 0.8:
                interpretation = "Forte pressione vendita"
            else:
                interpretation = "Neutro"

            return {
                "bids": bids,
                "asks": asks,
                "bid_volume": bid_volume,
                "ask_volume": ask_volume,
                "ratio": ratio,
                "interpretation": interpretation,
            }

        except Exception as e:
            log_error_with_context(e, "fetch_order_book", {"symbol": symbol})
            return {
                "bids": [],
                "asks": [],
                "bid_volume": 0,
                "ask_volume": 0,
                "ratio": 1.0,
                "interpretation": "Dati non disponibili",
            }

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for a symbol.

        Args:
            symbol: Trading symbol
            leverage: Leverage multiplier

        Returns:
            True if successful
        """
        try:
            exchange_symbol = self._get_symbol(symbol)
            self._retry_request(
                self.exchange.set_leverage,
                leverage,
                exchange_symbol
            )
            logger.info(f"Set leverage to {leverage}x for {symbol}")
            return True

        except Exception as e:
            log_error_with_context(e, "set_leverage", {"symbol": symbol, "leverage": leverage})
            return False

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
        Open a new position.

        Args:
            symbol: Trading symbol
            direction: "long" or "short"
            size_pct: Position size as percentage of available balance
            leverage: Leverage multiplier
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage

        Returns:
            Order execution details
        """
        try:
            exchange_symbol = self._get_symbol(symbol)

            # Set leverage first
            self.set_leverage(symbol, leverage)

            # Get current portfolio
            portfolio = self.fetch_portfolio()
            available = portfolio.get("available_balance", 0)

            # Get current price
            ticker = self.fetch_ticker(symbol)
            current_price = ticker.get("price", 0)

            if current_price <= 0:
                raise ValueError(f"Invalid price for {symbol}: {current_price}")

            # Calculate position size
            position_value = available * (size_pct / 100)
            quantity = position_value / current_price

            # Determine order side
            side = "buy" if direction == "long" else "sell"

            # Create market order
            order = self._retry_request(
                self.exchange.create_market_order,
                exchange_symbol,
                side,
                quantity
            )

            entry_price = float(order.get("average", current_price))
            order_id = order.get("id", "")

            logger.info(
                f"Opened {direction.upper()} position: {symbol} @ ${entry_price:.2f} "
                f"| Qty: {quantity:.6f} | Leverage: {leverage}x"
            )

            # Set stop loss and take profit if configured
            sl_price = None
            tp_price = None

            if stop_loss_pct and settings.ENABLE_STOP_LOSS:
                sl_price = self._calculate_sl_price(entry_price, direction, stop_loss_pct)
                self._set_stop_loss(symbol, direction, quantity, sl_price)

            if take_profit_pct and settings.ENABLE_TAKE_PROFIT:
                tp_price = self._calculate_tp_price(entry_price, direction, take_profit_pct)
                self._set_take_profit(symbol, direction, quantity, tp_price)

            return {
                "success": True,
                "order_id": order_id,
                "entry_price": entry_price,
                "quantity": quantity,
                "direction": direction,
                "leverage": leverage,
                "stop_loss_price": sl_price,
                "take_profit_price": tp_price,
            }

        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds to open position: {e}")
            return {"success": False, "error": "Insufficient funds"}

        except ccxt.InvalidOrder as e:
            logger.error(f"Invalid order: {e}")
            return {"success": False, "error": f"Invalid order: {e}"}

        except Exception as e:
            log_error_with_context(e, "open_position", {"symbol": symbol, "direction": direction})
            return {"success": False, "error": str(e)}

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Close an existing position.

        Args:
            symbol: Trading symbol

        Returns:
            Close execution details
        """
        try:
            exchange_symbol = self._get_symbol(symbol)

            # Get current position
            positions = self._fetch_positions_internal()
            position = next((p for p in positions if p["symbol"] == symbol), None)

            if not position:
                logger.warning(f"No open position found for {symbol}")
                return {"success": False, "error": "No position found"}

            # Determine closing side
            quantity = position["quantity"]
            direction = position["direction"]
            side = "sell" if direction == "long" else "buy"

            # Create closing market order
            order = self._retry_request(
                self.exchange.create_market_order,
                exchange_symbol,
                side,
                quantity,
                params={"reduceOnly": True}
            )

            exit_price = float(order.get("average", 0))
            entry_price = position["entry_price"]

            # Calculate P&L
            if direction == "long":
                pnl = (exit_price - entry_price) * quantity
                pnl_pct = ((exit_price / entry_price) - 1) * 100 * position["leverage"]
            else:
                pnl = (entry_price - exit_price) * quantity
                pnl_pct = ((entry_price / exit_price) - 1) * 100 * position["leverage"]

            # Cancel any pending SL/TP orders
            self._cancel_conditional_orders(symbol)

            logger.info(
                f"Closed {direction.upper()} position: {symbol} @ ${exit_price:.2f} "
                f"| PnL: ${pnl:.2f} ({pnl_pct:.2f}%)"
            )

            return {
                "success": True,
                "exit_price": exit_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
            }

        except Exception as e:
            log_error_with_context(e, "close_position", {"symbol": symbol})
            return {"success": False, "error": str(e)}

    def _calculate_sl_price(
        self,
        entry_price: float,
        direction: str,
        sl_pct: float
    ) -> float:
        """Calculate stop loss price."""
        if direction == "long":
            return entry_price * (1 - sl_pct / 100)
        else:
            return entry_price * (1 + sl_pct / 100)

    def _calculate_tp_price(
        self,
        entry_price: float,
        direction: str,
        tp_pct: float
    ) -> float:
        """Calculate take profit price."""
        if direction == "long":
            return entry_price * (1 + tp_pct / 100)
        else:
            return entry_price * (1 - tp_pct / 100)

    def _set_stop_loss(
        self,
        symbol: str,
        direction: str,
        quantity: float,
        price: float
    ) -> Optional[str]:
        """Set a stop loss order."""
        try:
            exchange_symbol = self._get_symbol(symbol)
            side = "sell" if direction == "long" else "buy"

            order = self._retry_request(
                self.exchange.create_order,
                exchange_symbol,
                "stop",
                side,
                quantity,
                price,
                params={"reduceOnly": True, "stopPrice": price}
            )
            logger.info(f"Set stop loss for {symbol} @ ${price:.2f}")
            return order.get("id")

        except Exception as e:
            log_error_with_context(e, "_set_stop_loss", {"symbol": symbol, "price": price})
            return None

    def _set_take_profit(
        self,
        symbol: str,
        direction: str,
        quantity: float,
        price: float
    ) -> Optional[str]:
        """Set a take profit order."""
        try:
            exchange_symbol = self._get_symbol(symbol)
            side = "sell" if direction == "long" else "buy"

            order = self._retry_request(
                self.exchange.create_order,
                exchange_symbol,
                "takeProfit",
                side,
                quantity,
                price,
                params={"reduceOnly": True, "takeProfitPrice": price}
            )
            logger.info(f"Set take profit for {symbol} @ ${price:.2f}")
            return order.get("id")

        except Exception as e:
            log_error_with_context(e, "_set_take_profit", {"symbol": symbol, "price": price})
            return None

    def _cancel_conditional_orders(self, symbol: str) -> None:
        """Cancel all conditional orders for a symbol."""
        try:
            exchange_symbol = self._get_symbol(symbol)
            open_orders = self._retry_request(
                self.exchange.fetch_open_orders,
                exchange_symbol
            )

            for order in open_orders:
                try:
                    self.exchange.cancel_order(order["id"], exchange_symbol)
                    logger.debug(f"Cancelled order {order['id']} for {symbol}")
                except Exception:
                    pass

        except Exception as e:
            log_error_with_context(e, "_cancel_conditional_orders", {"symbol": symbol})

    def get_total_exposure(self) -> float:
        """
        Get total exposure as percentage.

        Returns:
            Exposure percentage (0-100)
        """
        portfolio = self.fetch_portfolio()
        return portfolio.get("exposure_pct", 0)

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current position for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position data or None
        """
        positions = self._fetch_positions_internal()
        return next((p for p in positions if p["symbol"] == symbol), None)

    def has_open_position(self, symbol: str) -> bool:
        """Check if there's an open position for a symbol."""
        return self.get_position(symbol) is not None


# Global client instance
exchange_client = HyperliquidClient()
