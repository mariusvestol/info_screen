import tkinter as tk
from datetime import datetime, timedelta
import pytz
from dateutil import parser
from google.oauth2 import service_account
from googleapiclient.discovery import build

from ScreenStyle import ScreenStyle as ss


class CalendarFrame(tk.Frame):
    def __init__(self, parent, color):
        super().__init__(parent, bg="white", bd=0, relief="solid")
        
        # Google Calendar API
        self.SERVICE_ACCOUNT_FILE = 'key.json'  # Endre til din filbane
        self.SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        
        # Lag credentials-objekt
        self.credentials = service_account.Credentials.from_service_account_file(
            self.SERVICE_ACCOUNT_FILE, scopes=self.SCOPES)
        
        # Bygg tjenesten
        self.service = build('calendar', 'v3', credentials=self.credentials)

        # Liste over kalender-IDer
        self.calendar_ids = [
            'marius.vestoel@abakus.no',
            'marves@samfundet.no',
            'marius.vestol@gmail.com'
        ]
        
        self.HEADER_COLOR = color
        self.all_events_today = []

        self.update_calendar()

    def safe_fetch_events(self, calendar_id, now, page_token=None):
        """Henter hendelser trygt fra Google Calendar API med try/except."""
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                singleEvents=True,
                orderBy='startTime',
                pageToken=page_token
            ).execute()
            return events_result
        except Exception as e:
            print(f"Kunne ikke hente hendelser for {calendar_id}: {e}")
            return None

    def fetch_events_for_today_and_tomorrow(self):
        self.all_events_today = []  # Tøm listen før oppdatering
        now = datetime.utcnow().isoformat() + 'Z'  # UTC-tid
        today = datetime.now(pytz.timezone("Europe/Oslo")).date()
        tomorrow = today + timedelta(days=1)
    
        all_events_tomorrow = []

        # Hent alle hendelser fra alle kalendere
        for calendar_id in self.calendar_ids:
            page_token = None
            while True:
                events_result = self.safe_fetch_events(calendar_id, now, page_token)
                if not events_result:
                    break  # Hopp over denne kalenderen hvis feil

                events = events_result.get('items', [])
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    try:
                        event_time = parser.isoparse(start)
                    except Exception as e:
                        print(f"Kunne ikke parse tidspunkt for hendelse: {start}, feil: {e}")
                        continue

                    if event_time.date() == today:
                        self.all_events_today.append(event)
                    elif event_time.date() == tomorrow:
                        all_events_tomorrow.append(event)

                page_token = events_result.get('nextPageToken')
                if not page_token:
                    break

        rowCount = 0

        # Vis dagens overskrift
        tk.Label(self, text="I dag", fg=self.HEADER_COLOR, font=ss.FONT_SMALL, bg="white", anchor="w")\
            .grid(row=rowCount, column=0, sticky="w", padx=10, pady=5)
        rowCount += 1

        # Sorter og vis dagens hendelser
        for event in sorted(self.all_events_today, key=lambda x: x['start'].get('dateTime', x['start'].get('date'))):
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'dateTime' in event['start']:
                start_time = parser.isoparse(start).strftime("%H:%M")
            else:
                start_time = "Heldag"
            summary = event.get('summary', 'Ingen tittel')
            tk.Label(self, text=f"{start_time} - {summary}", font=ss.FONT_SMALL, bg="white")\
                .grid(row=rowCount, column=0, sticky="w", padx=10)
            rowCount +=1

        rowCount +=1  # Ekstra luftlinje

        # Vis morgendagens overskrift
        tk.Label(self, text="I morgen", fg=self.HEADER_COLOR, font=ss.FONT_SMALL, bg="white", anchor="w")\
            .grid(row=rowCount, column=0, sticky="w", padx=10, pady=5)
        rowCount +=1

        # Sorter og vis morgendagens hendelser
        for event in sorted(all_events_tomorrow, key=lambda x: x['start'].get('dateTime', x['start'].get('date'))):
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'dateTime' in event['start']:
                start_time = parser.isoparse(start).strftime("%H:%M")
            else:
                start_time = "Heldag"
            summary = event.get('summary', 'Ingen tittel')
            tk.Label(self, text=f"{start_time} - {summary}", font=ss.FONT_SMALL, bg="white")\
                .grid(row=rowCount, column=0, sticky="w", padx=10)
            rowCount +=1
            
    def update_calendar(self):
        # Fjern eksisterende widgets før oppdatering
        for widget in self.winfo_children():
            widget.destroy()

        # Hent kalenderhendelser
        self.fetch_events_for_today_and_tomorrow()
        
        # Oppdater kalenderen hvert 60. sekund
        self.after(60000, self.update_calendar)