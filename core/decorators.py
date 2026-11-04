import functools
import logging
import time
from typing import Callable, Any, Type, Tuple

logger = logging.getLogger("DuplicateFinder")


def measure_time(func: Callable) -> Callable:
    """Dekorator funkcji mierzący i logujący czas wykonania."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:

        start = time.perf_counter() # Rejestracja czasu przed uruchomieniem funkcji
        result = func(*args, **kwargs) # Wywołanie właściwej funkcji
        elapsed = time.perf_counter() - start #Obliczanie różnicy czasu
        logger.info(f"TIMER: Funkcja '{func.__name__}' wykonana w {elapsed:.4f} s") #Zapis do logów
        return result
    return wrapper


