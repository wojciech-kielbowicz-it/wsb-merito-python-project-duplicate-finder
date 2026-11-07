import hashlib
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from pathlib import Path
from typing import Dict, List, Tuple

from core.decorators import measure_time, retry, requires_valid_root
from core.reader import FileChunkIterator
from core.walker import build_file_pipeline

@retry(attempts=3, delay=0.05, exceptions=(OSError,))
def compute_sha256(file_path: Path, chunk_size: int = 65536) -> Tuple[Path, str]:
    """Funkcja licząca SHA-256 (pickle w multiprocessing)"""
    hasher = hashlib.sha256()
    for chunk in FileChunkIterator(file_path, chunk_size=chunk_size):
        hasher.update(chunk)
    return file_path, hasher.hexdigest()


def compute_pure_python_checksum(file_path: Path, chunk_size: int = 65536) -> Tuple[Path, int]:
    """
    CPU-bound task w czystym Pythonie
    Demonstracja przewagi procesów nad wątkami przy obliczeniach w bytecode
    """
    checksum = 0
    for chunk in FileChunkIterator(file_path, chunk_size=chunk_size):
        for byte in chunk:
            checksum = (checksum * 31 + byte) % 1_000_000_007
    return file_path, checksum

class DuplicateScanner:
    """Główna klasa skanera duplikatów wykorzystująca wątki oraz procesy"""

    def __init__(self, root_path: Path | str, min_size: int = 1) -> None:
        self._root_path = Path(root_path)
        self._is_configured = self._root_path.exists() and self._root_path.is_dir()
        self.min_size = min_size  # wywołuje setter @min_size.setter
        self._lock = threading.Lock()

    @property
    def root_path(self) -> Path:
        return self._root_path

    @property
    def min_size(self) -> int:
        return self._min_size

    @min_size.setter
    def min_size(self, value: int) -> None:
        if value < 0:
            raise ValueError("Minimalny rozmiar pliku nie może być ujemny")
        self._min_size = value

    @classmethod
    def from_string(cls, path_str: str, min_size: int = 1) -> "DuplicateScanner":
        """Alternatywny konstruktor przyjmujący napis ze ścieżką"""
        return cls(Path(path_str).resolve(), min_size=min_size)

    @staticmethod
    def format_bytes(size: int) -> str:
        """Metoda statyczna formatująca rozmiar w bajtach na czytelny napis"""
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    @requires_valid_root
    def _group_candidates_by_size_threaded(self, regex_pattern: str, workers: int = 4) -> List[Path]:
        """
        I/O bound współbieżnie pobiera rozmiary plików z dysku przy użyciu puli wątków
        Ochrona slownika przez threading.Lock
        Zwraca tylko pliki, których rozmiar występuje więcej niż raz (potencjalne duplikaty)
        """
        size_map: Dict[int, List[Path]] = defaultdict(list)
        files = list(build_file_pipeline(self._root_path, regex_pattern, self._min_size))

        def _stat_worker(p: Path) -> None:
            try:
                sz = p.stat().st_size
                with self._lock:  # Sekcja krytyczna -> Lock
                    size_map[sz].append(p)
            except OSError:
                pass

        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(_stat_worker, files))

        return [p for group in size_map.values() if len(group) > 1 for p in group]

    @requires_valid_root
    @measure_time
    def find_duplicates_threads(self, regex_pattern: str = r".*", workers: int = 4) -> Dict[str, List[Path]]:
        """Wyszukuje duplikaty używając puli wątków (ThreadPoolExecutor)."""
        candidates = self._group_candidates_by_size_threaded(regex_pattern, workers)
        duplicates: Dict[str, List[Path]] = defaultdict(list)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            for path, file_hash in pool.map(compute_sha256, candidates):
                with self._lock:
                    duplicates[file_hash].append(path)

        return {h: paths for h, paths in duplicates.items() if len(paths) > 1}

    @requires_valid_root
    @measure_time
    def find_duplicates_processes(self, regex_pattern: str = r".*", workers: int = 4) -> Dict[str, List[Path]]:
        """Wyszukuje duplikaty używając puli procesów (ProcessPoolExecutor)."""
        candidates = self._group_candidates_by_size_threaded(regex_pattern, workers)
        duplicates: Dict[str, List[Path]] = defaultdict(list)

        with ProcessPoolExecutor(max_workers=workers) as pool:
            for path, file_hash in pool.map(compute_sha256, candidates):
                duplicates[file_hash].append(path)

        return {h: paths for h, paths in duplicates.items() if len(paths) > 1}