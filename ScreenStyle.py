import tkinter as tk


class ScreenStyle:
    """
    Sentral stilmodell for Info-skjermen.
    Alle frames importerer denne klassen for farger, fonter og spacing –
    ingen magic numbers skal hardkodes i de individuelle frame-filene.
    """

    # ── Fargepalett ────────────────────────────────────────────────────
    # Gradient-bakgrunn (Apple-stil)
    GRAD_TOP        = "#C7D2FE"   # Myk indigo (topp)
    GRAD_BOTTOM     = "#FBCFE8"   # Myk rosa (bunn)
    BG_COLOR        = "#E4D0F3"   # Midtpunkt – brukes som fallback
    CARD_COLOR      = "#FFFFFF"   # Kortbakgrunn (brukes inne i kort)
    CARD_FROSTED    = "#F8F9FCEE" # Frosted glass – kan ikke bruke alpha i tk,
    CARD_FILL       = "#F1F2F6"   # Simulert frosted glass-farge
    ACCENT          = "#F97316"   # Primæraksent – oransje
    ACCENT_LIGHT    = "#DBEAFE"   # Lys aksent (bakgrunn-highlight)
    TEXT_PRIMARY    = "#111827"   # Primærtekst – nesten svart
    TEXT_SECONDARY  = "#6B7280"   # Sekundærtekst – mellomsgrå
    TEXT_MUTED      = "#9CA3AF"   # Dempet tekst
    DIVIDER         = "#E0E0E6"   # Skillelinje / borderfarge (mykere)
    SUCCESS         = "#10B981"   # Grønn aksent
    WARNING         = "#F59E0B"   # Gul/amber aksent

    # ── Typografi ──────────────────────────────────────────────────────
    # Klokke og hilsen
    FONT_TIME       = ("Helvetica", 60, "bold")   # HH:MM
    FONT_DATE       = ("Helvetica", 22)            # Dato under klokken
    FONT_GREETING   = ("Helvetica", 44, "bold")   # "God morgen" etc.

    # Inne i kort
    FONT_SECTION    = ("Helvetica", 22, "bold")   # Seksjonstittel ("Buss", "I dag" …)
    FONT_BODY       = ("Helvetica", 24)            # Vanlig innholdstekst
    FONT_BADGE      = ("Helvetica", 14, "bold")   # Kompakt badge-tekst (fremtidig bruk)

    # Bakoverkompatible aliaser (brukes av eksisterende kode)
    FONT_HEADER     = ("Helvetica", 44, "bold")
    FONT_SUBHEADER  = ("Helvetica", 22, "bold")
    FONT_SMALL      = ("Helvetica", 24)            # = FONT_BODY

    # ── Spacing ────────────────────────────────────────────────────────
    PAD_OUTER   = 20   # Ytre sidemarg (vindu → kort)
    PAD_CARD    = 14   # Indre kortpadding
    PAD_ROW     =  6   # Radavstand inne i kort
    PAD_SECTION = 12   # Loddrett avstand mellom kort

    # ── Hjelpemetode: kwargs for card-stil på tk.Frame ─────────────────
    @classmethod
    def card_kwargs(cls):
        """
        Returnerer en dict med bg for en tk.Frame inne i et RoundedCard.
        Kantene håndteres av RoundedCard-wrapperen.
        """
        return dict(
            bg=cls.CARD_FILL,
            highlightthickness=0,
            bd=0,
        )

    # Bakoverkompatibel instansattributt
    def __init__(self, color=None):
        self.HEADER_COLOR = color or self.ACCENT


class GradientCanvas(tk.Canvas):
    """
    Fullskjerm-Canvas som tegner en vertikal gradient fra GRAD_TOP til
    GRAD_BOTTOM.  Bruk med place(x=0, y=0, relwidth=1, relheight=1).
    """

    def __init__(self, parent):
        super().__init__(parent, highlightthickness=0, bd=0)
        self._c1 = self._hex_rgb(ScreenStyle.GRAD_TOP)
        self._c2 = self._hex_rgb(ScreenStyle.GRAD_BOTTOM)
        self.bind("<Configure>", self._draw)

    @staticmethod
    def _hex_rgb(h):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def _draw(self, event=None):
        self.delete("grad")
        w = self.winfo_width()
        h = self.winfo_height()
        if h < 2:
            return
        r1, g1, b1 = self._c1
        r2, g2, b2 = self._c2
        # Tegn 1 rektangel per 2 piksler for ytelse
        step = max(h // 200, 2)
        for y in range(0, h, step):
            t = y / max(h - 1, 1)
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            self.create_rectangle(0, y, w, y + step,
                                  fill=f"#{r:02x}{g:02x}{b:02x}",
                                  outline="", tags="grad")


class RoundedCard(tk.Canvas):
    """
    Canvas-basert kort med avrundede hjørner og frosted glass-effekt.
    Tegner en avrundet rektangel-bakgrunn og inneholder en inner-frame
    for innhold.  Bruk:
        card = RoundedCard(parent)
        card.pack(fill="x", ...)
        MyFrame(card.inner, ...).pack(fill="both", expand=True)
    """

    def __init__(self, parent, radius=18):
        super().__init__(parent, bg=ScreenStyle.BG_COLOR,
                         highlightthickness=0, bd=0)
        self._r = radius
        self._pad = 3

        self.inner = tk.Frame(self, bg=ScreenStyle.CARD_FILL,
                              highlightthickness=0, bd=0)
        self._win = self.create_window(self._pad, self._pad,
                                       window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_cfg)
        self.bind("<Configure>", self._redraw)

    def _on_inner_cfg(self, event):
        self.configure(height=event.height + self._pad * 2)

    def _redraw(self, event=None):
        self.delete("bg")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return
        r = min(self._r, w // 2, h // 2)
        # Doble punkter på kantene sikrer at spline passerer gjennom,
        # enkle punkter i hjørnene gir glatt kurve.
        pts = [
            r, 0,       r, 0,       w - r, 0,     w - r, 0,
            w, 0,
            w, r,       w, r,       w, h - r,     w, h - r,
            w, h,
            w - r, h,   w - r, h,   r, h,         r, h,
            0, h,
            0, h - r,   0, h - r,   0, r,         0, r,
            0, 0,
        ]
        self.create_polygon(pts, smooth=True,
                            fill=ScreenStyle.CARD_FILL,
                            outline=ScreenStyle.DIVIDER,
                            width=1, tags="bg")
        self.tag_lower("bg")
        self.itemconfigure(self._win, width=w - self._pad * 2)
