"""
Unit tests for PortfolioAllocator - Dynamic capital allocation manager.

Tests cover:
- Core allocation (BTC/ETH/SOL) - 65% of capital
- Opportunistic allocation (trending coins) - 25% of capital
- Score multiplier formula (score/70)
- Max per-coin cap enforcement (10% of equity)
- Tier classification (CORE/OPPORTUNISTIC)
- Action determination (OPEN/CLOSE/INCREASE/DECREASE/HOLD)
- Portfolio exposure limits
- Edge cases (zero equity, no opportunities, division by zero)
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestPortfolioAllocatorCoreAllocation:
    """Test core position allocation (BTC/ETH/SOL) - 65% of capital."""

    def test_core_allocation_equal_distribution(self):
        """Test core positions get equal base allocation."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        # All core symbols with equal scores
        opportunity_scores = {
            "BTC": {"opportunity_score": 70, "opportunity_level": "GOOD"},
            "ETH": {"opportunity_score": 70, "opportunity_level": "GOOD"},
            "SOL": {"opportunity_score": 70, "opportunity_level": "GOOD"}
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        # Each core should get ~33% of core allocation (65% / 3)
        core_allocations = [
            result["allocations"]["BTC"]["target_usd"],
            result["allocations"]["ETH"]["target_usd"],
            result["allocations"]["SOL"]["target_usd"]
        ]

        # Verify roughly equal
        assert all(2000 <= alloc <= 2500 for alloc in core_allocations)

    def test_core_allocation_score_multiplier(self):
        """Test score multiplier (score/70) adjusts allocation."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        # BTC high score, ETH/SOL lower
        opportunity_scores = {
            "BTC": {"opportunity_score": 84, "opportunity_level": "EXCELLENT"},  # 84/70 = 1.2x
            "ETH": {"opportunity_score": 56, "opportunity_level": "MODERATE"},  # 56/70 = 0.8x
            "SOL": {"opportunity_score": 70, "opportunity_level": "GOOD"}  # 70/70 = 1.0x
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        btc_allocation = result["allocations"]["BTC"]["target_usd"]
        eth_allocation = result["allocations"]["ETH"]["target_usd"]
        sol_allocation = result["allocations"]["SOL"]["target_usd"]

        # BTC should get more than SOL, SOL more than ETH
        assert btc_allocation > sol_allocation > eth_allocation

    def test_core_allocation_respects_max_exposure(self):
        """Test total allocation doesn't exceed max_total_exposure."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 80},
            "ETH": {"opportunity_score": 75},
            "SOL": {"opportunity_score": 70}
        }

        active_strategy = {
            "max_total_exposure_pct": 50.0  # Max 50% exposure
        }

        result = allocator.calculate_allocation(
            portfolio,
            opportunity_scores,
            active_strategy=active_strategy
        )

        total_allocated = sum(
            alloc["target_usd"]
            for alloc in result["allocations"].values()
        )

        # Should not exceed 50% of $10,000 = $5,000
        assert total_allocated <= 5000


class TestPortfolioAllocatorOpportunisticAllocation:
    """Test opportunistic allocation (trending coins) - 25% of capital."""

    def test_opportunistic_allocation_top_coins(self):
        """Test selects top N opportunistic coins by score."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 70, "tier": "CORE"},
            "ETH": {"opportunity_score": 68, "tier": "CORE"},
            "SOL": {"opportunity_score": 65, "tier": "CORE"},
            "DOGE": {"opportunity_score": 75, "tier": "OPPORTUNISTIC", "criteria_met": {"overall_quality": True}},
            "LINK": {"opportunity_score": 72, "tier": "OPPORTUNISTIC", "criteria_met": {"overall_quality": True}},
            "XRP": {"opportunity_score": 68, "tier": "OPPORTUNISTIC", "criteria_met": {"overall_quality": True}},
            "PEPE": {"opportunity_score": 55, "tier": "OPPORTUNISTIC", "criteria_met": {"overall_quality": False}}
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        # Should pick top 3 opportunistic (DOGE, LINK, XRP)
        assert "DOGE" in result["allocations"]
        assert "LINK" in result["allocations"]
        assert "XRP" in result["allocations"]
        assert "PEPE" not in result["allocations"]  # Score too low or quality fail

    def test_opportunistic_max_per_coin_cap(self):
        """Test enforces 10% max allocation per alt coin."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        # Single opportunistic coin with very high score
        opportunity_scores = {
            "BTC": {"opportunity_score": 70},
            "ETH": {"opportunity_score": 70},
            "SOL": {"opportunity_score": 70},
            "DOGE": {"opportunity_score": 95, "criteria_met": {"overall_quality": True}}
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        doge_allocation = result["allocations"]["DOGE"]["target_usd"]

        # Should not exceed 10% of $10,000 = $1,000
        assert doge_allocation <= 1000

    def test_opportunistic_score_weighted_distribution(self):
        """Test allocation is score-weighted among opportunistic coins."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 70},
            "ETH": {"opportunity_score": 70},
            "SOL": {"opportunity_score": 70},
            "DOGE": {"opportunity_score": 80, "criteria_met": {"overall_quality": True}},
            "LINK": {"opportunity_score": 60, "criteria_met": {"overall_quality": True}}
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        doge_allocation = result["allocations"]["DOGE"]["target_usd"]
        link_allocation = result["allocations"]["LINK"]["target_usd"]

        # DOGE (score 80) should get more than LINK (score 60)
        assert doge_allocation > link_allocation

    def test_opportunistic_filters_low_quality(self):
        """Test filters out coins that don't meet quality criteria."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 70},
            "DOGE": {
                "opportunity_score": 75,
                "criteria_met": {"overall_quality": False}  # Fails quality check
            },
            "LINK": {
                "opportunity_score": 72,
                "criteria_met": {"overall_quality": True}
            }
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        # DOGE should be excluded
        assert "DOGE" not in result["allocations"] or result["allocations"]["DOGE"]["target_usd"] == 0
        # LINK should be included
        assert "LINK" in result["allocations"]


class TestPortfolioAllocatorActionDetermination:
    """Test action determination (OPEN/CLOSE/INCREASE/DECREASE/HOLD)."""

    def test_action_open_new_position(self):
        """Test OPEN action when current=0 and target>0."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []  # No current positions
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 75}
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        assert result["allocations"]["BTC"]["action"] == "OPEN"

    def test_action_close_position(self):
        """Test CLOSE action when current>0 and target=0."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 8000,
            "positions": [
                {"symbol": "BTC", "market_value": 2000}
            ]
        }

        # BTC score too low to keep
        opportunity_scores = {
            "BTC": {"opportunity_score": 30}  # Below threshold
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        assert result["allocations"]["BTC"]["action"] == "CLOSE"

    def test_action_increase_position(self):
        """Test INCREASE action when target > current (>5% delta)."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 8000,
            "positions": [
                {"symbol": "BTC", "market_value": 1000}
            ]
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 80}  # High score, increase allocation
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        if result["allocations"]["BTC"]["target_usd"] > 1050:  # >5% increase
            assert result["allocations"]["BTC"]["action"] == "INCREASE"

    def test_action_decrease_position(self):
        """Test DECREASE action when target < current (>5% delta)."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 7000,
            "positions": [
                {"symbol": "BTC", "market_value": 3000}
            ]
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 60}  # Lower score, reduce allocation
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        if result["allocations"]["BTC"]["target_usd"] < 2850:  # >5% decrease
            assert result["allocations"]["BTC"]["action"] == "DECREASE"

    def test_action_hold_position(self):
        """Test HOLD action when delta < 5%."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 8000,
            "positions": [
                {"symbol": "BTC", "market_value": 2000}
            ]
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 70}  # Similar to current
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        # If target is within 5% of current (1900-2100), should HOLD
        target = result["allocations"]["BTC"]["target_usd"]
        if 1900 <= target <= 2100:
            assert result["allocations"]["BTC"]["action"] == "HOLD"


class TestPortfolioAllocatorTierClassification:
    """Test tier classification (CORE/OPPORTUNISTIC)."""

    def test_tier_core_symbols(self):
        """Test BTC/ETH/SOL always classified as CORE."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 70},
            "ETH": {"opportunity_score": 65},
            "SOL": {"opportunity_score": 68}
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        assert result["allocations"]["BTC"]["tier"] == "CORE"
        assert result["allocations"]["ETH"]["tier"] == "CORE"
        assert result["allocations"]["SOL"]["tier"] == "CORE"

    def test_tier_opportunistic_symbols(self):
        """Test non-core symbols classified as OPPORTUNISTIC."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 70},
            "DOGE": {"opportunity_score": 75, "criteria_met": {"overall_quality": True}},
            "LINK": {"opportunity_score": 72, "criteria_met": {"overall_quality": True}}
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        if "DOGE" in result["allocations"]:
            assert result["allocations"]["DOGE"]["tier"] == "OPPORTUNISTIC"
        if "LINK" in result["allocations"]:
            assert result["allocations"]["LINK"]["tier"] == "OPPORTUNISTIC"


class TestPortfolioAllocatorStrategyIntegration:
    """Test strategy-aware allocation."""

    def test_strategy_overrides_exposure(self):
        """Test active strategy overrides default exposure limits."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 75},
            "ETH": {"opportunity_score": 70}
        }

        active_strategy = {
            "max_total_exposure_pct": 30.0  # Conservative 30% max
        }

        result = allocator.calculate_allocation(
            portfolio,
            opportunity_scores,
            active_strategy=active_strategy
        )

        total_allocated = sum(
            alloc["target_usd"]
            for alloc in result["allocations"].values()
        )

        # Should respect strategy limit of 30%
        assert total_allocated <= 3000

    def test_strategy_position_size_limit(self):
        """Test strategy max_position_size_pct applies."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 90}
        }

        active_strategy = {
            "max_position_size_pct": 15.0  # Max 15% per position
        }

        result = allocator.calculate_allocation(
            portfolio,
            opportunity_scores,
            active_strategy=active_strategy
        )

        btc_allocation = result["allocations"]["BTC"]["target_usd"]

        # Should not exceed 15% of $10,000 = $1,500
        assert btc_allocation <= 1500


class TestPortfolioAllocatorEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_equity(self):
        """Test handles zero equity gracefully."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 0,
            "available_balance": 0,
            "positions": []
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 75}
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        # Should return zero allocations
        assert result["allocations"]["BTC"]["target_usd"] == 0

    def test_no_opportunities(self):
        """Test handles empty opportunity scores."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        opportunity_scores = {}

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        assert result["allocations"] == {}

    def test_all_scores_below_threshold(self):
        """Test when all scores below min_opportunity_score."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        # All scores below 60 (default threshold)
        opportunity_scores = {
            "BTC": {"opportunity_score": 45},
            "ETH": {"opportunity_score": 50},
            "SOL": {"opportunity_score": 55}
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        # Should still allocate to core (even if scores low)
        # But opportunistic should be filtered
        assert "BTC" in result["allocations"]

    def test_division_by_zero_protection(self):
        """Test protects against division by zero."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        # All scores zero
        opportunity_scores = {
            "BTC": {"opportunity_score": 0},
            "ETH": {"opportunity_score": 0},
            "SOL": {"opportunity_score": 0}
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        # Should not crash
        assert "allocations" in result

    def test_current_positions_preservation(self):
        """Test doesn't lose track of current positions."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 7000,
            "positions": [
                {"symbol": "BTC", "market_value": 2000},
                {"symbol": "ETH", "market_value": 1000}
            ]
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 70},
            "ETH": {"opportunity_score": 65},
            "SOL": {"opportunity_score": 68}
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        # Should include current positions in allocation
        assert "BTC" in result["allocations"]
        assert "ETH" in result["allocations"]
        assert result["allocations"]["BTC"]["current_usd"] == 2000
        assert result["allocations"]["ETH"]["current_usd"] == 1000


class TestPortfolioAllocatorAllocationSummary:
    """Test allocation summary and metadata."""

    def test_summary_total_target(self):
        """Test summary includes total target allocation."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 75},
            "ETH": {"opportunity_score": 70},
            "SOL": {"opportunity_score": 68}
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        assert "summary" in result
        assert "total_target_usd" in result["summary"]
        assert result["summary"]["total_target_usd"] > 0

    def test_summary_tier_breakdown(self):
        """Test summary breaks down by tier."""
        from core.portfolio_allocator import PortfolioAllocator

        allocator = PortfolioAllocator()

        portfolio = {
            "total_equity": 10000,
            "available_balance": 10000,
            "positions": []
        }

        opportunity_scores = {
            "BTC": {"opportunity_score": 75},
            "ETH": {"opportunity_score": 70},
            "SOL": {"opportunity_score": 68},
            "DOGE": {"opportunity_score": 72, "criteria_met": {"overall_quality": True}}
        }

        result = allocator.calculate_allocation(portfolio, opportunity_scores)

        assert "core_allocation_usd" in result["summary"]
        assert "opportunistic_allocation_usd" in result["summary"]
