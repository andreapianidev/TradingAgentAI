"""
Risk management and position sizing.
"""
from typing import Dict, Any, Optional, Tuple

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class RiskManager:
    """Manages risk limits and position sizing."""

    def __init__(self):
        """Initialize risk manager with settings."""
        self.max_leverage = settings.MAX_LEVERAGE
        self.max_position_size_pct = settings.MAX_POSITION_SIZE_PCT
        self.max_total_exposure_pct = settings.MAX_TOTAL_EXPOSURE_PCT
        self.default_stop_loss_pct = settings.STOP_LOSS_PCT
        self.default_take_profit_pct = settings.TAKE_PROFIT_PCT
        self.min_confidence = settings.MIN_CONFIDENCE_THRESHOLD

    def check_leverage(self, leverage: int) -> bool:
        """
        Check if leverage is within limits.

        Args:
            leverage: Proposed leverage

        Returns:
            True if leverage is valid
        """
        return 1 <= leverage <= self.max_leverage

    def check_position_size(
        self,
        size_pct: float,
        available_balance: float
    ) -> bool:
        """
        Check if position size is valid.

        Args:
            size_pct: Position size as percentage
            available_balance: Available balance in USDC

        Returns:
            True if size is valid
        """
        if size_pct <= 0 or size_pct > self.max_position_size_pct:
            return False

        # Check minimum order value
        position_value = available_balance * (size_pct / 100)
        min_order_value = 10.0  # $10 minimum

        return position_value >= min_order_value

    def check_total_exposure(
        self,
        new_position_pct: float,
        current_exposure_pct: float
    ) -> bool:
        """
        Check if new position would exceed exposure limits.

        Args:
            new_position_pct: New position size percentage
            current_exposure_pct: Current total exposure

        Returns:
            True if within limits
        """
        new_total = current_exposure_pct + new_position_pct
        return new_total <= self.max_total_exposure_pct

    def check_confidence(self, confidence: float) -> bool:
        """
        Check if confidence meets threshold.

        Args:
            confidence: Decision confidence (0-1)

        Returns:
            True if confidence is sufficient
        """
        return confidence >= self.min_confidence

    def calculate_stop_loss_price(
        self,
        entry_price: float,
        direction: str,
        stop_loss_pct: float = None
    ) -> float:
        """
        Calculate stop loss price.

        Args:
            entry_price: Entry price
            direction: Position direction (long/short)
            stop_loss_pct: Stop loss percentage (defaults to settings)

        Returns:
            Stop loss price
        """
        sl_pct = stop_loss_pct or self.default_stop_loss_pct

        if direction == "long":
            return entry_price * (1 - sl_pct / 100)
        else:  # short
            return entry_price * (1 + sl_pct / 100)

    def calculate_take_profit_price(
        self,
        entry_price: float,
        direction: str,
        take_profit_pct: float = None
    ) -> float:
        """
        Calculate take profit price.

        Args:
            entry_price: Entry price
            direction: Position direction (long/short)
            take_profit_pct: Take profit percentage (defaults to settings)

        Returns:
            Take profit price
        """
        tp_pct = take_profit_pct or self.default_take_profit_pct

        if direction == "long":
            return entry_price * (1 + tp_pct / 100)
        else:  # short
            return entry_price * (1 - tp_pct / 100)

    def calculate_position_size(
        self,
        available_balance: float,
        confidence: float,
        max_size_pct: float = None
    ) -> float:
        """
        Calculate optimal position size based on confidence.

        Higher confidence = larger position

        Args:
            available_balance: Available balance
            confidence: Decision confidence (0-1)
            max_size_pct: Maximum size percentage

        Returns:
            Position size percentage
        """
        max_pct = max_size_pct or self.max_position_size_pct

        # Scale size with confidence
        # confidence 0.6 -> ~1.5%
        # confidence 0.7 -> ~2.5%
        # confidence 0.8 -> ~3.5%
        # confidence 0.9 -> ~4.5%
        # confidence 1.0 -> 5%

        base_size = 1.0
        confidence_multiplier = (confidence - 0.5) * 8  # 0.5->0, 1.0->4

        size_pct = base_size + confidence_multiplier
        size_pct = max(1.0, min(max_pct, size_pct))

        return round(size_pct, 1)

    def calculate_leverage(
        self,
        confidence: float,
        max_leverage: int = None
    ) -> int:
        """
        Calculate optimal leverage based on confidence.

        Higher confidence = higher leverage (within limits)

        Args:
            confidence: Decision confidence (0-1)
            max_leverage: Maximum leverage

        Returns:
            Recommended leverage
        """
        max_lev = max_leverage or self.max_leverage

        # Leverage scaling:
        # confidence 0.6-0.7 -> 1-3x
        # confidence 0.7-0.85 -> 4-6x
        # confidence 0.85-1.0 -> 7-10x

        if confidence >= 0.85:
            leverage = min(max_lev, 7 + int((confidence - 0.85) * 20))
        elif confidence >= 0.7:
            leverage = 4 + int((confidence - 0.7) * 13)
        else:
            leverage = 1 + int((confidence - 0.6) * 20)

        return max(1, min(max_lev, leverage))

    def get_risk_adjusted_params(
        self,
        confidence: float,
        current_exposure: float,
        volatility: str = "normal"
    ) -> Dict[str, Any]:
        """
        Get risk-adjusted trading parameters.

        Args:
            confidence: Decision confidence
            current_exposure: Current portfolio exposure
            volatility: Market volatility (low/normal/high)

        Returns:
            Dictionary with adjusted parameters
        """
        # Base parameters
        leverage = self.calculate_leverage(confidence)
        size_pct = self.calculate_position_size(100, confidence)  # Dummy balance
        stop_loss = self.default_stop_loss_pct
        take_profit = self.default_take_profit_pct

        # Adjust for exposure
        if current_exposure > 25:
            leverage = min(leverage, 5)
            size_pct = min(size_pct, 2.0)

        if current_exposure > 20:
            leverage = min(leverage, 7)

        # Adjust for volatility
        if volatility == "high":
            stop_loss = 2.0  # Tighter stop loss
            take_profit = 7.0  # Larger take profit
            leverage = max(1, leverage - 2)
        elif volatility == "low":
            stop_loss = 4.0  # Wider stop loss
            take_profit = 4.0  # Smaller take profit

        return {
            "leverage": leverage,
            "position_size_pct": size_pct,
            "stop_loss_pct": stop_loss,
            "take_profit_pct": take_profit,
        }

    def validate_trade(
        self,
        leverage: int,
        size_pct: float,
        confidence: float,
        current_exposure: float,
        available_balance: float
    ) -> Tuple[bool, str]:
        """
        Validate all trade parameters.

        Args:
            leverage: Proposed leverage
            size_pct: Proposed position size
            confidence: Decision confidence
            current_exposure: Current exposure
            available_balance: Available balance

        Returns:
            Tuple of (is_valid, reason)
        """
        # Check leverage
        if not self.check_leverage(leverage):
            return False, f"Leverage {leverage} exceeds max {self.max_leverage}"

        # Check position size
        if not self.check_position_size(size_pct, available_balance):
            return False, f"Invalid position size: {size_pct}%"

        # Check exposure
        if not self.check_total_exposure(size_pct, current_exposure):
            return False, f"Would exceed max exposure {self.max_total_exposure_pct}%"

        # Check confidence
        if not self.check_confidence(confidence):
            return False, f"Confidence {confidence:.2f} below threshold {self.min_confidence}"

        return True, "All validations passed"

    def should_close_position(
        self,
        current_price: float,
        entry_price: float,
        direction: str,
        stop_loss_price: float,
        take_profit_price: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if position should be closed based on SL/TP.

        Args:
            current_price: Current price
            entry_price: Entry price
            direction: Position direction
            stop_loss_price: Stop loss price
            take_profit_price: Take profit price

        Returns:
            Tuple of (should_close, reason)
        """
        if direction == "long":
            if current_price <= stop_loss_price:
                return True, "stop_loss"
            if current_price >= take_profit_price:
                return True, "take_profit"
        else:  # short
            if current_price >= stop_loss_price:
                return True, "stop_loss"
            if current_price <= take_profit_price:
                return True, "take_profit"

        return False, None


# Global risk manager instance
risk_manager = RiskManager()
