"""
Advanced logging system with colored console output and file rotation.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from config.settings import settings


# ANSI color codes for console output
class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""

    LEVEL_COLORS = {
        logging.DEBUG: Colors.CYAN,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BOLD + Colors.RED,
    }

    def __init__(self, fmt: str = None, use_colors: bool = True):
        super().__init__(fmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors:
            color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)
            record.levelname = f"{color}{record.levelname}{Colors.RESET}"
            record.name = f"{Colors.BLUE}{record.name}{Colors.RESET}"
        return super().format(record)


def setup_logger(
    name: str = "trading_agent",
    log_file: Optional[str] = None,
    level: str = None
) -> logging.Logger:
    """
    Set up and configure the logger.

    Args:
        name: Logger name
        log_file: Path to log file (optional)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    level = level or settings.LOG_LEVEL
    log_file = log_file or settings.LOG_FILE

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    console_handler.setFormatter(ColoredFormatter(console_format, use_colors=True))
    logger.addHandler(console_handler)

    # File handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        file_handler.setFormatter(logging.Formatter(file_format))
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (defaults to trading_agent)

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"trading_agent.{name}")
    return setup_logger()


# Initialize the main logger
main_logger = setup_logger()


def log_trade_decision(
    symbol: str,
    action: str,
    direction: Optional[str],
    confidence: float,
    reasoning: str
) -> None:
    """Log a trading decision in a formatted way."""
    logger = get_logger("decisions")
    direction_str = direction.upper() if direction else "N/A"
    logger.info(
        f"\n{'='*50}\n"
        f"TRADE DECISION: {symbol}\n"
        f"Action: {action.upper()} | Direction: {direction_str}\n"
        f"Confidence: {confidence:.2%}\n"
        f"Reasoning: {reasoning[:200]}...\n"
        f"{'='*50}"
    )


def log_execution(
    symbol: str,
    action: str,
    price: float,
    quantity: float,
    order_id: str
) -> None:
    """Log a trade execution."""
    logger = get_logger("execution")
    logger.info(
        f"EXECUTED: {action.upper()} {symbol} @ ${price:.2f} "
        f"| Qty: {quantity:.6f} | Order ID: {order_id}"
    )


def log_portfolio_status(
    equity: float,
    available: float,
    exposure_pct: float,
    positions_count: int
) -> None:
    """Log portfolio status."""
    logger = get_logger("portfolio")
    logger.info(
        f"PORTFOLIO: Equity=${equity:.2f} | Available=${available:.2f} "
        f"| Exposure={exposure_pct:.1f}% | Positions={positions_count}"
    )


def log_error_with_context(
    error: Exception,
    context: str,
    additional_info: dict = None
) -> None:
    """Log an error with full context."""
    logger = get_logger("errors")
    info_str = ""
    if additional_info:
        info_str = " | ".join(f"{k}={v}" for k, v in additional_info.items())
    logger.error(
        f"ERROR in {context}: {type(error).__name__}: {str(error)}"
        f"{' | ' + info_str if info_str else ''}",
        exc_info=True
    )
