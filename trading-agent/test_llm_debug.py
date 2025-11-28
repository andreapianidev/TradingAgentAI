"""
Debug script to test LLM calls and identify the real issue.
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.llm_client import DeepSeekClient
from config.settings import settings
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(name)s: %(message)s'
)

def test_simple_call():
    """Test a simple LLM call."""
    print("=" * 60)
    print("TEST 1: Simple API Call")
    print("=" * 60)

    client = DeepSeekClient()

    # Simple test data
    portfolio = {
        "equity": 10000,
        "available": 9000,
        "exposure_pct": 10
    }

    market_data = {
        "symbol": "BTC",
        "price": 95000,
        "change_24h": 2.5
    }

    indicators = {
        "rsi": 55,
        "macd": 100,
        "macd_signal": 90,
        "ema20": 94000,
        "ema2": 95100
    }

    pivot_points = {
        "pp": 95000,
        "r1": 96000,
        "s1": 94000
    }

    forecast = {
        "trend": "bullish",
        "target_price": 96000,
        "change_pct": 1.05
    }

    orderbook = {
        "bid_volume": 1000000,
        "ask_volume": 900000,
        "ratio": 1.11
    }

    sentiment = {
        "label": "GREED",
        "score": 65
    }

    try:
        print("\nCalling get_trading_decision...")
        decision = client.get_trading_decision(
            symbol="BTC",
            portfolio=portfolio,
            market_data=market_data,
            indicators=indicators,
            pivot_points=pivot_points,
            forecast=forecast,
            orderbook=orderbook,
            sentiment=sentiment,
            news=[],
            open_positions=[],
            whale_flow=None,
            coingecko=None,
            exchange="alpaca"
        )

        print("\n" + "=" * 60)
        print("DECISION RECEIVED:")
        print("=" * 60)
        print(f"Action: {decision.get('action')}")
        print(f"Direction: {decision.get('direction')}")
        print(f"Confidence: {decision.get('confidence')}")
        print(f"Reasoning: {decision.get('reasoning', '')[:200]}...")
        print("=" * 60)

        if decision.get('action') == 'hold' and 'Default hold due to' in decision.get('reasoning', ''):
            print("\n❌ ERROR: Got default hold response!")
            print("This means the LLM call failed or response couldn't be parsed.")
            return False
        else:
            print("\n✅ SUCCESS: Got valid decision from LLM!")
            return True

    except Exception as e:
        print(f"\n❌ EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()

if __name__ == "__main__":
    print("\n🔍 DeepSeek LLM Debug Test\n")
    print(f"API Key: {settings.DEEPSEEK_API_KEY[:20]}... (masked)")
    print(f"Base URL: {settings.DEEPSEEK_BASE_URL}")
    print(f"Model: {settings.MODEL_NAME}\n")

    success = test_simple_call()

    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed - check logs above for details")
        sys.exit(1)
