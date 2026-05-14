import tkinter as tk
import os
import sqlite3
from datetime import datetime, timedelta
import pytz
from dateutil import parser
from google.oauth2 import service_account
from googleapiclient.discovery import build

from ScreenStyle import ScreenStyle as ss


class CalendarFrame(tk.Frame):
    """
    Henter og viser hendelser for i dag og i morgen fra Google Calendar.

    Kortstruktur
    ────────────
    ┌─ CalendarFrame (card border) ────────────────┐
    │  header:  "Kalender"                         │
    │  divider: ───────────────────────────────    │
    │  content: I dag                              │
    │           14:00  Møte med team               │
    │           16:30  Trening                     │
    │                                              │
    │           I morgen                           │
    │           09:00  Legetime                    │
    └───────────────────────────────────────────────┘

    Kun content_frame tømmes ved periodisk oppdatering.
    """

    def __init__(self, parent, color):
        super().__init__(parent, **ss.card_kwargs())

        # Google Calendar API
        self.SERVICE_ACCOUNT_FILE = 'key.json'
        self.SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        self.credentials = service_account.Credentials.from_service_account_file(
            self.SERVICE_ACCOUNT_FILE, scopes=self.SCOPES)
        self.service = build('calendar', 'v3', credentials=self.credentials)

        self.calendar_ids = [
            'marius.vestoel@abakus.no',
            'marves@samfundet.no',
            'marius.vestol@gmail.com',
        ]

        self.HEADER_COLOR = color
        self.all_events_today = []
        self.shift_db_path = os.path.join(os.path.dirname(__file__), "shift_plan.db")
        self.timezone = pytz.timezone("Europe/Oslo")

        # ── Persistent layout ─────────────────────────────────────────
        header = tk.Frame(self, bg=ss.CARD_FILL)
        header.pack(fill="x", padx=ss.PAD_CARD, pady=(ss.PAD_CARD, 4))
        tk.Label(header, text="Kalender", font=ss.FONT_SECTION,
                 fg=self.HEADER_COLOR, bg=ss.CARD_FILL).pack(anchor="w")

        tk.Frame(self, bg=ss.DIVIDER, height=1).pack(fill="x", padx=ss.PAD_CARD)

        self.content_frame = tk.Frame(self, bg=ss.CARD_FILL)
        self.content_frame.pack(fill="x", padx=ss.PAD_CARD,
                                pady=(4, ss.PAD_CARD))

        self.update_calendar()

    # ── API-henting ───────────────────────────────────────────────────

    def safe_fetch_events(self, calendar_id, now, page_token=None):
        """Henter hendelser trygt fra Google Calendar API med try/except."""
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                singleEvents=True,
                orderBy='startTime',
                pageToken=page_token,
            ).execute()
            return events_result
        except Exception as e:
            print(f"Kunne ikke hente hendelser for {calendar_id}: {e}")
            return None

    # ── Hent og render hendelser ──────────────────────────────────────

    def _render_event_list(self, events, label_text):
        """Renderer en dagseksjon (tittel + hendelsesrader) i content_frame."""
        tk.Label(self.content_frame, text=label_text,
                 font=ss.FONT_SECTION, fg=self.HEADER_COLOR,
                 bg=ss.CARD_FILL, anchor="w").pack(anchor="w", pady=(6, 2))

        sorted_events = sorted(
            events,
            key=lambda x: x['start'].get('dateTime', x['start'].get('date')),
        )
        for event in sorted_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            start_time = (
                parser.isoparse(start).strftime("%H:%M")
                if 'dateTime' in event['start']
                else "Heldag"
            )
            summary = event.get('summary', 'Ingen tittel')

            row = tk.Frame(self.content_frame, bg=ss.CARD_FILL)
            row.pack(anchor="w", fill="x", pady=1)

            tk.Label(row, text=start_time, font=ss.FONT_BODY,
                     fg=ss.TEXT_SECONDARY, bg=ss.CARD_FILL,
                     width=6, anchor="w").pack(side="left")
            tk.Label(row, text=summary, font=ss.FONT_BODY,
                     fg=ss.TEXT_PRIMARY, bg=ss.CARD_FILL,
                     anchor="w").pack(side="left")

    def fetch_events_for_today_and_tomorrow(self):
        self.all_events_today = []
        now = datetime.utcnow().isoformat() + 'Z'
        today    = datetime.now(self.timezone).date()
        tomorrow = today + timedelta(days=1)

        all_events_tomorrow = []

        for calendar_id in self.calendar_ids:
            page_token = None
            while True:
                events_result = self.safe_fetch_events(
                    calendar_id, now, page_token)
                if not events_result:
                    break

                for event in events_result.get('items', []):
                    start = event['start'].get(
                        'dateTime', event['start'].get('date'))
                    try:
                        event_time = parser.isoparse(start)
                    except Exception as e:
                        print(f"Kunne ikke parse tidspunkt: {start}, feil: {e}")
                        continue

                    if event_time.date() == today:
                        self.all_events_today.append(event)
                    elif event_time.date() == tomorrow:
                        all_events_tomorrow.append(event)

                page_token = events_result.get('nextPageToken')
                if not page_token:
                    break

        shift_today, shift_tomorrow = self.fetch_shift_events(today, tomorrow)
        self.all_events_today.extend(shift_today)
        all_events_tomorrow.extend(shift_tomorrow)

        self._render_event_list(self.all_events_today, "I dag")

        # Visuell luft mellom dagseksjonene
        tk.Frame(self.content_frame, bg=ss.CARD_FILL, height=4).pack()

        self._render_event_list(all_events_tomorrow, "I morgen")

    def _shift_to_event(self, row):
        start_dt = self.timezone.localize(
            datetime.fromisoformat(f"{row['shift_date']}T{row['start_time']}:00")
        )
        end_dt = self.timezone.localize(
            datetime.fromisoformat(f"{row['shift_date']}T{row['end_time']}:00")
        )
        return {
            "summary": "Jobb (Aneo)",
            "start": {"dateTime": start_dt.isoformat()},
            "end": {"dateTime": end_dt.isoformat()},
        }

    def fetch_shift_events(self, today, tomorrow):
        if not os.path.exists(self.shift_db_path):
            return [], []

        try:
            conn = sqlite3.connect(self.shift_db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT shift_date, start_time, end_time
                FROM shifts
                WHERE shift_date IN (?, ?)
                ORDER BY shift_date, start_time
                """,
                (today.isoformat(), tomorrow.isoformat()),
            ).fetchall()
            conn.close()
        except Exception as e:
            print(f"Kunne ikke hente vakter fra shift_plan.db: {e}")
            return [], []

        today_events = []
        tomorrow_events = []
        for row in rows:
            event = self._shift_to_event(row)
            if row["shift_date"] == today.isoformat():
                today_events.append(event)
            else:
                tomorrow_events.append(event)
        return today_events, tomorrow_events

    # ── Periodisk oppdatering ─────────────────────────────────────────

    def update_calendar(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.fetch_events_for_today_and_tomorrow()
        self.after(60000, self.update_calendar)
