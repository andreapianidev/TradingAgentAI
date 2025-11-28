"""
Cost tracking utilities for LLM API calls and trading fees.
"""
from typing import Dict, Any, Tuple
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# DeepSeek pricing (USD per token) - as of 2024
DEEPSEEK_PRICING = {
    "input": 0.14 / 1_000_000,      # $0.14 per 1M tokens
    "output": 0.28 / 1_000_000,     # $0.28 per 1M tokens
    "cached": 0.014 / 1_000_000,    # $0.014 per 1M tokens (cache hits)
}

# Alpaca crypto fee rates
ALPACA_FEE_RATES = {
    "paper": 0.0,           # Paper trading: 0%
    "live_maker": 0.00075,  # 0.075%
    "live_taker": 0.00075,  # 0.075%
}


def calculate_llm_cost(
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0
) -> float:
    """
    Calculate LLM API cost in USD based on DeepSeek pricing.

    Args:
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens
        cached_tokens: Number of cached tokens (90% discount)

    Returns:
        Cost in USD
    """
    input_cost = input_tokens * DEEPSEEK_PRICING["input"]
    output_cost = output_tokens * DEEPSEEK_PRICING["output"]
    cached_cost = cached_tokens * DEEPSEEK_PRICING["cached"]
    return input_cost + output_cost + cached_cost


def calculate_trading_fee(
    trade_value_usd: float,
    is_paper: bool = True,
    fee_type: str = "taker"
) -> Tuple[float, float]:
    """
    Calculate Alpaca trading fee.

    Args:
        trade_value_usd: Total trade value in USD
        is_paper: Whether this is paper trading
        fee_type: 'maker' or 'taker'

    Returns:
        Tuple of (actual_fee, estimated_live_fee)
        - actual_fee: 0 for paper, real fee for live
        - estimated_live_fee: what fee would be in live trading
    """
    rate_key = f"live_{fee_type}"
    live_rate = ALPACA_FEE_RATES.get(rate_key, ALPACA_FEE_RATES["live_taker"])
    estimated_live_fee = trade_value_usd * live_rate

    if is_paper:
        return 0.0, estimated_live_fee
    else:
        return estimated_live_fee, estimated_live_fee


class CostTracker:
    """Tracks and aggregates costs during a trading cycle."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all counters for new cycle."""
        self.llm_calls = 0
        self.llm_input_tokens = 0
        self.llm_output_tokens = 0
        self.llm_cached_tokens = 0
        self.llm_total_cost = 0.0
        self.trading_fees_actual = 0.0
        self.trading_fees_estimated = 0.0
        self.trades_count = 0
        self.costs_by_symbol: Dict[str, Dict[str, float]] = {}

    def add_llm_cost(
        self,
        symbol: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0
    ) -> float:
        """
        Record an LLM API call cost.

        Returns:
            Cost in USD for this call
        """
        cost = calculate_llm_cost(input_tokens, output_tokens, cached_tokens)

        self.llm_calls += 1
        self.llm_input_tokens += input_tokens
        self.llm_output_tokens += output_tokens
        self.llm_cached_tokens += cached_tokens
        self.llm_total_cost += cost

        if symbol not in self.costs_by_symbol:
            self.costs_by_symbol[symbol] = {"llm": 0.0, "fees_actual": 0.0, "fees_estimated": 0.0}
        self.costs_by_symbol[symbol]["llm"] += cost

        logger.debug(f"LLM cost for {symbol}: ${cost:.6f} ({input_tokens} in, {output_tokens} out)")
        return cost

    def add_trading_fee(
        self,
        symbol: str,
        trade_value_usd: float,
        is_paper: bool = True
    ) -> Tuple[float, float]:
        """
        Record a trading fee.

        Returns:
            Tuple of (actual_fee, estimated_fee)
        """
        actual_fee, estimated_fee = calculate_trading_fee(trade_value_usd, is_paper)

        self.trades_count += 1
        self.trading_fees_actual += actual_fee
        self.trading_fees_estimated += estimated_fee

        if symbol not in self.costs_by_symbol:
            self.costs_by_symbol[symbol] = {"llm": 0.0, "fees_actual": 0.0, "fees_estimated": 0.0}
        self.costs_by_symbol[symbol]["fees_actual"] += actual_fee
        self.costs_by_symbol[symbol]["fees_estimated"] += estimated_fee

        logger.debug(f"Trading fee for {symbol}: actual=${actual_fee:.4f}, estimated=${estimated_fee:.4f}")
        return actual_fee, estimated_fee

    def get_summary(self) -> Dict[str, Any]:
        """Get cost summary for current cycle."""
        return {
            "llm_calls": self.llm_calls,
            "llm_input_tokens": self.llm_input_tokens,
            "llm_output_tokens": self.llm_output_tokens,
            "llm_cached_tokens": self.llm_cached_tokens,
            "llm_total_cost_usd": self.llm_total_cost,
            "trading_fees_actual_usd": self.trading_fees_actual,
            "trading_fees_estimated_usd": self.trading_fees_estimated,
            "trades_count": self.trades_count,
            "total_cost_usd": self.llm_total_cost + self.trading_fees_actual,
            "total_cost_with_estimated_fees_usd": self.llm_total_cost + self.trading_fees_estimated,
            "costs_by_symbol": self.costs_by_symbol
        }

    def log_summary(self):
        """Log the cost summary."""
        summary = self.get_summary()
        logger.info(
            f"Cycle costs: LLM=${summary['llm_total_cost_usd']:.4f} "
            f"({summary['llm_calls']} calls, {summary['llm_input_tokens']}+{summary['llm_output_tokens']} tokens), "
            f"Fees=${summary['trading_fees_actual_usd']:.4f} (estimated: ${summary['trading_fees_estimated_usd']:.4f})"
        )


# Global instance for cycle tracking
cost_tracker = CostTracker()
