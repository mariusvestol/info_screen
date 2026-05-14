#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from playwright.sync_api import sync_playwright


APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "shift_plan.db"

DEFAULT_FILE_GUID = "FE5E7547-C649-0068-4238-91D4D682D8BD"
DEFAULT_SITE_URL = "https://aneomobility.sharepoint.com/sites/AneoMobility"
DEFAULT_PERSON_ALIASES = ("Marius V", "Marius Vestol", "Marius Vestøl")

XLSX_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
DAY_COLUMNS = {
    4: 1,   # D -> Monday
    5: 2,
    6: 3,
    7: 4,
    8: 5,
    9: 6,
    10: 7,  # J -> Sunday
}
TIME_RANGE_RE = re.compile(
    r"(?P<start_h>\d{1,2})[.:](?P<start_m>\d{2})\s*[-–]\s*"
    r"(?P<end_h>\d{1,2})[.:](?P<end_m>\d{2})"
)


@dataclass(frozen=True)
class Shift:
    person: str
    shift_date: str
    start_time: str
    end_time: str
    raw_value: str
    source_sheet: str
    source_cell: str
    source_week: int

    @property
    def id(self) -> str:
        return "|".join(
            [
                normalize_text(self.person),
                self.shift_date,
                self.start_time,
                self.end_time,
                self.source_cell,
            ]
        )


def load_dotenv() -> None:
    env_path = APP_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def normalize_text(value: object) -> str:
    text = str(value or "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip().casefold()


def parse_aliases(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return DEFAULT_PERSON_ALIASES
    aliases = tuple(part.strip() for part in raw.split(",") if part.strip())
    return aliases or DEFAULT_PERSON_ALIASES


def col_to_num(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        raise ValueError(f"Ugyldig cellereferanse: {cell_ref}")
    value = 0
    for char in match.group(1):
        value = value * 26 + ord(char) - 64
    return value


def num_to_col(num: int) -> str:
    value = ""
    while num:
        num, remainder = divmod(num - 1, 26)
        value = chr(65 + remainder) + value
    return value


def row_num(cell_ref: str) -> int:
    match = re.search(r"(\d+)$", cell_ref)
    if not match:
        raise ValueError(f"Ugyldig cellereferanse: {cell_ref}")
    return int(match.group(1))


def get_cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value = cell.find("a:v", XLSX_NS)
    inline = cell.find("a:is", XLSX_NS)

    if cell_type == "s" and value is not None:
        return shared_strings[int(value.text or "0")]
    if cell_type == "inlineStr" and inline is not None:
        return "".join(
            text.text or ""
            for text in inline.iter(
                "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
            )
        )
    if value is not None:
        return value.text or ""
    return ""


def read_xlsx_rows(xlsx_bytes: bytes) -> dict[int, dict[int, str]]:
    with ZipFile(io.BytesIO(xlsx_bytes)) as workbook:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", XLSX_NS):
                shared_strings.append(
                    "".join(
                        text.text or ""
                        for text in item.iter(
                            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
                        )
                    )
                )

        sheet = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        rows: dict[int, dict[int, str]] = {}
        for cell in sheet.findall(".//a:c", XLSX_NS):
            ref = cell.attrib["r"]
            text = get_cell_text(cell, shared_strings)
            if text == "":
                continue
            rows.setdefault(row_num(ref), {})[col_to_num(ref)] = text
        return rows


def parse_time_ranges(raw_value: str) -> Iterable[tuple[str, str]]:
    for match in TIME_RANGE_RE.finditer(raw_value):
        start_h = int(match.group("start_h"))
        start_m = int(match.group("start_m"))
        end_h = int(match.group("end_h"))
        end_m = int(match.group("end_m"))
        if not (0 <= start_h <= 23 and 0 <= end_h <= 23 and 0 <= start_m <= 59 and 0 <= end_m <= 59):
            continue
        yield f"{start_h:02d}:{start_m:02d}", f"{end_h:02d}:{end_m:02d}"


def find_shifts(rows: dict[int, dict[int, str]], aliases: tuple[str, ...], year: int) -> list[Shift]:
    normalized_aliases = {normalize_text(alias) for alias in aliases}
    shifts: list[Shift] = []
    active_week: int | None = None

    for row_index in sorted(rows):
        row = rows[row_index]
        name_or_header = row.get(3, "")
        week_candidate = row.get(4, "")

        if name_or_header and week_candidate:
            try:
                week_num = int(float(str(week_candidate).strip()))
            except ValueError:
                week_num = 0
            if 1 <= week_num <= 53 and re.search(r"\d{1,2}\s*[-–]\s*\d{1,2}", str(name_or_header)):
                active_week = week_num
                continue

        if active_week is None or normalize_text(name_or_header) not in normalized_aliases:
            continue

        person = str(name_or_header).replace("\xa0", " ").strip()
        for col_index, iso_weekday in DAY_COLUMNS.items():
            raw_value = str(row.get(col_index, "")).replace("\xa0", " ").strip()
            if not raw_value:
                continue

            for start_time, end_time in parse_time_ranges(raw_value):
                shift_date = datetime.fromisocalendar(year, active_week, iso_weekday).date()
                shifts.append(
                    Shift(
                        person=person,
                        shift_date=shift_date.isoformat(),
                        start_time=start_time,
                        end_time=end_time,
                        raw_value=raw_value,
                        source_sheet="Ark1",
                        source_cell=f"{num_to_col(col_index)}{row_index}",
                        source_week=active_week,
                    )
                )

    return sorted(shifts, key=lambda shift: (shift.shift_date, shift.start_time, shift.end_time))


def download_xlsx(site_url: str, file_guid: str, browser_profile: Path, chromium_path: str | None) -> bytes:
    url = f"{site_url.rstrip('/')}/_api/web/GetFileById('{file_guid}')/$value"
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(browser_profile),
            executable_path=chromium_path,
            headless=True,
            accept_downloads=False,
            args=["--disable-dev-shm-usage"],
        )
        try:
            response = context.request.get(url, headers={"Accept": "application/octet-stream"})
            body = response.body()
            if not response.ok:
                preview = body[:300].decode("utf-8", "replace")
                raise RuntimeError(f"SharePoint GET feilet: {response.status} {response.status_text}: {preview}")
            if body[:2] != b"PK":
                preview = body[:300].decode("utf-8", "replace")
                raise RuntimeError(f"SharePoint returnerte ikke en xlsx-fil: {preview}")
            return body
        finally:
            context.close()


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shifts (
          id TEXT PRIMARY KEY,
          person TEXT NOT NULL,
          shift_date TEXT NOT NULL,
          start_time TEXT NOT NULL,
          end_time TEXT NOT NULL,
          raw_value TEXT NOT NULL,
          source_sheet TEXT NOT NULL,
          source_cell TEXT NOT NULL,
          source_week INTEGER NOT NULL,
          updated_at TEXT NOT NULL
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shifts_date ON shifts(shift_date);")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        """
    )


def save_shifts(db_path: Path, person_aliases: tuple[str, ...], shifts: list[Shift]) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    primary_person = person_aliases[0]
    with sqlite3.connect(db_path) as conn:
        init_db(conn)
        conn.execute("DELETE FROM shifts WHERE person = ?", (primary_person,))
        conn.executemany(
            """
            INSERT INTO shifts (
              id, person, shift_date, start_time, end_time, raw_value,
              source_sheet, source_cell, source_week, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            [
                (
                    shift.id,
                    primary_person,
                    shift.shift_date,
                    shift.start_time,
                    shift.end_time,
                    shift.raw_value,
                    shift.source_sheet,
                    shift.source_cell,
                    shift.source_week,
                    now,
                )
                for shift in shifts
            ],
        )
        conn.execute(
            """
            INSERT INTO sync_meta(key, value) VALUES('last_sync_at', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """,
            (now,),
        )
        conn.execute(
            """
            INSERT INTO sync_meta(key, value) VALUES('last_success_at', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """,
            (now,),
        )
        conn.execute(
            """
            INSERT INTO sync_meta(key, value) VALUES('person', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """,
            (primary_person,),
        )
        conn.execute(
            """
            INSERT INTO sync_meta(key, value) VALUES('status', 'ok')
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """
        )
        conn.execute(
            """
            INSERT INTO sync_meta(key, value) VALUES('last_error', '')
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """
        )
        conn.execute(
            """
            INSERT INTO sync_meta(key, value) VALUES('last_error_at', '')
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """
        )
        conn.execute(
            """
            INSERT INTO sync_meta(key, value) VALUES('shift_count', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """,
            (str(len(shifts)),),
        )


def write_sync_meta(db_path: Path, values: dict[str, str]) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        init_db(conn)
        for key, value in values.items():
            conn.execute(
                """
                INSERT INTO sync_meta(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
                """,
                (key, value),
            )
        conn.execute(
            """
            INSERT INTO sync_meta(key, value) VALUES('last_attempt_at', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """,
            (now,),
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only sync from Ressursplan KS.xlsx to local shift_plan.db")
    parser.add_argument("--input-xlsx", type=Path, help="Use a local xlsx copy instead of downloading from SharePoint")
    parser.add_argument("--db", type=Path, default=Path(os.getenv("SHIFT_PLAN_DB", DB_PATH)))
    parser.add_argument("--year", type=int, default=int(os.getenv("SHIFT_PLAN_YEAR", datetime.now().year)))
    parser.add_argument("--person-aliases", default=os.getenv("SHIFT_PERSON_ALIASES"))
    parser.add_argument("--print", action="store_true", help="Print parsed shifts after saving")
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()
    write_sync_meta(args.db, {"status": "syncing"})

    try:
        aliases = parse_aliases(args.person_aliases)
        if args.input_xlsx:
            xlsx_bytes = args.input_xlsx.read_bytes()
        else:
            profile = Path(os.getenv("SHIFT_BROWSER_PROFILE", APP_DIR / "ms_browser_profile"))
            if not profile.is_absolute():
                profile = APP_DIR / profile
            chromium_path = os.getenv("SHIFT_CHROMIUM_PATH", "/usr/bin/chromium-browser").strip() or None
            site_url = os.getenv("SHIFT_SHAREPOINT_SITE", DEFAULT_SITE_URL)
            file_guid = os.getenv("SHIFT_FILE_GUID", DEFAULT_FILE_GUID)
            xlsx_bytes = download_xlsx(site_url, file_guid, profile, chromium_path)

        rows = read_xlsx_rows(xlsx_bytes)
        shifts = find_shifts(rows, aliases, args.year)
        save_shifts(args.db, aliases, shifts)

        print(f"OK: lagret {len(shifts)} vakter i {args.db}")
        if args.print:
            for shift in shifts:
                print(f"{shift.shift_date} {shift.start_time}-{shift.end_time} ({shift.raw_value}) [{shift.source_cell}]")
        return 0
    except Exception as exc:
        write_sync_meta(
            args.db,
            {
                "status": "error",
                "last_error_at": datetime.now().isoformat(timespec="seconds"),
                "last_error": str(exc)[:500],
            },
        )
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"Feil: {exc}", file=sys.stderr)
        raise SystemExit(1)
