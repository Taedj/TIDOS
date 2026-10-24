import time
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, limit, window, clock=time.monotonic):
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("limit must be an int >= 1")
        if isinstance(window, bool) or not isinstance(window, (int, float)) or window <= 0:
            raise ValueError("window must be > 0")
        self.limit = limit
        self.window = float(window)
        self.clock = clock
        self._events = {}

    def _recent(self, key, now):
        events = self._events.get(key)
        if events is None:
            return deque()
        while events and now - events[0] >= self.window:
            events.popleft()
        if not events:
            del self._events[key]
            return deque()
        return events

    def allow(self, key):
        now = self.clock()
        events = self._recent(key, now)
        if len(events) >= self.limit:
            return False
        events.append(now)
        self._events[key] = events
        return True

    def retry_after(self, key):
        now = self.clock()
        events = self._recent(key, now)
        if len(events) < self.limit:
            return 0.0
        return events[0] + self.window - now
