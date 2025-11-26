"""
Database CRUD operations for the trading agent.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import desc

from database.models import (
    MarketContext, TradeDecision, Position,
    PortfolioSnapshot, NewsEvent
)
from database.connection import db_manager
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseOperations:
    """CRUD operations for all database models."""

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
    ) -> int:
        """
        Save market context data.

        Returns:
            The ID of the created market context
        """
        with db_manager.get_session() as session:
            context = MarketContext(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                price=price,
                # Indicators
                macd=indicators.get("macd"),
                macd_signal=indicators.get("macd_signal"),
                macd_histogram=indicators.get("macd_histogram"),
                rsi=indicators.get("rsi"),
                ema20=indicators.get("ema20"),
                ema2=indicators.get("ema2"),
                # Pivot Points
                pivot_pp=pivot_points.get("pp"),
                pivot_r1=pivot_points.get("r1"),
                pivot_r2=pivot_points.get("r2"),
                pivot_s1=pivot_points.get("s1"),
                pivot_s2=pivot_points.get("s2"),
                pivot_distance_pct=pivot_points.get("distance_pct"),
                # Forecast
                forecast_trend=forecast.get("trend"),
                forecast_target_price=forecast.get("target_price"),
                forecast_change_pct=forecast.get("change_pct"),
                forecast_confidence=forecast.get("confidence"),
                # Order Book
                orderbook_bid_volume=orderbook.get("bid_volume"),
                orderbook_ask_volume=orderbook.get("ask_volume"),
                orderbook_ratio=orderbook.get("ratio"),
                # Sentiment
                sentiment_label=sentiment.get("label"),
                sentiment_score=sentiment.get("score"),
                # Raw data
                raw_data=raw_data
            )
            session.add(context)
            session.flush()
            context_id = context.id
            logger.debug(f"Saved market context {context_id} for {symbol}")
            return context_id

    def get_latest_market_context(self, symbol: str) -> Optional[MarketContext]:
        """Get the most recent market context for a symbol."""
        with db_manager.get_session() as session:
            return session.query(MarketContext).filter(
                MarketContext.symbol == symbol
            ).order_by(desc(MarketContext.timestamp)).first()

    # ============== Trade Decisions ==============

    def save_trade_decision(
        self,
        context_id: int,
        symbol: str,
        decision: Dict[str, Any],
        execution_status: str = "pending"
    ) -> int:
        """
        Save an LLM trading decision.

        Returns:
            The ID of the created trade decision
        """
        with db_manager.get_session() as session:
            trade = TradeDecision(
                context_id=context_id,
                symbol=symbol,
                timestamp=datetime.utcnow(),
                action=decision.get("action"),
                direction=decision.get("direction"),
                leverage=decision.get("leverage"),
                position_size_pct=decision.get("position_size_pct"),
                stop_loss_pct=decision.get("stop_loss_pct"),
                take_profit_pct=decision.get("take_profit_pct"),
                confidence=decision.get("confidence"),
                reasoning=decision.get("reasoning"),
                execution_status=execution_status
            )
            session.add(trade)
            session.flush()
            trade_id = trade.id
            logger.debug(f"Saved trade decision {trade_id} for {symbol}")
            return trade_id

    def update_trade_execution(
        self,
        trade_id: int,
        status: str,
        entry_price: float = None,
        entry_quantity: float = None,
        order_id: str = None,
        details: Dict[str, Any] = None
    ) -> None:
        """Update trade decision with execution details."""
        with db_manager.get_session() as session:
            trade = session.query(TradeDecision).filter(
                TradeDecision.id == trade_id
            ).first()
            if trade:
                trade.execution_status = status
                trade.execution_timestamp = datetime.utcnow()
                trade.entry_price = entry_price
                trade.entry_quantity = entry_quantity
                trade.order_id = order_id
                trade.execution_details = details
                logger.debug(f"Updated trade {trade_id} execution: {status}")

    def get_recent_trade_decisions(
        self,
        symbol: str = None,
        limit: int = 100
    ) -> List[TradeDecision]:
        """Get recent trade decisions, optionally filtered by symbol."""
        with db_manager.get_session() as session:
            query = session.query(TradeDecision)
            if symbol:
                query = query.filter(TradeDecision.symbol == symbol)
            return query.order_by(desc(TradeDecision.timestamp)).limit(limit).all()

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
        entry_trade_id: int
    ) -> int:
        """
        Create a new position record.

        Returns:
            The ID of the created position
        """
        with db_manager.get_session() as session:
            position = Position(
                symbol=symbol,
                direction=direction,
                entry_timestamp=datetime.utcnow(),
                entry_price=entry_price,
                quantity=quantity,
                leverage=leverage,
                entry_trade_id=entry_trade_id,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                status="open"
            )
            session.add(position)
            session.flush()
            position_id = position.id
            logger.info(f"Created position {position_id}: {symbol} {direction}")
            return position_id

    def close_position(
        self,
        position_id: int,
        exit_price: float,
        exit_reason: str,
        exit_trade_id: int = None
    ) -> None:
        """Close an open position."""
        with db_manager.get_session() as session:
            position = session.query(Position).filter(
                Position.id == position_id
            ).first()
            if position:
                position.exit_timestamp = datetime.utcnow()
                position.exit_price = exit_price
                position.exit_reason = exit_reason
                position.exit_trade_id = exit_trade_id
                position.status = "closed"

                # Calculate P&L
                if position.direction == "long":
                    pnl = (exit_price - float(position.entry_price)) * float(position.quantity)
                    pnl_pct = ((exit_price / float(position.entry_price)) - 1) * 100 * position.leverage
                else:  # short
                    pnl = (float(position.entry_price) - exit_price) * float(position.quantity)
                    pnl_pct = ((float(position.entry_price) / exit_price) - 1) * 100 * position.leverage

                position.realized_pnl = pnl
                position.realized_pnl_pct = pnl_pct
                logger.info(
                    f"Closed position {position_id}: {position.symbol} "
                    f"PnL: ${pnl:.2f} ({pnl_pct:.2f}%)"
                )

    def get_open_positions(self, symbol: str = None) -> List[Position]:
        """Get all open positions, optionally filtered by symbol."""
        with db_manager.get_session() as session:
            query = session.query(Position).filter(Position.status == "open")
            if symbol:
                query = query.filter(Position.symbol == symbol)
            return query.all()

    def get_position_by_symbol(self, symbol: str) -> Optional[Position]:
        """Get the open position for a specific symbol (if any)."""
        with db_manager.get_session() as session:
            return session.query(Position).filter(
                Position.symbol == symbol,
                Position.status == "open"
            ).first()

    def get_closed_positions(
        self,
        symbol: str = None,
        limit: int = 100
    ) -> List[Position]:
        """Get closed positions."""
        with db_manager.get_session() as session:
            query = session.query(Position).filter(Position.status == "closed")
            if symbol:
                query = query.filter(Position.symbol == symbol)
            return query.order_by(desc(Position.exit_timestamp)).limit(limit).all()

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
    ) -> int:
        """Save a portfolio snapshot."""
        with db_manager.get_session() as session:
            snapshot = PortfolioSnapshot(
                timestamp=datetime.utcnow(),
                total_equity_usdc=total_equity,
                available_balance_usdc=available_balance,
                margin_used_usdc=margin_used,
                open_positions_count=open_positions_count,
                total_exposure_pct=exposure_pct,
                total_pnl_usdc=total_pnl,
                total_pnl_pct=total_pnl_pct,
                raw_portfolio=raw_data
            )
            session.add(snapshot)
            session.flush()
            return snapshot.id

    def get_portfolio_history(self, limit: int = 1000) -> List[PortfolioSnapshot]:
        """Get portfolio snapshot history."""
        with db_manager.get_session() as session:
            return session.query(PortfolioSnapshot).order_by(
                desc(PortfolioSnapshot.timestamp)
            ).limit(limit).all()

    def get_latest_portfolio(self) -> Optional[PortfolioSnapshot]:
        """Get the most recent portfolio snapshot."""
        with db_manager.get_session() as session:
            return session.query(PortfolioSnapshot).order_by(
                desc(PortfolioSnapshot.timestamp)
            ).first()

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
    ) -> int:
        """Save a news event."""
        with db_manager.get_session() as session:
            news = NewsEvent(
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
            session.add(news)
            session.flush()
            return news.id

    def get_recent_news(
        self,
        symbol: str = None,
        limit: int = 10
    ) -> List[NewsEvent]:
        """Get recent news events."""
        with db_manager.get_session() as session:
            query = session.query(NewsEvent)
            if symbol:
                query = query.filter(NewsEvent.symbols.contains([symbol]))
            return query.order_by(desc(NewsEvent.published_at)).limit(limit).all()

    # ============== Statistics ==============

    def get_trading_stats(self) -> Dict[str, Any]:
        """Get trading statistics."""
        with db_manager.get_session() as session:
            total_trades = session.query(TradeDecision).filter(
                TradeDecision.action.in_(["open", "close"])
            ).count()

            closed_positions = session.query(Position).filter(
                Position.status == "closed"
            ).all()

            if closed_positions:
                wins = sum(1 for p in closed_positions if float(p.realized_pnl or 0) > 0)
                total_pnl = sum(float(p.realized_pnl or 0) for p in closed_positions)
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


# Global operations instance
db_ops = DatabaseOperations()
