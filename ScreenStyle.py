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
    FONT_GREETING   = ("Helvetica", 44, "bold")   # "God kveld / mester"

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
        Returnerer en dict med bg, highlightbackground og highlightthickness
        som gir en `tk.Frame` et enkelt kort-utseende (hvit bakgrunn + 1 px
        grå kant).  Bruk som:  super().__init__(parent, **ss.card_kwargs())
        """
        return dict(
            bg=cls.CARD_COLOR,
            highlightbackground=cls.DIVIDER,
            highlightthickness=1,
        )

    # Bakoverkompatibel instansattributt (ingen frames oppretter faktisk
    # en instans i dag, men beholder __init__ for fremtidig bruk)
    def __init__(self, color=None):
        self.HEADER_COLOR = color or self.ACCENT
