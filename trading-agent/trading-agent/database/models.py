"""
SQLAlchemy database models for the trading agent.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, ForeignKey, ARRAY, Index, Numeric
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class MarketContext(Base):
    """Store market context data for each analysis cycle."""
    __tablename__ = "market_contexts"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    price = Column(Numeric(20, 8), nullable=False)

    # Technical indicators
    macd = Column(Numeric(20, 8))
    macd_signal = Column(Numeric(20, 8))
    macd_histogram = Column(Numeric(20, 8))
    rsi = Column(Numeric(10, 4))
    ema20 = Column(Numeric(20, 8))
    ema2 = Column(Numeric(20, 8))

    # Pivot Points
    pivot_pp = Column(Numeric(20, 8))
    pivot_r1 = Column(Numeric(20, 8))
    pivot_r2 = Column(Numeric(20, 8))
    pivot_s1 = Column(Numeric(20, 8))
    pivot_s2 = Column(Numeric(20, 8))
    pivot_distance_pct = Column(Numeric(10, 4))

    # Forecast
    forecast_trend = Column(String(20))
    forecast_target_price = Column(Numeric(20, 8))
    forecast_change_pct = Column(Numeric(10, 4))
    forecast_confidence = Column(Numeric(5, 4))

    # Order Book
    orderbook_bid_volume = Column(Numeric(20, 8))
    orderbook_ask_volume = Column(Numeric(20, 8))
    orderbook_ratio = Column(Numeric(10, 4))

    # Sentiment
    sentiment_label = Column(String(20))
    sentiment_score = Column(Integer)

    # Raw JSON data
    raw_data = Column(JSONB)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    trade_decisions = relationship("TradeDecision", back_populates="context")

    __table_args__ = (
        Index('idx_market_contexts_symbol_timestamp', 'symbol', timestamp.desc()),
    )


class TradeDecision(Base):
    """Store LLM trading decisions."""
    __tablename__ = "trade_decisions"

    id = Column(Integer, primary_key=True)
    context_id = Column(Integer, ForeignKey("market_contexts.id"))
    symbol = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    # LLM Decision
    action = Column(String(10), nullable=False)  # open, close, hold
    direction = Column(String(10))  # long, short, null
    leverage = Column(Integer)
    position_size_pct = Column(Numeric(10, 4))
    stop_loss_pct = Column(Numeric(10, 4))
    take_profit_pct = Column(Numeric(10, 4))
    confidence = Column(Numeric(5, 4))
    reasoning = Column(Text)

    # Execution
    execution_status = Column(String(20))  # pending, executed, failed, skipped
    execution_details = Column(JSONB)
    execution_timestamp = Column(DateTime)

    # Entry details
    entry_price = Column(Numeric(20, 8))
    entry_quantity = Column(Numeric(20, 8))
    order_id = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    context = relationship("MarketContext", back_populates="trade_decisions")
    entry_position = relationship(
        "Position",
        foreign_keys="Position.entry_trade_id",
        back_populates="entry_trade"
    )
    exit_position = relationship(
        "Position",
        foreign_keys="Position.exit_trade_id",
        back_populates="exit_trade"
    )

    __table_args__ = (
        Index('idx_trade_decisions_symbol_timestamp', 'symbol', timestamp.desc()),
    )


class Position(Base):
    """Track open and closed positions."""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    direction = Column(String(10), nullable=False)

    # Entry
    entry_timestamp = Column(DateTime, nullable=False)
    entry_price = Column(Numeric(20, 8), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    leverage = Column(Integer, nullable=False)
    entry_trade_id = Column(Integer, ForeignKey("trade_decisions.id"))

    # Exit
    exit_timestamp = Column(DateTime)
    exit_price = Column(Numeric(20, 8))
    exit_reason = Column(String(50))  # take_profit, stop_loss, manual, signal_reversal
    exit_trade_id = Column(Integer, ForeignKey("trade_decisions.id"))

    # P&L
    realized_pnl = Column(Numeric(20, 8))
    realized_pnl_pct = Column(Numeric(10, 4))

    # Status
    status = Column(String(20), default="open")  # open, closed

    # Stop Loss & Take Profit
    stop_loss_price = Column(Numeric(20, 8))
    take_profit_price = Column(Numeric(20, 8))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    entry_trade = relationship(
        "TradeDecision",
        foreign_keys=[entry_trade_id],
        back_populates="entry_position"
    )
    exit_trade = relationship(
        "TradeDecision",
        foreign_keys=[exit_trade_id],
        back_populates="exit_position"
    )

    __table_args__ = (
        Index('idx_positions_symbol_status', 'symbol', 'status'),
    )


class PortfolioSnapshot(Base):
    """Periodic snapshots of portfolio state."""
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)

    # Balances
    total_equity_usdc = Column(Numeric(20, 8), nullable=False)
    available_balance_usdc = Column(Numeric(20, 8), nullable=False)
    margin_used_usdc = Column(Numeric(20, 8))

    # Positions summary
    open_positions_count = Column(Integer)
    total_exposure_pct = Column(Numeric(10, 4))

    # Performance
    total_pnl_usdc = Column(Numeric(20, 8))
    total_pnl_pct = Column(Numeric(10, 4))

    # Raw data
    raw_portfolio = Column(JSONB)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_portfolio_snapshots_timestamp', timestamp.desc()),
    )


class NewsEvent(Base):
    """Store news events and sentiment."""
    __tablename__ = "news_events"

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    source = Column(String(100))
    url = Column(Text)
    published_at = Column(DateTime)
    sentiment = Column(String(20))  # positive, negative, neutral
    relevance_score = Column(Numeric(5, 4))
    symbols = Column(ARRAY(String))  # Array of relevant symbols
    raw_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_news_events_published', published_at.desc()),
    )
