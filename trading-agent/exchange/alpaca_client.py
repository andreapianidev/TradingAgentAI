"""
Alpaca Markets client for paper trading and live trading.
Supports both stocks and crypto with the same interface as HyperliquidClient.
"""
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pytz

from config.settings import settings
from config.constants import MAX_RETRIES, RETRY_DELAY_BASE, ORDERBOOK_DEPTH
from utils.logger import get_logger, log_error_with_context

logger = get_logger(__name__)

# Alpaca symbol mappings for crypto
ALPACA_CRYPTO_SYMBOLS = {
    "BTC": "BTC/USD",
    "ETH": "ETH/USD",
    "SOL": "SOL/USD",
    "DOGE": "DOGE/USD",
    "AVAX": "AVAX/USD",
    "LINK": "LINK/USD",
}

# Alpaca stock symbols (example)
ALPACA_STOCK_SYMBOLS = {
    "AAPL": "AAPL",
    "GOOGL": "GOOGL",
    "MSFT": "MSFT",
    "TSLA": "TSLA",
    "NVDA": "NVDA",
    "SPY": "SPY",
}


class AlpacaClient:
    """Client for interacting with Alpaca Markets API."""

    def __init__(self):
        """Initialize the Alpaca client."""
        self.trading_client = None
        self.data_client = None
        self.crypto_client = None
        self._connected = False
        self._is_crypto = True  # Default to crypto mode

    def connect(self) -> bool:
        """
        Establish connection to Alpaca.

        Returns:
            True if connection successful
        """
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient

            api_key = settings.ALPACA_API_KEY
            secret_key = settings.ALPACA_SECRET_KEY
            paper = settings.ALPACA_PAPER_TRADING

            if not api_key or not secret_key:
                logger.error("Alpaca API credentials not configured")
                return False

            # Initialize trading client
            self.trading_client = TradingClient(
                api_key=api_key,
                secret_key=secret_key,
                paper=paper
            )

            # Initialize data clients
            self.crypto_client = CryptoHistoricalDataClient(
                api_key=api_key,
                secret_key=secret_key
            )
            self.data_client = StockHistoricalDataClient(
                api_key=api_key,
                secret_key=secret_key
            )

            # Test connection by fetching account
            account = self.trading_client.get_account()

            mode = "PAPER" if paper else "LIVE"
            logger.info("=" * 60)
            logger.info(f"ALPACA CONNECTION SUCCESSFUL - {mode} TRADING")
            logger.info("=" * 60)
            logger.info(f"  Account Status: {account.status}")
            logger.info(f"  Account Equity: ${float(account.equity):,.2f}")
            logger.info(f"  Buying Power: ${float(account.buying_power):,.2f}")
            logger.info(f"  Cash: ${float(account.cash):,.2f}")
            logger.info(f"  API Endpoint: {settings.ALPACA_BASE_URL}")
            logger.info(f"  Crypto Trading: Enabled")
            logger.info("=" * 60)

            self._connected = True
            return True

        except ImportError as e:
            logger.error(f"Alpaca SDK not installed. Run: pip install alpaca-py")
            log_error_with_context(e, "AlpacaClient.connect")
            return False
        except Exception as e:
            log_error_with_context(e, "AlpacaClient.connect")
            return False

    def disconnect(self) -> None:
        """Close the connection."""
        self._connected = False
        logger.info("Disconnected from Alpaca")

    def _get_symbol(self, symbol: str) -> str:
        """Convert short symbol to Alpaca format."""
        # Check if it's a crypto symbol
        if symbol in ALPACA_CRYPTO_SYMBOLS:
            self._is_crypto = True
            return ALPACA_CRYPTO_SYMBOLS[symbol]
        # Check if it's a stock symbol
        elif symbol in ALPACA_STOCK_SYMBOLS:
            self._is_crypto = False
            return ALPACA_STOCK_SYMBOLS[symbol]
        # Default: assume crypto
        self._is_crypto = True
        return f"{symbol}/USD"

    def _retry_request(self, func, *args, **kwargs) -> Any:
        """Execute a request with retry logic."""
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")

                # Check for specific retryable errors
                is_rate_limit = "rate limit" in error_str or "too many requests" in error_str or "429" in error_str
                is_network_error = "network" in error_str or "connection" in error_str or "timeout" in error_str
                is_temporary = "temporarily" in error_str or "try again" in error_str or "service unavailable" in error_str

                if is_rate_limit:
                    wait_time = RETRY_DELAY_BASE ** (attempt + 1)
                    logger.warning(f"Rate limit hit, waiting {wait_time}s...")
                    time.sleep(wait_time)
                elif is_network_error or is_temporary:
                    wait_time = RETRY_DELAY_BASE ** (attempt + 1)
                    logger.warning(f"Temporary error, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # For other errors (insufficient funds, invalid order, etc.),
                    # log the full error and re-raise immediately (no retry)
                    logger.error(f"Non-retryable error: {e}")
                    log_error_with_context(e, "AlpacaClient._retry_request")
                    raise

        # If we get here, all retries failed - include the original error
        error_msg = f"Max retries ({MAX_RETRIES}) exceeded. Last error: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current ticker data for a symbol.

        Args:
            symbol: Trading symbol (BTC, ETH, AAPL, etc.)

        Returns:
            Ticker data with price, volume, changes
        """
        try:
            from alpaca.data.requests import CryptoLatestQuoteRequest, StockLatestQuoteRequest
            from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
            from alpaca.data.timeframe import TimeFrame

            alpaca_symbol = self._get_symbol(symbol)

            if self._is_crypto:
                # Get latest quote for crypto
                request = CryptoLatestQuoteRequest(symbol_or_symbols=alpaca_symbol)
                quote = self._retry_request(self.crypto_client.get_crypto_latest_quote, request)
                quote_data = quote.data.get(alpaca_symbol) if hasattr(quote, 'data') else quote.get(alpaca_symbol)

                # Get bars for 24h stats
                end = datetime.now(pytz.UTC)
                start = end - timedelta(days=1)
                bars_request = CryptoBarsRequest(
                    symbol_or_symbols=alpaca_symbol,
                    timeframe=TimeFrame.Hour,
                    start=start,
                    end=end
                )
                bars = self._retry_request(self.crypto_client.get_crypto_bars, bars_request)
                bars_data = bars.data.get(alpaca_symbol, []) if hasattr(bars, 'data') else []

            else:
                # Stock quote
                request = StockLatestQuoteRequest(symbol_or_symbols=alpaca_symbol)
                quote = self._retry_request(self.data_client.get_stock_latest_quote, request)
                quote_data = quote.data.get(alpaca_symbol) if hasattr(quote, 'data') else quote.get(alpaca_symbol)

                # Get bars for 24h stats
                end = datetime.now(pytz.UTC)
                start = end - timedelta(days=1)
                bars_request = StockBarsRequest(
                    symbol_or_symbols=alpaca_symbol,
                    timeframe=TimeFrame.Hour,
                    start=start,
                    end=end
                )
                bars = self._retry_request(self.data_client.get_stock_bars, bars_request)
                bars_data = bars.data.get(alpaca_symbol, []) if hasattr(bars, 'data') else []

            # Calculate stats from bars
            high_24h = max((b.high for b in bars_data), default=0) if bars_data else 0
            low_24h = min((b.low for b in bars_data), default=0) if bars_data else 0
            volume_24h = sum(b.volume for b in bars_data) if bars_data else 0

            # Get last close price from bars as fallback
            last_bar_close = float(bars_data[-1].close) if bars_data else 0

            # Current price (mid price from bid/ask)
            bid = float(quote_data.bid_price) if quote_data else 0
            ask = float(quote_data.ask_price) if quote_data else 0
            price = (bid + ask) / 2 if bid and ask else bid or ask

            # Fallback to last bar close if quote price is 0
            if price <= 0 and last_bar_close > 0:
                price = last_bar_close
                logger.warning(f"Quote price was 0 for {symbol}, using last bar close: ${last_bar_close:.2f}")

            # If still 0, retry once with fresh quote
            if price <= 0:
                logger.warning(f"Price still 0 for {symbol}, retrying quote...")
                time.sleep(1)
                if self._is_crypto:
                    request = CryptoLatestQuoteRequest(symbol_or_symbols=alpaca_symbol)
                    quote = self._retry_request(self.crypto_client.get_crypto_latest_quote, request)
                    quote_data = quote.data.get(alpaca_symbol) if hasattr(quote, 'data') else quote.get(alpaca_symbol)
                else:
                    request = StockLatestQuoteRequest(symbol_or_symbols=alpaca_symbol)
                    quote = self._retry_request(self.data_client.get_stock_latest_quote, request)
                    quote_data = quote.data.get(alpaca_symbol) if hasattr(quote, 'data') else quote.get(alpaca_symbol)

                bid = float(quote_data.bid_price) if quote_data else 0
                ask = float(quote_data.ask_price) if quote_data else 0
                price = (bid + ask) / 2 if bid and ask else bid or ask

                if price <= 0 and last_bar_close > 0:
                    price = last_bar_close

            # Calculate 24h change
            if bars_data and len(bars_data) > 0:
                open_price = bars_data[0].open
                change_24h = ((price - open_price) / open_price * 100) if open_price else 0
            else:
                change_24h = 0

            return {
                "symbol": symbol,
                "price": price,
                "bid": bid,
                "ask": ask,
                "volume_24h": volume_24h,
                "change_24h": change_24h,
                "high_24h": high_24h,
                "low_24h": low_24h,
                "timestamp": int(datetime.now().timestamp() * 1000),
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
            from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
            from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

            alpaca_symbol = self._get_symbol(symbol)

            # Convert timeframe string to Alpaca TimeFrame
            tf_map = {
                "1m": TimeFrame.Minute,
                "5m": TimeFrame(5, TimeFrameUnit.Minute),
                "15m": TimeFrame(15, TimeFrameUnit.Minute),
                "30m": TimeFrame(30, TimeFrameUnit.Minute),
                "1h": TimeFrame.Hour,
                "4h": TimeFrame(4, TimeFrameUnit.Hour),
                "1d": TimeFrame.Day,
            }
            alpaca_tf = tf_map.get(timeframe, TimeFrame(15, TimeFrameUnit.Minute))

            # Calculate start time based on limit and timeframe
            tf_minutes = {
                "1m": 1, "5m": 5, "15m": 15, "30m": 30,
                "1h": 60, "4h": 240, "1d": 1440
            }
            minutes = tf_minutes.get(timeframe, 15)
            end = datetime.now(pytz.UTC)
            start = end - timedelta(minutes=minutes * limit * 1.5)  # Extra buffer

            if self._is_crypto:
                request = CryptoBarsRequest(
                    symbol_or_symbols=alpaca_symbol,
                    timeframe=alpaca_tf,
                    start=start,
                    end=end,
                    limit=limit
                )
                bars = self._retry_request(self.crypto_client.get_crypto_bars, request)
            else:
                request = StockBarsRequest(
                    symbol_or_symbols=alpaca_symbol,
                    timeframe=alpaca_tf,
                    start=start,
                    end=end,
                    limit=limit
                )
                bars = self._retry_request(self.data_client.get_stock_bars, request)

            bars_data = bars.data.get(alpaca_symbol, []) if hasattr(bars, 'data') else []

            # Convert to CCXT format [timestamp, open, high, low, close, volume]
            ohlcv = []
            for bar in bars_data:
                ohlcv.append([
                    int(bar.timestamp.timestamp() * 1000),
                    float(bar.open),
                    float(bar.high),
                    float(bar.low),
                    float(bar.close),
                    float(bar.volume)
                ])

            logger.debug(f"Fetched {len(ohlcv)} candles for {symbol}")
            return ohlcv[-limit:]  # Return only requested limit

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
            account = self._retry_request(self.trading_client.get_account)

            total_equity = float(account.equity)
            cash = float(account.cash)
            # Calculate margin used (equity - cash = positions value)
            margin_used = total_equity - cash if cash < total_equity else 0

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
                "available_balance": cash,
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
        """Fetch open positions from Alpaca."""
        try:
            positions = self._retry_request(self.trading_client.get_all_positions)
            open_positions = []

            logger.debug(f"Fetching positions from Alpaca... Found {len(positions)} raw positions")

            for pos in positions:
                qty = float(pos.qty)
                if qty != 0:
                    # Extract base symbol
                    symbol = pos.symbol
                    if "/" in symbol:
                        symbol = symbol.split("/")[0]

                    # Determine direction
                    direction = "long" if qty > 0 else "short"

                    position_data = {
                        "symbol": symbol,
                        "direction": direction,
                        "entry_price": float(pos.avg_entry_price),
                        "quantity": abs(qty),
                        "notional": float(pos.market_value),
                        "leverage": 1,  # Alpaca doesn't have leverage for crypto
                        "unrealized_pnl": float(pos.unrealized_pl),
                        "unrealized_pnl_pct": float(pos.unrealized_plpc) * 100,
                        "liquidation_price": 0,  # N/A for Alpaca
                    }
                    open_positions.append(position_data)

                    logger.debug(f"  Position: {symbol} {direction} @ ${float(pos.avg_entry_price):.2f} "
                                f"qty={abs(qty):.6f} P&L=${float(pos.unrealized_pl):.2f}")

            logger.info(f"Alpaca positions loaded: {len(open_positions)} open positions")
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
        Note: Alpaca has limited order book access. Returns bid/ask spread.

        Args:
            symbol: Trading symbol
            limit: Number of levels (limited in Alpaca)

        Returns:
            Order book with bids, asks, and analysis
        """
        try:
            from alpaca.data.requests import CryptoLatestQuoteRequest, StockLatestQuoteRequest

            alpaca_symbol = self._get_symbol(symbol)

            if self._is_crypto:
                request = CryptoLatestQuoteRequest(symbol_or_symbols=alpaca_symbol)
                quote = self._retry_request(self.crypto_client.get_crypto_latest_quote, request)
            else:
                request = StockLatestQuoteRequest(symbol_or_symbols=alpaca_symbol)
                quote = self._retry_request(self.data_client.get_stock_latest_quote, request)

            quote_data = quote.data.get(alpaca_symbol) if hasattr(quote, 'data') else quote.get(alpaca_symbol)

            if quote_data:
                bid = float(quote_data.bid_price)
                ask = float(quote_data.ask_price)
                bid_size = float(quote_data.bid_size)
                ask_size = float(quote_data.ask_size)

                # Create pseudo order book from quote
                bids = [[bid, bid_size]]
                asks = [[ask, ask_size]]

                ratio = bid_size / ask_size if ask_size > 0 else 1.0

                if ratio > 1.2:
                    interpretation = "Forte pressione acquisto"
                elif ratio < 0.8:
                    interpretation = "Forte pressione vendita"
                else:
                    interpretation = "Neutro"

                return {
                    "bids": bids,
                    "asks": asks,
                    "bid_volume": bid_size,
                    "ask_volume": ask_size,
                    "ratio": ratio,
                    "interpretation": interpretation,
                }

            return {
                "bids": [],
                "asks": [],
                "bid_volume": 0,
                "ask_volume": 0,
                "ratio": 1.0,
                "interpretation": "Dati non disponibili",
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
        Note: Alpaca crypto doesn't support leverage. This is a no-op.

        Args:
            symbol: Trading symbol
            leverage: Leverage multiplier (ignored for Alpaca)

        Returns:
            True (always succeeds as no-op)
        """
        logger.debug(f"Alpaca does not support leverage. Ignoring leverage={leverage} for {symbol}")
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
        Open a new position.

        Args:
            symbol: Trading symbol
            direction: "long" or "short"
            size_pct: Position size as percentage of available balance
            leverage: Leverage multiplier (ignored for Alpaca crypto)
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage

        Returns:
            Order execution details
        """
        try:
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            alpaca_symbol = self._get_symbol(symbol)
            logger.info(f"Opening {direction} position for {symbol} (Alpaca: {alpaca_symbol})")

            # IMPORTANT: Cancel ALL pending orders FIRST to prevent "wash trade" errors
            # This ensures no opposite side orders exist that would block the new position
            logger.info(f"Cancelling all pending orders for {alpaca_symbol} before opening position...")
            cancellation_success = self._cancel_orders_for_symbol(alpaca_symbol)

            if not cancellation_success:
                logger.warning(f"Failed to cancel all orders for {alpaca_symbol}, proceeding anyway...")

            # Brief wait to ensure orders are fully cancelled
            time.sleep(1)

            # Get current portfolio
            portfolio = self.fetch_portfolio()
            available = portfolio.get("available_balance", 0)
            logger.info(f"Available balance: ${available:,.2f}")

            # Get current price
            ticker = self.fetch_ticker(symbol)
            current_price = ticker.get("price", 0)
            logger.info(f"Current price for {symbol}: ${current_price:,.2f}")

            if current_price <= 0:
                raise ValueError(f"Invalid price for {symbol}: {current_price}")

            # Calculate position size (notional value)
            # Use 99% of calculated value to avoid "insufficient balance" errors
            # due to price fluctuations between fetch and order execution
            position_value = available * (size_pct / 100) * 0.99
            quantity = position_value / current_price

            logger.info(f"Order details: size_pct={size_pct}%, position_value=${position_value:,.2f}, quantity={quantity:.6f}")

            # Determine order side
            side = OrderSide.BUY if direction == "long" else OrderSide.SELL

            # Create market order
            order_request = MarketOrderRequest(
                symbol=alpaca_symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.GTC
            )

            logger.info(f"Submitting order: {side} {quantity:.6f} {alpaca_symbol}")
            order = self._retry_request(self.trading_client.submit_order, order_request)

            # Wait for fill
            time.sleep(1)
            filled_order = self.trading_client.get_order_by_id(order.id)

            entry_price = float(filled_order.filled_avg_price) if filled_order.filled_avg_price else current_price

            logger.info(
                f"Opened {direction.upper()} position: {symbol} @ ${entry_price:.2f} "
                f"| Qty: {quantity:.6f}"
            )

            # Calculate SL/TP prices
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
                "order_id": str(order.id),
                "entry_price": entry_price,
                "quantity": quantity,
                "direction": direction,
                "leverage": 1,  # No leverage for Alpaca crypto
                "stop_loss_price": sl_price,
                "take_profit_price": tp_price,
            }

        except Exception as e:
            log_error_with_context(e, "open_position", {"symbol": symbol, "direction": direction})
            return {"success": False, "error": str(e)}

    def _get_actual_position_quantity(self, symbol: str, alpaca_symbol: str) -> tuple:
        """
        Get the actual available quantity for a position by checking both
        Alpaca's current position and comparing against what we expect.

        Returns:
            Tuple of (available_quantity, warning_message)
            - available_quantity: The quantity that can actually be closed (None if position not found)
            - warning_message: Description if quantity mismatch detected (None if all good)
        """
        try:
            # Get fresh position data from Alpaca
            alpaca_positions = self._retry_request(self.trading_client.get_all_positions)
            alpaca_position = None

            for pos in alpaca_positions:
                if pos.symbol == alpaca_symbol:
                    alpaca_position = pos
                    break

            if not alpaca_position:
                return None, f"Position {symbol} not found on Alpaca after order cancellation"

            # Use qty_available if present (amount not locked by orders), otherwise fallback to qty
            if hasattr(alpaca_position, 'qty_available') and alpaca_position.qty_available is not None:
                actual_qty = abs(float(alpaca_position.qty_available))
                logger.info(f"Using available quantity for {symbol}: {actual_qty:.8f} (total: {abs(float(alpaca_position.qty)):.8f})")
            else:
                actual_qty = abs(float(alpaca_position.qty))
                logger.warning(f"qty_available not available for {symbol}, using total quantity: {actual_qty:.8f}")

            # Get our internal tracking for comparison
            internal_positions = self._fetch_positions_internal()
            internal_position = next((p for p in internal_positions if p["symbol"] == symbol), None)

            if internal_position:
                expected_qty = float(internal_position["quantity"])
                qty_difference = abs(expected_qty - actual_qty)

                # If there's more than 1% difference, it's likely a partial fill
                if qty_difference > (expected_qty * 0.01):
                    warning = (
                        f"Quantity mismatch for {symbol}: "
                        f"Expected {expected_qty:.8f}, Alpaca shows {actual_qty:.8f}. "
                        f"Likely partial fill from SL/TP order (difference: {qty_difference:.8f})"
                    )
                    return actual_qty, warning

            return actual_qty, None

        except Exception as e:
            logger.error(f"Error verifying position quantity: {e}")
            return None, f"Failed to verify quantity: {str(e)}"

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Close an existing position with enhanced error handling and partial close fallback.

        Args:
            symbol: Trading symbol

        Returns:
            Close execution details with actual closed quantity
        """
        try:
            # Get current position from our internal tracking
            positions = self._fetch_positions_internal()
            position = next((p for p in positions if p["symbol"] == symbol), None)

            if not position:
                logger.warning(f"No open position found for {symbol}")
                return {"success": False, "error": "No position found"}

            entry_price = position["entry_price"]
            direction = position["direction"]
            expected_quantity = position["quantity"]

            # Get the actual Alpaca position to retrieve the exact symbol format
            alpaca_positions = self._retry_request(self.trading_client.get_all_positions)
            alpaca_position = None
            for pos in alpaca_positions:
                pos_symbol = pos.symbol
                # Check if this position matches (crypto uses "/" format)
                if "/" in pos_symbol:
                    base_symbol = pos_symbol.split("/")[0]
                    if base_symbol == symbol:
                        alpaca_position = pos
                        break
                elif pos_symbol == symbol:
                    alpaca_position = pos
                    break

            if not alpaca_position:
                logger.warning(f"Position {symbol} not found on Alpaca (sync issue)")
                return {"success": False, "error": "Position not found on exchange"}

            # Use the exact symbol format from Alpaca
            alpaca_symbol = alpaca_position.symbol

            # STEP 1: Cancel ALL pending orders FIRST
            logger.info(f"Cancelling all pending orders for {alpaca_symbol} before close...")
            cancellation_result = self._cancel_orders_for_symbol(alpaca_symbol)

            if not cancellation_result["success"]:
                logger.error(f"Failed to cancel all orders for {alpaca_symbol}, aborting close")
                return {"success": False, "error": "Failed to cancel pending orders"}

            # STEP 2: Adaptive wait based on what was cancelled
            # Increased base wait times to handle Alpaca's balance lock delays better
            base_wait = 10  # Increased from 5s
            if cancellation_result["had_sl_tp"]:
                # SL/TP orders need more time to release balance
                base_wait = 15  # Increased from 8s
                logger.info(f"SL/TP orders detected, using extended wait time ({base_wait}s)")

            logger.info(f"Waiting {base_wait}s for balance to unlock after order cancellation...")
            time.sleep(base_wait)

            # STEP 3: Verify actual available quantity
            actual_qty, qty_warning = self._get_actual_position_quantity(symbol, alpaca_symbol)

            if actual_qty is None:
                return {"success": False, "error": qty_warning or "Failed to verify position quantity"}

            if qty_warning:
                logger.warning(qty_warning)

            # Handle case where quantity is fully locked (qty_available = 0)
            if actual_qty == 0:
                # Position exists but qty_available is 0 - likely still locked despite cancellation
                total_qty = abs(float(alpaca_position.qty))
                logger.warning(
                    f"Position {symbol} has qty_available=0 but total qty={total_qty:.8f}. "
                    f"Position may still be locked. Waiting additional 5s and retrying..."
                )
                time.sleep(5)

                # Re-check quantity after additional wait
                actual_qty, qty_warning = self._get_actual_position_quantity(symbol, alpaca_symbol)

                if actual_qty == 0:
                    # Still locked - use total quantity as last resort
                    logger.error(
                        f"Position {symbol} still showing qty_available=0 after extended wait. "
                        f"Attempting to close using total quantity {total_qty:.8f}"
                    )
                    actual_qty = total_qty

                    if actual_qty == 0:
                        return {
                            "success": False,
                            "error": f"Position {symbol} has zero quantity on exchange"
                        }

            # STEP 4: Prepare market order to close
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            side = OrderSide.SELL if direction == "long" else OrderSide.BUY

            logger.info(
                f"Closing {direction} position: {side} {actual_qty:.8f} {alpaca_symbol} "
                f"(expected: {expected_quantity:.8f})"
            )

            # STEP 5: Submit close order with enhanced retry logic
            max_retries = 3
            order = None
            final_quantity = actual_qty

            for attempt in range(max_retries):
                try:
                    close_order = MarketOrderRequest(
                        symbol=alpaca_symbol,
                        qty=final_quantity,
                        side=side,
                        time_in_force=TimeInForce.GTC
                    )

                    order = self._retry_request(self.trading_client.submit_order, close_order)
                    logger.info(f"Close order submitted successfully for {final_quantity:.8f} {symbol}")
                    break  # Success - exit retry loop

                except Exception as e:
                    error_str = str(e).lower()
                    is_balance_error = "insufficient balance" in error_str or "balance" in error_str
                    is_qty_error = "qty must be" in error_str or "quantity" in error_str

                    # Handle zero quantity error specially
                    if is_qty_error and "must be" in error_str and attempt < max_retries - 1:
                        logger.warning(
                            f"Quantity validation error (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Position may still be locked, waiting 5s and re-verifying..."
                        )
                        time.sleep(5)

                        # Re-verify quantity
                        fresh_qty, _ = self._get_actual_position_quantity(symbol, alpaca_symbol)
                        if fresh_qty and fresh_qty > 0:
                            logger.info(f"Quantity now available: {fresh_qty:.8f}, retrying close...")
                            final_quantity = fresh_qty
                            continue
                        else:
                            logger.error(f"Position still has zero available quantity after wait")
                            raise

                    if is_balance_error and attempt < max_retries - 1:
                        # Balance still locked - wait longer and try again
                        wait_time = 4 * (attempt + 1)  # Progressive: 4s, 8s
                        logger.warning(
                            f"Balance still locked (attempt {attempt + 1}/{max_retries}), "
                            f"waiting {wait_time}s..."
                        )
                        time.sleep(wait_time)

                        # On final retry, try to get fresh quantity in case of partial fill
                        if attempt == max_retries - 2:
                            logger.info("Final retry - re-verifying available quantity...")
                            fresh_qty, fresh_warning = self._get_actual_position_quantity(symbol, alpaca_symbol)
                            if fresh_qty and fresh_qty < final_quantity:
                                logger.warning(
                                    f"Quantity decreased to {fresh_qty:.8f}, adjusting close order"
                                )
                                final_quantity = fresh_qty

                    elif is_balance_error:
                        # Max retries reached with balance error - try partial close
                        logger.error(
                            f"Still insufficient balance after {max_retries} attempts. "
                            f"Attempting graceful degradation..."
                        )

                        # Try closing 90% of what we think is available
                        fallback_qty = final_quantity * 0.9
                        logger.info(f"Attempting partial close of {fallback_qty:.8f} {symbol}")

                        try:
                            close_order = MarketOrderRequest(
                                symbol=alpaca_symbol,
                                qty=fallback_qty,
                                side=side,
                                time_in_force=TimeInForce.GTC
                            )
                            order = self._retry_request(self.trading_client.submit_order, close_order)
                            final_quantity = fallback_qty
                            logger.warning(
                                f"Partial close successful: {fallback_qty:.8f}/{actual_qty:.8f}"
                            )
                            break
                        except Exception as fallback_error:
                            logger.error(f"Partial close also failed: {fallback_error}")
                            raise e  # Raise original error
                    else:
                        # Not a balance error or other issue - raise immediately
                        raise

            if not order:
                raise Exception("Failed to close position after max retries and fallback")

            # STEP 6: Wait for fill and get execution details
            time.sleep(2)
            filled_order = self.trading_client.get_order_by_id(order.id)

            # Get exit price from filled order
            exit_price = float(filled_order.filled_avg_price) if filled_order.filled_avg_price else entry_price

            # Fallback to ticker if order price not available
            if exit_price == 0:
                ticker = self.fetch_ticker(symbol)
                exit_price = ticker.get("price", entry_price)

            # Get actual filled quantity (may differ from requested)
            filled_qty = float(filled_order.filled_qty) if filled_order.filled_qty else final_quantity

            # Calculate P&L based on actual filled quantity
            if direction == "long":
                pnl = (exit_price - entry_price) * filled_qty
                pnl_pct = ((exit_price / entry_price) - 1) * 100
            else:
                pnl = (entry_price - exit_price) * filled_qty
                pnl_pct = ((entry_price / exit_price) - 1) * 100

            # Check if partial close
            is_partial = abs(filled_qty - expected_quantity) > (expected_quantity * 0.01)

            logger.info(
                f"Closed {direction.upper()} position: {symbol} @ ${exit_price:.2f} "
                f"| Qty: {filled_qty:.8f} | PnL: ${pnl:.2f} ({pnl_pct:.2f}%)"
                f"{' [PARTIAL CLOSE]' if is_partial else ''}"
            )

            return {
                "success": True,
                "exit_price": exit_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "filled_quantity": filled_qty,
                "expected_quantity": expected_quantity,
                "is_partial_close": is_partial,
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
            from alpaca.trading.requests import StopLimitOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            alpaca_symbol = self._get_symbol(symbol)
            side = OrderSide.SELL if direction == "long" else OrderSide.BUY

            # For crypto, Alpaca requires stop_limit orders, not just stop orders
            # Set limit price slightly worse than stop price to ensure execution
            if direction == "long":
                limit_price = price * 0.995  # 0.5% below stop for sells
            else:
                limit_price = price * 1.005  # 0.5% above stop for buys

            order_request = StopLimitOrderRequest(
                symbol=alpaca_symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.GTC,
                stop_price=price,
                limit_price=limit_price
            )

            order = self._retry_request(self.trading_client.submit_order, order_request)
            logger.info(f"Set stop loss for {symbol} @ ${price:.2f}")
            return str(order.id)

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
            from alpaca.trading.requests import LimitOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            alpaca_symbol = self._get_symbol(symbol)
            side = OrderSide.SELL if direction == "long" else OrderSide.BUY

            order_request = LimitOrderRequest(
                symbol=alpaca_symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.GTC,
                limit_price=price
            )

            order = self._retry_request(self.trading_client.submit_order, order_request)
            logger.info(f"Set take profit for {symbol} @ ${price:.2f}")
            return str(order.id)

        except Exception as e:
            log_error_with_context(e, "_set_take_profit", {"symbol": symbol, "price": price})
            return None

    def _cancel_orders_for_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Cancel all open orders for a symbol and verify cancellation.

        Returns:
            Dict with:
            - success: bool
            - orders_cancelled: int (count of cancelled orders)
            - had_sl_tp: bool (whether SL/TP orders were among them)
        """
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus

            request = GetOrdersRequest(
                status=QueryOrderStatus.OPEN,
                symbols=[symbol]
            )

            open_orders = self._retry_request(self.trading_client.get_orders, request)

            if not open_orders:
                logger.debug(f"No open orders found for {symbol}")
                return {"success": True, "orders_cancelled": 0, "had_sl_tp": False}

            cancelled_count = 0
            had_sl_tp = False

            for order in open_orders:
                try:
                    self.trading_client.cancel_order_by_id(order.id)
                    logger.info(f"Cancelled order {order.id} for {symbol}")
                    cancelled_count += 1

                    # Check if this was a SL or TP order
                    if hasattr(order, 'order_class') and order.order_class and order.order_class in ['bracket', 'oco']:
                        had_sl_tp = True
                    # Also check order type for stop/limit orders
                    if hasattr(order, 'type') and order.type and order.type in ['stop', 'stop_limit', 'limit']:
                        had_sl_tp = True

                except Exception as e:
                    logger.warning(f"Failed to cancel order {order.id}: {e}")

            # Wait for cancellations to process
            time.sleep(2)

            # Verify all orders are cancelled
            verify_request = GetOrdersRequest(
                status=QueryOrderStatus.OPEN,
                symbols=[symbol]
            )
            remaining_orders = self._retry_request(self.trading_client.get_orders, verify_request)

            success = len(remaining_orders) == 0

            if remaining_orders:
                logger.warning(f"Still have {len(remaining_orders)} open orders for {symbol} after cancellation")

            logger.info(f"Cancelled {cancelled_count} orders for {symbol} (SL/TP: {had_sl_tp})")

            return {
                "success": success,
                "orders_cancelled": cancelled_count,
                "had_sl_tp": had_sl_tp
            }

        except Exception as e:
            log_error_with_context(e, "_cancel_orders_for_symbol", {"symbol": symbol})
            return {"success": False, "orders_cancelled": 0, "had_sl_tp": False}

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
alpaca_client = AlpacaClient()
