import threading
import time
from collections import deque


class RateLimiter:
    """Sliding window per key, in memory: one process, one counter — enough to slow a password guesser behind the web app."""

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self.hits: dict[str, deque[float]] = {}
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        moment = time.monotonic()

        with self.lock:
            hits = self.hits.setdefault(key, deque())

            while hits and moment - hits[0] > self.window:
                hits.popleft()

            if len(hits) >= self.limit:
                return False

            hits.append(moment)

            if len(self.hits) > 10000:
                for stale in [
                    k
                    for k, v in self.hits.items()
                    if not v or moment - v[-1] > self.window
                ]:
                    self.hits.pop(stale, None)

            return True
