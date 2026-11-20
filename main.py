import argparse
import logging
import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import List
from benchmarks.gil_benchmark import run_gil_benchmarks

from core.patterns import extract_file_metadata, is_valid_extension
from core.scanner import DuplicateScanner

logging.basicConfig( # Logi -> godzina, poziom logowania
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("DuplicateFinder")


def print_welcome_banner() -> None:
    """Wyświetla ekran powitalny z opisem programu i dostępnymi parametrami CLI."""
    print("=" * 72)
    print("  WYSZUKIWARKA ZDUPLIKOWANYCH PLIKÓW & BENCHMARK GIL (Python 3.12+)")
    print("=" * 72)
    print("Co robi ten program?")
    print("  1. Rekurencyjnie skanuje wybrany folder i podfoldery (generatory).")
    print("  2. Grupuje pliki o tym samym rozmiarze (wątki + Lock).")
    print("  3. Liczy skróty SHA-256 blokami (własny iterator), aby wykryć")
    print("     identyczne pliki niezależnie od ich nazwy.")
    print("  4. Porównuje wydajność wątków i procesów (wpływ blokady GIL).")
    print("-" * 72)
    print("Dostępne parametry uruchomieniowe (CLI):")
    print("  --dir, -d <ścieżka>  Ścieżka do folderu nadrzędnego do przeskanowania")
    print("  --generate           Wygeneruj zestaw plików testowych (domyślnie ./test_data)")
    print("  --benchmark          Uruchom pełny benchmark porównawczy GIL")
    print("  --workers <liczba>   Liczba wątków/procesów roboczych (domyślnie: 4)")
    print("  --ext <.rozszerz.>   Filtruj tylko wybrane rozszerzenie (np. --ext .bin)")
    print("  --help, -h           Wyświetl skróconą pomoc argparse")
    print("-" * 72)
    print("Przykłady użycia:")
    print("  python3 main.py --generate --workers 4")
    print("  python3 main.py -d /sciezka/do/folderu --ext .bin")
    print("  python3 main.py --benchmark --workers 4")
    print("=" * 72)
    print()


def generate_test_dataset(target_dir: Path, num_groups: int = 8, file_size_kb: int = 512) -> List[Path]:
    """Generuje zestaw plików testowych (w tym celowe duplikaty) do skanowania i benchmarku"""
    
    
    if target_dir.exists(): # czyszczenie starego katalogu (o ile istnieje)
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    created_files: List[Path] = []
    logger.info(f"Generowanie danych testowych w '{target_dir}' ({num_groups} grup po {file_size_kb} KB)...")

    for i in range(1, num_groups + 1):
        sub_dir = target_dir / f"kat_{i % 3}" # rozrzucenie plikow po 3 katalogach
        sub_dir.mkdir(exist_ok=True)

        content = os.urandom(file_size_kb * 1024)   # Generowanie losowych bajtow aby obciazy I/O


        
        orig_path = sub_dir / f"raport_2026-10-{i:02d}_v1.bin" #  dwa identyczne pliki o roznych nazwach
        dup_path = sub_dir / f"kopia_2026-10-{i:02d}_v2.bin"

        orig_path.write_bytes(content)
        dup_path.write_bytes(content)
        created_files.extend([orig_path, dup_path])

        unique_path = sub_dir / f"unikalny_{i}.txt" # jeden unikalny plik do testow
        unique_path.write_bytes(os.urandom(1024))
        created_files.append(unique_path)

    return created_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Wyszukiwarka zduplikowanych plików i benchmark GIL.")
    parser.add_argument(
        "--dir", "-d", 
        type=str, 
        default=None, 
        help="Ścieżka do katalogu nadrzędnego, w którym ma nastąpić wyszukiwanie"
    )
    parser.add_argument("--generate", action="store_true", help="Wygeneruj testowy zestaw plików w './test_data'")
    parser.add_argument("--benchmark", action="store_true", help="Uruchom pełny benchmark porównawczy GIL")
    parser.add_argument("--workers", type=int, default=4, help="Liczba wątków/procesów roboczych")
    parser.add_argument("--ext", type=str, default=None, help="Filtruj tylko wybrane rozszerzenie (np. .bin)")

    if len(sys.argv) == 1:
        print_welcome_banner()
        raw_params = input("Podaj parametry (np. --benchmark --workers 4) lub wciśnij Enter, aby pominąć: ").strip()
        args = parser.parse_args(shlex.split(raw_params))
    else:
        args = parser.parse_args() # podanie argumetow powyzej
        print_welcome_banner()

    if args.generate: # Ustalenie scieżki nadrzednej
        target_path = Path(args.dir) if args.dir else Path("test_data") # domyslne generowanie plikow w test data (chyba ze podane jest dir)
        generate_test_dataset(target_path)
    elif args.dir:
        target_path = Path(args.dir).expanduser().resolve()
    else:
        user_input = input("Podaj ścieżkę do katalogu nadrzędnego (lub wciśnij Enter dla 'test_data'): ").strip() # prompt do usera jesli nie podany --dir ani --generate
        if user_input:
            target_path = Path(user_input).expanduser().resolve()
        else:
            target_path = Path("test_data")
            if not target_path.exists():
                generate_test_dataset(target_path)

    if not target_path.exists() or not target_path.is_dir(): # walidacja czy pod podana sciezka istnieje katalog
        logger.error(f"Podana ścieżka nadrzędna nie istnieje lub nie jest katalogiem: '{target_path}'")
        return

    logger.info(f"Skanowanie katalogu nadrzędnego: '{target_path}'")

    regex_filter = r".*" # oblsuga filtra roszerzen
    if args.ext:
        if not is_valid_extension(args.ext):
            logger.error(f"Nieprawidłowy format rozszerzenia: '{args.ext}' (wymagana kropka np. '.bin')")
            return
        regex_filter = rf"\{args.ext}$"

    if args.benchmark: # obsluga benchmarku gil
        all_files = [p for p in target_path.rglob("*") if p.is_file() and p.stat().st_size >= 100]
        if not all_files:
            logger.warning("Brak plików spełniających kryteria do uruchomienia benchmarku.")
            return
        run_gil_benchmarks(all_files, workers=args.workers)
        return

    scanner = DuplicateScanner.from_string(str(target_path), min_size=100) #inicjalizacja skanera i wyszukiwanie duplikatow

    logger.info("Rozpoczynanie wyszukiwania duplikatów -> wątki...")
    dups_threads = scanner.find_duplicates_threads(regex_pattern=regex_filter, workers=args.workers)

    logger.info("Rozpoczynanie wyszukiwania duplikatów -> procesy...")
    dups_procs = scanner.find_duplicates_processes(regex_pattern=regex_filter, workers=args.workers)

    print(f"\nZnaleziono {len(dups_threads)} grup zduplikowanych plików:")
    for idx, (file_hash, paths) in enumerate(dups_threads.items(), 1):
        size_str = DuplicateScanner.format_bytes(paths[0].stat().st_size)
        print(f"\nGrupa #{idx} | SHA-256: {file_hash[:16]}... | Rozmiar: {size_str}")
        for p in paths:
            meta = extract_file_metadata(p.name)
            meta_info = f" [Data: {meta['date']}, Wersja: {meta['version']}]" if meta and meta['date'] else ""
            print(f"  -> {p}{meta_info}")


if __name__ == "__main__":
    main()