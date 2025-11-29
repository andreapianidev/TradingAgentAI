#!/usr/bin/env python3
"""Test Hyperliquid leverage validation."""
import os
import sys

# Set Hyperliquid environment
os.environ['EXCHANGE'] = 'hyperliquid'
os.environ['LEVERAGE_STRATEGY'] = 'aggressive'
os.environ['MAX_LEVERAGE'] = '30'
os.environ['MAX_LEVERAGE_BTC'] = '30'
os.environ['MAX_LEVERAGE_ETH'] = '25'
os.environ['MAX_LEVERAGE_SOL'] = '15'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.decision_validator import DecisionValidator
from config.constants import ACTION_OPEN, DIRECTION_LONG


def test_hyperliquid_symbol_caps():
    """Test symbol-specific leverage caps."""
    print('=== TEST 1: HYPERLIQUID SYMBOL CAPS ===')

    validator = DecisionValidator()

    btc_max = validator._get_symbol_max_leverage('BTC')
    eth_max = validator._get_symbol_max_leverage('ETH')
    sol_max = validator._get_symbol_max_leverage('SOL')

    assert btc_max == 30, f"BTC max should be 30, got {btc_max}"
    assert eth_max == 25, f"ETH max should be 25, got {eth_max}"
    assert sol_max == 15, f"SOL max should be 15, got {sol_max}"

    print('✓ BTC max leverage: 30x')
    print('✓ ETH max leverage: 25x')
    print('✓ SOL max leverage: 15x')
    print()


def test_hyperliquid_leverage_clamping():
    """Test leverage is clamped to symbol-specific caps."""
    print('=== TEST 2: HYPERLIQUID LEVERAGE CLAMPING ===')

    validator = DecisionValidator()

    # Test BTC with excessive leverage (50x requested, should clamp to 30x)
    decision_btc = {
        'action': ACTION_OPEN,
        'symbol': 'BTC',
        'direction': DIRECTION_LONG,
        'leverage': 50,  # Exceeds BTC cap of 30x
        'position_size_pct': 3.0,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
        'confidence': 0.95,
        'reasoning': 'Very high confidence BTC trade'
    }

    is_valid, sanitized_btc, _ = validator.validate(decision_btc, current_exposure=0, has_position=False)
    assert is_valid, "Decision should be valid"
    assert sanitized_btc['leverage'] == 30, f"BTC leverage should be clamped to 30x, got {sanitized_btc['leverage']}"
    print(f'✓ BTC: Requested 50x → clamped to {sanitized_btc["leverage"]}x (symbol cap)')

    # Test SOL with moderate leverage (20x requested, should clamp to 15x)
    decision_sol = {
        'action': ACTION_OPEN,
        'symbol': 'SOL',
        'direction': DIRECTION_LONG,
        'leverage': 20,  # Exceeds SOL cap of 15x
        'position_size_pct': 3.0,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
        'confidence': 0.90,
        'reasoning': 'High confidence SOL trade'
    }

    is_valid, sanitized_sol, _ = validator.validate(decision_sol, current_exposure=0, has_position=False)
    assert is_valid, "Decision should be valid"
    assert sanitized_sol['leverage'] == 15, f"SOL leverage should be clamped to 15x, got {sanitized_sol['leverage']}"
    print(f'✓ SOL: Requested 20x → clamped to {sanitized_sol["leverage"]}x (symbol cap)')
    print()


def test_hyperliquid_exposure_with_leverage():
    """Test exposure calculation accounts for leverage."""
    print('=== TEST 3: HYPERLIQUID EXPOSURE WITH LEVERAGE ===')

    validator = DecisionValidator()

    # Position with 5% size × 10x leverage = 50% effective exposure
    decision = {
        'action': ACTION_OPEN,
        'symbol': 'BTC',
        'direction': DIRECTION_LONG,
        'leverage': 10,
        'position_size_pct': 5.0,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
        'confidence': 0.85,
        'reasoning': 'Moderate leverage trade'
    }

    is_valid, sanitized, reason = validator.validate(decision, current_exposure=0, has_position=False)
    assert is_valid, f"Decision should be valid: {reason}"

    effective_exposure = sanitized['position_size_pct'] * sanitized['leverage']
    print(f'✓ Position: {sanitized["position_size_pct"]}% × {sanitized["leverage"]}x = {effective_exposure}% effective exposure')

    # Should allow this as it's under 30% max exposure
    assert effective_exposure <= 30, f"Effective exposure {effective_exposure}% exceeds max 30%"
    print(f'✓ Total exposure: {effective_exposure}% (under 30% max)')
    print()


def test_hyperliquid_exposure_limit_with_leverage():
    """Test that high leverage is reduced when it would exceed exposure limit."""
    print('=== TEST 4: HYPERLIQUID EXPOSURE LIMIT ENFORCEMENT ===')

    validator = DecisionValidator()

    # Scenario 1: Current exposure is 10%, want to add 3% × 10x = 30% (should reduce size to fit)
    decision1 = {
        'action': ACTION_OPEN,
        'symbol': 'ETH',
        'direction': DIRECTION_LONG,
        'leverage': 10,
        'position_size_pct': 3.0,  # 3% × 10x = 30% effective
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
        'confidence': 0.90,
        'reasoning': 'Moderate leverage trade'
    }

    is_valid1, sanitized1, reason1 = validator.validate(decision1, current_exposure=10, has_position=False)

    if sanitized1['action'] == ACTION_OPEN:
        # Should be valid but position size reduced to fit
        effective_exposure1 = sanitized1['position_size_pct'] * sanitized1['leverage']
        total_exposure1 = 10 + effective_exposure1

        assert total_exposure1 <= 30, f"Total exposure {total_exposure1}% should not exceed 30%"
        print(f'✓ Scenario 1: Current 10% + (3% × 10x) = would exceed')
        print(f'  Adjusted to: {sanitized1["position_size_pct"]:.2f}% × {sanitized1["leverage"]}x = {effective_exposure1:.2f}%')
        print(f'  Total: {total_exposure1:.2f}% (within 30% max)')
    else:
        print(f'✓ Scenario 1: Converted to HOLD (insufficient room: {reason1})')

    # Scenario 2: Current exposure is 29%, want to add 2% × 5x = 10% (should reduce or convert to HOLD)
    decision2 = {
        'action': ACTION_OPEN,
        'symbol': 'BTC',
        'direction': DIRECTION_LONG,
        'leverage': 5,
        'position_size_pct': 2.0,  # 2% × 5x = 10% effective
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
        'confidence': 0.85,
        'reasoning': 'Small leverage trade at high exposure'
    }

    is_valid2, sanitized2, reason2 = validator.validate(decision2, current_exposure=29, has_position=False)

    if sanitized2['action'] == ACTION_OPEN:
        effective_exposure2 = sanitized2['position_size_pct'] * sanitized2['leverage']
        total_exposure2 = 29 + effective_exposure2
        assert total_exposure2 <= 30, f"Total exposure {total_exposure2}% should not exceed 30%"
        print(f'✓ Scenario 2: Current 29% + minimal position allowed')
        print(f'  Adjusted to: {sanitized2["position_size_pct"]:.2f}% × {sanitized2["leverage"]}x = {effective_exposure2:.2f}%')
    else:
        print(f'✓ Scenario 2: Converted to HOLD (exposure limit reached: {reason2})')

    print()


def test_hyperliquid_high_exposure_leverage_reduction():
    """Test that leverage is reduced when exposure is high."""
    print('=== TEST 5: HYPERLIQUID HIGH EXPOSURE LEVERAGE REDUCTION ===')

    validator = DecisionValidator()

    # High exposure scenario (26%) with high leverage
    decision = {
        'action': ACTION_OPEN,
        'symbol': 'BTC',
        'direction': DIRECTION_LONG,
        'leverage': 20,  # High leverage
        'position_size_pct': 2.0,
        'stop_loss_pct': 2.0,
        'take_profit_pct': 5.0,
        'confidence': 0.85,
        'reasoning': 'High leverage at high exposure'
    }

    adjusted = validator.adjust_for_high_exposure(decision, current_exposure=26)

    # Should reduce leverage to 5x max when exposure > 25%
    if adjusted['action'] == ACTION_OPEN:
        assert adjusted['leverage'] <= 5, f"Leverage should be reduced to max 5x, got {adjusted['leverage']}"
        print(f'✓ High exposure (26%) → leverage reduced from 20x to {adjusted["leverage"]}x')
    print()


def test_hyperliquid_valid_leverage_range():
    """Test that valid leverage values are preserved."""
    print('=== TEST 6: HYPERLIQUID VALID LEVERAGE PRESERVATION ===')

    validator = DecisionValidator()

    test_cases = [
        ('BTC', 5, 5),   # 5x is valid for BTC
        ('BTC', 20, 20), # 20x is valid for BTC
        ('ETH', 10, 10), # 10x is valid for ETH
        ('SOL', 10, 10), # 10x is valid for SOL
    ]

    for symbol, requested, expected in test_cases:
        decision = {
            'action': ACTION_OPEN,
            'symbol': symbol,
            'direction': DIRECTION_LONG,
            'leverage': requested,
            'position_size_pct': 2.0,
            'stop_loss_pct': 2.0,
            'take_profit_pct': 5.0,
            'confidence': 0.85,
            'reasoning': f'Test {symbol} {requested}x'
        }

        is_valid, sanitized, _ = validator.validate(decision, current_exposure=0, has_position=False)
        assert is_valid, f"{symbol} {requested}x should be valid"
        assert sanitized['leverage'] == expected, f"Expected {expected}x, got {sanitized['leverage']}x"
        print(f'✓ {symbol} {requested}x → preserved as {sanitized["leverage"]}x')
    print()


def main():
    """Run all Hyperliquid leverage tests."""
    print('\n' + '='*60)
    print('HYPERLIQUID LEVERAGE VALIDATION TESTS')
    print('='*60 + '\n')

    try:
        test_hyperliquid_symbol_caps()
        test_hyperliquid_leverage_clamping()
        test_hyperliquid_exposure_with_leverage()
        test_hyperliquid_exposure_limit_with_leverage()
        test_hyperliquid_high_exposure_leverage_reduction()
        test_hyperliquid_valid_leverage_range()

        print('='*60)
        print('ALL HYPERLIQUID LEVERAGE TESTS PASSED ✓')
        print('='*60)
        print('\nHyperliquid leverage system is working correctly!')
        print('The system correctly:')
        print('  • Applies symbol-specific leverage caps (BTC 30x, ETH 25x, SOL 15x)')
        print('  • Calculates effective exposure (position_size × leverage)')
        print('  • Enforces maximum exposure limits')
        print('  • Reduces leverage at high exposure levels')
        print('  • Preserves valid leverage values')
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
