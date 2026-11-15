"""Tiempos de la pieza, derivados de la narración real (transcripcion_palabras.json).

Todos los tiempos están en segundos de NARRACIÓN (0 = inicio del archivo de voz).
El vídeo comienza OFFSET segundos antes de la voz.
"""
OFFSET = 0.6            # respiro inicial antes de la voz
XF = 0.40               # duración de los fundidos entre escenas
CIERRE_INICIO = 60.40   # inicio del clip oficial de cierre (3.5 s)
FIN_NARRACION = 64.70
DURACION_VIDEO = OFFSET + 65.80   # = 66.4 s

# (escena, inicio, fin) — los cortes caen en las pausas de la voz
ESCENAS = [
    ("s1", -OFFSET, 10.10),       # apertura: surtidor + titular
    ("s2", 10.10, 21.05),         # mapa + fecha + condición
    ("s3", 21.05, 28.42),         # comparación tope vs. asignación
    ("sq", 28.42, 30.00),         # ¿Qué significa esto?
    ("s4", 30.00, 39.05),         # costo internacional / subsidio / precio
    ("s5a", 39.05, 47.72),        # el costo no desaparece
    ("s5b", 47.72, 56.25),        # la condición del tope
    ("s5c", 56.25, CIERRE_INICIO),  # pregunta de sostenibilidad
    ("s6", CIERRE_INICIO, 99.0),  # cierre con logo oficial
]

# (inicio, fin, [líneas]) — máx. 2 líneas, 3-6 palabras por bloque
SUBTITULOS = [
    (0.00, 1.50, ["¿La gasolina no subirá"]),
    (1.50, 3.30, ["en República Dominicana", "hasta enero?"]),
    (3.68, 6.10, ["Hay un detalle que", "cambia toda la historia:"]),
    (6.52, 8.00, ["el Gobierno puso un límite"]),
    (8.00, 9.95, ["a lo que está dispuesto", "a subsidiar."]),
    (10.32, 12.40, ["El anuncio contempla", "mantener estables"]),
    (12.40, 14.10, ["los principales combustibles"]),
    (14.10, 16.50, ["hasta el 7 de enero", "de 2027,"]),
    (16.68, 18.50, ["siempre que el subsidio", "no supere"]),
    (18.50, 21.00, ["1,500 millones de pesos", "semanales."]),
    (21.24, 24.20, ["Para la semana del", "14 al 20 de noviembre,"]),
    (24.20, 25.20, ["el Estado destinó"]),
    (25.20, 28.42, ["796.4 millones de pesos."]),
    (28.46, 30.00, ["¿Qué significa esto?"]),
    (30.12, 32.40, ["Cuando el mercado", "internacional encarece"]),
    (32.40, 34.10, ["los combustibles,", "el Gobierno puede"]),
    (34.10, 35.88, ["asumir parte del costo,"]),
    (35.88, 37.05, ["en lugar de trasladarlo"]),
    (37.05, 39.00, ["completamente", "a los consumidores."]),
    (39.24, 41.02, ["Pero mantener", "los precios congelados"]),
    (41.02, 43.45, ["no significa que", "desaparezca el costo."]),
    (43.58, 45.50, ["La diferencia cubierta", "por el subsidio"]),
    (45.50, 47.72, ["se financia con", "recursos públicos."]),
    (47.78, 50.50, ["Y si el subsidio supera", "el límite anunciado,"]),
    (50.50, 53.00, ["el congelamiento deja", "de estar garantizado."]),
    (53.22, 54.62, ["Eso no significa", "que los precios"]),
    (54.62, 56.22, ["aumenten automáticamente."]),
    (56.28, 57.85, ["La pregunta es:"]),
    (57.90, 60.75, ["¿qué tan sostenible resulta", "mantener esta medida?"]),
    (61.30, 62.72, ["Capital Curioso."]),
    (62.72, 64.60, ["La historia detrás", "de los números."]),
]
