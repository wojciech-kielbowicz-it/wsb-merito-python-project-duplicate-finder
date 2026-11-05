import re
from typing import Optional, Dict

VALID_EXTENSION_RE = re.compile(r"^\.[a-zA-Z0-9]{1,10}$") # walidacja pliku - pełne dopasowanie


FILENAME_META_RE = re.compile(r"""     # Ekstrakcja danych z pliku + verbose - lazy match
    ^
    (?P<prefix>[a-zA-Z0-9_-]+?)           #Nazwa pliku
    (?:_(?P<date>\d{4}-\d{2}-\d{2}))?     # Opcjonalna data w formacie YYYY-MM-DD
    (?:_v(?P<version>\d+))?               # Opcjonalny numer wersji np. _v1 itd.
    \.(?P<ext>[a-zA-Z0-9]+)               # Rozszerzenie pliku
    $
""", re.VERBOSE)


def is_valid_extension(ext: str) -> bool:
    """Waliduje format rozszerzenia pliku (np. '.txt', '.log')."""
    return VALID_EXTENSION_RE.fullmatch(ext) is not None


def extract_file_metadata(filename: str) -> Optional[Dict[str, Optional[str]]]:
    """Wyciąga ustrukturyzowane metadane z nazwy pliku przy użyciu grup nazwanych."""
    match = FILENAME_META_RE.search(filename)
    if match:
        return match.groupdict()
    return None