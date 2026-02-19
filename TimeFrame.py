import tkinter as tk
from datetime import datetime

from ScreenStyle import ScreenStyle as ss


class TimeFrame(tk.Frame):
    """
    Viser klokke og dato oppdatert hvert sekund.
    Pakkes til høyre i top_bar i ScreenApp (side="right").
    """

    def __init__(self, parent, color):
        super().__init__(parent, bg=ss.BG_COLOR)
        self.color  = color
        self.parent = parent

        # Klokken i stor, tydelig aksent-farge
        self.time_label = tk.Label(
            self,
            font=ss.FONT_TIME,
            fg=color,
            bg=ss.BG_COLOR,
        )
        self.time_label.pack(anchor="e")

        # Dato i sekundærtekstfarge – litt dempet ift klokken
        self.date_label = tk.Label(
            self,
            font=ss.FONT_DATE,
            fg=ss.TEXT_SECONDARY,
            bg=ss.BG_COLOR,
        )
        self.date_label.pack(anchor="e")

        self.update_time()

    def update_time(self):
        now   = datetime.now()
        today = now.strftime("%A %-d. %B")
        self.time_label.config(text=now.strftime("%H:%M"))
        self.date_label.config(text=today)
        self.parent.after(1000, self.update_time)
