"""Simple process-wide rate limiter for Nominatim (1 req/s)."""
from __future__ import annotations

import threading
import time


class RateLimiter:
    def __init__(self, min_interval_s: float = 1.0) -> None:
        self.min_interval_s = min_interval_s
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            if elapsed < self.min_interval_s:
                time.sleep(self.min_interval_s - elapsed)
            self._last = time.monotonic()


nominatim_limiter = RateLimiter(1.0)
