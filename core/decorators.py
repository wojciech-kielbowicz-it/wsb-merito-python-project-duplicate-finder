import functools
import logging
import time
from typing import Callable, Any, Type, Tuple

logger = logging.getLogger("DuplicateFinder")


def measure_time(func: Callable) -> Callable:
    """Dekorator funkcji mierzący i logujący czas wykonania"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:

        start = time.perf_counter() # Rejestracja czasu przed uruchomieniem funkcji
        result = func(*args, **kwargs) # Wywołanie właściwej funkcji
        elapsed = time.perf_counter() - start #Obliczanie różnicy czasu
        logger.info(f"TIMER: Funkcja '{func.__name__}' wykonana w {elapsed:.4f} s") #Zapis do logów
        return result
    return wrapper


def retry(attempts: int = 3, delay: float = 0.1, exceptions: Tuple[Type[Exception], ...] = (OSError,)) -> Callable:
    """Fabryka dekoratorów: ponawia wykonanie funkcji w razie wystąpienia określonych wyjątków"""
    def decorator(func: Callable) -> Callable: # Pierwsza warstwa -> liczba prób, opóźnienie, typy błędów
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any: # Druga warswta -> dekorowana funkcja
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs) # Próba wykonania oryginalnej funkcji
                except exceptions as e:
                    logger.warning(f"RETRY: {func.__name__} próba {attempt}/{attempts} nieudana: {e}") # Zapis do logów -> Spodziewany błąd
                    if attempt == attempts:
                        logger.error(f"RETRY: Wyczerpano limit prób dla {func.__name__}") # Zapis do logów -> Błąd krytyczny (ostatnia próba w pętli)
                        raise
                    time.sleep(delay) 
        return wrapper
    return decorator

def requires_valid_root(method: Callable) -> Callable:
    """Dekorator metody sprawdzający stan obiektu (self) przed wykonaniem operacji."""
    @functools.wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        if not getattr(self, "_is_configured", False) or not self.root_path.exists():
            raise RuntimeError(
                f"Nie można wywołać '{method.__name__}': ścieżka bazowa '{self.root_path}' "
                f"nie istnieje lub skaner nie został poprawnie skonfigurowany."
            )
        return method(self, *args, **kwargs)
    return wrapper