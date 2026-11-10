"""Tiempos del video (en segundos), sincronizados con la transcripción por palabra
de assets/audio/transcripcion.json (voz Jaider, 76,3 s)."""

NARR_END = 76.28          # fin del audio de narración
CIERRE_START = 76.30      # empieza el cierre animado de Capital Curioso (3,5 s)
TOTAL = CIERRE_START + 3.5
FPS = 30

# (inicio, fin, nombre de escena)
SCENES = [
    (0.00, 3.55, "gancho_contador"),
    (3.55, 7.94, "gancho_banderas"),
    (7.94, 9.20, "trump"),
    (9.20, 11.90, "elecciones"),
    (11.90, 14.00, "fox"),
    (14.00, 16.75, "fin_de_anio"),
    (16.75, 19.20, "cita_no_la_necesitan"),
    (19.20, 20.95, "detalle"),
    (20.95, 24.95, "expediente"),
    (24.95, 28.40, "infografia_38"),
    (28.40, 30.85, "linea_tiempo"),
    (30.85, 35.70, "dudas"),
    (35.70, 37.45, "cita_definirlo"),
    (37.45, 43.30, "warrick"),
    (43.30, 44.95, "mapa"),
    (44.95, 48.95, "netanyahu"),
    (48.95, 51.90, "relojes"),
    (51.90, 53.80, "israel"),
    (53.80, 55.40, "golan"),
    (55.40, 57.50, "cita_golan"),
    (57.50, 59.30, "fundacion"),
    (59.30, 63.70, "contador_300"),
    (63.70, 65.60, "ranking"),
    (65.60, 70.00, "pagando"),
    (70.00, CIERRE_START, "encuesta"),
    (CIERRE_START, TOTAL, "cierre"),
]

# Golpes de sonido ("boom") en cada dato fuerte: (tiempo, intensidad 0..1)
HITS = [
    (2.62, 0.6), (6.86, 1.0), (8.14, 0.5), (12.96, 0.45), (17.82, 0.7),
    (19.28, 0.8), (23.30, 0.9), (26.12, 0.6), (27.44, 0.45), (29.64, 0.8),
    (35.74, 0.55), (41.90, 0.7), (44.96, 0.55), (48.22, 0.85), (50.94, 0.65),
    (55.48, 0.8), (61.54, 1.0), (63.78, 0.65), (68.96, 0.9), (70.14, 0.6),
]

# Barridos de aire en los cortes
WHOOSHES = [s for s, _, _ in SCENES[1:]]

# Ticks de contador: (inicio, fin, ticks por segundo)
TICK_RANGES = [(0.15, 2.62, 18), (25.08, 26.12, 16), (59.36, 61.54, 16)]

# Transiciones con la lupa de Capital Curioso
LUPA_TRANSITIONS = [7.94, 19.20, 30.85, 43.30, 57.50, 70.00]

# Tramos sin subtítulos (la pantalla ya muestra el texto como gráfico)
NO_SUBS = [(6.75, 7.94), (17.75, 19.20), (19.20, 20.95), (35.70, 37.45),
           (55.40, 57.50), (70.00, TOTAL)]

# Correcciones a la transcripción automática
FIXES = {"¿Sú": "¿Su", "Atlante": "Atlantic"}

# Palabras resaltadas en rojo en los subtítulos
KEYWORDS = {
    "4", "acabó", "noviembre", "elecciones", "fox", "news", "termina", "necesitan",
    "detalle", "obama", "2016", "38", "10", "2028", "militar", "efectivo",
    "definirlo", "2027", "netanyahu", "cero", "dos", "meses", "golan", "golpe",
    "severo", "300", "cualquier", "pagándolas", "trump", "israel",
}
