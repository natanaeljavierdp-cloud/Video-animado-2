"""Utilidades compartidas: lectura del EDL y conversión de tiempos clip -> línea de tiempo."""
import json, os

PROY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(PROY, "build")
ASSETS = os.path.join(PROY, "assets")
os.makedirs(BUILD, exist_ok=True)


def cargar_edl():
    edl = json.load(open(os.path.join(PROY, "edl.json"), encoding="utf-8"))
    fps = edl["fps"]
    f = 0
    for c in edl["clips"]:
        c["frames"] = c["out"] - c["in"]
        c["t0_frame"] = f
        c["t0"] = f / fps
        c["dur"] = c["frames"] / fps
        c["ruta"] = os.path.normpath(os.path.join(PROY, edl["fuentes_dir"], c["archivo"]))
        f += c["frames"]
    edl["frames_clips"] = f
    edl["frames_total"] = f + edl["end_card_frames"]
    edl["dur_total"] = edl["frames_total"] / fps
    edl["por_id"] = {c["id"]: c for c in edl["clips"]}
    return edl


def tl(edl, clip_id, src):
    """Segundo del clip original -> segundo de la línea de tiempo final."""
    c = edl["por_id"][clip_id]
    return c["t0"] + src - c["in"] / edl["fps"]


def transcripcion():
    return json.load(open(os.path.join(BUILD, "transcripcion_large-v3.json"), encoding="utf-8"))
