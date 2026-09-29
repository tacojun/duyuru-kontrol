import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CliChecks(unittest.TestCase):
    def run_cli(self, *args, input_text=None):
        return subprocess.run(
            [sys.executable, "-m", "duyuru_kontrol", *args],
            input=input_text, text=True, capture_output=True, check=False,
        )

    def test_stdin_json_success(self):
        result = self.run_cli("-", "--year", "2026", "--format", "json",
                              input_text="24 Eylül Perşembe")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)[0]["ok"])

    def test_file_error_exit_and_location(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duyuru.txt"
            path.write_text("GTO\n24 Eylül 2026 Çarşamba", encoding="utf-8")
            result = self.run_cli(str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("2:1 WEEKDAY_MISMATCH", result.stdout)

    def test_missing_file_is_not_reported_as_success(self):
        result = self.run_cli("/does-not-exist.txt")
        self.assertEqual(result.returncode, 2)
        self.assertIn("okunamadı", result.stderr)

    def test_invalid_month_variant_returns_diagnostic_instead_of_crashing(self):
        result = self.run_cli("-", "--format", "json",
                              input_text="24 MAYİS 2026 Pazar")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)[0]["diagnostics"][0]["code"], "INVALID_MONTH")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
