"""
Validation of LLM trading decisions.
"""
from typing import Dict, Any, Tuple, Optional

from config.settings import settings
from config.constants import (
    ACTION_OPEN, ACTION_CLOSE, ACTION_HOLD,
    DIRECTION_LONG, DIRECTION_SHORT
)
from utils.logger import get_logger

logger = get_logger(__name__)


class DecisionValidator:
    """Validates and sanitizes LLM trading decisions."""

    def __init__(self):
        """Initialize the validator."""
        self.max_leverage = settings.MAX_LEVERAGE
        self.max_position_size = settings.MAX_POSITION_SIZE_PCT
        self.max_exposure = settings.MAX_TOTAL_EXPOSURE_PCT
        self.min_confidence = settings.MIN_CONFIDENCE_THRESHOLD

    def validate(
        self,
        decision: Dict[str, Any],
        current_exposure: float = 0,
        has_position: bool = False
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        Validate a trading decision.

        Args:
            decision: LLM decision dictionary
            current_exposure: Current portfolio exposure percentage
            has_position: Whether position already exists for symbol

        Returns:
            Tuple of (is_valid, sanitized_decision, reason)
        """
        action = decision.get("action")
        symbol = decision.get("symbol")

        # Validate action
        if action not in [ACTION_OPEN, ACTION_CLOSE, ACTION_HOLD]:
            return False, decision, f"Invalid action: {action}"

        # HOLD always valid
        if action == ACTION_HOLD:
            return True, self._sanitize_hold(decision), "Valid hold"

        # CLOSE validation
        if action == ACTION_CLOSE:
            if not has_position:
                logger.warning(f"Cannot close non-existent position for {symbol}")
                return False, self._convert_to_hold(decision), "No position to close"
            return True, decision, "Valid close"

        # OPEN validation
        if action == ACTION_OPEN:
            return self._validate_open(decision, current_exposure, has_position)

        return False, decision, "Unknown validation error"

    def _validate_open(
        self,
        decision: Dict[str, Any],
        current_exposure: float,
        has_position: bool
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Validate an OPEN decision."""
        symbol = decision.get("symbol")

        # Check if position already exists
        if has_position:
            logger.warning(f"Position already exists for {symbol}")
            return False, self._convert_to_hold(decision), "Position already exists"

        # Validate direction
        direction = decision.get("direction")
        if direction not in [DIRECTION_LONG, DIRECTION_SHORT]:
            return False, self._convert_to_hold(decision), f"Invalid direction: {direction}"

        # Validate confidence
        confidence = decision.get("confidence", 0)
        if confidence < self.min_confidence:
            logger.info(
                f"Confidence {confidence:.2f} below threshold {self.min_confidence}"
            )
            return False, self._convert_to_hold(decision), "Confidence too low"

        # Sanitize and clamp values
        sanitized = self._sanitize_open(decision)

        # Validate exposure
        new_size = sanitized.get("position_size_pct", 0)
        new_exposure = current_exposure + new_size

        if new_exposure > self.max_exposure:
            logger.warning(
                f"Would exceed max exposure: {new_exposure:.1f}% > {self.max_exposure}%"
            )
            # Reduce position size to fit
            max_allowed = self.max_exposure - current_exposure
            if max_allowed < 1.0:  # Minimum 1%
                return False, self._convert_to_hold(decision), "Exposure limit reached"

            sanitized["position_size_pct"] = max(1.0, min(max_allowed, new_size))
            logger.info(f"Reduced position size to {sanitized['position_size_pct']:.1f}%")

        return True, sanitized, "Valid open"

    def _sanitize_open(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize OPEN decision values."""
        sanitized = decision.copy()

        # Force leverage to 1 - Alpaca crypto does not support leverage
        # LLM may suggest leverage > 1, but we ignore it completely
        leverage = decision.get("leverage", 1)
        sanitized["leverage"] = 1  # Always force to 1x for Alpaca crypto

        if leverage != 1:
            logger.info(f"Forced leverage from {leverage}x to 1x (Alpaca crypto does not support leverage)")

        # Clamp position size
        size = decision.get("position_size_pct", 2.0)
        sanitized["position_size_pct"] = max(1.0, min(self.max_position_size, float(size)))

        if size != sanitized["position_size_pct"]:
            logger.info(f"Clamped position size from {size}% to {sanitized['position_size_pct']}%")

        # Validate stop loss (dynamic: 1-10%) with safe float conversion
        try:
            stop_loss_raw = decision.get("stop_loss_pct", settings.STOP_LOSS_PCT)
            stop_loss = float(stop_loss_raw) if stop_loss_raw is not None else settings.STOP_LOSS_PCT
        except (TypeError, ValueError):
            logger.warning(f"Invalid stop_loss_pct value: {decision.get('stop_loss_pct')}, using default")
            stop_loss = settings.STOP_LOSS_PCT
        sanitized["stop_loss_pct"] = max(1.0, min(10.0, stop_loss))

        # Validate take profit (dynamic: 2-20%) with safe float conversion
        try:
            take_profit_raw = decision.get("take_profit_pct", settings.TAKE_PROFIT_PCT)
            take_profit = float(take_profit_raw) if take_profit_raw is not None else settings.TAKE_PROFIT_PCT
        except (TypeError, ValueError):
            logger.warning(f"Invalid take_profit_pct value: {decision.get('take_profit_pct')}, using default")
            take_profit = settings.TAKE_PROFIT_PCT
        sanitized["take_profit_pct"] = max(2.0, min(20.0, take_profit))

        # Validate Risk/Reward ratio (minimum 1.5:1)
        sl = sanitized["stop_loss_pct"]
        tp = sanitized["take_profit_pct"]

        # Safety check: SL must be > 0 to avoid division by zero
        if sl <= 0:
            logger.warning(f"Invalid SL ({sl}%), forcing to minimum 1%")
            sl = 1.0
            sanitized["stop_loss_pct"] = sl

        rr_ratio = tp / sl

        if rr_ratio < 1.5:
            # Adjust TP to meet minimum R:R of 1.5:1
            min_tp = sl * 1.5
            old_tp = tp
            sanitized["take_profit_pct"] = max(2.0, min(20.0, min_tp))
            logger.warning(
                f"Risk/Reward ratio too low ({rr_ratio:.2f}:1). "
                f"Adjusted TP from {old_tp}% to {sanitized['take_profit_pct']}% "
                f"(new R:R = {sanitized['take_profit_pct']/sl:.2f}:1)"
            )
        else:
            logger.info(
                f"Dynamic TP/SL: SL={sl}%, TP={tp}%, R:R={rr_ratio:.2f}:1"
            )

        # Preserve tp_sl_reasoning if provided by LLM
        if decision.get("tp_sl_reasoning"):
            sanitized["tp_sl_reasoning"] = decision["tp_sl_reasoning"]

        # Validate confidence
        confidence = decision.get("confidence", 0)
        sanitized["confidence"] = max(0.0, min(1.0, float(confidence)))

        return sanitized

    def _sanitize_hold(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize HOLD decision."""
        sanitized = decision.copy()
        sanitized["action"] = ACTION_HOLD
        sanitized["direction"] = None
        sanitized["leverage"] = None
        sanitized["position_size_pct"] = None
        return sanitized

    def _convert_to_hold(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Convert any decision to HOLD."""
        return {
            "action": ACTION_HOLD,
            "symbol": decision.get("symbol"),
            "direction": None,
            "leverage": None,
            "position_size_pct": None,
            "stop_loss_pct": None,
            "take_profit_pct": None,
            "confidence": decision.get("confidence", 0),
            "reasoning": f"Converted to HOLD: {decision.get('reasoning', 'No reason')}"
        }

    def adjust_for_high_exposure(
        self,
        decision: Dict[str, Any],
        current_exposure: float
    ) -> Dict[str, Any]:
        """
        Adjust decision based on current exposure.

        High exposure = more conservative decisions
        """
        if decision.get("action") != ACTION_OPEN:
            return decision

        adjusted = decision.copy()

        # If exposure > 25%, require higher confidence
        if current_exposure > 25:
            min_confidence = 0.75
            if adjusted.get("confidence", 0) < min_confidence:
                logger.info(
                    f"High exposure ({current_exposure:.1f}%) requires "
                    f"confidence >= {min_confidence}"
                )
                return self._convert_to_hold(decision)

            # Also reduce position size
            adjusted["position_size_pct"] = min(
                adjusted.get("position_size_pct", 2.0),
                2.0  # Max 2% when exposure is high
            )

        # Leverage is always 1x for Alpaca crypto (no leverage support)
        # Keep this line for safety even though _sanitize_open already forces it
        adjusted["leverage"] = 1

        return adjusted


# Global validator instance
decision_validator = DecisionValidator()
