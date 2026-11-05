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

def filter_by_regex(paths: Iterable[Path], pattern: str) -> Iterator[Path]:
    """Generator filtrujący ścieżki na podstawie wyrażenia regularnego (wyrażenie generujące)."""
    compiled_re = re.compile(pattern)
    return (p for p in paths if compiled_re.search(p.name))


def filter_by_min_size(paths: Iterable[Path], min_bytes: int = 1) -> Iterator[Path]:
    """Generator odrzucający pliki mniejsze niż min_bytes (wyrażenie generujące)."""
    return (p for p in paths if p.stat().st_size >= min_bytes)

def build_file_pipeline(root: Path, regex_pattern: str = r".*", min_bytes: int = 1) -> Iterator[Path]:
    """Pipeline generatorów łączący skanowanie i dwuetapowe filtrowanie."""
    raw_files = scan_directory_recursive(root)
    regex_filtered = filter_by_regex(raw_files, regex_pattern)
    size_filtered = filter_by_min_size(regex_filtered, min_bytes)
    yield from size_filtered