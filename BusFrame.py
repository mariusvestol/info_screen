import tkinter as tk
import requests
from datetime import datetime
from PIL import Image, ImageTk

from ScreenStyle import ScreenStyle as ss


class BusFrame(tk.Frame):
    """
    Viser sanntids avgangsinformasjon fra Entur API.

    Kortstruktur
    ────────────
    ┌─ BusFrame (card border) ─────────────────────┐
    │  header:  "Buss"                              │
    │  divider: ──────────────────────────────────  │
    │  content: [ikon]  Destinasjon       X min     │
    │           [ikon]  Destinasjon       Y min     │
    └───────────────────────────────────────────────┘

    Kun content_frame tømmes ved periodisk oppdatering; header og
    divider er persistente og vises alltid.
    """

    def __init__(self, parent, color):
        super().__init__(parent, **ss.card_kwargs())
        self.parent = parent

        # Holder referanser til PhotoImage-objekter for å hindre GC
        self.route_images = []

        self.HEADER_COLOR = color

        # Pikselerstatning: ikke-hvite piksler → aksentfarge
        self.toleranse = 105
        self.color = self._hex_to_rgb(color)

        # ── Entur API ─────────────────────────────────────────────────
        self.ENTUR_URL = "https://api.entur.io/journey-planner/v3/graphql"
        self.ENTUR_HEADERS = {
            "Content-Type": "application/json",
            "ET-Client-Name": "infoskjerm-test",
        }
        self.ENTUR_QUERY = """
{
  quay(id: "NSR:Quay:74792") {
    estimatedCalls(timeRange: 7200, numberOfDepartures: 5) {
      expectedArrivalTime
      destinationDisplay {
        frontText
      }
      serviceJourney {
        line {
          name
        }
      }
    }
  }
}
"""

        # ── Persistent layout ─────────────────────────────────────────
        header = tk.Frame(self, bg=ss.CARD_FILL)
        header.pack(fill="x", padx=ss.PAD_CARD, pady=(ss.PAD_CARD, 4))
        tk.Label(header, text="Buss", font=ss.FONT_SECTION,
                 fg=self.HEADER_COLOR, bg=ss.CARD_FILL).pack(anchor="w")

        tk.Frame(self, bg=ss.DIVIDER, height=1).pack(fill="x", padx=ss.PAD_CARD)

        self.content_frame = tk.Frame(self, bg=ss.CARD_FILL)
        self.content_frame.pack(fill="x", padx=ss.PAD_CARD,
                                pady=(4, ss.PAD_CARD))

        self.update_bus_info()

    # ── Bildelasting med fargeerstatning ──────────────────────────────

    def _er_nesten_hvit(self, pixel):
        r, g, b = pixel[0:3]
        return (r >= 255 - self.toleranse
                and g >= 255 - self.toleranse
                and b >= 255 - self.toleranse)

    def _hex_to_rgb(self, hex_str):
        hex_str = hex_str.lstrip('#')
        return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))

    def _load_route_image(self, route_num):
        """
        Laster rutebilde og erstatter ikke-hvite piksler med aksentfargen.
        Prøver <route_num>.png, faller tilbake til 12.png.
        Returnerer ImageTk.PhotoImage eller None ved feil.
        """
        for filename in (f"{route_num}.png", "12.png"):
            try:
                img = Image.open(filename).convert("RGBA").resize((140, 60))
                pixels = img.getdata()
                new_pixels = [
                    self.color + (p[3],) if not self._er_nesten_hvit(p)
                    else (255, 255, 255, p[3])
                    for p in pixels
                ]
                img.putdata(new_pixels)
                photo = ImageTk.PhotoImage(img)
                self.route_images.append(photo)   # hindre GC
                return photo
            except Exception:
                continue
        return None

    # ── Én busslinje ──────────────────────────────────────────────────

    def bus_row(self, parent, route_num, destination, wait):
        row = tk.Frame(parent, bg=ss.CARD_FILL)
        row.pack(fill="x", pady=ss.PAD_ROW)

        photo = self._load_route_image(route_num)
        if photo:
            tk.Label(row, image=photo, bg=ss.CARD_FILL).pack(
                side="left", padx=(0, 10))

        tk.Label(row, text=destination, font=ss.FONT_BODY,
                 fg=ss.TEXT_PRIMARY, bg=ss.CARD_FILL).pack(side="left")

        tk.Label(row, text=wait, font=ss.FONT_BODY,
                 fg=self.HEADER_COLOR, bg=ss.CARD_FILL).pack(side="right")

    # ── Periodisk oppdatering ─────────────────────────────────────────

    def update_bus_info(self):
        # Tøm bare innholdsrammen – header og divider forblir intakte
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.route_images.clear()

        try:
            response = requests.post(
                self.ENTUR_URL,
                json={'query': self.ENTUR_QUERY},
                headers=self.ENTUR_HEADERS,
            )
            data = response.json()
            now = datetime.now()
            for call in data["data"]["quay"]["estimatedCalls"]:
                arrival = datetime.fromisoformat(
                    call["expectedArrivalTime"][:-6])
                diff = int((arrival - now).total_seconds() // 60)
                line = call["serviceJourney"]["line"]["name"]
                dest = call["destinationDisplay"]["frontText"]
                self.bus_row(self.content_frame, line, dest, f"{diff} min")
        except Exception as e:
            self.bus_row(self.content_frame, "??", "Ingen data", "N/A")
            print("Feil ved henting av bussdata:", e)

        self.after(60000, self.update_bus_info)
