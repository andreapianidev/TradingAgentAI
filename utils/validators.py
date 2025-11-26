"""
Input validators for the trading agent.
"""
from typing import Any, Optional, Tuple
import re


def validate_symbol(symbol: str) -> Tuple[bool, str]:
    """
    Validate trading symbol.

    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_symbols = ["BTC", "ETH", "SOL"]

    if not symbol:
        return False, "Symbol cannot be empty"

    symbol_upper = symbol.upper()
    if symbol_upper not in valid_symbols:
        return False, f"Invalid symbol: {symbol}. Must be one of {valid_symbols}"

    return True, ""


def validate_direction(direction: str) -> Tuple[bool, str]:
    """Validate trade direction."""
    valid_directions = ["long", "short"]

    if not direction:
        return False, "Direction cannot be empty"

    if direction.lower() not in valid_directions:
        return False, f"Invalid direction: {direction}. Must be 'long' or 'short'"

    return True, ""


def validate_leverage(leverage: int, max_leverage: int = 10) -> Tuple[bool, str]:
    """Validate leverage value."""
    if not isinstance(leverage, (int, float)):
        return False, "Leverage must be a number"

    leverage = int(leverage)

    if leverage < 1:
        return False, "Leverage must be at least 1"

    if leverage > max_leverage:
        return False, f"Leverage cannot exceed {max_leverage}"

    return True, ""


def validate_position_size(
    size_pct: float,
    min_size: float = 1.0,
    max_size: float = 5.0
) -> Tuple[bool, str]:
    """Validate position size percentage."""
    if not isinstance(size_pct, (int, float)):
        return False, "Position size must be a number"

    if size_pct < min_size:
        return False, f"Position size must be at least {min_size}%"

    if size_pct > max_size:
        return False, f"Position size cannot exceed {max_size}%"

    return True, ""


def validate_confidence(confidence: float) -> Tuple[bool, str]:
    """Validate confidence value."""
    if not isinstance(confidence, (int, float)):
        return False, "Confidence must be a number"

    if confidence < 0 or confidence > 1:
        return False, "Confidence must be between 0 and 1"

    return True, ""


def validate_price(price: float) -> Tuple[bool, str]:
    """Validate price value."""
    if not isinstance(price, (int, float)):
        return False, "Price must be a number"

    if price <= 0:
        return False, "Price must be positive"

    return True, ""


def validate_quantity(quantity: float) -> Tuple[bool, str]:
    """Validate quantity value."""
    if not isinstance(quantity, (int, float)):
        return False, "Quantity must be a number"

    if quantity <= 0:
        return False, "Quantity must be positive"

    return True, ""


def validate_api_key(api_key: str) -> Tuple[bool, str]:
    """Validate API key format."""
    if not api_key:
        return False, "API key cannot be empty"

    if len(api_key) < 10:
        return False, "API key seems too short"

    return True, ""


def validate_database_url(url: str) -> Tuple[bool, str]:
    """Validate database URL format."""
    if not url:
        return False, "Database URL cannot be empty"

    if not url.startswith("postgresql://"):
        return False, "Database URL must start with 'postgresql://'"

    return True, ""


def validate_percentage(value: float, name: str = "Value") -> Tuple[bool, str]:
    """Validate percentage value (0-100)."""
    if not isinstance(value, (int, float)):
        return False, f"{name} must be a number"

    if value < 0 or value > 100:
        return False, f"{name} must be between 0 and 100"

    return True, ""


def sanitize_string(s: str, max_length: int = 1000) -> str:
    """Sanitize string input."""
    if not s:
        return ""

    # Remove control characters
    s = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', s)

    # Truncate
    return s[:max_length]
