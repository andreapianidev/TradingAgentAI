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
        news = self._get_news_safe()
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

        # Log news feed results
        logger.info("-" * 50)
        logger.info(f"NEWS FEED ({len(news)} articles):")
        if news:
            for i, article in enumerate(news[:5], 1):  # Show top 5
                sentiment_emoji = {"positive": "+", "negative": "-", "neutral": "~"}.get(article.get("sentiment", "neutral"), "~")
                logger.info(f"  [{sentiment_emoji}] {article.get('title', 'N/A')[:80]}")
        else:
            logger.info("  No relevant news found")

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
                    news=news,
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
        self._generate_daily_analysis(sentiment, news, whale_flow)

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
        news: List[Dict[str, Any]],
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
            news: Recent news
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

        # Log ATR volatility analysis
        logger.info("-" * 40)
        logger.info("VOLATILITY ANALYSIS (ATR):")
        atr = indicators.get('atr', 0)
        atr_30 = indicators.get('atr_30', 0)
        atr_pct = indicators.get('atr_pct', 0)
        volatility_ratio = indicators.get('volatility_ratio', 1.0)

        logger.info(f"  ATR (14): {atr:.2f}")
        logger.info(f"  ATR (30): {atr_30:.2f}")
        logger.info(f"  ATR%: {atr_pct:.2f}%" if atr_pct else "  ATR%: N/A")
        logger.info(f"  Volatility Ratio: {volatility_ratio:.2f}")

        if volatility_ratio < 0.8:
            vol_status = "LOW (calmer than usual)"
        elif volatility_ratio < 1.2:
            vol_status = "NORMAL"
        elif volatility_ratio < 1.5:
            vol_status = "HIGH (elevated)"
        else:
            vol_status = "EXTREME (caution!)"

        logger.info(f"  Status: {vol_status}")

        # Calculate and show recommended ranges
        if atr_pct and atr_pct > 0:
            if volatility_ratio < 1.2:
                sl_mult_range = "2.0-3.0x"
            elif volatility_ratio < 1.5:
                sl_mult_range = "1.5-2.5x"
            else:
                sl_mult_range = "1.5-2.0x"

            logger.info(f"  Recommended SL multiplier: {sl_mult_range} ATR")
            logger.info(f"  Trading Mode: {'PAPER' if portfolio_manager.is_paper_trading else 'LIVE'}")

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
            indicators={
                **indicators,
                'atr': indicators.get('atr'),
                'atr_30': indicators.get('atr_30'),
                'atr_pct': indicators.get('atr_pct'),
                'volatility_ratio': indicators.get('volatility_ratio')
            },
            pivot_points=pivot_points,
            forecast=forecast,
            orderbook=orderbook,
            sentiment=sentiment,
            raw_data={
                "market_data": market_data,
                "news_count": len(news),
                "news": news[:5] if news else [],
                "whale_alerts_count": len(whale_alerts),
                "whale_flow": whale_flow,
                "atr_analysis": {
                    "atr": indicators.get('atr'),
                    "atr_pct": indicators.get('atr_pct'),
                    "volatility_ratio": indicators.get('volatility_ratio'),
                    "trading_mode": "paper" if portfolio_manager.is_paper_trading else "live"
                }
            }
        )

        # 7. NUOVO: Advanced news analysis
        from data.news_analyzer import news_analyzer
        logger.info("Analyzing news with advanced sentiment and relevance scoring...")
        news_analysis = news_analyzer.analyze_news_for_symbol(symbol, news)

        logger.info(f"News Analysis: {news_analysis.get('aggregate_sentiment')} "
                   f"(score: {news_analysis.get('overall_score'):.2f}, "
                   f"relevance: {news_analysis.get('relevance_score'):.2f}, "
                   f"confidence: {news_analysis.get('confidence'):.2%})")

        # 8. NUOVO: Data quality validation
        from core.data_validator import data_validator
        logger.info("Validating data quality...")
        data_quality = data_validator.validate_all_data(
            market_data=market_data,
            indicators=indicators,
            pivot_points=pivot_points,
            forecast=forecast,
            orderbook=orderbook,
            sentiment=sentiment,
            news=news,
            whale_flow=whale_flow,
            coingecko=coingecko
        )

        quality = data_quality.get('overall_quality', 0)
        recommendation = data_quality.get('recommendation', 'UNKNOWN')
        logger.info(f"Data Quality: {quality:.1%} ({recommendation})")

        # Log warnings se presenti
        if data_quality.get('warnings'):
            for warning in data_quality['warnings']:
                logger.warning(f"  ⚠️  {warning}")

        # 9. NUOVO: Calculate weighted scores
        from core.data_weighting import weighting_engine

        # Determine market regime
        logger.info("Determining market regime...")
        market_regime = weighting_engine.determine_market_regime(
            indicators, coingecko, whale_flow
        )
        logger.info(f"Market Regime: {market_regime.upper()}")

        # Calculate composite score
        logger.info("Calculating weighted decision scores...")
        weighted_scores = weighting_engine.calculate_composite_score(
            symbol=symbol,
            indicators=indicators,
            pivot_points=pivot_points,
            forecast=forecast,
            whale_flow=whale_flow,
            sentiment=sentiment,
            news_analysis=news_analysis,
            coingecko=coingecko,
            market_regime=market_regime
        )

        composite_score = weighted_scores.get('composite_score', 0)
        score_confidence = weighted_scores.get('confidence', 0)
        logger.info(f"Composite Score: {composite_score:.3f} "
                   f"(confidence: {score_confidence:.2%})")

        # Log top contributing components
        components = weighted_scores.get('components', {})
        sorted_components = sorted(
            components.items(),
            key=lambda x: x[1].get('contribution', 0),
            reverse=True
        )
        logger.info("Top Contributing Factors:")
        for comp_name, comp_data in sorted_components[:3]:
            contribution = comp_data.get('contribution', 0)
            comp_score = comp_data.get('score', 0)
            logger.info(f"  • {comp_name}: score={comp_score:.3f}, contribution={contribution:.3f}")

        # 10. Check if we have an existing position
        has_position = portfolio_manager.client.has_open_position(symbol)

        # 11. Get LLM decision with enhanced prompts
        logger.info("Requesting LLM decision with specialized prompts...")

        # Add is_paper flag to portfolio dict for AI to know trading mode
        portfolio_with_mode = {
            **portfolio,
            'is_paper': portfolio_manager.is_paper_trading
        }

        # Determine action context
        action_context = "close_position" if has_position else "market_analysis"

        # Get specialized prompt
        from config.prompts import get_system_prompt_for_scenario, build_user_prompt_with_scores

        system_prompt = get_system_prompt_for_scenario(action_context, market_regime)
        user_prompt = build_user_prompt_with_scores(
            symbol=symbol,
            portfolio=portfolio_with_mode,
            market_data=market_data,
            indicators=indicators,
            pivot_points=pivot_points,
            forecast=forecast,
            orderbook=orderbook,
            sentiment=sentiment,
            news=news,
            open_positions=open_positions,
            whale_flow=whale_flow,
            coingecko=coingecko,
            weighted_scores=weighted_scores,      # NUOVO
            news_analysis=news_analysis,          # NUOVO
            data_quality=data_quality             # NUOVO
        )

        # Call LLM with specialized prompts
        decision = llm_client.get_trading_decision_with_prompts(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            symbol=symbol
        )

        action = decision.get("action", ACTION_HOLD)
        confidence = decision.get("confidence", 0)

        # Log detailed LLM decision
        logger.info("=" * 50)
        logger.info("LLM DECISION:")
        logger.info(f"  Action: {action.upper()}")
        if action != ACTION_HOLD:
            logger.info(f"  Direction: {decision.get('direction', 'N/A').upper()}")
            logger.info(f"  Position Size: {decision.get('position_size_pct', 0)}%")
            logger.info(f"  Leverage: {decision.get('leverage', 1)}x")
            logger.info(f"  Stop Loss: {decision.get('stop_loss_pct', 0)}%")
            logger.info(f"  Take Profit: {decision.get('take_profit_pct', 0)}%")
        logger.info(f"  Confidence: {confidence:.2%}")
        logger.info(f"  Reasoning: {decision.get('reasoning', 'N/A')}")
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

    def _get_news_safe(self) -> List[Dict[str, Any]]:
        """Get news with error handling and save to database."""
        try:
            news = get_recent_news(10)  # Get more news for database storage

            # Save news to database (deduplicates automatically)
            if news:
                try:
                    saved_count = db_ops.save_news_batch(news)
                    if saved_count > 0:
                        logger.debug(f"Saved {saved_count} new news items to database")
                except Exception as e:
                    logger.debug(f"Error saving news to database: {e}")

            return news[:5]  # Return top 5 for LLM analysis
        except Exception as e:
            logger.warning(f"Failed to get news: {e}")
            return []

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
        news: List[Dict[str, Any]],
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

                # Generate analysis using LLM
                analysis = llm_client.generate_market_analysis(
                    symbol=symbol,
                    price=price,
                    indicators=indicators,
                    pivot_points=pivot_points,
                    forecast=forecast,
                    sentiment=sentiment,
                    news=news,
                    whale_flow=whale_flow
                )

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
                        "total": len(news),
                        "positive": sum(1 for n in news if n.get("sentiment") == "positive"),
                        "negative": sum(1 for n in news if n.get("sentiment") == "negative"),
                        "sentiment_score": sentiment.get("score"),
                        "sentiment_label": sentiment.get("label")
                    }
                )

                logger.info(f"AI analysis for {symbol} saved: {analysis.get('market_outlook', 'N/A')}")

            except Exception as e:
                logger.warning(f"Failed to generate AI analysis for {symbol}: {e}")

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
