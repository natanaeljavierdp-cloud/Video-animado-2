#!/usr/bin/env python3
"""Capital Curioso — Thanksgiving 2026 (vertical 1080x1920, 30 fps).

Genera todos los cuadros con PIL, mezcla narración + música + efectos y
exporta build/capital_curioso_thanksgiving.mp4.

Uso:  python3 render.py            (video completo)
      python3 render.py --stills   (cuadros de prueba en build/stills)
"""
import json, math, os, subprocess, sys, wave
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(HERE, "assets", *p)
BUILD = os.path.join(HERE, "build")
os.makedirs(BUILD, exist_ok=True)

W, H, FPS = 1080, 1920, 30
NARR_DUR = 64.522449            # duración exacta de la narración
CLOSE_DUR = 3.5                 # cierre animado de la marca
CLOSE_START = round(NARR_DUR * FPS) / FPS
TOTAL_FRAMES = round(NARR_DUR * FPS) + round(CLOSE_DUR * FPS)

# ---------------------------------------------------------------- marca
NAVY = (10, 40, 90)
NAVY_2 = (24, 62, 124)
RED = (254, 74, 85)
RED_D = (214, 40, 54)
GREEN = (24, 168, 92)
WHITE = (255, 255, 255)
GREY = (214, 221, 232)
GREY_T = (96, 110, 135)
CREAM = (247, 249, 252)

def font(w, s):
    return _font(w, int(s))

@lru_cache(None)
def _font(w, s):
    return ImageFont.truetype(A("fonts", f"Poppins-{w}.ttf"), s)

EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

@lru_cache(None)
def emoji(ch, size):
    f = ImageFont.truetype(EMOJI_FONT, 109)
    im = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((70, 70), ch, font=f, embedded_color=True, anchor="mm")
    im = im.crop(im.getbbox())
    r = size / max(im.size)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x

def prog(t, t0, d):
    return clamp((t - t0) / d) if d > 0 else float(t >= t0)

def ease_out(p):
    return 1 - (1 - p) ** 3

def ease_in_out(p):
    return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2

def ease_back(p, s=1.9):
    p -= 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2

def lerp(a, b, p):
    return a + (b - a) * p

def window(t, t0, t1, fin=.28, fout=.25):
    """(alpha, entrada) para un elemento visible entre t0 y t1."""
    if t < t0 or t > t1 + fout:
        return 0.0, 0.0
    pin = prog(t, t0, fin)
    pout = 1 - prog(t, t1, fout)
    return min(pin, pout) if t > t1 else pin, pin

# ---------------------------------------------------------------- dibujo
def scale_alpha(im, a):
    if a >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return im

def paste(base, sp, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    if abs(scale - 1) > 0.003:
        sp = sp.resize((max(1, int(sp.width * scale)), max(1, int(sp.height * scale))), Image.BICUBIC)
    if abs(rot) > 0.05:
        sp = sp.rotate(rot, resample=Image.BICUBIC, expand=True)
    sp = scale_alpha(sp, alpha)
    base.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)))

def pop(base, sp, cx, cy, t, t0, t1=1e9, dur=.38, rot=0.0, from_scale=0.0):
    """Aparece con rebote (easeOutBack) y se desvanece al final."""
    if t < t0 or t > t1 + .25:
        return
    p = prog(t, t0, dur)
    sc = lerp(from_scale, 1, ease_back(p))
    a = clamp(p * 2.5)
    if t > t1:
        q = prog(t, t1, .25)
        a *= 1 - q
        sc *= 1 - .15 * q
    paste(base, sp, cx, cy, sc, a, rot)

def slide(base, sp, cx, cy, t, t0, t1=1e9, dx=0, dy=120, dur=.35, out_dx=0, out_dy=-80):
    if t < t0 or t > t1 + .25:
        return
    p = ease_out(prog(t, t0, dur))
    x, y, a = cx + dx * (1 - p), cy + dy * (1 - p), p
    if t > t1:
        q = ease_in_out(prog(t, t1, .25))
        x += out_dx * q
        y += out_dy * q
        a *= 1 - q
    paste(base, sp, x, y, 1, a)

@lru_cache(None)
def shadow_card(w, h, r=44, fill=WHITE, blur=22, sh_alpha=70, border=None):
    pad = blur * 2
    im = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 12, pad + w, pad + h + 12), r, fill=sh_alpha)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    im.paste(Image.new("RGBA", im.size, (5, 20, 50, 255)), (0, 0), sh)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=fill + (255,) if len(fill) == 3 else fill,
                        outline=border, width=6 if border else 0)
    return im, pad

def card(w, h, r=44, fill=WHITE, border=None):
    im, pad = shadow_card(w, h, r, fill, border=border)
    return im.copy(), pad

def text_w(s, f):
    return f.getlength(s)

def draw_text(d, xy, s, f, fill, anchor="mm", stroke=0, sfill=None):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sfill)

def up_arrow(d, cx, cy, s, fill, down=False):
    k = -1 if down else 1
    pts = [(cx, cy - k * s * .55), (cx + s * .45, cy - k * s * .05), (cx + s * .16, cy - k * s * .05),
           (cx + s * .16, cy + k * s * .5), (cx - s * .16, cy + k * s * .5), (cx - s * .16, cy - k * s * .05),
           (cx - s * .45, cy - k * s * .05)]
    d.polygon(pts, fill=fill)

def rich_line(d, cx, cy, parts, anchor_y="mm"):
    """parts: [(texto, font, color)] centrado en cx."""
    total = sum(text_w(s, f) for s, f, c in parts)
    x = cx - total / 2
    for s, f, c in parts:
        d.text((x, cy), s, font=f, fill=c, anchor="lm")
        x += text_w(s, f)

# ---------------------------------------------------------------- fotos
IMG = {
    "cocina": "01_familia_cocina.jpg", "padrehijo": "02_padre_hijo_mesa.jpg", "mercado": "03_mercado.jpg",
    "gasolinera": "04_gasolinera.jpg", "mangueras": "05_mangueras.jpg", "cisterna": "06_camion_cisterna.jpg",
    "buffet": "07_pavo_buffet.jpg", "pavo": "08_pavo_horneado.jpg", "ilustracion": "09_ilustracion_mesa.png",
}
BRIGHT = {"gasolinera": (1.18, 1.05), "cisterna": (1.12, 1.1), "padrehijo": (1.04, 1.04),
          "mercado": (1.12, 1.08), "buffet": (1.1, 1.0), "mangueras": (1.05, 1.05)}

@lru_cache(None)
def photo(key, cover_scale=1.18):
    im = Image.open(A("img", IMG[key])).convert("RGB")
    im = ImageOps.exif_transpose(im)
    b, c = BRIGHT.get(key, (1.0, 1.0))
    if b != 1: im = ImageEnhance.Brightness(im).enhance(b)
    if c != 1: im = ImageEnhance.Color(im).enhance(c)
    r = max(W * cover_scale / im.width, H * cover_scale / im.height)
    return im.resize((int(im.width * r + .5), int(im.height * r + .5)), Image.LANCZOS)

def kenburns(key, p, z0=1.0, z1=1.12, fx0=.5, fy0=.5, fx1=.5, fy1=.5):
    """p 0..1. z = zoom relativo al encuadre 'cover'. fx/fy = centro (0..1 de la imagen)."""
    im = photo(key)
    base = min(im.width / W, im.height / H)  # cuánto cabe a zoom 1
    z = lerp(z0, z1, p)
    cw, ch = W * base / z, H * base / z
    cx = lerp(fx0, fx1, p) * im.width
    cy = lerp(fy0, fy1, p) * im.height
    x0 = clamp(cx - cw / 2, 0, im.width - cw)
    y0 = clamp(cy - ch / 2, 0, im.height - ch)
    return im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")

# Escenas de fondo: (inicio, fin, imagen, parámetros ken burns, velo blanco)
SCENES = [
    (0.00, 5.62, "cocina", dict(z0=1.0, z1=1.16, fx0=.45, fy0=.5, fx1=.42, fy1=.42), 0),
    (5.62, 22.30, "ilustracion", dict(z0=1.0, z1=1.06, fx0=.30, fy0=.5, fx1=.70, fy1=.5), 70),
    (22.30, 31.30, "buffet", dict(z0=1.0, z1=1.1, fx0=.5, fy0=.4, fx1=.5, fy1=.45), "blur"),
    (31.30, 33.62, "mangueras", dict(z0=1.04, z1=1.18, fx0=.5, fy0=.45, fx1=.45, fy1=.4), 0),
    (33.62, 39.86, "gasolinera", dict(z0=1.0, z1=1.12, fx0=.5, fy0=.55, fx1=.5, fy1=.5), 0),
    (39.86, 44.80, "cisterna", dict(z0=1.0, z1=1.05, fx0=.28, fy0=.5, fx1=.55, fy1=.5), 0),
    (44.80, 57.00, "mercado", dict(z0=1.0, z1=1.14, fx0=.5, fy0=.55, fx1=.5, fy1=.5), 0),
    (57.00, CLOSE_START, "padrehijo", dict(z0=1.0, z1=1.1, fx0=.5, fy0=.45, fx1=.55, fy1=.45), 0),
]
TRANS = .26  # transición "push" rápida

def scene_frame(i, t):
    t0, t1, key, kb, veil = SCENES[i]
    p = clamp((t - t0) / (t1 - t0 + TRANS))
    if veil == "blur":
        fr = blurred_bg(key, p, kb)
    else:
        fr = kenburns(key, p, **kb)
        if veil:
            fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, veil)))
    return fr

def blurred_bg(key, p, kb):
    fr = kenburns(key, p, **kb).resize((270, 480), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5))
    fr = fr.resize((W, H), Image.BILINEAR)
    fr.alpha_composite(Image.new("RGBA", (W, H), (240, 246, 255, 60)))
    return fr

def background(t):
    idx = 0
    for i, s in enumerate(SCENES):
        if t >= s[0]:
            idx = i
    fr = scene_frame(idx, t)
    # transición push desde la escena anterior
    if idx > 0 and t - SCENES[idx][0] < TRANS:
        q = ease_in_out((t - SCENES[idx][0]) / TRANS)
        prev = scene_frame(idx - 1, t)
        out = Image.new("RGBA", (W, H))
        off = int(W * q)
        out.paste(prev, (-off, 0))
        out.paste(fr, (W - off, 0))
        fr = out
    # degradado suave arriba para que los subtítulos respiren
    fr.alpha_composite(top_gradient())
    return fr

@lru_cache(None)
def top_gradient():
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a = np.zeros((H, W), np.uint8)
    for y in range(560):
        a[y, :] = int(105 * (1 - y / 560) ** 1.6)
    g.putalpha(Image.fromarray(a))
    g2 = Image.new("RGBA", (W, H), NAVY + (255,))
    g2.putalpha(Image.fromarray(a))
    return g2

# ---------------------------------------------------------------- subtítulos
def load_tokens():
    w = json.load(open(A("transcripcion_palabras.json")))
    # corrección: Whisper omitió "caro." (verificado con una segunda pasada del tramo 22–26.5 s)
    toks = []
    i = 0
    merges = {34: (38, "$58.63"), 40: (41, "6%"), 74: (77, "$21.50"), 79: (81, "$23.68"),
              101: (104, "$6.53"), 142: (143, "$39")}
    while i < len(w):
        x = w[i]
        if i in merges:
            j, txt = merges[i]
            end_txt = w[j]["w"]
            punct = end_txt[-1] if end_txt[-1] in ",." else ""
            toks.append([txt + punct, x["s"], w[j]["e"]])
            i = j + 1
            continue
        if i == 67:  # "El" largo → "caro." + "El"
            toks.append(["caro.", 24.56, 25.14])
            toks.append(["El", 25.28, 25.46])
            i += 1
            continue
        s = x["w"].replace("diesel", "diésel")
        toks.append([s, x["s"], x["e"]])
        i += 1
    return toks

RED_WORDS = {"cara", "más", "$58.63", "6%", "2022", "sube", "caro", "pavo", "16", "$21.50", "$23.68",
             "culpable", "diésel", "irán", "récord", "$6.53", "septiembre", "leche", "pan", "papas",
             "arándanos", "10", "guerra"}
GREEN_WORDS = {"$39", "salida"}
SUB_SIZE = 82
SUB_Y = 300

def norm(s):
    return s.lower().strip("¿?,.¡!")

def chunk_tokens(toks):
    f = font("Black", SUB_SIZE)
    chunks, cur = [], []
    for k, tok in enumerate(toks):
        cand = cur + [tok]
        width = text_w(" ".join(x[0].upper() for x in cand), f)
        gap = tok[1] - cur[-1][2] if cur else 0
        if cur and (width > 930 or len(cur) >= 4 or gap > .35 or cur[-1][0][-1] in ".?,"):
            chunks.append(cur)
            cur = [tok]
        else:
            cur = cand
    if cur:
        chunks.append(cur)
    out = []
    for n, c in enumerate(chunks):
        start = c[0][1] - .06
        nxt = chunks[n + 1][0][1] - .06 if n + 1 < len(chunks) else NARR_DUR
        end = min(nxt, c[-1][2] + .7)
        out.append((start, end, c))
    return out

TOKS = load_tokens()
CHUNKS = chunk_tokens(TOKS)

def word_color(s):
    n = norm(s)
    if n in GREEN_WORDS: return GREEN
    if n in RED_WORDS: return RED
    return WHITE

def draw_subs(base, t):
    for start, end, c in CHUNKS:
        if start <= t < end:
            break
    else:
        return
    f = font("Black", SUB_SIZE)
    words = [x[0].upper() for x in c]
    space = text_w(" ", f) + 34
    widths = [text_w(s, f) for s in words]
    total = sum(widths) + space * (len(words) - 1)
    layer = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
    x = W / 2 - total / 2
    for (s, ws, we), wd, txt in zip(c, widths, words):
        if t >= ws - .04:
            p = prog(t, ws - .04, .16)
            sc = lerp(.55, 1, ease_back(p, 2.2))
            active = ws - .04 <= t < max(we, ws + .18)
            sc *= 1.04 if active else 1
            col = word_color(s)
            wl = Image.new("RGBA", (int(wd + 60), 200), (0, 0, 0, 0))
            d = ImageDraw.Draw(wl)
            d.text((30, 100), txt, font=f, fill=col, anchor="lm", stroke_width=10, stroke_fill=NAVY)
            paste(layer, wl, x + wd / 2, 130, sc, clamp(p * 3))
        x += wd + space
    base.alpha_composite(layer, (0, SUB_Y - 130))

# ---------------------------------------------------------------- íconos
def person(d, cx, cy, s, col):
    d.ellipse((cx - s * .28, cy - s * .62, cx + s * .28, cy - s * .06), fill=col)
    d.rounded_rectangle((cx - s * .46, cy, cx + s * .46, cy + s * .62), s * .3, fill=col)

@lru_cache(None)
def price_tag_sprite():
    w, h = 470, 230
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = 30
    pts = [(o + 90, o), (o + w, o), (o + w, o + h), (o + 90, o + h), (o, o + h / 2)]
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).polygon([(x + 6, y + 10) for x, y in pts], fill=(5, 20, 50, 90))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(im)
    d.polygon(pts, fill=RED)
    d.ellipse((o + 58, o + h / 2 - 20, o + 98, o + h / 2 + 20), fill=WHITE)
    draw_text(d, (o + 245, o + h / 2 + 4), "PRECIO", font("Black", 74), WHITE)
    up_arrow(d, o + 410, o + h / 2, 100, WHITE)
    return im

@lru_cache(None)
def hook_text_sprite():
    c, pad = card(960, 210, 50)
    d = ImageDraw.Draw(c)
    f = font("Black", 104)
    e = emoji("📈", 104)
    parts = [("TU CENA ", f, NAVY), ("SUBIÓ", f, RED)]
    total = sum(text_w(s, ff) for s, ff, _ in parts) + 24 + e.width
    x = pad + 480 - total / 2
    for s, ff, col in parts:
        d.text((x, pad + 112), s, font=ff, fill=col, anchor="lm")
        x += text_w(s, ff)
    c.alpha_composite(e, (int(x + 24), int(pad + 105 - e.height / 2)))
    return c

@lru_cache(None)
def source_card():
    c, pad = card(940, 270, 40)
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((pad + 40, pad + 36, pad + 250, pad + 92), 28, fill=RED)
    draw_text(d, (pad + 145, pad + 66), "FUENTE", font("Black", 34), WHITE)
    d.text((pad + 40, pad + 150), "American Farm Bureau", font=font("ExtraBold", 60), fill=NAVY, anchor="lm")
    d.text((pad + 40, pad + 218), "Federation", font=font("ExtraBold", 60), fill=NAVY, anchor="lm")
    # ícono de documento
    x0, y0 = pad + 790, pad + 60
    d.rounded_rectangle((x0, y0, x0 + 110, y0 + 150), 14, fill=CREAM, outline=NAVY, width=6)
    for k in range(4):
        d.line((x0 + 22, y0 + 38 + k * 28, x0 + 88 - (20 if k == 3 else 0), y0 + 38 + k * 28), fill=NAVY_2, width=8)
    return c

@lru_cache(None)
def source_pill():
    f = font("SemiBold", 30)
    s = "Fuente: American Farm Bureau Federation"
    w = int(text_w(s, f)) + 60
    c, pad = card(w, 62, 31, fill=WHITE)
    d = ImageDraw.Draw(c)
    draw_text(d, (pad + w / 2, pad + 33), s, f, NAVY)
    return c

TABLE_PEOPLE = None

def table_card(t, t0):
    c, pad = card(940, 560, 44)
    d = ImageDraw.Draw(c)
    cx, cy = pad + 470, pad + 235
    d.rounded_rectangle((cx - 230, cy - 80, cx + 230, cy + 80), 40, fill=NAVY)
    # platos y pavo
    for k in range(4):
        for yy in (cy - 48, cy + 48):
            px = cx - 165 + k * 110
            d.ellipse((px - 22, yy - 22, px + 22, yy + 22), fill=WHITE)
    d.ellipse((cx - 50, cy - 30, cx + 50, cy + 30), fill=(196, 120, 58))
    seats = [(cx - 165 + k * 110, cy - 150) for k in range(4)] + [(cx + 320, cy)] + \
            [(cx + 165 - k * 110, cy + 150) for k in range(4)] + [(cx - 320, cy)]
    for n, (sx, sy) in enumerate(seats):
        p = prog(t, t0 + .12 * n, .25)
        if p <= 0: continue
        s = 70 * ease_back(p)
        col = RED if n % 2 == 0 else NAVY_2
        person(d, sx, sy + (8 if sy > cy else 0), s, col)
    pl = prog(t, 10.2, .3)
    if pl > 0:
        lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        rich_line(dl, pad + 470, pad + 485, [("10 ", font("Black", 72), RED), ("personas", font("Black", 72), NAVY)])
        c.alpha_composite(scale_alpha(lay, pl))
    return c

def counter_card(t):
    c, pad = card(960, 470, 46)
    d = ImageDraw.Draw(c)
    draw_text(d, (pad + 480, pad + 70), "CENA DE THANKSGIVING · 10 PERSONAS", font("Bold", 36), GREY_T)
    p = ease_out(prog(t, 12.35, 2.25))
    val = 58.63 * p
    s = f"${val:,.2f}"
    f = font("Black", 196)
    sc = 1 + .06 * math.sin(clamp((t - 14.6) / .3) * math.pi)
    lay = Image.new("RGBA", (960, 260), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((480, 130), s, font=f, fill=RED, anchor="mm")
    paste(c, lay, pad + 480, pad + 245, sc)
    draw_text(d, (pad + 480, pad + 400), "costo promedio en EE. UU.", font("SemiBold", 40), NAVY)
    return c

@lru_cache(None)
def pct_card():
    c, pad = card(780, 210, 105, fill=RED)
    d = ImageDraw.Draw(c)
    up_arrow(d, pad + 120, pad + 105, 130, WHITE)
    d.text((pad + 210, pad + 112), "+6%", font=font("Black", 140), fill=WHITE, anchor="lm")
    d.text((pad + 545, pad + 78), "vs. el año", font=font("Bold", 38), fill=WHITE, anchor="lm")
    d.text((pad + 545, pad + 128), "pasado", font=font("Bold", 38), fill=WHITE, anchor="lm")
    return c

def timeline_card(t):
    c, pad = card(960, 660, 46)
    d = ImageDraw.Draw(c)
    draw_text(d, (pad + 480, pad + 70), "Precio de la cena, año por año", font("ExtraBold", 46), NAVY)
    years = [2022, 2023, 2024, 2025, 2026]
    ys = [.0, .35, .62, .86, .52]  # forma cualitativa: baja 3 años y sube en 2026
    x0, x1, top, bot = pad + 110, pad + 850, pad + 170, pad + 410
    pts = [(lerp(x0, x1, k / 4), lerp(top, bot, ys[k])) for k in range(5)]
    d.line((x0 - 30, bot + 40, x1 + 30, bot + 40), fill=GREY, width=6)
    p = ease_in_out(prog(t, 18.45, 2.0))
    seg = p * 4
    for k in range(4):
        q = clamp(seg - k)
        if q <= 0: break
        a, b = pts[k], pts[k + 1]
        e = (lerp(a[0], b[0], q), lerp(a[1], b[1], q))
        d.line((a, e), fill=RED if k == 3 else NAVY_2, width=14, joint="curve")
    for k, (x, y) in enumerate(pts):
        if seg >= k - .02:
            r = 22 if k in (0, 4) else 15
            col = RED if k == 4 else NAVY
            d.ellipse((x - r, y - r, x + r, y + r), fill=col, outline=WHITE, width=5)
        col = RED if k == 4 else (NAVY if k == 0 else GREY_T)
        draw_text(d, (x, bot + 90), str(years[k]), font("Black" if k in (0, 4) else "SemiBold", 44 if k in (0, 4) else 36), col)
    # flechas de baja (gris) entre 2022 y 2025
    if seg > 3.2:
        q = prog(t, 18.45 + 2.0 * 3.2 / 4, .3)
        up_arrow(d, pts[4][0], pts[4][1] - 70 - 10 * q, 56 * ease_back(q) if q > 0 else 1, RED)
    pb = prog(t, 21.2, .35)
    if pb > 0:
        lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        f = font("Black", 44)
        s = "PRIMERA SUBIDA DESDE 2022"
        w = text_w(s, f) + 70
        dl.rounded_rectangle((pad + 480 - w / 2, pad + 595 - 42, pad + 480 + w / 2, pad + 595 + 42), 42, fill=RED)
        draw_text(dl, (pad + 480, pad + 598), s, f, WHITE)
        paste(c, lay, c.width / 2, c.height / 2, 1, clamp(pb * 3))
    return c

# ---------------------------------------------------------------- pavo
@lru_cache(None)
def turkey_photo():
    im = Image.open(A("img", IMG["pavo"])).convert("RGB")
    r = 900 / im.height
    return im.resize((int(im.width * r), 900), Image.LANCZOS)

def turkey_card(t):
    w, h = 720, 800
    c, pad = card(w + 24, h + 24, 48)
    ph = turkey_photo()
    z = lerp(1.0, 1.08, prog(t, 22.3, 9))
    cw, ch = w / z * ph.height / h * (h / ph.height), h / z
    # recorte centrado
    sc = max(w / ph.width, h / ph.height) * z
    rw, rh = w / sc, h / sc
    cx, cy = ph.width / 2, ph.height * .52
    crop = ph.resize((w, h), Image.BILINEAR, box=(cx - rw / 2, cy - rh / 2, cx + rw / 2, cy + rh / 2)).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), 38, fill=255)
    c.paste(crop, (pad + 12, pad + 12), mask)
    return c

@lru_cache(None)
def label_pill(s, size=44, fill=NAVY, color=WHITE, wgt="ExtraBold"):
    f = font(wgt, size)
    w = int(text_w(s, f)) + 70
    h = int(size * 1.8)
    c, pad = card(w, h, h // 2, fill=fill)
    draw_text(ImageDraw.Draw(c), (pad + w / 2, pad + h / 2 + 3), s, f, color)
    return c

def price_tag(year, price, red, strike_p=0.0):
    w, h = 470, 150
    fill = RED if red else WHITE
    c, pad = card(w, h, 30, fill=fill, border=None if red else NAVY)
    d = ImageDraw.Draw(c)
    tc = WHITE if red else NAVY
    d.ellipse((pad + 26, pad + h / 2 - 14, pad + 54, pad + h / 2 + 14), outline=tc, width=6)
    d.text((pad + 78, pad + 45), year, font=font("Bold", 36), fill=tc, anchor="lm")
    d.text((pad + 76, pad + 104), price, font=font("Black", 70), fill=tc, anchor="lm")
    if red:
        up_arrow(d, pad + 410, pad + h / 2, 70, WHITE)
    if strike_p > 0:
        x0, x1 = pad + 30, pad + w - 30
        d.line((x0, pad + h - 30, lerp(x0, x1, strike_p), lerp(pad + h - 30, pad + 34, strike_p)), fill=RED, width=14)
    return c

# ---------------------------------------------------------------- diésel / mapa / gráfico
@lru_cache(None)
def diesel_sprite():
    c, pad = card(760, 230, 50, fill=RED)
    d = ImageDraw.Draw(c)
    # gota de combustible
    gx, gy = pad + 120, pad + 118
    d.polygon([(gx, gy - 80), (gx - 52, gy + 5), (gx + 52, gy + 5)], fill=WHITE)
    d.ellipse((gx - 55, gy - 30, gx + 55, gy + 78), fill=WHITE)
    d.ellipse((gx - 22, gy + 8, gx + 4, gy + 38), fill=RED)
    draw_text(d, (pad + 450, pad + 122), "DIÉSEL", font("Black", 150), WHITE)
    return c

@lru_cache(None)
def map_base():
    g = json.load(open(A("geo", "world.json")))
    w, h = 960, 720
    lon0, lon1, lat0, lat1 = 24.0, 72.0, 11.0, 44.0
    def P(lon, lat):
        # Mercator simple
        y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
        y0 = math.log(math.tan(math.pi / 4 + math.radians(lat0) / 2))
        y1 = math.log(math.tan(math.pi / 4 + math.radians(lat1) / 2))
        return (pad + (lon - lon0) / (lon1 - lon0) * w, pad + 40 + (1 - (y - y0) / (y1 - y0)) * (h - 80))
    c, pad = card(w, h, 46, fill=(226, 238, 250))
    sea = c
    layer = Image.new("RGBA", c.size, (0, 0, 0, 0))
    iran = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d, di = ImageDraw.Draw(layer), ImageDraw.Draw(iran)
    for ft in g["features"]:
        geom = ft["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        is_iran = ft["properties"]["name"] == "Iran"
        for poly in polys:
            ring = [P(lon, lat) for lon, lat in poly[0]]
            if len(ring) < 3: continue
            (di if is_iran else d).polygon(ring, fill=RED if is_iran else (205, 213, 226), outline=WHITE, width=3)
    mask = Image.new("L", c.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((pad, pad, pad + w, pad + h), 46, fill=255)
    out = c.copy()
    l2 = Image.new("RGBA", c.size, (0, 0, 0, 0)); l2.paste(layer, (0, 0), mask)
    i2 = Image.new("RGBA", c.size, (0, 0, 0, 0)); i2.paste(iran, (0, 0), mask)
    out.alpha_composite(l2)
    lbl = ImageDraw.Draw(l2)
    names = [("IRAK", 43.5, 33), ("ARABIA SAUDITA", 44.5, 24), ("TURQUÍA", 33.5, 39.3), ("AFGANISTÁN", 66, 34.5),
             ("PAKISTÁN", 68.5, 28), ("Golfo Pérsico", 51.5, 27)]
    txt = Image.new("RGBA", c.size, (0, 0, 0, 0))
    dt = ImageDraw.Draw(txt)
    for n, lo, la in names:
        draw_text(dt, P(lo, la), n, font("SemiBold", 24), GREY_T)
    out.alpha_composite(txt)
    return out, i2, P(53.5, 32.6)

def map_card(t):
    base, iran, (ix, iy) = map_base()
    c = base.copy()
    p = prog(t, 34.85, .35)
    if p > 0:
        pulse = .82 + .18 * (0.5 + 0.5 * math.sin((t - 34.85) * 7))
        c.alpha_composite(scale_alpha(iran, clamp(p * 2) * pulse))
        lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        f = font("Black", 58)
        w = text_w("IRÁN", f) + 60
        dl.rounded_rectangle((ix - w / 2, iy - 44, ix + w / 2, iy + 44), 44, fill=NAVY)
        draw_text(dl, (ix, iy + 3), "IRÁN", f, WHITE)
        sc = ease_back(p)
        paste(c, lay, c.width / 2, c.height / 2, 1, clamp(p * 3))
    return c

DIESEL_Y = [0.10, 0.16, 0.13, 0.30, 0.42, 0.38, 0.55, 0.62, 0.58, 0.74, 0.82, 0.95]  # forma ilustrativa

def chart_card(t):
    w, h = 960, 760
    c, pad = card(w, h, 46)
    d = ImageDraw.Draw(c)
    d.text((pad + 50, pad + 62), "Precio del diésel por galón", font=font("ExtraBold", 44), fill=NAVY, anchor="lm")
    x0, x1, top, bot = pad + 60, pad + 880, pad + 300, pad + 640
    for k in range(5):
        y = lerp(top - 60, bot, k / 4)
        d.line((x0, y, x1, y), fill=(232, 237, 245), width=3)
    d.line((x0, bot, x1, bot), fill=GREY, width=5)
    pts = [(lerp(x0, x1 - 40, k / (len(DIESEL_Y) - 1)), lerp(bot - 20, top, v)) for k, v in enumerate(DIESEL_Y)]
    p = ease_in_out(prog(t, 35.6, 2.6))
    n = p * (len(pts) - 1)
    drawn = [pts[0]]
    for k in range(len(pts) - 1):
        q = clamp(n - k)
        if q <= 0: break
        a, b = pts[k], pts[k + 1]
        drawn.append((lerp(a[0], b[0], q), lerp(a[1], b[1], q)))
    if len(drawn) > 1:
        poly = drawn + [(drawn[-1][0], bot), (drawn[0][0], bot)]
        area = Image.new("RGBA", c.size, (0, 0, 0, 0))
        ImageDraw.Draw(area).polygon(poly, fill=RED + (40,))
        c.alpha_composite(area)
        d = ImageDraw.Draw(c)
        d.line(drawn, fill=RED, width=12, joint="curve")
        ex, ey = drawn[-1]
        d.ellipse((ex - 12, ey - 12, ex + 12, ey + 12), fill=RED)
    draw_text(d, (x0 + 10, bot + 40), "Inicio de la guerra", font("SemiBold", 28), GREY_T, anchor="lm")
    draw_text(d, (x1 - 40, bot + 40), "Septiembre", font("Bold", 30), NAVY, anchor="mm")
    draw_text(d, (pad + w - 40, pad + h - 34), "Fuente: AAA", font("SemiBold", 28), GREY_T, anchor="rm")
    # punto récord + rótulo
    pr = prog(t, 37.1, .4)
    if pr > 0:
        ex, ey = pts[-1]
        lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        pulse = 1 + .35 * (0.5 + 0.5 * math.sin((t - 37.1) * 8))
        r = 26 * pulse
        dl.ellipse((ex - r, ey - r, ex + r, ey + r), fill=RED + (90,))
        dl.ellipse((ex - 20, ey - 20, ex + 20, ey + 20), fill=RED, outline=WHITE, width=6)
        # callout
        bx0, by0, bx1, by1 = pad + 50, pad + 115, pad + 650, pad + 265
        dl.rounded_rectangle((bx0, by0, bx1, by1), 26, fill=NAVY)
        dl.line(((bx1, by0 + 70), (ex - 26, ey)), fill=NAVY, width=6)
        cnt = 6.53 * ease_out(prog(t, 37.1, 1.4))
        dl.text((bx0 + 30, by0 + 52), f"${cnt:.2f}/galón", font=font("Black", 64), fill=(255, 120, 128), anchor="lm")
        dl.text((bx0 + 30, by0 + 115), "– récord (septiembre)", font=font("Bold", 38), fill=WHITE, anchor="lm")
        paste(c, lay, c.width / 2, c.height / 2, 1, clamp(pr * 3))
    return c

# ---------------------------------------------------------------- camión e ingredientes
@lru_cache(None)
def icon(kind, s=150):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = s / 150
    if kind == "leche":
        d.polygon([(40 * k, 45 * k), (75 * k, 12 * k), (110 * k, 45 * k)], fill=(225, 232, 244), outline=NAVY, width=int(5 * k))
        d.rectangle((60 * k, 4 * k, 90 * k, 16 * k), fill=NAVY_2)
        d.rounded_rectangle((40 * k, 45 * k, 110 * k, 145 * k), 8 * k, fill=WHITE, outline=NAVY, width=int(5 * k))
        d.rectangle((43 * k, 75 * k, 107 * k, 112 * k), fill=(70, 140, 230))
        draw_text(d, (75 * k, 94 * k), "MILK", font("Black", int(20 * k)), WHITE)
    elif kind == "pan":
        d.rounded_rectangle((10 * k, 45 * k, 140 * k, 125 * k), 40 * k, fill=(214, 140, 66), outline=(140, 78, 28), width=int(5 * k))
        d.ellipse((14 * k, 30 * k, 136 * k, 95 * k), fill=(232, 165, 85), outline=(140, 78, 28), width=int(5 * k))
        for j in range(3):
            x = 45 * k + j * 30 * k
            d.line((x, 48 * k, x + 18 * k, 72 * k), fill=(250, 218, 160), width=int(7 * k))
    elif kind == "papas":
        for (x, y, rx, ry) in [(55, 95, 45, 33), (98, 80, 40, 30), (72, 58, 36, 27)]:
            d.ellipse(((x - rx) * k, (y - ry) * k, (x + rx) * k, (y + ry) * k), fill=(196, 148, 92), outline=(122, 84, 44), width=int(5 * k))
            for dx, dy in [(-12, -6), (10, 5), (-2, 12)]:
                d.ellipse(((x + dx - 3) * k, (y + dy - 3) * k, (x + dx + 3) * k, (y + dy + 3) * k), fill=(122, 84, 44))
    elif kind == "arandanos":
        d.ellipse((62 * k, 8 * k, 96 * k, 38 * k), fill=(70, 160, 90))
        for (x, y) in [(50, 70), (95, 68), (72, 105), (35, 108), (110, 105), (72, 48)]:
            d.ellipse(((x - 25) * k, (y - 25) * k, (x + 25) * k, (y + 25) * k), fill=(196, 24, 54), outline=(120, 10, 30), width=int(4 * k))
            d.ellipse(((x - 12) * k, (y - 14) * k, (x - 3) * k, (y - 5) * k), fill=(255, 150, 160))
    return im

@lru_cache(None)
def truck_sprite():
    im = Image.new("RGBA", (720, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 30, 480, 230), 22, fill=WHITE, outline=NAVY, width=8)
    d.rectangle((18, 160, 472, 190), fill=RED)
    draw_text(d, (245, 100), "CARGA", font("Black", 64), NAVY)
    d.rounded_rectangle((490, 90, 690, 230), 26, fill=NAVY)
    d.polygon([(560, 90), (650, 90), (690, 150), (690, 160), (560, 160)], fill=NAVY)
    d.polygon([(575, 104), (640, 104), (672, 150), (575, 150)], fill=(170, 210, 245))
    d.rectangle((680, 190, 705, 215), fill=RED)
    for x in (110, 380, 600):
        d.ellipse((x - 46, 186, x + 46, 278), fill=(30, 34, 44))
        d.ellipse((x - 20, 212, x + 20, 252), fill=GREY)
    return im

INGREDIENTS = [("leche", "Leche", 41.62), ("pan", "Pan", 42.50), ("papas", "Papas", 43.30), ("arandanos", "Arándanos", 44.06)]

def truck_card(t):
    w, h = 960, 900
    c, pad = card(w, h, 46)
    d = ImageDraw.Draw(c)
    rich_line(d, pad + w / 2, pad + 70, [("Transportar cuesta más ", font("ExtraBold", 44), NAVY)])
    up_arrow(d, pad + w / 2 + text_w("Transportar cuesta más ", font("ExtraBold", 44)) / 2 + 26, pad + 70, 52, RED)
    drive = ease_in_out(prog(t, 44.55, .5)) * 700
    bounce = 4 * math.sin(t * 18)
    tx, ty = pad + 470 + drive, pad + 690 + bounce
    tr = truck_sprite()
    c.alpha_composite(tr, (int(tx - tr.width / 2), int(ty - tr.height / 2)))
    for n, (kind, name, t0) in enumerate(INGREDIENTS):
        if t < t0 - .05: continue
        ic = icon(kind)
        sx, sy = pad + 140 + n * 227, pad + 250
        dx, dy = tx - 225 + n * 95 - 60, ty - 150
        pj = ease_in_out(prog(t, t0 + .45, .45))
        x = lerp(sx, dx, pj)
        y = lerp(sy, dy, pj) - math.sin(pj * math.pi) * 150
        sc = lerp(1, .62, pj) * ease_back(prog(t, t0 - .05, .3))
        paste(c, ic, x, y, sc)
        # rótulo con flechita roja (se queda en la fila)
        lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        f = font("ExtraBold", 36)
        tw = text_w(name, f)
        dl.text((sx - (tw + 40) / 2, sy + 115), name, font=f, fill=NAVY, anchor="lm")
        up_arrow(dl, sx + (tw + 40) / 2 - 14, sy + 112, 38, RED)
        paste(c, lay, c.width / 2, c.height / 2, 1, clamp(prog(t, t0, .25) * 3))
    return c

# ---------------------------------------------------------------- ahorro
@lru_cache(None)
def store_card():
    c, pad = card(860, 250, 44)
    d = ImageDraw.Draw(c)
    x0, y0 = pad + 40, pad + 40
    for k in range(5):
        d.rectangle((x0 + k * 34, y0, x0 + k * 34 + 34, y0 + 52), fill=RED if k % 2 == 0 else WHITE, outline=RED, width=3)
    d.rectangle((x0 + 8, y0 + 52, x0 + 162, y0 + 165), fill=CREAM, outline=NAVY, width=6)
    d.rectangle((x0 + 62, y0 + 95, x0 + 108, y0 + 165), fill=NAVY_2)
    d.text((pad + 250, pad + 95), "Algunas tiendas", font=font("ExtraBold", 50), fill=NAVY, anchor="lm")
    d.text((pad + 250, pad + 160), "bajan precios", font=font("ExtraBold", 50), fill=GREEN, anchor="lm")
    up_arrow(d, pad + 250 + text_w("bajan precios", font("ExtraBold", 50)) + 50, pad + 160, 64, GREEN, down=True)
    return c

@lru_cache(None)
def piggy(s=170):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = s / 170
    pink, dark = (255, 170, 190), (214, 98, 128)
    d.ellipse((60 * k, 2 * k, 104 * k, 46 * k), fill=(255, 200, 60), outline=(205, 150, 20), width=int(4 * k))
    draw_text(d, (82 * k, 25 * k), "$", font("Black", int(28 * k)), (160, 110, 10))
    d.rectangle((70 * k, 46 * k, 94 * k, 60 * k), fill=(0, 0, 0, 0))
    for x in (40, 110):
        d.rounded_rectangle((x * k, 120 * k, (x + 22) * k, 160 * k), 8 * k, fill=dark)
    d.ellipse((10 * k, 52 * k, 160 * k, 145 * k), fill=pink, outline=dark, width=int(5 * k))
    d.polygon([(40 * k, 62 * k), (55 * k, 30 * k), (72 * k, 58 * k)], fill=pink, outline=dark)
    d.ellipse((135 * k, 80 * k, 168 * k, 115 * k), fill=(255, 140, 165), outline=dark, width=int(4 * k))
    d.ellipse((144 * k, 92 * k, 150 * k, 100 * k), fill=dark)
    d.ellipse((154 * k, 92 * k, 160 * k, 100 * k), fill=dark)
    d.ellipse((112 * k, 76 * k, 122 * k, 86 * k), fill=NAVY)
    d.rectangle((68 * k, 58 * k, 98 * k, 64 * k), fill=dark)
    return im

def compare_card(t):
    w, h = 960, 800
    c, pad = card(w, h, 46)
    d = ImageDraw.Draw(c)
    draw_text(d, (pad + w / 2, pad + 64), "Cena para 10 personas", font("ExtraBold", 46), NAVY)
    base_y, maxh = pad + 640, 400
    cols = [(pad + 260, "Promedio", 58.63, RED, 49.50, 50.6), (pad + 700, "Aldi", 39.0, GREEN, 53.40, 54.2)]
    for cx, name, val, col, t0, t1 in cols:
        if t < t0: continue
        p = ease_out(prog(t, t0, t1 - t0))
        bh = maxh * val / 58.63 * p
        d.rounded_rectangle((cx - 120, base_y - bh, cx + 120, base_y), 26, fill=col)
        v = val * p
        s = f"${v:.2f}" if name == "Promedio" else f"${v:.0f}"
        draw_text(d, (cx, base_y - bh - 55), s, font("Black", 84), col)
        draw_text(d, (cx, base_y + 50), name, font("ExtraBold", 50), NAVY)
    d.line((pad + 80, base_y, pad + w - 80, base_y), fill=GREY, width=6)
    pp = prog(t, 54.25, .4)
    if pp > 0:
        pg = piggy(170)
        paste(c, pg, pad + 820, pad + 250, ease_back(pp), clamp(pp * 3), rot=8 * math.sin((t - 54.25) * 4) * (1 - prog(t, 54.25, 1.5)))
        lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        f = font("Black", 40)
        s = "AHORRAS $19.63"
        tw = text_w(s, f) + 50
        cx, cy = pad + 700, pad + 140
        dl.rounded_rectangle((cx - tw / 2 - 60, cy - 34, cx + tw / 2 - 60, cy + 34), 34, fill=GREEN)
        draw_text(dl, (cx - 60, cy + 3), s, f, WHITE)
        paste(c, lay, c.width / 2, c.height / 2, 1, clamp(pp * 3))
    return c

@lru_cache(None)
def cta_card():
    c, pad = card(960, 270, 50, fill=NAVY)
    d = ImageDraw.Draw(c)
    f = font("Black", 84)
    draw_text(d, (pad + 480, pad + 85), "COMPARA ANTES", f, WHITE)
    e = emoji("✅", 84)
    tw = text_w("DE COMPRAR", f)
    x = pad + 480 - (tw + 24 + e.width) / 2
    d.text((x, pad + 190), "DE COMPRAR", font=f, fill=WHITE, anchor="lm")
    c.alpha_composite(e, (int(x + tw + 24), int(pad + 188 - e.height / 2)))
    return c

# ---------------------------------------------------------------- encuesta y compartir
POLL = [("Pernil", "🍖", 58.05), ("Arroz con gandules", "🍚", 58.40), ("Tamales", "🫔", 58.75), ("Otro", "💬", 59.10)]

def poll_card(t):
    w, h = 960, 900
    c, pad = card(w, h, 46)
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((pad + 330, pad + 40, pad + 630, pad + 100), 30, fill=RED)
    draw_text(d, (pad + 480, pad + 72), "ENCUESTA", font("Black", 38), WHITE)
    draw_text(d, (pad + 480, pad + 160), "¿Qué plato latino no", font("ExtraBold", 54), NAVY)
    draw_text(d, (pad + 480, pad + 230), "falta en tu mesa?", font("ExtraBold", 54), NAVY)
    # resaltado que recorre las opciones (como si alguien votara)
    hi = -1
    if t > 59.5:
        hi = int((t - 59.5) / .55) % 4
    for n, (name, em, t0) in enumerate(POLL):
        p = prog(t, t0, .3)
        if p <= 0: continue
        oy = pad + 330 + n * 135
        lay = Image.new("RGBA", (880, 130), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        on = n == hi
        dl.rounded_rectangle((0, 8, 880, 118), 55, fill=NAVY if on else (236, 241, 248), outline=NAVY, width=5)
        e = emoji(em, 70)
        lay.alpha_composite(e, (40, int(63 - e.height / 2)))
        dl.text((140, 64), name, font=font("ExtraBold", 48), fill=WHITE if on else NAVY, anchor="lm")
        dl.ellipse((790, 38, 846, 94), outline=WHITE if on else NAVY, width=6)
        if on:
            dl.ellipse((804, 52, 832, 80), fill=RED)
        paste(c, lay, pad + 480 + (1 - ease_out(p)) * 200, oy, 1, clamp(p * 2))
    return c

@lru_cache(None)
def share_icon(s=190):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, s - 1, s - 1), fill=RED)
    k = s / 190
    pts = [(62 * k, 95 * k), (128 * k, 58 * k), (128 * k, 132 * k)]
    d.line((pts[0], pts[1]), fill=WHITE, width=int(12 * k))
    d.line((pts[0], pts[2]), fill=WHITE, width=int(12 * k))
    for x, y in pts:
        d.ellipse((x - 22 * k, y - 22 * k, x + 22 * k, y + 22 * k), fill=WHITE)
    return im

# ---------------------------------------------------------------- composición
def frame(fi):
    t = fi / FPS
    if t >= CLOSE_START - 1e-6:
        return closing_frame(fi - round(NARR_DUR * FPS))
    base = background(t)

    # 1) GANCHO -----------------------------------------------------
    if t < 6.0:
        p = ease_out(prog(t, .25, 2.75))
        y = lerp(1700, 840, p)
        wob = 3 * math.sin(t * 6) if t > 3 else 0
        a = 1 - prog(t, 5.45, .25)
        paste(base, price_tag_sprite(), 560, y, lerp(.7, 1, p), clamp(prog(t, .25, .2)) * a, rot=6 + wob)
        pop(base, hook_text_sprite(), W / 2, 1290, t, 2.28, 5.45)

    # 2) EL COSTO ---------------------------------------------------
    if 5.6 <= t < 22.6:
        slide(base, source_card(), W / 2, 640, t, 5.74, 12.05, dx=-W, dy=0, out_dy=-100)
        if 8.5 <= t < 12.4:
            sp = table_card(t, 8.62)
            slide(base, sp, W / 2, 1150, t, 8.50, 12.05, dy=160, out_dy=-100)
        slide(base, source_pill(), W / 2, 1610, t, 12.1, 22.05, dy=60, out_dy=40)
        if 12.1 <= t < 18.7:
            slide(base, counter_card(t), W / 2, 860, t, 12.15, 18.30, dy=150, out_dy=-120)
            pop(base, pct_card(), W / 2, 1290, t, 15.98, 18.30)
        if 18.2 <= t < 22.6:
            slide(base, timeline_card(t), W / 2, 1030, t, 18.32, 22.05, dy=150, out_dy=-100)

    # 3) EL PAVO ----------------------------------------------------
    if 22.3 <= t < 31.6:
        slide(base, turkey_card(t), W / 2, 900, t, 22.40, 31.05, dy=200, out_dy=-100)
        pop(base, label_pill("Pavo de 16 libras", 48), W / 2, 1335, t, 25.95, 31.05)
        if t >= 27.4:
            strike = ease_out(prog(t, 28.95, .35))
            slide(base, price_tag("2025", "$21.50", False, strike), 300, 1500, t, 27.42, 31.05, dx=-200, dy=0)
        pop(base, price_tag("2026", "$23.68", True), 790, 1500, t, 29.40, 31.05, rot=-3)

    # 4) EL CULPABLE ------------------------------------------------
    if 31.3 <= t < 33.9:
        pop(base, label_pill("¿EL CULPABLE?", 56, fill=WHITE, color=NAVY, wgt="Black"), W / 2, 860, t, 31.55, 33.55)
        pop(base, diesel_sprite(), W / 2, 1100, t, 32.80, 33.55, rot=-4)
    if 33.6 <= t < 35.8:
        slide(base, map_card(t), W / 2, 1010, t, 33.65, 35.45, dy=160, out_dx=-W, out_dy=0)
        pop(base, label_pill("Guerra de Irán", 46, fill=RED), W / 2, 1450, t, 34.55, 35.45)
    if 35.4 <= t < 40.2:
        slide(base, chart_card(t), W / 2, 1010, t, 35.45, 39.70, dx=W, dy=0, out_dy=-100)
    if 39.8 <= t < 45.1:
        slide(base, truck_card(t), W / 2, 1060, t, 39.90, 44.75, dy=160, out_dy=-100)

    # 5) LA SALIDA --------------------------------------------------
    if 44.8 <= t < 57.3:
        slide(base, store_card(), W / 2, 760, t, 46.20, 49.25, dx=-W, dy=0, out_dy=-100)
        if 49.3 <= t:
            slide(base, compare_card(t), W / 2, 930, t, 49.40, 56.95, dy=170, out_dy=-100)
        pop(base, cta_card(), W / 2, 1500, t, 54.62, 56.95)

    # 6) CIERRE -----------------------------------------------------
    if 57.0 <= t:
        slide(base, poll_card(t), W / 2, 960, t, 57.85, 64.6, dy=170)
        if t >= 61.4:
            b = abs(math.sin((t - 61.4) * 5.5)) * 40 * max(0, 1 - (t - 61.4) / 3)
            pop(base, share_icon(), 300, 1555 - b, t, 61.40, 64.6)
            pop(base, label_pill("¡Compártelo!", 54, fill=WHITE, color=NAVY, wgt="Black"), 640, 1555, t, 61.65, 64.6)

    draw_subs(base, t)
    return base.convert("RGB")

CLOSE_FRAMES = None

def closing_frame(k):
    global CLOSE_FRAMES
    if CLOSE_FRAMES is None:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", A("cierre_capital_curioso.mp4"), "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        CLOSE_FRAMES = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    k = min(k, len(CLOSE_FRAMES) - 1)
    im = Image.fromarray(CLOSE_FRAMES[k])
    # transición corta desde la última escena
    if k < 6:
        last = frame(round(NARR_DUR * FPS) - 1)
        im = Image.blend(last, im, (k + 1) / 7)
    return im

def render_bytes(fi):
    return frame(fi).tobytes()

# ---------------------------------------------------------------- audio
SR = 48000

def tone_pop():
    n = int(SR * .12)
    t = np.arange(n) / SR
    f = 950 * np.exp(-t * 28) + 260
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = np.exp(-t * 38) * (1 - np.exp(-t * 900))
    return (np.sin(ph) * env * .55).astype(np.float32)

def tone_cash():
    rng = np.random.default_rng(3)
    n = int(SR * 1.1)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    # clic mecánico (cajón)
    for off in (0.0, .045):
        i0 = int(off * SR)
        m = int(.03 * SR)
        nz = rng.standard_normal(m) * np.exp(-np.arange(m) / SR * 160)
        out[i0:i0 + m] += (nz * .35).astype(np.float32)
    # campanita "ching"
    tb = t - .09
    msk = tb > 0
    bell = np.zeros(n)
    for fr, amp, dec in [(2093, .5, 5), (2637, .35, 6), (3136, .25, 7), (4186, .15, 9), (5274, .08, 11)]:
        bell += amp * np.sin(2 * np.pi * fr * tb) * np.exp(-tb * dec)
    out += (bell * msk * .32).astype(np.float32)
    return out

def tone_whoosh():
    rng = np.random.default_rng(7)
    n = int(SR * .3)
    t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    # filtro paso bajo móvil sencillo
    y = np.zeros(n)
    a = 0
    for i in range(n):
        c = .05 + .25 * (i / n)
        a += c * (nz[i] - a)
        y[i] = a
    env = np.sin(np.pi * t / .3) ** 2
    return (y * env * .22).astype(np.float32)

def build_audio():
    total = TOTAL_FRAMES / FPS
    n = int(total * SR) + SR
    mix = np.zeros((n, 2), np.float32)

    def load(path, gain_db=0.0):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.float32).reshape(-1, 2) * (10 ** (gain_db / 20))

    voice = load(A("audio", "narracion.mp3"))
    music = load(A("audio", "musica_wallpaper_kevin_macleod.mp3"))[:n]
    # música: entrada suave, ducking ligero bajo la voz, salida al final del cierre
    env_v = np.abs(voice[:, 0])
    win = int(.25 * SR)
    smooth = np.convolve(env_v, np.ones(win) / win, mode="same")
    duck = np.ones(len(music), np.float32)
    talk = np.clip(smooth / 0.03, 0, 1)
    duck[:len(talk)] = 1 - .35 * talk
    mg = 10 ** (-23 / 20)
    tt = np.arange(len(music)) / SR
    fade = np.clip(tt / .8, 0, 1) * np.clip((total - tt) / 1.8, 0, 1)
    # en el cierre la música sube un poco
    lift = 1 + .6 * np.clip((tt - CLOSE_START) / .4, 0, 1)
    music = music * (mg * duck * fade * lift)[:, None]
    mix[:len(music)] += music
    mix[:len(voice)] += voice

    fx = {"pop": tone_pop(), "cash": tone_cash(), "whoosh": tone_whoosh()}
    cues = [
        ("whoosh", .2), ("pop", 2.30),
        ("whoosh", 5.62), ("pop", 5.80), ("pop", 10.22), ("pop", 12.40), ("cash", 14.55), ("pop", 16.00),
        ("whoosh", 18.30), ("pop", 21.20),
        ("whoosh", 22.30), ("pop", 26.00), ("cash", 27.45), ("cash", 29.42),
        ("whoosh", 31.30), ("pop", 32.82), ("whoosh", 33.62), ("pop", 34.88), ("whoosh", 35.45), ("pop", 37.12), ("cash", 38.55),
        ("whoosh", 39.86), ("pop", 41.62), ("pop", 42.50), ("pop", 43.30), ("pop", 44.06),
        ("whoosh", 44.80), ("pop", 46.22), ("pop", 49.45), ("cash", 54.15), ("pop", 54.62),
        ("whoosh", 57.00), ("pop", 57.86), ("pop", 61.42),
    ]
    vol = {"pop": .55, "cash": .6, "whoosh": .35}
    for name, at in cues:
        s = fx[name] * vol[name]
        i0 = int(at * SR)
        mix[i0:i0 + len(s)] += s[:, None]
    mix = mix[:int(total * SR)]
    peak = np.abs(mix).max()
    if peak > .98:
        mix *= .98 / peak
    path = os.path.join(BUILD, "mezcla.wav")
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
    return path

# ---------------------------------------------------------------- main
def main():
    if "--stills" in sys.argv:
        out = os.path.join(BUILD, "stills"); os.makedirs(out, exist_ok=True)
        ts = [float(x) for x in sys.argv[sys.argv.index("--stills") + 1:]] or [1, 4]
        for t in ts:
            frame(round(t * FPS)).save(os.path.join(out, f"t{t:05.2f}.jpg"), quality=88)
        return
    audio = build_audio()
    out = os.path.join(BUILD, "capital_curioso_thanksgiving.mp4")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                           "-shortest", out], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for k, b in enumerate(pool.imap(render_bytes, range(TOTAL_FRAMES), chunksize=4)):
            ff.stdin.write(b)
            if k % 150 == 0:
                print(f"{k}/{TOTAL_FRAMES}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("OK", out)

if __name__ == "__main__":
    main()
