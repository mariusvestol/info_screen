import tkinter as tk
import requests
from dateutil import parser

from ScreenStyle import ScreenStyle as ss


class TodoFrame(tk.Frame):
    """
    Henter og viser aktive Todoist-oppgaver sortert etter frist.
    Bruker Todoist API v1 (api/v1).
    """

    def __init__(self, parent, color):
        super().__init__(parent, **ss.card_kwargs())
        self.api_token = "336e15184c172256e5a482b78dbce8d011284a9d"
        self.color     = color
        self.headers   = {"Authorization": f"Bearer {self.api_token}"}
        self.all_tasks = []

        # ── Persistent layout ─────────────────────────────────────────
        header = tk.Frame(self, bg=ss.CARD_FILL)
        header.pack(fill="x", padx=ss.PAD_CARD, pady=(ss.PAD_CARD, 4))
        tk.Label(header, text="Tasks", font=ss.FONT_SECTION,
                 fg=self.color, bg=ss.CARD_FILL).pack(anchor="w")

        tk.Frame(self, bg=ss.DIVIDER, height=1).pack(fill="x", padx=ss.PAD_CARD)

        self.tasks_container = tk.Frame(self, bg=ss.CARD_FILL)
        self.tasks_container.pack(fill="x", padx=ss.PAD_CARD,
                                   pady=(4, ss.PAD_CARD))

        self.update_tasks()

    # ── API-henting (ny v1 API) ──────────────────────────────────────

    def safe_fetch_tasks(self):
        """Henter Todoist-oppgaver fra den nye API v1."""
        url = "https://api.todoist.com/api/v1/tasks"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            # Ny API returnerer { "results": [...] }
            return data.get("results", [])
        except Exception as e:
            print(f"Kunne ikke hente Todoist-oppgaver: {e}")
            return []

    # ── Render ────────────────────────────────────────────────────────

    def update_tasks(self):
        for widget in self.tasks_container.winfo_children():
            widget.destroy()

        try:
            self.all_tasks = self.safe_fetch_tasks()

            if not self.all_tasks:
                tk.Label(self.tasks_container,
                         text="Ingen aktive oppgaver",
                         font=ss.FONT_BODY,
                         fg=ss.TEXT_SECONDARY,
                         bg=ss.CARD_FILL).pack(anchor="w")
            else:
                tasks_with_date    = []
                tasks_without_date = []

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

                tasks_sorted = (
                    sorted(tasks_with_date, key=lambda x: x[0])
                    + tasks_without_date
                )

                for dt, content in tasks_sorted:
                    if dt:
                        date_str = (
                            dt.strftime("%d.%m")
                            if dt.time().hour == 0 and dt.time().minute == 0
                            else dt.strftime("%d.%m %H:%M")
                        )
                    else:
                        date_str = "TBD"

                    row = tk.Frame(self.tasks_container, bg=ss.CARD_FILL)
                    row.pack(anchor="w", pady=2, fill="x")

                    tk.Label(row, text=date_str,
                             fg=self.color, font=ss.FONT_BODY,
                             bg=ss.CARD_FILL, width=10, anchor="w").pack(side="left")
                    tk.Label(row, text=content,
                             font=ss.FONT_BODY, fg=ss.TEXT_PRIMARY,
                             bg=ss.CARD_FILL, anchor="w").pack(side="left")
        except Exception as e:
            print(f"Feil ved visning av oppgaver: {e}")
            tk.Label(self.tasks_container,
                     text="Kunne ikke laste oppgaver",
                     font=ss.FONT_BODY,
                     fg=ss.TEXT_SECONDARY,
                     bg=ss.CARD_FILL).pack(anchor="w")

        # Oppdater hvert minutt
        self.after(60000, self.update_tasks)
