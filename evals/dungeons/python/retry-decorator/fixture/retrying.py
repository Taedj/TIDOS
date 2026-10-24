import time


def retry(times=3, exceptions=(Exception,), base_delay=0.1, sleep=time.sleep):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            for _ in range(times):
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    sleep(base_delay)
        return wrapper
    return decorator
