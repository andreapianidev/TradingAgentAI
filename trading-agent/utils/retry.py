"""
Retry utilities for API calls with exponential backoff.

Provides decorators and functions for handling transient failures with:
- Exponential backoff (2^attempt * base_delay)
- Configurable max retries
- Retry on specific exceptions
- Special handling for rate limits (429)
- Logging for debugging
"""
import time
import functools
from typing import Callable, Type, Tuple, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


def exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    rate_limit_delay: float = 120.0
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for first retry (default: 1.0)
        max_delay: Maximum delay between retries (default: 60.0)
        retry_on: Tuple of exception types to retry on (default: all Exception)
        rate_limit_delay: Delay for HTTP 429 rate limit (default: 120.0s)

    Usage:
        @exponential_backoff(max_retries=3, base_delay=2.0)
        def fetch_data():
            return api.get()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except retry_on as e:
                    last_exception = e

                    # Check if it's a rate limit error (HTTP 429)
                    is_rate_limit = False
                    if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                        is_rate_limit = e.response.status_code == 429
                    elif '429' in str(e):
                        is_rate_limit = True

                    # Last attempt, don't retry
                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries: {e}"
                        )
                        break

                    # Calculate delay
                    if is_rate_limit:
                        delay = rate_limit_delay
                        logger.warning(
                            f"{func.__name__} rate limited (429), "
                            f"waiting {delay}s before retry {attempt + 1}/{max_retries}"
                        )
                    else:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}, "
                            f"retrying in {delay:.1f}s"
                        )

                    time.sleep(delay)

            # All retries exhausted
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Functional approach to retry with backoff (alternative to decorator).

    Args:
        func: Function to retry
        max_retries: Maximum retry attempts
        base_delay: Base delay in seconds
        retry_on: Exception types to retry on

    Returns:
        Wrapped function with retry logic

    Usage:
        result = retry_with_backoff(api.get_data, max_retries=5)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except retry_on as e:
                last_exception = e

                if attempt == max_retries:
                    logger.error(f"{func.__name__} failed after {max_retries} retries")
                    break

                delay = base_delay * (2 ** attempt)
                logger.debug(f"Retry {attempt + 1}/{max_retries} in {delay}s")
                time.sleep(delay)

        if last_exception:
            raise last_exception

    return wrapper


class RateLimitTracker:
    """
    Tracks API rate limit usage for monitoring and alerting.

    Attributes:
        api_name: Name of the API being tracked
        total_calls: Total API calls made
        failed_calls: Failed API calls
        rate_limited_calls: Calls that hit rate limit
        last_call_time: Timestamp of last API call
    """

    def __init__(self, api_name: str):
        """
        Initialize rate limit tracker.

        Args:
            api_name: Name of the API to track
        """
        self.api_name = api_name
        self.total_calls = 0
        self.failed_calls = 0
        self.rate_limited_calls = 0
        self.last_call_time: Optional[float] = None
        self._start_time = time.time()

    def record_call(self, success: bool = True, rate_limited: bool = False):
        """
        Record an API call.

        Args:
            success: Whether the call succeeded
            rate_limited: Whether the call hit rate limit
        """
        self.total_calls += 1
        self.last_call_time = time.time()

        if not success:
            self.failed_calls += 1

        if rate_limited:
            self.rate_limited_calls += 1

    def get_stats(self) -> dict:
        """
        Get rate limit statistics.

        Returns:
            Dictionary with usage statistics
        """
        uptime_hours = (time.time() - self._start_time) / 3600

        return {
            "api_name": self.api_name,
            "total_calls": self.total_calls,
            "failed_calls": self.failed_calls,
            "rate_limited_calls": self.rate_limited_calls,
            "success_rate": (
                ((self.total_calls - self.failed_calls) / self.total_calls * 100)
                if self.total_calls > 0 else 0
            ),
            "calls_per_hour": self.total_calls / uptime_hours if uptime_hours > 0 else 0,
            "uptime_hours": uptime_hours
        }

    def check_threshold(self, threshold_pct: float = 90.0, daily_quota: int = 333) -> bool:
        """
        Check if usage exceeds threshold percentage of daily quota.

        Args:
            threshold_pct: Alert threshold (default: 90%)
            daily_quota: Daily API quota (default: 333 for CMC free tier)

        Returns:
            True if threshold exceeded, False otherwise
        """
        if daily_quota <= 0:
            return False

        uptime_hours = (time.time() - self._start_time) / 3600
        if uptime_hours <= 0:
            return False

        # Only warn if we've been running for at least 1 hour
        # to avoid misleading extrapolations from short uptimes
        if uptime_hours < 1.0:
            logger.debug(
                f"{self.api_name}: {self.total_calls} calls in {uptime_hours*60:.1f} minutes "
                f"(too early for daily projection)"
            )
            return False

        # Extrapolate daily usage
        estimated_daily_calls = (self.total_calls / uptime_hours) * 24

        usage_pct = (estimated_daily_calls / daily_quota) * 100

        if usage_pct >= threshold_pct:
            logger.warning(
                f"{self.api_name} rate limit: {usage_pct:.1f}% of daily quota "
                f"({estimated_daily_calls:.0f}/{daily_quota} calls/day, "
                f"actual: {self.total_calls} calls in {uptime_hours:.1f}h)"
            )
            return True

        return False

    def log_stats(self):
        """Log current statistics."""
        stats = self.get_stats()
        logger.info(
            f"{self.api_name} stats: "
            f"{stats['total_calls']} calls, "
            f"{stats['success_rate']:.1f}% success, "
            f"{stats['calls_per_hour']:.1f} calls/hour"
        )
