import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.vac_module_analyzer import INTEGRITY_PRIMITIVES, main, scan_binary_bytes


class TestVacModuleAnalyzer(unittest.TestCase):
    def test_scan_binary_bytes_detects_ascii_and_utf16_primitives(self):
        sample = b"\x00\x00NtQueryVirtualMemory\x00\x00" + "K32GetMappedFileNameW".encode("utf-16le")
        hits = scan_binary_bytes(sample)
        self.assertIn("NtQueryVirtualMemory", hits)
        self.assertIn("K32GetMappedFileNameW", hits)
        self.assertEqual(hits["NtQueryVirtualMemory"], [2])

    def test_cli_standalone_file_scan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pe_path = Path(tmpdir) / "sample.dll"
            pe_path.write_bytes(b"MZ\x90\x00VirtualQueryEx\x00NtQueryVirtualMemory\x00")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = main([str(pe_path)])
            self.assertEqual(rc, 0)
            self.assertIn("VirtualQueryEx", buf.getvalue())
            self.assertIn("NtQueryVirtualMemory", buf.getvalue())

    def test_primitives_list_non_empty(self):
        self.assertGreaterEqual(len(INTEGRITY_PRIMITIVES), 7)


if __name__ == "__main__":
    unittest.main()
