import time


class SlidingWindowLimiter:
    def __init__(self, limit, window, clock=time.monotonic):
        raise NotImplementedError

    def allow(self, key):
        raise NotImplementedError

    def retry_after(self, key):
        raise NotImplementedError
