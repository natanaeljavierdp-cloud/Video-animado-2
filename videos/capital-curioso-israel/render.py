"""Renderiza el video vertical 9:16 "¿SE ACABÓ EL DINERO DE EE.UU. PARA ISRAEL?"
para Capital Curioso, cuadro a cuadro con PIL, y lo une con la mezcla de audio.

Uso:
    python3 render.py                 # video completo -> salida/capital_curioso_israel.mp4
    python3 render.py --preview 12.5  # guarda un PNG del cuadro en t=12.5 s
    python3 render.py --from 40 --to 50  # renderiza solo un tramo (pruebas)
"""
import argparse
import json
import math
import os
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import timeline as TL

HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(HERE, "assets", *p)  # noqa: E731
W, H = 1080, 1920
FPS = TL.FPS

NAVY = (11, 31, 58)
NAVY2 = (18, 46, 84)
RED = (214, 40, 40)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PAPER = (232, 221, 196)
INK = (40, 34, 28)
GOLD = (232, 182, 54)


# ----------------------------------------------------------------- utilidades
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def prog(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else float(t >= a)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return 3 * x * x - 2 * x * x * x


def ease_out_expo(x):
    return 1 if x >= 1 else 1 - 2 ** (-10 * x)


def back_out(x, s=1.9):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def pop(t, t0, d=0.22):
    """Escala de 'aparición con rebote': 0 antes de t0, rebota y queda en 1."""
    if t < t0:
        return 0.0
    return back_out(prog(t, t0, t0 + d))


@lru_cache(None)
def font(name, size):
    return ImageFont.truetype(A("fonts", name + ".ttf"), size)


def fmt_int(v):
    return f"{int(v):,}".replace(",", ".")


# ------------------------------------------------------------------ imágenes
@lru_cache(None)
def photo(name, blur=0, dark=0.0):
    im = Image.open(A("img", name + ".jpg")).convert("RGB")
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    if dark:
        im = Image.blend(im, Image.new("RGB", im.size, BLACK), dark)
    return im


@lru_cache(None)
def cover_base(name, w, h, blur=0, dark=0.0, over=1.0):
    """Imagen escalada para cubrir (w,h) con margen 'over' para el Ken Burns."""
    im = photo(name, blur, dark)
    s = max(w / im.width, h / im.height) * over
    return im.resize((max(w, round(im.width * s)), max(h, round(im.height * s))), Image.LANCZOS)


def kb(name, lt, dur, size=(W, H), z0=1.0, z1=1.12, fx=0.5, fy=0.5, px=0.0, py=0.0,
       blur=0, dark=0.0):
    """Ken Burns: zoom lento de z0 a z1 centrado en (fx,fy) con paneo (px,py)."""
    w, h = size
    base = cover_base(name, w, h, blur, dark)
    p = ease_in_out(clamp(lt / max(dur, 1e-6)))
    z = z0 + (z1 - z0) * p
    # ventana en coordenadas de base (base ya cubre w,h a zoom 1)
    scale = min(base.width / w, base.height / h)
    cw, ch = w * scale / z, h * scale / z
    cx = fx * base.width + px * p * cw * 0.15
    cy = fy * base.height + py * p * ch * 0.15
    x0 = clamp(cx - cw / 2, 0, base.width - cw)
    y0 = clamp(cy - ch / 2, 0, base.height - ch)
    return base.resize((w, h), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")


def paste(dst, src, x, y, alpha=1.0):
    """alpha_composite con recorte y opacidad."""
    x, y = int(round(x)), int(round(y))
    if alpha <= 0.003:
        return
    if alpha < 0.999:
        a = src.getchannel("A").point(lambda v: int(v * alpha))
        src = src.copy()
        src.putalpha(a)
    sx0, sy0 = max(0, -x), max(0, -y)
    sx1, sy1 = min(src.width, dst.width - x), min(src.height, dst.height - y)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    if (sx0, sy0, sx1, sy1) != (0, 0, src.width, src.height):
        src = src.crop((sx0, sy0, sx1, sy1))
    dst.alpha_composite(src, dest=(x + sx0, y + sy0))


def put(dst, layer, cx, cy, scale=1.0, alpha=1.0, angle=0.0):
    """Pega una capa centrada en (cx,cy) con escala, opacidad y rotación."""
    if scale <= 0.01 or alpha <= 0.003:
        return
    if angle:
        layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    if abs(scale - 1) > 0.004:
        layer = layer.resize((max(1, round(layer.width * scale)), max(1, round(layer.height * scale))),
                             Image.BILINEAR)
    paste(dst, layer, cx - layer.width / 2, cy - layer.height / 2, alpha)


@lru_cache(None)
def txt(text, fname, size, fill=WHITE, stroke=0, stroke_fill=BLACK, shadow=0):
    f = font(fname, size)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    pad = stroke + shadow + 6
    w, h = r - l + pad * 2, b - t + pad * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l + shadow * 0.6, pad - t + shadow), text, font=f,
                                fill=(0, 0, 0, 170), stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        sh = sh.filter(ImageFilter.GaussianBlur(shadow * 0.7))
        im.alpha_composite(sh)
    d.text((pad - l, pad - t), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def text_w(text, fname, size):
    f = font(fname, size)
    return f.getlength(text)


def words_line(dst, t, words, fname, size, cy, cx=W / 2, stroke=0, shadow=8, gap=None,
               popd=0.2, stroke_fill=BLACK):
    """Línea de palabras (texto, color, tiempo) que aparecen una a una con rebote."""
    gap = gap if gap is not None else size * 0.30 + 8
    widths = [text_w(w, fname, size) for w, _, _ in words]
    total = sum(widths) + gap * (len(words) - 1)
    x = cx - total / 2
    for (w, col, t0), ww in zip(words, widths):
        s = pop(t, t0, popd)
        if s > 0:
            layer = txt(w, fname, size, col, stroke, stroke_fill, shadow)
            put(dst, layer, x + ww / 2, cy, scale=0.6 + 0.4 * s if s < 1 else s,
                alpha=clamp((t - t0) / 0.08))
        x += ww + gap


def rrect(size, radius, fill, outline=None, width=0):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=fill,
                                         outline=outline, width=width)
    return im


def rounded_photo(img, radius, border=0, border_col=WHITE):
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    if border:
        ImageDraw.Draw(out).rounded_rectangle((0, 0, w - 1, h - 1), radius, outline=border_col,
                                              width=border)
    return out


def circle_photo(name, d, fx=0.5, fy=0.35, zoom=1.6, border=8):
    base = cover_base(name, d, d)
    s = min(base.width, base.height) / zoom
    cx, cy = fx * base.width, fy * base.height
    x0 = clamp(cx - s / 2, 0, base.width - s)
    y0 = clamp(cy - s / 2, 0, base.height - s)
    im = base.resize((d, d), Image.LANCZOS, box=(x0, y0, x0 + s, y0 + s))
    mask = Image.new("L", (d, d), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d - 1, d - 1), fill=255)
    out = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    ImageDraw.Draw(out).ellipse((0, 0, d - 1, d - 1), outline=WHITE, width=border)
    return out


circle_photo = lru_cache(None)(circle_photo)


# --------------------------------------------------------------- texturas
@lru_cache(None)
def grain_layers():
    rng = np.random.default_rng(3)
    out = []
    for _ in range(6):
        n = rng.normal(0, 1, (H // 2, W // 2))
        a = np.clip(np.abs(n) * 9, 0, 22).astype(np.uint8)
        v = np.where(n > 0, 255, 0).astype(np.uint8)
        im = Image.fromarray(np.dstack([v, v, v, a]), "RGBA").resize((W, H), Image.NEAREST)
        out.append(im)
    return out


@lru_cache(None)
def vignette():
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H / 2) / (H * 0.6)) ** 2)
    a = (np.clip(d - 0.55, 0, 1) ** 1.4 * 330).clip(0, 210).astype(np.uint8)
    z = np.zeros_like(a)
    return Image.fromarray(np.dstack([z, z, z, a]), "RGBA")


@lru_cache(None)
def grad(top_a, bot_a, y0=0, y1=H):
    """Degradado negro vertical (para legibilidad del texto)."""
    col = np.zeros((H,), np.float32)
    ys = np.arange(H)
    p = np.clip((ys - y0) / max(1, y1 - y0), 0, 1)
    col = top_a + (bot_a - top_a) * p
    a = np.repeat(col[:, None], W, axis=1).astype(np.uint8)
    z = np.zeros_like(a)
    return Image.fromarray(np.dstack([z, z, z, a]), "RGBA")


@lru_cache(None)
def navy_board():
    """Fondo azul marino de 'pizarra de investigación' con cuadrícula tenue."""
    rng = np.random.default_rng(11)
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.42) / H) ** 2)
    base = np.array(NAVY2, np.float32)[None, None, :] * (1 - d[..., None] * 1.1) + \
        np.array(NAVY, np.float32)[None, None, :] * d[..., None] * 1.1
    base += rng.normal(0, 3.2, (H, W, 1))
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(g)
    for gx in range(0, W, 90):
        dg.line((gx, 0, gx, H), fill=(255, 255, 255, 10), width=1)
    for gy in range(0, H, 90):
        dg.line((0, gy, W, gy), fill=(255, 255, 255, 10), width=1)
    im.alpha_composite(g)
    return im


@lru_cache(None)
def paper(w, h, seed=5):
    """Textura de papel envejecido."""
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (h // 4 + 1, w // 4 + 1))
    n = np.array(Image.fromarray(((n * 20) + 128).clip(0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC),
                 np.float32) - 128
    fine = rng.normal(0, 5, (h, w))
    y, x = np.mgrid[0:h, 0:w]
    edge = np.minimum(np.minimum(x, w - x), np.minimum(y, h - y)) / (0.12 * min(w, h))
    edge = np.clip(edge, 0, 1)
    base = np.array(PAPER, np.float32)[None, None, :]
    img = base + (n + fine)[..., None] * np.array([1.0, 0.95, 0.85]) - (1 - edge[..., None]) * 38
    return Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")


# ------------------------------------------------------------- marca: lupa
@lru_cache(None)
def lupa(d):
    """Lupa de Capital Curioso: aro blanco, mango rojo y '?' rojo."""
    S = 4
    D = d * S
    im = Image.new("RGBA", (int(D * 1.5), int(D * 1.5)), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    r = D / 2
    cx = cy = r + D * 0.06
    ring = D * 0.11
    # mango
    a = math.radians(45)
    x0, y0 = cx + (r - ring * 0.2) * math.cos(a), cy + (r - ring * 0.2) * math.sin(a)
    x1, y1 = cx + (r + D * 0.36) * math.cos(a), cy + (r + D * 0.36) * math.sin(a)
    hw = D * 0.095
    dr.line((x0, y0, x1, y1), fill=RED + (255,), width=int(hw * 2))
    dr.ellipse((x1 - hw, y1 - hw, x1 + hw, y1 + hw), fill=RED + (255,))
    # lente
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=NAVY + (255,))
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), outline=WHITE + (255,), width=int(ring))
    # brillo
    dr.arc((cx - r * 0.72, cy - r * 0.72, cx + r * 0.72, cy + r * 0.72), 205, 245,
           fill=(150, 175, 215, 255), width=int(D * 0.035))
    # signo ?
    f = font("Poppins900", int(D * 0.6))
    dr.text((cx, cy + D * 0.02), "?", font=f, fill=RED + (255,), anchor="mm")
    return im.resize((im.width // S, im.height // S), Image.LANCZOS)


# --------------------------------------------------------- componentes UI
@lru_cache(None)
def lower_third(name, role):
    f1, f2 = font("Poppins800", 54), font("Poppins600", 36)
    w = int(max(f1.getlength(name), f2.getlength(role)) + 90)
    h = 156
    im = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((10, 14, w + 10, h + 14), fill=(0, 0, 0, 150))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, h * 0.58), fill=NAVY + (245,))
    d.rectangle((0, h * 0.58, w, h), fill=WHITE + (245,))
    d.rectangle((0, 0, 16, h), fill=RED + (255,))
    d.text((44, h * 0.29), name, font=f1, fill=WHITE, anchor="lm")
    d.text((44, h * 0.79), role, font=f2, fill=NAVY, anchor="lm")
    return im


def draw_lower_third(dst, t, t0, name, role, y=1150, t_out=None):
    if t < t0:
        return
    lt = lower_third(name, role)
    p = ease_out(prog(t, t0, t0 + 0.35))
    x = -lt.width + (60 + lt.width) * p
    a = 1.0
    if t_out is not None and t > t_out:
        a = 1 - prog(t, t_out, t_out + 0.2)
    # máscara de barrido
    paste(dst, lt, x, y, a)


@lru_cache(None)
def quote_card_bg():
    bg = navy_board().copy()
    d = ImageDraw.Draw(bg)
    d.rectangle((70, 470, 1010, 1290), outline=(255, 255, 255, 40), width=3)
    return bg


def quote_card(dst, t, t0, lines, author, avatar=None, header=None, header_t=None, size=92):
    """Tarjeta de cita: fondo azul marino, comillas rojas, texto palabra por palabra."""
    paste(dst, quote_card_bg(), 0, 0)
    qs = pop(t, t0 - 0.1, 0.3)
    put(dst, txt("“", "Anton", 330, RED), 220, 500, scale=qs)
    if header:
        words_line(dst, t, [(header, RED, header_t)], "Poppins800", 54, 420)
    y = 820 - (len(lines) - 1) * size * 0.62
    for line in lines:
        words_line(dst, t, line, "Poppins800", size, y, shadow=6)
        y += size * 1.24
    put(dst, txt("”", "Anton", 330, RED), 900, y + size * 1.05, scale=pop(t, t0 + 0.2, 0.3))
    last = max(w[2] for line in lines for w in line)
    ta = last + 0.25
    if t >= ta:
        a = prog(t, ta, ta + 0.3)
        y_auth = 1190
        if avatar:
            put(dst, circle_photo(*avatar), 250, y_auth, alpha=a, scale=0.8 + 0.2 * a)
            put(dst, txt("— " + author, "Poppins700", 44, WHITE), 600, y_auth, alpha=a)
        else:
            put(dst, txt("— " + author, "Poppins700", 44, WHITE), W / 2, y_auth, alpha=a)


@lru_cache(None)
def calendar_card(month, day, year, w=400, h=450):
    im = Image.new("RGBA", (w + 30, h + 30), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((15, 22, w + 15, h + 22), 26, fill=(0, 0, 0, 160))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((15, 15, w + 15, h + 15), 26, fill=WHITE)
    d.rounded_rectangle((15, 15, w + 15, 15 + h * 0.26), 26, fill=RED)
    d.rectangle((15, 15 + h * 0.15, w + 15, 15 + h * 0.26), fill=RED)
    for rx in (w * 0.28, w * 0.72):
        d.rounded_rectangle((15 + rx - 9, 0, 15 + rx + 9, 42), 9, fill=NAVY)
    d.text((15 + w / 2, 15 + h * 0.13), f"{month} {year}", font=font("Poppins800", int(h * 0.11)),
           fill=WHITE, anchor="mm")
    d.text((15 + w / 2, 15 + h * 0.62), str(day), font=font("Anton", int(h * 0.5)), fill=NAVY,
           anchor="mm")
    return im


def red_circle(dst, cx, cy, rx, ry, p, width=12):
    """Círculo rojo dibujado 'a mano' que se completa según p (0..1)."""
    if p <= 0:
        return
    layer = Image.new("RGBA", (int(rx * 2 + 60), int(ry * 2 + 60)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ox, oy = layer.width / 2, layer.height / 2
    n = 60
    end = -110 + 380 * p
    pts = []
    for i in range(n + 1):
        a = math.radians(-110 + (end + 110) * i / n)
        wob = 1 + 0.04 * math.sin(a * 3)
        pts.append((ox + rx * wob * math.cos(a), oy + ry * wob * math.sin(a)))
    d.line(pts, fill=RED + (255,), width=width, joint="curve")
    paste(dst, layer, cx - ox, cy - oy)


@lru_cache(None)
def ballot_icon(s=220):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((s * 0.08, s * 0.45, s * 0.92, s * 0.95), 18, fill=WHITE)
    d.rectangle((s * 0.08, s * 0.45, s * 0.92, s * 0.58), fill=NAVY)
    d.rounded_rectangle((s * 0.3, s * 0.49, s * 0.7, s * 0.54), 6, fill=BLACK)
    d.polygon([(s * 0.36, s * 0.52), (s * 0.40, s * 0.08), (s * 0.70, s * 0.12), (s * 0.66, s * 0.52)],
              fill=WHITE, outline=NAVY)
    d.line([(s * 0.46, s * 0.27), (s * 0.52, s * 0.34), (s * 0.62, s * 0.18)], fill=RED, width=10,
           joint="curve")
    return im


def stamp(dst, t, t0, text, cx, cy, angle=-12, size=80, col=RED):
    if t < t0:
        return
    p = prog(t, t0, t0 + 0.16)
    s = 2.2 - 1.2 * ease_out(p)
    lay = stamp_layer(text, size, col)
    put(dst, lay, cx, cy, scale=s, alpha=0.25 + 0.7 * p, angle=angle)


@lru_cache(None)
def stamp_layer(text, size, col):
    f = font("Anton", size)
    tw = f.getlength(text)
    w, h = int(tw + size * 0.9), int(size * 1.7)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 6, w - 6, h - 6), 14, outline=col + (255,), width=9)
    d.rounded_rectangle((20, 20, w - 20, h - 20), 8, outline=col + (255,), width=3)
    d.text((w / 2, h / 2), text, font=f, fill=col + (255,), anchor="mm")
    # textura de tinta gastada
    rng = np.random.default_rng(len(text))
    a = np.array(im.getchannel("A"), np.float32)
    holes = rng.random(a.shape) < 0.13
    a[holes] *= 0.25
    im.putalpha(Image.fromarray(a.astype(np.uint8)))
    return im


def polaroid(name, w, h, caption=None, fx=0.5, fy=0.4):
    key = (name, w, h, caption, fx, fy)
    if key in _POLA:
        return _POLA[key]
    pad, bottom = 22, 80 if caption else 22
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((20, 26, w + 20, h + 26), fill=(0, 0, 0, 170))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(im).rectangle((20, 20, w + 20, h + 20), fill=(246, 244, 238))
    ph = kb(name, 0, 1, size=(w - pad * 2, h - pad - bottom), z0=1.0, z1=1.0, fx=fx, fy=fy)
    im.alpha_composite(ph, dest=(20 + pad, 20 + pad))
    if caption:
        ImageDraw.Draw(im).text((20 + w / 2, 20 + h - bottom / 2), caption, font=font("Typewriter", 38),
                                fill=INK, anchor="mm")
    # chincheta
    d = ImageDraw.Draw(im)
    d.ellipse((20 + w / 2 - 16, 6, 20 + w / 2 + 16, 38), fill=RED, outline=(120, 10, 10), width=3)
    _POLA[key] = im
    return im


_POLA = {}


def red_string(dst, p0, p1, p, width=6):
    """Hilo rojo de conexión (pizarra de investigación) que se dibuja según p."""
    if p <= 0:
        return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0 = p0
    x1, y1 = p1
    xe, ye = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p
    sag = 40 * p
    pts = []
    for i in range(21):
        u = i / 20
        pts.append((x0 + (xe - x0) * u, y0 + (ye - y0) * u + math.sin(math.pi * u) * sag))
    d.line(pts, fill=(150, 10, 10, 200), width=width + 4, joint="curve")
    d.line(pts, fill=RED + (255,), width=width, joint="curve")
    d.ellipse((x0 - 10, y0 - 10, x0 + 10, y0 + 10), fill=RED)
    if p >= 1:
        d.ellipse((x1 - 10, y1 - 10, x1 + 10, y1 + 10), fill=RED)
    dst.alpha_composite(layer)


def headline(dst, t, lines, y, size=110, fname="Anton", stroke=0, shadow=10):
    """lines: lista de listas de (palabra, color, tiempo)."""
    for i, line in enumerate(lines):
        words_line(dst, t, line, fname, size, y + i * size * 1.08, stroke=stroke, shadow=shadow)


def chip(text, size=44, fill=RED, col=WHITE, fname="Poppins800", padx=30, pady=14):
    key = (text, size, fill, col, fname)
    if key not in _CHIP:
        f = font(fname, size)
        w = int(f.getlength(text) + padx * 2)
        h = int(size * 1.25 + pady * 2)
        im = rrect((w, h), 12, fill)
        ImageDraw.Draw(im).text((w / 2, h / 2), text, font=f, fill=col, anchor="mm")
        _CHIP[key] = im
    return _CHIP[key]


_CHIP = {}


def clock(dst, cx, cy, r, angle_min, angle_hour, face=WHITE, hand=NAVY, accent=RED):
    S = 2
    im = Image.new("RGBA", (int(r * 2 * S + 20), int(r * 2 * S + 20)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = im.width / 2
    R = r * S
    d.ellipse((o - R, o - R, o + R, o + R), fill=face, outline=accent, width=int(14 * S))
    for k in range(12):
        a = math.radians(k * 30)
        r0 = R * (0.78 if k % 3 == 0 else 0.84)
        d.line((o + r0 * math.sin(a), o - r0 * math.cos(a), o + R * 0.9 * math.sin(a),
                o - R * 0.9 * math.cos(a)), fill=hand, width=int((8 if k % 3 == 0 else 4) * S))
    for ang, ln, wd, c in ((angle_hour, 0.5, 14, hand), (angle_min, 0.75, 8, accent)):
        a = math.radians(ang)
        d.line((o, o, o + R * ln * math.sin(a), o - R * ln * math.cos(a)), fill=c, width=int(wd * S))
    d.ellipse((o - 14 * S, o - 14 * S, o + 14 * S, o + 14 * S), fill=accent)
    im = im.resize((im.width // S, im.height // S), Image.LANCZOS)
    paste(dst, im, cx - im.width / 2, cy - im.height / 2)


# ------------------------------------------------------------------ mapa
@lru_cache(None)
def world_polys():
    import shapefile  # pyshp
    sf = shapefile.Reader(A("geo", "naturalearth_lowres.shp"), encoding="latin-1")
    fields = [f[0] for f in sf.fields[1:]]
    polys = []
    for rec, shp in zip(sf.records(), sf.shapes()):
        name = rec[fields.index("name")]
        parts = list(shp.parts) + [len(shp.points)]
        for i in range(len(parts) - 1):
            pts = shp.points[parts[i]:parts[i + 1]]
            polys.append((name, np.array(pts)))
    return polys


def draw_map(lt, dur):
    p = ease_in_out(clamp(lt / (dur * 0.85)))
    # cámara: (lon, lat, grados visibles a lo ancho)
    c0, c1 = np.array([25.0, 22.0]), np.array([35.0, 31.4])
    w0, w1 = 150.0, 7.5
    span = w0 * (w1 / w0) ** p
    c = c0 + (c1 - c0) * (1 - (1 - p) ** 2)
    S = 1  # supersampling via dibujo a 2x
    SS = 2
    im = Image.new("RGBA", (W * SS, H * SS), NAVY + (255,))
    d = ImageDraw.Draw(im)
    k = math.cos(math.radians(31))
    sx = W * SS / (span * k)
    sy = W * SS / span

    def proj(arr):
        x = (arr[:, 0] - c[0]) * k * sx + W * SS / 2
        y = -(arr[:, 1] - c[1]) * sy + H * SS * 0.42
        return list(zip(x.tolist(), y.tolist()))

    for name, arr in world_polys():
        lon0, lon1 = arr[:, 0].min(), arr[:, 0].max()
        if lon1 < c[0] - span or lon0 > c[0] + span:
            continue
        isr = name in ("Israel",)
        if isr:
            continue
        d.polygon(proj(arr), fill=(36, 70, 112), outline=(90, 125, 170), width=max(1, int(2 * SS)))
    pulse = 0.5 + 0.5 * math.sin(lt * 9)
    for name, arr in world_polys():
        if name == "Israel":
            col = (int(214 + 30 * pulse), 40, 40)
            d.polygon(proj(arr), fill=col, outline=WHITE, width=3 * SS)
    out = im.resize((W, H), Image.BILINEAR)
    return out, (c, span, k)


def map_to_screen(lon, lat, cam):
    c, span, k = cam
    sx = W / (span * k)
    sy = W / span
    return (lon - c[0]) * k * sx + W / 2, -(lat - c[1]) * sy + H * 0.42


# ----------------------------------------------------------- subtítulos
def load_chunks():
    data = json.load(open(A("audio", "transcripcion.json"), encoding="utf-8"))
    words = []
    for s in data:
        for w in s["words"]:
            tx = w["w"].strip()
            for a, b in TL.FIXES.items():
                tx = tx.replace(a, b)
            words.append((tx, w["s"], w["e"]))
    chunks, cur = [], []
    for i, (tx, s, e) in enumerate(words):
        cur.append((tx, s, e))
        nxt_gap = words[i + 1][1] - e if i + 1 < len(words) else 9
        chars = sum(len(x[0]) + 1 for x in cur)
        if tx[-1] in ".,?!" or len(cur) >= 4 or chars > 20 or nxt_gap > 0.35:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for i, ch in enumerate(chunks):
        start = ch[0][1]
        end = chunks[i + 1][0][1] if i + 1 < len(chunks) else ch[-1][2] + 0.4
        end = min(end, ch[-1][2] + 0.6)
        out.append((start, end, ch))
    return out


CHUNKS = None


def is_kw(word):
    w = word.lower().strip("¿?¡!.,")
    return w in TL.KEYWORDS


def draw_subs(dst, t):
    for a, b in TL.NO_SUBS:
        if a <= t < b:
            return
    for start, end, ch in CHUNKS:
        if start - 0.05 <= t < end:
            size = 74
            fname = "Poppins900"
            items = [(w.upper().rstrip(","), s) for w, s, _ in ch]
            widths = [text_w(w, fname, size) for w, _ in items]
            gap = 36
            total = sum(widths) + gap * (len(items) - 1)
            if total > W - 80:
                size = int(size * (W - 80) / total)
                widths = [text_w(w, fname, size) for w, _ in items]
                total = sum(widths) + gap * (len(items) - 1)
            x = W / 2 - total / 2
            cy = 1530
            for (w, s), ww in zip(items, widths):
                if t >= s - 0.04:
                    col = RED if is_kw(w) else WHITE
                    active = s - 0.04 <= t < s + 0.25
                    sc = 1.0 + 0.12 * (1 - prog(t, s - 0.04, s + 0.2)) if active else 1.0
                    lay = txt(w, fname, size, col, 9, BLACK, 10)
                    put(dst, lay, x + ww / 2, cy, scale=sc)
                x += ww + gap
            return


# ----------------------------------------------------------------- escenas
def sc_gancho_contador(t, lt, dur):
    f = Image.new("RGBA", (W, H), (4, 6, 12, 255))
    glow = glow_layer()
    paste(f, glow, 0, 0, alpha=0.5 + 0.5 * prog(t, 0, 2.6))
    words_line(f, t, [("AYUDA DE EE.UU. A ISRAEL", (200, 205, 220), 0.25)], "Typewriter", 46, 640)
    p = ease_out_expo(prog(t, 0.12, 2.62))
    val = 4_000_000_000 * p
    s = "$" + fmt_int(val)
    size = 138
    lay = txt(s, "Anton", size, WHITE, 0, BLACK, 12)
    sc = 1.0 + 0.08 * (1 - prog(t, 2.62, 2.9)) * (t >= 2.62)
    put(f, lay, W / 2, 860, scale=sc)
    if t >= 2.62:
        put(f, chip("CADA AÑO", 64), W / 2, 1050, scale=pop(t, 2.62))
    # barra de progreso fina bajo el contador
    d = ImageDraw.Draw(f)
    d.rectangle((140, 960, 140 + 800 * p, 966), fill=RED)
    return f


@lru_cache(None)
def glow_layer():
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / 600) ** 2 + ((y - 880) / 520) ** 2)
    a = (np.clip(1 - d, 0, 1) ** 2 * 120).astype(np.uint8)
    r = np.full_like(a, RED[0])
    g = np.full_like(a, 20)
    b = np.full_like(a, 30)
    return Image.fromarray(np.dstack([r, g, b, a]), "RGBA")


def sc_gancho_banderas(t, lt, dur):
    f = navy_board().copy()
    cut = 6.80
    sep = 0 if t < cut else ease_out(prog(t, cut, cut + 0.35)) * 70
    cw, ch = 860, 560
    p_in1 = ease_out(prog(t, 3.55, 3.85))
    p_in2 = ease_out(prog(t, 3.70, 4.00))
    for i, (name, yc, pin, fx) in enumerate((("bandera_eeuu", 520, p_in1, 0.5),
                                             ("bandera_israel", 1190, p_in2, 0.5))):
        img = kb(name, lt, dur, size=(cw, ch), z0=1.05, z1=1.2, fx=fx, fy=0.5,
                 px=(1 if i == 0 else -1))
        if t >= cut:
            g = prog(t, cut, cut + 0.5) * 0.65
            img = Image.blend(img, img.convert("L").convert("RGBA"), g)
        card = rounded_photo(img, 26, 8, WHITE)
        dy = (-sep if i == 0 else sep)
        x = (W - cw) / 2 + (1 - pin) * (-W if i == 0 else W)
        paste(f, card, x, yc - ch / 2 + dy)
    # línea roja que las une
    y_top, y_bot = 520 + ch / 2, 1190 - ch / 2
    lp = ease_out(prog(t, 4.0, 4.5))
    d = ImageDraw.Draw(f)
    if t < cut:
        ye = y_top + (y_bot - y_top) * lp
        if lp > 0:
            d.line((W / 2, y_top, W / 2, ye), fill=RED, width=16)
            d.ellipse((W / 2 - 22, y_top - 22, W / 2 + 22, y_top + 22), fill=RED)
            if lp >= 1:
                d.ellipse((W / 2 - 22, y_bot - 22, W / 2 + 22, y_bot + 22), fill=RED)
                pulse = 0.5 + 0.5 * math.sin(t * 8)
                d.ellipse((W / 2 - 34 - 8 * pulse, (y_top + y_bot) / 2 - 34 - 8 * pulse,
                           W / 2 + 34 + 8 * pulse, (y_top + y_bot) / 2 + 34 + 8 * pulse),
                          outline=RED, width=5)
        words_line(f, t, [("Y TRUMP", WHITE, 5.14), ("ACABA DE DECIR…", WHITE, 5.52)],
                   "Poppins800", 58, 205, shadow=8)
    else:
        # línea cortada: dos mitades que se retraen + chispas
        r = ease_out(prog(t, cut, cut + 0.4))
        mid = (y_top + y_bot) / 2
        d.line((W / 2, y_top - sep, W / 2, mid - 30 - 120 * r - sep), fill=RED, width=16)
        d.line((W / 2, mid + 30 + 120 * r + sep, W / 2, y_bot + sep), fill=RED, width=16)
        rng = np.random.default_rng(int(t * 30))
        if t < cut + 0.35:
            for _ in range(18):
                a = rng.random() * 2 * math.pi
                L = 30 + 160 * r * rng.random()
                d.line((W / 2, mid, W / 2 + L * math.cos(a), mid + L * math.sin(a)), fill=(255, 200, 80),
                       width=4)
        # tijera
        if t < cut + 0.5:
            put(f, scissors(), W / 2 + 160 - 160 * prog(t, cut - 0.1, cut + 0.08), mid,
                alpha=1 - prog(t, cut + 0.3, cut + 0.5))
        s = pop(t, 6.92, 0.25)
        put(f, txt("SE ACABÓ", "Anton", 230, RED, 6, WHITE, 18), W / 2, mid, scale=s * (1 + 0.6 * (1 - s)))
    return f


@lru_cache(None)
def scissors():
    s = 220
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line((s * 0.1, s * 0.3, s * 0.95, s * 0.62), fill=WHITE, width=16)
    d.line((s * 0.1, s * 0.7, s * 0.95, s * 0.38), fill=WHITE, width=16)
    for cy in (0.22, 0.78):
        d.ellipse((s * 0.62, s * cy - 34, s * 0.62 + 68, s * cy + 34), outline=WHITE, width=12)
    d.ellipse((s * 0.5 - 9, s * 0.5 - 9, s * 0.5 + 9, s * 0.5 + 9), fill=RED)
    return im.rotate(180)


def sc_trump(t, lt, dur):
    f = kb("trump", lt, dur + 0.5, z0=1.0, z1=1.1, fx=0.5, fy=0.42)
    f.alpha_composite(grad(0, 200, 900, H))
    draw_lower_third(f, t, 8.0, "DONALD TRUMP", "Presidente de EE.UU.", y=1160)
    s = pop(t, 8.14, 0.25)
    if s > 0:
        put(f, calendar_card("NOV", 3, 2026, 360, 400), 250, 420, scale=s, angle=4)
        red_circle(f, 250, 460, 140, 120, ease_out(prog(t, 8.46, 9.0)))
    return f


def sc_elecciones(t, lt, dur):
    f = kb("voto", lt, dur, z0=1.08, z1=1.22, fx=0.5, fy=0.55, py=-1)
    f.alpha_composite(grad(210, 0, 0, 900))
    f.alpha_composite(grad(0, 170, 1100, H))
    put(f, ballot_icon(200), W / 2, 230, scale=pop(t, 9.2, 0.3))
    headline(f, t, [[("EL", WHITE, 9.2), ("MISMO", WHITE, 9.28), ("DÍA", WHITE, 9.6)],
                    [("DE", WHITE, 9.9), ("LAS", WHITE, 10.02)],
                    [("ELECCIONES", RED, 10.16)]], 430, size=120, stroke=0)
    put(f, calendar_card("NOV", 3, 2026, 230, 260), 900, 1140, scale=pop(t, 10.6, 0.25), angle=-6)
    return f


def sc_fox(t, lt, dur):
    f = kb("estudio_tv", lt, dur, z0=1.0, z1=1.15, fx=0.5, fy=0.5, px=1)
    f.alpha_composite(grad(200, 30, 0, 800))
    f.alpha_composite(grad(0, 170, 1150, H))
    headline(f, t, [[("TRUMP", WHITE, 12.0), ("LO", WHITE, 12.26)], [("ANUNCIÓ", WHITE, 12.46), ("EN", WHITE, 12.86)]],
             300, size=110)
    s = pop(t, 12.96, 0.25)
    if s:
        put(f, chip("FOX NEWS", 92, RED), W / 2, 590, scale=s)
        put(f, chip("ENTREVISTA · 3 NOV 2026", 38, WHITE, NAVY), W / 2, 720, scale=pop(t, 13.2, 0.25))
    put(f, circle_photo("trump", 260, 0.5, 0.38, 1.9), W / 2, 1050, scale=pop(t, 12.0, 0.3))
    return f


def sc_fin_de_anio(t, lt, dur):
    f = kb("dolares", lt, dur, z0=1.05, z1=1.2, fx=0.5, fy=0.45, dark=0.55)
    headline(f, t, [[("LA", WHITE, 14.02), ("AYUDA", WHITE, 14.18)], [("TERMINA", RED, 14.46)],
                    [("A", WHITE, 15.1), ("FINALES", WHITE, 15.24)], [("DE", WHITE, 15.72), ("2026", RED, 15.82)]],
             330, size=125)
    # tira de meses
    months = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
    p = ease_in_out(prog(t, 14.5, 16.0))
    cur = p * 11
    bw, gap = 76, 8
    x0 = (W - (12 * bw + 11 * gap)) / 2
    y = 1110
    d = ImageDraw.Draw(f)
    for i, m in enumerate(months):
        a = pop(t, 14.2 + i * 0.03, 0.2)
        if a <= 0:
            continue
        x = x0 + i * (bw + gap)
        on = i <= cur
        fill = RED if on else (255, 255, 255, 40)
        d.rounded_rectangle((x, y, x + bw, y + 92), 10, fill=fill, outline=(255, 255, 255, 120), width=2)
        d.text((x + bw / 2, y + 46), m, font=font("Poppins800", 25), fill=WHITE, anchor="mm")
    if p >= 1:
        red_circle(f, x0 + 11 * (bw + gap) + bw / 2, y + 46, 70, 76, ease_out(prog(t, 16.0, 16.5)), 9)
    return f


def sc_cita_no_la_necesitan(t, lt, dur):
    f = Image.new("RGBA", (W, H))
    quote_card(f, t, 16.85, [[("No", WHITE, 17.82), ("la", WHITE, 18.10), ("necesitan.", RED, 18.22)]],
               "Donald Trump, Fox News", avatar=("trump", 130, 0.5, 0.38, 1.9),
               header="¿SU RAZÓN?", header_t=16.8, size=104)
    return f


def sc_detalle(t, lt, dur):
    f = kb("expedientes", lt, dur, z0=1.1, z1=1.3, fx=0.5, fy=0.5, blur=6, dark=0.6)
    p = ease_in_out(prog(t, 19.2, 20.95))
    s = 0.5 + 1.3 * p
    put(f, lupa(520), W / 2 + 120 - 120 * p, 900 + 60 - 60 * p, scale=s, alpha=0.9)
    f.alpha_composite(grad(120, 120))
    headline(f, t, [[("PERO", WHITE, 19.28), ("HAY", WHITE, 19.88)], [("UN", RED, 20.10), ("DETALLE…", RED, 20.20)]],
             780, size=150, stroke=0, shadow=16)
    return f


def sc_expediente(t, lt, dur):
    f = kb("expedientes", lt, dur, z0=1.25, z1=1.35, fx=0.5, fy=0.5, blur=10, dark=0.55)
    # carpeta que se abre
    pw, ph = 900, 1060
    px_, py_ = (W - pw) / 2, 300
    page = paper(pw, ph)
    pin = ease_out(prog(t, 20.95, 21.3))
    yoff = (1 - pin) * 700
    pg = page.copy()
    d = ImageDraw.Draw(pg)
    d.text((pw / 2, 120), "MEMORANDO DE ENTENDIMIENTO", font=font("Typewriter", 44), fill=INK, anchor="mm")
    d.text((pw / 2, 215), "EE.UU. – ISRAEL", font=font("Anton", 96), fill=NAVY, anchor="mm")
    d.line((80, 290, pw - 80, 290), fill=INK, width=3)
    rng = np.random.default_rng(2)
    yy = 340
    for i in range(9):
        L = rng.integers(380, pw - 160)
        if i in (2, 5):
            d.rectangle((80, yy, 80 + L, yy + 26), fill=(20, 20, 20))
        else:
            d.text((80, yy), "▬" * 0, font=font("Typewriter", 26), fill=INK)
            d.line((80, yy + 14, 80 + L, yy + 14), fill=(90, 80, 70), width=6)
        yy += 52
    paste(f, pg, px_, py_ + yoff)
    # año 2016 resaltado
    words_line(f, t, [("2016", RED, 21.2)], "Anton", 120, py_ + yoff + 860, cx=W / 2 - 200)
    if t >= 23.76:
        red_circle(f, W / 2 - 200, py_ + 860, 150, 90, ease_out(prog(t, 23.76, 24.2)), 10)
    # tapa de la carpeta (se abre hacia arriba)
    op = ease_in_out(prog(t, 21.2, 21.7))
    if op < 1:
        cover_h = int(ph * (1 - op))
        if cover_h > 4:
            cover = Image.new("RGBA", (pw, cover_h), (196, 160, 98, 255))
            ImageDraw.Draw(cover).text((pw / 2, cover_h / 2), "CONFIDENCIAL", font=font("Anton", 90),
                                       fill=(120, 90, 50), anchor="mm")
            paste(f, cover, px_, py_ + yoff + ph - cover_h)
    stamp(f, t, 21.75, "CLASIFICADO", 690, py_ + yoff + 640, angle=10, size=70)
    # polaroids
    s1 = pop(t, 22.5, 0.3)
    if s1:
        put(f, polaroid("firma_documento", 440, 330), 300, 1180, scale=s1, angle=7)
    s2 = pop(t, 23.0, 0.3)
    if s2:
        put(f, polaroid("obama", 400, 500, "BARACK OBAMA", 0.5, 0.33), 760, 1030, scale=s2, angle=-5)
        red_string(f, (W / 2 - 60, py_ + 230), (760, 800), ease_out(prog(t, 23.0, 23.4)))
    stamp(f, t, 23.30, "FIRMADO POR OBAMA", W / 2, 1360, angle=-8, size=78)
    return f


def sc_infografia_38(t, lt, dur):
    f = navy_board().copy()
    words_line(f, t, [("ACUERDO 2016", (200, 210, 230), 24.95)], "Typewriter", 48, 330)
    p = ease_out_expo(prog(t, 25.08, 26.12))
    put(f, txt("$" + fmt_int(38000 * p), "Anton", 210, WHITE, 0, BLACK, 14), W / 2, 560,
        scale=1 + 0.08 * (1 - prog(t, 26.12, 26.4)) * (t >= 26.12))
    if t >= 26.12:
        put(f, txt("MILLONES", "Anton", 110, WHITE, 0, BLACK, 10), W / 2, 740, scale=pop(t, 26.12))
    if t >= 27.12:
        put(f, chip("EN 10 AÑOS", 76, RED), W / 2, 890, scale=pop(t, 27.30))
    # barra -> 10 bloques
    bx, by, bw, bh = 90, 1040, 900, 90
    fill = ease_out(prog(t, 25.1, 26.4))
    sp = ease_in_out(prog(t, 27.5, 28.2))
    d = ImageDraw.Draw(f)
    if sp <= 0:
        d.rounded_rectangle((bx, by, bx + bw, by + bh), 14, outline=(255, 255, 255, 90), width=3)
        if fill > 0:
            d.rounded_rectangle((bx, by, bx + bw * fill, by + bh), 14, fill=RED)
    else:
        for i in range(10):
            sx, sy = bx + i * bw / 10, by
            col_, row = i % 5, i // 5
            gx, gy = 70 + col_ * 192, 1000 + row * 140
            x = sx + (gx - sx) * sp
            y = sy + (gy - sy) * sp
            w_ = bw / 10 + (172 - bw / 10) * sp
            d.rounded_rectangle((x, y, x + w_, y + 110 * sp + bh * (1 - sp) - 6), 12, fill=RED,
                                outline=WHITE, width=2)
            if sp > 0.7:
                d.text((x + w_ / 2, y + 52), "$3.800 M", font=font("Poppins800", 31), fill=WHITE, anchor="mm")
        if sp >= 1:
            words_line(f, t, [("$3.800 MILLONES POR AÑO", WHITE, 28.2)], "Poppins800", 44, 1320)
    return f


def sc_linea_tiempo(t, lt, dur):
    f = navy_board().copy()
    headline(f, t, [[("NO", WHITE, 28.66), ("VENCE", WHITE, 28.8)], [("HASTA", WHITE, 29.12), ("2028", RED, 29.64)]],
             330, size=130)
    y = 980
    x0, x1 = 100, 980
    lp = ease_out(prog(t, 28.4, 29.0))
    d = ImageDraw.Draw(f)
    d.line((x0, y, x0 + (x1 - x0) * lp, y), fill=WHITE, width=8)
    nodes = [(150, "2016", "FIRMA", 28.45, WHITE), (390, "2019", "INICIA", 28.7, WHITE),
             (690, "2026", "HOY", 28.95, RED), (930, "2028", "VENCE", 29.64, RED)]
    for x, yr, lab, t0, col in nodes:
        s = pop(t, t0, 0.25)
        if s <= 0:
            continue
        r = 22 * s
        if yr == "2026":
            bl = 0.5 + 0.5 * math.sin(t * 12)
            d.ellipse((x - r - 16 * bl, y - r - 16 * bl, x + r + 16 * bl, y + r + 16 * bl), fill=(214, 40, 40, 90))
        d.ellipse((x - r, y - r, x + r, y + r), fill=col, outline=WHITE, width=4)
        put(f, txt(yr, "Anton", 74, col if col == RED else WHITE), x, y - 90, scale=s)
        put(f, txt(lab, "Poppins800", 36, WHITE), x, y + 80, scale=s)
    if t >= 29.64:
        red_circle(f, 930, y - 60, 110, 150, ease_out(prog(t, 29.7, 30.2)), 9)
    return f


def sc_dudas(t, lt, dur):
    f = kb("interrogantes", lt, dur, z0=1.05, z1=1.18, fx=0.5, fy=0.4, dark=0.62)
    headline(f, t, [[("LE", WHITE, 31.08), ("PREGUNTARON…", WHITE, 31.26)]], 260, size=96)
    cards = [("¿AYUDA MILITAR?", "caza_f16", 32.38, 560), ("¿DINERO EN EFECTIVO?", "dolares", 33.48, 950)]
    active = 0 if t < 33.48 else 1
    for i, (label, img, t0, cy) in enumerate(cards):
        s = pop(t, t0, 0.28)
        if s <= 0:
            continue
        on = (i == active) and t < 34.74
        a = 1.0 if (on or t >= 34.74) else 0.45
        put(f, dudas_card(label, img), W / 2, cy, scale=s * (1.04 if on else 0.96), alpha=a)
    if t >= 34.74:
        q = pop(t, 34.74, 0.3)
        wob = math.sin(t * 6) * 6
        put(f, txt("?", "Anton", 300, RED, 8, WHITE, 16), W / 2, 1290, scale=q, angle=wob)
    return f


@lru_cache(None)
def dudas_card(label, img):
    w, h = 900, 330
    card = rrect((w, h), 26, NAVY + (235,), WHITE, 4)
    ph = kb(img, 0, 1, size=(300, 270), z0=1, z1=1, fx=0.5, fy=0.5)
    card.alpha_composite(rounded_photo(ph, 18), dest=(30, 30))
    d = ImageDraw.Draw(card)
    words = label.split(" ")
    if len(words) > 2:
        lines = [" ".join(words[:2]), " ".join(words[2:])]
    else:
        lines = [label]
    yy = h / 2 - (len(lines) - 1) * 40
    for ln in lines:
        d.text((360 + (w - 380) / 2, yy), ln, font=font("Anton", 74), fill=WHITE, anchor="mm")
        yy += 82
    return card


def sc_cita_definirlo(t, lt, dur):
    f = Image.new("RGBA", (W, H))
    quote_card(f, t, 35.7, [[("Como", WHITE, 35.74), ("usted", WHITE, 35.94)],
                            [("quiera", WHITE, 36.20), ("definirlo.", RED, 36.44)]],
               "Donald Trump", avatar=("trump", 130, 0.5, 0.38, 1.9), size=100)
    return f


def sc_warrick(t, lt, dur):
    f = kb("capitolio", lt, dur, z0=1.0, z1=1.12, fx=0.5, fy=0.55, dark=0.35)
    f.alpha_composite(grad(170, 40, 0, 900))
    draw_lower_third(f, t, 37.72, "THOMAS WARRICK", "Atlantic Council", y=1170)
    # cita
    headline(f, t, [[("“PROBABLEMENTE", WHITE, 39.6)], [("NO", WHITE, 39.8), ("ESTE", WHITE, 40.4), ("AÑO…", WHITE, 40.62)],
                    [("SINO", RED, 41.2), ("EN", RED, 41.4), ("2027”", RED, 41.9)]], 250, size=96)
    # calendario 2026 -> 2027
    s = pop(t, 38.3, 0.3)
    if s:
        flip = prog(t, 41.4, 41.9)
        yr = "2026" if flip < 0.5 else "2027"
        sy = abs(1 - 2 * flip) if 0 < flip < 1 else 1
        card = year_card(yr)
        card = card.resize((card.width, max(2, int(card.height * sy))), Image.BILINEAR)
        put(f, card, W / 2, 850, scale=s)
        if yr == "2026" and t > 40.62:
            d = ImageDraw.Draw(f)
            p = ease_out(prog(t, 40.62, 41.0))
            d.line((W / 2 - 170, 900, W / 2 - 170 + 340 * p, 830), fill=RED, width=14)
    return f


@lru_cache(None)
def year_card(yr):
    w, h = 420, 300
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 24, fill=WHITE)
    d.rounded_rectangle((0, 0, w - 1, 80), 24, fill=RED if yr == "2027" else NAVY)
    d.rectangle((0, 50, w - 1, 80), fill=RED if yr == "2027" else NAVY)
    d.text((w / 2, 42), "CALENDARIO", font=font("Poppins800", 34), fill=WHITE, anchor="mm")
    d.text((w / 2, 190), yr, font=font("Anton", 150), fill=RED if yr == "2027" else NAVY, anchor="mm")
    return im


def sc_mapa(t, lt, dur):
    f, cam = draw_map(lt, dur)
    f.alpha_composite(navy_grid_overlay())
    words_line(f, t, [("LO", WHITE, 43.36), ("MÁS", WHITE, 43.48), ("CURIOSO…", RED, 43.64)], "Anton", 110, 260,
               shadow=10)
    p = prog(t, 43.3 + dur * 0.6, 43.3 + dur * 0.85)
    if p > 0:
        x, y = map_to_screen(35.0, 31.3, cam)
        put(f, chip("ISRAEL", 64, RED), x + 230, y - 40, scale=pop(t, 43.3 + dur * 0.6))
    return f


@lru_cache(None)
def navy_grid_overlay():
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    for gx in range(0, W, 120):
        d.line((gx, 0, gx, H), fill=(255, 255, 255, 14), width=1)
    for gy in range(0, H, 120):
        d.line((0, gy, W, gy), fill=(255, 255, 255, 14), width=1)
    return g


def sc_netanyahu(t, lt, dur):
    f = kb("netanyahu", lt, dur, z0=1.0, z1=1.12, fx=0.5, fy=0.38)
    f.alpha_composite(grad(200, 0, 0, 700))
    f.alpha_composite(grad(0, 190, 1050, H))
    draw_lower_third(f, t, 45.0, "BENJAMÍN NETANYAHU", "Primer ministro de Israel", y=1170)
    headline(f, t, [[("QUERÍA", WHITE, 46.68), ("REDUCIR", WHITE, 46.96)], [("LA", WHITE, 47.4), ("AYUDA", WHITE, 47.58), ("A", WHITE, 47.88)]],
             170, size=100)
    s = pop(t, 48.22, 0.3)
    if s:
        put(f, chip("CERO", 96, RED), W / 2, 450, scale=s * (1 + 0.5 * (1 - s)))
    return f


def sc_relojes(t, lt, dur):
    f = Image.new("RGBA", (W, H), NAVY + (255,))
    f.alpha_composite(navy_grid_overlay())
    lt2 = t - 48.95
    # izquierda: plan de Netanyahu (lento)
    a_l = pop(t, 49.0, 0.3)
    if a_l:
        put(f, txt("PLAN DE", "Poppins800", 44, WHITE), 270, 470, alpha=a_l)
        put(f, txt("NETANYAHU", "Poppins800", 44, WHITE), 270, 525, alpha=a_l)
        clock(f, 270, 860, 200 * a_l, lt2 * 25, lt2 * 2)
        put(f, txt("10 AÑOS", "Anton", 120, WHITE, 0, BLACK, 10), 270, 1200, scale=pop(t, 49.66))
    # derecha: anuncio de Trump (rápido, rojo)
    a_r = pop(t, 50.58, 0.3)
    if a_r:
        d = ImageDraw.Draw(f)
        d.rectangle((W / 2, 0, W, H), fill=(150, 22, 26, int(255 * min(1, a_r))))
        put(f, txt("ANUNCIO", "Poppins800", 44, WHITE), 810, 470, alpha=a_r)
        put(f, txt("DE TRUMP", "Poppins800", 44, WHITE), 810, 525, alpha=a_r)
        clock(f, 810, 860, 200 * min(1, a_r), lt2 * 900, lt2 * 75, face=WHITE, hand=(120, 10, 10), accent=RED)
        put(f, txt("2 MESES", "Anton", 120, WHITE, 0, BLACK, 10), 810, 1200, scale=pop(t, 50.94))
    d = ImageDraw.Draw(f)
    d.line((W / 2, 380, W / 2, 1320), fill=WHITE, width=6)
    if a_r:
        put(f, chip("VS", 54, WHITE, RED), W / 2, 860, scale=a_r)
    return f


def sc_israel(t, lt, dur):
    f = kb("tel_aviv", lt, dur, z0=1.0, z1=1.14, fx=0.55, fy=0.5, py=-1)
    f.alpha_composite(grad(190, 0, 0, 700))
    headline(f, t, [[("EN", WHITE, 51.96), ("ISRAEL…", RED, 52.14)]], 260, size=130)
    put(f, chip("LA OPOSICIÓN REACCIONA", 46, NAVY), W / 2, 420, scale=pop(t, 52.86))
    return f


def sc_golan(t, lt, dur):
    f = kb("lider_opositor", lt, dur, z0=1.0, z1=1.12, fx=0.5, fy=0.45)
    f.alpha_composite(grad(0, 200, 1000, H))
    draw_lower_third(f, t, 53.86, "YAIR GOLAN", "Líder opositor israelí", y=1170)
    return f


def sc_cita_golan(t, lt, dur):
    f = Image.new("RGBA", (W, H))
    quote_card(f, t, 55.4, [[("Golpe", RED, 55.48), ("severo", RED, 55.72)], [("a", WHITE, 56.36), ("la", WHITE, 56.56), ("seguridad", WHITE, 56.68)],
                            [("de", WHITE, 57.06), ("Israel.", WHITE, 57.2)]],
               "Yair Golan", avatar=("lider_opositor", 130, 0.5, 0.42, 1.7), size=96)
    return f


def sc_fundacion(t, lt, dur):
    f = kb("jerusalen", lt, dur, z0=1.0, z1=1.15, fx=0.5, fy=0.55, px=1)
    f.alpha_composite(grad(190, 0, 0, 750))
    headline(f, t, [[("DESDE", WHITE, 57.56), ("SU", WHITE, 58.18)], [("FUNDACIÓN", RED, 58.42)]], 260, size=130)
    put(f, chip("1948", 70, WHITE, NAVY), W / 2, 560, scale=pop(t, 58.7))
    return f


def sc_contador_300(t, lt, dur):
    f = kb("avion_carga", lt, dur, z0=1.0, z1=1.12, fx=0.45, fy=0.5, dark=0.62)
    words_line(f, t, [("ISRAEL", RED, 59.36), ("HA", WHITE, 59.6), ("RECIBIDO", WHITE, 59.76)], "Poppins800", 64, 520)
    p = ease_out_expo(prog(t, 59.9, 61.54))
    put(f, txt("+$" + fmt_int(300000 * p), "Anton", 190, WHITE, 0, BLACK, 14), W / 2, 780,
        scale=1 + 0.1 * (1 - prog(t, 61.54, 61.9)) * (t >= 61.54))
    if t >= 61.54:
        put(f, txt("MILLONES", "Anton", 120, RED, 0, BLACK, 10), W / 2, 960, scale=pop(t, 61.54))
        put(f, chip("DE EE.UU.", 56, WHITE, NAVY), W / 2, 1100, scale=pop(t, 62.68))
    return f


def sc_ranking(t, lt, dur):
    f = navy_board().copy()
    headline(f, t, [[("MÁS", WHITE, 63.78), ("QUE", WHITE, 63.98)], [("CUALQUIER", RED, 64.16)], [("OTRO", WHITE, 64.64), ("PAÍS", WHITE, 64.86)]],
             250, size=110)
    rows = [("1º", "ISRAEL", 1.0, RED, 63.75), ("2º", "OTRO PAÍS", 0.55, (120, 135, 160), 63.9),
            ("3º", "OTRO PAÍS", 0.38, (90, 105, 130), 64.0)]
    y = 760
    d = ImageDraw.Draw(f)
    for rank, name, val, col, t0 in rows:
        p = ease_out(prog(t, t0, t0 + 0.5))
        if p <= 0:
            y += 190
            continue
        d.text((80, y + 60), rank, font=font("Anton", 90), fill=WHITE, anchor="lm")
        L = 720 * val * p
        d.rounded_rectangle((210, y, 210 + L, y + 120), 16, fill=col)
        if p > 0.5:
            d.text((236, y + 60), name, font=font("Poppins800", 46), fill=WHITE, anchor="lm")
        y += 190
    # medalla
    s = pop(t, 64.3, 0.3)
    if s:
        put(f, medal(), 900, 760 + 60, scale=s, angle=math.sin(t * 4) * 6)
    return f


@lru_cache(None)
def medal():
    s = 210
    im = Image.new("RGBA", (s, int(s * 1.35)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(s * 0.25, 0), (s * 0.45, 0), (s * 0.62, s * 0.5), (s * 0.42, s * 0.5)], fill=RED)
    d.polygon([(s * 0.75, 0), (s * 0.55, 0), (s * 0.38, s * 0.5), (s * 0.58, s * 0.5)], fill=NAVY2)
    cy = s * 0.82
    d.ellipse((s * 0.1, cy - s * 0.4, s * 0.9, cy + s * 0.4), fill=GOLD, outline=(160, 110, 20), width=8)
    d.text((s / 2, cy), "1", font=font("Anton", 120), fill=(120, 80, 10), anchor="mm")
    return im


def sc_pagando(t, lt, dur):
    f = kb("caza_f16", lt, dur, z0=1.0, z1=1.15, fx=0.5, fy=0.56, py=-1)
    f.alpha_composite(grad(200, 0, 0, 760))
    headline(f, t, [[("PODRÁ", WHITE, 65.94), ("SEGUIR", WHITE, 66.54)], [("COMPRANDO", WHITE, 66.7)],
                    [("ARMAS", RED, 67.24), ("DE", WHITE, 67.46), ("EE.UU.", WHITE, 67.6)]], 230, size=104)
    if t >= 68.76:
        lt3 = t - 68.76
        ang = 22 * math.exp(-lt3 * 3.0) * math.cos(lt3 * 9)
        s = pop(t, 68.76, 0.3)
        put(f, price_tag(), 640, 1050, scale=s, angle=ang - 8)
    return f


@lru_cache(None)
def price_tag():
    w, h = 560, 300
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    pts = [(30, 30 + h / 2), (30 + 110, 30), (30 + w, 30), (30 + w, 30 + h), (30 + 110, 30 + h)]
    ImageDraw.Draw(sh).polygon([(x + 8, y + 12) for x, y in pts], fill=(0, 0, 0, 160))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(im)
    d.polygon(pts, fill=(250, 246, 236), outline=RED)
    d.line(pts + [pts[0]], fill=RED, width=8)
    d.ellipse((30 + 70, 30 + h / 2 - 22, 30 + 114, 30 + h / 2 + 22), fill=NAVY)
    d.text((30 + 120 + (w - 120) / 2, 30 + h * 0.3), "AHORA:", font=font("Poppins800", 54), fill=NAVY, anchor="mm")
    d.text((30 + 120 + (w - 120) / 2, 30 + h * 0.66), "PAGANDO", font=font("Anton", 110), fill=RED, anchor="mm")
    return im


def sc_encuesta(t, lt, dur):
    f = Image.new("RGBA", (W, H), NAVY + (255,))
    f.alpha_composite(navy_grid_overlay())
    put(f, lupa(170), W / 2 + 30, 300, scale=pop(t, 70.0, 0.35), angle=math.sin(t * 2) * 4)
    words_line(f, t, [("¿QUÉ", WHITE, 70.14), ("CREES", WHITE, 70.28), ("TÚ?", RED, 70.38)], "Anton", 140, 560)
    opts = [("FIN REAL DE LA AYUDA", RED, 71.04, 800), ("ANUNCIO QUE NUNCA", (40, 110, 230), 72.66, 1010)]
    for i, (label, dot, t0, y) in enumerate(opts):
        s = pop(t, t0, 0.3)
        if s:
            hl = 0.5 + 0.5 * math.sin((t - t0) * 5 + i * math.pi)
            put(f, poll_option(label, dot, "SE CUMPLIRÁ" if i == 1 else None), W / 2, y, scale=s * (1 + 0.015 * hl))
    if t >= 74.86:
        a = prog(t, 74.86, 75.1)
        words_line(f, t, [("TE", WHITE, 74.86), ("LEO", WHITE, 74.98), ("EN", WHITE, 75.22), ("LOS", WHITE, 75.26)],
                   "Poppins900", 64, 1250)
        words_line(f, t, [("COMENTARIOS", RED, 75.34)], "Poppins900", 76, 1340)
        bounce = abs(math.sin((t - 74.86) * 6)) * 40
        put(f, arrow_down(), W / 2, 1530 + bounce, alpha=a)
    # fuentes
    if t >= 72.0:
        put(f, txt("Fuentes: Fox News · AFP/CNN · AP · Atlantic Council · CBS", "Poppins600", 28,
                   (190, 200, 220)), W / 2, 1800, alpha=prog(t, 72.0, 72.5))
    return f


@lru_cache(None)
def poll_option(label, dot, line2):
    w, h = 900, 170
    im = rrect((w, h), 85, (255, 255, 255, 25), WHITE, 5)
    d = ImageDraw.Draw(im)
    d.ellipse((40, h / 2 - 38, 116, h / 2 + 38), fill=dot, outline=WHITE, width=4)
    if line2:
        d.text((150, h / 2 - 30), label, font=font("Poppins800", 50), fill=WHITE, anchor="lm")
        d.text((150, h / 2 + 32), line2, font=font("Poppins800", 50), fill=WHITE, anchor="lm")
    else:
        d.text((150, h / 2), label, font=font("Poppins800", 50), fill=WHITE, anchor="lm")
    return im


@lru_cache(None)
def arrow_down():
    im = Image.new("RGBA", (160, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((58, 0, 102, 110), fill=RED)
    d.polygon([(10, 100), (150, 100), (80, 195)], fill=RED)
    return im


CIERRE_DIR = os.path.join(HERE, "salida", "cierre_frames")


def extract_cierre():
    os.makedirs(CIERRE_DIR, exist_ok=True)
    if not os.listdir(CIERRE_DIR):
        subprocess.run(["ffmpeg", "-v", "error", "-i", A("cierre.mp4"), os.path.join(CIERRE_DIR, "%04d.png")],
                       check=True)


def sc_cierre(t, lt, dur):
    n = len(os.listdir(CIERRE_DIR))
    i = min(n, int(lt * 30) + 1)
    f = Image.open(os.path.join(CIERRE_DIR, f"{i:04d}.png")).convert("RGBA")
    s = pop(t, TL.CIERRE_START + 1.9, 0.3)
    if s:
        put(f, chip("SÍGUENOS", 58, RED), W / 2, 1600, scale=s)
    return f


SCENE_FN = {name: globals()["sc_" + name] for _, _, name in TL.SCENES}


# ------------------------------------------------------------- composición
def hit_amount(t):
    v = 0.0
    for ht, s in TL.HITS:
        if ht <= t < ht + 0.35:
            v = max(v, s * (1 - (t - ht) / 0.35) ** 2)
    return v


def render_frame(i):
    t = i / FPS
    for a, b, name in TL.SCENES:
        if a <= t < b:
            break
    lt, dur = t - a, b - a
    f = SCENE_FN[name](t, lt, dur)
    if name != "cierre":
        # golpe de zoom al entrar en cada escena
        if lt < 0.2 and a > 0:
            z = 1 + 0.06 * (1 - ease_out(lt / 0.2))
            cw, ch = W / z, H / z
            f = f.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
        draw_subs(f, t)
        # marca de agua
        if name != "encuesta":
            put(f, brand_tag(), 190, 110, alpha=0.92)
        f.alpha_composite(vignette())
        f.alpha_composite(grain_layers()[(i // 3) % 6])
        # transición con lupa
        for tt in TL.LUPA_TRANSITIONS:
            if tt - 0.18 <= t < tt + 0.22:
                p = (t - (tt - 0.18)) / 0.4
                fl = 1 - abs(p - 0.45) / 0.45
                if fl > 0:
                    wl = Image.new("RGBA", (W, H), (255, 255, 255, int(150 * fl)))
                    f.alpha_composite(wl)
                put(f, lupa(420), -300 + (W + 600) * p, H * 0.45 - 200 + 400 * p, angle=-20 + 40 * p)
        # golpe: sacudida + flash + aberración cromática
        h = hit_amount(t)
        if h > 0.02:
            rng = np.random.default_rng(i)
            dx, dy = (rng.random(2) - 0.5) * 2 * 22 * h
            arr = np.array(f.convert("RGB"))
            sh = int(10 * h)
            if sh:
                arr[:, :, 0] = np.roll(arr[:, :, 0], sh, axis=1)
                arr[:, :, 2] = np.roll(arr[:, :, 2], -sh, axis=1)
            f = Image.fromarray(arr).convert("RGBA")
            g = Image.new("RGBA", (W, H), NAVY + (255,))
            g.alpha_composite(f, dest=(0, 0))
            f = g.transform((W, H), Image.AFFINE, (1, 0, -dx, 0, 1, -dy), Image.BILINEAR, fillcolor=NAVY)
            if h > 0.5:
                f.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(110 * (h - 0.5) * 2))))
    # fundido de entrada
    if t < 0.15:
        f.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - t / 0.15)))))
    return f.convert("RGB").tobytes()


@lru_cache(None)
def brand_tag():
    l = lupa(64)
    tx = txt("CAPITAL CURIOSO", "Poppins800", 30, WHITE, 0, BLACK, 6)
    im = Image.new("RGBA", (l.width + tx.width + 10, max(l.height, tx.height)), (0, 0, 0, 0))
    im.alpha_composite(l, dest=(0, (im.height - l.height) // 2))
    im.alpha_composite(tx, dest=(l.width + 4, (im.height - tx.height) // 2 - 6))
    return im


def init_worker():
    global CHUNKS
    CHUNKS = load_chunks()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", type=float, nargs="*")
    ap.add_argument("--from", dest="t0", type=float, default=0)
    ap.add_argument("--to", dest="t1", type=float, default=TL.TOTAL)
    ap.add_argument("--out", default=os.path.join(HERE, "salida", "capital_curioso_israel.mp4"))
    ap.add_argument("--jobs", type=int, default=3)
    args = ap.parse_args()
    os.makedirs(os.path.join(HERE, "salida"), exist_ok=True)

    extract_cierre()
    if args.preview:
        init_worker()
        for tp in args.preview:
            raw = render_frame(int(round(tp * FPS)))
            p = os.path.join(HERE, "salida", f"preview_{tp:05.2f}.png")
            Image.frombytes("RGB", (W, H), raw).save(p)
            print(p)
        return

    mix = os.path.join(HERE, "salida", "mezcla.wav")
    print("Mezclando audio…", flush=True)
    subprocess.run([sys.executable, os.path.join(HERE, "audio.py"), A("audio", "narracion.mp3"), mix], check=True)

    i0, i1 = int(args.t0 * FPS), int(args.t1 * FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-ss", str(args.t0), "-t", str(args.t1 - args.t0), "-i", mix,
        "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-tune", "film", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-movflags", "+faststart",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", args.out,
    ], stdin=subprocess.PIPE)
    with Pool(args.jobs, initializer=init_worker, maxtasksperchild=300) as pool:
        for k, raw in enumerate(pool.imap(render_frame, range(i0, i1), chunksize=4)):
            ff.stdin.write(raw)
            if k % 150 == 0:
                print(f"  cuadro {i0 + k}/{i1}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("Listo:", args.out)


if __name__ == "__main__":
    main()
