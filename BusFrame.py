import tkinter as tk
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageTk


# VI KAN LAGE EN METODE SOM BYTTER FARGE PÅ ALLE


                #superklassen er denne inni paramteren
class BusFrame(tk.Frame):

    def __init__(self, parent, color):
        super().__init__(parent, bg="white")
        self.parent = parent
        
        self.bus_images = []
        self.route_images = []


        # DISSE KUNNE LOWKEY VÆRT EN EGEN KLASSE

        self.FONT_HEADER = ("Helvetica", 45, "bold")
        self.FONT_SUBHEADER = ("Helvetica", 20, "bold")
        self.FONT_TIME = ("Helvetica", 60)
        self.FONT_SMALL = ("Helvetica", 26)
        self.HEADER_COLOR = color

        # -- Color change --

        self.toleranse = 105
        self.color = self.hex_to_rgb(color)


        # -- Entur API ---
        self.ENTUR_URL = "https://api.entur.io/journey-planner/v3/graphql"
        self.ENTUR_HEADERS = {
    "Content-Type": "application/json",
    "ET-Client-Name": "infoskjerm-test"
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
        self.update_bus_info()

    def er_nesten_hvit(self, pixel):
        r, g, b = pixel[0:3]
        return r >= 255 - self.toleranse and g >= 255 - self.toleranse and b >= 255 - self.toleranse



    def bus_row(self, parent, route_num, destination, wait):
        row = tk.Frame(parent, bg="white")
        row.pack(fill="x", pady=6)
        try:
            route_img = Image.open(f"{route_num}.png").convert("RGBA").resize((140, 60))
            pixels = route_img.getdata()
            new_pixels = []
            for pixel in pixels:
                if not self.er_nesten_hvit(pixel):  # Hvis pikselen ikke er "nesten hvit"
                    new_pixels.append(self.color + (pixel[3],))
                else:
                    new_pixels.append((255, 255, 255, pixel[3]))  # Sett til helt hvit    
            route_img.putdata(new_pixels)
            route_photo = ImageTk.PhotoImage(route_img)
            self.route_images.append(route_photo)
            tk.Label(row, image=route_photo, bg="white").pack(side="left", padx=5)
        except Exception as e:
            route_img = Image.open("12.png").convert("RGBA").resize((140, 60))
            pixels = route_img.getdata()
            new_pixels = []
            for pixel in pixels:
                if not self.er_nesten_hvit(pixel):  # Hvis pikselen ikke er "nesten hvit"
                    new_pixels.append(self.color + (pixel[3],))
                else:
                    new_pixels.append((255, 255, 255, pixel[3]))  # Sett til helt hvit    
            route_img.putdata(new_pixels)
            route_photo = ImageTk.PhotoImage(route_img)
            self.route_images.append(route_photo)
            tk.Label(row, image=route_photo, bg="white").pack(side="left", padx=5)

        # Destinasjon
        tk.Label(row, text=destination, font=self.FONT_SMALL, bg="white").pack(side="left", padx=10)
        # Tid til ankomst
        tk.Label(row, text=wait, font=self.FONT_SMALL, fg=self.HEADER_COLOR, bg="white").pack(side="right", padx=10)

    def update_bus_info(self):
        for widget in self.winfo_children():
            widget.destroy()

        try:
            response = requests.post(self.ENTUR_URL, json={'query': self.ENTUR_QUERY}, headers=self.ENTUR_HEADERS)
            data = response.json()
            now = datetime.now()
            for call in data["data"]["quay"]["estimatedCalls"]:
                arrival_time = datetime.fromisoformat(call["expectedArrivalTime"][:-6])
                diff = int((arrival_time - now).total_seconds() // 60)
                line = call["serviceJourney"]["line"]["name"]
                dest = call["destinationDisplay"]["frontText"]
                self.bus_row(self, line, dest, f"{diff} min")
        except Exception as e:
            self.bus_row(self, "??", "Ingen data", "N/A")
            print("Feil ved henting av bussdata:", e)
        self.after(60000, self.update_bus_info)


    def hex_to_rgb(self, hex_str):
        hex_str = hex_str.lstrip('#')
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

        # Oppdater hvert minutt
