"""Línea de tiempo del video (segundos), sincronizada con la narración."""

FPS = 30
W, H = 1080, 1920
MAIN_END = 72.6          # fin de la narración + respiro
CLOSE_LEN = 3.5          # cierre_capital.mp4
TOTAL = MAIN_END + CLOSE_LEN

# Cortes de escena grandes (glitch + whoosh)
SCENE_CUTS = [4.5, 16.0, 21.75, 46.6, 50.75, 59.4, 68.6]
# Cortes internos (zoom punch + whoosh suave)
SHOT_CUTS = [7.7, 9.6, 12.3, 14.5, 17.4, 18.9, 29.1, 33.0, 38.9, 42.5, 55.7, 63.0, 65.6]

# Golpes / acentos de sonido: (tiempo, tipo)
HITS = [
    (0.02, "impact"),
    (3.08, "stamp"),        # "firmó igual"
    (4.74, "pop"),          # 16 NOV
    (10.06, "counter"),     # 107 millones (tic tic)
    (11.36, "impact_soft"),
    (13.54, "pop"),         # 4G
    (14.64, "pop"),         # 5G
    (19.66, "stamp"),       # Ministerio de Defensa
    (23.66, "pop"),         # rótulo Leah Campos
    (27.56, "pop"),         # días antes
    (35.46, "glitch"),      # China
    (37.0, "impact_soft"),  # 20 %
    (39.2, "pop"),          # Indotel responde
    (42.08, "pop"), (42.54, "pop"), (44.62, "pop"), (45.38, "pop"),
    (47.76, "pop"),         # aquí (RD)
    (49.5, "ping"), (50.08, "ping"),  # Haití / Perú
    (52.5, "stamp"),        # visa revocada
    (54.36, "riser_short"), # cable
    (58.52, "glitch"),      # Huawei tachado
    (61.38, "impact_soft"), # pelea
    (66.56, "impact_soft"), # soberanía
    (67.7, "glitch"),       # riesgo
    (68.6, "impact"),       # pregunta final
    (70.66, "pop"), (71.68, "pop"),
    (MAIN_END + 1.0, "ping"),  # logo del cierre
]
