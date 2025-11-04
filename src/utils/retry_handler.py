"""
Retry Handler with Exponential Backoff and 429 Detection
=========================================================
Provides robust retry logic for HTTP requests with intelligent error handling
"""

import time
import logging
from typing import Callable, Any, Optional
from functools import wraps
import requests
from .config import Config

logger = logging.getLogger(__name__)


class RetryHandler:
    """Handles retries with exponential backoff and rate limit detection"""

    def __init__(self,
                 max_retries: int = None,
                 initial_delay: float = None,
                 backoff_factor: float = None,
                 max_delay: float = 300):
        """
        Initialize retry handler

        Args:
            max_retries: Maximum number of retry attempts (default from Config)
            initial_delay: Initial delay between retries in seconds (default from Config)
            backoff_factor: Multiplier for exponential backoff (default from Config)
            max_delay: Maximum delay between retries in seconds (default 300)
        """
        self.max_retries = max_retries or Config.MAX_RETRIES
        self.initial_delay = initial_delay or Config.INITIAL_RETRY_DELAY
        self.backoff_factor = backoff_factor or Config.RETRY_BACKOFF
        self.max_delay = max_delay

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for current attempt using exponential backoff

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds (capped at max_delay)
        """
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if request should be retried based on exception type

        Args:
            exception: The exception that occurred
            attempt: Current attempt number

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_retries:
            return False

        # Retry on connection errors
        if isinstance(exception, (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError
        )):
            return True

        # Retry on specific HTTP status codes
        if isinstance(exception, requests.exceptions.HTTPError):
            if hasattr(exception, 'response') and exception.response is not None:
                status_code = exception.response.status_code

                # Always retry on server errors (5xx)
                if 500 <= status_code < 600:
                    return True

                # Retry on 429 (Too Many Requests)
                if status_code == 429:
                    return True

                # Retry on 408 (Request Timeout)
                if status_code == 408:
                    return True

                # Don't retry on client errors (4xx) except those above
                if 400 <= status_code < 500:
                    return False

        return False

    def handle_429(self, response: Optional[requests.Response] = None) -> float:
        """
        Handle 429 Rate Limit error with intelligent delay

        Args:
            response: HTTP response object (may contain Retry-After header)

        Returns:
            Delay in seconds before retry
        """
        # Check for Retry-After header
        if response and 'Retry-After' in response.headers:
            try:
                retry_after = int(response.headers['Retry-After'])
                logger.warning(f"Rate limited. Retry-After header suggests {retry_after}s delay")
                return min(retry_after, self.max_delay)
            except (ValueError, TypeError):
                pass

        # Default: 5 minute delay for rate limits
        default_delay = 300
        logger.warning(f"Rate limited (429). Waiting {default_delay}s before retry")
        return default_delay

    def retry_request(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic

        Args:
            func: Function to execute (should return requests.Response)
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of successful function execution

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                response = func(*args, **kwargs)

                # Check for 429 status code
                if hasattr(response, 'status_code') and response.status_code == 429:
                    if attempt < self.max_retries:
                        delay = self.handle_429(response)
                        logger.info(f"Attempt {attempt + 1}/{self.max_retries + 1}: "
                                   f"Rate limited, waiting {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        raise requests.exceptions.HTTPError(
                            f"Rate limit exceeded after {self.max_retries} retries",
                            response=response
                        )

                # Raise for other HTTP errors
                if hasattr(response, 'raise_for_status'):
                    response.raise_for_status()

                return response

            except Exception as e:
                last_exception = e

                if not self.should_retry(e, attempt):
                    logger.debug(f"Not retrying: {type(e).__name__}: {str(e)}")
                    raise

                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries + 1} failed: "
                        f"{type(e).__name__}: {str(e)}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed")
                    raise

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception


def retry_on_error(max_retries: int = None,
                   initial_delay: float = None,
                   backoff_factor: float = None):
    """
    Decorator for automatic retry with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries
        backoff_factor: Multiplier for exponential backoff

    Example:
        @retry_on_error(max_retries=3, initial_delay=1, backoff_factor=2)
        def fetch_data(url):
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            handler = RetryHandler(
                max_retries=max_retries,
                initial_delay=initial_delay,
                backoff_factor=backoff_factor
            )
            return handler.retry_request(func, *args, **kwargs)
        return wrapper
    return decorator


class RateLimitTracker:
    """
    Tracks rate limit violations and adjusts request timing accordingly
    """

    def __init__(self):
        self.violations = {}  # source -> (count, last_violation_time)
        self.cooldown_multipliers = {}  # source -> multiplier

    def record_violation(self, source: str):
        """
        Record a rate limit violation for a source

        Args:
            source: Source identifier (e.g., 'sec', 'earnings')
        """
        current_time = time.time()

        if source in self.violations:
            count, last_time = self.violations[source]
            # Reset count if last violation was more than 1 hour ago
            if current_time - last_time > 3600:
                count = 0
            self.violations[source] = (count + 1, current_time)
        else:
            self.violations[source] = (1, current_time)

        # Increase cooldown multiplier
        count = self.violations[source][0]
        self.cooldown_multipliers[source] = 1.5 ** count

        logger.warning(
            f"Rate limit violation #{count} for {source}. "
            f"Cooldown multiplier: {self.cooldown_multipliers[source]:.1f}x"
        )

    def get_adjusted_delay(self, source: str, base_delay: float) -> float:
        """
        Get adjusted delay based on rate limit history

        Args:
            source: Source identifier
            base_delay: Base delay between requests

        Returns:
            Adjusted delay in seconds
        """
        if source in self.cooldown_multipliers:
            multiplier = self.cooldown_multipliers[source]
            return base_delay * multiplier
        return base_delay

    def clear_violations(self, source: str):
        """
        Clear violation history for a source (called after successful period)

        Args:
            source: Source identifier
        """
        if source in self.violations:
            del self.violations[source]
        if source in self.cooldown_multipliers:
            del self.cooldown_multipliers[source]
        logger.info(f"Cleared rate limit violations for {source}")


# Global rate limit tracker
global_rate_limit_tracker = RateLimitTracker()
