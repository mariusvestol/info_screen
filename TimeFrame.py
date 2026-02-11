import tkinter as tk
from datetime import datetime, timedelta
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from PIL import Image, ImageTk
import pytz

from ScreenStyle import ScreenStyle as ss

class TimeFrame(tk.Frame):
    def __init__(self, parent, color):
        super().__init__(parent)

        self.color = color
        self.parent = parent

        self.configure(bg=ss.BG_COLOR)
        
        self.time_label = tk.Label(self, font=ss.FONT_TIME, fg=color, bg=ss.BG_COLOR)
        self.time_label.pack(anchor="e")
        self.date_label = tk.Label(self, font=ss.FONT_SMALL, fg=color, bg=ss.BG_COLOR)
        self.date_label.pack(anchor="e")

        self.update_time()

    def update_time(self):
        now = datetime.now()
        self.time_label.config(text=now.strftime("%H:%M"))
        
        today = now.strftime("%A %-d. %B")
        
        self.date_label.config(text=f"{today}")
        
        self.parent.after(1000, self.update_time)
