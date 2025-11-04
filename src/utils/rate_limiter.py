"""
Rate Limiter Utility
====================
Implements rate limiting for API requests
"""

import time
from threading import Lock


class RateLimiter:
    """Thread-safe rate limiter"""

    def __init__(self, requests_per_second: float):
        """
        Initialize rate limiter

        Args:
            requests_per_second: Maximum requests per second allowed
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0
        self.lock = Lock()

    def wait(self):
        """Wait if necessary to respect rate limit"""
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time

            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)

            self.last_request_time = time.time()

    def __enter__(self):
        """Context manager entry - wait for rate limit"""
        self.wait()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - no action needed"""
        return False
