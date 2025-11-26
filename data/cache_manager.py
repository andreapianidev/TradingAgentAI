"""
Cache manager for external API data.
"""
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps

from utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Simple in-memory cache manager."""

    def __init__(self):
        """Initialize the cache manager."""
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if datetime.utcnow() > entry["expires_at"]:
            del self._cache[key]
            return None

        return entry["value"]

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 300
    ) -> None:
        """
        Set cache value with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
        """
        self._cache[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl_seconds),
            "created_at": datetime.utcnow(),
        }
        logger.debug(f"Cached {key} for {ttl_seconds}s")

    def delete(self, key: str) -> bool:
        """
        Delete cached value.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries removed
        """
        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in self._cache.items()
            if now > entry["expires_at"]
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "total_entries": len(self._cache),
            "keys": list(self._cache.keys()),
        }


# Global cache manager
cache_manager = CacheManager()


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    Decorator for caching function results.

    Args:
        ttl_seconds: Time to live in seconds
        key_prefix: Prefix for cache key

    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # Check cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # Call function
            result = func(*args, **kwargs)

            # Cache result
            cache_manager.set(cache_key, result, ttl_seconds)

            return result

        return wrapper
    return decorator
