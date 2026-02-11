import tkinter as tk

# Frames
from BusFrame import BusFrame
from CalendarFrame import CalendarFrame
from WeatherFrame import WeatherFrame
from TimeFrame import TimeFrame
from TodoFrame import TodoFrame


#Style
from ScreenStyle import ScreenStyle as ss


BG_COLOR = "#f9f9f9"
color = "#ADD8E6"
HEADER_COLOR = color;


# --- Fullscreen toggle ---
fullscreen = False
def toggle_fullscreen(event=None):
    global fullscreen
    fullscreen = not fullscreen
    root.attributes("-fullscreen", fullscreen)


root = tk.Tk()
root.title("Info Skjerm")
root.geometry("600x800")
root.configure(bg=ss.BG_COLOR)
root.bind("<F11>", toggle_fullscreen)



# Init greeting
greeting_frame = tk.Frame(root, bg=BG_COLOR)
greeting_frame.pack(pady=10, anchor="w", padx=20)
tk.Label(greeting_frame, text="God kveld", font=ss.FONT_HEADER, fg=HEADER_COLOR, bg=BG_COLOR).pack(anchor="w")
tk.Label(greeting_frame, text="mester", font=ss.FONT_HEADER, fg=HEADER_COLOR, bg=BG_COLOR).pack(anchor="w")


#Init time
timeFrame = TimeFrame(root, color)
timeFrame.place(x=750, y=10)


# Init bus
busFrame = BusFrame(root, color)
busFrame.pack(pady=30, padx=20, fill="x")


#Init calendar
calendarFrame = CalendarFrame(root, color)
calendarFrame.pack(pady=10, padx=20, fill="x")


#Init weatherFrame
weatherFrame = WeatherFrame(root, color)
weatherFrame.pack(pady=10, padx=20, fill="x")

#Init TodoFrame
todoFrame = TodoFrame(root, color)
todoFrame.pack(pady=10, padx=20, fill="x")


root.mainloop()