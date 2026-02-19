import tkinter as tk

# Frames
from BusFrame import BusFrame
from CalendarFrame import CalendarFrame
from WeatherFrame import WeatherFrame
from TimeFrame import TimeFrame
from TodoFrame import TodoFrame

# Stil
from ScreenStyle import ScreenStyle as ss

# Aksent hentes fra ScreenStyle – én kilde til sannhet
ACCENT = ss.ACCENT


# ── Fullscreen-toggle ─────────────────────────────────────────────────
fullscreen = False

def toggle_fullscreen(event=None):
    global fullscreen
    fullscreen = not fullscreen
    root.attributes("-fullscreen", fullscreen)


# ── Rotvindu ──────────────────────────────────────────────────────────
# Antakelse: appen kjøres typisk i fullscreen (F11). 1000×800 er et
# fornuftig utgangspunkt for utvikling; timeren er nå pakket dynamisk
# til høyre slik at layout fungerer i alle bredder.
root = tk.Tk()
root.title("Info Skjerm")
root.geometry("1000x800")
root.configure(bg=ss.BG_COLOR)
root.resizable(True, True)
root.bind("<F11>", toggle_fullscreen)


# ── Topplinje: Hilsen (venstre) + Klokke (høyre) ─────────────────────
# Bruker pack i stedet for place() for å sikre korrekt layout i alle
# vindusbredder og under fullscreen.
top_bar = tk.Frame(root, bg=ss.BG_COLOR)
top_bar.pack(fill="x", padx=ss.PAD_OUTER, pady=(ss.PAD_OUTER, ss.PAD_SECTION))

greeting_frame = tk.Frame(top_bar, bg=ss.BG_COLOR)
greeting_frame.pack(side="left", anchor="nw")
tk.Label(greeting_frame, text="God kveld", font=ss.FONT_GREETING,
         fg=ACCENT, bg=ss.BG_COLOR).pack(anchor="w")
tk.Label(greeting_frame, text="mester",    font=ss.FONT_GREETING,
         fg=ACCENT, bg=ss.BG_COLOR).pack(anchor="w")

timeFrame = TimeFrame(top_bar, ACCENT)
timeFrame.pack(side="right", anchor="ne")


# ── Innholdskort ──────────────────────────────────────────────────────
busFrame = BusFrame(root, ACCENT)
busFrame.pack(pady=(0, ss.PAD_SECTION), padx=ss.PAD_OUTER, fill="x")

calendarFrame = CalendarFrame(root, ACCENT)
calendarFrame.pack(pady=(0, ss.PAD_SECTION), padx=ss.PAD_OUTER, fill="x")

weatherFrame = WeatherFrame(root, ACCENT)
weatherFrame.pack(pady=(0, ss.PAD_SECTION), padx=ss.PAD_OUTER, fill="x")

todoFrame = TodoFrame(root, ACCENT)
todoFrame.pack(pady=(0, ss.PAD_SECTION), padx=ss.PAD_OUTER, fill="x")


root.mainloop()
