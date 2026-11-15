"""Identidad visual de Capital Curioso (extraída del cierre oficial capital_curioso_cierre.mp4).

Colores muestreados del clip de cierre:
  fondo azul marino  -> (10, 40, 90)   #0A285A
  rojo de la lupa    -> (252, 74, 86)  #FC4A56
  blanco             -> (255, 255, 255)
Tipografía: Poppins (SIL Open Font License), la misma familia geométrica del logotipo.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent          # capital-curioso/
ASSETS = RAIZ / "assets"
FUENTES = ASSETS / "fuentes"

NAVY = (10, 40, 90)
NAVY_DEEP = (6, 22, 52)
GRAPHITE = (16, 18, 24)
RED = (252, 74, 86)
WHITE = (255, 255, 255)
GOLD = (232, 186, 96)
GREY = (168, 180, 200)
GREY_DARK = (92, 104, 126)

FONT_FILES = {
    "medium": FUENTES / "Poppins_500Medium.ttf",
    "semibold": FUENTES / "Poppins_600SemiBold.ttf",
    "bold": FUENTES / "Poppins_700Bold.ttf",
    "black": FUENTES / "Poppins_800ExtraBold.ttf",
}

W, H, FPS = 1080, 1920, 30
