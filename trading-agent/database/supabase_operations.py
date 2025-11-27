"""
Database operations using Supabase client instead of direct SQLAlchemy.
This replaces the SQLAlchemy-based operations for cloud deployment.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
import os

from supabase import create_client, Client
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class SupabaseOperations:
    """CRUD operations using Supabase client."""

    def __init__(self):
        """Initialize Supabase client."""
        self.client: Optional[Client] = None
        self._connect()

    def _connect(self):
        """Establish Supabase connection."""
        try:
            url = settings.SUPABASE_URL
            key = settings.SUPABASE_SERVICE_KEY

            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

            self.client = create_client(url, key)
            logger.info("Supabase connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise

    # ============== Market Context ==============

    def save_market_context(
        self,
        symbol: str,
        price: float,
        indicators: Dict[str, Any],
        pivot_points: Dict[str, Any],
        forecast: Dict[str, Any],
        orderbook: Dict[str, Any],
        sentiment: Dict[str, Any],
        raw_data: Dict[str, Any] = None
    ) -> str:
        """
        Save market context data.

        Returns:
            The ID of the created market context
        """
        data = {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "price": price,
            # Indicators
            "macd": indicators.get("macd"),
            "macd_signal": indicators.get("macd_signal"),
            "macd_histogram": indicators.get("macd_histogram"),
            "rsi": indicators.get("rsi"),
            "ema20": indicators.get("ema20"),
            "ema2": indicators.get("ema2"),
            # Pivot Points
            "pivot_pp": pivot_points.get("pp"),
            "pivot_r1": pivot_points.get("r1"),
            "pivot_r2": pivot_points.get("r2"),
            "pivot_s1": pivot_points.get("s1"),
            "pivot_s2": pivot_points.get("s2"),
            "pivot_distance_pct": pivot_points.get("distance_pct"),
            # Forecast
            "forecast_trend": forecast.get("trend"),
            "forecast_target_price": forecast.get("target_price"),
            "forecast_change_pct": forecast.get("change_pct"),
            "forecast_confidence": forecast.get("confidence"),
            # Order Book
            "orderbook_bid_volume": orderbook.get("bid_volume"),
            "orderbook_ask_volume": orderbook.get("ask_volume"),
            "orderbook_ratio": orderbook.get("ratio"),
            # Sentiment
            "sentiment_label": sentiment.get("label"),
            "sentiment_score": sentiment.get("score"),
            # Raw data
            "raw_data": raw_data
        }

        result = self.client.table("trading_market_contexts").insert(data).execute()
        context_id = result.data[0]["id"]
        logger.debug(f"Saved market context {context_id} for {symbol}")
        return context_id

    def get_latest_market_context(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the most recent market context for a symbol."""
        result = self.client.table("trading_market_contexts") \
            .select("*") \
            .eq("symbol", symbol) \
            .order("timestamp", desc=True) \
            .limit(1) \
            .execute()

        return result.data[0] if result.data else None

    # ============== Trade Decisions ==============

    def save_trade_decision(
        self,
        context_id: str,
        symbol: str,
        decision: Dict[str, Any],
        execution_status: str = "pending",
        raw_llm_decision: Dict[str, Any] = None
    ) -> str:
        """
        Save an LLM trading decision.

        Returns:
            The ID of the created trade decision
        """
        # Store sanitized decision fields (may be null if converted to HOLD)
        # and raw LLM decision in execution_details for analysis
        data = {
            "context_id": context_id,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "action": decision.get("action"),
            "direction": decision.get("direction"),
            "leverage": decision.get("leverage"),
            "position_size_pct": decision.get("position_size_pct"),
            "stop_loss_pct": decision.get("stop_loss_pct"),
            "take_profit_pct": decision.get("take_profit_pct"),
            "confidence": decision.get("confidence"),
            "reasoning": decision.get("reasoning"),
            "execution_status": execution_status,
            "trading_mode": "paper" if settings.PAPER_TRADING else "live",
            # Store raw LLM decision in execution_details for analysis
            "execution_details": {"raw_llm_decision": raw_llm_decision} if raw_llm_decision else None
        }

        result = self.client.table("trading_decisions").insert(data).execute()
        trade_id = result.data[0]["id"]
        logger.debug(f"Saved trade decision {trade_id} for {symbol}")
        return trade_id

    def update_trade_execution(
        self,
        trade_id: str,
        status: str,
        entry_price: float = None,
        entry_quantity: float = None,
        order_id: str = None,
        details: Dict[str, Any] = None
    ) -> None:
        """Update trade decision with execution details."""
        update_data = {
            "execution_status": status,
            "execution_timestamp": datetime.utcnow().isoformat()
        }

        if entry_price is not None:
            update_data["entry_price"] = entry_price
        if entry_quantity is not None:
            update_data["entry_quantity"] = entry_quantity
        if order_id is not None:
            update_data["order_id"] = order_id
        if details is not None:
            update_data["execution_details"] = details

        self.client.table("trading_decisions") \
            .update(update_data) \
            .eq("id", trade_id) \
            .execute()

        logger.debug(f"Updated trade {trade_id} execution: {status}")

    def get_recent_trade_decisions(
        self,
        symbol: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent trade decisions, optionally filtered by symbol."""
        query = self.client.table("trading_decisions").select("*")

        if symbol:
            query = query.eq("symbol", symbol)

        result = query.order("timestamp", desc=True).limit(limit).execute()
        return result.data

    # ============== Positions ==============

    def create_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        quantity: float,
        leverage: int,
        stop_loss_price: float,
        take_profit_price: float,
        entry_trade_id: str
    ) -> str:
        """
        Create a new position record.

        Returns:
            The ID of the created position
        """
        data = {
            "symbol": symbol,
            "direction": direction,
            "entry_timestamp": datetime.utcnow().isoformat(),
            "entry_price": entry_price,
            "quantity": quantity,
            "leverage": leverage,
            "entry_trade_id": entry_trade_id,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "status": "open",
            "trading_mode": "paper" if settings.PAPER_TRADING else "live"
        }

        result = self.client.table("trading_positions").insert(data).execute()
        position_id = result.data[0]["id"]
        logger.info(f"Created position {position_id}: {symbol} {direction}")
        return position_id

    def close_position(
        self,
        position_id: str,
        exit_price: float,
        exit_reason: str,
        exit_trade_id: str = None
    ) -> None:
        """Close an open position."""
        # First get the position to calculate P&L
        result = self.client.table("trading_positions") \
            .select("*") \
            .eq("id", position_id) \
            .execute()

        if not result.data:
            logger.warning(f"Position {position_id} not found")
            return

        position = result.data[0]
        entry_price = float(position["entry_price"])
        quantity = float(position["quantity"])
        leverage = position["leverage"]
        direction = position["direction"]

        # Calculate P&L
        if direction == "long":
            pnl = (exit_price - entry_price) * quantity
            pnl_pct = ((exit_price / entry_price) - 1) * 100 * leverage
        else:  # short
            pnl = (entry_price - exit_price) * quantity
            pnl_pct = ((entry_price / exit_price) - 1) * 100 * leverage

        update_data = {
            "exit_timestamp": datetime.utcnow().isoformat(),
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "status": "closed",
            "realized_pnl": pnl,
            "realized_pnl_pct": pnl_pct
        }

        if exit_trade_id:
            update_data["exit_trade_id"] = exit_trade_id

        self.client.table("trading_positions") \
            .update(update_data) \
            .eq("id", position_id) \
            .execute()

        logger.info(f"Closed position {position_id}: {position['symbol']} PnL: ${pnl:.2f} ({pnl_pct:.2f}%)")

    def get_open_positions(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get all open positions, optionally filtered by symbol."""
        query = self.client.table("trading_positions") \
            .select("*") \
            .eq("status", "open")

        if symbol:
            query = query.eq("symbol", symbol)

        result = query.execute()
        return result.data

    def get_position_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the open position for a specific symbol (if any)."""
        result = self.client.table("trading_positions") \
            .select("*") \
            .eq("symbol", symbol) \
            .eq("status", "open") \
            .execute()

        return result.data[0] if result.data else None

    def get_closed_positions(
        self,
        symbol: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get closed positions."""
        query = self.client.table("trading_positions") \
            .select("*") \
            .eq("status", "closed")

        if symbol:
            query = query.eq("symbol", symbol)

        result = query.order("exit_timestamp", desc=True).limit(limit).execute()
        return result.data

    # ============== Portfolio Snapshots ==============

    def save_portfolio_snapshot(
        self,
        total_equity: float,
        available_balance: float,
        margin_used: float,
        open_positions_count: int,
        exposure_pct: float,
        total_pnl: float = None,
        total_pnl_pct: float = None,
        raw_data: Dict[str, Any] = None
    ) -> str:
        """Save a portfolio snapshot."""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_equity_usdc": total_equity,
            "available_balance_usdc": available_balance,
            "margin_used_usdc": margin_used,
            "open_positions_count": open_positions_count,
            "exposure_pct": exposure_pct,
            "total_pnl": total_pnl or 0,
            "total_pnl_pct": total_pnl_pct or 0,
            "raw_data": raw_data,
            "trading_mode": "paper" if settings.PAPER_TRADING else "live"
        }

        result = self.client.table("trading_portfolio_snapshots").insert(data).execute()
        return result.data[0]["id"]

    def get_portfolio_history(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get portfolio snapshot history."""
        result = self.client.table("trading_portfolio_snapshots") \
            .select("*") \
            .order("timestamp", desc=True) \
            .limit(limit) \
            .execute()

        return result.data

    def get_latest_portfolio(self) -> Optional[Dict[str, Any]]:
        """Get the most recent portfolio snapshot."""
        result = self.client.table("trading_portfolio_snapshots") \
            .select("*") \
            .order("timestamp", desc=True) \
            .limit(1) \
            .execute()

        return result.data[0] if result.data else None

    # ============== News Events ==============

    def save_news_event(
        self,
        title: str,
        summary: str = None,
        source: str = None,
        url: str = None,
        published_at: datetime = None,
        sentiment: str = None,
        relevance_score: float = None,
        symbols: List[str] = None,
        raw_data: Dict[str, Any] = None
    ) -> str:
        """Save a news event."""
        data = {
            "title": title,
            "summary": summary,
            "source": source,
            "url": url,
            "published_at": published_at.isoformat() if published_at else None,
            "sentiment": sentiment or "neutral",
            "symbols": symbols,
            "raw_data": raw_data
        }

        result = self.client.table("trading_news").insert(data).execute()
        return result.data[0]["id"]

    def get_recent_news(
        self,
        symbol: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent news events."""
        query = self.client.table("trading_news").select("*")

        if symbol:
            query = query.contains("symbols", [symbol])

        result = query.order("published_at", desc=True).limit(limit).execute()
        return result.data

    # ============== Alerts ==============

    def save_alert(
        self,
        alert_type: str,
        title: str,
        message: str,
        severity: str = "info",
        symbol: str = None,
        position_id: str = None,
        decision_id: str = None,
        details: Dict[str, Any] = None
    ) -> str:
        """Save an alert."""
        data = {
            "alert_type": alert_type,
            "title": title,
            "message": message,
            "severity": severity,
            "symbol": symbol,
            "position_id": position_id,
            "decision_id": decision_id,
            "details": details,
            "is_read": False,
            "is_dismissed": False,
            "trading_mode": "paper" if settings.PAPER_TRADING else "live"
        }

        result = self.client.table("trading_alerts").insert(data).execute()
        return result.data[0]["id"]

    def get_unread_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get unread alerts."""
        result = self.client.table("trading_alerts") \
            .select("*") \
            .eq("is_read", False) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        return result.data

    # ============== Statistics ==============

    def get_trading_stats(self) -> Dict[str, Any]:
        """Get trading statistics."""
        # Get total trades
        decisions_result = self.client.table("trading_decisions") \
            .select("id", count="exact") \
            .in_("action", ["open", "close"]) \
            .execute()

        total_trades = decisions_result.count or 0

        # Get closed positions for win rate
        closed_result = self.client.table("trading_positions") \
            .select("*") \
            .eq("status", "closed") \
            .execute()

        closed_positions = closed_result.data or []

        if closed_positions:
            wins = sum(1 for p in closed_positions if float(p.get("realized_pnl") or 0) > 0)
            total_pnl = sum(float(p.get("realized_pnl") or 0) for p in closed_positions)
            win_rate = wins / len(closed_positions) if closed_positions else 0
        else:
            wins = 0
            total_pnl = 0
            win_rate = 0

        return {
            "total_trades": total_trades,
            "closed_positions": len(closed_positions),
            "wins": wins,
            "losses": len(closed_positions) - wins,
            "win_rate": win_rate,
            "total_pnl": total_pnl
        }

    # ============== Bot Logs ==============

    def save_bot_log(
        self,
        message: str,
        log_level: str = "INFO",
        component: str = None,
        symbol: str = None,
        cycle_id: str = None,
        details: Dict[str, Any] = None,
        error_stack: str = None
    ) -> str:
        """Save a bot log entry."""
        data = {
            "message": message,
            "log_level": log_level,
            "component": component,
            "symbol": symbol,
            "cycle_id": cycle_id,
            "details": details,
            "error_stack": error_stack,
            "trading_mode": "paper" if settings.PAPER_TRADING else "live"
        }

        result = self.client.table("trading_bot_logs").insert(data).execute()
        return result.data[0]["id"]

    # ============== Trading Cycles ==============

    def start_trading_cycle(self) -> str:
        """Start a new trading cycle."""
        data = {
            "started_at": datetime.utcnow().isoformat(),
            "status": "running",
            "trading_mode": "paper" if settings.PAPER_TRADING else "live"
        }

        result = self.client.table("trading_cycles").insert(data).execute()
        return result.data[0]["id"]

    def complete_trading_cycle(
        self,
        cycle_id: str,
        symbols_processed: int = 0,
        decisions_made: int = 0,
        orders_executed: int = 0,
        errors_count: int = 0,
        error_message: str = None,
        results: Dict[str, Any] = None
    ) -> None:
        """Complete a trading cycle."""
        started_result = self.client.table("trading_cycles") \
            .select("started_at") \
            .eq("id", cycle_id) \
            .execute()

        started_at = None
        duration = None
        if started_result.data:
            started_at = datetime.fromisoformat(started_result.data[0]["started_at"].replace("Z", "+00:00"))
            duration = (datetime.utcnow() - started_at.replace(tzinfo=None)).total_seconds()

        update_data = {
            "completed_at": datetime.utcnow().isoformat(),
            "status": "failed" if errors_count > 0 else "completed",
            "duration_seconds": duration,
            "symbols_processed": symbols_processed,
            "decisions_made": decisions_made,
            "orders_executed": orders_executed,
            "errors_count": errors_count,
            "error_message": error_message,
            "results": results
        }

        self.client.table("trading_cycles") \
            .update(update_data) \
            .eq("id", cycle_id) \
            .execute()


    # ============== AI Analysis ==============

    def save_ai_analysis(
        self,
        symbol: str,
        summary_text: str,
        market_outlook: str,
        confidence_score: float,
        key_levels: Dict[str, Any] = None,
        risk_factors: List[str] = None,
        opportunities: List[str] = None,
        trend_strength: str = None,
        momentum: str = None,
        volatility_level: str = None,
        indicators_snapshot: Dict[str, Any] = None,
        news_sentiment_summary: Dict[str, Any] = None
    ) -> str:
        """
        Save daily AI-generated market analysis.
        Uses UPSERT to update if analysis for this date/symbol already exists.

        Returns:
            The ID of the created/updated analysis
        """
        from datetime import date

        data = {
            "analysis_date": date.today().isoformat(),
            "symbol": symbol,
            "summary_text": summary_text,
            "market_outlook": market_outlook,
            "confidence_score": confidence_score,
            "key_levels": key_levels,
            "risk_factors": risk_factors,
            "opportunities": opportunities,
            "trend_strength": trend_strength,
            "momentum": momentum,
            "volatility_level": volatility_level,
            "indicators_snapshot": indicators_snapshot,
            "news_sentiment_summary": news_sentiment_summary,
            "trading_mode": "paper" if settings.PAPER_TRADING else "live"
        }

        result = self.client.table("trading_ai_analysis") \
            .upsert(data, on_conflict="analysis_date,symbol") \
            .execute()

        analysis_id = result.data[0]["id"]
        logger.info(f"Saved AI analysis for {symbol} on {date.today()}")
        return analysis_id

    def get_latest_ai_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the most recent AI analysis for a symbol."""
        result = self.client.table("trading_ai_analysis") \
            .select("*") \
            .eq("symbol", symbol) \
            .order("analysis_date", desc=True) \
            .limit(1) \
            .execute()

        return result.data[0] if result.data else None

    def should_generate_analysis(self, symbol: str) -> bool:
        """Check if we need to generate new analysis today."""
        from datetime import date

        result = self.client.table("trading_ai_analysis") \
            .select("id") \
            .eq("symbol", symbol) \
            .eq("analysis_date", date.today().isoformat()) \
            .execute()

        return len(result.data) == 0

    # ============== News (Batch) ==============

    def save_news_batch(self, news_items: List[Dict[str, Any]]) -> int:
        """
        Save multiple news items, avoiding duplicates by URL.

        Returns:
            Number of news items saved
        """
        if not news_items:
            return 0

        saved_count = 0
        for item in news_items:
            try:
                # Check if news already exists by URL
                url = item.get("url")
                if url:
                    existing = self.client.table("trading_news") \
                        .select("id") \
                        .eq("url", url) \
                        .execute()

                    if existing.data:
                        continue  # Skip duplicate

                # Parse published_at if it's a string
                published_at = item.get("published_at")
                if isinstance(published_at, str):
                    try:
                        from dateutil import parser
                        published_at = parser.parse(published_at).isoformat()
                    except:
                        published_at = datetime.utcnow().isoformat()

                data = {
                    "title": item.get("title", "")[:500],
                    "summary": (item.get("summary") or "")[:1000],
                    "source": item.get("source", "RSS Feed"),
                    "url": url,
                    "published_at": published_at,
                    "sentiment": item.get("sentiment", "neutral"),
                    "symbols": item.get("symbols"),
                    "raw_data": item.get("raw_data")
                }

                self.client.table("trading_news").insert(data).execute()
                saved_count += 1

            except Exception as e:
                logger.debug(f"Error saving news item: {e}")
                continue

        if saved_count > 0:
            logger.info(f"Saved {saved_count} news items to database")
        return saved_count

    def save_analyzed_news_batch(self, analyzed_items: List[Dict[str, Any]]) -> int:
        """
        Save AI-analyzed news items with enhanced sentiment data.

        This updates existing news items with AI analysis or creates new entries.

        Args:
            analyzed_items: List of analyzed news items from news_analyzer

        Returns:
            Number of items saved/updated
        """
        if not analyzed_items:
            return 0

        saved_count = 0
        for item in analyzed_items:
            try:
                url = item.get("url")
                if not url:
                    continue

                # Parse published_at if it's a string
                published_at = item.get("published_at")
                if isinstance(published_at, str):
                    try:
                        from dateutil import parser
                        published_at = parser.parse(published_at).isoformat()
                    except Exception:
                        published_at = datetime.utcnow().isoformat()

                # Build AI analysis data
                ai_analysis = {
                    "ai_summary": item.get("summary", ""),
                    "ai_sentiment": item.get("sentiment", "neutral"),
                    "ai_sentiment_score": item.get("sentiment_score", 0.0),
                    "ai_impact_level": item.get("impact_level", "low"),
                    "ai_affected_symbols": item.get("affected_symbols", []),
                    "ai_key_points": item.get("key_points", []),
                    "ai_market_implications": item.get("market_implications", ""),
                    "analysis_method": item.get("analysis_method", "deepseek"),
                    "has_full_content": item.get("has_full_content", False),
                    "content_length": item.get("content_length", 0),
                    "age_hours": item.get("age_hours", 0),
                }

                data = {
                    "title": item.get("title", "")[:500],
                    "summary": item.get("summary", "")[:1000],
                    "source": item.get("source", "RSS Feed"),
                    "url": url,
                    "published_at": published_at,
                    "sentiment": item.get("sentiment", "neutral"),
                    "symbols": item.get("affected_symbols"),
                    "raw_data": ai_analysis
                }

                # Check if news exists
                existing = self.client.table("trading_news") \
                    .select("id") \
                    .eq("url", url) \
                    .execute()

                if existing.data:
                    # Update with AI analysis
                    self.client.table("trading_news") \
                        .update({"raw_data": ai_analysis, "sentiment": item.get("sentiment", "neutral")}) \
                        .eq("url", url) \
                        .execute()
                else:
                    # Insert new
                    self.client.table("trading_news").insert(data).execute()

                saved_count += 1

            except Exception as e:
                logger.debug(f"Error saving analyzed news item: {e}")
                continue

        if saved_count > 0:
            logger.info(f"Saved/updated {saved_count} AI-analyzed news items to database")
        return saved_count

    # ============== Whale Alerts ==============

    def save_whale_alert(
        self,
        symbol: str,
        amount: float = None,
        amount_usd: float = None,
        blockchain: str = None,
        from_address: str = None,
        from_type: str = None,
        to_address: str = None,
        to_type: str = None,
        tx_hash: str = None,
        transaction_time: datetime = None,
        flow_direction: str = None,
        raw_data: Dict[str, Any] = None
    ) -> str:
        """Save a whale alert transaction."""
        data = {
            "symbol": symbol,
            "amount": amount,
            "amount_usd": amount_usd,
            "blockchain": blockchain,
            "from_address": from_address,
            "from_type": from_type,
            "to_address": to_address,
            "to_type": to_type,
            "tx_hash": tx_hash,
            "transaction_time": transaction_time.isoformat() if transaction_time else None,
            "flow_direction": flow_direction,
            "raw_data": raw_data
        }

        result = self.client.table("trading_whale_alerts").insert(data).execute()
        return result.data[0]["id"]

    def save_whale_alerts_batch(self, alerts: List[Dict[str, Any]]) -> int:
        """
        Save multiple whale alerts, avoiding duplicates by tx_hash.

        Returns:
            Number of alerts saved
        """
        if not alerts:
            return 0

        saved_count = 0
        for alert in alerts:
            try:
                # Check if alert already exists by tx_hash
                tx_hash = alert.get("hash") or alert.get("tx_hash")
                if tx_hash:
                    existing = self.client.table("trading_whale_alerts") \
                        .select("id") \
                        .eq("tx_hash", tx_hash) \
                        .execute()

                    if existing.data:
                        continue  # Skip duplicate

                # Determine flow direction
                from_type = alert.get("from_type", "")
                to_type = alert.get("to_type", "")

                if "exchange" in to_type.lower():
                    flow_direction = "inflow"
                elif "exchange" in from_type.lower():
                    flow_direction = "outflow"
                else:
                    flow_direction = "transfer"

                data = {
                    "symbol": alert.get("symbol", "BTC"),
                    "amount": alert.get("amount"),
                    "amount_usd": alert.get("amount_usd"),
                    "blockchain": alert.get("blockchain"),
                    "from_type": from_type,
                    "to_type": to_type,
                    "tx_hash": tx_hash,
                    "flow_direction": flow_direction,
                    "raw_data": alert
                }

                self.client.table("trading_whale_alerts").insert(data).execute()
                saved_count += 1

            except Exception as e:
                logger.debug(f"Error saving whale alert: {e}")
                continue

        if saved_count > 0:
            logger.info(f"Saved {saved_count} whale alerts to database")
        return saved_count

    def save_whale_flow_summary(
        self,
        symbol: str,
        inflow_exchange: float,
        outflow_exchange: float,
        net_flow: float,
        alert_count: int,
        interpretation: str = None,
        period_start: datetime = None,
        period_end: datetime = None
    ) -> str:
        """Save a whale flow summary."""
        data = {
            "symbol": symbol,
            "inflow_exchange": inflow_exchange,
            "outflow_exchange": outflow_exchange,
            "net_flow": net_flow,
            "alert_count": alert_count,
            "interpretation": interpretation,
            "period_start": period_start.isoformat() if period_start else None,
            "period_end": period_end.isoformat() if period_end else None
        }

        result = self.client.table("trading_whale_flow_summary").insert(data).execute()
        return result.data[0]["id"]

    def get_recent_whale_alerts(
        self,
        symbol: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent whale alerts."""
        query = self.client.table("trading_whale_alerts").select("*")

        if symbol:
            query = query.eq("symbol", symbol)

        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data


    # ============== Position Sync ==============

    def sync_positions_from_alpaca(self, alpaca_positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synchronize positions from Alpaca to database.
        - Closes positions in DB that don't exist on Alpaca
        - Creates new positions that exist on Alpaca but not in DB
        - Updates existing positions with current data

        Args:
            alpaca_positions: List of positions from Alpaca API

        Returns:
            Sync results with created, updated, closed counts
        """
        results = {
            "created": [],
            "updated": [],
            "closed": [],
            "duplicates_cleaned": 0
        }

        now = datetime.utcnow().isoformat()
        trading_mode = "paper" if settings.PAPER_TRADING else "live"

        # Get existing open positions from database
        db_result = self.client.table("trading_positions") \
            .select("*") \
            .eq("status", "open") \
            .execute()

        db_positions = db_result.data or []

        # Handle duplicates: group by symbol
        positions_by_symbol = {}
        for pos in db_positions:
            symbol = pos["symbol"]
            if symbol not in positions_by_symbol:
                positions_by_symbol[symbol] = []
            positions_by_symbol[symbol].append(pos)

        # Close duplicate positions (keep most recent per symbol)
        for symbol, positions in positions_by_symbol.items():
            if len(positions) > 1:
                # Sort by created_at desc
                positions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                duplicates = positions[1:]
                for dup in duplicates:
                    self.client.table("trading_positions") \
                        .update({
                            "status": "closed",
                            "exit_timestamp": now,
                            "exit_reason": "duplicate_cleanup",
                            "updated_at": now
                        }) \
                        .eq("id", dup["id"]) \
                        .execute()
                    results["duplicates_cleaned"] += 1
                    logger.info(f"Closed duplicate position {dup['id']} for {symbol}")

        # Build map with only most recent position per symbol
        db_position_map = {
            symbol: sorted(positions, key=lambda x: x.get("created_at", ""), reverse=True)[0]
            for symbol, positions in positions_by_symbol.items()
        }

        # Extract Alpaca symbols set
        alpaca_symbols = set()

        # Process Alpaca positions
        for pos in alpaca_positions:
            symbol = pos.get("symbol", "")
            # Remove /USD suffix for crypto
            if "/" in symbol:
                symbol = symbol.split("/")[0]

            alpaca_symbols.add(symbol)

            qty = abs(float(pos.get("quantity", 0)))
            direction = pos.get("direction", "long")
            entry_price = float(pos.get("entry_price", 0))
            unrealized_pnl = float(pos.get("unrealized_pnl", 0))
            unrealized_pnl_pct = float(pos.get("unrealized_pnl_pct", 0))

            existing = db_position_map.get(symbol)

            if existing:
                # Update existing position
                self.client.table("trading_positions") \
                    .update({
                        "quantity": qty,
                        "entry_price": entry_price,
                        "unrealized_pnl": unrealized_pnl,
                        "unrealized_pnl_pct": unrealized_pnl_pct,
                        "updated_at": now
                    }) \
                    .eq("id", existing["id"]) \
                    .execute()
                results["updated"].append(symbol)
                logger.debug(f"Updated position for {symbol}")
            else:
                # Create new position
                self.client.table("trading_positions") \
                    .insert({
                        "symbol": symbol,
                        "direction": direction,
                        "entry_timestamp": now,
                        "entry_price": entry_price,
                        "quantity": qty,
                        "leverage": 1,
                        "unrealized_pnl": unrealized_pnl,
                        "unrealized_pnl_pct": unrealized_pnl_pct,
                        "status": "open",
                        "trading_mode": trading_mode
                    }) \
                    .execute()
                results["created"].append(symbol)
                logger.info(f"Created position from Alpaca sync: {symbol}")

        # Close positions that exist in DB but not in Alpaca
        for symbol, position in db_position_map.items():
            if symbol not in alpaca_symbols:
                self.client.table("trading_positions") \
                    .update({
                        "status": "closed",
                        "exit_timestamp": now,
                        "exit_reason": "sync_not_found_on_alpaca",
                        "updated_at": now
                    }) \
                    .eq("id", position["id"]) \
                    .execute()
                results["closed"].append(symbol)
                logger.info(f"Closed position not found on Alpaca: {symbol}")

        logger.info(f"Position sync complete: created={len(results['created'])}, "
                   f"updated={len(results['updated'])}, closed={len(results['closed'])}, "
                   f"duplicates_cleaned={results['duplicates_cleaned']}")

        return results

    # ============== CoinGecko Market Global ==============

    def save_market_global(self, coingecko_data: Dict[str, Any]) -> Optional[str]:
        """
        Save CoinGecko global market data.

        Args:
            coingecko_data: CoinGecko market summary data

        Returns:
            ID of the saved record or None
        """
        try:
            global_data = coingecko_data.get("global", {})
            trending = coingecko_data.get("trending", [])
            trending_symbols = coingecko_data.get("trending_symbols", [])
            tracked_trending = coingecko_data.get("tracked_trending", [])

            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "btc_dominance": global_data.get("btc_dominance"),
                "eth_dominance": global_data.get("eth_dominance"),
                "total_market_cap_usd": global_data.get("total_market_cap_usd"),
                "total_volume_24h_usd": global_data.get("total_volume_24h_usd"),
                "market_cap_change_24h_pct": global_data.get("market_cap_change_24h_pct"),
                "active_cryptocurrencies": global_data.get("active_cryptocurrencies"),
                "trending_coins": trending,
                "trending_symbols": trending_symbols,
                "tracked_trending": tracked_trending
            }

            result = self.client.table("trading_market_global").insert(data).execute()

            if result.data:
                return result.data[0]["id"]
            return None

        except Exception as e:
            logger.warning(f"Failed to save market global data: {e}")
            return None


    # ============== Cost Tracking ==============

    def save_llm_cost(
        self,
        symbol: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        cached_tokens: int = 0,
        model: str = None,
        decision_id: str = None,
        details: Dict[str, Any] = None
    ) -> str:
        """
        Save LLM API cost record.

        Returns:
            ID of the created cost record
        """
        data = {
            "cost_type": "llm",
            "llm_provider": "deepseek",
            "llm_model": model or "deepseek-chat",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "cost_usd": cost_usd,
            "symbol": symbol,
            "decision_id": decision_id,
            "trading_mode": "paper" if settings.PAPER_TRADING else "live",
            "details": details
        }

        result = self.client.table("trading_costs").insert(data).execute()
        cost_id = result.data[0]["id"]
        logger.debug(f"Saved LLM cost {cost_id}: ${cost_usd:.6f} for {symbol}")
        return cost_id

    def save_trading_fee(
        self,
        symbol: str,
        trade_value_usd: float,
        fee_usd: float,
        fee_type: str = "taker",
        position_id: str = None,
        estimated_fee_usd: float = None
    ) -> str:
        """
        Save trading fee record.

        Returns:
            ID of the created cost record
        """
        fee_rate = 0.00075 if not settings.PAPER_TRADING else 0

        data = {
            "cost_type": "trading_fee",
            "fee_type": fee_type,
            "trade_value_usd": trade_value_usd,
            "fee_rate": fee_rate,
            "cost_usd": fee_usd,
            "symbol": symbol,
            "position_id": position_id,
            "trading_mode": "paper" if settings.PAPER_TRADING else "live",
            "details": {"estimated_live_fee_usd": estimated_fee_usd} if estimated_fee_usd else None
        }

        result = self.client.table("trading_costs").insert(data).execute()
        cost_id = result.data[0]["id"]
        logger.debug(f"Saved trading fee {cost_id}: ${fee_usd:.4f} for {symbol}")
        return cost_id

    def get_costs_by_date_range(
        self,
        start_date: str,
        end_date: str = None,
        cost_type: str = None,
        symbol: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get cost records for a date range.

        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format), defaults to now
            cost_type: Filter by 'llm' or 'trading_fee'
            symbol: Filter by symbol

        Returns:
            List of cost records
        """
        query = self.client.table("trading_costs") \
            .select("*") \
            .gte("created_at", start_date)

        if end_date:
            query = query.lte("created_at", end_date)

        if cost_type:
            query = query.eq("cost_type", cost_type)

        if symbol:
            query = query.eq("symbol", symbol)

        result = query.order("created_at", desc=True).execute()
        return result.data

    def get_cost_totals(
        self,
        start_date: str,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        Get aggregated cost totals for a period.

        Returns:
            Dictionary with llm and trading fee totals
        """
        costs = self.get_costs_by_date_range(start_date, end_date)

        llm_costs = [c for c in costs if c["cost_type"] == "llm"]
        fee_costs = [c for c in costs if c["cost_type"] == "trading_fee"]

        return {
            "llm_total_usd": sum(float(c["cost_usd"]) for c in llm_costs),
            "llm_calls": len(llm_costs),
            "llm_input_tokens": sum(c.get("input_tokens") or 0 for c in llm_costs),
            "llm_output_tokens": sum(c.get("output_tokens") or 0 for c in llm_costs),
            "llm_cached_tokens": sum(c.get("cached_tokens") or 0 for c in llm_costs),
            "trading_fees_total_usd": sum(float(c["cost_usd"]) for c in fee_costs),
            "trades_count": len(fee_costs),
            "total_cost_usd": sum(float(c["cost_usd"]) for c in costs)
        }

    def update_decision_llm_cost(
        self,
        decision_id: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        cached_tokens: int = 0
    ) -> None:
        """Update a trading decision with LLM cost info."""
        self.client.table("trading_decisions") \
            .update({
                "llm_input_tokens": input_tokens,
                "llm_output_tokens": output_tokens,
                "llm_cached_tokens": cached_tokens,
                "llm_cost_usd": cost_usd
            }) \
            .eq("id", decision_id) \
            .execute()

        logger.debug(f"Updated decision {decision_id} with LLM cost: ${cost_usd:.6f}")


# Global operations instance
db_ops = SupabaseOperations()
