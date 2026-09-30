"""Tarih geçerliliği, tarih-gün eşleşmesi ve karakter sınırı kontrolleri."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import re

MONTHS = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}
WEEKDAYS = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")
_WEEKDAY_RE = "|".join(WEEKDAYS)
_MONTH_RE = "|".join(MONTHS)

# A weekday is optional: always validate the date, then compare its weekday if
# one is stated. Named dates may take their year from the explicit --year option.
_NAMED_DATE = re.compile(
    rf"(?<!\w)(?P<day>\d{{1,2}})\s+(?P<month>{_MONTH_RE})(?!\w)"
    rf"(?:\s+(?P<year>\d{{4}})(?!\w))?"
    rf"(?:\s+(?P<weekday>{_WEEKDAY_RE})(?!\w)"
    rf"(?:\s+(?P<year_after>\d{{4}})(?!\w))?)?",
    re.IGNORECASE,
)
_NUMERIC_DATE = re.compile(
    rf"(?<![\w.])(?P<day>\d{{1,2}})\.(?P<month>\d{{1,2}})\."
    rf"(?P<year>\d{{4}})(?!\w|\.\d)"
    rf"(?:\s+(?P<weekday>{_WEEKDAY_RE})(?!\w))?",
    re.IGNORECASE,
)


def _tr_lower(value: str) -> str:
    """Lowercase Turkish I/İ independently of the process locale."""
    return value.translate(str.maketrans({"I": "ı", "İ": "i"})).lower()


def _location(text: str, offset: int) -> tuple[int, int]:
    return text.count("\n", 0, offset) + 1, offset - text.rfind("\n", 0, offset)


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    line: int
    column: int

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


@dataclass(frozen=True)
class Report:
    characters: int
    checked_dates: int
    diagnostics: tuple[Diagnostic, ...]

    @property
    def ok(self) -> bool:
        return not self.diagnostics

    def to_dict(self) -> dict[str, object]:
        return {
            "characters": self.characters,
            "checked_dates": self.checked_dates,
            "ok": self.ok,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


def check_text(text: str, *, year: int | None = None, max_chars: int | None = None) -> Report:
    """Validate dates, compare stated weekdays and optionally limit characters.

    A single final line ending is ignored because text files commonly contain
    one. Internal line breaks and other characters are counted.
    """
    if year is not None and not 1 <= year <= 9999:
        raise ValueError("year must be between 1 and 9999")
    if max_chars is not None and max_chars < 0:
        raise ValueError("max_chars must be non-negative")

    if text.endswith("\r\n"):
        content = text[:-2]
    elif text.endswith("\n"):
        content = text[:-1]
    else:
        content = text
    diagnostics: list[Diagnostic] = []
    matches = sorted(
        (*_NAMED_DATE.finditer(content), *_NUMERIC_DATE.finditer(content)),
        key=lambda match: match.start(),
    )

    for match in matches:
        line, column = _location(content, match.start())
        first_year = match.group("year")
        last_year = match.groupdict().get("year_after")
        if first_year and last_year:
            diagnostics.append(Diagnostic(
                "AMBIGUOUS_YEAR", "Aynı tarihte iki yıl yazılmış.", line, column,
            ))
            continue
        supplied_year = first_year or last_year
        if supplied_year and year is not None and int(supplied_year) != year:
            diagnostics.append(Diagnostic(
                "YEAR_CONFLICT",
                f"Metindeki {supplied_year} yılı --year {year} ile uyuşmuyor.",
                line, column,
            ))
            continue
        actual_year = int(supplied_year) if supplied_year else year
        if actual_year is None:
            diagnostics.append(Diagnostic(
                "YEAR_REQUIRED",
                "Yıl belirtilmemiş; --year ile verin veya tarihe yılı ekleyin.",
                line, column,
            ))
            continue

        month_token = _tr_lower(match.group("month"))
        if month_token.isdigit():
            month = int(month_token)
        else:
            month = MONTHS.get(month_token)
            if month is None:
                diagnostics.append(Diagnostic(
                    "INVALID_MONTH", f"Geçersiz ay adı: {match.group('month')}.", line, column,
                ))
                continue
        try:
            actual_date = date(actual_year, month, int(match.group("day")))
        except ValueError:
            diagnostics.append(Diagnostic(
                "INVALID_DATE", f"Geçersiz tarih: {match.group(0)}.", line, column,
            ))
            continue

        stated_day = match.group("weekday")
        expected_day = WEEKDAYS[actual_date.weekday()]
        if stated_day is not None and _tr_lower(stated_day) != _tr_lower(expected_day):
            diagnostics.append(Diagnostic(
                "WEEKDAY_MISMATCH",
                f"{actual_date:%d.%m.%Y} için doğru gün {expected_day}; metinde {match.group('weekday')} yazıyor.",
                line, column,
            ))

    if max_chars is not None and len(content) > max_chars:
        diagnostics.append(Diagnostic(
            "CHAR_LIMIT_EXCEEDED",
            f"Metin {len(content)} karakter; sınır {max_chars} (aşım: {len(content) - max_chars}).",
            1, 1,
        ))

    return Report(len(content), len(matches), tuple(diagnostics))
