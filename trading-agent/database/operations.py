"""
Database CRUD operations for the trading agent.
Uses Supabase as the primary database backend.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from utils.logger import get_logger

logger = get_logger(__name__)

# Use Supabase operations
from database.supabase_operations import db_ops as supabase_ops


class DatabaseOperations:
    """CRUD operations wrapper - delegates to Supabase operations."""

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
        """Save market context data."""
        return supabase_ops.save_market_context(
            symbol=symbol,
            price=price,
            indicators=indicators,
            pivot_points=pivot_points,
            forecast=forecast,
            orderbook=orderbook,
            sentiment=sentiment,
            raw_data=raw_data
        )

    def get_latest_market_context(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the most recent market context for a symbol."""
        return supabase_ops.get_latest_market_context(symbol)

    # ============== Trade Decisions ==============

    def save_trade_decision(
        self,
        context_id: str,
        symbol: str,
        decision: Dict[str, Any],
        execution_status: str = "pending",
        raw_llm_decision: Dict[str, Any] = None
    ) -> str:
        """Save an LLM trading decision."""
        return supabase_ops.save_trade_decision(
            context_id=context_id,
            symbol=symbol,
            decision=decision,
            execution_status=execution_status,
            raw_llm_decision=raw_llm_decision
        )

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
        supabase_ops.update_trade_execution(
            trade_id=trade_id,
            status=status,
            entry_price=entry_price,
            entry_quantity=entry_quantity,
            order_id=order_id,
            details=details
        )

    def get_recent_trade_decisions(
        self,
        symbol: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent trade decisions, optionally filtered by symbol."""
        return supabase_ops.get_recent_trade_decisions(symbol=symbol, limit=limit)

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
        """Create a new position record."""
        return supabase_ops.create_position(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            quantity=quantity,
            leverage=leverage,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            entry_trade_id=entry_trade_id
        )

    def close_position(
        self,
        position_id: str,
        exit_price: float,
        exit_reason: str,
        exit_trade_id: str = None
    ) -> None:
        """Close an open position."""
        supabase_ops.close_position(
            position_id=position_id,
            exit_price=exit_price,
            exit_reason=exit_reason,
            exit_trade_id=exit_trade_id
        )

    def get_open_positions(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get all open positions, optionally filtered by symbol."""
        return supabase_ops.get_open_positions(symbol=symbol)

    def get_position_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the open position for a specific symbol (if any)."""
        return supabase_ops.get_position_by_symbol(symbol)

    def get_closed_positions(
        self,
        symbol: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get closed positions."""
        return supabase_ops.get_closed_positions(symbol=symbol, limit=limit)

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
        return supabase_ops.save_portfolio_snapshot(
            total_equity=total_equity,
            available_balance=available_balance,
            margin_used=margin_used,
            open_positions_count=open_positions_count,
            exposure_pct=exposure_pct,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            raw_data=raw_data
        )

    def get_portfolio_history(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get portfolio snapshot history."""
        return supabase_ops.get_portfolio_history(limit=limit)

    def get_latest_portfolio(self) -> Optional[Dict[str, Any]]:
        """Get the most recent portfolio snapshot."""
        return supabase_ops.get_latest_portfolio()

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
        return supabase_ops.save_news_event(
            title=title,
            summary=summary,
            source=source,
            url=url,
            published_at=published_at,
            sentiment=sentiment,
            relevance_score=relevance_score,
            symbols=symbols,
            raw_data=raw_data
        )

    def get_recent_news(
        self,
        symbol: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent news events."""
        return supabase_ops.get_recent_news(symbol=symbol, limit=limit)

    def save_news_batch(self, news_items: List[Dict[str, Any]]) -> int:
        """Save multiple news items, avoiding duplicates by URL."""
        return supabase_ops.save_news_batch(news_items)

    def save_analyzed_news_batch(self, analyzed_items: List[Dict[str, Any]]) -> int:
        """Save AI-analyzed news items with enhanced sentiment data."""
        return supabase_ops.save_analyzed_news_batch(analyzed_items)

    # ============== Statistics ==============

    def get_trading_stats(self) -> Dict[str, Any]:
        """Get trading statistics."""
        return supabase_ops.get_trading_stats()

    # ============== Position Sync ==============

    def sync_positions_from_alpaca(
        self,
        alpaca_positions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Sync positions from Alpaca to database."""
        return supabase_ops.sync_positions_from_alpaca(alpaca_positions)


# Global operations instance
db_ops = DatabaseOperations()
