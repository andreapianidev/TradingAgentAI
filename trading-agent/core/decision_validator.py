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
        self.exchange = settings.EXCHANGE

    def _get_symbol_max_leverage(self, symbol: str) -> int:
        """Get maximum leverage allowed for a specific symbol."""
        if self.exchange.lower() != "hyperliquid":
            return 1  # Alpaca and other exchanges: no leverage

        # Symbol-specific caps for Hyperliquid
        symbol_upper = symbol.upper()
        if "BTC" in symbol_upper:
            return settings.MAX_LEVERAGE_BTC
        elif "ETH" in symbol_upper:
            return settings.MAX_LEVERAGE_ETH
        elif "SOL" in symbol_upper:
            return settings.MAX_LEVERAGE_SOL
        else:
            # Default to conservative for unknown symbols
            return min(10, settings.MAX_LEVERAGE)

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

        # Validate exposure (accounting for leverage)
        new_size = sanitized.get("position_size_pct", 0)
        new_leverage = sanitized.get("leverage", 1)

        # Real exposure = position_size_pct × leverage
        effective_exposure = new_size * new_leverage
        new_total_exposure = current_exposure + effective_exposure

        if new_total_exposure > self.max_exposure:
            logger.warning(
                f"Would exceed max exposure: {new_total_exposure:.1f}% > {self.max_exposure}% "
                f"(size={new_size}% × leverage={new_leverage}x = {effective_exposure:.1f}%)"
            )
            # Reduce position size to fit
            max_allowed_exposure = self.max_exposure - current_exposure
            max_allowed_size = max_allowed_exposure / new_leverage if new_leverage > 0 else 0

            if max_allowed_size < 1.0:  # Minimum 1%
                return False, self._convert_to_hold(decision), "Exposure limit reached"

            sanitized["position_size_pct"] = max(1.0, min(max_allowed_size, new_size))
            logger.info(
                f"Reduced position size to {sanitized['position_size_pct']:.1f}% "
                f"(effective exposure: {sanitized['position_size_pct'] * new_leverage:.1f}%)"
            )

        return True, sanitized, "Valid open"

    def _sanitize_open(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize OPEN decision values (exchange-aware)."""
        sanitized = decision.copy()
        symbol = decision.get("symbol", "")

        # Exchange-aware leverage validation
        leverage = decision.get("leverage", 1)
        symbol_max = self._get_symbol_max_leverage(symbol)

        if self.exchange.lower() == "alpaca":
            # Alpaca: force to 1x (no leverage support)
            sanitized["leverage"] = 1
            if leverage != 1:
                logger.info(f"Forced leverage from {leverage}x to 1x (Alpaca does not support leverage)")

        elif self.exchange.lower() == "hyperliquid":
            # Hyperliquid: validate and clamp leverage
            leverage_int = int(max(1, min(symbol_max, leverage)))

            # Apply symbol-specific cap
            if leverage_int > symbol_max:
                logger.info(f"Clamped leverage from {leverage}x to {symbol_max}x (symbol cap for {symbol})")

            # Apply overall max leverage
            if leverage_int > self.max_leverage:
                leverage_int = self.max_leverage
                logger.info(f"Clamped leverage to {self.max_leverage}x (global max)")

            sanitized["leverage"] = leverage_int

        else:
            # Unknown exchange: default to 1x for safety
            sanitized["leverage"] = 1
            logger.warning(f"Unknown exchange '{self.exchange}', forcing leverage to 1x")

        # Clamp position size
        size = decision.get("position_size_pct", 2.0)
        sanitized["position_size_pct"] = max(1.0, min(self.max_position_size, float(size)))

        if size != sanitized["position_size_pct"]:
            logger.info(f"Clamped position size from {size}% to {sanitized['position_size_pct']}%")

        # Validate stop loss
        stop_loss = decision.get("stop_loss_pct", settings.STOP_LOSS_PCT)
        sanitized["stop_loss_pct"] = max(1.0, min(10.0, float(stop_loss)))

        # Validate take profit
        take_profit = decision.get("take_profit_pct", settings.TAKE_PROFIT_PCT)
        sanitized["take_profit_pct"] = max(1.0, min(20.0, float(take_profit)))

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
        # Never block CLOSE or HOLD actions - we always want to allow exits
        if decision.get("action") in [ACTION_CLOSE, ACTION_HOLD]:
            return decision

        # Only adjust OPEN actions
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

            # For Hyperliquid, also consider reducing leverage in high exposure
            if self.exchange.lower() == "hyperliquid":
                current_leverage = adjusted.get("leverage", 1)
                if current_leverage > 5:
                    adjusted["leverage"] = 5
                    logger.info(f"Reduced leverage to 5x due to high exposure ({current_exposure:.1f}%)")

        return adjusted


# Global validator instance
decision_validator = DecisionValidator()
