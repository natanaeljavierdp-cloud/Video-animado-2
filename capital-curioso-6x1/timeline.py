"""Tiempos clave (segundos), tomados de la transcripción palabra por palabra
de assets/narracion.mp3 (assets/data/words.json, faster-whisper 'small')."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(HERE, "assets/data/words.json"), encoding="utf-8"))

NARR_END = 66.59          # fin del audio de narración
CLOSE_START = 66.60       # cierre animado (clip de 3.5 s + 1.4 s congelado)
CLOSE_LEN = 4.9
TOTAL = CLOSE_START + CLOSE_LEN

# Escenas (inicio, fin)
S1 = (0.0, 8.90)      # gancho
S2 = (8.90, 17.00)    # la noticia
S3 = (17.00, 31.90)   # qué cambia
S4 = (31.90, 39.50)   # impacto
S5 = (39.50, 52.94)   # comparación LatAm
S6 = (52.94, 61.96)   # la pregunta
S7 = (61.96, CLOSE_START)  # encuesta
S8 = (CLOSE_START, TOTAL)  # cierre
CUTS = [S2[0], S3[0], S4[0], S5[0], S6[0], S7[0], S8[0]]

T = dict(
    # 1
    n83=0.38, anos=1.02, seis_dias=3.60, descansar=5.10, uno=5.72,
    hoy=7.02, acabo=7.98,
    # 2
    presidente=9.82, lula=10.18, decreto=11.18, escala=12.54, x61=12.88,
    vigente=14.10, y1943=14.86,
    # 3
    que_cambia=17.12, dic16=18.74, h44=21.06, h42=22.14, dos_dias=24.34,
    pagados=25.56, dic2027=26.64, h40=28.98, sin_bajar=30.24, salario=31.08,
    # 4
    m15=32.14, trabajan=34.24, por_fin=36.60, fin_semana=37.62,
    # 5
    brasil=39.68, colombia=41.44, chile=41.94, h42b=43.08, mexico=44.38,
    h48=45.74, h40mx=47.22, y2030=47.86, eeuu=49.72, h40us=52.08,
    ranking=50.30,
    # 6
    gran_pregunta=53.66, trabajar=54.98, funciona=56.48, empresas=58.36,
    trabajador=60.78,
    # 7
    cuantos=63.10, te_leo=65.18,
)
