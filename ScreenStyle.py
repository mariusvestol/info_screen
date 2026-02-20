import tkinter as tk


class ScreenStyle:
    """
    Sentral stilmodell for Info-skjermen.
    Alle frames importerer denne klassen for farger, fonter og spacing –
    ingen magic numbers skal hardkodes i de individuelle frame-filene.
    """

    # ── Fargepalett ────────────────────────────────────────────────────
    BG_COLOR        = "#F0F2F5"   # Sidebackgrunn – kjølig lys grå
    CARD_COLOR      = "#FFFFFF"   # Kortbakgrunn
    ACCENT          = "#3B82F6"   # Primæraksent – moderne blå
    ACCENT_LIGHT    = "#DBEAFE"   # Lys aksent (bakgrunn-highlight)
    TEXT_PRIMARY    = "#111827"   # Primærtekst – nesten svart
    TEXT_SECONDARY  = "#6B7280"   # Sekundærtekst – mellomsgrå
    TEXT_MUTED      = "#9CA3AF"   # Dempet tekst
    DIVIDER         = "#E5E7EB"   # Skillelinje / borderfarge
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
            bg=cls.CARD_COLOR,
            highlightthickness=0,
            bd=0,
        )

    # Bakoverkompatibel instansattributt
    def __init__(self, color=None):
        self.HEADER_COLOR = color or self.ACCENT


class RoundedCard(tk.Canvas):
    """
    Canvas-basert kort med avrundede hjørner.
    Tegner en avrundet rektangel-bakgrunn og inneholder en inner-frame
    for innhold.  Bruk:
        card = RoundedCard(parent)
        card.pack(fill="x", ...)
        MyFrame(card.inner, ...).pack(fill="both", expand=True)
    """

    def __init__(self, parent, radius=16):
        super().__init__(parent, bg=ScreenStyle.BG_COLOR,
                         highlightthickness=0, bd=0)
        self._r = radius
        self._pad = 3

        self.inner = tk.Frame(self, bg=ScreenStyle.CARD_COLOR,
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
        # Doble punkter på kantene for å sikre at spline passerer gjennom,
        # enkle punkter i hjørnene for glatt kurve.
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
                            fill=ScreenStyle.CARD_COLOR,
                            outline=ScreenStyle.DIVIDER,
                            width=1, tags="bg")
        self.tag_lower("bg")
        self.itemconfigure(self._win, width=w - self._pad * 2)
