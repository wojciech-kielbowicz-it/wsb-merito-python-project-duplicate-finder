import os
import re
from pathlib import Path
from typing import Iterator, Iterable

def scan_directory_recursive(root: Path) -> Iterator[Path]:
    """
    Generator rekurencyjnie przeglądający katalog za pomocą os.scandir i yield from.
    """
    try:
        with os.scandir(root) as entries: # otwarcie folderu
            for entry in entries:
                if entry.is_file(follow_symlinks=False): # jeśli to plik zwracamy ścieżke
                    yield Path(entry.path)
                elif entry.is_dir(follow_symlinks=False): # jeśli podfolder wchodzimy i szukamy dalej
                    yield from scan_directory_recursive(Path(entry.path))
    except PermissionError: # wyjątek - brak dostępu
        pass