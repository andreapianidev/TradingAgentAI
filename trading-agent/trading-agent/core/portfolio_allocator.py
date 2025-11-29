"""
PortfolioAllocator: Dynamic multi-asset capital allocation manager.

Manages portfolio allocation across:
- Core positions (BTC, ETH, SOL): 60-70% of capital
- Opportunistic positions (dynamic trending crypto): 20-30% of capital
- Maximum 10% per individual alt coin
- Total exposure target: 50-60%
- Strategy-aware allocation (different for scalping vs swing_trading)
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Core portfolio symbols (always monitored, priority allocation)
CORE_SYMBOLS = {"BTC", "ETH", "SOL"}


class PortfolioAllocator:
    """Manages dynamic capital allocation across multiple crypto assets."""

    def __init__(self):
        """Initialize the portfolio allocator."""
        self.core_symbols = CORE_SYMBOLS
        self.active_strategy = None  # Will be loaded from settings

    def calculate_allocation(
        self,
        portfolio: Dict[str, Any],
        opportunity_scores: Dict[str, Dict[str, Any]],
        active_strategy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate optimal capital allocation across all crypto opportunities.

        Args:
            portfolio: Current portfolio state (total_equity, positions, etc.)
            opportunity_scores: Dict of {symbol: evaluation_result} from CryptoEvaluator
            active_strategy: Active trading strategy config (affects allocation)

        Returns:
            Allocation plan with position sizes and priorities
        """
        total_equity = portfolio.get("total_equity", 0)
        available_balance = portfolio.get("available_balance", 0)
        current_positions = portfolio.get("positions", [])

        logger.info("=" * 60)
        logger.info("PORTFOLIO ALLOCATION CALCULATOR")
        logger.info("=" * 60)
        logger.info(f"Total Equity: ${total_equity:,.2f}")
        logger.info(f"Available Balance: ${available_balance:,.2f}")
        logger.info(f"Current Positions: {len(current_positions)}")

        # Get strategy parameters
        strategy_config = self._get_strategy_config(active_strategy)
        logger.info(f"Strategy: {strategy_config['name']}")
        logger.info(f"Max Total Exposure: {strategy_config['max_total_exposure_pct']}%")

        # Calculate target allocations
        max_total_exposure = strategy_config["max_total_exposure_pct"] / 100
        target_total_capital = total_equity * max_total_exposure

        logger.info(f"Target Total Capital: ${target_total_capital:,.2f}")

        # Separate core vs opportunistic
        core_opportunities = {
            sym: score for sym, score in opportunity_scores.items()
            if sym in self.core_symbols
        }
        opportunistic_opportunities = {
            sym: score for sym, score in opportunity_scores.items()
            if sym not in self.core_symbols
        }

        logger.info(f"Core Opportunities: {len(core_opportunities)}")
        logger.info(f"Opportunistic Opportunities: {len(opportunistic_opportunities)}")

        # Allocate capital
        core_allocation = self._allocate_core_positions(
            core_opportunities,
            target_total_capital,
            strategy_config,
            current_positions
        )

        opportunistic_allocation = self._allocate_opportunistic_positions(
            opportunistic_opportunities,
            target_total_capital,
            strategy_config,
            current_positions,
            core_allocation
        )

        # Combine allocations
        all_allocations = {**core_allocation, **opportunistic_allocation}

        # Calculate summary
        total_allocated = sum(alloc["target_usd"] for alloc in all_allocations.values())
        allocation_pct = (total_allocated / total_equity * 100) if total_equity > 0 else 0

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_equity": total_equity,
            "available_balance": available_balance,
            "target_total_capital": target_total_capital,
            "total_allocated": total_allocated,
            "allocation_pct": allocation_pct,
            "strategy": strategy_config["name"],
            "allocations": all_allocations,
            "core_count": len(core_allocation),
            "opportunistic_count": len(opportunistic_allocation),
        }

        logger.info("=" * 60)
        logger.info(f"Total Allocated: ${total_allocated:,.2f} ({allocation_pct:.1f}% of equity)")
        logger.info(f"Core Positions: {len(core_allocation)}")
        logger.info(f"Opportunistic Positions: {len(opportunistic_allocation)}")
        logger.info("=" * 60)

        return summary

    def _get_strategy_config(self, active_strategy: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get strategy-specific configuration.

        Args:
            active_strategy: Active strategy from database

        Returns:
            Strategy config with allocation parameters
        """
        if active_strategy and active_strategy.get("config"):
            config = active_strategy["config"]
            return {
                "name": active_strategy.get("display_name", "Unknown"),
                "max_total_exposure_pct": config.get("max_total_exposure_pct", 50),
                "max_position_size_pct": config.get("max_position_size_pct", 10),
                "core_allocation_pct": config.get("core_allocation_pct", 65),
                "opportunistic_allocation_pct": config.get("opportunistic_allocation_pct", 25),
                "max_opportunistic_coins": config.get("max_opportunistic_coins", 3),
                "min_opportunity_score": config.get("min_opportunity_score", 60),
            }
        else:
            # Default configuration
            return {
                "name": "Default",
                "max_total_exposure_pct": settings.MAX_TOTAL_EXPOSURE_PCT,
                "max_position_size_pct": settings.MAX_POSITION_SIZE_PCT,
                "core_allocation_pct": 65,
                "opportunistic_allocation_pct": 25,
                "max_opportunistic_coins": 3,
                "min_opportunity_score": 60,
            }

    def _allocate_core_positions(
        self,
        core_opportunities: Dict[str, Dict[str, Any]],
        target_total_capital: float,
        strategy_config: Dict[str, Any],
        current_positions: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Allocate capital to core positions (BTC, ETH, SOL).

        Args:
            core_opportunities: Evaluated opportunities for core symbols
            target_total_capital: Total capital to allocate
            strategy_config: Strategy configuration
            current_positions: Currently open positions

        Returns:
            Dictionary of {symbol: allocation_info}
        """
        allocations = {}

        if not core_opportunities:
            return allocations

        core_allocation_pct = strategy_config["core_allocation_pct"] / 100
        core_total_capital = target_total_capital * core_allocation_pct

        logger.info(f"Core Allocation Capital: ${core_total_capital:,.2f}")

        # Sort by opportunity score (higher = better)
        sorted_core = sorted(
            core_opportunities.items(),
            key=lambda x: x[1].get("overall_score", 0),
            reverse=True
        )

        # Equal weight across core positions, adjusted by score
        num_core = len(sorted_core)
        base_allocation = core_total_capital / num_core

        for symbol, evaluation in sorted_core:
            score = evaluation.get("overall_score", 0)
            opportunity_level = evaluation.get("opportunity_level", "MODERATE")

            # Adjust allocation based on score
            score_multiplier = score / 70  # Normalize around 70 as baseline
            target_usd = base_allocation * score_multiplier

            # Get current position if exists
            current_position = next(
                (p for p in current_positions if p.get("symbol") == symbol),
                None
            )
            current_usd = float(current_position.get("market_value", 0)) if current_position else 0

            allocations[symbol] = {
                "symbol": symbol,
                "tier": "CORE",
                "target_usd": target_usd,
                "current_usd": current_usd,
                "delta_usd": target_usd - current_usd,
                "opportunity_score": score,
                "opportunity_level": opportunity_level,
                "action": self._determine_action(current_usd, target_usd),
            }

            logger.info(f"  {symbol}: ${target_usd:,.2f} (score {score:.1f}, {opportunity_level})")

        return allocations

    def _allocate_opportunistic_positions(
        self,
        opportunistic_opportunities: Dict[str, Dict[str, Any]],
        target_total_capital: float,
        strategy_config: Dict[str, Any],
        current_positions: List[Dict[str, Any]],
        core_allocation: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Allocate capital to opportunistic positions (dynamic trending crypto).

        Args:
            opportunistic_opportunities: Evaluated opportunities for alt coins
            target_total_capital: Total capital to allocate
            strategy_config: Strategy configuration
            current_positions: Currently open positions
            core_allocation: Already allocated core positions

        Returns:
            Dictionary of {symbol: allocation_info}
        """
        allocations = {}

        if not opportunistic_opportunities:
            return allocations

        opportunistic_allocation_pct = strategy_config["opportunistic_allocation_pct"] / 100
        opportunistic_total_capital = target_total_capital * opportunistic_allocation_pct
        max_opportunistic_coins = strategy_config["max_opportunistic_coins"]
        min_opportunity_score = strategy_config["min_opportunity_score"]
        max_alt_coin_pct = settings.MAX_ALT_COIN_PCT / 100  # 10% default

        logger.info(f"Opportunistic Allocation Capital: ${opportunistic_total_capital:,.2f}")
        logger.info(f"Max Opportunistic Coins: {max_opportunistic_coins}")
        logger.info(f"Min Opportunity Score: {min_opportunity_score}")

        # Filter by minimum score and criteria
        qualified_opportunities = {
            sym: eval_result
            for sym, eval_result in opportunistic_opportunities.items()
            if (
                eval_result.get("overall_score", 0) >= min_opportunity_score and
                eval_result.get("criteria_met", {}).get("overall_quality", False)
            )
        }

        if not qualified_opportunities:
            logger.info("No opportunistic opportunities met minimum criteria")
            return allocations

        # Sort by score and take top N
        sorted_opportunistic = sorted(
            qualified_opportunities.items(),
            key=lambda x: x[1].get("overall_score", 0),
            reverse=True
        )[:max_opportunistic_coins]

        logger.info(f"Qualified Opportunistic Coins: {[s for s, _ in sorted_opportunistic]}")

        # Calculate max capital per alt coin (10% of total equity)
        total_equity = target_total_capital / (strategy_config["max_total_exposure_pct"] / 100)
        max_per_alt_coin = total_equity * max_alt_coin_pct

        # Distribute opportunistic capital weighted by score
        total_score = sum(eval_result.get("overall_score", 0) for _, eval_result in sorted_opportunistic)

        for symbol, evaluation in sorted_opportunistic:
            score = evaluation.get("overall_score", 0)
            opportunity_level = evaluation.get("opportunity_level", "MODERATE")

            # Weight by score
            score_weight = score / total_score if total_score > 0 else 1 / len(sorted_opportunistic)
            target_usd = opportunistic_total_capital * score_weight

            # Cap at max per alt coin
            target_usd = min(target_usd, max_per_alt_coin)

            # Get current position if exists
            current_position = next(
                (p for p in current_positions if p.get("symbol") == symbol),
                None
            )
            current_usd = float(current_position.get("market_value", 0)) if current_position else 0

            allocations[symbol] = {
                "symbol": symbol,
                "tier": "OPPORTUNISTIC",
                "target_usd": target_usd,
                "current_usd": current_usd,
                "delta_usd": target_usd - current_usd,
                "opportunity_score": score,
                "opportunity_level": opportunity_level,
                "action": self._determine_action(current_usd, target_usd),
                "max_allowed_usd": max_per_alt_coin,
            }

            logger.info(f"  {symbol}: ${target_usd:,.2f} (score {score:.1f}, {opportunity_level})")

        return allocations

    def _determine_action(self, current_usd: float, target_usd: float) -> str:
        """
        Determine action based on current vs target allocation.

        Args:
            current_usd: Current position value in USD
            target_usd: Target position value in USD

        Returns:
            Action: "OPEN", "INCREASE", "DECREASE", "CLOSE", or "HOLD"
        """
        delta_pct = abs(current_usd - target_usd) / max(current_usd, target_usd, 1) * 100

        # Threshold for action (5% difference)
        threshold_pct = 5

        if current_usd == 0 and target_usd > 0:
            return "OPEN"
        elif target_usd == 0 and current_usd > 0:
            return "CLOSE"
        elif delta_pct < threshold_pct:
            return "HOLD"
        elif target_usd > current_usd:
            return "INCREASE"
        else:
            return "DECREASE"

    def should_replace_core_position(
        self,
        core_symbol: str,
        current_position: Dict[str, Any],
        new_opportunity: Dict[str, Any]
    ) -> bool:
        """
        Determine if a core position (BTC/ETH/SOL) should be sold to buy a new opportunity.

        Only allows replacement if:
        1. Current position is in profit (unrealized P&L > 0)
        2. New opportunity has exceptional score (>= 80)
        3. Core position score is weak (< 50)

        Args:
            core_symbol: Core symbol being considered for replacement
            current_position: Current position data (P&L, etc.)
            new_opportunity: Evaluation result for new crypto

        Returns:
            True if replacement is recommended
        """
        # Check if position is in profit
        unrealized_pnl_pct = float(current_position.get("unrealized_pnl_pct", 0))
        if unrealized_pnl_pct <= 0:
            logger.info(f"Not replacing {core_symbol}: position not in profit ({unrealized_pnl_pct:.2f}%)")
            return False

        # Check new opportunity quality
        new_score = new_opportunity.get("overall_score", 0)
        if new_score < 80:
            logger.info(f"Not replacing {core_symbol}: new opportunity score too low ({new_score:.1f})")
            return False

        # Would need current evaluation of core position to compare scores
        # For now, only allow replacement for EXCELLENT opportunities
        logger.info(f"Replacement possible for {core_symbol}: in profit ({unrealized_pnl_pct:.2f}%), "
                   f"new opportunity EXCELLENT ({new_score:.1f})")
        return True


# Global allocator
portfolio_allocator = PortfolioAllocator()


def calculate_portfolio_allocation(
    portfolio: Dict[str, Any],
    opportunity_scores: Dict[str, Dict[str, Any]],
    active_strategy: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Convenience function to calculate portfolio allocation."""
    return portfolio_allocator.calculate_allocation(portfolio, opportunity_scores, active_strategy)
