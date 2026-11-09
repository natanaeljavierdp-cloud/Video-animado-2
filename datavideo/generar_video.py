#!/usr/bin/env python3
"""
Generador de videos verticales (1080x1920) con gráficos estadísticos animados.
Uso:  python3 generar_video.py config.json salida.mp4
Requiere: python3, matplotlib, numpy, ffmpeg.
"""
import json, os, subprocess, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.animation import FuncAnimation, FFMpegWriter

# ---------- Estilo por defecto (se puede sobreescribir en el JSON -> "estilo") ----------
ESTILO = {
    "fondo": "#0F1419",
    "texto": "#F5F5F5",
    "texto_suave": "#9AA4AE",
    "acento": "#E8B23A",      # barra/linea destacada
    "barra": "#3A7BD5",       # barras normales
    "rejilla": "#2A323B",
    "fuente": "Inter",
}

FPS = 30
W, H = 1080, 1920
DPI = 120


def ease(t):
    """Ease-out cúbico: arranca rápido y frena suave."""
    t = np.clip(t, 0, 1)
    return 1 - (1 - t) ** 3


def formatear(v, cfg):
    dec = cfg.get("decimales", 0)
    esc = cfg.get("escala", 1)
    txt = f"{v / esc:,.{dec}f}"
    if cfg.get("separador_es", True):  # 10,760,028 -> 10.760.028 ; 1.5 -> 1,5
        txt = txt.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{cfg.get('prefijo', '')}{txt}{cfg.get('sufijo', '')}"


def main(ruta_cfg, ruta_salida):
    cfg = json.load(open(ruta_cfg, encoding="utf-8"))
    est = {**ESTILO, **cfg.get("estilo", {})}
    plt.rcParams["font.family"] = est["fuente"]

    etiquetas = [str(e) for e in cfg["etiquetas"]]
    valores = np.array(cfg["valores"], dtype=float)
    n = len(valores)
    tipo = cfg.get("tipo", "barras")          # "barras" | "linea"
    dur_anim = cfg.get("duracion_animacion", 6.0)
    dur_pausa = cfg.get("pausa_final", 2.5)
    total = int((dur_anim + dur_pausa) * FPS)
    paso = dur_anim / n                         # segundos por elemento

    # --- Sincronización opcional con la narración ---
    # "tiempos": segundo en que empieza a crecer cada barra (uno por etiqueta).
    # "audio": ruta del MP3 (relativa al JSON); se mide su duración y se une al video.
    base = os.path.dirname(os.path.abspath(ruta_cfg))
    audio = cfg.get("audio")
    if audio:
        audio = os.path.join(base, audio)
    tiempos = cfg.get("tiempos")
    if tiempos:
        assert len(tiempos) == n, "'tiempos' debe tener un valor por etiqueta"
        inicios = np.array(tiempos, dtype=float)
        crece = cfg.get("duracion_barra", 1.0)
        dur_anim = inicios[-1] + crece
    else:
        inicios = np.arange(n) * paso
        crece = paso * 1.6
    fin = dur_anim + dur_pausa
    if audio:
        dur_audio = float(subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", audio]).decode().strip())
        fin = max(fin, dur_audio + cfg.get("cola_audio", 1.0))
    total = int(round(fin * FPS))

    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=est["fondo"])

    # Textos fijos
    fig.text(0.07, 0.92, cfg.get("titulo", ""), color=est["texto"], fontsize=40,
             fontweight="bold", va="top", wrap=True)
    fig.text(0.07, 0.795, cfg.get("subtitulo", ""), color=est["texto_suave"],
             fontsize=22, va="top")
    fig.text(0.07, 0.165, "Fuente: " + cfg.get("fuente", ""), color=est["texto_suave"],
             fontsize=16)
    contador = fig.text(0.07, 0.755, "", color=est["acento"], fontsize=64,
                        fontweight="bold", va="top")
    etiqueta_contador = fig.text(0.07, 0.685, "", color=est["texto"], fontsize=22, va="top")
    # Remate opcional: {"texto": "×5 en 70 años", "inicio": 20.0}
    remate_cfg = cfg.get("remate")
    remate = fig.text(0.10, 0.615, remate_cfg["texto"] if remate_cfg else "",
                      color=est["acento"], fontsize=44, fontweight="bold", va="top", alpha=0)

    ax = fig.add_axes([0.08, 0.235, 0.78, 0.40])  # zona segura TikTok/Reels
    ax.set_facecolor(est["fondo"])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=est["texto_suave"], labelsize=18, length=0)
    ax.set_yticks([])
    ymax = valores.max() * 1.18
    ax.set_ylim(0, ymax)
    x = np.arange(n)
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas, rotation=0 if n <= 8 else 45)
    ax.axhline(0, color=est["rejilla"], lw=2)

    if tipo == "barras":
        barras = ax.bar(x, np.zeros(n), width=0.68, color=est["barra"])
        textos = [ax.text(i, 0, "", ha="center", va="bottom", color=est["texto"],
                          fontsize=16, fontweight="bold") for i in range(n)]
    else:
        linea, = ax.plot([], [], color=est["acento"], lw=6, solid_capstyle="round")
        punto, = ax.plot([], [], "o", color=est["acento"], ms=18)
        textos = [ax.text(i, 0, "", ha="center", va="bottom", color=est["texto"],
                          fontsize=16, fontweight="bold") for i in range(n)]

    corto = {**cfg, **cfg.get("formato_corto", {})}

    def actualizar(f):
        t = f / FPS
        actual = 0.0
        idx_actual = 0
        if tipo == "barras":
            for i, b in enumerate(barras):
                p = ease((t - inicios[i]) / crece)
                h = valores[i] * p
                b.set_height(h)
                # La barra que está creciendo ahora va en color de acento
                activa = max(int(np.searchsorted(inicios, t, side="right")) - 1, 0)
                b.set_color(est["acento"] if i == activa else est["barra"])
                if p > 0.05:
                    textos[i].set_position((i, h + ymax * 0.01))
                    textos[i].set_text(formatear(h, corto))
                if p > 0:
                    actual, idx_actual = h, i
        else:
            prog = min(t / dur_anim, 1) * (n - 1)
            k = int(np.floor(prog))
            fr = prog - k
            xs = list(x[:k + 1]); ys = list(valores[:k + 1])
            if k < n - 1:
                xs.append(k + fr); ys.append(valores[k] + (valores[k + 1] - valores[k]) * fr)
            linea.set_data(xs, ys)
            punto.set_data([xs[-1]], [ys[-1]])
            for i in range(n):
                if i <= prog + 1e-6:
                    textos[i].set_position((i - 0.15, valores[i] + ymax * 0.06))
                    textos[i].set_text(formatear(valores[i], corto))
            actual, idx_actual = ys[-1], min(k, n - 1)
        if remate_cfg:
            remate.set_alpha(float(np.clip((t - remate_cfg["inicio"]) / 0.4, 0, 1)))
        contador.set_text(formatear(actual, cfg))
        etiqueta_contador.set_text(f"{cfg.get('etiqueta_contador', '')} {etiquetas[idx_actual]}".strip())
        return []

    anim = FuncAnimation(fig, actualizar, frames=total, blit=False)
    writer = FFMpegWriter(fps=FPS, codec="libx264",
                          extra_args=["-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "18"])
    destino = ruta_salida + ".sin_audio.mp4" if audio else ruta_salida
    anim.save(destino, writer=writer, dpi=DPI)
    if audio:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", destino, "-i", audio,
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "192k", ruta_salida], check=True)
        os.remove(destino)
    print("Listo:", ruta_salida)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
