"""
Main trading agent orchestration.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from config.settings import settings
from config.constants import ACTION_HOLD, EXECUTION_SKIPPED

from exchange.order_manager import order_manager
from exchange.portfolio import portfolio_manager

from indicators.technical import TechnicalIndicators, calculate_indicators
from indicators.pivot_points import calculate_pivot_points
from indicators.forecasting import get_price_forecast

from data.market_data import market_data_collector
from data.sentiment import get_market_sentiment
from data.news_feed import get_recent_news
from data.whale_alert import get_whale_alerts, analyze_whale_flow
from data.cache_manager import cache_manager

from core.llm_client import llm_client
from core.decision_validator import decision_validator
from core.risk_manager import risk_manager

from database.operations import db_ops

from utils.logger import get_logger, log_error_with_context

logger = get_logger(__name__)


class TradingAgent:
    """Main trading agent that orchestrates the trading cycle."""

    def __init__(self):
        """Initialize the trading agent."""
        self.symbols = settings.symbols_list
        self._initialized = False

    def initialize(self) -> bool:
        """
        Initialize all components.

        Returns:
            True if initialization successful
        """
        logger.info("=" * 50)
        logger.info("Initializing Trading Agent...")
        logger.info("=" * 50)

        try:
            # Database connection is handled automatically by Supabase client
            logger.info("Using Supabase database...")

            # Connect to exchange (uses appropriate client based on PAPER_TRADING setting)
            trading_mode = portfolio_manager.get_trading_mode()
            logger.info(f"Trading Mode: {trading_mode}")
            logger.info("Connecting to exchange...")
            if not portfolio_manager.client.connect():
                logger.error("Failed to connect to exchange")
                return False

            # Set initial equity for P&L tracking
            portfolio_manager.set_initial_equity()

            # Test LLM connection
            logger.info("Testing LLM connection...")
            if not llm_client.test_connection():
                logger.warning("LLM connection test failed, will retry during execution")

            self._initialized = True
            logger.info("Trading Agent initialized successfully")
            return True

        except Exception as e:
            log_error_with_context(e, "TradingAgent.initialize")
            return False

    def run_cycle(self) -> Dict[str, Any]:
        """
        Run a complete trading cycle for all symbols.

        Returns:
            Cycle results dictionary
        """
        if not self._initialized:
            if not self.initialize():
                return {"success": False, "error": "Initialization failed"}

        cycle_start = datetime.utcnow()
        logger.info("=" * 50)
        logger.info(f"Starting Trading Cycle at {cycle_start.isoformat()}")
        logger.info("=" * 50)

        results = {
            "success": True,
            "timestamp": cycle_start.isoformat(),
            "symbols": {},
            "errors": [],
        }

        # Check SL/TP in paper trading mode
        if portfolio_manager.is_paper_trading:
            closed_by_sltp = portfolio_manager.check_stop_loss_take_profit()
            if closed_by_sltp:
                for closed in closed_by_sltp:
                    logger.info(f"[PAPER] Position closed by {closed.get('close_reason', 'SL/TP')}")

        # Get portfolio state
        portfolio = portfolio_manager.get_portfolio_state()
        open_positions = portfolio.get("positions", [])
        current_exposure = portfolio.get("exposure_pct", 0)

        mode_label = "[PAPER] " if portfolio_manager.is_paper_trading else ""
        logger.info(f"{mode_label}Portfolio: ${portfolio.get('total_equity', 0):.2f} | "
                   f"Exposure: {current_exposure:.1f}%")

        # Get global sentiment, news, and whale alerts (shared across symbols)
        sentiment = self._get_sentiment_safe()
        news = self._get_news_safe()
        whale_alerts = self._get_whale_alerts_safe()
        whale_flow = self._analyze_whale_flow_safe()

        # Process each symbol
        for symbol in self.symbols:
            try:
                result = self._process_symbol(
                    symbol=symbol,
                    portfolio=portfolio,
                    open_positions=open_positions,
                    current_exposure=current_exposure,
                    sentiment=sentiment,
                    news=news,
                    whale_alerts=whale_alerts,
                    whale_flow=whale_flow
                )
                results["symbols"][symbol] = result

                # Update exposure after trade
                if result.get("executed"):
                    portfolio = portfolio_manager.get_portfolio_state()
                    current_exposure = portfolio.get("exposure_pct", 0)

            except Exception as e:
                log_error_with_context(e, f"process_symbol:{symbol}")
                results["symbols"][symbol] = {"success": False, "error": str(e)}
                results["errors"].append(f"{symbol}: {str(e)}")

        # Save portfolio snapshot
        try:
            portfolio_manager.save_snapshot()
        except Exception as e:
            logger.error(f"Failed to save portfolio snapshot: {e}")

        # Cleanup
        cache_manager.cleanup_expired()

        cycle_end = datetime.utcnow()
        duration = (cycle_end - cycle_start).total_seconds()

        logger.info("=" * 50)
        logger.info(f"Cycle completed in {duration:.2f}s")

        # Show paper trading summary
        if portfolio_manager.is_paper_trading:
            summary = portfolio_manager.get_paper_trading_summary()
            if summary:
                logger.info("-" * 30)
                logger.info("PAPER TRADING SUMMARY:")
                logger.info(f"  Initial: ${summary['initial_balance']:,.2f}")
                logger.info(f"  Current: ${summary['current_equity']:,.2f}")
                logger.info(f"  P&L: ${summary['total_pnl']:,.2f} ({summary['total_pnl_pct']:+.2f}%)")
                logger.info(f"  Trades: {summary['total_trades']} | Win Rate: {summary['win_rate']:.1f}%")
                logger.info(f"  Open Positions: {summary['open_positions']}")

        logger.info("=" * 50)

        results["duration_seconds"] = duration

        return results

    def _process_symbol(
        self,
        symbol: str,
        portfolio: Dict[str, Any],
        open_positions: List[Dict[str, Any]],
        current_exposure: float,
        sentiment: Dict[str, Any],
        news: List[Dict[str, Any]],
        whale_alerts: List[Dict[str, Any]],
        whale_flow: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a single symbol through the trading pipeline.

        Args:
            symbol: Trading symbol
            portfolio: Portfolio state
            open_positions: List of open positions
            current_exposure: Current exposure percentage
            sentiment: Market sentiment data
            news: Recent news
            whale_alerts: Recent whale transactions
            whale_flow: Whale capital flow analysis

        Returns:
            Processing result dictionary
        """
        logger.info(f"\n--- Analyzing {symbol} ---")

        # 1. Collect market data
        market_data = market_data_collector.get_complete_market_data(symbol)
        ohlcv = market_data.get("ohlcv", [])

        if not ohlcv:
            logger.warning(f"No OHLCV data for {symbol}, skipping")
            return {"success": False, "error": "No OHLCV data"}

        price = market_data.get("price", 0)

        # Safety check: refuse to trade with invalid market data
        if price <= 0:
            logger.error(f"Invalid price for {symbol}: ${price}. Refusing to trade.")
            return {"success": False, "error": "Invalid market data: price is 0"}

        logger.info(f"Price: ${price:.2f} | 24h: {market_data.get('change_24h', 0):.2f}%")

        # 2. Calculate indicators
        indicators = calculate_indicators(ohlcv)

        # Safety check: refuse to trade without valid indicators
        rsi = indicators.get('rsi')
        if rsi is None or not isinstance(rsi, (int, float)):
            logger.error(f"Invalid RSI for {symbol}: {rsi}. Refusing to trade.")
            return {"success": False, "error": "Invalid market data: RSI is N/A"}

        logger.info(f"RSI: {rsi:.1f} | "
                   f"MACD: {indicators.get('macd', 0):.4f}")

        # 3. Calculate pivot points
        pivot_points = calculate_pivot_points(ohlcv)

        # 4. Get forecast
        forecast = get_price_forecast(symbol, ohlcv)
        logger.info(f"Forecast: {forecast.get('trend', 'N/A')} | "
                   f"Target: ${forecast.get('target_price', 0):.2f}")

        # 5. Get order book
        orderbook = market_data.get("orderbook", {})

        # 6. Save market context to database
        context_id = db_ops.save_market_context(
            symbol=symbol,
            price=price,
            indicators=indicators,
            pivot_points=pivot_points,
            forecast=forecast,
            orderbook=orderbook,
            sentiment=sentiment,
            raw_data={
                "market_data": market_data,
                "news_count": len(news),
                "news": news[:5] if news else [],
                "whale_alerts_count": len(whale_alerts),
                "whale_flow": whale_flow
            }
        )

        # Log whale flow if significant
        if whale_flow.get("net_flow", 0) != 0:
            logger.info(f"Whale Flow: {whale_flow.get('interpretation', 'N/A')} | "
                       f"Net: ${whale_flow.get('net_flow', 0):,.0f}")

        # 7. Check if we have an existing position
        has_position = portfolio_manager.client.has_open_position(symbol)

        # 8. Get LLM decision
        logger.info("Requesting LLM decision...")
        decision = llm_client.get_trading_decision(
            symbol=symbol,
            portfolio=portfolio,
            market_data=market_data,
            indicators=indicators,
            pivot_points=pivot_points,
            forecast=forecast,
            orderbook=orderbook,
            sentiment=sentiment,
            news=news,
            open_positions=open_positions,
            whale_flow=whale_flow
        )

        action = decision.get("action", ACTION_HOLD)
        confidence = decision.get("confidence", 0)
        logger.info(f"LLM Decision: {action.upper()} | Confidence: {confidence:.2f}")

        # 9. Validate decision
        is_valid, sanitized_decision, reason = decision_validator.validate(
            decision=decision,
            current_exposure=current_exposure,
            has_position=has_position
        )

        if not is_valid:
            logger.warning(f"Decision validation failed: {reason}")
            # Save as skipped
            db_ops.save_trade_decision(
                context_id=context_id,
                symbol=symbol,
                decision=sanitized_decision,
                execution_status=EXECUTION_SKIPPED
            )
            return {
                "success": True,
                "action": "hold",
                "reason": reason,
                "executed": False
            }

        # 10. Adjust for exposure if needed
        sanitized_decision = decision_validator.adjust_for_high_exposure(
            sanitized_decision,
            current_exposure
        )

        # 11. Execute the decision
        execution_result = order_manager.execute_decision(
            decision=sanitized_decision,
            context_id=context_id
        )

        return {
            "success": execution_result.get("success", False),
            "action": sanitized_decision.get("action"),
            "direction": sanitized_decision.get("direction"),
            "confidence": sanitized_decision.get("confidence"),
            "executed": execution_result.get("success", False),
            "trade_id": execution_result.get("trade_id"),
            "result": execution_result.get("result"),
        }

    def _get_sentiment_safe(self) -> Dict[str, Any]:
        """Get sentiment with error handling."""
        try:
            return get_market_sentiment()
        except Exception as e:
            logger.warning(f"Failed to get sentiment: {e}")
            return {
                "score": 50,
                "label": "NEUTRAL",
                "interpretation": "Sentiment unavailable"
            }

    def _get_news_safe(self) -> List[Dict[str, Any]]:
        """Get news with error handling."""
        try:
            return get_recent_news(5)
        except Exception as e:
            logger.warning(f"Failed to get news: {e}")
            return []

    def _get_whale_alerts_safe(self) -> List[Dict[str, Any]]:
        """Get whale alerts with error handling."""
        try:
            alerts = get_whale_alerts(limit=10, min_value_usd=1_000_000)
            if alerts:
                logger.info(f"Found {len(alerts)} whale transactions (>$1M)")
            return alerts
        except Exception as e:
            logger.warning(f"Failed to get whale alerts: {e}")
            return []

    def _analyze_whale_flow_safe(self) -> Dict[str, Any]:
        """Analyze whale capital flow with error handling."""
        try:
            return analyze_whale_flow()
        except Exception as e:
            logger.warning(f"Failed to analyze whale flow: {e}")
            return {
                "inflow_exchange": 0,
                "outflow_exchange": 0,
                "net_flow": 0,
                "interpretation": "Whale data unavailable",
                "alert_count": 0
            }

    def shutdown(self) -> None:
        """Clean shutdown of all components."""
        logger.info("Shutting down Trading Agent...")

        try:
            portfolio_manager.client.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting exchange: {e}")

        try:
            llm_client.close()
        except Exception as e:
            logger.error(f"Error closing LLM client: {e}")

        # Supabase client doesn't need explicit disconnect

        logger.info("Trading Agent shutdown complete")


# Global agent instance
trading_agent = TradingAgent()


def run_trading_cycle() -> Dict[str, Any]:
    """Convenience function to run a trading cycle."""
    return trading_agent.run_cycle()
