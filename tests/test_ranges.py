import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from duyuru_kontrol import check_text


class RangeChecks(unittest.TestCase):
    def test_valid_range_counts_both_endpoints(self):
        report = check_text("24–25 Eylül 2026")
        self.assertTrue(report.ok)
        self.assertEqual(report.checked_dates, 2)

    def test_separators_and_surrounding_whitespace(self):
        for separator in ("-", "–", "—"):
            for space in ("", " ", "  ", "\t"):
                with self.subTest(separator=separator, space=space):
                    report = check_text(f"24{space}{separator}{space}25 Eylül 2026")
                    self.assertTrue(report.ok)
                    self.assertEqual(report.checked_dates, 2)

    def test_invalid_start_preserves_endpoint_location(self):
        report = check_text("Duyuru\nTarih: 31–24 Eylül 2026")
        self.assertEqual(report.checked_dates, 2)
        self.assertEqual([d.code for d in report.diagnostics], ["INVALID_DATE"])
        self.assertEqual((report.diagnostics[0].line, report.diagnostics[0].column), (2, 8))
        self.assertIn("31", report.diagnostics[0].message)

    def test_reversed_range_is_reported_at_start(self):
        report = check_text("Duyuru\nTarih: 25–24 Eylül 2026")
        self.assertEqual(report.checked_dates, 2)
        self.assertEqual([d.code for d in report.diagnostics], ["REVERSED_RANGE"])
        self.assertEqual((report.diagnostics[0].line, report.diagnostics[0].column), (2, 8))

    def test_non_leap_year_invalid_end_location(self):
        report = check_text("Duyuru\nTarih: 28 – 29 Şubat 2025")
        self.assertEqual(report.checked_dates, 2)
        self.assertEqual([d.code for d in report.diagnostics], ["INVALID_DATE"])
        self.assertEqual((report.diagnostics[0].line, report.diagnostics[0].column), (2, 13))
        self.assertIn("29", report.diagnostics[0].message)

    def test_leap_year_range_is_valid(self):
        for year in (2024, 2000):
            with self.subTest(year=year):
                report = check_text(f"28–29 Şubat {year}")
                self.assertTrue(report.ok)
                self.assertEqual(report.checked_dates, 2)

    def test_both_invalid_endpoints_are_reported_without_order_check(self):
        report = check_text("32–31 Eylül 2026")
        self.assertEqual(report.checked_dates, 2)
        self.assertEqual([d.code for d in report.diagnostics], ["INVALID_DATE", "INVALID_DATE"])
        self.assertEqual([d.column for d in report.diagnostics], [1, 4])

    def test_equal_endpoints_are_valid(self):
        report = check_text("24–24 Eylül 2026")
        self.assertTrue(report.ok)
        self.assertEqual(report.checked_dates, 2)

    def test_missing_year_counts_candidates_and_requires_year(self):
        report = check_text("Tarih: 24–25 Eylül")
        self.assertEqual(report.checked_dates, 2)
        self.assertEqual([d.code for d in report.diagnostics], ["YEAR_REQUIRED"])
        self.assertEqual(report.diagnostics[0].column, 8)

    def test_explicit_year_option_is_used(self):
        self.assertTrue(check_text("28–29 Şubat", year=2024).ok)
        report = check_text("28–29 Şubat", year=2025)
        self.assertEqual(report.checked_dates, 2)
        self.assertEqual([d.code for d in report.diagnostics], ["INVALID_DATE"])

    def test_year_conflict_precedes_calendar_checks(self):
        report = check_text("31–24 Eylül 2026", year=2025)
        self.assertEqual(report.checked_dates, 2)
        self.assertEqual([d.code for d in report.diagnostics], ["YEAR_CONFLICT"])
        self.assertEqual(report.diagnostics[0].column, 1)

    def test_two_years_on_range_preserve_ambiguity_error(self):
        report = check_text("24–25 Eylül 2026 Cuma 2027")
        self.assertEqual(report.checked_dates, 2)
        self.assertEqual([d.code for d in report.diagnostics], ["AMBIGUOUS_YEAR"])
        self.assertEqual(report.diagnostics[0].column, 1)

    def test_range_weekday_is_explicitly_ambiguous(self):
        for text in ("24–25 Eylül 2026 Cuma", "24–25 Eylül Cuma 2026",
                     "24–25 Eylül 2026 Perşembe–Cuma"):
            with self.subTest(text=text):
                report = check_text(text)
                self.assertEqual(report.checked_dates, 2)
                self.assertEqual([d.code for d in report.diagnostics], ["AMBIGUOUS_RANGE_WEEKDAY"])
                self.assertEqual(report.diagnostics[0].column, 1)

    def test_ambiguous_weekday_does_not_hide_calendar_or_order_errors(self):
        for text, code in (("31–24 Eylül 2026 Cuma", "INVALID_DATE"),
                           ("25–24 Eylül 2026 Cuma", "REVERSED_RANGE")):
            with self.subTest(text=text):
                report = check_text(text)
                self.assertEqual([d.code for d in report.diagnostics],
                                 [code, "AMBIGUOUS_RANGE_WEEKDAY"])

    def test_mixed_ranges_and_single_dates_do_not_overlap(self):
        report = check_text("24–25 Eylül 2026; 26 Eylül 2026 Cumartesi; 27.09.2026; 28–29 Eylül 2026")
        self.assertTrue(report.ok)
        self.assertEqual(report.checked_dates, 6)

    def test_turkish_month_variants_preserve_validation(self):
        self.assertTrue(check_text("1–2 NİSAN 2026").ok)
        report = check_text("24–25 MAYİS 2026")
        self.assertEqual(report.checked_dates, 2)
        self.assertEqual([d.code for d in report.diagnostics], ["INVALID_MONTH"])

    def test_range_and_character_limit_errors_coexist(self):
        report = check_text("25–24 Eylül 2026\r\n", max_chars=15)
        self.assertEqual(report.characters, 16)
        self.assertEqual(report.checked_dates, 2)
        self.assertEqual([d.code for d in report.diagnostics], ["REVERSED_RANGE", "CHAR_LIMIT_EXCEEDED"])


class RangeCliChecks(unittest.TestCase):
    def run_range_cli(self, text, *args):
        result = subprocess.run(
            [sys.executable, "-m", "duyuru_kontrol", "-", "--format", "json", *args],
            input="Duyuru\nTarih: " + text, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.stderr, "")
        reports = json.loads(result.stdout)
        self.assertEqual(len(reports), 1)
        report = reports[0]
        self.assertEqual(report["file"], "-")
        self.assertEqual(report["checked_dates"], 2)
        self.assertEqual(report["characters"], len("Duyuru\nTarih: " + text))
        return result, report

    def test_valid_ranges_json_exit_and_count(self):
        for text in ("24–25 Eylül 2026", "28—29 Şubat 2024", "24 - 25 Eylül 2026"):
            with self.subTest(text=text):
                result, report = self.run_range_cli(text)
                self.assertEqual(result.returncode, 0)
                self.assertTrue(report["ok"])
                self.assertEqual(report["diagnostics"], [])

    def test_invalid_and_reversed_ranges_json_exit_and_locations(self):
        cases = (("31–24 Eylül 2026", "INVALID_DATE", 8),
                 ("25–24 Eylül 2026", "REVERSED_RANGE", 8),
                 ("28–29 Şubat 2025", "INVALID_DATE", 11))
        for text, code, column in cases:
            with self.subTest(text=text):
                result, report = self.run_range_cli(text)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(report["ok"])
                self.assertEqual([d["code"] for d in report["diagnostics"]], [code])
                self.assertEqual((report["diagnostics"][0]["line"],
                                  report["diagnostics"][0]["column"]), (2, column))

    def test_missing_year_and_option_json(self):
        result, report = self.run_range_cli("24–25 Eylül")
        self.assertEqual(result.returncode, 1)
        self.assertEqual([d["code"] for d in report["diagnostics"]], ["YEAR_REQUIRED"])
        self.assertEqual((report["diagnostics"][0]["line"], report["diagnostics"][0]["column"]), (2, 8))
        result, report = self.run_range_cli("24–25 Eylül", "--year", "2026")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["ok"])

    def test_year_conflict_json_exit_and_location(self):
        result, report = self.run_range_cli("24–25 Eylül 2026", "--year", "2025")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ok"])
        self.assertEqual([d["code"] for d in report["diagnostics"]], ["YEAR_CONFLICT"])
        self.assertEqual((report["diagnostics"][0]["line"], report["diagnostics"][0]["column"]), (2, 8))

    def test_weekday_range_is_not_reported_as_verified(self):
        result, report = self.run_range_cli("24–25 Eylül 2026 Cuma")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ok"])
        self.assertEqual([d["code"] for d in report["diagnostics"]], ["AMBIGUOUS_RANGE_WEEKDAY"])
        self.assertEqual((report["diagnostics"][0]["line"], report["diagnostics"][0]["column"]), (2, 8))

    def test_file_range_json_preserves_end_location(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duyuru.txt"
            path.write_text("Duyuru\nTarih: 28 – 29 Şubat 2025\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "duyuru_kontrol", str(path), "--format", "json"],
                text=True, capture_output=True, check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        reports = json.loads(result.stdout)
        self.assertEqual(len(reports), 1)
        report = reports[0]
        self.assertEqual(report["file"], str(path))
        self.assertEqual(report["characters"], len("Duyuru\nTarih: 28 – 29 Şubat 2025"))
        self.assertEqual(report["checked_dates"], 2)
        self.assertFalse(report["ok"])
        self.assertEqual([d["code"] for d in report["diagnostics"]], ["INVALID_DATE"])
        self.assertEqual((report["diagnostics"][0]["line"], report["diagnostics"][0]["column"]), (2, 13))


if __name__ == "__main__":
    unittest.main()
