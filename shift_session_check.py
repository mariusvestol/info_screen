#!/usr/bin/env python3
"""
SharePoint session-cache check for the shift plan.

This does not use Graph/MSAL. It launches Chromium with a persistent profile
directory. First run is manual: complete Microsoft login in the opened browser.
Later runs reuse the same Chromium profile and should reach the Excel file
without a login prompt.

Run:
  .venv/bin/python shift_session_check.py

Useful flags:
  --headless        run without a visible browser after the session is cached
  --keep-open      leave the browser open for inspection
  --wait-login 600 wait up to 10 minutes for manual login
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


APP_DIR = Path(__file__).resolve().parent

DEFAULT_EXCEL_URL = (
    "https://aneomobility.sharepoint.com/sites/AneoMobility/_layouts/15/Doc.aspx"
    "?sourcedoc=%7BFE5E7547-C649-0068-4238-91D4D682D8BD%7D"
    "&file=Ressursplan%20KS.xlsx&action=default&mobileredirect=true"
    "&DefaultItemOpen=1"
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


def bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def profile_path() -> Path:
    configured = os.getenv("SHIFT_BROWSER_PROFILE", "ms_browser_profile")
    path = Path(configured)
    if not path.is_absolute():
        path = APP_DIR / path
    return path


def chromium_path() -> str | None:
    configured = os.getenv("SHIFT_CHROMIUM_PATH", "/usr/bin/chromium-browser").strip()
    return configured or None


def is_login_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return (
        "login.microsoftonline.com" in host
        or "login.live.com" in host
        or "adfs" in host
    )


def looks_like_excel_loaded(url: str, title: str) -> bool:
    lowered = f"{url} {title}".lower()
    if is_login_url(url):
        return False
    return (
        "aneomobility.sharepoint.com" in lowered
        and (
            "ressursplan" in lowered
            or "doc.aspx" in lowered
            or "excel" in lowered
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test SharePoint browser session cache")
    parser.add_argument(
        "--headless",
        action="store_true",
        default=bool_env("SHIFT_HEADLESS", False),
        help="Run Chromium headless. Default is headed so first login is possible.",
    )
    parser.add_argument(
        "--keep-open",
        action="store_true",
        help="Leave Chromium open after the check.",
    )
    parser.add_argument(
        "--wait-login",
        type=int,
        default=int(os.getenv("SHIFT_WAIT_LOGIN_SECONDS", "300")),
        help="Seconds to wait for manual login when needed.",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    excel_url = os.getenv("SHIFT_EXCEL_URL", DEFAULT_EXCEL_URL).strip()
    user_data_dir = profile_path()
    user_data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Bruker Chromium-profil: {user_data_dir}")
    print(f"Headless: {args.headless}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(user_data_dir),
            executable_path=chromium_path(),
            headless=args.headless,
            accept_downloads=True,
            viewport={"width": 1400, "height": 900},
            args=["--disable-dev-shm-usage"],
        )
        page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto(excel_url, wait_until="domcontentloaded", timeout=120000)
        except PlaywrightTimeoutError:
            print("Lasting tok for lang tid, fortsetter med status-sjekk.")

        deadline = time.time() + args.wait_login
        prompted_for_login = False

        while True:
            current_url = page.url
            title = page.title()

            if looks_like_excel_loaded(current_url, title):
                print("OK: SharePoint/Excel ser ut til å være lastet.")
                print(f"Tittel: {title}")
                print(f"URL: {current_url}")
                if args.keep_open:
                    input("Trykk Enter for å lukke Chromium...")
                context.close()
                return 0

            if is_login_url(current_url) and not prompted_for_login:
                prompted_for_login = True
                print("Microsoft-login trengs i dette Chromium-vinduet.")
                print("Fullfør login/MFA manuelt. Scriptet venter og lagrer session i profilen.")

            if time.time() >= deadline:
                print("FEIL: Kom ikke inn på Excel-filen før timeout.")
                print(f"Siste tittel: {title}")
                print(f"Siste URL: {current_url}")
                if args.keep_open:
                    input("Trykk Enter for å lukke Chromium...")
                context.close()
                return 2

            page.wait_for_timeout(1000)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"Feil: {exc}", file=sys.stderr)
        raise SystemExit(1)
