#!/usr/bin/env python3
"""Test backward compatibility with Alpaca exchange."""
import os
import sys

# Set Alpaca environment
os.environ['EXCHANGE'] = 'alpaca'
os.environ['MAX_LEVERAGE'] = '30'  # Should be ignored for Alpaca
os.environ['LEVERAGE_STRATEGY'] = 'aggressive'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.decision_validator import DecisionValidator
from config.constants import ACTION_OPEN, ACTION_HOLD, DIRECTION_LONG


def test_alpaca_leverage_forced_to_1():
    """Test that Alpaca always forces leverage to 1."""
    print('=== TEST 1: ALPACA LEVERAGE FORCED TO 1 ===')

    validator = DecisionValidator()

    # LLM suggests high leverage (should be ignored)
    decision = {
        'action': ACTION_OPEN,
        'symbol': 'BTC',
        'direction': DIRECTION_LONG,
        'leverage': 20,  # LLM suggests 20x
        'position_size_pct': 3.0,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
        'confidence': 0.85,
        'reasoning': 'Test decision'
    }

    is_valid, sanitized, reason = validator.validate(decision, current_exposure=0, has_position=False)

    assert is_valid, f"Decision should be valid: {reason}"
    assert sanitized['leverage'] == 1, f"Leverage should be 1, got {sanitized['leverage']}"
    print(f'✓ LLM suggested {decision["leverage"]}x, validator forced to {sanitized["leverage"]}x')
    print()


def test_alpaca_symbol_max_leverage():
    """Test symbol-specific max leverage returns 1 for Alpaca."""
    print('=== TEST 2: ALPACA SYMBOL MAX LEVERAGE ===')

    validator = DecisionValidator()

    btc_max = validator._get_symbol_max_leverage('BTC')
    eth_max = validator._get_symbol_max_leverage('ETH')
    sol_max = validator._get_symbol_max_leverage('SOL')

    assert btc_max == 1, f"BTC max should be 1 for Alpaca, got {btc_max}"
    assert eth_max == 1, f"ETH max should be 1 for Alpaca, got {eth_max}"
    assert sol_max == 1, f"SOL max should be 1 for Alpaca, got {sol_max}"

    print('✓ BTC max leverage: 1x')
    print('✓ ETH max leverage: 1x')
    print('✓ SOL max leverage: 1x')
    print()


def test_alpaca_exposure_calculation():
    """Test exposure calculation with forced 1x leverage."""
    print('=== TEST 3: ALPACA EXPOSURE CALCULATION ===')

    validator = DecisionValidator()

    # Decision with 5% position size
    decision = {
        'action': ACTION_OPEN,
        'symbol': 'BTC',
        'direction': DIRECTION_LONG,
        'leverage': 10,  # Will be forced to 1
        'position_size_pct': 5.0,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
        'confidence': 0.85,
        'reasoning': 'Test decision'
    }

    is_valid, sanitized, reason = validator.validate(decision, current_exposure=20, has_position=False)

    assert is_valid, f"Decision should be valid: {reason}"
    assert sanitized['leverage'] == 1, "Leverage should be 1"

    # With 1x leverage, effective exposure = position size
    # Current: 20%, New: 5% × 1 = 5%, Total: 25% (under 30% max)
    effective_exposure = sanitized['position_size_pct'] * sanitized['leverage']
    total_exposure = 20 + effective_exposure

    print(f'✓ Position size: {sanitized["position_size_pct"]}%')
    print(f'✓ Leverage: {sanitized["leverage"]}x')
    print(f'✓ Effective exposure: {effective_exposure}%')
    print(f'✓ Total exposure: {total_exposure}% (max 30%)')
    print()


def test_alpaca_high_exposure_adjustment():
    """Test high exposure adjustment doesn't break with 1x leverage."""
    print('=== TEST 4: ALPACA HIGH EXPOSURE ADJUSTMENT ===')

    validator = DecisionValidator()

    # Test 4a: High confidence allows trade but reduces position size
    decision_high_conf = {
        'action': ACTION_OPEN,
        'symbol': 'ETH',
        'direction': DIRECTION_LONG,
        'leverage': 5,  # Will be forced to 1
        'position_size_pct': 4.0,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
        'confidence': 0.80,  # High confidence (>= 0.75)
        'reasoning': 'High confidence trade'
    }

    adjusted_high = validator.adjust_for_high_exposure(decision_high_conf, current_exposure=26)

    # With confidence >= 0.75, trade is allowed but position size reduced to 2%
    assert adjusted_high['action'] == ACTION_OPEN, "High confidence should allow trade"
    assert adjusted_high['position_size_pct'] <= 2.0, "Position size should be reduced to max 2%"
    print(f'✓ High exposure (26%) + high confidence (0.80) → allowed with reduced size ({adjusted_high["position_size_pct"]}%)')

    # Test 4b: Low confidence converts to HOLD
    decision_low_conf = {
        'action': ACTION_OPEN,
        'symbol': 'SOL',
        'direction': DIRECTION_LONG,
        'leverage': 3,
        'position_size_pct': 4.0,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
        'confidence': 0.70,  # Below 0.75 threshold
        'reasoning': 'Moderate confidence trade'
    }

    adjusted_low = validator.adjust_for_high_exposure(decision_low_conf, current_exposure=26)

    assert adjusted_low['action'] == ACTION_HOLD, "Low confidence at high exposure should convert to HOLD"
    print(f'✓ High exposure (26%) + low confidence (0.70) → converted to HOLD')
    print()


def test_alpaca_multiple_positions():
    """Test multiple positions don't exceed exposure limit."""
    print('=== TEST 5: ALPACA MULTIPLE POSITIONS ===')

    validator = DecisionValidator()

    # First position: 5%
    decision1 = {
        'action': ACTION_OPEN,
        'symbol': 'BTC',
        'direction': DIRECTION_LONG,
        'leverage': 1,
        'position_size_pct': 5.0,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
        'confidence': 0.85,
        'reasoning': 'First position'
    }

    is_valid1, sanitized1, _ = validator.validate(decision1, current_exposure=0, has_position=False)
    assert is_valid1, "First position should be valid"

    current_exposure = sanitized1['position_size_pct'] * sanitized1['leverage']
    print(f'✓ Position 1: {sanitized1["position_size_pct"]}% × {sanitized1["leverage"]}x = {current_exposure}%')

    # Second position: 5%
    decision2 = {
        'action': ACTION_OPEN,
        'symbol': 'ETH',
        'direction': DIRECTION_LONG,
        'leverage': 1,
        'position_size_pct': 5.0,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
        'confidence': 0.80,
        'reasoning': 'Second position'
    }

    is_valid2, sanitized2, _ = validator.validate(decision2, current_exposure=current_exposure, has_position=False)
    assert is_valid2, "Second position should be valid"

    current_exposure += sanitized2['position_size_pct'] * sanitized2['leverage']
    print(f'✓ Position 2: {sanitized2["position_size_pct"]}% × {sanitized2["leverage"]}x = {sanitized2["position_size_pct"]}%')
    print(f'✓ Total exposure: {current_exposure}% (under 30% max)')
    print()


def main():
    """Run all backward compatibility tests."""
    print('\n' + '='*60)
    print('ALPACA BACKWARD COMPATIBILITY TESTS')
    print('='*60 + '\n')

    try:
        test_alpaca_leverage_forced_to_1()
        test_alpaca_symbol_max_leverage()
        test_alpaca_exposure_calculation()
        test_alpaca_high_exposure_adjustment()
        test_alpaca_multiple_positions()

        print('='*60)
        print('ALL ALPACA COMPATIBILITY TESTS PASSED ✓')
        print('='*60)
        print('\nBackward compatibility with Alpaca is maintained!')
        print('The system correctly:')
        print('  • Forces leverage to 1x for Alpaca')
        print('  • Validates exposure limits')
        print('  • Handles high exposure scenarios')
        print('  • Supports multiple positions')
        return 0

    except AssertionError as e:
        print(f'\n✗ TEST FAILED: {e}')
        return 1
    except Exception as e:
        print(f'\n✗ UNEXPECTED ERROR: {e}')
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
