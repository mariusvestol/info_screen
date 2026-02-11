import tkinter as tk
import requests
from dateutil import parser
from ScreenStyle import ScreenStyle as ss  # Samme styling som CalendarFrame


class TodoFrame(tk.Frame):
    def __init__(self, parent, color):
        super().__init__(parent, bg="white", bd=0, relief="solid")
        self.api_token = "336e15184c172256e5a482b78dbce8d011284a9d"
        self.color = color
        self.headers = {"Authorization": f"Bearer {self.api_token}"}
        self.all_tasks = []

        # Overskrift
        tk.Label(self, text="Tasks", fg=self.color, font=ss.FONT_SMALL, bg="white", anchor="w")\
            .grid(row=0, column=0, sticky="w", padx=10, pady=5)

        # Container for oppgavene
        self.tasks_container = tk.Frame(self, bg="white")
        self.tasks_container.grid(row=1, column=0, sticky="w", padx=10)

        self.update_tasks()

    def safe_fetch_tasks(self):
        """Henter Todoist-oppgaver trygt med try/except."""
        url = "https://api.todoist.com/rest/v2/tasks"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Kunne ikke hente Todoist-oppgaver: {e}")
            return []

    def update_tasks(self):
        # Tøm eksisterende widgets
        for widget in self.tasks_container.winfo_children():
            widget.destroy()

        self.all_tasks = self.safe_fetch_tasks()

        if not self.all_tasks:
            tk.Label(self.tasks_container, text="Ingen aktive oppgaver 🎉", font=ss.FONT_SMALL, bg="white")\
                .pack(anchor="w")
        else:
            tasks_with_date = []
            tasks_without_date = []

            # Del opp i oppgaver med og uten dato
            for task in self.all_tasks:
                due = task.get("due")
                if due and (due.get("datetime") or due.get("date")):
                    try:
                        dt_str = due.get("datetime") or due.get("date")
                        dt = parser.isoparse(dt_str)
                        tasks_with_date.append((dt, task["content"]))
                    except Exception:
                        tasks_without_date.append((None, task["content"]))
                else:
                    tasks_without_date.append((None, task["content"]))

            # Sorter med dato først, så uten
            tasks_sorted = sorted(tasks_with_date, key=lambda x: x[0]) + tasks_without_date

            # Legg inn i GUI
            for dt, content in tasks_sorted:
                if dt:
                    # Hvis klokkeslett = 00:00 → vis bare dato
                    if dt.time().hour == 0 and dt.time().minute == 0:
                        date_str = dt.strftime("%d.%m")
                    else:
                        date_str = dt.strftime("%d.%m %H:%M")
                else:
                    date_str = "TBD"

                # Først dato i farget tekst
                row_frame = tk.Frame(self.tasks_container, bg="white")
                row_frame.pack(anchor="w", pady=1, fill="x")

                tk.Label(row_frame, text=date_str, fg=self.color, font=ss.FONT_SMALL, bg="white")\
                    .pack(side="left")
                tk.Label(row_frame, text=f" - {content}", font=ss.FONT_SMALL, bg="white")\
                    .pack(side="left")

        # Oppdater hvert 60. sekund
        self.after(60000, self.update_tasks)
