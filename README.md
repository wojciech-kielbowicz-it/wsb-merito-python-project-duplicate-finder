# Wyszukiwarka zduplikowanych plików

Projekt zaliczeniowy z przedmiotu **Zaawansowane techniki programowania w języku Python**.

## Opis projektu

Program służy do wyszukiwania zduplikowanych plików w wybranym katalogu nadrzędnym oraz jego podkatalogach. Zamiast polegać na nazwach plików (które mogą być różne dla identycznych danych), aplikacja porównuje ich faktyczną zawartość. Aby uniknąć zbędnego czytania wszystkich plików, skaner działa dwuetapowo:

1. Najpierw rekurencyjnie skanuje dysk i szybko grupuje pliki po ich rozmiarze w bajtach – jeśli plik ma unikalny rozmiar, od razu zostaje odrzucony jako kandydat na duplikat.
2. Następnie dla plików o tym samym rozmiarze obliczany jest skrót kryptograficzny SHA-256 (czytany porcjami po 64 KB, żeby nie zapychać pamięci RAM). Pliki z takim samym skrótem trafiają do raportu.

Dodatkowo aplikacja posiada ekran powitalny z opisem opcji, obsługuje zarówno argumenty wiersza poleceń (CLI), jak i tryb interaktywny, potrafi wyciągać metadane (datę i wersję) z nazw plików za pomocą wyrażeń regularnych, ma wbudowany generator plików testowych oraz moduł benchmarku do badania wpływu GIL.

## Wymagania i uruchomienie

Projekt wymaga **Pythona 3.12+** (testowany na **CPython 3.14.4**) i korzysta wyłącznie z biblioteki standardowej, więc nie ma potrzeby instalowania dodatkowych paczek ani pliku `requirements.txt`.

1. **Tryb interaktywny (najprostszy):**
   ```bash
   python3 main.py
   ```
   Po uruchomieniu program wyświetla ekran powitalny ze spisem flag, pozwala wpisać parametry bezpośrednio w konsoli (np. `--benchmark --workers 4`), a następnie pyta o ścieżkę do folderu nadrzędnego (wciśnięcie Enter używa lub tworzy domyślny folder `test_data`).

2. **Wygenerowanie świeżych danych testowych i wyszukiwanie duplikatów:**
   ```bash
   python3 main.py --generate --workers 4
   ```

3. **Skanowanie konkretnego katalogu z filtrowaniem po rozszerzeniu:**
   ```bash
   python3 main.py -d /sciezka/do/folderu --ext .bin
   ```

4. **Uruchomienie benchmarku porównawczego GIL:**
   ```bash
   python3 main.py --benchmark --workers 4
   ```
4. **Uruchomienie testów:**
   ```bash
   python3 -m unittest discover -s tests -v


## Tabela mapowania zagadnień

| # | Zagadnienie | Gdzie w kodzie (plik / klasa / funkcja) |
|---|---|---|
| 1 | **Dekoratory funkcji** (w tym z parametrami + `functools.wraps`) | `core/decorators.py` → `measure_time`, `retry(attempts, delay, exceptions)` |
| 2 | **Dekoratory metod** (własny z `self` + wbudowane) | `core/decorators.py` → `requires_valid_root`; `core/scanner.py` → `@property`, `@min_size.setter`, `@classmethod` (`from_string`), `@staticmethod` (`format_bytes`) |
| 3 | **Własny iterator** (`__iter__`, `__next__`) | `core/reader.py` → klasa `FileChunkIterator` |
| 4 | **Generatory, `yield from` i potok (pipeline)** | `core/walker.py` → `scan_directory_recursive`, wyrażenia generujące w `filter_by_regex` i `filter_by_min_size`, potok `build_file_pipeline` |
| 5 | **Wyrażenia regularne** (walidacja, ekstrakcja, grupy nazwane) | `core/patterns.py` → `VALID_EXTENSION_RE` (`fullmatch`), `FILENAME_META_RE` (`re.VERBOSE`, grupy nazwane `(?P<name>...)`, `groupdict()`) |
| 6 | **Wątki (I/O) i synchronizacja** | `core/scanner.py` → `ThreadPoolExecutor` oraz `threading.Lock` w `_group_candidates_by_size_threaded` i `find_duplicates_threads` |
| 7 | **Procesy (CPU)** | `core/scanner.py` → `ProcessPoolExecutor` w `find_duplicates_processes` |
| 8 | **Pomiar i analiza GIL** | `benchmarks/gil_benchmark.py` → `run_gil_benchmarks()`; `core/scanner.py` → `compute_pure_python_checksum` vs `compute_sha256` |

## Wyniki pomiarów wydajności i wnioski dotyczące GIL

Benchmark został uruchomiony poleceniem z flagami `--benchmark --workers 4` na zestawie **24 plików testowych** (8 grup po dwa duplikaty 512 KB + 8 unikalnych plików po 1 KB).

**Środowisko uruchomieniowe:**
* Wersja Pythona: `3.14.4` (standardowa kompilacja CPython)
* Liczba rdzeni CPU: `8`
* Interwał przełączania wątków: `0.005 s`
* Kompilacja free-threading: `False` | GIL aktywny: `True`

### Tabela wyników

| Test | Sekwencyjnie | 4 Wątki (`ThreadPoolExecutor`) | 4 Procesy (`ProcessPoolExecutor`) |
|---|---|---|---|
| **Test 1: Czysty Python CPU-bound** (`compute_pure_python_checksum`) | `1.2205 s` | `1.2135 s` (**1.01x**) | `0.4871 s` (**2.51x**) |
| **Test 2: I/O + Biblioteka C** (`hashlib.sha256`) | `0.0333 s` | `0.0123 s` (**2.71x**) | `0.0258 s` (**1.29x**) |

### Wnioski dotyczące Global Interpreter Lock (GIL)

1. W **Teście 1 (czysty Python CPU-bound)** obliczenia wykonywane są w całości w pętli bajtkodu Pythona, gdzie blokada GIL jest cały czas trzymana. Przez to uruchomienie 4 wątków nie dało praktycznie żadnego przyspieszenia (`1.2135 s` względem `1.2205 s`, czyli zaledwie `1.01x`), ponieważ w danej chwili kod Pythona i tak wykonywał tylko jeden wątek.
2. Zastosowanie `ProcessPoolExecutor` w tym samym teście pozwoliło ominąć GIL, ponieważ każdy z 4 procesów ma własny interpreter i może pracować równolegle na osobnym rdzeniu CPU – czas spadł do `0.4871 s` (przyspieszenie **2.51x**).
3. W **Teście 2 (`hashlib.sha256`)** sytuacja całkowicie się odwróciła i najszybsze okazały się wątki (`0.0123 s`, przyspieszenie **2.71x**). Dzieje się tak, ponieważ odczyt bloków pliku z dysku (I/O) oraz napisana w języku C funkcja licząca SHA-256 w module `hashlib` jawnie zwalniają blokadę GIL.
4. Dzięki temu wątki mogły liczyć skróty naprawdę równolegle bez kosztu tworzenia osobnych procesów systemowych.
5. Procesy w Teście 2 też przyspieszyły względem wersji sekwencyjnej (`0.0258 s`, czyli **1.29x**), ale wypadły ponad dwa razy gorzej od wątków – przy tak krótkim całkowitym czasie obliczeń (`~0.03 s`) duży udział w czasie wykonania miał narzut na uruchomienie puli procesów i przesyłanie danych przez `pickle`.
6. Praktyczny wniosek z pomiarów jest taki, że do obliczeń w czystym Pythonie należy używać procesów, natomiast do operacji dyskowych oraz bibliotek C zwalniających GIL (jak `hashlib`) znacznie lepiej sprawdzają się lekkie wątki.

## Problemy napotkane w trakcie realizacji

* **Błąd serializacji (`pickle`) przy `ProcessPoolExecutor`:** Początkowo funkcja obliczająca SHA-256 była metodą wewnątrz klasy `DuplicateScanner`. Przy próbie uruchomienia jej na wielu procesach Python próbował zserializować cały obiekt `self`, co kończyło się błędem, ponieważ obiekt posiadał atrybut `threading.Lock` (którego nie da się zserializować). Problem rozwiązałem poprzez przeniesienie `compute_sha256` i `compute_pure_python_checksum` na poziom modułu w `core/scanner.py`.
* **Bezpieczne podawanie ścieżki i ryzyko usunięcia plików:** W pierwszej wersji skryptu brak folderu automatycznie uruchamiał generator danych, a podanie `--generate` z własną ścieżką mogło usunąć jej zawartość przez `shutil.rmtree`. Przebudowałem `main.py`, dodając walidację istnienia katalogu, ekran powitalny oraz tryb interaktywny z bezpiecznym parsowaniem parametrów przez `shlex.split`.


