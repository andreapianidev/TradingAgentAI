"""
Advanced logging system with colored console output, file rotation, and Supabase logging.
"""
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Any

from config.settings import settings


# Global cycle ID - set when bot starts
_current_cycle_id: Optional[str] = None


def set_cycle_id(cycle_id: str) -> None:
    """Set the current trading cycle ID for log correlation."""
    global _current_cycle_id
    _current_cycle_id = cycle_id


def get_cycle_id() -> Optional[str]:
    """Get the current trading cycle ID."""
    return _current_cycle_id or os.environ.get("CYCLE_ID")


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


class SupabaseHandler(logging.Handler):
    """Custom logging handler that sends logs to Supabase."""

    def __init__(self, level=logging.INFO):
        super().__init__(level)
        self._client = None
        self._init_failed = False

    def _get_client(self):
        """Lazy load Supabase client."""
        if self._init_failed:
            return None

        if self._client is None:
            try:
                from supabase import create_client
                url = settings.SUPABASE_URL
                key = settings.SUPABASE_SERVICE_KEY
                if url and key:
                    self._client = create_client(url, key)
            except Exception:
                self._init_failed = True
                return None
        return self._client

    def emit(self, record: logging.LogRecord):
        """Send log record to Supabase."""
        client = self._get_client()
        if not client:
            return

        try:
            # Extract component name from logger name
            # Strip ANSI codes that may have been added by ColoredFormatter
            import re
            ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
            raw_name = ansi_escape.sub('', record.name) if record.name else "main"
            component = raw_name.replace("trading_agent.", "")
            component = component[:50] if len(component) > 50 else component

            # Use levelno to get clean level name (avoids ANSI codes from ColoredFormatter)
            level_names = {10: 'DEBUG', 20: 'INFO', 30: 'WARNING', 40: 'ERROR', 50: 'CRITICAL'}
            log_level = level_names.get(record.levelno, 'INFO')

            # Build log data
            log_data = {
                "log_level": log_level,
                "message": record.getMessage(),
                "component": component,
                "cycle_id": get_cycle_id(),
                "trading_mode": "paper" if settings.PAPER_TRADING else "live"
            }

            # Add extra fields if present
            if hasattr(record, 'symbol'):
                log_data["symbol"] = record.symbol
            if hasattr(record, 'details'):
                log_data["details"] = record.details

            # Add exception info if present
            if record.exc_info:
                import traceback
                log_data["error_stack"] = "".join(traceback.format_exception(*record.exc_info))

            # Insert log into Supabase (fire and forget)
            client.table("trading_bot_logs").insert(log_data).execute()

        except Exception:
            # Don't let logging failures break the bot
            pass


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

    # Supabase handler for real-time logs in dashboard
    supabase_handler = SupabaseHandler(level=logging.INFO)
    logger.addHandler(supabase_handler)

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

    # Convert reasoning to string if it's not already (handles dict, list, etc.)
    if not isinstance(reasoning, str):
        reasoning_str = str(reasoning)
    else:
        reasoning_str = reasoning

    # Truncate reasoning to 200 characters
    reasoning_preview = reasoning_str[:200] + "..." if len(reasoning_str) > 200 else reasoning_str

    logger.info(
        f"\n{'='*50}\n"
        f"TRADE DECISION: {symbol}\n"
        f"Action: {action.upper()} | Direction: {direction_str}\n"
        f"Confidence: {confidence:.2%}\n"
        f"Reasoning: {reasoning_preview}\n"
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


def log_with_details(
    message: str,
    level: str = "INFO",
    component: str = None,
    symbol: str = None,
    details: Dict[str, Any] = None
) -> None:
    """
    Log a message with additional details that will be stored in Supabase.

    Args:
        message: Log message
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        component: Component name
        symbol: Trading symbol (optional)
        details: Additional JSON details (optional)
    """
    logger = get_logger(component or "main")

    # Create a LogRecord with extra attributes
    record = logger.makeRecord(
        name=logger.name,
        level=getattr(logging, level.upper(), logging.INFO),
        fn="",
        lno=0,
        msg=message,
        args=(),
        exc_info=None
    )

    # Add extra attributes
    if symbol:
        record.symbol = symbol
    if details:
        record.details = details

    # Handle the record
    logger.handle(record)


def log_llm_request(
    symbol: str,
    system_prompt: str,
    user_prompt: str
) -> None:
    """Log an LLM request with full prompt details."""
    log_with_details(
        message=f"Sending LLM request for {symbol}",
        level="INFO",
        component="llm",
        symbol=symbol,
        details={
            "type": "llm_request",
            "system_prompt_preview": system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt,
            "user_prompt_preview": user_prompt[:1000] + "..." if len(user_prompt) > 1000 else user_prompt,
            "system_prompt_length": len(system_prompt),
            "user_prompt_length": len(user_prompt)
        }
    )


def log_llm_response(
    symbol: str,
    response: str,
    decision: Dict[str, Any] = None
) -> None:
    """Log an LLM response with full details."""
    # Safe extraction of action
    action_str = 'parse_error'
    if decision and isinstance(decision, dict):
        action_str = decision.get('action', 'N/A')

    # Safe extraction of response preview
    response_preview = None
    if response:
        try:
            response_preview = str(response)[:2000] if response else None
        except:
            response_preview = "[non-serializable response]"

    log_with_details(
        message=f"Received LLM response for {symbol}: {action_str}",
        level="INFO",
        component="llm",
        symbol=symbol,
        details={
            "type": "llm_response",
            "raw_response": response_preview,
            "action": action_str,
            "has_decision": decision is not None
        }
    )
