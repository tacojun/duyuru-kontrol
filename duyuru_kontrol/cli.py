"""Command-line interface for the announcement checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import check_text


def _non_negative(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("negatif olamaz")
    return number


def _year(value: str) -> int:
    number = int(value)
    if not 1 <= number <= 9999:
        raise argparse.ArgumentTypeError("1 ile 9999 arasında olmalı")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Türkçe duyurularda tarih geçerliliğini, tarih-gün eşleşmesini ve karakter sınırını kontrol et."
    )
    parser.add_argument("files", metavar="DOSYA", nargs="+", help="UTF-8 dosyalar; standart girdi için -")
    parser.add_argument("--year", type=_year, help="Yıl yazılmayan tarihler için yıl")
    parser.add_argument("--max-chars", type=_non_negative, help="İsteğe bağlı karakter sınırı")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    if args.files.count("-") > 1:
        parser.error("standart girdi yalnızca bir kez kullanılabilir")

    results = []
    for filename in args.files:
        try:
            text = sys.stdin.read() if filename == "-" else Path(filename).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            parser.exit(2, f"{filename}: okunamadı: {error}\n")
        report = check_text(text, year=args.year, max_chars=args.max_chars)
        results.append({"file": filename, **report.to_dict()})

    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for item in results:
            print(f"{item['file']}: {item['characters']} karakter, {item['checked_dates']} tarih; "
                  f"{'OK' if item['ok'] else 'HATA'}")
            for diagnostic in item["diagnostics"]:
                print(f"  {diagnostic['line']}:{diagnostic['column']} "
                      f"{diagnostic['code']}: {diagnostic['message']}")
    return int(any(not item["ok"] for item in results))
