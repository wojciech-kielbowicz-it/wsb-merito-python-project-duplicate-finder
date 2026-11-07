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