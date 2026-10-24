import functools
import time


def retry(times=3, exceptions=(Exception,), base_delay=0.1, sleep=time.sleep):
    if not isinstance(times, int) or isinstance(times, bool) or times < 1:
        raise ValueError("times must be an int >= 1")
    if isinstance(exceptions, type):
        exceptions = (exceptions,)

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(times):
                try:
                    return fn(*args, **kwargs)
                except exceptions:
                    if attempt == times - 1:
                        raise
                    sleep(base_delay * 2 ** attempt)
        return wrapper
    return decorator
