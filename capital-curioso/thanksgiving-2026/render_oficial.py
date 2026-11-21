#!/usr/bin/env python3
"""Capital Curioso — Thanksgiving 2026, FORMATO OFICIAL (azul marino / rojo #C8102E).

Uso:  python3 render_oficial.py                 → build/capital_curioso_thanksgiving_oficial.mp4
      python3 render_oficial.py --stills 3 15   → build/stills_oficial/
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
NARR_DUR = 64.522449
TOTAL_FRAMES = round(NARR_DUR * FPS)          # duración = audio
CLOSE_START = 62.0                             # cierre animado dentro del audio
CLOSE_SPEED = 3.5 / (TOTAL_FRAMES / FPS - CLOSE_START)

# ---------------------------------------------------------------- paleta oficial (únicos colores)
NAVY = (0x0B, 0x1F, 0x3A)
NAVY2 = (0x13, 0x29, 0x4B)
RED = (0xC8, 0x10, 0x2E)
WHITE = (255, 255, 255)
GREY = (0xD9, 0xDE, 0xE5)
GREEN = (0x2E, 0x9E, 0x5B)

def rgba(c, a=255):
    return c + (a,)

@lru_cache(None)
def font(w, s):
    return ImageFont.truetype(A("fonts", f"Poppins-{w}.ttf"), int(s))

# ---------------------------------------------------------------- utilidades
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x

def prog(t, t0, d):
    return clamp((t - t0) / d) if d > 0 else float(t >= t0)

def ease_out(p): return 1 - (1 - p) ** 3
def ease_in_out(p): return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def ease_back(p, s=1.7):
    p -= 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2
def lerp(a, b, p): return a + (b - a) * p

def scale_alpha(im, a):
    if a >= .999: return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return im

def paste(base, sp, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if alpha <= .01 or scale <= .01: return
    if abs(scale - 1) > .003:
        sp = sp.resize((max(1, int(sp.width * scale)), max(1, int(sp.height * scale))), Image.BICUBIC)
    if abs(rot) > .05:
        sp = sp.rotate(rot, resample=Image.BICUBIC, expand=True)
    sp = scale_alpha(sp, alpha)
    base.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)))

def pop(base, sp, cx, cy, t, t0, t1=1e9, dur=.36, rot=0.0):
    if t < t0 or t > t1 + .25: return
    p = prog(t, t0, dur)
    sc, a = lerp(.4, 1, ease_back(p)), clamp(p * 2.5)
    if t > t1:
        q = prog(t, t1, .25); a *= 1 - q; sc *= 1 - .1 * q
    paste(base, sp, cx, cy, sc, a, rot)

def slide(base, sp, cx, cy, t, t0, t1=1e9, dx=0, dy=110, dur=.35, out_dx=0, out_dy=-80):
    if t < t0 or t > t1 + .25: return
    p = ease_out(prog(t, t0, dur))
    x, y, a = cx + dx * (1 - p), cy + dy * (1 - p), p
    if t > t1:
        q = ease_in_out(prog(t, t1, .25)); x += out_dx * q; y += out_dy * q; a *= 1 - q
    paste(base, sp, x, y, 1, a)

def tw(s, f): return f.getlength(s)

def text(d, xy, s, f, fill, anchor="mm", stroke=0, sfill=None):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sfill)

def arrow(d, cx, cy, s, fill, down=False):
    k = -1 if down else 1
    pts = [(cx, cy - k * s * .55), (cx + s * .45, cy - k * s * .05), (cx + s * .16, cy - k * s * .05),
           (cx + s * .16, cy + k * s * .5), (cx - s * .16, cy + k * s * .5), (cx - s * .16, cy - k * s * .05),
           (cx - s * .45, cy - k * s * .05)]
    d.polygon(pts, fill=fill)

@lru_cache(None)
def _card(w, h, border, r, bw, fill):
    pad = 30
    im = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 10, pad + w, pad + h + 10), r, fill=120)
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    im.paste(Image.new("RGBA", im.size, rgba(NAVY)), (0, 0), sh)
    ImageDraw.Draw(im).rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=rgba(fill),
                                         outline=rgba(border) if border else None, width=bw if border else 0)
    return im, pad

def card(w, h, border=WHITE, r=22, bw=3, fill=NAVY2):
    im, pad = _card(int(w), int(h), border, r, bw, fill)
    return im.copy(), pad

@lru_cache(None)
def tag(s, size=34, fill=RED, color=WHITE, wgt="Black", padx=28):
    """Etiqueta pequeña tipo FUENTE / ENCUESTA."""
    f = font(wgt, size)
    w, h = int(tw(s, f)) + padx * 2, int(size * 1.7)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 10, fill=rgba(fill))
    text(d, (w / 2, h / 2 + 2), s, f, color)
    return im

@lru_cache(None)
def pill(s, size=44, border=WHITE, color=WHITE, wgt="ExtraBold"):
    f = font(wgt, size)
    w, h = int(tw(s, f)) + 70, int(size * 1.9)
    c, pad = card(w, h, border=border, r=16)
    text(ImageDraw.Draw(c), (pad + w / 2, pad + h / 2 + 3), s, f, color)
    return c

# ---------------------------------------------------------------- fondos
IMG = {
    "cocina": "01_familia_cocina.jpg", "padrehijo": "02_padre_hijo_mesa.jpg", "mercado": "03_mercado.jpg",
    "gasolinera": "04_gasolinera.jpg", "mangueras": "05_mangueras.jpg", "cisterna": "06_camion_cisterna.jpg",
    "buffet": "07_pavo_buffet.jpg", "pavo": "08_pavo_horneado.jpg",
}
OVERLAY_A = int(255 * .60)   # capa azul marino #0B1F3A al 60 %

@lru_cache(None)
def photo(key):
    im = ImageOps.exif_transpose(Image.open(A("img", IMG[key]))).convert("RGB")
    # leve desaturación para un look uniforme de marca
    im = ImageEnhance.Color(im).enhance(.75)
    r = max(W * 1.18 / im.width, H * 1.18 / im.height)
    return im.resize((int(im.width * r + .5), int(im.height * r + .5)), Image.LANCZOS)

def kenburns(key, p, z0=1.0, z1=1.1, fx0=.5, fy0=.5, fx1=.5, fy1=.5):
    im = photo(key)
    base = min(im.width / W, im.height / H)
    z = lerp(z0, z1, p)
    cw, ch = W * base / z, H * base / z
    cx, cy = lerp(fx0, fx1, p) * im.width, lerp(fy0, fy1, p) * im.height
    x0, y0 = clamp(cx - cw / 2, 0, im.width - cw), clamp(cy - ch / 2, 0, im.height - ch)
    return im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")

@lru_cache(None)
def overlay():
    return Image.new("RGBA", (W, H), rgba(NAVY, OVERLAY_A))

@lru_cache(None)
def grid_bg():
    """Fondo sin foto: degradado #0B1F3A → #13294B con cuadrícula sutil."""
    y = np.linspace(0, 1, H)[:, None, None]
    g = (np.array(NAVY) * (1 - y) + np.array(NAVY2) * y) * np.ones((1, W, 1))
    im = Image.fromarray(g.astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for x in range(0, W + 1, 90):
        d.line((x, 0, x, H), fill=rgba(GREY, 16), width=2)
    for yy in range(0, H + 1, 90):
        d.line((0, yy, W, yy), fill=rgba(GREY, 16), width=2)
    im.alpha_composite(lay)
    return im

SCENES = [
    (0.00, 5.62, "cocina", dict(z0=1.0, z1=1.14, fx0=.45, fy0=.5, fx1=.42, fy1=.42)),
    (5.62, 22.30, "grid", None),
    (22.30, 31.30, "buffet", dict(z0=1.0, z1=1.08, fx0=.5, fy0=.4, fx1=.5, fy1=.45)),
    (31.30, 35.50, "mangueras", dict(z0=1.04, z1=1.16, fx0=.5, fy0=.45, fx1=.45, fy1=.4)),
    (35.50, 39.86, "gasolinera", dict(z0=1.0, z1=1.1, fx0=.5, fy0=.55, fx1=.5, fy1=.5)),
    (39.86, 44.80, "cisterna", dict(z0=1.0, z1=1.05, fx0=.28, fy0=.5, fx1=.55, fy1=.5)),
    (44.80, 57.00, "mercado", dict(z0=1.0, z1=1.12, fx0=.5, fy0=.55, fx1=.5, fy1=.5)),
    (57.00, CLOSE_START, "padrehijo", dict(z0=1.0, z1=1.08, fx0=.5, fy0=.45, fx1=.55, fy1=.45)),
]
TRANS = .3

def scene_frame(i, t):
    t0, t1, key, kb = SCENES[i]
    if key == "grid":
        fr = grid_bg().copy()
        return fr
    p = clamp((t - t0) / (t1 - t0 + TRANS))
    fr = kenburns(key, p, **kb)
    if key == "buffet":
        fr = fr.resize((270, 480), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4)).resize((W, H), Image.BILINEAR)
    fr.alpha_composite(overlay())
    return fr

def background(t):
    idx = max(i for i, s in enumerate(SCENES) if t >= s[0])
    fr = scene_frame(idx, t)
    if idx > 0 and t - SCENES[idx][0] < TRANS:     # fundido limpio
        q = ease_in_out((t - SCENES[idx][0]) / TRANS)
        fr = Image.blend(scene_frame(idx - 1, t), fr, q)
    fr.alpha_composite(top_shade())
    return fr

@lru_cache(None)
def top_shade():
    a = np.zeros((H, W), np.uint8)
    for y in range(520):
        a[y] = int(110 * (1 - y / 520) ** 1.5)
    g = Image.new("RGBA", (W, H), rgba(NAVY))
    g.putalpha(Image.fromarray(a))
    return g

# ---------------------------------------------------------------- subtítulos
def load_tokens():
    w = json.load(open(A("transcripcion_palabras.json")))
    merges = {34: (38, "$58.63"), 40: (41, "6%"), 74: (77, "$21.50"), 79: (81, "$23.68"),
              101: (104, "$6.53"), 142: (143, "$39")}
    toks, i = [], 0
    while i < len(w):
        x = w[i]
        if i in merges:
            j, txt = merges[i]
            p = w[j]["w"][-1] if w[j]["w"][-1] in ",." else ""
            toks.append([txt + p, x["s"], w[j]["e"]]); i = j + 1; continue
        if i == 67:  # Whisper omitió "caro." (verificado en segunda pasada)
            toks += [["caro.", 24.56, 25.14], ["El", 25.28, 25.46]]; i += 1; continue
        toks.append([x["w"].replace("diesel", "diésel"), x["s"], x["e"]]); i += 1
    return toks

KEY = {"cara", "más", "$58.63", "6%", "2022", "sube", "caro", "pavo", "16", "$21.50", "$23.68", "culpable",
       "diésel", "irán", "guerra", "récord", "$6.53", "septiembre", "leche", "pan", "papas", "arándanos", "10",
       "$39", "aldi", "compara"}
SUB_SIZE, SUB_Y = 80, 300

def norm(s): return s.lower().strip("¿?,.¡!")

def chunk_tokens(toks):
    f = font("Black", SUB_SIZE)
    chunks, cur = [], []
    for tok in toks:
        cand = cur + [tok]
        width = tw(" ".join(x[0].upper() for x in cand), f) + 34 * len(cand)
        gap = tok[1] - cur[-1][2] if cur else 0
        if cur and (width > 940 or len(cur) >= 4 or gap > .35 or cur[-1][0][-1] in ".?,"):
            chunks.append(cur); cur = [tok]
        else:
            cur = cand
    chunks.append(cur)
    out = []
    for n, c in enumerate(chunks):
        nxt = chunks[n + 1][0][1] - .06 if n + 1 < len(chunks) else NARR_DUR
        out.append((c[0][1] - .06, min(nxt, c[-1][2] + .7), c))
    return out

CHUNKS = chunk_tokens(load_tokens())

def draw_subs(base, t):
    cur = next((c for s, e, c in CHUNKS if s <= t < e), None)
    if not cur: return
    f = font("Black", SUB_SIZE)
    words = [x[0].upper() for x in cur]
    gap = tw(" ", f) + 34
    widths = [tw(s, f) for s in words]
    x = W / 2 - (sum(widths) + gap * (len(words) - 1)) / 2
    for (s, ws, we), wd, txt in zip(cur, widths, words):
        if t >= ws - .06:
            p = prog(t, ws - .06, .15)
            sc = lerp(.6, 1, ease_back(p, 2)) * (1.04 if ws - .06 <= t < max(we, ws + .18) else 1)
            col = RED if norm(s) in KEY else WHITE
            wl = Image.new("RGBA", (int(wd + 60), 170), (0, 0, 0, 0))
            ImageDraw.Draw(wl).text((30, 85), txt, font=f, fill=col, anchor="lm", stroke_width=10, stroke_fill=NAVY)
            paste(base, wl, x + wd / 2, SUB_Y, sc, clamp(p * 3))
        x += wd + gap

# ---------------------------------------------------------------- 1. gancho
@lru_cache(None)
def price_tag_sprite():
    w, h = 460, 220
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    o = 20
    pts = [(o + 85, o), (o + w, o), (o + w, o + h), (o + 85, o + h), (o, o + h / 2)]
    d = ImageDraw.Draw(im)
    d.polygon(pts, fill=RED, outline=WHITE, width=4)
    d.ellipse((o + 52, o + h / 2 - 18, o + 88, o + h / 2 + 18), fill=NAVY, outline=WHITE, width=4)
    text(d, (o + 240, o + h / 2 + 4), "PRECIO", font("Black", 70), WHITE)
    arrow(d, o + 400, o + h / 2, 96, WHITE)
    return im

@lru_cache(None)
def hook_sprite():
    f = font("Black", 116)
    w = tw("TU CENA SUBIÓ", f) + 90
    c, pad = card(w, 220, border=RED, bw=4)
    d = ImageDraw.Draw(c)
    x = pad + 45
    d.text((x, pad + 118), "TU CENA ", font=f, fill=WHITE, anchor="lm")
    d.text((x + tw("TU CENA ", f), pad + 118), "SUBIÓ", font=f, fill=RED, anchor="lm")
    return c

# ---------------------------------------------------------------- 2. el costo
@lru_cache(None)
def source_card():
    c, pad = card(940, 250)
    d = ImageDraw.Draw(c)
    c.alpha_composite(tag("FUENTE", 34), (pad + 40, pad + 34))
    d.text((pad + 40, pad + 140), "American Farm Bureau", font=font("ExtraBold", 58), fill=WHITE, anchor="lm")
    d.text((pad + 40, pad + 205), "Federation", font=font("ExtraBold", 58), fill=WHITE, anchor="lm")
    x0, y0 = pad + 800, pad + 50
    d.rounded_rectangle((x0, y0, x0 + 100, y0 + 140), 10, outline=WHITE, width=5)
    for k in range(4):
        d.line((x0 + 20, y0 + 35 + k * 26, x0 + 80 - (22 if k == 3 else 0), y0 + 35 + k * 26),
               fill=RED if k == 0 else WHITE, width=6)
    return c

@lru_cache(None)
def source_strip():
    f = font("SemiBold", 30)
    s = "American Farm Bureau Federation"
    tg = tag("FUENTE", 26)
    w = int(tw(s, f)) + tg.width + 70
    c, pad = card(w, 66, border=None, r=12)
    c.alpha_composite(tg, (pad + 16, pad + 33 - tg.height // 2))
    ImageDraw.Draw(c).text((pad + tg.width + 40, pad + 35), s, font=f, fill=WHITE, anchor="lm")
    return c

def person(d, cx, cy, s, col):
    lw = max(4, int(s * .09))
    d.ellipse((cx - s * .24, cy - s * .62, cx + s * .24, cy - s * .14), outline=col, width=lw)
    d.arc((cx - s * .44, cy - s * .02, cx + s * .44, cy + s * .82), 180, 360, fill=col, width=lw)

def table_card(t, t0):
    c, pad = card(940, 560)
    d = ImageDraw.Draw(c)
    cx, cy = pad + 470, pad + 235
    d.rounded_rectangle((cx - 230, cy - 78, cx + 230, cy + 78), 30, outline=WHITE, width=6)
    for k in range(4):
        for yy in (cy - 42, cy + 42):
            px = cx - 165 + k * 110
            d.ellipse((px - 20, yy - 20, px + 20, yy + 20), outline=GREY, width=4)
    seats = [(cx - 165 + k * 110, cy - 150) for k in range(4)] + [(cx + 315, cy)] + \
            [(cx + 165 - k * 110, cy + 145) for k in range(4)] + [(cx - 315, cy)]
    for n, (sx, sy) in enumerate(seats):
        p = prog(t, t0 + .12 * n, .25)
        if p > 0:
            person(d, sx, sy, 72 * ease_back(p), RED if n % 2 == 0 else WHITE)
    pl = prog(t, 10.2, .3)
    if pl > 0:
        lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        f = font("Black", 70)
        tot = tw("10 personas", f)
        dl.text((pad + 470 - tot / 2, pad + 485), "10 ", font=f, fill=RED, anchor="lm")
        dl.text((pad + 470 - tot / 2 + tw("10 ", f), pad + 485), "personas", font=f, fill=WHITE, anchor="lm")
        c.alpha_composite(scale_alpha(lay, pl))
    return c

def counter_card(t):
    c, pad = card(960, 450)
    d = ImageDraw.Draw(c)
    text(d, (pad + 480, pad + 66), "CENA DE THANKSGIVING · 10 PERSONAS", font("Bold", 36), GREY)
    v = 58.63 * ease_out(prog(t, 12.35, 2.25))
    sc = 1 + .06 * math.sin(clamp((t - 14.6) / .3) * math.pi)
    lay = Image.new("RGBA", (960, 250), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((480, 125), f"${v:.2f}", font=font("Black", 196), fill=RED, anchor="mm")
    paste(c, lay, pad + 480, pad + 235, sc)
    text(d, (pad + 480, pad + 390), "costo promedio en EE. UU.", font("SemiBold", 40), WHITE)
    return c

@lru_cache(None)
def pct_card():
    c, pad = card(780, 200, border=RED, bw=4)
    d = ImageDraw.Draw(c)
    arrow(d, pad + 115, pad + 100, 125, RED)
    d.text((pad + 205, pad + 106), "+6%", font=font("Black", 136), fill=RED, anchor="lm")
    d.text((pad + 545, pad + 75), "vs. el año", font=font("Bold", 38), fill=WHITE, anchor="lm")
    d.text((pad + 545, pad + 125), "pasado", font=font("Bold", 38), fill=WHITE, anchor="lm")
    return c

def timeline_card(t):
    c, pad = card(960, 680)
    d = ImageDraw.Draw(c)
    text(d, (pad + 480, pad + 66), "Precio de la cena, año por año", font("ExtraBold", 46), WHITE)
    years = [2022, 2023, 2024, 2025, 2026]
    ys = [.0, .35, .62, .86, .50]          # forma cualitativa: baja 3 años y sube en 2026
    x0, x1, top, bot = pad + 110, pad + 850, pad + 175, pad + 420
    pts = [(lerp(x0, x1, k / 4), lerp(top, bot, ys[k])) for k in range(5)]
    for k in range(4):
        y = lerp(top, bot, k / 3)
        d.line((x0 - 40, y, x1 + 40, y), fill=rgba(GREY, 40), width=2)
    d.line((x0 - 40, bot + 40, x1 + 40, bot + 40), fill=GREY, width=4)
    seg = ease_in_out(prog(t, 18.45, 1.9)) * 4
    for k in range(4):
        q = clamp(seg - k)
        if q <= 0: break
        a, b = pts[k], pts[k + 1]
        d.line((a, (lerp(a[0], b[0], q), lerp(a[1], b[1], q))), fill=RED if k == 3 else WHITE, width=12)
    for k, (x, y) in enumerate(pts):
        if seg >= k - .02:
            r = 20 if k in (0, 4) else 14
            d.ellipse((x - r, y - r, x + r, y + r), fill=RED if k == 4 else WHITE, outline=NAVY2, width=5)
        big = k in (0, 4)
        text(d, (x, bot + 90), str(years[k]), font("Black" if big else "SemiBold", 44 if big else 36),
             RED if k == 4 else (WHITE if big else GREY))
    if seg >= 4:
        q = prog(t, 18.45 + 1.9, .3)
        arrow(d, pts[4][0], pts[4][1] - 70, 56 * ease_back(q), RED)
    pb = prog(t, 21.1, .35)
    if pb > 0:
        tg = tag("PRIMERA SUBIDA DESDE 2022", 42)
        paste(c, tg, pad + 480, pad + 600, lerp(.7, 1, ease_back(pb)), clamp(pb * 3))
    return c

# ---------------------------------------------------------------- 3. el pavo
@lru_cache(None)
def turkey_src():
    im = ImageOps.exif_transpose(Image.open(A("img", IMG["pavo"]))).convert("RGB")
    return im.resize((int(im.width * 900 / im.height), 900), Image.LANCZOS)

def turkey_card(t):
    w, h = 700, 780
    ph = turkey_src()
    z = lerp(1.0, 1.08, prog(t, 22.3, 9))
    sc = max(w / ph.width, h / ph.height) * z
    rw, rh = w / sc, h / sc
    cx, cy = ph.width / 2, ph.height * .52
    crop = ph.resize((w, h), Image.BILINEAR, box=(cx - rw / 2, cy - rh / 2, cx + rw / 2, cy + rh / 2))
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).rectangle((20, 30, w + 20, h + 30), fill=140)
    im.paste(Image.new("RGBA", im.size, rgba(NAVY)), (0, 0), sh.filter(ImageFilter.GaussianBlur(12)))
    im.paste(crop, (20, 20))
    ImageDraw.Draw(im).rectangle((20, 20, w + 19, h + 19), outline=WHITE, width=4)   # marco blanco fino
    return im

def price_card(year, price, red, strike=0.0):
    w, h = 450, 150
    c, pad = card(w, h, border=RED if red else WHITE, bw=4)
    d = ImageDraw.Draw(c)
    d.text((pad + 34, pad + 42), year, font=font("Bold", 36), fill=GREY, anchor="lm")
    d.text((pad + 32, pad + 102), price, font=font("Black", 72), fill=RED if red else WHITE, anchor="lm")
    if red:
        arrow(d, pad + 390, pad + h / 2, 70, RED)
    if strike > 0:
        x0, x1 = pad + 24, pad + 330
        d.line((x0, pad + 125, lerp(x0, x1, strike), lerp(pad + 125, pad + 60, strike)), fill=RED, width=12)
    return c

# ---------------------------------------------------------------- 4. el culpable
@lru_cache(None)
def diesel_sprite():
    c, pad = card(740, 230, border=RED, bw=5)
    d = ImageDraw.Draw(c)
    gx, gy = pad + 115, pad + 118
    d.polygon([(gx, gy - 82), (gx - 50, gy + 2), (gx + 50, gy + 2)], fill=RED)
    d.ellipse((gx - 54, gy - 30, gx + 54, gy + 78), fill=RED)
    d.arc((gx - 30, gy + 4, gx + 10, gy + 50), 100, 200, fill=WHITE, width=6)
    text(d, (pad + 440, pad + 122), "DIÉSEL", font("Black", 150), WHITE)
    return c

@lru_cache(None)
def map_parts():
    g = json.load(open(A("geo", "world.json")))
    w, h = 960, 720
    lon0, lon1, lat0, lat1 = 24.0, 72.0, 11.0, 44.0
    my = lambda la: math.log(math.tan(math.pi / 4 + math.radians(la) / 2))
    c, pad = card(w, h, fill=NAVY)
    P = lambda lo, la: (pad + (lo - lon0) / (lon1 - lon0) * w,
                        pad + 40 + (1 - (my(la) - my(lat0)) / (my(lat1) - my(lat0))) * (h - 80))
    land = Image.new("RGBA", c.size, (0, 0, 0, 0))
    iran = Image.new("RGBA", c.size, (0, 0, 0, 0))
    dl, di = ImageDraw.Draw(land), ImageDraw.Draw(iran)
    for ft in g["features"]:
        geom = ft["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        isi = ft["properties"]["name"] == "Iran"
        for poly in polys:
            ring = [P(lo, la) for lo, la in poly[0]]
            if len(ring) < 3: continue
            if isi:
                di.polygon(ring, fill=RED, outline=WHITE, width=3)
            else:
                dl.polygon(ring, fill=NAVY2, outline=rgba(GREY, 150), width=2)
    mask = Image.new("L", c.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((pad + 3, pad + 3, pad + w - 3, pad + h - 3), 20, fill=255)
    l2 = Image.new("RGBA", c.size, (0, 0, 0, 0)); l2.paste(land, (0, 0), mask)
    i2 = Image.new("RGBA", c.size, (0, 0, 0, 0)); i2.paste(iran, (0, 0), mask)
    c.alpha_composite(l2)
    d = ImageDraw.Draw(c)
    for n, lo, la in [("IRAK", 43.5, 33), ("ARABIA SAUDITA", 44.5, 24), ("TURQUÍA", 33.5, 39.3),
                      ("AFGANISTÁN", 66, 34.5), ("PAKISTÁN", 68.5, 28), ("Golfo Pérsico", 51.5, 27)]:
        text(d, P(lo, la), n, font("SemiBold", 24), GREY)
    d.rounded_rectangle((pad, pad, pad + w, pad + h), 22, outline=WHITE, width=3)
    return c, i2, P(53.5, 32.6)

def map_card(t):
    base, iran, (ix, iy) = map_parts()
    c = base.copy()
    p = prog(t, 34.85, .35)
    if p > 0:
        pulse = .85 + .15 * (.5 + .5 * math.sin((t - 34.85) * 7))
        c.alpha_composite(scale_alpha(iran, clamp(p * 2) * pulse))
        paste(c, tag("IRÁN", 54), ix, iy, lerp(.6, 1, ease_back(p)), clamp(p * 3))
    return c

# línea del diésel: forma ilustrativa, sin valores intermedios
DIESEL_Y = [0.08, 0.15, 0.12, 0.30, 0.42, 0.37, 0.55, 0.63, 0.58, 0.75, 0.84, 1.0]
CHART_T0, CHART_DUR = 35.65, 1.9   # termina 37.55 → queda completo hasta 39.7

def chart_card(t):
    w, h = 960, 800
    c, pad = card(w, h)
    d = ImageDraw.Draw(c)
    d.text((pad + 44, pad + 60), "Precio del diésel por galón", font=font("ExtraBold", 44), fill=WHITE, anchor="lm")
    x0, x1, top, bot = pad + 60, pad + 820, pad + 330, pad + 660
    for k in range(5):
        y = lerp(top, bot, k / 4)
        d.line((x0, y, x1 + 60, y), fill=rgba(GREY, 35), width=2)
    d.line((x0, bot, x1 + 60, bot), fill=GREY, width=4)
    pts = [(lerp(x0, x1, k / (len(DIESEL_Y) - 1)), lerp(bot - 10, top, v)) for k, v in enumerate(DIESEL_Y)]
    n = ease_in_out(prog(t, CHART_T0, CHART_DUR)) * (len(pts) - 1)
    drawn = [pts[0]]
    for k in range(len(pts) - 1):
        q = clamp(n - k)
        if q <= 0: break
        a, b = pts[k], pts[k + 1]
        drawn.append((lerp(a[0], b[0], q), lerp(a[1], b[1], q)))
    if len(drawn) > 1:
        area = Image.new("RGBA", c.size, (0, 0, 0, 0))
        ImageDraw.Draw(area).polygon(drawn + [(drawn[-1][0], bot), (drawn[0][0], bot)], fill=rgba(RED, 55))
        c.alpha_composite(area)
        d = ImageDraw.Draw(c)
        d.line(drawn, fill=RED, width=10, joint="curve")
        ex, ey = drawn[-1]
        d.ellipse((ex - 11, ey - 11, ex + 11, ey + 11), fill=RED)
    d.text((x0, bot + 38), "Inicio de la guerra", font=font("SemiBold", 28), fill=GREY, anchor="lm")
    text(d, (x1, bot + 38), "Septiembre", font("Bold", 30), WHITE)
    d.text((pad + w - 36, pad + h - 30), "Fuente: AAA", font=font("SemiBold", 28), fill=GREY, anchor="rm")
    pr = prog(t, 37.12, .4)
    if pr > 0:
        ex, ey = pts[-1]
        lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        r = 24 * (1 + .35 * (.5 + .5 * math.sin((t - 37.12) * 8)))
        dl.ellipse((ex - r, ey - r, ex + r, ey + r), fill=rgba(RED, 90))
        dl.ellipse((ex - 18, ey - 18, ex + 18, ey + 18), fill=RED, outline=WHITE, width=5)
        bx0, by0, bx1, by1 = pad + 44, pad + 110, pad + 700, pad + 255
        dl.rounded_rectangle((bx0, by0, bx1, by1), 16, fill=NAVY, outline=RED, width=4)
        dl.line(((bx1, by0 + 70), (ex - 22, ey)), fill=RED, width=4)
        v = 6.53 * ease_out(prog(t, 37.12, 1.4))
        dl.text((bx0 + 28, by0 + 50), f"${v:.2f}/galón", font=font("Black", 64), fill=RED, anchor="lm")
        dl.text((bx0 + 28, by0 + 112), "– récord (septiembre)", font=font("Bold", 38), fill=WHITE, anchor="lm")
        paste(c, lay, c.width / 2, c.height / 2, 1, clamp(pr * 3))
    return c

# íconos lineales blanco + rojo
@lru_cache(None)
def icon(kind, s=150):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = s / 150
    lw = max(3, int(7 * k))
    P = lambda *xy: [v * k for v in xy]
    if kind == "leche":
        d.polygon(P(40, 48, 75, 16, 110, 48), outline=WHITE, width=lw)
        d.rectangle(P(60, 4, 90, 16), outline=WHITE, width=lw)
        d.rectangle(P(40, 48, 110, 145), outline=WHITE, width=lw)
        d.rectangle(P(48, 80, 102, 112), fill=RED)
    elif kind == "pan":
        d.rounded_rectangle(P(12, 50, 138, 128), 34 * k, outline=WHITE, width=lw)
        d.arc(P(14, 26, 136, 100), 180, 360, fill=WHITE, width=lw)
        for j in range(3):
            x = 48 + j * 28
            d.line(P(x, 52, x + 16, 76), fill=RED, width=lw)
    elif kind == "papas":
        for (x, y, rx, ry) in [(55, 98, 42, 30), (100, 82, 38, 28), (72, 58, 34, 25)]:
            d.ellipse(P(x - rx, y - ry, x + rx, y + ry), outline=WHITE, width=lw)
            d.ellipse(P(x - 6, y - 4, x + 2, y + 4), fill=RED)
    elif kind == "arandanos":
        d.line(P(75, 10, 75, 40), fill=WHITE, width=lw)
        d.line(P(75, 22, 100, 12), fill=WHITE, width=lw)
        for (x, y) in [(50, 72), (98, 70), (74, 108), (36, 110), (112, 108)]:
            d.ellipse(P(x - 23, y - 23, x + 23, y + 23), outline=RED, width=lw)
    return im

@lru_cache(None)
def truck_sprite():
    im = Image.new("RGBA", (720, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((14, 36, 476, 226), outline=WHITE, width=8)
    d.line((14, 180, 476, 180), fill=RED, width=10)
    text(d, (245, 110), "CARGA", font("Black", 62), WHITE)
    d.polygon([(492, 90), (620, 90), (690, 150), (690, 226), (492, 226)], outline=WHITE, width=8)
    d.polygon([(520, 108), (608, 108), (656, 150), (520, 150)], outline=GREY, width=5)
    for x in (110, 380, 600):
        d.ellipse((x - 44, 190, x + 44, 278), fill=NAVY2, outline=WHITE, width=8)
        d.ellipse((x - 12, 222, x + 12, 246), fill=RED)
    return im

INGREDIENTS = [("leche", "Leche", 41.62), ("pan", "Pan", 42.50), ("papas", "Papas", 43.30), ("arandanos", "Arándanos", 44.06)]

def truck_card(t):
    w, h = 960, 900
    c, pad = card(w, h)
    d = ImageDraw.Draw(c)
    f = font("ExtraBold", 44)
    s = "Transportar cuesta más"
    d.text((pad + w / 2 - (tw(s, f) + 60) / 2, pad + 66), s, font=f, fill=WHITE, anchor="lm")
    arrow(d, pad + w / 2 + (tw(s, f) + 60) / 2 - 22, pad + 66, 52, RED)
    drive = ease_in_out(prog(t, 44.5, .5)) * 720
    tx, ty = pad + 470 + drive, pad + 690 + 3 * math.sin(t * 18)
    tr = truck_sprite()
    c.alpha_composite(tr, (int(tx - tr.width / 2), int(ty - tr.height / 2)))
    for n, (kind, name, t0) in enumerate(INGREDIENTS):
        if t < t0 - .05: continue
        sx, sy = pad + 140 + n * 227, pad + 250
        dx, dy = tx - 285 + n * 95, ty - 150
        pj = ease_in_out(prog(t, t0 + .45, .45))
        x, y = lerp(sx, dx, pj), lerp(sy, dy, pj) - math.sin(pj * math.pi) * 150
        paste(c, icon(kind), x, y, lerp(1, .62, pj) * ease_back(prog(t, t0 - .05, .3)))
        lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        fl = font("ExtraBold", 36)
        wl = tw(name, fl)
        dl.text((sx - (wl + 40) / 2, sy + 115), name, font=fl, fill=WHITE, anchor="lm")
        arrow(dl, sx + (wl + 40) / 2 - 14, sy + 112, 38, RED)
        paste(c, lay, c.width / 2, c.height / 2, 1, clamp(prog(t, t0, .25) * 3))
    return c

# ---------------------------------------------------------------- 5. la salida
@lru_cache(None)
def store_card():
    c, pad = card(880, 240)
    d = ImageDraw.Draw(c)
    x0, y0 = pad + 40, pad + 40
    for k in range(5):
        d.rectangle((x0 + k * 34, y0, x0 + k * 34 + 34, y0 + 48), fill=RED if k % 2 == 0 else NAVY2, outline=WHITE, width=3)
    d.rectangle((x0 + 8, y0 + 48, x0 + 162, y0 + 160), outline=WHITE, width=6)
    d.rectangle((x0 + 62, y0 + 92, x0 + 108, y0 + 160), outline=WHITE, width=5)
    d.text((pad + 250, pad + 90), "Algunas tiendas", font=font("ExtraBold", 50), fill=WHITE, anchor="lm")
    d.text((pad + 250, pad + 155), "bajan precios", font=font("ExtraBold", 50), fill=WHITE, anchor="lm")
    arrow(d, pad + 250 + tw("bajan precios", font("ExtraBold", 50)) + 48, pad + 155, 62, WHITE, down=True)
    return c

@lru_cache(None)
def piggy(s=170):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = s / 170
    lw = int(7 * k)
    P = lambda *xy: [v * k for v in xy]
    d.ellipse(P(62, 2, 104, 44), outline=GREEN, width=lw)
    text(d, (83 * k, 24 * k), "$", font("Black", int(26 * k)), GREEN)
    for x in (40, 108):
        d.line(P(x + 10, 128, x + 10, 158), fill=WHITE, width=lw)
    d.ellipse(P(12, 54, 158, 144), outline=WHITE, width=lw)
    d.polygon(P(42, 64, 56, 34, 72, 60), outline=WHITE, width=lw)
    d.ellipse(P(136, 82, 166, 114), outline=WHITE, width=lw)
    d.line(P(70, 60, 98, 60), fill=GREEN, width=lw)
    d.ellipse(P(110, 76, 120, 86), fill=WHITE)
    return im

def compare_card(t):
    w, h = 960, 800
    c, pad = card(w, h)
    d = ImageDraw.Draw(c)
    text(d, (pad + w / 2, pad + 62), "Cena para 10 personas", font("ExtraBold", 46), WHITE)
    base_y, maxh = pad + 640, 400
    for cx, name, val, col, t0, t1 in [(pad + 260, "Promedio", 58.63, RED, 49.50, 50.6),
                                       (pad + 700, "Aldi", 39.0, GREEN, 53.40, 54.2)]:
        if t < t0: continue
        p = ease_out(prog(t, t0, t1 - t0))
        bh = maxh * val / 58.63 * p
        d.rounded_rectangle((cx - 120, base_y - bh, cx + 120, base_y), 10, fill=col)
        s = f"${val * p:.2f}" if name == "Promedio" else f"${val * p:.0f}"
        text(d, (cx, base_y - bh - 55), s, font("Black", 84), col)
        text(d, (cx, base_y + 50), name, font("ExtraBold", 50), WHITE)
    d.line((pad + 80, base_y, pad + w - 80, base_y), fill=GREY, width=4)
    pp = prog(t, 54.25, .4)
    if pp > 0:
        paste(c, piggy(150), pad + 870, pad + 185, ease_back(pp), clamp(pp * 3),
              rot=8 * math.sin((t - 54.25) * 4) * (1 - prog(t, 54.25, 1.5)))
    return c

@lru_cache(None)
def cta_card():
    c, pad = card(960, 250, border=RED, bw=4)
    d = ImageDraw.Draw(c)
    f = font("Black", 84)
    text(d, (pad + 480, pad + 82), "COMPARA ANTES", f, WHITE)
    text(d, (pad + 480, pad + 178), "DE COMPRAR", f, WHITE)
    return c

# ---------------------------------------------------------------- 6. cierre
POLL = [("Pernil", 58.05), ("Arroz con gandules", 58.40), ("Tamales", 58.75), ("Otro", 59.10)]

def poll_card(t):
    w, h = 960, 860
    c, pad = card(w, h)
    d = ImageDraw.Draw(c)
    tg = tag("ENCUESTA", 38)
    c.alpha_composite(tg, (int(pad + w / 2 - tg.width / 2), pad + 40))
    text(d, (pad + 480, pad + 170), "¿Qué plato latino no", font("ExtraBold", 54), WHITE)
    text(d, (pad + 480, pad + 240), "falta en tu mesa?", font("ExtraBold", 54), WHITE)
    hi = int((t - 59.5) / .55) % 4 if t > 59.5 else -1
    for n, (name, t0) in enumerate(POLL):
        p = prog(t, t0, .3)
        if p <= 0: continue
        lay = Image.new("RGBA", (880, 124), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        on = n == hi
        dl.rounded_rectangle((0, 6, 879, 116), 14, fill=NAVY, outline=RED if on else rgba(GREY, 160), width=4)
        dl.text((36, 62), f"{chr(65 + n)}", font=font("Black", 46), fill=RED, anchor="lm")
        dl.text((96, 62), name, font=font("ExtraBold", 48), fill=WHITE, anchor="lm")
        dl.ellipse((796, 36, 846, 86), outline=WHITE, width=5)
        if on: dl.ellipse((808, 48, 834, 74), fill=RED)
        paste(c, lay, pad + 480 + (1 - ease_out(p)) * 200, pad + 340 + n * 128, 1, clamp(p * 2))
    return c

@lru_cache(None)
def share_icon(s=180):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((2, 2, s - 3, s - 3), fill=RED, outline=WHITE, width=4)
    k = s / 190
    pts = [(62 * k, 95 * k), (128 * k, 58 * k), (128 * k, 132 * k)]
    d.line((pts[0], pts[1]), fill=WHITE, width=int(11 * k))
    d.line((pts[0], pts[2]), fill=WHITE, width=int(11 * k))
    for x, y in pts:
        d.ellipse((x - 21 * k, y - 21 * k, x + 21 * k, y + 21 * k), fill=WHITE)
    return im

# --- cierre animado de la marca, recoloreado a la paleta oficial
_CLOSE = None

def closing_frames():
    """Descompone cada píxel del clip original en fondo/rojo/blanco y lo recompone con #0B1F3A/#C8102E/#FFFFFF."""
    global _CLOSE
    cache = os.path.join(BUILD, "cierre_oficial.npy")
    if _CLOSE is None and os.path.exists(cache):
        _CLOSE = np.load(cache, mmap_mode="r")
    if _CLOSE is None:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", A("cierre_capital_curioso.mp4"), "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3).astype(np.float32)
        bg0, red0, wh0 = np.array([10, 40, 90.]), np.array([254, 74, 85.]), np.array([255, 255, 255.])
        M = np.stack([red0 - bg0, wh0 - bg0], 1)        # 3x2
        Mp = np.linalg.pinv(M)                           # 2x3
        bg1, red1, wh1 = np.array(NAVY, float), np.array(RED, float), np.array(WHITE, float)
        M1 = np.stack([red1 - bg1, wh1 - bg1], 1)
        out = []
        for f in fr:
            coef = np.clip((f - bg0) @ Mp.T, 0, 1)
            out.append(np.clip(bg1 + coef @ M1.T, 0, 255).astype(np.uint8))
        np.save(cache, np.stack(out))
        _CLOSE = np.load(cache, mmap_mode="r")
    return _CLOSE

# ---------------------------------------------------------------- composición
def frame(fi):
    t = fi / FPS
    if t >= CLOSE_START:
        cf = closing_frames()
        k = min(int((t - CLOSE_START) * CLOSE_SPEED * FPS), len(cf) - 1)
        base = Image.fromarray(cf[k]).convert("RGBA")
        q = prog(t, CLOSE_START, .25)
        if q < 1:
            base = Image.blend(frame_body(CLOSE_START - .001), base, q)
        share_overlay(base, t)
        draw_subs(base, t)
        return base.convert("RGB")
    base = frame_body(t)
    draw_subs(base, t)
    return base.convert("RGB")

def frame_body(t):
    base = background(t)
    # 1) gancho
    if t < 6.0:
        p = ease_out(prog(t, .25, 2.75))
        a = 1 - prog(t, 5.45, .25)
        paste(base, price_tag_sprite(), 560, lerp(1700, 840, p), lerp(.7, 1, p),
              clamp(prog(t, .25, .2)) * a, rot=6 + (3 * math.sin(t * 6) if t > 3 else 0))
        pop(base, hook_sprite(), W / 2, 1290, t, 2.28, 5.45)
    # 2) el costo
    if 5.6 <= t < 22.6:
        slide(base, source_card(), W / 2, 640, t, 5.74, 12.05, dx=-W, dy=0, out_dy=-100)
        if 8.5 <= t < 12.4:
            slide(base, table_card(t, 8.62), W / 2, 1150, t, 8.50, 12.05, dy=150, out_dy=-100)
        slide(base, source_strip(), W / 2, 1610, t, 12.1, 22.05, dy=60, out_dy=40)
        if 12.1 <= t < 18.7:
            slide(base, counter_card(t), W / 2, 860, t, 12.15, 18.30, dy=150, out_dy=-120)
            pop(base, pct_card(), W / 2, 1290, t, 15.98, 18.30)
        if 18.2 <= t < 22.6:
            slide(base, timeline_card(t), W / 2, 1030, t, 18.32, 22.05, dy=150, out_dy=-100)
    # 3) el pavo
    if 22.3 <= t < 31.6:
        slide(base, turkey_card(t), W / 2, 890, t, 22.40, 31.05, dy=200, out_dy=-100)
        pop(base, pill("Pavo de 16 libras", 46), W / 2, 1325, t, 25.95, 31.05)
        if t >= 27.4:
            slide(base, price_card("2025", "$21.50", False, ease_out(prog(t, 28.95, .35))), 300, 1500, t,
                  27.42, 31.05, dx=-200, dy=0)
        pop(base, price_card("2026", "$23.68", True), 790, 1500, t, 29.40, 31.05)
    # 4) el culpable
    if 31.3 <= t < 33.9:
        pop(base, tag("¿EL CULPABLE?", 52), W / 2, 860, t, 31.55, 33.55)
        pop(base, diesel_sprite(), W / 2, 1100, t, 32.80, 33.55, rot=-3)
    if 33.6 <= t < 35.8:
        slide(base, map_card(t), W / 2, 1010, t, 33.65, 35.45, dy=150, out_dx=-W, out_dy=0)
        pop(base, pill("Guerra de Irán", 46, border=RED), W / 2, 1450, t, 34.55, 35.45)
    if 35.4 <= t < 40.2:
        slide(base, chart_card(t), W / 2, 1010, t, 35.45, 39.70, dx=W, dy=0, out_dy=-100)
    if 39.8 <= t < 45.1:
        slide(base, truck_card(t), W / 2, 1060, t, 39.90, 44.75, dy=150, out_dy=-100)
    # 5) la salida
    if 44.8 <= t < 57.3:
        slide(base, store_card(), W / 2, 760, t, 46.20, 49.25, dx=-W, dy=0, out_dy=-100)
        if t >= 49.3:
            slide(base, compare_card(t), W / 2, 930, t, 49.40, 56.95, dy=160, out_dy=-100)
        pop(base, cta_card(), W / 2, 1500, t, 54.62, 56.95)
    # 6) encuesta + compartir
    if t >= 57.0:
        slide(base, poll_card(t), W / 2, 940, t, 57.85, 1e9, dy=160)
        share_overlay(base, t)
    return base

def share_overlay(base, t):
    if t < 61.4: return
    y = 1530 if t < CLOSE_START else 1640
    b = abs(math.sin((t - 61.4) * 6)) * 32
    pop(base, share_icon(), 330, y - b, t, 61.40)
    pop(base, pill("¡Compártelo!", 54, border=RED, wgt="Black"), 670, y, t, 61.60)

def render_bytes(fi):
    return frame(fi).tobytes()

# ---------------------------------------------------------------- audio
SR = 48000

def fx_pop():
    t = np.arange(int(SR * .12)) / SR
    ph = 2 * np.pi * np.cumsum(950 * np.exp(-t * 28) + 260) / SR
    return (np.sin(ph) * np.exp(-t * 38) * (1 - np.exp(-t * 900)) * .55).astype(np.float32)

def fx_cash():
    rng = np.random.default_rng(3)
    n = int(SR * 1.1); t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for off in (0.0, .045):
        i0, m = int(off * SR), int(.03 * SR)
        out[i0:i0 + m] += (rng.standard_normal(m) * np.exp(-np.arange(m) / SR * 160) * .35).astype(np.float32)
    tb = t - .09
    bell = sum(a * np.sin(2 * np.pi * f * tb) * np.exp(-tb * dcy)
               for f, a, dcy in [(2093, .5, 5), (2637, .35, 6), (3136, .25, 7), (4186, .15, 9), (5274, .08, 11)])
    return out + (bell * (tb > 0) * .32).astype(np.float32)

def fx_whoosh():
    rng = np.random.default_rng(7)
    n = int(SR * .3); t = np.arange(n) / SR
    nz = rng.standard_normal(n); y = np.zeros(n); a = 0
    for i in range(n):
        a += (.05 + .25 * i / n) * (nz[i] - a); y[i] = a
    return (y * np.sin(np.pi * t / .3) ** 2 * .22).astype(np.float32)

def build_audio():
    total = TOTAL_FRAMES / FPS
    n = int(total * SR)
    def load(p):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.float32).reshape(-1, 2)
    voice = load(A("audio", "narracion.mp3"))[:n]
    music = load(A("audio", "musica_local_forecast_kevin_macleod.mp3"))[:n].copy()
    sm = np.convolve(np.abs(voice[:, 0]), np.ones(int(.25 * SR)) / int(.25 * SR), mode="same")
    duck = 1 - .35 * np.clip(sm / .03, 0, 1)
    duck = np.pad(duck, (0, max(0, len(music) - len(duck))), constant_values=1)[:len(music)]
    tt = np.arange(len(music)) / SR
    fade = np.clip(tt / .8, 0, 1) * np.clip((total - tt) / 1.2, 0, 1)
    music *= (10 ** (-15 / 20) * duck * fade)[:, None]     # pista base suave (≈-24 dB RMS) → fondo bajo
    mix = np.zeros((n, 2), np.float32)
    mix[:len(music)] += music
    mix[:len(voice)] += voice
    fx = {"pop": fx_pop() * .5, "cash": fx_cash() * .55, "whoosh": fx_whoosh() * .3}
    cues = [("whoosh", .2), ("pop", 2.30), ("whoosh", 5.62), ("pop", 5.80), ("pop", 10.22), ("pop", 12.40),
            ("cash", 14.55), ("pop", 16.00), ("whoosh", 18.30), ("pop", 21.10), ("whoosh", 22.30), ("pop", 26.00),
            ("cash", 27.45), ("cash", 29.42), ("whoosh", 31.30), ("pop", 32.82), ("whoosh", 33.62), ("pop", 34.88),
            ("whoosh", 35.45), ("pop", 37.12), ("cash", 38.55), ("whoosh", 39.86), ("pop", 41.62), ("pop", 42.50),
            ("pop", 43.30), ("pop", 44.06), ("whoosh", 44.80), ("pop", 46.22), ("pop", 49.45), ("cash", 54.15),
            ("pop", 54.62), ("whoosh", 57.00), ("pop", 57.86), ("pop", 61.42), ("whoosh", 62.0)]
    for name, at in cues:
        s = fx[name]; i0 = int(at * SR)
        e = min(n, i0 + len(s))
        mix[i0:e] += s[:e - i0, None]
    mix *= min(1, .98 / np.abs(mix).max())
    path = os.path.join(BUILD, "mezcla_oficial.wav")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((mix * 32767).astype(np.int16).tobytes())
    return path

def main():
    if "--stills" in sys.argv:
        out = os.path.join(BUILD, "stills_oficial"); os.makedirs(out, exist_ok=True)
        for t in [float(x) for x in sys.argv[sys.argv.index("--stills") + 1:]]:
            frame(round(t * FPS)).save(os.path.join(out, f"t{t:05.2f}.jpg"), quality=88)
        return
    closing_frames()   # precalcula el cierre recoloreado una sola vez
    audio = build_audio()
    out = os.path.join(BUILD, "capital_curioso_thanksgiving_oficial.mp4")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                           "-t", f"{TOTAL_FRAMES / FPS:.4f}", out], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for k, b in enumerate(pool.imap(render_bytes, range(TOTAL_FRAMES), chunksize=4)):
            ff.stdin.write(b)
            if k % 300 == 0: print(f"{k}/{TOTAL_FRAMES}", flush=True)
    ff.stdin.close(); ff.wait()
    print("OK", out)

if __name__ == "__main__":
    main()
