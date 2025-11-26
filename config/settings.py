"""
Configuration settings loaded from environment variables.
Uses Pydantic for validation and type safety.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    """Application settings with validation."""

    # Exchange - Hyperliquid
    HYPERLIQUID_API_KEY: str = Field(default="")
    HYPERLIQUID_SECRET: str = Field(default="")
    HYPERLIQUID_TESTNET: bool = Field(default=True)

    # Trading Parameters
    TARGET_SYMBOLS: str = Field(default="BTC,ETH,SOL")
    TIMEFRAME: str = Field(default="15m")
    MAX_LEVERAGE: int = Field(default=10)
    DEFAULT_LEVERAGE: int = Field(default=3)
    MAX_POSITION_SIZE_PCT: float = Field(default=5.0)
    MAX_TOTAL_EXPOSURE_PCT: float = Field(default=30.0)

    # LLM - DeepSeek
    DEEPSEEK_API_KEY: str = Field(default="")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com")
    MODEL_NAME: str = Field(default="deepseek-chat")
    LLM_TEMPERATURE: float = Field(default=0.3)
    LLM_MAX_TOKENS: int = Field(default=2000)

    # Database
    DATABASE_URL: str = Field(default="postgresql://user:password@localhost:5432/trading_agent")

    # External APIs
    COINMARKETCAP_API_KEY: str = Field(default="")
    NEWS_FEED_URL: str = Field(default="")
    WHALE_ALERT_API_KEY: str = Field(default="")

    # Risk Management
    ENABLE_STOP_LOSS: bool = Field(default=True)
    ENABLE_TAKE_PROFIT: bool = Field(default=True)
    STOP_LOSS_PCT: float = Field(default=3.0)
    TAKE_PROFIT_PCT: float = Field(default=5.0)
    MIN_CONFIDENCE_THRESHOLD: float = Field(default=0.6)

    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default="logs/trading_agent.log")

    # Dashboard
    DASHBOARD_PORT: int = Field(default=8501)
    DASHBOARD_HOST: str = Field(default="0.0.0.0")

    @property
    def symbols_list(self) -> List[str]:
        """Return target symbols as a list."""
        return [s.strip() for s in self.TARGET_SYMBOLS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
