import tkinter as tk
from PIL import Image, ImageTk
import requests

from ScreenStyle import ScreenStyle as ss


class WeatherFrame(tk.Frame):
    """
    Henter og viser nåværende vær fra met.no.

    Kortstruktur
    ────────────
    ┌─ WeatherFrame (card border) ─────────────────┐
    │  header:  "Vær"                              │
    │  divider: ───────────────────────────────    │
    │  content: 8.5°C  –  4.2 m/s   [ikon]        │
    └───────────────────────────────────────────────┘
    """

    ICON_MAP = {
        "clearsky_day":        "icons/sun.png",
        "clearsky_night":      "icons/moon.png",
        "partlycloudy_day":    "icons/partly_cloudy.png",
        "partlycloudy_night":  "icons/partly_cloudy.png",
        "cloudy":              "icons/cloudy.png",
        "rain":                "icons/rainy.png",
        "snow":                "icons/snowy.png",
        "fair_day":            "icons/partly_cloudy.png",
        "fair_night":          "icons/moon.png",
        "lightsnow":           "icons/snowy.png",
        # Legg til flere symbol_code → ikon-mappings her
    }

    def __init__(self, parent, color):
        super().__init__(parent, **ss.card_kwargs())
        self.latitude  = 63.4305
        self.longitude = 10.3951
        self.url = (
            f"https://api.met.no/weatherapi/locationforecast/2.0/compact"
            f"?lat={self.latitude}&lon={self.longitude}"
        )
        self.headers = {"User-Agent": "MyWeatherApp/1.0 your_email@example.com"}
        self.color = color

        # ── Persistent layout ─────────────────────────────────────────
        header = tk.Frame(self, bg=ss.CARD_FILL)
        header.pack(fill="x", padx=ss.PAD_CARD, pady=(ss.PAD_CARD, 4))
        tk.Label(header, text="Vær", font=ss.FONT_SECTION,
                 fg=self.color, bg=ss.CARD_FILL).pack(anchor="w")

        tk.Frame(self, bg=ss.DIVIDER, height=1).pack(fill="x", padx=ss.PAD_CARD)

        self.weather_container = tk.Frame(self, bg=ss.CARD_FILL)
        self.weather_container.pack(fill="x", padx=ss.PAD_CARD,
                                    pady=(4, ss.PAD_CARD))

        self.update_weather()

    # ── API-kall ──────────────────────────────────────────────────────

    def get_weather(self):
        try:
            response = requests.get(self.url, headers=self.headers)
            response.raise_for_status()
            data    = response.json()
            current = data["properties"]["timeseries"][0]
            details = current["data"]["instant"]["details"]

            temperature = details.get("air_temperature")
            wind_speed  = details.get("wind_speed")
            next_hours  = current["data"].get("next_1_hours")
            symbol = next_hours["summary"]["symbol_code"] if next_hours else None
            return [temperature, wind_speed, symbol]
        except Exception as e:
            return [None, None, f"Feil ved henting av værdata: {e}"]

    # ── Render ────────────────────────────────────────────────────────

    def update_weather(self):
        for widget in self.weather_container.winfo_children():
            widget.destroy()

        temp, wind, symbol = self.get_weather()

        if temp is not None:
            row = tk.Frame(self.weather_container, bg=ss.CARD_FILL)
            row.pack(anchor="w", pady=2, fill="x")

            tk.Label(row,
                     text=f"{temp}°C  –  {wind} m/s",
                     font=ss.FONT_BODY,
                     fg=ss.TEXT_PRIMARY,
                     bg=ss.CARD_FILL).pack(side="left")

            icon_label = tk.Label(row, bg=ss.CARD_FILL)
            icon_label.pack(side="left", padx=10)
            self.load_icon(symbol, icon_label)
        else:
            tk.Label(self.weather_container,
                     text=symbol,
                     font=ss.FONT_BODY,
                     fg=ss.TEXT_PRIMARY,
                     bg=ss.CARD_FILL).pack(anchor="w")

        # Oppdater hvert 30. minutt
        self.after(1800000, self.update_weather)

    def load_icon(self, symbol_code, label):
        try:
            if not symbol_code:
                label.config(text="Ingen værbeskrivelse")
                return
            path  = self.ICON_MAP.get(symbol_code, f"icons/{symbol_code}.png")
            img   = Image.open(path).resize((60, 60))
            photo = ImageTk.PhotoImage(img)
            label.config(image=photo, text="")
            label.image = photo   # hindre GC
        except FileNotFoundError:
            label.config(text="Ikon mangler", image="")
            print(symbol_code)
