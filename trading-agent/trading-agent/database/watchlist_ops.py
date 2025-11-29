"""
Database operations for trading_watchlist table.
Manages cryptocurrency watchlist with opportunity scores and allocation tracking.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class WatchlistOperations:
    """Database operations for trading_watchlist table."""

    def __init__(self):
        """Initialize watchlist operations."""
        self._client = None

    def _get_client(self):
        """Get Supabase client (lazy initialization)."""
        if self._client is None:
            try:
                from supabase import create_client
                url = settings.SUPABASE_URL
                key = settings.SUPABASE_SERVICE_KEY

                if not url or not key:
                    logger.error("Supabase credentials not configured")
                    return None

                self._client = create_client(url, key)
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                return None

        return self._client

    def save_watchlist_entry(
        self,
        symbol: str,
        tier: str,
        evaluation: Dict[str, Any],
        allocation: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Save or update a watchlist entry.

        Args:
            symbol: Crypto symbol (e.g., "BTC", "DOGE")
            tier: Position tier ("CORE", "OPPORTUNISTIC", "SATELLITE")
            evaluation: Evaluation result from CryptoEvaluator
            allocation: Allocation info from PortfolioAllocator (optional)

        Returns:
            Entry ID if successful, None otherwise
        """
        client = self._get_client()
        if not client:
            return None

        try:
            # Check if entry already exists
            existing = client.table('trading_watchlist').select('id').eq('symbol', symbol).eq('is_active', True).execute()

            entry_data = {
                'symbol': symbol,
                'tier': tier,
                'is_active': True,
                'opportunity_score': evaluation.get('overall_score'),
                'opportunity_level': evaluation.get('opportunity_level'),
                'technical_score': evaluation.get('scores', {}).get('technical'),
                'sentiment_score': evaluation.get('scores', {}).get('sentiment'),
                'trending_score': evaluation.get('scores', {}).get('trending'),
                'liquidity_score': evaluation.get('scores', {}).get('liquidity'),
                'volatility_score': evaluation.get('scores', {}).get('volatility'),
                'news_score': evaluation.get('scores', {}).get('news'),
                'criteria_met': json.dumps(evaluation.get('criteria_met', {})),
                'reasoning': evaluation.get('reasoning', []),
                'raw_evaluation_data': json.dumps(evaluation),
                'last_evaluated_at': datetime.utcnow().isoformat(),
            }

            # Add allocation data if provided
            if allocation:
                entry_data['target_allocation_usd'] = allocation.get('target_usd')
                entry_data['current_allocation_usd'] = allocation.get('current_usd')
                entry_data['recommended_action'] = allocation.get('action')

            if existing.data and len(existing.data) > 0:
                # Update existing entry
                result = client.table('trading_watchlist').update(entry_data).eq('id', existing.data[0]['id']).execute()
                logger.info(f"Updated watchlist entry for {symbol} (tier: {tier}, score: {evaluation.get('overall_score'):.1f})")
                return existing.data[0]['id']
            else:
                # Insert new entry
                entry_data['added_at'] = datetime.utcnow().isoformat()
                result = client.table('trading_watchlist').insert(entry_data).execute()
                logger.info(f"Added new watchlist entry for {symbol} (tier: {tier}, score: {evaluation.get('overall_score'):.1f})")
                return result.data[0]['id'] if result.data else None

        except Exception as e:
            logger.error(f"Failed to save watchlist entry for {symbol}: {e}")
            return None

    def get_active_watchlist(self, tier: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all active watchlist entries.

        Args:
            tier: Optional filter by tier ("CORE", "OPPORTUNISTIC", "SATELLITE")

        Returns:
            List of watchlist entries
        """
        client = self._get_client()
        if not client:
            return []

        try:
            query = client.table('trading_watchlist').select('*').eq('is_active', True)

            if tier:
                query = query.eq('tier', tier)

            result = query.order('opportunity_score', desc=True).execute()

            if result.data:
                logger.info(f"Retrieved {len(result.data)} active watchlist entries" + (f" (tier: {tier})" if tier else ""))
                return result.data

            return []

        except Exception as e:
            logger.error(f"Failed to get active watchlist: {e}")
            return []

    def get_symbols_by_tier(self, tier: str) -> List[str]:
        """
        Get list of symbols for a specific tier.

        Args:
            tier: Position tier ("CORE", "OPPORTUNISTIC", "SATELLITE")

        Returns:
            List of symbols
        """
        entries = self.get_active_watchlist(tier=tier)
        return [entry['symbol'] for entry in entries]

    def remove_from_watchlist(self, symbol: str, reason: str = "") -> bool:
        """
        Deactivate a watchlist entry (soft delete).

        Args:
            symbol: Crypto symbol to remove
            reason: Optional reason for removal

        Returns:
            True if successful
        """
        client = self._get_client()
        if not client:
            return False

        try:
            result = client.table('trading_watchlist').update({
                'is_active': False,
                'removed_at': datetime.utcnow().isoformat(),
            }).eq('symbol', symbol).eq('is_active', True).execute()

            logger.info(f"Removed {symbol} from watchlist" + (f": {reason}" if reason else ""))

            # Log alert for removal
            self._log_watchlist_alert(symbol, "REMOVED", reason)

            return True

        except Exception as e:
            logger.error(f"Failed to remove {symbol} from watchlist: {e}")
            return False

    def update_allocation(
        self,
        symbol: str,
        target_usd: float,
        current_usd: float,
        action: str
    ) -> bool:
        """
        Update allocation info for a watchlist entry.

        Args:
            symbol: Crypto symbol
            target_usd: Target allocation in USD
            current_usd: Current allocation in USD
            action: Recommended action (OPEN, INCREASE, DECREASE, CLOSE, HOLD)

        Returns:
            True if successful
        """
        client = self._get_client()
        if not client:
            return False

        try:
            result = client.table('trading_watchlist').update({
                'target_allocation_usd': target_usd,
                'current_allocation_usd': current_usd,
                'recommended_action': action,
            }).eq('symbol', symbol).eq('is_active', True).execute()

            return bool(result.data)

        except Exception as e:
            logger.error(f"Failed to update allocation for {symbol}: {e}")
            return False

    def get_watchlist_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for the watchlist.

        Returns:
            Dictionary with summary stats
        """
        client = self._get_client()
        if not client:
            return {}

        try:
            active = self.get_active_watchlist()

            core_count = sum(1 for e in active if e['tier'] == 'CORE')
            opportunistic_count = sum(1 for e in active if e['tier'] == 'OPPORTUNISTIC')

            total_target_allocation = sum(
                float(e.get('target_allocation_usd', 0) or 0) for e in active
            )
            total_current_allocation = sum(
                float(e.get('current_allocation_usd', 0) or 0) for e in active
            )

            avg_opportunity_score = (
                sum(float(e.get('opportunity_score', 0) or 0) for e in active) / len(active)
                if active else 0
            )

            return {
                'total_active': len(active),
                'core_count': core_count,
                'opportunistic_count': opportunistic_count,
                'total_target_allocation_usd': total_target_allocation,
                'total_current_allocation_usd': total_current_allocation,
                'avg_opportunity_score': avg_opportunity_score,
                'timestamp': datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get watchlist summary: {e}")
            return {}

    def _log_watchlist_alert(self, symbol: str, alert_type: str, message: str):
        """
        Log an alert for watchlist changes.

        Args:
            symbol: Crypto symbol
            alert_type: Type of alert (ADDED, REMOVED, SCORE_CHANGED)
            message: Alert message
        """
        client = self._get_client()
        if not client:
            return

        try:
            client.table('trading_alerts').insert({
                'alert_type': f'WATCHLIST_{alert_type}',
                'severity': 'info',
                'message': f"{symbol}: {message}",
                'metadata': json.dumps({'symbol': symbol, 'alert_type': alert_type}),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log watchlist alert: {e}")


# Global instance
watchlist_ops = WatchlistOperations()


def save_to_watchlist(
    symbol: str,
    tier: str,
    evaluation: Dict[str, Any],
    allocation: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """Convenience function to save watchlist entry."""
    return watchlist_ops.save_watchlist_entry(symbol, tier, evaluation, allocation)


def get_active_watchlist(tier: Optional[str] = None) -> List[Dict[str, Any]]:
    """Convenience function to get active watchlist."""
    return watchlist_ops.get_active_watchlist(tier)


def remove_from_watchlist(symbol: str, reason: str = "") -> bool:
    """Convenience function to remove from watchlist."""
    return watchlist_ops.remove_from_watchlist(symbol, reason)
