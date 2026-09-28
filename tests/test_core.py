import unittest

from duyuru_kontrol import check_text


class DateChecks(unittest.TestCase):
    def test_named_date_with_explicit_year(self):
        report = check_text("Etkinlik 24 Eylül 2026 Perşembe günü yapılacak.")
        self.assertTrue(report.ok)
        self.assertEqual(report.checked_dates, 1)

    def test_year_after_weekday_and_case_insensitive_month(self):
        report = check_text("24 EYLÜL Perşembe 2026")
        self.assertTrue(report.ok)
        self.assertEqual(report.checked_dates, 1)

    def test_wrong_weekday_is_diagnosed(self):
        report = check_text("Açılış\n24 Eylül 2026 Çarşamba")
        self.assertEqual(report.diagnostics[0].code, "WEEKDAY_MISMATCH")
        self.assertEqual((report.diagnostics[0].line, report.diagnostics[0].column), (2, 1))
        self.assertIn("Perşembe", report.diagnostics[0].message)

    def test_year_argument_checks_short_date(self):
        self.assertTrue(check_text("24 Eylül Perşembe", year=2026).ok)
        self.assertEqual(check_text("24 Eylül Perşembe").diagnostics[0].code, "YEAR_REQUIRED")

    def test_year_conflict_is_explicit(self):
        report = check_text("24 Eylül 2026 Perşembe", year=2025)
        self.assertEqual(report.diagnostics[0].code, "YEAR_CONFLICT")

    def test_numeric_and_invalid_leap_date(self):
        self.assertTrue(check_text("29.02.2024 Perşembe").ok)
        self.assertEqual(
            check_text("29.02.2025 Cumartesi").diagnostics[0].code, "INVALID_DATE"
        )

    def test_multiple_dates(self):
        report = check_text("24 Eylül 2026 Perşembe - 25 Eylül 2026 Cuma")
        self.assertTrue(report.ok)
        self.assertEqual(report.checked_dates, 2)

    def test_weekday_is_required_for_date_check(self):
        report = check_text("24 Eylül 2026")
        self.assertTrue(report.ok)
        self.assertEqual(report.checked_dates, 0)

    def test_two_years_on_one_date_are_rejected(self):
        report = check_text("24 Eylül 2026 Perşembe 2027")
        self.assertEqual(report.diagnostics[0].code, "AMBIGUOUS_YEAR")

    def test_turkish_capital_i(self):
        report = check_text("1 NİSAN 2026 ÇARŞAMBA")
        self.assertTrue(report.ok)


class LengthChecks(unittest.TestCase):
    def test_single_final_newline_is_not_counted(self):
        report = check_text("Merhaba\n", max_chars=7)
        self.assertTrue(report.ok)
        self.assertEqual(report.characters, 7)

    def test_limit_and_internal_newline(self):
        report = check_text("a\nb", max_chars=2)
        self.assertEqual(report.characters, 3)
        self.assertEqual(report.diagnostics[0].code, "CHAR_LIMIT_EXCEEDED")

    def test_only_one_final_line_ending_is_ignored(self):
        self.assertEqual(check_text("a\n\n").characters, 2)
        self.assertEqual(check_text("a\r\n").characters, 1)

    def test_negative_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            check_text("a", max_chars=-1)


if __name__ == "__main__":
    unittest.main()
