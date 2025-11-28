"""
Whale Alert - Monitor large crypto transactions.
Uses reverse engineering of whale-alert.io public data.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import httpx

from config.constants import CACHE_WHALE_DURATION
from utils.logger import get_logger

logger = get_logger(__name__)


class WhaleAlertCollector:
    """
    Collects whale movement data from whale-alert.io.

    Uses reverse-engineered API endpoint instead of official API ($699/month).
    """

    def __init__(self):
        """Initialize the whale alert collector."""
        self.base_url = "https://api.whale-alert.io/feed"
        self._cache: List[Dict[str, Any]] = []
        self._cache_time: Optional[datetime] = None

    def get_recent_alerts(
        self,
        limit: int = 10,
        min_value_usd: float = 1_000_000
    ) -> List[Dict[str, Any]]:
        """
        Get recent whale alerts.

        Args:
            limit: Maximum number of alerts
            min_value_usd: Minimum transaction value in USD

        Returns:
            List of whale alert transactions
        """
        # Check cache
        if self._is_cache_valid():
            filtered = [
                a for a in self._cache
                if a.get("amount_usd", 0) >= min_value_usd
            ]
            return filtered[:limit]

        # Fetch new data
        alerts = self._fetch_alerts()

        if alerts:
            self._cache = alerts
            self._cache_time = datetime.utcnow()

            filtered = [
                a for a in alerts
                if a.get("amount_usd", 0) >= min_value_usd
            ]
            return filtered[:limit]

        return self._cache[:limit] if self._cache else []

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_time or not self._cache:
            return False

        age = (datetime.utcnow() - self._cache_time).total_seconds()
        return age < CACHE_WHALE_DURATION

    def _fetch_alerts(self) -> List[Dict[str, Any]]:
        """
        Fetch whale alerts from reverse-engineered endpoint.

        The whale-alert.io website makes POST requests to get feed data.
        Uses fallback sources if primary fails.
        """
        alerts = []

        try:
            # Method 1: Try the public feed endpoint (whale-alert.io)
            alerts = self._fetch_from_public_feed()

            if alerts:
                logger.debug(f"Whale alerts: fetched {len(alerts)} from primary source (whale-alert.io)")
            else:
                # Method 2: Try fallback source (BlockchainCenter)
                logger.info("Whale alerts: primary source unavailable, trying fallback (BlockchainCenter)")
                alerts = self._fetch_from_page_data()

                if alerts:
                    logger.debug(f"Whale alerts: fetched {len(alerts)} from fallback source")
                else:
                    logger.warning("Whale alerts: both primary and fallback sources returned no data")

        except Exception as e:
            logger.warning(f"Error fetching whale alerts: {e}")

        # Log summary when no data available at all
        if not alerts and not self._cache:
            logger.info("Whale alerts: no data available from any source, trading decisions will proceed without whale flow analysis")

        return alerts

    def _fetch_from_public_feed(self) -> List[Dict[str, Any]]:
        """Try to fetch from public feed endpoint (whale-alert.io)."""
        alerts = []
        WHALE_ALERT_TIMEOUT = 10.0

        try:
            # The website loads data via this endpoint
            with httpx.Client(timeout=WHALE_ALERT_TIMEOUT) as client:
                # Try the feed endpoint used by the website
                response = client.post(
                    "https://whale-alert.io/feed",
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0 (compatible; TradingBot/1.0)"
                    },
                    json={"limit": 50}
                )

                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        alerts = self._parse_alerts(data)
                    elif isinstance(data, dict) and "transactions" in data:
                        alerts = self._parse_alerts(data["transactions"])
                else:
                    logger.debug(f"Whale-alert.io returned status {response.status_code}")

        except httpx.TimeoutException:
            logger.debug(f"Whale-alert.io timeout (>{WHALE_ALERT_TIMEOUT}s)")
        except httpx.ConnectError:
            logger.debug("Whale-alert.io connection failed")
        except Exception as e:
            logger.debug(f"Whale-alert.io fetch failed: {e}")

        return alerts

    def _fetch_from_page_data(self) -> List[Dict[str, Any]]:
        """Fallback: Fetch from alternative sources (BlockchainCenter)."""
        alerts = []
        FALLBACK_TIMEOUT = 10.0

        try:
            # Try BlockchainCenter whale tracking
            with httpx.Client(timeout=FALLBACK_TIMEOUT) as client:
                response = client.get(
                    "https://www.blockchaincenter.net/api/whale-watch/",
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0 (compatible; TradingBot/1.0)"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        for item in data[:50]:
                            alert = {
                                "blockchain": item.get("blockchain", "unknown"),
                                "symbol": item.get("symbol", "BTC"),
                                "amount": item.get("amount", 0),
                                "amount_usd": item.get("amount_usd", 0),
                                "from_type": item.get("from", {}).get("type", "unknown"),
                                "to_type": item.get("to", {}).get("type", "unknown"),
                                "timestamp": item.get("timestamp"),
                                "hash": item.get("hash", "")[:16],
                            }
                            alerts.append(alert)
                else:
                    logger.debug(f"BlockchainCenter returned status {response.status_code}")

        except httpx.TimeoutException:
            logger.debug(f"BlockchainCenter timeout (>{FALLBACK_TIMEOUT}s)")
        except httpx.ConnectError:
            logger.debug("BlockchainCenter connection failed")
        except Exception as e:
            logger.debug(f"BlockchainCenter fetch failed: {e}")

        return alerts

    def _parse_alerts(self, raw_data: List[Dict]) -> List[Dict[str, Any]]:
        """Parse raw alert data into standard format."""
        alerts = []

        for item in raw_data:
            try:
                alert = {
                    "blockchain": item.get("blockchain", "unknown"),
                    "symbol": item.get("symbol", "BTC"),
                    "amount": float(item.get("amount", 0)),
                    "amount_usd": float(item.get("amount_usd", 0)),
                    "from_type": self._get_wallet_type(item.get("from", {})),
                    "to_type": self._get_wallet_type(item.get("to", {})),
                    "timestamp": item.get("timestamp"),
                    "hash": item.get("hash", "")[:16] if item.get("hash") else "",
                }
                alerts.append(alert)

            except Exception:
                continue

        return alerts

    def _get_wallet_type(self, wallet_info: Dict) -> str:
        """Determine wallet type (exchange, unknown, etc)."""
        if isinstance(wallet_info, dict):
            owner = wallet_info.get("owner", "")
            owner_type = wallet_info.get("owner_type", "")

            if owner_type == "exchange" or owner:
                return f"exchange:{owner}" if owner else "exchange"

            return wallet_info.get("type", "unknown")

        return "unknown"

    def analyze_flow(
        self,
        alerts: List[Dict[str, Any]],
        symbol: str = None
    ) -> Dict[str, Any]:
        """
        Analyze capital flow direction from alerts.

        Args:
            alerts: List of whale alerts
            symbol: Filter by symbol (optional)

        Returns:
            Flow analysis dictionary
        """
        if symbol:
            alerts = [a for a in alerts if a.get("symbol", "").upper() == symbol.upper()]

        if not alerts:
            return {
                "inflow_exchange": 0,
                "outflow_exchange": 0,
                "net_flow": 0,
                "interpretation": "Nessun movimento significativo",
                "alert_count": 0
            }

        inflow = 0  # To exchange (potential sell pressure)
        outflow = 0  # From exchange (potential buy/hold)

        for alert in alerts:
            amount_usd = alert.get("amount_usd", 0)
            to_type = alert.get("to_type", "")
            from_type = alert.get("from_type", "")

            if "exchange" in to_type.lower():
                inflow += amount_usd
            if "exchange" in from_type.lower():
                outflow += amount_usd

        net_flow = outflow - inflow  # Positive = bullish (leaving exchanges)

        if net_flow > 10_000_000:
            interpretation = "Forte outflow da exchange (bullish)"
        elif net_flow < -10_000_000:
            interpretation = "Forte inflow verso exchange (bearish)"
        elif abs(net_flow) < 1_000_000:
            interpretation = "Flusso bilanciato (neutro)"
        else:
            interpretation = "Movimento moderato"

        return {
            "inflow_exchange": inflow,
            "outflow_exchange": outflow,
            "net_flow": net_flow,
            "interpretation": interpretation,
            "alert_count": len(alerts)
        }


# Global whale alert collector
whale_collector = WhaleAlertCollector()


def get_whale_alerts(
    limit: int = 10,
    min_value_usd: float = 1_000_000
) -> List[Dict[str, Any]]:
    """Convenience function to get whale alerts."""
    return whale_collector.get_recent_alerts(limit, min_value_usd)


def analyze_whale_flow(symbol: str = None) -> Dict[str, Any]:
    """Convenience function to analyze whale capital flow."""
    alerts = whale_collector.get_recent_alerts(50, 500_000)
    return whale_collector.analyze_flow(alerts, symbol)
