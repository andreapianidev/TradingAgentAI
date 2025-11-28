"""
Main trading agent orchestration.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date

from config.settings import settings
from config.supabase_settings import supabase_settings
from config.constants import ACTION_HOLD, EXECUTION_SKIPPED

from exchange.order_manager import order_manager
from exchange.portfolio import portfolio_manager

from indicators.technical import TechnicalIndicators, calculate_indicators
from indicators.pivot_points import calculate_pivot_points
from indicators.forecasting import get_price_forecast

from data.market_data import market_data_collector
from data.sentiment import get_market_sentiment
from data.news_feed import get_news_for_analysis
from data.news_analyzer import news_analyzer, analyze_news, get_news_for_llm
from data.whale_alert import get_whale_alerts, analyze_whale_flow
from data.coingecko import get_market_summary as get_coingecko_data
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

            # Sync positions from Alpaca to database
            logger.info("Syncing positions from Alpaca...")
            self._sync_alpaca_positions()

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

    def _check_auto_close_positions(self, open_positions: List[Dict[str, Any]]) -> List[str]:
        """
        Check if any positions should be auto-closed based on profit threshold.

        Args:
            open_positions: List of currently open positions

        Returns:
            List of symbols to auto-close
        """
        auto_close_pct = settings.AUTO_CLOSE_AT_PROFIT_PCT
        if not auto_close_pct:
            return []  # Auto-close disabled

        to_close = []
        for pos in open_positions:
            try:
                unrealized_pnl_pct = float(pos.get("unrealized_pnl_pct", 0))
                symbol = pos.get("symbol", "")

                if unrealized_pnl_pct >= auto_close_pct:
                    logger.info(f"🎯 AUTO-CLOSE triggered for {symbol}: "
                               f"profit {unrealized_pnl_pct:.2f}% >= {auto_close_pct}%")
                    to_close.append(symbol)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error checking auto-close for position: {e}")
                continue

        return to_close

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

        # Note: Stop loss/take profit are handled by Alpaca's native order system
        # No need to manually check here - Alpaca executes SL/TP orders automatically

        # Get portfolio state
        portfolio = portfolio_manager.get_portfolio_state()
        open_positions = portfolio.get("positions", [])
        current_exposure = portfolio.get("exposure_pct", 0)

        mode_label = "[PAPER] " if portfolio_manager.is_paper_trading else ""
        logger.info(f"{mode_label}Portfolio: ${portfolio.get('total_equity', 0):.2f} | "
                   f"Exposure: {current_exposure:.1f}%")

        # Check auto-close BEFORE processing symbols
        auto_close_symbols = self._check_auto_close_positions(open_positions)
        if auto_close_symbols:
            logger.info(f"🎯 Auto-closing {len(auto_close_symbols)} position(s) due to profit threshold")
            for symbol in auto_close_symbols:
                try:
                    logger.info(f"Executing auto-close for {symbol}")
                    close_decision = {
                        "action": "close",
                        "symbol": symbol,
                        "confidence": 1.0,
                        "reasoning": f"AUTO-CLOSE: Profit reached {settings.AUTO_CLOSE_AT_PROFIT_PCT}%"
                    }
                    # Execute the close order
                    execution_result = order_manager.execute_decision(
                        decision=close_decision,
                        context_id=None
                    )

                    if execution_result.get("success"):
                        logger.info(f"✓ Auto-closed {symbol} successfully")
                    else:
                        logger.warning(f"Failed to auto-close {symbol}: {execution_result.get('result')}")

                except Exception as e:
                    logger.error(f"Error auto-closing {symbol}: {e}")

            # Refresh portfolio state after auto-closes
            portfolio = portfolio_manager.get_portfolio_state()
            open_positions = portfolio.get("positions", [])
            current_exposure = portfolio.get("exposure_pct", 0)
            logger.info(f"Portfolio updated after auto-close: Exposure: {current_exposure:.1f}%")

        # Get global sentiment, news, whale alerts, and CoinGecko data (shared across symbols)
        sentiment = self._get_sentiment_safe()
        news_data = self._get_news_safe()  # Now returns Dict with analysis
        whale_alerts = self._get_whale_alerts_safe()
        whale_flow = self._analyze_whale_flow_safe()
        coingecko = self._get_coingecko_safe()

        # Log CoinGecko global market data
        logger.info("-" * 50)
        logger.info("COINGECKO MARKET DATA:")
        if coingecko.get("global"):
            global_data = coingecko["global"]
            logger.info(f"  BTC Dominance: {global_data.get('btc_dominance', 0):.1f}%")
            logger.info(f"  Total Market Cap: ${global_data.get('total_market_cap_usd', 0)/1e12:.2f}T")
            logger.info(f"  Market Cap Change 24h: {global_data.get('market_cap_change_24h_pct', 0):+.2f}%")
        if coingecko.get("trending"):
            trending_symbols = [t["symbol"] for t in coingecko["trending"][:5]]
            logger.info(f"  Trending: {', '.join(trending_symbols)}")
        if coingecko.get("tracked_trending"):
            logger.info(f"  Our coins trending: {', '.join(coingecko['tracked_trending'])}")

        # Log sentiment data
        logger.info("-" * 50)
        logger.info("MARKET SENTIMENT:")
        logger.info(f"  Fear & Greed Index: {sentiment.get('score', 'N/A')} ({sentiment.get('label', 'N/A')})")
        logger.info(f"  Interpretation: {sentiment.get('interpretation', 'N/A')}")

        # Log advanced news analysis results
        logger.info("-" * 50)
        news_analysis = news_data.get("analysis", {})
        analyzed_articles = news_analysis.get("analyzed_articles", [])
        aggregated_sentiment = news_data.get("aggregated_sentiment", {})

        logger.info(f"ADVANCED NEWS ANALYSIS ({news_analysis.get('total_analyzed', 0)} articles analyzed):")
        logger.info(f"  Fresh news: {news_analysis.get('fresh_count', 0)} | Stale filtered: {news_analysis.get('stale_filtered', 0)}")
        logger.info(f"  Analysis time: {news_analysis.get('analysis_time_seconds', 0):.1f}s")
        logger.info("")

        # Aggregated sentiment
        logger.info(f"  AGGREGATED SENTIMENT:")
        logger.info(f"    Score: {aggregated_sentiment.get('score', 0):.3f} | Label: {aggregated_sentiment.get('label', 'neutral').upper()}")
        logger.info(f"    Confidence: {aggregated_sentiment.get('confidence', 0):.0%}")
        logger.info(f"    Interpretation: {aggregated_sentiment.get('interpretation', 'N/A')}")

        # Breakdown
        breakdown = aggregated_sentiment.get("breakdown", {})
        if breakdown:
            logger.info(f"    Breakdown: {breakdown.get('very_bullish', 0)} very_bullish, {breakdown.get('bullish', 0)} bullish, "
                       f"{breakdown.get('neutral', 0)} neutral, {breakdown.get('bearish', 0)} bearish, {breakdown.get('very_bearish', 0)} very_bearish")

        # Per-symbol sentiment
        symbol_sentiments = news_data.get("symbol_sentiments", {})
        if symbol_sentiments:
            logger.info("")
            logger.info(f"  PER-SYMBOL SENTIMENT:")
            for sym, data in symbol_sentiments.items():
                logger.info(f"    {sym}: {data.get('label', 'neutral')} (score: {data.get('score', 0):.2f}, articles: {data.get('article_count', 0)})")

        # High impact news
        high_impact = news_data.get("high_impact_news", [])
        if high_impact:
            logger.info("")
            logger.info(f"  HIGH IMPACT NEWS ({len(high_impact)}):")
            for article in high_impact[:3]:
                sentiment_emoji = {"very_bullish": "[++]", "bullish": "[+]", "neutral": "[~]",
                                  "bearish": "[-]", "very_bearish": "[--]"}.get(article.get("sentiment", "neutral"), "[~]")
                logger.info(f"    {sentiment_emoji} {article.get('title', 'N/A')[:60]}")
                if article.get("summary"):
                    logger.info(f"       Summary: {article.get('summary', '')[:80]}...")

        # Top analyzed articles
        if analyzed_articles:
            logger.info("")
            logger.info(f"  TOP ANALYZED ARTICLES:")
            for i, article in enumerate(analyzed_articles[:5], 1):
                sentiment_emoji = {"very_bullish": "[++]", "bullish": "[+]", "neutral": "[~]",
                                  "bearish": "[-]", "very_bearish": "[--]"}.get(article.get("sentiment", "neutral"), "[~]")
                age = article.get("age_hours", 0)
                impact = article.get("impact_level", "low")
                source = article.get("source", "Unknown")
                logger.info(f"    {i}. {sentiment_emoji} [{impact.upper()}] {article.get('title', 'N/A')[:55]}")
                logger.info(f"       Source: {source} | Age: {age:.1f}h | Score: {article.get('sentiment_score', 0):.2f}")
                if article.get("key_points"):
                    logger.info(f"       Key: {article.get('key_points', [''])[0][:60]}")
        else:
            logger.info("  No news articles analyzed")

        # Log whale alerts
        logger.info("-" * 50)
        logger.info(f"WHALE ALERTS ({len(whale_alerts)} transactions >$1M):")
        if whale_alerts:
            for alert in whale_alerts[:5]:  # Show top 5
                logger.info(f"  {alert.get('symbol', 'CRYPTO')}: ${alert.get('amount_usd', 0):,.0f} | {alert.get('from_owner', 'unknown')} -> {alert.get('to_owner', 'unknown')}")
        if whale_flow.get("net_flow", 0) != 0:
            logger.info(f"  Net Flow: ${whale_flow.get('net_flow', 0):,.0f} ({whale_flow.get('interpretation', 'N/A')})")

        logger.info("-" * 50)

        # Process each symbol
        for symbol in self.symbols:
            try:
                result = self._process_symbol(
                    symbol=symbol,
                    portfolio=portfolio,
                    open_positions=open_positions,
                    current_exposure=current_exposure,
                    sentiment=sentiment,
                    news_data=news_data,
                    whale_alerts=whale_alerts,
                    whale_flow=whale_flow,
                    coingecko=coingecko
                )
                results["symbols"][symbol] = result

                # ALWAYS refresh portfolio state after processing each symbol
                # This prevents stale exposure data when processing multiple symbols
                # in fast-moving markets, reducing over-exposure risk
                portfolio = portfolio_manager.get_portfolio_state()
                open_positions = portfolio.get("positions", [])
                new_exposure = portfolio.get("exposure_pct", 0)

                if new_exposure != current_exposure:
                    logger.debug(f"Exposure updated after {symbol}: {current_exposure:.1f}% -> {new_exposure:.1f}%")
                    current_exposure = new_exposure

            except Exception as e:
                log_error_with_context(e, f"process_symbol:{symbol}")
                results["symbols"][symbol] = {"success": False, "error": str(e)}
                results["errors"].append(f"{symbol}: {str(e)}")

        # Save portfolio snapshot
        try:
            portfolio_manager.save_snapshot()
        except Exception as e:
            logger.error(f"Failed to save portfolio snapshot: {e}")

        # Generate daily AI analysis (once per day per symbol)
        self._generate_daily_analysis(sentiment, news_data, whale_flow)

        # Check cost alerts
        self._check_cost_alerts()

        # Cleanup
        cache_manager.cleanup_expired()

        cycle_end = datetime.utcnow()
        duration = (cycle_end - cycle_start).total_seconds()

        logger.info("=" * 50)
        logger.info(f"Cycle completed in {duration:.2f}s")

        # Show portfolio summary
        portfolio_final = portfolio_manager.get_portfolio_state()
        mode_label = "PAPER" if portfolio_manager.is_paper_trading else "LIVE"
        logger.info("-" * 30)
        logger.info(f"PORTFOLIO SUMMARY ({mode_label} - Alpaca):")
        logger.info(f"  Equity: ${portfolio_final.get('total_equity', 0):,.2f}")
        logger.info(f"  Available: ${portfolio_final.get('available_balance', 0):,.2f}")
        logger.info(f"  Exposure: {portfolio_final.get('exposure_pct', 0):.1f}%")
        logger.info(f"  Open Positions: {len(portfolio_final.get('positions', []))}")

        # Log individual positions
        for pos in portfolio_final.get("positions", []):
            pnl = pos.get("unrealized_pnl", 0)
            pnl_pct = pos.get("unrealized_pnl_pct", 0)
            logger.info(f"    {pos.get('symbol')}: {pos.get('direction')} @ ${pos.get('entry_price', 0):.2f} | "
                       f"P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")

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
        news_data: Dict[str, Any],
        whale_alerts: List[Dict[str, Any]],
        whale_flow: Dict[str, Any],
        coingecko: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a single symbol through the trading pipeline.

        Args:
            symbol: Trading symbol
            portfolio: Portfolio state
            open_positions: List of open positions
            current_exposure: Current exposure percentage
            sentiment: Market sentiment data
            news_data: Advanced news analysis data (Dict with analysis, articles, sentiments)
            whale_alerts: Recent whale transactions
            whale_flow: Whale capital flow analysis
            coingecko: CoinGecko market data (global, trending, coins)

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

        # Log all technical indicators
        logger.info("-" * 40)
        logger.info("TECHNICAL INDICATORS:")
        logger.info(f"  RSI: {rsi:.1f} {'(OVERBOUGHT)' if indicators.get('rsi_overbought') else '(OVERSOLD)' if indicators.get('rsi_oversold') else ''}")
        logger.info(f"  MACD: {indicators.get('macd', 0):.4f} | Signal: {indicators.get('macd_signal', 0):.4f} | Histogram: {indicators.get('macd_histogram', 0):.4f}")
        logger.info(f"  MACD Trend: {'BULLISH' if indicators.get('macd_bullish') else 'BEARISH'} | Histogram Rising: {indicators.get('macd_histogram_rising', False)}")
        logger.info(f"  EMA2: ${indicators.get('ema2', 0):.2f} | EMA20: ${indicators.get('ema20', 0):.2f}")
        logger.info(f"  Price vs EMA20: {'ABOVE' if indicators.get('price_above_ema20') else 'BELOW'}")
        logger.info(f"  Volume SMA: {indicators.get('volume_sma', 0):,.0f}")

        # 3. Calculate pivot points
        pivot_points = calculate_pivot_points(ohlcv)
        logger.info("-" * 40)
        logger.info("PIVOT POINTS:")
        logger.info(f"  PP (Pivot): ${pivot_points.get('pp', 0):.2f}")
        logger.info(f"  R1: ${pivot_points.get('r1', 0):.2f} | R2: ${pivot_points.get('r2', 0):.2f}")
        logger.info(f"  S1: ${pivot_points.get('s1', 0):.2f} | S2: ${pivot_points.get('s2', 0):.2f}")
        logger.info(f"  Distance from PP: {pivot_points.get('distance_pct', 0):.2f}%")

        # 4. Get forecast
        forecast = get_price_forecast(symbol, ohlcv)
        logger.info("-" * 40)
        logger.info("PROPHET FORECAST:")
        logger.info(f"  Trend: {forecast.get('trend', 'N/A').upper()}")
        logger.info(f"  Target Price: ${forecast.get('target_price', 0):.2f}")
        logger.info(f"  Expected Change: {forecast.get('change_pct', 0):+.2f}%")
        logger.info(f"  Forecast Confidence: {forecast.get('confidence', 0):.1%}")

        # 5. Get order book
        orderbook = market_data.get("orderbook", {})
        logger.info("-" * 40)
        logger.info("ORDER BOOK:")
        logger.info(f"  Bid Volume: {orderbook.get('bid_volume', 0):,.2f}")
        logger.info(f"  Ask Volume: {orderbook.get('ask_volume', 0):,.2f}")
        logger.info(f"  Bid/Ask Ratio: {orderbook.get('ratio', 0):.2f}")
        logger.info(f"  Interpretation: {orderbook.get('interpretation', 'N/A')}")
        logger.info("-" * 40)

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
                "news_analysis": news_data.get("analysis", {}),
                "news_aggregated_sentiment": news_data.get("aggregated_sentiment", {}),
                "news_symbol_sentiment": news_data.get("symbol_sentiments", {}).get(symbol, {}),
                "whale_alerts_count": len(whale_alerts),
                "whale_flow": whale_flow
            }
        )

        # 7. Check if we have an existing position
        has_position = portfolio_manager.client.has_open_position(symbol)

        # 8. Get LLM decision with advanced news data
        logger.info("Requesting LLM decision...")

        # Get symbol-specific news summary for LLM
        news_for_llm = get_news_for_llm(news_data.get("analysis", {}), symbol=symbol)

        decision, usage_metadata = llm_client.get_trading_decision(
            symbol=symbol,
            portfolio=portfolio,
            market_data=market_data,
            indicators=indicators,
            pivot_points=pivot_points,
            forecast=forecast,
            orderbook=orderbook,
            sentiment=sentiment,
            news_data=news_for_llm,  # Pass enriched news data
            open_positions=open_positions,
            whale_flow=whale_flow,
            coingecko=coingecko
        )

        # Save LLM cost to database
        if usage_metadata and usage_metadata.get("cost_usd", 0) > 0:
            try:
                db_ops.save_llm_cost(
                    symbol=symbol,
                    input_tokens=usage_metadata.get("input_tokens", 0),
                    output_tokens=usage_metadata.get("output_tokens", 0),
                    cost_usd=usage_metadata.get("cost_usd", 0),
                    cached_tokens=usage_metadata.get("cached_tokens", 0),
                    model=usage_metadata.get("model"),
                    details={"provider": usage_metadata.get("provider", "deepseek"), "type": "trading_decision"}
                )
                logger.debug(f"Saved LLM cost: ${usage_metadata.get('cost_usd', 0):.6f}")
            except Exception as e:
                logger.warning(f"Failed to save LLM cost: {e}")

        action = decision.get("action", ACTION_HOLD)
        confidence = decision.get("confidence", 0)

        # Log detailed LLM decision with safe value handling
        logger.info("=" * 50)
        logger.info("LLM DECISION:")
        logger.info(f"  Action: {action.upper() if action else 'N/A'}")
        if action and action != ACTION_HOLD:
            direction = decision.get('direction')
            logger.info(f"  Direction: {direction.upper() if direction else 'N/A'}")
            logger.info(f"  Position Size: {decision.get('position_size_pct', 0) or 0}%")
            logger.info(f"  Leverage: {decision.get('leverage', 1) or 1}x")

            # Safe numeric handling for TP/SL
            sl_pct = decision.get('stop_loss_pct') or 0
            tp_pct = decision.get('take_profit_pct') or 0
            try:
                sl_pct = float(sl_pct)
                tp_pct = float(tp_pct)
                rr_ratio = tp_pct / sl_pct if sl_pct > 0 else 0
            except (TypeError, ValueError):
                sl_pct, tp_pct, rr_ratio = 0, 0, 0

            logger.info(f"  Stop Loss: {sl_pct}% (DYNAMIC)")
            logger.info(f"  Take Profit: {tp_pct}% (DYNAMIC)")
            logger.info(f"  Risk/Reward: {rr_ratio:.2f}:1")

            tp_sl_reasoning = decision.get('tp_sl_reasoning')
            if tp_sl_reasoning:
                logger.info(f"  TP/SL Reasoning: {tp_sl_reasoning}")

        logger.info(f"  Confidence: {confidence:.2%}")
        reasoning = decision.get('reasoning', 'N/A')
        # Truncate very long reasoning for log readability
        if reasoning and len(str(reasoning)) > 500:
            reasoning = str(reasoning)[:500] + "..."
        logger.info(f"  Reasoning: {reasoning}")
        logger.info("=" * 50)

        # 9. Validate decision
        is_valid, sanitized_decision, reason = decision_validator.validate(
            decision=decision,
            current_exposure=current_exposure,
            has_position=has_position
        )

        if not is_valid:
            logger.warning(f"Decision validation failed: {reason}")
            # Save as skipped - pass raw LLM decision for analysis
            db_ops.save_trade_decision(
                context_id=context_id,
                symbol=symbol,
                decision=sanitized_decision,
                execution_status=EXECUTION_SKIPPED,
                raw_llm_decision=decision  # Store original LLM values
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

    def _sync_alpaca_positions(self) -> None:
        """
        Sync positions from Alpaca to database at startup.
        This ensures the database reflects the actual positions on Alpaca.
        """
        try:
            # Get positions from Alpaca
            portfolio = portfolio_manager.get_portfolio_state()
            alpaca_positions = portfolio.get("positions", [])

            logger.info("-" * 50)
            logger.info("SYNCING POSITIONS FROM ALPACA TO DATABASE")
            logger.info(f"Alpaca has {len(alpaca_positions)} open positions:")

            for pos in alpaca_positions:
                logger.info(f"  → {pos.get('symbol')}: {pos.get('direction')} @ ${pos.get('entry_price', 0):.2f} "
                           f"qty={pos.get('quantity', 0):.6f} P&L=${pos.get('unrealized_pnl', 0):.2f}")

            # Sync to database
            sync_result = db_ops.sync_positions_from_alpaca(alpaca_positions)

            if sync_result["created"]:
                logger.info(f"✓ Created new positions in DB: {sync_result['created']}")
            if sync_result["updated"]:
                logger.info(f"✓ Updated existing positions: {sync_result['updated']}")
            if sync_result["closed"]:
                logger.info(f"✓ Closed positions not on Alpaca: {sync_result['closed']}")
            if sync_result["duplicates_cleaned"]:
                logger.info(f"✓ Cleaned up {sync_result['duplicates_cleaned']} duplicate positions")

            if not any([sync_result["created"], sync_result["updated"], sync_result["closed"], sync_result["duplicates_cleaned"]]):
                logger.info("✓ Database already in sync with Alpaca")

            logger.info("-" * 50)

        except Exception as e:
            logger.warning(f"Failed to sync positions from Alpaca: {e}")
            # Don't fail initialization if sync fails

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

    def _get_news_safe(self) -> Dict[str, Any]:
        """
        Get news with advanced AI analysis.

        Returns:
            Dictionary containing:
            - raw_news: Original RSS news items
            - analysis: Full analysis result from news_analyzer
            - for_llm: Formatted data for LLM consumption
        """
        try:
            # Step 1: Get raw news from RSS feeds (more items for analysis)
            raw_news = get_news_for_analysis(30)
            logger.info(f"Fetched {len(raw_news)} raw news items from RSS feeds")

            if not raw_news:
                return self._empty_news_result()

            # Save raw news to database (deduplicates automatically)
            try:
                saved_count = db_ops.save_news_batch(raw_news)
                if saved_count > 0:
                    logger.debug(f"Saved {saved_count} new news items to database")
            except Exception as e:
                logger.debug(f"Error saving news to database: {e}")

            # Step 2: Run advanced analysis (scraping + DeepSeek)
            # Always run news analysis for now (scheduling can be added later if needed)
            # TODO: Add scheduling via settings table if API cost optimization is needed

            analysis = analyze_news(raw_news)

            # Step 3: Save analyzed news to database
            try:
                analyzed_articles = analysis.get("analyzed_articles", [])
                if analyzed_articles:
                    saved = db_ops.save_analyzed_news_batch(analyzed_articles)
                    if saved > 0:
                        logger.debug(f"Saved {saved} analyzed news items to database")
            except Exception as e:
                logger.debug(f"Error saving analyzed news: {e}")

            return {
                "raw_news": raw_news,
                "analysis": analysis,
                "aggregated_sentiment": analysis.get("aggregated_sentiment", {}),
                "symbol_sentiments": analysis.get("symbol_sentiments", {}),
                "high_impact_news": analysis.get("high_impact_news", []),
            }

        except Exception as e:
            logger.warning(f"Failed to get/analyze news: {e}")
            return self._empty_news_result()

    def _empty_news_result(self) -> Dict[str, Any]:
        """Return empty news result structure."""
        return {
            "raw_news": [],
            "analysis": {
                "analyzed_articles": [],
                "aggregated_sentiment": {
                    "score": 0.0,
                    "label": "neutral",
                    "interpretation": "Nessuna news disponibile",
                    "confidence": 0.0,
                },
                "symbol_sentiments": {},
                "high_impact_news": [],
                "total_analyzed": 0,
            },
            "aggregated_sentiment": {
                "score": 0.0,
                "label": "neutral",
                "interpretation": "Nessuna news disponibile",
                "confidence": 0.0,
            },
            "symbol_sentiments": {},
            "high_impact_news": [],
        }

    def _get_whale_alerts_safe(self) -> List[Dict[str, Any]]:
        """Get whale alerts with error handling and save to database."""
        try:
            alerts = get_whale_alerts(limit=20, min_value_usd=1_000_000)

            # Save whale alerts to database (deduplicates automatically)
            if alerts:
                logger.info(f"Found {len(alerts)} whale transactions (>$1M)")
                try:
                    saved_count = db_ops.save_whale_alerts_batch(alerts)
                    if saved_count > 0:
                        logger.debug(f"Saved {saved_count} new whale alerts to database")
                except Exception as e:
                    logger.debug(f"Error saving whale alerts to database: {e}")

            return alerts[:10]  # Return top 10 for analysis
        except Exception as e:
            logger.warning(f"Failed to get whale alerts: {e}")
            return []

    def _analyze_whale_flow_safe(self) -> Dict[str, Any]:
        """Analyze whale capital flow with error handling and save summary."""
        try:
            flow = analyze_whale_flow()

            # Save whale flow summary to database if significant
            if flow.get("alert_count", 0) > 0:
                try:
                    db_ops.save_whale_flow_summary(
                        symbol="ALL",  # Aggregated across all symbols
                        inflow_exchange=flow.get("inflow_exchange", 0),
                        outflow_exchange=flow.get("outflow_exchange", 0),
                        net_flow=flow.get("net_flow", 0),
                        alert_count=flow.get("alert_count", 0),
                        interpretation=flow.get("interpretation")
                    )
                except Exception as e:
                    logger.debug(f"Error saving whale flow summary: {e}")

            return flow
        except Exception as e:
            logger.warning(f"Failed to analyze whale flow: {e}")
            return {
                "inflow_exchange": 0,
                "outflow_exchange": 0,
                "net_flow": 0,
                "interpretation": "Whale data unavailable",
                "alert_count": 0
            }

    def _get_coingecko_safe(self) -> Dict[str, Any]:
        """Get CoinGecko market data with error handling and save to database."""
        try:
            data = get_coingecko_data(self.symbols)

            # Save to database for dashboard display
            if data.get("global"):
                try:
                    db_ops.save_market_global(data)
                except Exception as e:
                    logger.debug(f"Error saving CoinGecko data to database: {e}")

            return data
        except Exception as e:
            logger.warning(f"Failed to get CoinGecko data: {e}")
            return {
                "global": {},
                "trending": [],
                "trending_symbols": [],
                "tracked_trending": [],
                "coins": {},
                "error": str(e)
            }

    def _generate_daily_analysis(
        self,
        sentiment: Dict[str, Any],
        news_data: Dict[str, Any],
        whale_flow: Dict[str, Any]
    ) -> None:
        """
        Generate daily AI market analysis for each symbol.
        Only generates once per day per symbol.
        """
        for symbol in self.symbols:
            try:
                # Check if we need to generate analysis today
                if not db_ops.should_generate_analysis(symbol):
                    logger.debug(f"AI analysis for {symbol} already exists for today, skipping")
                    continue

                logger.info(f"Generating daily AI analysis for {symbol}...")

                # Get latest market context
                context = db_ops.get_latest_market_context(symbol)
                if not context:
                    logger.warning(f"No market context for {symbol}, skipping AI analysis")
                    continue

                # Extract data from context
                price = float(context.get("price", 0))
                indicators = {
                    "rsi": context.get("rsi"),
                    "macd": context.get("macd"),
                    "macd_signal": context.get("macd_signal"),
                    "macd_histogram": context.get("macd_histogram"),
                    "ema2": context.get("ema2"),
                    "ema20": context.get("ema20"),
                    "macd_bullish": (context.get("macd") or 0) > (context.get("macd_signal") or 0),
                    "price_above_ema20": price > float(context.get("ema20") or 0)
                }
                pivot_points = {
                    "pp": context.get("pivot_pp"),
                    "r1": context.get("pivot_r1"),
                    "r2": context.get("pivot_r2"),
                    "s1": context.get("pivot_s1"),
                    "s2": context.get("pivot_s2")
                }
                forecast = {
                    "trend": context.get("forecast_trend"),
                    "target_price": context.get("forecast_target_price"),
                    "change_pct": context.get("forecast_change_pct")
                }

                # Get symbol-specific news for analysis
                news_for_llm = get_news_for_llm(news_data.get("analysis", {}), symbol=symbol)

                # Generate analysis using LLM
                analysis, usage_metadata = llm_client.generate_market_analysis(
                    symbol=symbol,
                    price=price,
                    indicators=indicators,
                    pivot_points=pivot_points,
                    forecast=forecast,
                    sentiment=sentiment,
                    news_data=news_for_llm,
                    whale_flow=whale_flow
                )

                # Save LLM cost for daily analysis
                if usage_metadata and usage_metadata.get("cost_usd", 0) > 0:
                    try:
                        db_ops.save_llm_cost(
                            symbol=symbol,
                            input_tokens=usage_metadata.get("input_tokens", 0),
                            output_tokens=usage_metadata.get("output_tokens", 0),
                            cost_usd=usage_metadata.get("cost_usd", 0),
                            cached_tokens=usage_metadata.get("cached_tokens", 0),
                            model=usage_metadata.get("model"),
                            details={"provider": usage_metadata.get("provider", "deepseek"), "type": "daily_analysis"}
                        )
                        logger.debug(f"Saved daily analysis LLM cost: ${usage_metadata.get('cost_usd', 0):.6f}")
                    except Exception as e:
                        logger.warning(f"Failed to save daily analysis LLM cost: {e}")

                # Extract news sentiment summary from analysis
                news_aggregated = news_data.get("aggregated_sentiment", {})
                symbol_sentiment = news_data.get("symbol_sentiments", {}).get(symbol, {})
                analyzed_count = news_data.get("analysis", {}).get("total_analyzed", 0)

                # Save to database
                db_ops.save_ai_analysis(
                    symbol=symbol,
                    summary_text=analysis.get("summary_text", ""),
                    market_outlook=analysis.get("market_outlook", "neutral"),
                    confidence_score=analysis.get("confidence_score", 0.5),
                    key_levels=analysis.get("key_levels"),
                    risk_factors=analysis.get("risk_factors"),
                    opportunities=analysis.get("opportunities"),
                    trend_strength=analysis.get("trend_strength"),
                    momentum=analysis.get("momentum"),
                    volatility_level=analysis.get("volatility_level"),
                    indicators_snapshot=indicators,
                    news_sentiment_summary={
                        "total_analyzed": analyzed_count,
                        "aggregated_score": news_aggregated.get("score", 0),
                        "aggregated_label": news_aggregated.get("label", "neutral"),
                        "symbol_score": symbol_sentiment.get("score", 0),
                        "symbol_label": symbol_sentiment.get("label", "neutral"),
                        "symbol_article_count": symbol_sentiment.get("article_count", 0),
                        "fear_greed_score": sentiment.get("score"),
                        "fear_greed_label": sentiment.get("label")
                    }
                )

                logger.info(f"AI analysis for {symbol} saved: {analysis.get('market_outlook', 'N/A')}")

            except Exception as e:
                logger.warning(f"Failed to generate AI analysis for {symbol}: {e}")

    def _check_cost_alerts(self) -> None:
        """Check if daily costs exceed configured threshold and create alert."""
        try:
            # Get cost alert setting
            threshold_setting = supabase_settings.get_setting('cost_alert_daily_threshold_usd')

            if not threshold_setting:
                logger.debug("Cost alert setting not configured, skipping check")
                return

            if not threshold_setting.get('enabled', False):
                logger.debug("Cost alerts disabled, skipping check")
                return

            threshold = float(threshold_setting.get('threshold', 1.0))

            # Get today's costs
            today = date.today().isoformat()
            totals = db_ops.get_cost_totals(start_date=today)
            daily_cost = totals.get('total_cost_usd', 0)

            if daily_cost > threshold:
                # Create alert
                db_ops.save_alert(
                    alert_type='high_cost',
                    title='Daily Cost Threshold Exceeded',
                    message=f'Operating costs today: ${daily_cost:.4f} (threshold: ${threshold:.2f})',
                    severity='warning',
                    details={
                        'daily_cost_usd': daily_cost,
                        'threshold_usd': threshold,
                        'llm_cost_usd': totals.get('llm_cost_usd', 0),
                        'trading_fee_usd': totals.get('trading_fee_usd', 0),
                        'date': today
                    }
                )
                logger.warning(f"Cost alert: Daily costs ${daily_cost:.4f} exceeded threshold ${threshold:.2f}")
            else:
                logger.debug(f"Daily costs ${daily_cost:.4f} within threshold ${threshold:.2f}")

        except Exception as e:
            logger.warning(f"Failed to check cost alerts: {e}")

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
