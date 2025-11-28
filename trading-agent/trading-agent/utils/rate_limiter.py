"""
Rate limiter for API calls.

Implements a simple token bucket algorithm to prevent exceeding API rate limits.
"""
import time
import threading
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Thread-safe rate limiter using token bucket algorithm.

    Ensures API calls don't exceed the specified rate limit.
    """

    def __init__(self, calls_per_minute: int = 30, name: str = "default"):
        """
        Initialize the rate limiter.

        Args:
            calls_per_minute: Maximum number of calls allowed per minute
            name: Identifier for logging purposes
        """
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.name = name
        self._last_call: float = 0.0
        self._lock = threading.Lock()
        self._call_count: int = 0
        self._window_start: float = 0.0

        logger.debug(f"RateLimiter '{name}' initialized: {calls_per_minute} calls/min "
                    f"(min interval: {self.min_interval:.2f}s)")

    def wait(self) -> float:
        """
        Wait if necessary to comply with rate limit.

        Returns:
            Time waited in seconds (0 if no wait was needed)
        """
        with self._lock:
            now = time.time()
            elapsed = now - self._last_call

            wait_time = 0.0
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                logger.debug(f"RateLimiter '{self.name}': waiting {wait_time:.2f}s")
                time.sleep(wait_time)

            self._last_call = time.time()
            self._call_count += 1

            return wait_time

    def acquire(self) -> bool:
        """
        Acquire permission to make an API call.

        Non-blocking alternative to wait() - returns immediately.

        Returns:
            True if call is allowed, False if rate limit would be exceeded
        """
        with self._lock:
            now = time.time()
            elapsed = now - self._last_call

            if elapsed >= self.min_interval:
                self._last_call = now
                self._call_count += 1
                return True

            return False

    def reset(self) -> None:
        """Reset the rate limiter state."""
        with self._lock:
            self._last_call = 0.0
            self._call_count = 0
            self._window_start = 0.0
            logger.debug(f"RateLimiter '{self.name}' reset")

    @property
    def calls_made(self) -> int:
        """Return the number of calls made since initialization or last reset."""
        return self._call_count

    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with stats about the rate limiter
        """
        with self._lock:
            now = time.time()
            time_since_last = now - self._last_call if self._last_call > 0 else 0

            return {
                "name": self.name,
                "calls_per_minute": self.calls_per_minute,
                "min_interval_seconds": self.min_interval,
                "total_calls": self._call_count,
                "seconds_since_last_call": round(time_since_last, 2),
                "ready_for_next": time_since_last >= self.min_interval,
            }


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate limiter that adapts based on API responses.

    Backs off when rate limit errors (429) are encountered.
    """

    def __init__(
        self,
        calls_per_minute: int = 30,
        name: str = "adaptive",
        backoff_multiplier: float = 2.0,
        max_backoff_seconds: float = 60.0,
    ):
        """
        Initialize the adaptive rate limiter.

        Args:
            calls_per_minute: Initial maximum calls per minute
            name: Identifier for logging
            backoff_multiplier: Factor to multiply interval on rate limit hit
            max_backoff_seconds: Maximum wait time between calls
        """
        super().__init__(calls_per_minute, name)
        self.initial_interval = self.min_interval
        self.backoff_multiplier = backoff_multiplier
        self.max_backoff_seconds = max_backoff_seconds
        self._consecutive_429s: int = 0

    def on_rate_limit_error(self) -> float:
        """
        Called when a 429 rate limit error is received.

        Increases the minimum interval between calls.

        Returns:
            New minimum interval in seconds
        """
        with self._lock:
            self._consecutive_429s += 1
            self.min_interval = min(
                self.min_interval * self.backoff_multiplier,
                self.max_backoff_seconds
            )
            logger.warning(
                f"RateLimiter '{self.name}': rate limit hit #{self._consecutive_429s}, "
                f"backing off to {self.min_interval:.2f}s interval"
            )
            return self.min_interval

    def on_success(self) -> None:
        """
        Called when a successful response is received.

        Gradually restores the rate limit toward the original value.
        """
        with self._lock:
            if self._consecutive_429s > 0:
                self._consecutive_429s = 0
                # Gradually restore (don't jump back immediately)
                self.min_interval = max(
                    self.initial_interval,
                    self.min_interval / self.backoff_multiplier
                )
                logger.debug(
                    f"RateLimiter '{self.name}': success, interval now {self.min_interval:.2f}s"
                )

    def reset(self) -> None:
        """Reset the rate limiter to initial state."""
        super().reset()
        with self._lock:
            self.min_interval = self.initial_interval
            self._consecutive_429s = 0


# Pre-configured rate limiters for common use cases
deepseek_rate_limiter = AdaptiveRateLimiter(
    calls_per_minute=30,
    name="deepseek",
    backoff_multiplier=2.0,
    max_backoff_seconds=30.0,
)
