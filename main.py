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


