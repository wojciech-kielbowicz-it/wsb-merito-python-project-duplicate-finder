import sys
import sysconfig
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import cpu_count
from pathlib import Path
from typing import List, Callable, Any

from core.scanner import compute_sha256, compute_pure_python_checksum


def print_environment_info() -> None:
    """Wypisuje informacje o interpreterze i statusie GIL"""
    print("=" * 65)
    print("INFORMACJE O ŚRODOWISKU URUCHOMIENIOWYM")
    print("=" * 65)
    print(f"Wersja Pythona           : {sys.version.split()[0]}")
    print(f"Liczba rdzeni CPU        : {cpu_count()}")
    print(f"Interwał przełączania    : {sys.getswitchinterval()} s")
    free_threading = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
    print(f"Kompilacja free-threading: {free_threading}")
    if hasattr(sys, "_is_gil_enabled"):
        print(f"GIL aktywny              : {sys._is_gil_enabled()}")
    print("=" * 65)


def _run_mode(name: str, func: Callable, files: List[Path], executor_cls: Any = None, workers: int = 4) -> float:
    start = time.perf_counter()
    if executor_cls is None:
        for f in files:
            func(f)
    else:
        with executor_cls(max_workers=workers) as ex:
            list(ex.map(func, files))
    elapsed = time.perf_counter() - start
    print(f"  {name:<25} | Czas: {elapsed:.4f} s")
    return elapsed


def run_gil_benchmarks(files: List[Path], workers: int = 4) -> None:
    """Uruchamia zestawienie porównawcze Sekwencyjnie vs Wątki vs Procesy"""
    print_environment_info()
    print(f"Liczba plików testowych: {len(files)} | Liczba workerów: {workers}\n")

    print("TEST 1: Czysty Python CPU-bound (Własna suma kontrolna - GIL trzymany)")
    t_seq_cpu = _run_mode("Sekwencyjnie", compute_pure_python_checksum, files)
    t_thr_cpu = _run_mode(f"Wątki ({workers})", compute_pure_python_checksum, files, ThreadPoolExecutor, workers)
    t_prc_cpu = _run_mode(f"Procesy ({workers})", compute_pure_python_checksum, files, ProcessPoolExecutor, workers)

    print("\nTEST 2: I/O + Biblioteka C zwalniająca GIL (hashlib.sha256)")
    t_seq_sha = _run_mode("Sekwencyjnie", compute_sha256, files)
    t_thr_sha = _run_mode(f"Wątki ({workers})", compute_sha256, files, ThreadPoolExecutor, workers)
    t_prc_sha = _run_mode(f"Procesy ({workers})", compute_sha256, files, ProcessPoolExecutor, workers)

    print("\n" + "=" * 65)
    print("PODSUMOWANIE PRZYSPIESZENIA")
    print("=" * 65)
    print(f"Czysty Python (CPU) -> Wątki: {t_seq_cpu/t_thr_cpu:.2f}x | Procesy: {t_seq_cpu/t_prc_cpu:.2f}x")
    print(f"SHA-256 (I/O + C)   -> Wątki: {t_seq_sha/t_thr_sha:.2f}x | Procesy: {t_seq_sha/t_prc_sha:.2f}x")
    print("=" * 65)