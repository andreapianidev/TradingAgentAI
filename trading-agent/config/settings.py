"""
Configuration settings loaded from Supabase with environment variables as fallback.
Uses Pydantic for validation and type safety.

Priority order:
1. Supabase trading_settings table (primary source for runtime config)
2. Environment variables (fallback, used for secrets like API keys)
3. Default values
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os
import logging

logger = logging.getLogger(__name__)


def _load_supabase_overrides() -> dict:
    """
    Load settings from Supabase and return as environment variable overrides.
    This is called before Settings class is instantiated.
    """
    try:
        from config.supabase_settings import get_env_overrides
        overrides = get_env_overrides()

        if overrides:
            logger.info(f"Loaded {len(overrides)} settings from Supabase")
            # Set as environment variables so Pydantic picks them up
            for key, value in overrides.items():
                if key not in os.environ or os.getenv(f'FORCE_ENV_{key}') is None:
                    os.environ[key] = value
        return overrides

    except ImportError as e:
        logger.debug(f"Supabase settings module not available: {e}")
        return {}
    except Exception as e:
        logger.warning(f"Failed to load Supabase settings, using env vars: {e}")
        return {}


# Load Supabase overrides before Settings class is instantiated
_supabase_overrides = _load_supabase_overrides()


class Settings(BaseSettings):
    """Application settings with validation."""

    # ============ EXCHANGE SELECTION ============
    # Choose which exchange to use: "hyperliquid" or "alpaca"
    EXCHANGE: str = Field(default="alpaca")

    # ============ EXCHANGE - HYPERLIQUID ============
    # These are ALWAYS loaded from environment variables (secrets)
    HYPERLIQUID_API_KEY: str = Field(default="")
    HYPERLIQUID_SECRET: str = Field(default="")
    HYPERLIQUID_TESTNET: bool = Field(default=True)

    # ============ EXCHANGE - ALPACA ============
    # Get your API keys from https://alpaca.markets (Paper Trading)
    ALPACA_API_KEY: str = Field(default="")
    ALPACA_SECRET_KEY: str = Field(default="")
    ALPACA_PAPER_TRADING: bool = Field(default=True)
    ALPACA_BASE_URL: str = Field(default="https://paper-api.alpaca.markets")

    # ============ TRADING PARAMETERS ============
    # These can be overridden from Supabase
    TARGET_SYMBOLS: str = Field(default="BTC,ETH,SOL")
    TIMEFRAME: str = Field(default="15m")
    # NOTE: Alpaca crypto does NOT support leverage. These are kept for compatibility
    # but are always forced to 1 in the DecisionValidator when using Alpaca.
    MAX_LEVERAGE: int = Field(default=1)  # Always 1 for Alpaca crypto
    DEFAULT_LEVERAGE: int = Field(default=1)  # Always 1 for Alpaca crypto
    MAX_POSITION_SIZE_PCT: float = Field(default=5.0)
    MAX_TOTAL_EXPOSURE_PCT: float = Field(default=30.0)

    # ============ LLM - DEEPSEEK ============
    # These are ALWAYS loaded from environment variables (secrets)
    DEEPSEEK_API_KEY: str = Field(default="")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com")
    MODEL_NAME: str = Field(default="deepseek-chat")
    LLM_TEMPERATURE: float = Field(default=0.3)
    LLM_MAX_TOKENS: int = Field(default=2000)

    # ============ LLM - DEEPSEEK NEWS ANALYZER ============
    # Separate API key for news analysis (keeps costs isolated)
    DEEPSEEK_NEWS_API_KEY: str = Field(default="")

    # ============ DATABASE ============
    # Primary database URL (legacy) - still used for SQLAlchemy migrations
    DATABASE_URL: str = Field(default="postgresql://user:password@localhost:5432/trading_agent")

    # Supabase credentials for trading_settings table
    SUPABASE_URL: str = Field(default="")
    SUPABASE_SERVICE_KEY: str = Field(default="")

    # ============ EXTERNAL APIs ============
    COINMARKETCAP_API_KEY: str = Field(default="")
    NEWS_FEED_URL: str = Field(default="")
    WHALE_ALERT_API_KEY: str = Field(default="")

    # ============ NEWS CONFIGURATION ============
    # Comma-separated list of RSS feed URLs
    NEWS_RSS_FEEDS: str = Field(
        default="https://cointelegraph.com/rss,https://bitcoinmagazine.com/.rss/full/,https://www.coindesk.com/arc/outboundfeeds/rss/,https://decrypt.co/feed,https://bitcoinist.com/feed/,https://www.newsbtc.com/feed/"
    )
    NEWS_MAX_ARTICLES_PER_FEED: int = Field(default=20)
    NEWS_MAX_ARTICLES_TO_ANALYZE: int = Field(default=20)
    NEWS_MAX_AGE_HOURS: int = Field(default=4)

    # ============ PAPER TRADING MODE ============
    # Can be controlled from Supabase dashboard
    PAPER_TRADING: bool = Field(default=True)
    PAPER_TRADING_INITIAL_BALANCE: float = Field(default=10000.0)

    # ============ BOT CONTROL ============
    # Controlled from Supabase dashboard
    BOT_ACTIVE: bool = Field(default=True)

    # ============ RISK MANAGEMENT ============
    # Can be controlled from Supabase dashboard
    ENABLE_STOP_LOSS: bool = Field(default=True)
    ENABLE_TAKE_PROFIT: bool = Field(default=True)
    STOP_LOSS_PCT: float = Field(default=3.0)
    TAKE_PROFIT_PCT: float = Field(default=5.0)
    MIN_CONFIDENCE_THRESHOLD: float = Field(default=0.6)

    # ============ TRADING STRATEGY (Dynamic from DB) ============
    # These are loaded from trading_strategies table and override the above
    STRATEGY_NAME: Optional[str] = Field(default=None)
    STRATEGY_CONFIG: Optional[dict] = Field(default=None)
    TP_RANGE_MIN: float = Field(default=5.0)
    TP_RANGE_MAX: float = Field(default=8.0)
    SL_RANGE_MIN: float = Field(default=2.0)
    SL_RANGE_MAX: float = Field(default=4.0)
    AUTO_CLOSE_AT_PROFIT_PCT: Optional[float] = Field(default=None)

    # ============ LOGGING ============
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default="logs/trading_agent.log")

    # ============ DASHBOARD ============
    DASHBOARD_PORT: int = Field(default=8501)
    DASHBOARD_HOST: str = Field(default="0.0.0.0")

    @property
    def symbols_list(self) -> List[str]:
        """Return target symbols as a list."""
        return [s.strip() for s in self.TARGET_SYMBOLS.split(",")]

    @property
    def rss_feeds_list(self) -> List[str]:
        """Return RSS feeds as a list."""
        return [f.strip() for f in self.NEWS_RSS_FEEDS.split(",") if f.strip()]

    @property
    def is_using_supabase(self) -> bool:
        """Check if settings were loaded from Supabase."""
        return bool(_supabase_overrides)

    def refresh_from_supabase(self) -> 'Settings':
        """
        Refresh settings from Supabase.
        Returns a new Settings instance with updated values.
        """
        global _supabase_overrides
        try:
            from config.supabase_settings import supabase_settings
            supabase_settings.refresh()
            _supabase_overrides = _load_supabase_overrides()
            return Settings()
        except Exception as e:
            logger.error(f"Failed to refresh settings from Supabase: {e}")
            return self

    def get_settings_source(self) -> dict:
        """Return info about where each setting was loaded from."""
        sources = {}
        for key in _supabase_overrides:
            sources[key] = 'supabase'
        return sources

    def load_strategy_from_db(self):
        """Load active strategy from Supabase and override settings."""
        try:
            # Import here to avoid circular dependency
            from database.supabase_operations import db_ops

            strategy = db_ops.get_active_strategy()
            if not strategy:
                logger.warning("No strategy in DB, using hardcoded defaults")
                return

            config = strategy.get("config", {})
            self.STRATEGY_NAME = strategy.get("name")
            self.STRATEGY_CONFIG = config

            # Override settings with strategy config
            self.MAX_POSITION_SIZE_PCT = config.get("max_position_size_pct", 2.5)
            self.MAX_TOTAL_EXPOSURE_PCT = config.get("max_total_exposure_pct", 40.0)
            self.MIN_CONFIDENCE_THRESHOLD = config.get("min_confidence", 0.60)

            # Store TP/SL ranges for LLM prompt
            self.TP_RANGE_MIN = config.get("tp_range_min", 3.0)
            self.TP_RANGE_MAX = config.get("tp_range_max", 6.0)
            self.AUTO_CLOSE_AT_PROFIT_PCT = config.get("auto_close_at_profit_pct")
            self.SL_RANGE_MIN = config.get("sl_range_min", 1.5)
            self.SL_RANGE_MAX = config.get("sl_range_max", 3.0)

            logger.info(f"✓ Loaded strategy '{self.STRATEGY_NAME}' from database")
            logger.info(f"  Position size: {self.MAX_POSITION_SIZE_PCT}%")
            logger.info(f"  Max exposure: {self.MAX_TOTAL_EXPOSURE_PCT}%")
            logger.info(f"  TP range: {self.TP_RANGE_MIN}-{self.TP_RANGE_MAX}%")
            if self.AUTO_CLOSE_AT_PROFIT_PCT:
                logger.info(f"  Auto-close at: {self.AUTO_CLOSE_AT_PROFIT_PCT}%")

        except Exception as e:
            logger.warning(f"Failed to load strategy from DB, using defaults: {e}")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Allow extra fields for flexibility
        extra = "ignore"


# Global settings instance
settings = Settings()

# Load active trading strategy from database
settings.load_strategy_from_db()

# Log settings source on module load
if _supabase_overrides:
    logger.info(f"Settings loaded from Supabase: {list(_supabase_overrides.keys())}")
else:
    logger.info("All settings loaded from environment variables")
