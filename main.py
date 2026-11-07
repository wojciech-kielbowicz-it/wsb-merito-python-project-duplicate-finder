import argparse
import logging
import os
import shutil
from pathlib import Path
from typing import List

from core.patterns import extract_file_metadata, is_valid_extension
from core.scanner import DuplicateScanner

logging.basicConfig( # Logi -> godzina, poziom logowania
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("DuplicateFinder")


def generate_test_dataset(target_dir: Path, num_groups: int = 8, file_size_kb: int = 512) -> List[Path]:
    """Generuje zestaw plików testowych (w tym celowe duplikaty) do skanowania i benchmarku"""
    
    
    if target_dir.exists(): # czyszczenie starego katalogu
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
    parser.add_argument("--dir", type=str, default="test_data", help="Katalog do przeskanowania")
    parser.add_argument("--generate", action="store_true", help="Wygeneruj testowy zestaw plików przed działaniem")
    parser.add_argument("--workers", type=int, default=4, help="Liczba wątków/procesów roboczych")
    parser.add_argument("--ext", type=str, default=None, help="Filtruj tylko wybrane rozszerzenie (np. .bin)")
    args = parser.parse_args() # podanie argumetow powyzej

    target_path = Path(args.dir)

    # Autogenerowanie folderow jesli podane jest rozszerzenie po fladze --ext lub wpisana jest flaga --generate
    if args.generate or not target_path.exists():
        generate_test_dataset(target_path)

    # Domyślnie kazde rozszerzenie. Jesli podano jakies rozszerzenia po --ext to tylko te rozszerzenie
    regex_filter = r".*"
    if args.ext:
        if not is_valid_extension(args.ext):
            logger.error(f"Nieprawidłowy format rozszerzenia: '{args.ext}' (wymagana kropka np. '.bin')")
            return
        regex_filter = rf"\{args.ext}$"

    # Inicjalizacja skanera (bez plikow ponizej 100 b )
    scanner = DuplicateScanner.from_string(str(target_path), min_size=100)


    # Porownania 
    logger.info("Rozpoczynanie wyszukiwania duplikatów -> wątki...") # watki
    dups_threads = scanner.find_duplicates_threads(regex_pattern=regex_filter, workers=args.workers)

    logger.info("Rozpoczynanie wyszukiwania duplikatów -> procesy...") # procesy
    dups_procs = scanner.find_duplicates_processes(regex_pattern=regex_filter, workers=args.workers)

    
    print(f"\nZnaleziono {len(dups_threads)} grup zduplikowanych plików:") # Formatowanie i wyswietlanie
    for idx, (file_hash, paths) in enumerate(dups_threads.items(), 1):
        size_str = DuplicateScanner.format_bytes(paths[0].stat().st_size)
        print(f"\nGrupa #{idx} | SHA-256: {file_hash[:16]}... | Rozmiar: {size_str}") # Pokazujemy tylko początek hasha SHA (dla czytelnosci)
        for p in paths:
            meta = extract_file_metadata(p.name) # Wyciagamy metadane z nazwy (jesli regex dopasuje date i nazwe info jest doklejane na koniec)
            meta_info = f" [Data: {meta['date']}, Wersja: {meta['version']}]" if meta and meta['date'] else ""
            print(f"  -> {p}{meta_info}")


if __name__ == "__main__":
    main()
