#!/usr/bin/env python3
"""Test exchange-aware prompt generation."""
import os
import sys

# Set test environment
os.environ['EXCHANGE'] = 'alpaca'
os.environ['LEVERAGE_STRATEGY'] = 'aggressive'
os.environ['MAX_LEVERAGE'] = '30'
os.environ['MAX_LEVERAGE_BTC'] = '30'
os.environ['MAX_LEVERAGE_ETH'] = '25'
os.environ['MAX_LEVERAGE_SOL'] = '15'

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.prompts import get_system_prompt, _get_leverage_rules, build_user_prompt


def test_leverage_rules():
    """Test leverage rules factory."""
    print('=== TEST 1: LEVERAGE RULES FACTORY ===')

    # Test Alpaca
    alpaca_rules = _get_leverage_rules('alpaca')
    assert 'ALPACA' in alpaca_rules, "Missing ALPACA in rules"
    assert 'SEMPRE 1' in alpaca_rules, "Missing 'SEMPRE 1' constraint"
    print('✓ Alpaca leverage rules correct')

    # Test Hyperliquid aggressive
    hyper_rules = _get_leverage_rules('hyperliquid')
    assert 'AGGRESSIVE' in hyper_rules, "Missing AGGRESSIVE strategy"
    assert 'Confidence 0.60-0.69' in hyper_rules, "Missing confidence tiers"
    assert 'BTC: MAX 30x' in hyper_rules, "Missing BTC cap"
    assert 'ETH: MAX 25x' in hyper_rules, "Missing ETH cap"
    assert 'SOL: MAX 15x' in hyper_rules, "Missing SOL cap"
    print('✓ Hyperliquid aggressive leverage rules correct')
    print()


def test_alpaca_prompt():
    """Test Alpaca system prompt."""
    print('=== TEST 2: ALPACA SYSTEM PROMPT ===')

    prompt = get_system_prompt(exchange='alpaca')

    assert 'IMPORTANTE - EXCHANGE ALPACA' in prompt, "Missing Alpaca section"
    assert 'NON supporta la leva' in prompt, "Missing no-leverage statement"
    assert 'leverage' in prompt.lower(), "Missing leverage keyword"

    # Check it doesn't contain Hyperliquid rules
    assert 'AGGRESSIVE' not in prompt, "Should not contain Hyperliquid rules"

    print('✓ Alpaca system prompt is correct')
    print('✓ Correctly excludes Hyperliquid leverage rules')
    print()


def test_hyperliquid_prompt():
    """Test Hyperliquid system prompt."""
    print('=== TEST 3: HYPERLIQUID SYSTEM PROMPT ===')

    prompt = get_system_prompt(exchange='hyperliquid')

    assert 'STRATEGIA LEVA: AGGRESSIVE' in prompt, "Missing aggressive strategy"
    assert 'Confidence 0.60-0.69' in prompt, "Missing confidence tier 1"
    assert 'Confidence 0.70-0.79' in prompt, "Missing confidence tier 2"
    assert 'Confidence 0.80-0.89' in prompt, "Missing confidence tier 3"
    assert 'Confidence 0.90-1.00' in prompt, "Missing confidence tier 4"
    assert 'BTC: MAX 30x' in prompt, "Missing BTC cap"
    assert 'ETH: MAX 25x' in prompt, "Missing ETH cap"
    assert 'SOL: MAX 15x' in prompt, "Missing SOL cap"

    # Check it doesn't contain Alpaca-specific rules
    assert 'SEMPRE 1' not in prompt, "Should not contain Alpaca 1x constraint"

    print('✓ Hyperliquid system prompt is correct')
    print('✓ Contains all confidence-based leverage tiers')
    print('✓ Contains all symbol-specific caps')
    print('✓ Correctly excludes Alpaca rules')
    print()


def test_user_prompt():
    """Test user prompt includes exchange info."""
    print('=== TEST 4: USER PROMPT EXCHANGE INFO ===')

    # Mock data
    mock_portfolio = {'total_value': 10000, 'cash': 5000}
    mock_market = {'price': 50000, 'volume': 1000000}
    mock_indicators = {'rsi': 50, 'macd': 0.5}
    mock_pivot = {'r1': 51000, 's1': 49000}

    # Test Alpaca
    alpaca_prompt = build_user_prompt(
        symbol='BTC',
        portfolio=mock_portfolio,
        market_data=mock_market,
        indicators=mock_indicators,
        pivot_points=mock_pivot,
        forecast={},
        orderbook={},
        sentiment={},
        news=[],
        open_positions=[],
        whale_flow={},
        coingecko={},
        exchange='alpaca'
    )

    assert 'Exchange: ALPACA' in alpaca_prompt, "Missing exchange info in Alpaca prompt"
    print('✓ Alpaca user prompt includes exchange: ALPACA')

    # Test Hyperliquid
    hyper_prompt = build_user_prompt(
        symbol='BTC',
        portfolio=mock_portfolio,
        market_data=mock_market,
        indicators=mock_indicators,
        pivot_points=mock_pivot,
        forecast={},
        orderbook={},
        sentiment={},
        news=[],
        open_positions=[],
        whale_flow={},
        coingecko={},
        exchange='hyperliquid'
    )

    assert 'Exchange: HYPERLIQUID' in hyper_prompt, "Missing exchange info in Hyperliquid prompt"
    print('✓ Hyperliquid user prompt includes exchange: HYPERLIQUID')
    print()


def main():
    """Run all tests."""
    print('\n' + '='*60)
    print('EXCHANGE-AWARE PROMPTS VALIDATION')
    print('='*60 + '\n')

    try:
        test_leverage_rules()
        test_alpaca_prompt()
        test_hyperliquid_prompt()
        test_user_prompt()

        print('='*60)
        print('ALL TESTS PASSED ✓')
        print('='*60)
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
