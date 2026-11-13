"""Línea de tiempo compartida por el render de video y la mezcla de audio.

Todos los tiempos (en segundos) salen de la transcripción palabra por palabra
de la voz (assets/words.json), así cada escena cae justo con la narración.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
VOICE_END = 70.62
DURATION = 73.8          # voz + cierre animado de Capital Curioso

# ---- Escenas (inicio, fin) ---------------------------------------------
S1 = (0.0, 7.3)     # Soldados salvadoreños + mapa de la isla
S2 = (7.3, 21.1)    # Bukele, flecha El Salvador -> Puerto Príncipe, contador
S3 = (21.1, 34.45)  # Línea de tiempo: cuartel 400 Mawozo / estadio
S4 = (34.45, 43.15) # ¿Y nosotros? Abinader + cita
S5 = (43.15, 54.9)  # ONU / Amnistía (pantalla dividida)
S6 = (54.9, 62.45)  # Frontera, Jimaní, verja
S7 = (62.45, VOICE_END)  # Pregunta + encuesta
OUTRO = (VOICE_END, DURATION)

# ---- Planos de foto: (inicio, archivo, foco x, foco y, zoom0, zoom1, deriva x) ----
SHOTS = [
    (0.0,   "p10", 0.37, 0.50, 1.10, 1.22, -0.03),  # soldado salvadoreño + blindado
    (3.6,   "p14", 0.57, 0.42, 1.18, 1.06,  0.03),  # soldados con casco
    (7.3,   "p13", 0.62, 0.50, 1.05, 1.16, -0.03),  # llegada al aeropuerto
    (9.55,  "p15", 0.70, 0.36, 1.08, 1.18,  0.00),  # Nayib Bukele
    (14.0,  "p12", 0.42, 0.45, 1.06, 1.16,  0.03),  # fuerza salvadoreña formada
    (16.8,  "p07", 0.24, 0.45, 1.10, 1.20,  0.02),  # blindados
    (21.25, "p09", 0.48, 0.55, 1.06, 1.16,  0.00),  # calles de Puerto Príncipe
    (23.85, "p06", 0.58, 0.50, 1.18, 1.06, -0.03),  # convoy aéreo
    (26.4,  "p04", 0.55, 0.50, 1.06, 1.16,  0.03),  # estadio Sylvio Cator
    (30.6,  "p07", 0.76, 0.55, 1.08, 1.18, -0.02),  # estadio (aérea)
    (34.45, "p05", 0.47, 0.30, 1.04, 1.14,  0.00),  # Abinader con mandos
    (38.3,  "p03", 0.50, 0.30, 1.04, 1.14,  0.00),  # Abinader
    (43.15, "p11", 0.72, 0.60, 1.06, 1.14,  0.00),  # calle de Puerto Príncipe
    (45.05, "SPLIT", 0, 0, 0, 0, 0),                # ONU / Amnistía
    (54.9,  "p00", 0.46, 0.55, 1.04, 1.16,  0.02),  # verja fronteriza
    (62.45, "p01B", 0.50, 0.60, 1.05, 1.12,  0.00), # pregunta final (fondo desenfocado)
    (VOICE_END, "OUTRO", 0, 0, 0, 0, 0),
]

# ---- Efectos de sonido sincronizados -------------------------------------
# tipo: whoosh, hit, boom, type (con duración), pop, tick (con duración), ding, sting, riser
CUES = [
    ("boom", 0.05), ("riser", 3.4, 1.0),
    ("whoosh", 3.55), ("pop", 3.3), ("pop", 4.75), ("hit", 5.0),
    ("whoosh", 7.25), ("type", 7.5, 1.3),
    ("whoosh", 9.5), ("pop", 9.75), ("whoosh", 10.4), ("swoosh_long", 10.9),
    ("whoosh", 13.95), ("pop", 14.1), ("pop", 14.4), ("pop", 14.7), ("pop", 15.0),
    ("whoosh", 16.75), ("hit", 16.95), ("tick", 19.05, 1.2), ("ding", 20.25),
    ("whoosh", 21.2), ("type", 21.6, 1.6), ("whoosh", 23.8), ("boom", 25.1),
    ("whoosh", 26.35), ("type", 27.3, 1.5), ("pop", 27.7),
    ("whoosh", 30.55), ("riser", 30.6, 0.9), ("hit", 31.55),
    ("whoosh", 34.4), ("hit", 34.6), ("pop", 35.8), ("whoosh", 38.25), ("type", 38.5, 1.1),
    ("whoosh", 43.1), ("hit", 43.3), ("whoosh", 45.0), ("pop", 45.4), ("type", 45.7, 1.4),
    ("whoosh", 51.2), ("pop", 51.4), ("type", 51.6, 1.2),
    ("whoosh", 54.85), ("pop", 56.6), ("swoosh_long", 57.85), ("boom", 59.0),
    ("pop", 59.75), ("pop", 60.95),
    ("whoosh", 62.4), ("riser", 61.6, 0.9), ("hit", 62.6), ("pop", 67.75),
    ("hit", 68.2), ("hit", 69.5),
    ("whoosh", 70.6), ("sting", 70.85),
]


def load_words():
    """Palabras con tiempos, corrigiendo los nombres que la transcripción escribe mal."""
    raw = json.load(open(os.path.join(HERE, "assets", "words.json")))
    fixes = {"Najib": "Nayib", "Maguoso,": "Mawozo,", "verga": "verja", "debe": "¿debe"}
    out, i = [], 0
    while i < len(raw):
        w = dict(raw[i])
        if w["w"] == "2" and i + 1 < len(raw) and raw[i + 1]["w"].startswith("."):
            w["w"] = "2" + raw[i + 1]["w"].replace(".", ",", 1)
            w["e"] = raw[i + 1]["e"]
            i += 1
        w["w"] = fixes.get(w["w"], w["w"])
        out.append(w)
        i += 1
    return out
