"""
Utility helper functions.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
import json


def round_price(price: float, decimals: int = 2) -> float:
    """Round price to specified decimals."""
    return float(Decimal(str(price)).quantize(
        Decimal(10) ** -decimals,
        rounding=ROUND_DOWN
    ))


def round_quantity(quantity: float, decimals: int = 6) -> float:
    """Round quantity to specified decimals."""
    return float(Decimal(str(quantity)).quantize(
        Decimal(10) ** -decimals,
        rounding=ROUND_DOWN
    ))


def calculate_pnl(
    entry_price: float,
    exit_price: float,
    quantity: float,
    direction: str,
    leverage: int = 1
) -> Dict[str, float]:
    """
    Calculate profit/loss for a trade.

    Returns:
        Dictionary with pnl and pnl_pct
    """
    if direction == "long":
        pnl = (exit_price - entry_price) * quantity
        pnl_pct = ((exit_price / entry_price) - 1) * 100 * leverage
    else:  # short
        pnl = (entry_price - exit_price) * quantity
        pnl_pct = ((entry_price / exit_price) - 1) * 100 * leverage

    return {
        "pnl": round(pnl, 4),
        "pnl_pct": round(pnl_pct, 4)
    }


def format_currency(value: float, symbol: str = "$") -> str:
    """Format value as currency."""
    if abs(value) >= 1_000_000:
        return f"{symbol}{value/1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{symbol}{value/1_000:.2f}K"
    else:
        return f"{symbol}{value:.2f}"


def format_percentage(value: float) -> str:
    """Format value as percentage."""
    return f"{value:.2f}%"


def safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
    """Safely divide two numbers."""
    if denominator == 0:
        return default
    return numerator / denominator


def parse_json_safe(text: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON string."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def get_time_ago(timestamp: datetime) -> str:
    """Get human-readable time ago string."""
    now = datetime.utcnow()
    diff = now - timestamp

    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours}h ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes}m ago"
    else:
        return "just now"


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp value between min and max."""
    return max(min_value, min(max_value, value))


def merge_dicts(*dicts: Dict) -> Dict:
    """Merge multiple dictionaries."""
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def filter_none(d: Dict) -> Dict:
    """Remove None values from dictionary."""
    return {k: v for k, v in d.items() if v is not None}


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
