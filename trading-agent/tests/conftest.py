"""
Pytest configuration and shared fixtures.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# ============================================================================
# Settings Mock
# ============================================================================

@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings for all tests."""
    with patch('config.settings.settings') as mock:
        mock.MAX_LEVERAGE = 10
        mock.MAX_POSITION_SIZE_PCT = 5.0
        mock.MAX_TOTAL_EXPOSURE_PCT = 30.0
        mock.STOP_LOSS_PCT = 3.0
        mock.TAKE_PROFIT_PCT = 5.0
        mock.MIN_CONFIDENCE_THRESHOLD = 0.6
        mock.PAPER_TRADING = True
        yield mock


# ============================================================================
# Database Mocks
# ============================================================================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    mock = MagicMock()
    mock.table.return_value.select.return_value.execute.return_value.data = []
    mock.table.return_value.insert.return_value.execute.return_value.data = [{"id": "test-id"}]
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
    return mock


# ============================================================================
# Exchange Client Mocks
# ============================================================================

@pytest.fixture
def mock_exchange_client():
    """Mock exchange client for testing."""
    mock = AsyncMock()
    mock.connect.return_value = True
    mock.fetch_ticker.return_value = {
        'symbol': 'BTC/USDC',
        'last': 50000.0,
        'bid': 49990.0,
        'ask': 50010.0,
        'high': 51000.0,
        'low': 49000.0,
        'volume': 1000000.0,
        'change_24h': 2.5
    }
    mock.fetch_portfolio.return_value = {
        'equity': 10000.0,
        'available': 8000.0,
        'margin_used': 2000.0,
        'positions': []
    }
    mock.fetch_order_book.return_value = {
        'bids': [[49990, 10], [49980, 20]],
        'asks': [[50010, 10], [50020, 20]]
    }
    return mock


# ============================================================================
# OHLCV Test Data
# ============================================================================

@pytest.fixture
def sample_ohlcv_data():
    """
    Generate sample OHLCV data for indicator tests.
    200 candles at 15-minute intervals.
    """
    base_time = int(datetime(2024, 1, 1).timestamp() * 1000)
    interval = 15 * 60 * 1000  # 15 minutes in milliseconds

    data = []
    price = 50000.0

    for i in range(200):
        # Simulate some price movement
        change = np.random.uniform(-0.5, 0.5)
        price = price * (1 + change / 100)

        open_price = price
        high_price = price * (1 + np.random.uniform(0, 0.3) / 100)
        low_price = price * (1 - np.random.uniform(0, 0.3) / 100)
        close_price = price * (1 + np.random.uniform(-0.2, 0.2) / 100)
        volume = np.random.uniform(100000, 500000)

        data.append([
            base_time + (i * interval),
            open_price,
            high_price,
            low_price,
            close_price,
            volume
        ])

    return data


@pytest.fixture
def sample_ohlcv_bullish():
    """Generate bullish trending OHLCV data (prices going up)."""
    base_time = int(datetime(2024, 1, 1).timestamp() * 1000)
    interval = 15 * 60 * 1000

    data = []
    price = 50000.0

    for i in range(200):
        # Upward trend
        price = price * 1.002  # 0.2% increase per candle

        open_price = price * 0.999
        high_price = price * 1.003
        low_price = price * 0.998
        close_price = price
        volume = np.random.uniform(100000, 500000)

        data.append([
            base_time + (i * interval),
            open_price,
            high_price,
            low_price,
            close_price,
            volume
        ])

    return data


@pytest.fixture
def sample_ohlcv_bearish():
    """Generate bearish trending OHLCV data (prices going down)."""
    base_time = int(datetime(2024, 1, 1).timestamp() * 1000)
    interval = 15 * 60 * 1000

    data = []
    price = 50000.0

    for i in range(200):
        # Downward trend
        price = price * 0.998  # 0.2% decrease per candle

        open_price = price * 1.001
        high_price = price * 1.002
        low_price = price * 0.997
        close_price = price
        volume = np.random.uniform(100000, 500000)

        data.append([
            base_time + (i * interval),
            open_price,
            high_price,
            low_price,
            close_price,
            volume
        ])

    return data


@pytest.fixture
def sample_ohlcv_sideways():
    """Generate sideways/ranging OHLCV data."""
    base_time = int(datetime(2024, 1, 1).timestamp() * 1000)
    interval = 15 * 60 * 1000

    data = []
    base_price = 50000.0

    for i in range(200):
        # Oscillate around base price
        variation = np.sin(i / 10) * 500  # +/- 500 around base
        price = base_price + variation

        open_price = price * (1 + np.random.uniform(-0.1, 0.1) / 100)
        high_price = price * 1.002
        low_price = price * 0.998
        close_price = price * (1 + np.random.uniform(-0.1, 0.1) / 100)
        volume = np.random.uniform(100000, 500000)

        data.append([
            base_time + (i * interval),
            open_price,
            high_price,
            low_price,
            close_price,
            volume
        ])

    return data


# ============================================================================
# Portfolio & Position Fixtures
# ============================================================================

@pytest.fixture
def sample_portfolio():
    """Sample portfolio data."""
    return {
        'equity': 10000.0,
        'available': 8000.0,
        'margin_used': 2000.0,
        'open_positions_count': 1,
        'total_exposure_pct': 20.0
    }


@pytest.fixture
def sample_open_position():
    """Sample open position."""
    return {
        'symbol': 'BTC/USDC',
        'direction': 'long',
        'entry_price': 50000.0,
        'quantity': 0.1,
        'leverage': 5,
        'stop_loss_price': 48500.0,
        'take_profit_price': 52500.0,
        'unrealized_pnl': 100.0
    }


# ============================================================================
# Trading Decision Fixtures
# ============================================================================

@pytest.fixture
def sample_decision():
    """Sample trading decision."""
    return {
        'action': 'open',
        'direction': 'long',
        'leverage': 5,
        'position_size_pct': 3.0,
        'stop_loss_pct': 3.0,
        'take_profit_pct': 5.0,
        'confidence': 0.75,
        'reasoning': 'Test decision'
    }


# ============================================================================
# Market Context Fixtures
# ============================================================================

@pytest.fixture
def sample_indicators():
    """Sample technical indicators."""
    return {
        'macd': 150.0,
        'macd_signal': 120.0,
        'macd_histogram': 30.0,
        'rsi': 55.0,
        'ema2': 50100.0,
        'ema20': 49800.0,
        'price': 50000.0,
        'macd_bullish': True,
        'rsi_overbought': False,
        'rsi_oversold': False,
        'price_above_ema20': True
    }


@pytest.fixture
def sample_forecast():
    """Sample Prophet forecast."""
    return {
        'trend': 'RIALZISTA',
        'target_price': 52000.0,
        'confidence': 0.72,
        'change_pct': 4.0
    }


@pytest.fixture
def sample_sentiment():
    """Sample market sentiment."""
    return {
        'label': 'NEUTRAL',
        'score': 50,
        'interpretation': 'Mercato equilibrato'
    }
