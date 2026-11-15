#!/usr/bin/env python3
"""Capital Curioso — "El costo de congelar los combustibles".

Genera los fotogramas 1080x1920 @30 fps con PIL y los envía a FFmpeg.
Todas las animaciones se calculan por código a partir de los tiempos reales
de la narración (combustibles/transcripcion_palabras.json).

Uso:
  python3 render.py video  <salida_sin_audio.mp4> [--sin-subtitulos]
  python3 render.py frame  <t_video_segundos> <salida.png>
  python3 render.py portada <salida.png>
"""
import math
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from marca import (ASSETS, FONT_FILES, FPS, GOLD, GRAPHITE, GREY, GREY_DARK,  # noqa: E402
                   H, NAVY, NAVY_DEEP, RED, W, WHITE)

from tiempos import (CIERRE_INICIO, DURACION_VIDEO, ESCENAS, OFFSET,  # noqa: E402
                     SUBTITULOS, XF)

FOTOS = ASSETS / "fotos"
CIERRE = ASSETS / "referencias" / "capital_curioso_cierre.mp4"
SHOW_SUBS = True

# ----------------------------------------------------------------- utilidades


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, t0, dur):
    return clamp((t - t0) / dur) if dur > 0 else float(t >= t0)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_back(x):
    c1, c3 = 1.4, 2.4
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


@lru_cache(maxsize=None)
def font(weight, size):
    return ImageFont.truetype(str(FONT_FILES[weight]), size)


@lru_cache(maxsize=512)
def text_sprite(text, weight, size, color, tracking=0, shadow=0.55, stroke=0):
    """Texto como RGBA recortado, con sombra suave opcional."""
    f = font(weight, size)
    if tracking:
        widths = [f.getlength(c) for c in text]
        tw = int(sum(widths) + tracking * (len(text) - 1)) + 4
    else:
        tw = int(f.getlength(text)) + 4
    asc, desc = f.getmetrics()
    th = asc + desc
    pad = 30
    im = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def draw(dr, fill, sw=0):
        if tracking:
            x = pad
            for c, wdt in zip(text, widths):
                dr.text((x, pad), c, font=f, fill=fill, stroke_width=sw, stroke_fill=fill)
                x += wdt + tracking
        else:
            dr.text((pad, pad), text, font=f, fill=fill, stroke_width=sw, stroke_fill=fill)

    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        draw(ImageDraw.Draw(sh), (0, 0, 0, int(255 * shadow)), sw=max(2, size // 22))
        sh = sh.filter(ImageFilter.GaussianBlur(max(3, size // 9)))
        im = Image.alpha_composite(im, sh)
        d = ImageDraw.Draw(im)
    if stroke:
        draw(d, (0, 0, 0, 150), sw=stroke)
    draw(d, color + (255,) if len(color) == 3 else color)
    return im


def place(canvas, sprite, x, y, anchor="mm", opacity=1.0, scale=1.0):
    """Pega un sprite RGBA. anchor: l/m/r + t/m/b (el sprite incluye 30 px de margen)."""
    if opacity <= 0.003:
        return
    sp = sprite
    if scale != 1.0:
        sp = sp.resize((max(1, int(sp.width * scale)), max(1, int(sp.height * scale))), Image.BICUBIC)
    if opacity < 0.999:
        a = sp.getchannel("A").point(lambda v: int(v * opacity))
        sp = sp.copy()
        sp.putalpha(a)
    w, h = sp.size
    ax, ay = anchor[0], anchor[1]
    px = x - (w / 2 if ax == "m" else (w - 30 * scale if ax == "r" else 30 * scale))
    py = y - (h / 2 if ay == "m" else (h - 30 * scale if ay == "b" else 30 * scale))
    canvas.alpha_composite(sp, (int(round(px)), int(round(py))))


def text(canvas, s, x, y, size, weight="bold", color=WHITE, anchor="mm", opacity=1.0,
         tracking=0, shadow=0.55, scale=1.0):
    place(canvas, text_sprite(s, weight, size, color, tracking, shadow), x, y, anchor, opacity, scale)


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def with_opacity(img, op):
    if op >= 0.999:
        return img
    a = img.getchannel("A").point(lambda v: int(v * op))
    img = img.copy()
    img.putalpha(a)
    return img


def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle([int(v) for v in box], radius=r, fill=fill, outline=outline, width=width)


def rgba(c, a):
    return tuple(c[:3]) + (int(255 * clamp(a)),)


# ----------------------------------------------------------- fondos y fotos


@lru_cache(maxsize=None)
def bg_gradient(kind="navy"):
    y = np.linspace(0, 1, H)[:, None]
    if kind == "navy":
        top, bot = np.array(NAVY_DEEP), np.array(GRAPHITE)
    else:
        top, bot = np.array((14, 22, 40)), np.array((10, 11, 15))
    g = top * (1 - y) + bot * y
    arr = np.repeat(g[:, None, :], W, axis=1).reshape(H, W, 3)
    # brillo radial suave arriba (profundidad)
    yy, xx = np.mgrid[0:H, 0:W]
    glow = np.exp(-(((xx - 540) / 700) ** 2 + ((yy - 620) / 760) ** 2))
    arr = arr + glow[..., None] * np.array((14, 30, 62)) * 0.9
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")


@lru_cache(maxsize=None)
def grid_layer():
    im = layer()
    d = ImageDraw.Draw(im)
    for x in range(0, W, 90):
        d.line([(x, 0), (x, H)], fill=(255, 255, 255, 9))
    for y in range(0, H, 90):
        d.line([(0, y), (W, y)], fill=(255, 255, 255, 9))
    return im


@lru_cache(maxsize=None)
def vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2)
    a = np.clip((r - 0.62) / 0.6, 0, 1) ** 1.6 * 150
    # banda inferior para la legibilidad de subtítulos
    band = np.clip((yy - 1180) / 220, 0, 1) * np.clip((1700 - yy) / 160 + 0.6, 0, 1) * 70
    a = np.clip(a + band, 0, 210)
    arr = np.zeros((H, W, 4), np.uint8)
    arr[..., 3] = a.astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


@lru_cache(maxsize=None)
def photo(name, warm=False):
    """Carga y gradúa una foto: ligera desaturación y sombras hacia el azul marca."""
    im = Image.open(FOTOS / name).convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255
    lum = a @ np.array([0.299, 0.587, 0.114])
    a = a * 0.82 + lum[..., None] * 0.18                         # desaturar 18 %
    shadow_tint = np.array([0.04, 0.10, 0.24])
    a = a + (1 - lum[..., None]) ** 2 * shadow_tint * 0.55        # sombras azuladas
    a = np.clip((a - 0.5) * 1.08 + 0.5, 0, 1) ** 1.05             # contraste
    out = Image.fromarray((a * 255).astype(np.uint8))
    if out.width < 1500:  # reescalado previo de alta calidad
        s = 1.6
        out = out.resize((int(out.width * s), int(out.height * s)), Image.LANCZOS)
        out = out.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    return out


@lru_cache(maxsize=None)
def feather_mask(ph, top=170, bottom=220):
    y = np.arange(ph)
    a = np.clip(y / top, 0, 1) * np.clip((ph - 1 - y) / bottom, 0, 1)
    a = (np.sin(a * np.pi / 2) ** 2 * 255).astype(np.uint8)
    return Image.fromarray(np.repeat(a[:, None], W, axis=1), "L")


def photo_panel(canvas, name, y0, y1, k, zoom=(1.0, 1.08), pan=(0.0, 0.0), dim=0.0,
                label=True, opacity=1.0, focus=(0.5, 0.5)):
    """Panel fotográfico a todo el ancho con movimiento de cámara (k: 0..1)."""
    src = photo(name)
    ph = y1 - y0
    sw, sh = src.size
    s0 = max(W / sw, ph / sh)
    z = zoom[0] + (zoom[1] - zoom[0]) * ease_in_out(clamp(k))
    s = s0 * z
    vw, vh = W / s, ph / s
    p = pan[0] + (pan[1] - pan[0]) * ease_in_out(clamp(k))
    cx = clamp(sw * focus[0] + p * (sw - vw) / 2, vw / 2, sw - vw / 2)
    cy = clamp(sh * focus[1], vh / 2, sh - vh / 2)
    img = src.transform((W, ph), Image.AFFINE, (1 / s, 0, cx - vw / 2, 0, 1 / s, cy - vh / 2),
                        resample=Image.BICUBIC)
    if dim > 0:
        img = Image.blend(img, Image.new("RGB", img.size, NAVY_DEEP), dim)
    img = img.convert("RGBA")
    m = feather_mask(ph)
    if opacity < 1:
        m = m.point(lambda v: int(v * opacity))
    img.putalpha(m)
    canvas.alpha_composite(img, (0, y0))
    if label:
        text(canvas, "IMAGEN ILUSTRATIVA", 90, 284, 18, "semibold", (255, 255, 255),
             anchor="lm", opacity=0.6 * opacity, tracking=3, shadow=0.7)


# ------------------------------------------------------------ marca / cabecera


@lru_cache(maxsize=None)
def logo_mark(size):
    """Lupa con signo de interrogación, recortada del cierre oficial."""
    im = Image.open(ASSETS / "logo.png").convert("RGB")
    a = np.asarray(im).astype(np.int32)
    diff = np.abs(a - np.array(NAVY)).sum(2)
    ys, xs = np.where(diff[:470] > 60)
    box = (xs.min() - 4, ys.min() - 4, xs.max() + 5, ys.max() + 5)
    crop = im.crop(box)
    ca = np.asarray(crop).astype(np.float32)
    d = np.abs(ca - np.array(NAVY)).sum(2)
    alpha = np.clip(d / 140, 0, 1)
    # des-mezcla del fondo marino
    rgb = (ca - np.array(NAVY) * (1 - alpha[..., None])) / np.maximum(alpha[..., None], 1e-3)
    out = np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8)
    lm = Image.fromarray(out, "RGBA")
    return lm.resize((size, int(lm.height * size / lm.width)), Image.LANCZOS)


def brand_bug(canvas, op=1.0):
    """Marca fija (lupa + nombre); se dibuja una sola vez por fotograma."""
    if op <= 0.003:
        return
    lm = logo_mark(54)
    canvas.alpha_composite(with_opacity(lm, op), (84, 232 - lm.height // 2))
    text(canvas, "CAPITAL CURIOSO", 152, 232, 25, "bold", WHITE, anchor="lm", opacity=op,
         tracking=2, shadow=0.6)


def header(canvas, kicker, op=1.0):
    """Separador rojo + antetítulo de la escena (la marca la dibuja brand_bug)."""
    if op <= 0:
        return
    x2 = 152 + font("bold", 25).getlength("CAPITAL CURIOSO") + 2 * 14 + 22
    d = ImageDraw.Draw(canvas)
    d.rectangle([x2, 218, x2 + 4, 246], fill=rgba(RED, op))
    text(canvas, kicker, x2 + 22, 232, 25, "semibold", GREY, anchor="lm", opacity=op,
         tracking=2, shadow=0.6)


def fuente_line(canvas, s, y=1238, op=1.0):
    text(canvas, s, 90, y, 21, "medium", GREY, anchor="lm", opacity=0.85 * op, shadow=0.7)


# ------------------------------------------------------------------ escenas
# Cada escena recibe T = tiempo de la narración (s) y devuelve una imagen RGBA.


def s1_apertura(T):
    c = bg_gradient().copy()
    k = (T + OFFSET) / 11.3
    photo_panel(c, "05_bomba_gasolina.jpg", 300, 1330, k, zoom=(1.06, 1.18), pan=(-0.35, 0.25),
                focus=(0.55, 0.5))
    header(c, "COMBUSTIBLES  RD", ease_out(prog(T, -0.4, 0.6)))
    # titular
    lines = [("¿GASOLINA", WHITE), ("CONGELADA", RED), ("HASTA ENERO?", WHITE)]
    lift = ease_in_out(prog(T, 6.3, 0.6)) * 0
    for i, (s, col) in enumerate(lines):
        p = ease_out(prog(T, -0.2 + i * 0.22, 0.6))
        text(c, s, 90, 410 + i * 116 + (1 - p) * 40 - lift, 108, "black", col, anchor="lm",
             opacity=p, shadow=0.75)
    # etiqueta: el límite
    p = ease_back(prog(T, 7.55, 0.5))
    if p > 0:
        d = ImageDraw.Draw(c)
        w = 640 * clamp(p)
        rrect(d, (90, 1060, 90 + w, 1150), 10, fill=rgba(RED, 0.94))
        text(c, "EL GOBIERNO PUSO UN LÍMITE", 120, 1105, 37, "bold", WHITE, anchor="lm",
             opacity=prog(T, 7.75, 0.3), shadow=0.25)
    p2 = prog(T, 3.7, 0.5)
    text(c, "Un detalle que cambia la historia", 92, 1000, 34, "semibold", GREY, anchor="lm",
         opacity=p2 * (1 - prog(T, 7.4, 0.3)), shadow=0.8)
    return c


def s2_anuncio(T):
    c = bg_gradient().copy()
    k = (T - 9.8) / 11.6
    dim = 0.25 + 0.3 * ease_in_out(prog(T, 13.6, 0.8))
    photo_panel(c, "04_mapa_rd.jpg", 290, 1300, k, zoom=(1.05, 1.16), pan=(0.0, 0.0), dim=dim,
                focus=(0.5, 0.48))
    header(c, "EL ANUNCIO")
    text(c, "República Dominicana", 90, 360, 34, "semibold", GREY, anchor="lm",
         opacity=ease_out(prog(T, 10.3, 0.6)) * (1 - prog(T, 13.4, 0.4)), shadow=0.8)
    text(c, "Precios estables de los", 90, 405, 34, "semibold", WHITE, anchor="lm",
         opacity=ease_out(prog(T, 11.2, 0.6)) * (1 - prog(T, 13.4, 0.4)), shadow=0.8)
    text(c, "principales combustibles", 90, 450, 34, "semibold", WHITE, anchor="lm",
         opacity=ease_out(prog(T, 12.4, 0.6)) * (1 - prog(T, 13.4, 0.4)), shadow=0.8)

    # tarjeta de fecha
    p = ease_back(prog(T, 13.75, 0.55))
    if p > 0:
        card = layer()
        d = ImageDraw.Draw(card)
        cx, cy, cw, ch = 540, 690, 760, 290
        rrect(d, (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2), 26,
              fill=(8, 24, 56, 228), outline=(255, 255, 255, 40), width=2)
        rrect(d, (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy - ch / 2 + 62), 26, fill=rgba(RED, 1))
        d.rectangle([cx - cw / 2, cy - ch / 2 + 36, cx + cw / 2, cy - ch / 2 + 62], fill=rgba(RED, 1))
        text(card, "CONGELAMIENTO HASTA EL", cx, cy - ch / 2 + 32, 27, "bold", WHITE, tracking=3,
             shadow=0)
        # el número del día aparece cuando se pronuncia "7"
        pd = ease_out(prog(T, 14.25, 0.4))
        text(card, "7", cx - 210, cy + 40, 170, "black", WHITE, opacity=pd, scale=0.8 + 0.2 * pd,
             shadow=0.4)
        pm = ease_out(prog(T, 14.7, 0.4))
        text(card, "ENERO", cx + 70, cy + 4, 84, "black", WHITE, opacity=pm, shadow=0.4)
        py = ease_out(prog(T, 15.25, 0.45))
        text(card, "2027", cx + 70, cy + 86, 84, "black", RED, opacity=py, shadow=0.4)
        dy = max(0, int((1 - p) * 50))
        c.alpha_composite(with_opacity(card.crop((0, 0, W, H - dy)), clamp(prog(T, 13.75, 0.3))), (0, dy))

    # condición: tope semanal
    p = ease_out(prog(T, 16.6, 0.6))
    if p > 0:
        y = 1085 + (1 - p) * 60
        cl = layer()
        d = ImageDraw.Draw(cl)
        rrect(d, (130, y - 125, 950, y + 165), 26, fill=(12, 14, 20, 225), outline=rgba(GOLD, 0.85),
              width=3)
        text(cl, "CONDICIÓN", 540, y - 85, 28, "bold", GOLD, tracking=6, shadow=0)
        text(cl, "TOPE DEL SUBSIDIO", 540, y - 24, 46, "bold", WHITE, shadow=0)
        # contador sincronizado con "mil quinientos millones"
        pc = ease_out(prog(T, 18.45, 0.9))
        val = 1500 * pc
        text(cl, f"RD${val:,.0f} MILLONES", 540, y + 54, 66, "black", WHITE,
             opacity=prog(T, 18.4, 0.2), shadow=0)
        text(cl, "SEMANALES", 540, y + 118, 40, "black", RED, opacity=ease_out(prog(T, 20.1, 0.35)),
             tracking=4, shadow=0)
        c.alpha_composite(with_opacity(cl, p))
    return c


def s3_cifras(T):
    c = bg_gradient("graphite").copy()
    c.alpha_composite(grid_layer())
    header(c, "LOS NÚMEROS")
    p = ease_out(prog(T, 21.1, 0.6))
    text(c, "Subsidio semanal a los combustibles", 90, 330, 36, "bold", WHITE, anchor="lm",
         opacity=p, shadow=0.5)
    text(c, "Millones de pesos dominicanos (RD$)", 90, 378, 28, "medium", GREY, anchor="lm",
         opacity=p, shadow=0.5)

    base_y, top_y = 1130, 560                 # 1,500 -> 570 px de altura
    full_h = base_y - top_y
    h_asig = full_h * (796.4 / 1500.0)        # proporción exacta: 53.09 %
    d = ImageDraw.Draw(c)
    # eje
    d.line([(110, base_y), (970, base_y)], fill=(255, 255, 255, 90), width=2)
    bars = [
        (180, 470, full_h, 21.3, 0.9, RED, "TOPE SEMANAL", "RD$1,500 M", 1500.0, "{:,.0f}"),
        (610, 900, h_asig, 25.05, 1.2, WHITE, "SEMANA 14-20 NOV.", "RD$796.4 M", 796.4, "{:,.1f}"),
    ]
    for x0, x1, hh, t0, dur, col, lab, _, v, fmt in bars:
        pb = ease_out(prog(T, t0, dur))
        if pb <= 0:
            continue
        h_now = hh * pb
        if col == WHITE:
            fill = (236, 240, 246, 255)
        else:
            fill = rgba(RED, 1)
        rrect(d, (x0, base_y - h_now, x1, base_y), 14, fill=fill)
        d.rectangle([x0, base_y - min(h_now, 16), x1, base_y], fill=fill)
        num = fmt.format(v * pb)
        text(c, "RD$" + num, (x0 + x1) / 2, base_y - h_now - 82, 54, "black", col if col != WHITE else WHITE,
             shadow=0.5)
        text(c, "MILLONES", (x0 + x1) / 2, base_y - h_now - 36, 26, "bold", GREY, tracking=3, shadow=0.5)
        text(c, lab, (x0 + x1) / 2, base_y + 40, 25, "bold", GREY, tracking=1, opacity=pb, shadow=0.5)
    # línea punteada del tope
    pl = prog(T, 22.2, 0.6)
    if pl > 0:
        x_end = 180 + (960 - 180) * ease_out(pl)
        x = 180
        while x < x_end:
            d.line([(x, top_y), (min(x + 16, x_end), top_y)], fill=rgba(RED, 0.75), width=3)
            x += 28
    # porcentaje (cálculo propio: 796.4 / 1,500 = 53.1 %)
    pp = ease_out(prog(T, 26.6, 0.5))
    if pp > 0:
        yb = base_y - h_asig
        cy_ = base_y - h_asig / 2
        text(c, "53.1 %", 755, cy_ - 20, 50, "black", NAVY, opacity=pp, shadow=0)
        text(c, "DEL TOPE", 755, cy_ + 26, 24, "bold", NAVY, opacity=pp, tracking=3, shadow=0)
    fuente_line(c, "Fuente: Presidencia de la República / MICM. Porcentaje: cálculo de Capital Curioso.",
                y=1236, op=prog(T, 21.4, 0.6))
    return c


def sq_pregunta(T):
    c = bg_gradient().copy()
    k = (T - 28.2) / 2.0
    photo_panel(c, "01_signo_interrogacion.jpg", 300, 1330, k, zoom=(1.0, 1.07), dim=0.15,
                focus=(0.5, 0.45))
    header(c, "LA EXPLICACIÓN")
    p = ease_out(prog(T, 28.45, 0.45))
    text(c, "¿QUÉ SIGNIFICA", 540, 1080 + (1 - p) * 30, 88, "black", WHITE, opacity=p, shadow=0.8)
    text(c, "ESTO?", 540, 1180 + (1 - p) * 30, 88, "black", RED, opacity=p, shadow=0.8)
    return c


def arrow(d, x0, y0, x1, y1, col, w=5, head=18):
    d.line([(x0, y0), (x1, y1)], fill=col, width=w)
    ang = math.atan2(y1 - y0, x1 - x0)
    pts = [(x1, y1),
           (x1 - head * math.cos(ang - 0.45), y1 - head * math.sin(ang - 0.45)),
           (x1 - head * math.cos(ang + 0.45), y1 - head * math.sin(ang + 0.45))]
    d.polygon(pts, fill=col)


def s4_mecanismo(T):
    c = bg_gradient("graphite").copy()
    c.alpha_composite(grid_layer())
    k = (T - 29.8) / 9.5
    photo_panel(c, "03_grafico_subida.jpg", 280, 820, k, zoom=(1.02, 1.12), pan=(-0.2, 0.2), dim=0.1)
    header(c, "CÓMO FUNCIONA")
    p = ease_out(prog(T, 30.5, 0.5))
    d = ImageDraw.Draw(c)
    rrect(d, (90, 700 - 34, 90 + 520 * p, 700 + 34), 8, fill=(8, 24, 56, 235))
    text(c, "MERCADO INTERNACIONAL", 112, 700, 30, "bold", WHITE, anchor="lm", opacity=p,
         tracking=2, shadow=0)
    text(c, "encarece los combustibles", 92, 770, 32, "semibold", GREY, anchor="lm",
         opacity=ease_out(prog(T, 31.5, 0.5)), shadow=0.8)

    # barra del costo del combustible (esquema, sin montos)
    x0, y0, y1 = 110, 925, 1065
    w_base, w_full = 470, 860                       # longitud antes / después del encarecimiento
    pg = ease_in_out(prog(T, 31.6, 1.1))
    pa = ease_out(prog(T, 30.4, 0.5))
    wcur = (w_base * pa) + (w_full - w_base) * pg
    text(c, "COSTO DEL COMBUSTIBLE", x0, 885, 26, "bold", GREY, anchor="lm", opacity=pa,
         tracking=3, shadow=0.5)
    if wcur > 2:
        # parte que paga el consumidor (fija)
        rrect(d, (x0, y0, x0 + min(wcur, w_base), y1), 12, fill=(236, 240, 246, 255))
        if wcur > w_base:
            sub = prog(T, 33.4, 0.6)                 # "el Gobierno puede asumir parte del costo"
            col = tuple(int(GREY_DARK[i] * (1 - sub) + RED[i] * sub) for i in range(3))
            rrect(d, (x0 + w_base - 12, y0, x0 + wcur, y1), 12, fill=col + (255,))
            d.rectangle([x0 + w_base - 2, y0, x0 + w_base + 2, y1], fill=(16, 18, 24, 255))
            ps = ease_out(prog(T, 33.6, 0.5))
            text(c, "SUBSIDIO", x0 + w_base + (w_full - w_base) / 2, (y0 + y1) / 2, 40, "black",
                 WHITE, opacity=ps, shadow=0.3)
            text(c, "lo asume el Estado", x0 + w_base + (w_full - w_base) / 2, y1 + 40, 28,
                 "semibold", RED, opacity=ps, shadow=0.5)
    pc = ease_out(prog(T, 35.9, 0.5))                # "en lugar de trasladarlo ... a los consumidores"
    text(c, "PRECIO AL", x0 + w_base / 2, (y0 + y1) / 2 - 21, 33, "black", NAVY, opacity=pc, shadow=0)
    text(c, "CONSUMIDOR", x0 + w_base / 2, (y0 + y1) / 2 + 21, 33, "black", NAVY, opacity=pc, shadow=0)
    text(c, "se mantiene estable", x0 + w_base / 2, y1 + 40, 28, "semibold", WHITE, opacity=pc,
         shadow=0.5)
    fuente_line(c, "Esquema ilustrativo: no representa montos reales.", y=1185,
                op=prog(T, 31.0, 0.6))
    return c


def building(d, cx, cy, s, col):
    # icono simple de edificio público
    d.polygon([(cx - 70 * s, cy - 40 * s), (cx, cy - 80 * s), (cx + 70 * s, cy - 40 * s)], fill=col)
    for i in range(4):
        x = cx - 52 * s + i * 34.7 * s
        d.rectangle([x - 7 * s, cy - 32 * s, x + 7 * s, cy + 36 * s], fill=col)
    d.rectangle([cx - 76 * s, cy + 40 * s, cx + 76 * s, cy + 52 * s], fill=col)


def s5a_costo(T):
    c = bg_gradient().copy()
    k = (T - 38.8) / 9.2
    photo_panel(c, "02_camion_cisterna.jpg", 290, 860, k, zoom=(1.04, 1.14), pan=(0.3, -0.2),
                dim=0.12, focus=(0.55, 0.5))
    header(c, "EL COSTO")
    p = ease_out(prog(T, 39.3, 0.5))
    text(c, "PRECIO CONGELADO", 90, 780 + (1 - p) * 30, 40, "bold", GREY, anchor="lm", opacity=p,
         tracking=2, shadow=0.8)
    p2 = ease_out(prog(T, 41.1, 0.5))
    text(c, "EL COSTO", 90, 855 + (1 - p2) * 30, 92, "black", WHITE, anchor="lm", opacity=p2,
         shadow=0.8)
    text(c, "NO DESAPARECE", 90, 955 + (1 - p2) * 30, 92, "black", RED, anchor="lm", opacity=p2,
         shadow=0.8)
    # flujo: subsidio -> recursos públicos
    pf = ease_out(prog(T, 43.7, 0.5))
    if pf > 0:
        fl = layer()
        d = ImageDraw.Draw(fl)
        y = 1135
        rrect(d, (90, y - 58, 400, y + 58), 16, fill=rgba(RED, 1))
        text(fl, "SUBSIDIO", 245, y, 40, "black", WHITE, shadow=0)
        pa = ease_out(prog(T, 45.6, 0.5))
        if pa > 0:
            arrow(d, 420, y, 420 + 110 * pa, y, (255, 255, 255, 230), w=6, head=20)
        pr = ease_out(prog(T, 46.3, 0.5))
        if pr > 0:
            rl = layer()
            dr = ImageDraw.Draw(rl)
            rrect(dr, (560, y - 58, 990, y + 58), 16, fill=(236, 240, 246, 255))
            building(dr, 620, y + 2, 0.42, NAVY + (255,))
            text(rl, "RECURSOS", 800, y - 20, 34, "black", NAVY, shadow=0)
            text(rl, "PÚBLICOS", 800, y + 20, 34, "black", NAVY, shadow=0)
            fl.alpha_composite(with_opacity(rl, pr))
        c.alpha_composite(with_opacity(fl, pf))
    return c


def s5b_condicion(T):
    c = bg_gradient("graphite").copy()
    c.alpha_composite(grid_layer())
    header(c, "LA CONDICIÓN")
    d = ImageDraw.Draw(c)
    # paso 1: si el subsidio supera el tope
    p1 = ease_out(prog(T, 47.85, 0.5))
    y = 420
    rrect(d, (90, y - 80, 990, y + 80), 22, fill=rgba((26, 30, 40), p1), outline=rgba(GOLD, 0.9 * p1),
          width=3)
    text(c, "SI EL SUBSIDIO SEMANAL SUPERA", 540, y - 28, 34, "bold", GREY, opacity=p1, shadow=0)
    text(c, "RD$1,500 MILLONES", 540, y + 28, 56, "black", GOLD, opacity=p1, shadow=0)
    # flecha
    pa = ease_out(prog(T, 50.3, 0.4))
    if pa > 0:
        arrow(d, 540, 520, 540, 520 + 90 * pa, rgba(WHITE, 0.85), w=6, head=22)
    # paso 2
    p2 = ease_out(prog(T, 50.55, 0.5))
    y = 740
    rrect(d, (90, y - 100, 990, y + 100), 22, fill=rgba((26, 30, 40), p2), outline=rgba(WHITE, 0.3 * p2),
          width=2)
    text(c, "EL CONGELAMIENTO", 540, y - 40, 50, "black", WHITE, opacity=p2, shadow=0)
    text(c, "DEJA DE ESTAR", 540, y + 14, 42, "bold", WHITE, opacity=p2, shadow=0)
    text(c, "GARANTIZADO", 540, y + 62, 42, "bold", RED, opacity=ease_out(prog(T, 52.1, 0.4)),
         shadow=0)
    # aclaración: no implica aumento automático
    p3 = ease_back(prog(T, 53.3, 0.55))
    if p3 > 0:
        y = 1050
        cl = layer()
        dc = ImageDraw.Draw(cl)
        rrect(dc, (90, y - 95, 990, y + 95), 22, fill=(236, 240, 246, 255))
        text(cl, "NO SIGNIFICA QUE LOS PRECIOS", 540, y - 30, 34, "bold", NAVY, shadow=0)
        text(cl, "AUMENTEN AUTOMÁTICAMENTE", 540, y + 22, 40, "black", NAVY, shadow=0)
        dy = max(0, int((1 - p3) * 40))
        c.alpha_composite(with_opacity(cl.crop((0, 0, W, H - dy)), clamp(prog(T, 53.3, 0.3))), (0, dy))
    fuente_line(c, "Condición incluida en el anuncio del Gobierno (13 de noviembre de 2026).",
                y=1236, op=prog(T, 48.2, 0.6))
    return c


def s5c_sostenible(T):
    c = bg_gradient().copy()
    k = (T - 56.0) / 5.0
    photo_panel(c, "05_bomba_gasolina.jpg", 300, 1330, k, zoom=(1.2, 1.08), pan=(0.3, 0.1),
                dim=0.35, focus=(0.55, 0.5))
    header(c, "LA PREGUNTA")
    p0 = ease_out(prog(T, 56.35, 0.5))
    text(c, "LA PREGUNTA ES", 90, 470, 34, "bold", GREY, anchor="lm", opacity=p0, tracking=4,
         shadow=0.8)
    lines = [("¿QUÉ TAN", WHITE), ("SOSTENIBLE", RED), ("ES ESTA", WHITE), ("MEDIDA?", WHITE)]
    for i, (s, col) in enumerate(lines):
        p = ease_out(prog(T, 57.9 + i * 0.28, 0.5))
        text(c, s, 90, 580 + i * 112 + (1 - p) * 34, 104, "black", col, anchor="lm", opacity=p,
             shadow=0.8)
    return c


# ---------------------------------------------------------------- cierre

_cierre_frames = None


def cierre_frames():
    global _cierre_frames
    if _cierre_frames is None:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(CIERRE), "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        n = len(raw) // (W * H * 3)
        _cierre_frames = [raw[i * W * H * 3:(i + 1) * W * H * 3] for i in range(n)]
    return _cierre_frames


def s6_cierre(T):
    fr = cierre_frames()
    i = int(clamp((T - CIERRE_INICIO) * FPS, 0, len(fr) - 1))
    c = Image.frombytes("RGB", (W, H), fr[i]).convert("RGBA")
    p = ease_out(prog(T, 62.75, 0.6))
    text(c, "La historia detrás de los números.", 540, 1545 - (1 - p) * -16, 40, "semibold",
         (226, 232, 242), opacity=p, shadow=0.35)
    return c


SCENE_FUNCS = {
    "s1": s1_apertura, "s2": s2_anuncio, "s3": s3_cifras, "sq": sq_pregunta,
    "s4": s4_mecanismo, "s5a": s5a_costo, "s5b": s5b_condicion, "s5c": s5c_sostenible,
    "s6": s6_cierre,
}

# ------------------------------------------------------------- subtítulos


def draw_subs(c, T):
    for s0, s1, lines in SUBTITULOS:
        if s0 - 0.02 <= T < s1:
            p = ease_out(prog(T, s0, 0.14))
            pout = 1 - prog(T, s1 - 0.08, 0.08)
            op = p * pout
            n = len(lines)
            lh = 78
            y0 = 1392 - (n - 1) * lh / 2 + (1 - p) * 10
            for j, ln in enumerate(lines):
                place(c, text_sprite(ln, "bold", 60, WHITE, 0, 0.75, 0), 540, y0 + j * lh, "mm", op)
            return


# -------------------------------------------------------------- composición


def frame_at(tv, subs=True):
    T = tv - OFFSET
    active = [(n, a, b) for n, a, b in ESCENAS if a - XF / 2 <= T < b + XF / 2]
    out = None
    for n, a, b in active:
        img = SCENE_FUNCS[n](T)
        if out is None:
            out = img
        else:
            # transición: fundido con leve acercamiento de la escena entrante
            p = ease_in_out(clamp((T - (a - XF / 2)) / XF))
            sc = 1.035 - 0.035 * p
            if sc > 1.0005:
                img = img.resize((int(W * sc), int(H * sc)), Image.BILINEAR)
                l, tp = (img.width - W) // 2, (img.height - H) // 2
                img = img.crop((l, tp, l + W, tp + H))
            out = Image.blend(out, img, p)
    if out is None:
        out = bg_gradient().copy()
    is_cierre = T >= CIERRE_INICIO
    fade_v = 1 - prog(T, CIERRE_INICIO - XF / 2, XF)
    if fade_v > 0:
        v = vignette() if fade_v >= 0.999 else with_opacity(vignette(), fade_v)
        out.alpha_composite(v)
        brand_bug(out, fade_v * ease_out(prog(T, -0.4, 0.6)))
    if subs and SHOW_SUBS and not is_cierre:
        draw_subs(out, T)
    # fundido de entrada
    if tv < 0.35:
        out = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), out, ease_out(tv / 0.35))
    return out.convert("RGB")


def _render_bytes(i):
    return frame_at(i / FPS, SHOW_SUBS).tobytes()


def render_video(path):
    n = int(round(DURACION_VIDEO * FPS))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
           "-tune", "film", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
           "-movflags", "+faststart", path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for k, b in enumerate(pool.imap(_render_bytes, range(n), chunksize=6)):
            proc.stdin.write(b)
            if k % 150 == 0:
                print(f"  fotograma {k}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("listo:", path, n, "fotogramas")


def portada(path):
    c = bg_gradient().copy()
    photo_panel(c, "05_bomba_gasolina.jpg", 120, 1820, 0.5, zoom=(1.12, 1.12), pan=(0, 0), dim=0.42,
                focus=(0.55, 0.5), label=False)
    c.alpha_composite(vignette())
    lm = logo_mark(150)
    c.alpha_composite(lm, (540 - lm.width // 2, 330))
    text(c, "CAPITAL CURIOSO", 540, 590, 40, "black", WHITE, tracking=4, shadow=0.7)
    text(c, "¿QUIÉN PAGA", 540, 830, 128, "black", WHITE, shadow=0.85)
    text(c, "EL SUBSIDIO?", 540, 965, 128, "black", RED, shadow=0.85)
    d = ImageDraw.Draw(c)
    d.rectangle([440, 1078, 640, 1084], fill=rgba(GOLD, 1))
    text(c, "Combustibles congelados hasta el", 540, 1160, 44, "semibold", WHITE, shadow=0.8)
    text(c, "7 de enero de 2027, con un tope de", 540, 1218, 44, "semibold", WHITE, shadow=0.8)
    text(c, "RD$1,500 millones semanales", 540, 1276, 44, "bold", GOLD, shadow=0.8)
    text(c, "IMAGEN ILUSTRATIVA", 540, 1760, 20, "semibold", WHITE, opacity=0.55, tracking=3)
    c.convert("RGB").save(path)


if __name__ == "__main__":
    mode = sys.argv[1]
    if "--sin-subtitulos" in sys.argv:
        SHOW_SUBS = False
    if mode == "video":
        render_video(sys.argv[2])
    elif mode == "frame":
        frame_at(float(sys.argv[2])).save(sys.argv[3])
    elif mode == "portada":
        portada(sys.argv[2])
