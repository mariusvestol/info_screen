import tkinter as tk
from datetime import datetime

# Frames
from BusFrame import BusFrame
from CalendarFrame import CalendarFrame
from WeatherFrame import WeatherFrame
from TimeFrame import TimeFrame
from TodoFrame import TodoFrame

# Stil
from ScreenStyle import ScreenStyle as ss, RoundedCard

# Aksent hentes fra ScreenStyle – én kilde til sannhet
ACCENT = ss.ACCENT


# ── Hilsen basert på tid på døgnet ────────────────────────────────────
def get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "God morgen"
    elif 12 <= hour < 18:
        return "God ettermiddag"
    else:
        return "God kveld"


# ── Fullscreen-toggle ─────────────────────────────────────────────────
fullscreen = False

def toggle_fullscreen(event=None):
    global fullscreen
    fullscreen = not fullscreen
    root.attributes("-fullscreen", fullscreen)


# ── Rotvindu ──────────────────────────────────────────────────────────
root = tk.Tk()
root.title("Info Skjerm")
root.geometry("1000x800")
root.configure(bg=ss.BG_COLOR)
root.resizable(True, True)
root.bind("<F11>", toggle_fullscreen)


# ── Topplinje: Hilsen (venstre) + Klokke (høyre) ─────────────────────
top_bar = tk.Frame(root, bg=ss.BG_COLOR)
top_bar.pack(fill="x", padx=ss.PAD_OUTER, pady=(ss.PAD_OUTER, ss.PAD_SECTION))

greeting_label = tk.Label(top_bar, text=get_greeting(), font=ss.FONT_GREETING,
                          fg=ACCENT, bg=ss.BG_COLOR)
greeting_label.pack(side="left", anchor="w")

timeFrame = TimeFrame(top_bar, ACCENT)
timeFrame.pack(side="right", anchor="ne")


def update_greeting():
    greeting_label.config(text=get_greeting())
    root.after(60000, update_greeting)

update_greeting()


# ── Innholdskort med avrundede hjørner ────────────────────────────────
bus_card = RoundedCard(root)
bus_card.pack(pady=(0, ss.PAD_SECTION), padx=ss.PAD_OUTER, fill="x")
BusFrame(bus_card.inner, ACCENT).pack(fill="both", expand=True)

cal_card = RoundedCard(root)
cal_card.pack(pady=(0, ss.PAD_SECTION), padx=ss.PAD_OUTER, fill="x")
CalendarFrame(cal_card.inner, ACCENT).pack(fill="both", expand=True)

weather_card = RoundedCard(root)
weather_card.pack(pady=(0, ss.PAD_SECTION), padx=ss.PAD_OUTER, fill="x")
WeatherFrame(weather_card.inner, ACCENT).pack(fill="both", expand=True)

todo_card = RoundedCard(root)
todo_card.pack(pady=(0, ss.PAD_SECTION), padx=ss.PAD_OUTER, fill="x")
TodoFrame(todo_card.inner, ACCENT).pack(fill="both", expand=True)


root.mainloop()
