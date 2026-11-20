import tempfile
import unittest
from pathlib import Path

from core.patterns import is_valid_extension, extract_file_metadata
from core.reader import FileChunkIterator
from core.scanner import DuplicateScanner


class TestDuplicateFinderProject(unittest.TestCase):

    def test_regex_validation_and_extraction(self) -> None:
        self.assertTrue(is_valid_extension(".bin"))
        self.assertFalse(is_valid_extension("bin"))

        meta = extract_file_metadata("raport_2026-10-21_v3.pdf")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["prefix"], "raport")
        self.assertEqual(meta["date"], "2026-10-21")
        self.assertEqual(meta["version"], "3")
        self.assertEqual(meta["ext"], "pdf")

    def test_custom_chunk_iterator(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"ABCDEFGHIJ")
            tmp_path = Path(tmp.name)

        try:
            chunks = list(FileChunkIterator(tmp_path, chunk_size=4))
            self.assertEqual(chunks, [b"ABCD", b"EFGH", b"IJ"])
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_duplicate_scanner_threads_and_processes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "a.bin").write_bytes(b"same_2345")
            (root / "b.bin").write_bytes(b"same_12345")
            (root / "c.bin").write_bytes(b"uniq_99999")

            scanner = DuplicateScanner(root, min_size=5)
            res_t = scanner.find_duplicates_threads(workers=2)
            res_p = scanner.find_duplicates_processes(workers=2)

            self.assertEqual(len(res_t), 1)
            self.assertEqual(len(res_p), 1)
            found_files = list(res_t.values())[0]
            self.assertEqual(len(found_files), 2)


if __name__ == "__main__":
    unittest.main()