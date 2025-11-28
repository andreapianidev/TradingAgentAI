"""
Tests for the RiskManager class.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestRiskManagerLeverage:
    """Test leverage validation."""

    def test_check_leverage_valid_minimum(self):
        """Test minimum valid leverage (1x)."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            assert rm.check_leverage(1) is True

    def test_check_leverage_valid_maximum(self):
        """Test maximum valid leverage."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            assert rm.check_leverage(10) is True

    def test_check_leverage_exceeds_max(self):
        """Test leverage above maximum fails."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            assert rm.check_leverage(11) is False
            assert rm.check_leverage(20) is False

    def test_check_leverage_zero_invalid(self):
        """Test zero leverage is invalid."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            assert rm.check_leverage(0) is False


class TestRiskManagerPositionSize:
    """Test position size validation."""

    def test_check_position_size_valid(self):
        """Test valid position size."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            # 3% of 10000 = 300 (above $10 minimum)
            assert rm.check_position_size(3.0, 10000.0) is True

    def test_check_position_size_exceeds_max(self):
        """Test position size above maximum fails."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            assert rm.check_position_size(6.0, 10000.0) is False

    def test_check_position_size_below_minimum_order(self):
        """Test position size below minimum order value."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            # 1% of 100 = 1 (below $10 minimum)
            assert rm.check_position_size(1.0, 100.0) is False

    def test_check_position_size_zero_invalid(self):
        """Test zero position size is invalid."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            assert rm.check_position_size(0, 10000.0) is False


class TestRiskManagerExposure:
    """Test exposure validation."""

    def test_check_total_exposure_within_limit(self):
        """Test exposure within limit."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            # 5% new + 20% current = 25% (under 30%)
            assert rm.check_total_exposure(5.0, 20.0) is True

    def test_check_total_exposure_exceeds_limit(self):
        """Test exposure exceeds limit."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            # 5% new + 28% current = 33% (over 30%)
            assert rm.check_total_exposure(5.0, 28.0) is False

    def test_check_total_exposure_at_limit(self):
        """Test exposure exactly at limit."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            # 5% new + 25% current = 30% (exactly at limit)
            assert rm.check_total_exposure(5.0, 25.0) is True


class TestRiskManagerConfidence:
    """Test confidence validation."""

    def test_check_confidence_above_threshold(self):
        """Test confidence above threshold passes."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            assert rm.check_confidence(0.75) is True
            assert rm.check_confidence(0.9) is True

    def test_check_confidence_below_threshold(self):
        """Test confidence below threshold fails."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            assert rm.check_confidence(0.5) is False
            assert rm.check_confidence(0.59) is False

    def test_check_confidence_at_threshold(self):
        """Test confidence exactly at threshold passes."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            assert rm.check_confidence(0.6) is True


class TestRiskManagerStopLoss:
    """Test stop loss calculation."""

    def test_calculate_stop_loss_long(self):
        """Test stop loss for long position."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            # Entry 50000, 3% SL for long = 48500
            sl = rm.calculate_stop_loss_price(50000.0, "long")
            assert sl == 48500.0

    def test_calculate_stop_loss_short(self):
        """Test stop loss for short position."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            # Entry 50000, 3% SL for short = 51500
            sl = rm.calculate_stop_loss_price(50000.0, "short")
            assert sl == 51500.0

    def test_calculate_stop_loss_custom_percentage(self):
        """Test stop loss with custom percentage."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            # Entry 50000, 5% SL for long = 47500
            sl = rm.calculate_stop_loss_price(50000.0, "long", 5.0)
            assert sl == 47500.0


class TestRiskManagerTakeProfit:
    """Test take profit calculation."""

    def test_calculate_take_profit_long(self):
        """Test take profit for long position."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            # Entry 50000, 5% TP for long = 52500
            tp = rm.calculate_take_profit_price(50000.0, "long")
            assert tp == 52500.0

    def test_calculate_take_profit_short(self):
        """Test take profit for short position."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            # Entry 50000, 5% TP for short = 47500
            tp = rm.calculate_take_profit_price(50000.0, "short")
            assert tp == 47500.0


class TestRiskManagerPositionSizeCalculation:
    """Test position size calculation based on confidence."""

    def test_calculate_position_size_low_confidence(self):
        """Test small position for low confidence."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            size = rm.calculate_position_size(10000.0, 0.6)
            assert size >= 1.0
            assert size <= 2.0

    def test_calculate_position_size_medium_confidence(self):
        """Test medium position for medium confidence."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            size = rm.calculate_position_size(10000.0, 0.75)
            assert size >= 2.0
            assert size <= 3.5

    def test_calculate_position_size_high_confidence(self):
        """Test larger position for high confidence."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            size = rm.calculate_position_size(10000.0, 0.95)
            assert size >= 4.0
            assert size <= 5.0


class TestRiskManagerLeverageCalculation:
    """Test leverage calculation based on confidence."""

    def test_calculate_leverage_low_confidence(self):
        """Test low leverage for low confidence."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            leverage = rm.calculate_leverage(0.65)
            assert leverage >= 1
            assert leverage <= 3

    def test_calculate_leverage_medium_confidence(self):
        """Test medium leverage for medium confidence."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            leverage = rm.calculate_leverage(0.75)
            assert leverage >= 4
            assert leverage <= 6

    def test_calculate_leverage_high_confidence(self):
        """Test high leverage for high confidence."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            leverage = rm.calculate_leverage(0.9)
            assert leverage >= 7
            assert leverage <= 10


class TestRiskManagerValidateTrade:
    """Test complete trade validation."""

    def test_validate_trade_all_pass(self):
        """Test trade validation when all checks pass."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            is_valid, reason = rm.validate_trade(
                leverage=5,
                size_pct=3.0,
                confidence=0.75,
                current_exposure=10.0,
                available_balance=10000.0
            )

            assert is_valid is True
            assert "passed" in reason.lower()

    def test_validate_trade_fails_leverage(self):
        """Test trade validation fails on leverage."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            is_valid, reason = rm.validate_trade(
                leverage=15,
                size_pct=3.0,
                confidence=0.75,
                current_exposure=10.0,
                available_balance=10000.0
            )

            assert is_valid is False
            assert "leverage" in reason.lower()

    def test_validate_trade_fails_exposure(self):
        """Test trade validation fails on exposure."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            is_valid, reason = rm.validate_trade(
                leverage=5,
                size_pct=5.0,
                confidence=0.75,
                current_exposure=28.0,  # 28 + 5 = 33 > 30
                available_balance=10000.0
            )

            assert is_valid is False
            assert "exposure" in reason.lower()

    def test_validate_trade_fails_confidence(self):
        """Test trade validation fails on confidence."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            is_valid, reason = rm.validate_trade(
                leverage=5,
                size_pct=3.0,
                confidence=0.5,  # Below 0.6 threshold
                current_exposure=10.0,
                available_balance=10000.0
            )

            assert is_valid is False
            assert "confidence" in reason.lower()


class TestRiskManagerShouldClosePosition:
    """Test position close detection."""

    def test_should_close_long_stop_loss_hit(self):
        """Test position close on stop loss for long."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            should_close, reason = rm.should_close_position(
                current_price=48000.0,  # Below SL
                entry_price=50000.0,
                direction="long",
                stop_loss_price=48500.0,
                take_profit_price=52500.0
            )

            assert should_close is True
            assert reason == "stop_loss"

    def test_should_close_long_take_profit_hit(self):
        """Test position close on take profit for long."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            should_close, reason = rm.should_close_position(
                current_price=53000.0,  # Above TP
                entry_price=50000.0,
                direction="long",
                stop_loss_price=48500.0,
                take_profit_price=52500.0
            )

            assert should_close is True
            assert reason == "take_profit"

    def test_should_close_short_stop_loss_hit(self):
        """Test position close on stop loss for short."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            should_close, reason = rm.should_close_position(
                current_price=52000.0,  # Above SL for short
                entry_price=50000.0,
                direction="short",
                stop_loss_price=51500.0,
                take_profit_price=47500.0
            )

            assert should_close is True
            assert reason == "stop_loss"

    def test_should_close_short_take_profit_hit(self):
        """Test position close on take profit for short."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            should_close, reason = rm.should_close_position(
                current_price=47000.0,  # Below TP for short
                entry_price=50000.0,
                direction="short",
                stop_loss_price=51500.0,
                take_profit_price=47500.0
            )

            assert should_close is True
            assert reason == "take_profit"

    def test_should_not_close_within_range(self):
        """Test position should not close when within SL/TP range."""
        with patch('config.settings.settings') as mock_settings:
            mock_settings.MAX_LEVERAGE = 10
            mock_settings.MAX_POSITION_SIZE_PCT = 5.0
            mock_settings.MAX_TOTAL_EXPOSURE_PCT = 30.0
            mock_settings.STOP_LOSS_PCT = 3.0
            mock_settings.TAKE_PROFIT_PCT = 5.0
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 0.6

            from core.risk_manager import RiskManager
            rm = RiskManager()

            should_close, reason = rm.should_close_position(
                current_price=50500.0,  # Between SL and TP
                entry_price=50000.0,
                direction="long",
                stop_loss_price=48500.0,
                take_profit_price=52500.0
            )

            assert should_close is False
            assert reason is None
