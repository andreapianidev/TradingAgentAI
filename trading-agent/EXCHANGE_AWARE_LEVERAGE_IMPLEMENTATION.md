# Exchange-Aware Leverage System - Implementation Summary

## Overview

Successfully implemented a comprehensive exchange-aware leverage system that adapts DeepSeek AI prompts and decision validation based on the active exchange (Alpaca vs Hyperliquid).

## User Preferences Selected

- **Leverage Strategy**: AGGRESSIVE (max 20x leverage)
- **Rollout Strategy**: IMMEDIATE (full power deployment)
- **Symbol-Specific Caps**:
  - BTC: 30x (most stable, blue-chip)
  - ETH: 25x (medium volatility)
  - SOL: 15x (high volatility)

## Implementation Details

### 1. Exchange-Aware Prompts (`config/prompts.py`)

**Added 3 leverage rules constants:**

- `ALPACA_LEVERAGE_RULES`: Forces leverage = 1 (spot trading only)
- `HYPERLIQUID_LEVERAGE_RULES_CONSERVATIVE`: Max 10x leverage with confidence-based tiers
- `HYPERLIQUID_LEVERAGE_RULES_AGGRESSIVE`: Max 20x leverage with aggressive confidence-based tiers

**Leverage Strategy (Aggressive):**
```
Confidence 0.60-0.69 → Leverage 2-5x   (setup moderato)
Confidence 0.70-0.79 → Leverage 5-10x  (setup forte)
Confidence 0.80-0.89 → Leverage 10-15x (setup eccellente)
Confidence 0.90-1.00 → Leverage 15-20x (setup perfetto, max leverage)
```

**Symbol-Specific Caps:**
- BTC: MAX 30x (più stabile, blue-chip)
- ETH: MAX 25x (volatilità media, liquido)
- SOL: MAX 15x (alta volatilità)

**Factory Function:**
- `_get_leverage_rules(exchange: str) -> str`: Selects appropriate rules based on exchange and strategy

**Modified Functions:**
- `get_system_prompt(exchange: str)`: Injects exchange-specific leverage rules
- `build_user_prompt(..., exchange: str)`: Includes exchange info in output
- `get_decision_correction_prompt(..., exchange: str)`: Exchange-aware corrections
- `get_system_prompt_for_scenario(..., exchange: str)`: Scenario-specific prompts with exchange context
- `build_user_prompt_with_scores(..., exchange: str)`: Enhanced prompts with exchange info

### 2. LLM Client Integration (`core/llm_client.py`)

**Changes:**
- Added `exchange` parameter to `get_trading_decision()`
- Added `exchange` parameter to `get_trading_decision_with_prompts()`
- All prompt builders now receive exchange context
- Removed duplicate method
- Exchange context flows through retry/correction logic

### 3. Agent Orchestration (`core/agent.py`)

**Changes:**
- Added `exchange` to portfolio context dictionary
- Passes `settings.EXCHANGE` to `get_system_prompt_for_scenario()`
- Passes `settings.EXCHANGE` to `build_user_prompt_with_scores()`
- Passes `settings.EXCHANGE` to `get_trading_decision_with_prompts()`

### 4. Leverage Settings (`config/settings.py`)

**New Settings:**
```python
LEVERAGE_STRATEGY: str = "aggressive"  # or "conservative"
MAX_LEVERAGE: int = 30                 # Overall max leverage cap
DEFAULT_LEVERAGE: int = 5              # Safe starting point

# Symbol-specific caps (Hyperliquid only)
MAX_LEVERAGE_BTC: int = 30
MAX_LEVERAGE_ETH: int = 25
MAX_LEVERAGE_SOL: int = 15
```

### 5. Decision Validation (`core/decision_validator.py`)

**New Method:**
- `_get_symbol_max_leverage(symbol: str) -> int`: Returns symbol-specific max leverage
  - Alpaca: Always returns 1
  - Hyperliquid: Returns BTC 30x, ETH 25x, SOL 15x

**Modified Methods:**
- `_sanitize_open()`: Exchange-aware leverage validation
  - Alpaca: Forces leverage to 1x
  - Hyperliquid: Validates and clamps to symbol-specific caps

**Enhanced Exposure Calculation:**
```python
# Real exposure = position_size_pct × leverage
effective_exposure = position_size_pct * leverage
total_exposure = current_exposure + effective_exposure
```

**High Exposure Protection:**
- When exposure > 25%, reduces leverage to max 5x for Hyperliquid
- Requires higher confidence for new positions

## Test Results

### ✅ Prompt Generation Tests
- Alpaca prompts include "no leverage" rules
- Hyperliquid prompts include aggressive leverage strategy
- All confidence-based tiers present
- Symbol-specific caps included
- Exchange info in user prompts

### ✅ Alpaca Backward Compatibility Tests
- Leverage forced to 1x (even when LLM suggests 20x)
- Symbol max leverage returns 1x for all symbols
- Exposure calculation works correctly with 1x
- High exposure scenarios handled properly
- Multiple positions supported

### ✅ Hyperliquid Leverage Tests
- Symbol-specific caps enforced (BTC 30x, ETH 25x, SOL 15x)
- Excessive leverage clamped to caps
- Effective exposure calculated correctly (size × leverage)
- Exposure limits enforced with leverage
- Leverage reduced at high exposure (>25% → max 5x)
- Valid leverage values preserved

## Key Features

### 1. Exchange Detection
The system automatically detects which exchange is active via `settings.EXCHANGE` and adapts:
- Prompts injected into DeepSeek AI
- Leverage validation rules
- Exposure calculations
- Symbol-specific caps

### 2. Risk Management
- **Alpaca**: Safe 1x spot trading (no leverage)
- **Hyperliquid**: Controlled leverage with multiple safety layers
  - Symbol-specific caps (more volatile = lower max leverage)
  - Confidence-based leverage selection (AI decides based on confidence)
  - Exposure limits (total portfolio exposure capped at 30%)
  - High exposure protection (reduces leverage when portfolio exposure > 25%)

### 3. Liquidation Risk Awareness
The AI is instructed about liquidation formulas:
```
Liquidation Distance = 100% / leverage

Examples:
- 2x leverage → liquidation at -50% move
- 5x leverage → liquidation at -20% move
- 10x leverage → liquidation at -10% move
- 20x leverage → liquidation at -5% move
```

### 4. ATR Volatility Adjustments
The AI is instructed to reduce leverage when ATR% > 6% (high volatility).

## Files Modified

1. `trading-agent/config/prompts.py` (lines 11-114, 117-141, 143+, 342+, 517+, 607+, 765+)
2. `trading-agent/core/llm_client.py` (lines 52+, 230+, 273+)
3. `trading-agent/core/agent.py` (lines 715-720, 728-732, 733-750, 753-758)
4. `trading-agent/config/settings.py` (lines 73-88)
5. `trading-agent/core/decision_validator.py` (lines 19-42, 115-141, 143-187, 258-264)

## Test Files Created

1. `trading-agent/test_exchange_prompts.py`: Validates prompt generation
2. `trading-agent/test_alpaca_compatibility.py`: Validates Alpaca backward compatibility
3. `trading-agent/test_hyperliquid_leverage.py`: Validates Hyperliquid leverage system

## How to Use

### Switch to Alpaca (Safe, No Leverage)
```bash
# In .env or Supabase settings
EXCHANGE=alpaca
```

### Switch to Hyperliquid (Leverage Enabled)
```bash
# In .env or Supabase settings
EXCHANGE=hyperliquid
LEVERAGE_STRATEGY=aggressive  # or "conservative"
MAX_LEVERAGE=30
MAX_LEVERAGE_BTC=30
MAX_LEVERAGE_ETH=25
MAX_LEVERAGE_SOL=15
```

## Benefits

1. **AI-Powered Leverage Selection**: DeepSeek AI selects leverage based on:
   - Trade confidence (0.6-1.0)
   - Market conditions (volatility, regime)
   - Technical indicators (RSI, MACD, etc.)
   - Symbol characteristics (BTC vs SOL)

2. **Maximum Safety**: Multiple validation layers:
   - AI prompt constraints
   - DecisionValidator enforcement
   - Symbol-specific caps
   - Exposure limits
   - High exposure protection

3. **Backward Compatible**: Alpaca users unaffected, system still forces 1x leverage

4. **Future-Ready**: Easy to add new exchanges by:
   - Adding leverage rules constant
   - Updating `_get_leverage_rules()` factory
   - Adding exchange-specific caps in settings

## Example Scenarios

### Scenario 1: High Confidence BTC Trade (Hyperliquid)
```
Confidence: 0.92
Symbol: BTC
AI Decision: leverage = 18x (within 15-20x tier for 0.90-1.00)
Validator: Accepts (under BTC cap of 30x)
Result: Position opened with 18x leverage
```

### Scenario 2: Moderate Confidence SOL Trade (Hyperliquid)
```
Confidence: 0.75
Symbol: SOL
AI Decision: leverage = 8x (within 5-10x tier for 0.70-0.79)
Validator: Accepts (under SOL cap of 15x)
Result: Position opened with 8x leverage
```

### Scenario 3: High Leverage Request Exceeds Cap (Hyperliquid)
```
Confidence: 0.95
Symbol: SOL
AI Decision: leverage = 18x (within 15-20x tier for 0.90-1.00)
Validator: Clamps to 15x (SOL cap)
Result: Position opened with 15x leverage (clamped)
```

### Scenario 4: Alpaca (Always 1x)
```
Confidence: 0.95
Symbol: BTC
AI Decision: leverage = 1x (Alpaca rules in prompt)
Validator: Confirms 1x (Alpaca forces 1x)
Result: Position opened with 1x leverage
```

## Next Steps

The system is fully implemented and tested. You can now:

1. **Test in Testnet**: Set `EXCHANGE=hyperliquid` and `HYPERLIQUID_TESTNET=true`
2. **Monitor First Trades**: Watch logs for leverage selection and validation
3. **Adjust Strategy**: Switch between "aggressive" and "conservative" if needed
4. **Fine-Tune Caps**: Adjust symbol-specific caps based on performance
5. **Add More Symbols**: Extend `_get_symbol_max_leverage()` for additional coins

## Summary

✅ Exchange-aware prompts fully implemented
✅ Leverage validation with symbol-specific caps
✅ Exposure calculation accounts for leverage
✅ All tests passing (prompts, Alpaca compatibility, Hyperliquid leverage)
✅ Backward compatible with existing Alpaca setup
✅ Ready for Hyperliquid deployment

The trading bot is now specialized for Hyperliquid with intelligent, AI-powered leverage selection while maintaining full Alpaca backward compatibility.
