import tkinter as tk
from PIL import Image, ImageTk
import requests
from ScreenStyle import ScreenStyle as ss


class WeatherFrame(tk.Frame):
    ICON_MAP = {
        "clearsky_day": "icons/sun.png",
        "clearsky_night": "icons/moon.png",
        "partlycloudy_day": "icons/partly_cloudy.png",
        "partlycloudy_night": "icons/partly_cloudy.png",
        "cloudy": "icons/cloudy.png",
        "rain": "icons/rainy.png",
        "snow": "icons/snowy.png",
        "fair_day": "icons/partly_cloudy.png",
        "fair_night": "icons/moon.png", # kanskje denne burde hatt skyer..
        "lightsnow":  "icons/snowy.png",
        # Legg til flere symbol_code → ikon mappings her
    }

    def __init__(self, parent, color):
        super().__init__(parent, bg="white", bd=0, relief="solid")
        self.latitude = 63.4305
        self.longitude = 10.3951
        self.url = (
            f"https://api.met.no/weatherapi/locationforecast/2.0/compact"
            f"?lat={self.latitude}&lon={self.longitude}"
        )
        self.headers = {
            "User-Agent": "MyWeatherApp/1.0 your_email@example.com"
        }
        self.color = color

        # Overskrift
        tk.Label(self, text="Vær", fg=self.color, font=ss.FONT_SMALL, bg="white", anchor="w")\
            .grid(row=0, column=0, sticky="w", padx=10, pady=5)

        # Container for værdata
        self.weather_container = tk.Frame(self, bg="white")
        self.weather_container.grid(row=1, column=0, sticky="w", padx=10)

        self.update_weather()

    def get_weather(self):
        try:
            response = requests.get(self.url, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            current = data["properties"]["timeseries"][0]
            details = current["data"]["instant"]["details"]

            temperature = details.get("air_temperature")
            wind_speed = details.get("wind_speed")

            next_hours = current["data"].get("next_1_hours")
            symbol = next_hours["summary"]["symbol_code"] if next_hours else None

            return [temperature, wind_speed, symbol]

        except Exception as e:
            return [None, None, f"Feil ved henting av værdata: {e}"]

    def update_weather(self):
        # Tøm containeren først
        for widget in self.weather_container.winfo_children():
            widget.destroy()

        temp, wind, symbol = self.get_weather()

        if temp is not None:
            row_frame = tk.Frame(self.weather_container, bg="white")
            row_frame.pack(anchor="w", pady=2, fill="x")

            tk.Label(row_frame, text=f"{temp}°C, {wind} m/s", font=ss.FONT_SMALL, bg="white")\
                .pack(side="left")

            # Last inn ikon
            icon_label = tk.Label(row_frame, bg="white")
            icon_label.pack(side="left", padx=5)
            self.load_icon(symbol, icon_label)
        else:
            tk.Label(self.weather_container, text=symbol, font=ss.FONT_SMALL, bg="white")\
                .pack(anchor="w")

        # Oppdater hvert 30. minutt
        self.after(1800000, self.update_weather)

    def load_icon(self, symbol_code, label):
        try:
            if not symbol_code:
                label.config(text="Ingen værbeskrivelse")
                return

            # Hent filbane fra ICON_MAP, fallback til symbol_code.png
            path = self.ICON_MAP.get(symbol_code, f"icons/{symbol_code}.png")

            img = Image.open(path).resize((50, 50))
            photo = ImageTk.PhotoImage(img)
            label.config(image=photo, text="")
            label.image = photo  # Unngå garbage collection
        except FileNotFoundError:
            label.config(text="Ikon mangler", image="")
            print(symbol_code)
