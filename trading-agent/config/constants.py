"""
System constants and configuration values.
"""

# Indicator Parameters
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9

RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

EMA_SHORT_PERIOD = 2
EMA_LONG_PERIOD = 20

VOLUME_SMA_PERIOD = 20

# Pivot Points thresholds
PIVOT_NEAR_RESISTANCE_THRESHOLD = 0.99  # price > R1 * 0.99
PIVOT_NEAR_SUPPORT_THRESHOLD = 1.01     # price < S1 * 1.01

# Prophet Forecasting
PROPHET_FORECAST_PERIODS = 16  # 4 hours with 15min timeframe
PROPHET_RETRAIN_CYCLES = 50
PROPHET_RETRAIN_HOURS = 1

# Forecast trend thresholds
FORECAST_BULLISH_THRESHOLD = 1.0   # +1% = bullish
FORECAST_BEARISH_THRESHOLD = -1.0  # -1% = bearish

# Order Book
ORDERBOOK_DEPTH = 10
ORDERBOOK_BUY_PRESSURE_THRESHOLD = 1.2
ORDERBOOK_SELL_PRESSURE_THRESHOLD = 0.8

# Sentiment mapping
SENTIMENT_FEAR_MAX = 25
SENTIMENT_NEUTRAL_MAX = 45
# Above 45 = GREED

# Cache durations (seconds)
CACHE_SENTIMENT_DURATION = 3600  # 1 hour
CACHE_NEWS_DURATION = 1800       # 30 minutes
CACHE_WHALE_DURATION = 900       # 15 minutes
CACHE_NEWS_ANALYSIS_TTL = 1800   # 30 minutes for analyzed news cache

# HTTP Timeouts (seconds) - unified across all modules
HTTP_TIMEOUT_RSS = 15.0          # RSS feed fetching
HTTP_TIMEOUT_SCRAPE = 20.0       # Article scraping
HTTP_TIMEOUT_DEEPSEEK = 45.0     # DeepSeek API calls
HTTP_TIMEOUT_DEFAULT = 30.0      # Default for other HTTP calls

# Rate limiting
DEEPSEEK_RATE_LIMIT_PER_MIN = 30  # Max DeepSeek API calls per minute
NEWS_ANALYSIS_MAX_WORKERS = 2     # Concurrent article analysis threads
NEWS_ANALYSIS_MAX_RETRIES = 2     # Max retries for failed API calls
NEWS_ANALYSIS_RETRY_DELAY = 2.0   # Base delay for exponential backoff

# OHLCV data
OHLCV_LIMIT = 200  # Number of candles to fetch

# Indicator weights for decision making
INDICATOR_WEIGHTS = {
    "pivot_points": 0.8,
    "macd": 0.7,
    "rsi": 0.7,
    "whale_flow": 0.65,
    "forecast": 0.6,
    "news": 0.55,          # AI-analyzed news (increased from 0.3)
    "coingecko": 0.5,
    "orderbook": 0.5,
    "sentiment": 0.4,
}

# Trading actions
ACTION_OPEN = "open"
ACTION_CLOSE = "close"
ACTION_HOLD = "hold"

# Position directions
DIRECTION_LONG = "long"
DIRECTION_SHORT = "short"

# Execution status
EXECUTION_PENDING = "pending"
EXECUTION_EXECUTED = "executed"
EXECUTION_FAILED = "failed"
EXECUTION_SKIPPED = "skipped"

# Position status
POSITION_OPEN = "open"
POSITION_CLOSED = "closed"

# Exit reasons
EXIT_TAKE_PROFIT = "take_profit"
EXIT_STOP_LOSS = "stop_loss"
EXIT_MANUAL = "manual"
EXIT_SIGNAL_REVERSAL = "signal_reversal"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # seconds, exponential backoff

# Minimum order requirements
MIN_ORDER_VALUE_USD = 10.0

# Exchange specific
HYPERLIQUID_SYMBOLS = {
    "BTC": "BTC/USDC:USDC",
    "ETH": "ETH/USDC:USDC",
    "SOL": "SOL/USDC:USDC",
}
