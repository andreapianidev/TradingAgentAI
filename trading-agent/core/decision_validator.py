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

# Alpaca fee for R:R calculation (taker fee per trade)
ALPACA_FEE_PCT = 0.15  # 0.15% per trade = 0.30% round-trip


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
        """Sanitize OPEN decision values with R:R validation and tracking."""
        sanitized = decision.copy()

        # Initialize tracking fields
        sanitized["tp_sl_adjusted"] = False
        sanitized["tp_sl_adjustment_reason"] = None
        sanitized["original_tp_pct"] = None
        sanitized["original_sl_pct"] = None

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

        # Store original values for tracking
        original_sl = sanitized["stop_loss_pct"]
        original_tp = sanitized["take_profit_pct"]
        sanitized["original_sl_pct"] = original_sl
        sanitized["original_tp_pct"] = original_tp

        sl = sanitized["stop_loss_pct"]
        tp = sanitized["take_profit_pct"]

        # Safety check: SL must be > 0 to avoid division by zero
        if sl <= 0:
            logger.warning(f"Invalid SL ({sl}%), forcing to minimum 1%")
            sl = 1.0
            sanitized["stop_loss_pct"] = sl

        # Apply confidence scaling to TP
        confidence = decision.get("confidence", 0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.6

        tp = self._adjust_tp_by_confidence(tp, confidence)
        sanitized["take_profit_pct"] = tp

        # Calculate NET Risk/Reward ratio considering Alpaca fees
        # Entry fee + Exit fee = 0.30% total
        total_fees = ALPACA_FEE_PCT * 2
        net_tp = tp - total_fees  # Net profit after fees
        net_rr_ratio = net_tp / sl if sl > 0 else 0
        gross_rr_ratio = tp / sl if sl > 0 else 0

        # Minimum R:R of 1.5:1 AFTER fees
        if net_rr_ratio < 1.5:
            # Calculate minimum TP to achieve 1.5:1 net R:R
            min_net_tp = sl * 1.5
            min_gross_tp = min_net_tp + total_fees
            old_tp = tp
            new_tp = max(2.0, min(20.0, min_gross_tp))
            sanitized["take_profit_pct"] = new_tp

            # Track the adjustment
            sanitized["tp_sl_adjusted"] = True
            sanitized["tp_sl_adjustment_reason"] = (
                f"R:R netto {net_rr_ratio:.2f}:1 < 1.5:1 minimo (fee {total_fees:.2f}%). "
                f"TP modificato da {old_tp:.1f}% a {new_tp:.1f}% "
                f"(nuovo R:R netto = {(new_tp - total_fees)/sl:.2f}:1)"
            )
            logger.warning(sanitized["tp_sl_adjustment_reason"])
        else:
            logger.info(
                f"Dynamic TP/SL: SL={sl}%, TP={tp}%, "
                f"Gross R:R={gross_rr_ratio:.2f}:1, "
                f"Net R:R={net_rr_ratio:.2f}:1 (after {total_fees:.2f}% fees)"
            )

        # Preserve tp_sl_reasoning if provided by LLM
        if decision.get("tp_sl_reasoning"):
            sanitized["tp_sl_reasoning"] = decision["tp_sl_reasoning"]

        # Validate confidence
        sanitized["confidence"] = max(0.0, min(1.0, confidence))

        return sanitized

    def _adjust_tp_by_confidence(self, tp_pct: float, confidence: float) -> float:
        """
        Scale Take Profit based on confidence level.

        High confidence (>0.85): Allow more ambitious TP (+10%)
        Low confidence (<0.65): More conservative TP (-10%)

        Args:
            tp_pct: Original take profit percentage
            confidence: LLM confidence score (0-1)

        Returns:
            Adjusted take profit percentage
        """
        if confidence >= 0.85:
            # High confidence: more ambitious TP
            adjusted = tp_pct * 1.1
            logger.info(f"High confidence ({confidence:.2f}): TP scaled up 10% ({tp_pct:.1f}% -> {adjusted:.1f}%)")
            return min(20.0, adjusted)
        elif confidence < 0.65:
            # Low confidence: conservative TP
            adjusted = tp_pct * 0.9
            logger.info(f"Low confidence ({confidence:.2f}): TP scaled down 10% ({tp_pct:.1f}% -> {adjusted:.1f}%)")
            return max(2.0, adjusted)
        return tp_pct

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
