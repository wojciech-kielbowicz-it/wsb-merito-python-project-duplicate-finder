from pathlib import Path
from typing import Iterator

class FileChunkIterator:
    """
    Własny iterator czytający plik binarny blokami o zadanym rozmiarze.
    Gwarantuje niskie zużycie pamięci RAM nawet dla plików wielogigabajtowych.
    """
    def __init__(self, file_path: Path | str, chunk_size: int = 65536) -> None:
        if chunk_size <= 0:
            raise ValueError("Rozmiar bloku (chunk_size) musi być dodatni.")
        self.file_path = Path(file_path)
        self.chunk_size = chunk_size
        self._file = None

    def __iter__(self) -> Iterator[bytes]:
        self._file = open(self.file_path, "rb")
        return self

    def __next__(self) -> bytes:
        if self._file is None or self._file.closed:
            raise StopIteration

        chunk = self._file.read(self.chunk_size)
        if not chunk:
            self._file.close()
            raise StopIteration
        return chunk

    def __del__(self) -> None:
        if self._file and not self._file.closed:
            self._file.close()