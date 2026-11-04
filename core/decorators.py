import functools
import logging
import time
from typing import Callable, Any, Type, Tuple

logger = logging.getLogger("DuplicateFinder")


def measure_time(func: Callable) -> Callable:
    """Dekorator funkcji mierzący i logujący czas wykonania."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"TIMER: Funkcja '{func.__name__}' wykonana w {elapsed:.4f} s")
        return result
    return wrapper


