"""Check an installed distribution from outside the source checkout.

Run with the target virtual environment's Python, in isolated mode:
    /path/to/venv/bin/python -I /path/to/scripts/check_installed.py --expected-version 0.2.0
"""

import argparse
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import unittest

import duyuru_kontrol
from duyuru_kontrol import check_text


class InstalledPackageChecks(unittest.TestCase):
    def run_cli(self, text, options, *, module=False):
        command = ([sys.executable, "-I", "-m", "duyuru_kontrol"] if module else
                   [str(Path(sys.executable).parent / "duyuru-kontrol")])
        command.extend(["-", "--format", "json"])
        for name, value in options.items():
            command.extend(["--" + name.replace("_", "-"), str(value)])
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        result = subprocess.run(command, input=text, text=True, capture_output=True,
                                check=False, env=environment)
        self.assertEqual(result.stderr, "")
        reports = json.loads(result.stdout)
        self.assertEqual(len(reports), 1)
        return result.returncode, reports[0]

    def test_package_origin_and_version(self):
        source = Path(__file__).resolve().parents[1]
        self.assertFalse(Path.cwd().resolve().is_relative_to(source),
                         "Run this check outside the source checkout")
        module = Path(duyuru_kontrol.__file__).resolve()
        purelib = Path(sysconfig.get_path("purelib")).resolve()
        self.assertTrue(module.is_relative_to(purelib), str(module))
        distribution = metadata.distribution("duyuru-kontrol")
        self.assertEqual(module, Path(distribution.locate_file(
            "duyuru_kontrol/__init__.py")).resolve())
        self.assertEqual(distribution.version, EXPECTED_VERSION)
        self.assertEqual(distribution.requires or [], [])
        print(f"Installed duyuru-kontrol {distribution.version}: {module}")

    def test_console_and_api_scenarios(self):
        # Check JSON fields and locations as well as success/failure. The API
        # and console command must come from the same installed distribution.
        cases = (
            ("valid date", "24 Eylül 2026 Perşembe", {}, 1, (), ()),
            ("numeric date", "24.09.2026", {}, 1, (), ()),
            ("wrong weekday", "24 Eylül 2026 Çarşamba", {}, 1,
             ("WEEKDAY_MISMATCH",), ((2, 8),)),
            ("invalid date", "31 Eylül 2026", {}, 1, ("INVALID_DATE",), ((2, 8),)),
            ("valid range", "24–25 Eylül 2026", {}, 2, (), ()),
            ("reversed range", "25–24 Eylül 2026", {}, 2,
             ("REVERSED_RANGE",), ((2, 8),)),
            ("invalid start", "31–24 Eylül 2026", {}, 2, ("INVALID_DATE",), ((2, 8),)),
            ("invalid end", "28–29 Şubat 2025", {}, 2, ("INVALID_DATE",), ((2, 11),)),
            ("leap year", "28–29 Şubat 2024", {}, 2, (), ()),
            ("both invalid", "32–31 Eylül 2026", {}, 2,
             ("INVALID_DATE", "INVALID_DATE"), ((2, 8), (2, 11))),
            ("missing year", "24–25 Eylül", {}, 2, ("YEAR_REQUIRED",), ((2, 8),)),
            ("year option", "24–25 Eylül", {"year": 2026}, 2, (), ()),
            ("year conflict", "24–25 Eylül 2026", {"year": 2025}, 2,
             ("YEAR_CONFLICT",), ((2, 8),)),
            ("character limit", "24 Eylül 2026", {"max_chars": 1}, 1,
             ("CHAR_LIMIT_EXCEEDED",), ((1, 1),)),
            ("ambiguous weekday", "24–25 Eylül 2026 Cuma", {}, 2,
             ("AMBIGUOUS_RANGE_WEEKDAY",), ((2, 8),)),
        )
        for name, date_text, options, count, codes, locations in cases:
            with self.subTest(case=name):
                text = "Duyuru\nTarih: " + date_text
                exit_code, report = self.run_cli(text, options)
                self.assertEqual(exit_code, int(bool(codes)))
                self.assertEqual(report["file"], "-")
                self.assertEqual(report["characters"], len(text))
                self.assertEqual(report["checked_dates"], count)
                self.assertEqual(report["ok"], not codes)
                self.assertEqual(tuple(d["code"] for d in report["diagnostics"]), codes)
                self.assertEqual(tuple((d["line"], d["column"])
                                       for d in report["diagnostics"]), locations)
                self.assertEqual({k: v for k, v in report.items() if k != "file"},
                                 check_text(text, **options).to_dict())

    def test_python_module_entry_point(self):
        exit_code, report = self.run_cli("24–25 Eylül 2026", {}, module=True)
        self.assertEqual(exit_code, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["checked_dates"], 2)
        self.assertEqual(report["diagnostics"], [])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-version", required=True)
    EXPECTED_VERSION = parser.parse_args().expected_version
    unittest.main(argv=[sys.argv[0]], verbosity=2)
