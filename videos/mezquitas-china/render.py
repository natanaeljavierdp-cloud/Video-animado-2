"""Video vertical 9:16 — Capital Curioso: las mezquitas en China.

Uso:
    python3 render.py            # render completo -> build/video_sin_audio.mp4
    python3 render.py --still 12.5 23.4   # fotogramas de prueba en build/stills/
"""
import json
import math
import os
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(HERE, "assets", *p)  # noqa: E731
B = lambda *p: os.path.join(HERE, "build", *p)  # noqa: E731

W, H, FPS = 1080, 1920, 30
BAR = 165                       # barras de cine
INTRO_T = 66.70                 # empieza el cierre de Capital Curioso
INTRO_LEN = 3.5
T_END = INTRO_T + INTRO_LEN
NFRAMES = int(round(T_END * FPS))

NAVY = (10, 40, 90)
NAVY_D = (5, 16, 38)
RED = (254, 74, 85)
WHITE = (245, 247, 250)
GRAY = (150, 160, 175)

# ------------------------------------------------------------------ utilidades
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lin(t, a, b):
    return clamp((t - a) / (b - a)) if b != a else float(t >= a)


def eo(x):  # ease out cubic
    x = clamp(x)
    return 1 - (1 - x) ** 3


def eio(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def eback(x, s=1.7):
    x = clamp(x)
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


@lru_cache(None)
def font(name, size):
    return ImageFont.truetype(A("fonts", name), size)


F_ANTON = "Anton.woff"
F_P5, F_P7, F_P8, F_P9 = "Poppins-500.woff", "Poppins-700.woff", "Poppins-800.woff", "Poppins-900.woff"
F_ELITE = "Elite.woff"
F_SERIF, F_SERIF_I = "Playfair-700.woff", "Playfair-700i.woff"


@lru_cache(4096)
def text_img(text, fname, size, fill=WHITE, stroke=0, stroke_fill=(0, 0, 0), shadow=0, spacing=0):
    f = font(fname, size)
    if spacing:
        widths = [f.getlength(c) for c in text]
        tw = int(sum(widths) + spacing * (len(text) - 1))
    else:
        tw = int(f.getlength(text))
    asc, desc = f.getmetrics()
    pad = stroke + shadow * 2 + 6
    im = Image.new("RGBA", (tw + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def draw(dx, dy, col, sw, sf):
        if spacing:
            x = pad + dx
            for c, w_ in zip(text, widths):
                d.text((x, pad + dy), c, font=f, fill=col, stroke_width=sw, stroke_fill=sf)
                x += w_ + spacing
        else:
            d.text((pad + dx, pad + dy), text, font=f, fill=col, stroke_width=sw, stroke_fill=sf)

    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d2 = ImageDraw.Draw(sh)
        d2.text((pad, pad + shadow), text, font=f, fill=(0, 0, 0, 200), stroke_width=stroke, stroke_fill=(0, 0, 0, 200))
        sh = sh.filter(ImageFilter.GaussianBlur(shadow))
        im = Image.alpha_composite(im, sh)
        d = ImageDraw.Draw(im)
    draw(0, 0, fill, stroke, stroke_fill)
    bb = im.getbbox() or (0, 0, 1, 1)
    # recorte horizontal solamente; vertical fijo para alinear líneas
    return im.crop((bb[0], 0, bb[2], im.size[1]))


def with_alpha(im, a):
    if a >= 0.999:
        return im
    im = im.copy()
    al = im.getchannel("A").point(lambda v: int(v * a))
    im.putalpha(al)
    return im


def paste(base, im, cx, cy, scale=1.0, alpha=1.0, anchor="c", rot=0.0):
    if alpha <= 0.003 or scale <= 0.01:
        return
    if abs(scale - 1) > 0.003:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    im = with_alpha(im, alpha)
    if anchor == "c":
        x, y = cx - im.width // 2, cy - im.height // 2
    elif anchor == "l":
        x, y = cx, cy - im.height // 2
    elif anchor == "r":
        x, y = cx - im.width, cy - im.height // 2
    else:
        x, y = cx, cy
    x, y = int(x), int(y)
    # recorte para alpha_composite (no admite destino negativo)
    sx, sy = max(0, -x), max(0, -y)
    if sx or sy:
        im = im.crop((sx, sy, im.width, im.height))
        x, y = x + sx, y + sy
    if x >= base.width or y >= base.height or im.width <= 0 or im.height <= 0:
        return
    base.alpha_composite(im, (x, y))


def rect_layer(w, h, fill, radius=0, outline=None, width=0):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=fill, outline=outline, width=width)
    return im


def overlay_fill(base, color, alpha):
    if alpha <= 0:
        return
    base.alpha_composite(Image.new("RGBA", base.size, color + (int(255 * clamp(alpha)),)))


# ------------------------------------------------------------------ fotos
def grade(im, sat=0.5, dark=0.85, tint=(0.93, 1.0, 1.08)):
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    a = lum[..., None] * (1 - sat) + a * sat
    a = a * np.array(tint, np.float32)
    a = 128 + (a - 128) * 1.08
    a *= dark
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


@lru_cache(None)
def photo(name, cover_w=W, cover_h=H, over=1.25, sat=0.5, dark=0.85, blur=0):
    im = Image.open(A("fotos", name)).convert("RGB")
    s = max(cover_w * over / im.width, cover_h * over / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    im = grade(im, sat, dark)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return im


def kenburns(src, out_w, out_h, z, fx, fy):
    """z: zoom (1 = cubrir justo), fx, fy: centro 0..1 dentro de la imagen."""
    base = min(src.width / out_w, src.height / out_h)
    cw, ch = out_w * base / z, out_h * base / z
    cx = clamp(fx, 0, 1) * src.width
    cy = clamp(fy, 0, 1) * src.height
    x0 = clamp(cx - cw / 2, 0, src.width - cw)
    y0 = clamp(cy - ch / 2, 0, src.height - ch)
    sc = cw / out_w
    return src.transform((out_w, out_h), Image.AFFINE, (sc, 0, x0, 0, sc, y0), resample=Image.BILINEAR).convert("RGBA")


# ------------------------------------------------------------------ palabras / subtítulos
FIX = {"mesquitas": "mezquitas", "mesquita": "mezquita", "Shadyan": "Shadian", "huigures": "uigures"}
KEY = {"cúpula", "miles", "mezquitas", "2016", "xi", "jinping", "sinización", "borrar", "extranjera",
       "alteradas", "cerradas", "demolidas", "minarete", "media", "luna", "escritura", "árabe", "pagodas",
       "shadian", "2019", "infectados", "virus", "extremismo", "curarse", "sars", "terrorismo",
       "difamación", "fe", "chinas", "nadie"}


def load_words():
    ws = json.load(open(A("palabras.json")))
    out = []
    for w in ws:
        txt = w["w"]
        core = txt.strip(",.¿?")
        if core in FIX:
            txt = txt.replace(core, FIX[core])
        out.append(dict(w=txt, s=w["s"], e=w["e"], key=txt.strip(",.").lower() in KEY))
    return out


WORDS = load_words()


def build_chunks():
    chunks, cur = [], []
    for i, w in enumerate(WORDS):
        cur.append(w)
        nxt = WORDS[i + 1] if i + 1 < len(WORDS) else None
        chars = sum(len(x["w"]) + 1 for x in cur)
        brk = (w["w"][-1] in ",." or len(cur) >= 3 or chars > 16 or nxt is None
               or (nxt and nxt["s"] - w["e"] > 0.45))
        if nxt and len(cur) < 3 and chars + len(nxt["w"]) < 13 and w["w"][-1] not in ",." and nxt["s"] - w["e"] < 0.3:
            brk = False
        if brk:
            chunks.append(cur)
            cur = []
    res = []
    for i, c in enumerate(chunks):
        start = c[0]["s"] - 0.05
        end = chunks[i + 1][0]["s"] - 0.05 if i + 1 < len(chunks) else c[-1]["e"] + 0.5
        end = min(end, c[-1]["e"] + 0.7)
        res.append((start, end, c))
    return res


CHUNKS = build_chunks()
CAPTION_OFF = [(37.0, 38.45), (53.1, 54.38), (61.3, 99)]
CAP_Y = 1600


def draw_captions(base, t):
    if any(a <= t < b for a, b in CAPTION_OFF):
        return
    for start, end, c in CHUNKS:
        if start <= t < end:
            break
    else:
        return
    size = 64
    imgs = []
    for w in c:
        txt = w["w"].upper()
        col = RED if w["key"] else WHITE
        imgs.append(text_img(txt, F_P9, size, col, stroke=7, stroke_fill=(5, 10, 20), shadow=0))
    gap = 18
    total = sum(i.width for i in imgs) + gap * (len(imgs) - 1)
    scale_fit = min(1.0, 980 / total)
    x = W / 2 - total * scale_fit / 2
    out_a = 1 - lin(t, end - 0.12, end)
    for w, im in zip(c, imgs):
        p = lin(t, w["s"] - 0.04, w["s"] + 0.14)
        if p > 0:
            sc = (1.25 - 0.25 * eo(p)) * scale_fit
            paste(base, im, x + im.width * scale_fit / 2, CAP_Y, sc, min(1, p * 1.6) * out_a)
        x += (im.width + gap) * scale_fit


# ------------------------------------------------------------------ elementos periodísticos
def lower_third(base, t, t0, l1, l2, y, t1=None, x=70):
    p = eo(lin(t, t0, t0 + 0.45))
    if t1 is not None:
        p *= 1 - eio(lin(t, t1, t1 + 0.35))
    if p <= 0:
        return
    i1 = text_img(l1, F_P8, 50, WHITE)
    i2 = text_img(l2, F_P5, 32, (190, 205, 230)) if l2 else None
    bw = max(i1.width, i2.width if i2 else 0) + 70
    bh = 150 if i2 else 100
    w_ = int(bw * p)
    if w_ > 4:
        box = rect_layer(w_, bh, NAVY + (235,), radius=6)
        paste(base, box, x + 14, y, anchor="tl")
        sub = Image.new("RGBA", (w_, bh), (0, 0, 0, 0))
        paste(sub, i1, 34, 18 + i1.height // 2 - 8, anchor="l", alpha=lin(t, t0 + 0.2, t0 + 0.5))
        if i2:
            paste(sub, i2, 36, 98, anchor="l", alpha=lin(t, t0 + 0.3, t0 + 0.6))
        paste(base, sub, x + 14, y, anchor="tl")
    paste(base, rect_layer(14, bh, RED + (255,)), x, y, anchor="tl", alpha=min(1, p * 3))


def source_card(base, t, t0, name, sub, y, t1=None):
    p = eo(lin(t, t0, t0 + 0.5))
    if t1 is not None:
        p *= 1 - eio(lin(t, t1, t1 + 0.3))
    if p <= 0:
        return
    i1 = text_img(name, F_SERIF, 50, (20, 22, 28))
    i2 = text_img(sub, F_P7, 28, (90, 98, 112))
    bw = max(i1.width, i2.width) + 90
    card = rect_layer(bw, 140, (238, 240, 243, 245), radius=8)
    paste(card, rect_layer(10, 140, RED + (255,)), 0, 0, anchor="tl")
    # comillas
    paste(card, text_img("“", F_SERIF, 90, RED), bw - 52, 52)
    paste(card, i1, 38, 50, anchor="l")
    paste(card, i2, 40, 104, anchor="l")
    xoff = (1 - p) * -120
    paste(base, card, W / 2 + xoff, y, alpha=p)


def pin_icon(size=60, col=RED):
    im = Image.new("RGBA", (size * 4, size * 5), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size * 4
    d.ellipse((0, 0, s, s), fill=col)
    d.polygon([(s * 0.14, s * 0.72), (s * 0.86, s * 0.72), (s / 2, s * 1.22)], fill=col)
    d.ellipse((s * 0.32, s * 0.32, s * 0.68, s * 0.68), fill=(255, 255, 255))
    return im.resize((size, int(size * 1.25)), Image.LANCZOS)


# ------------------------------------------------------------------ mapa
MAP = json.load(open(A("mapa_asia.json")))
LON0, LON1, LAT0, LAT1 = 70.0, 138.0, 16.0, 55.0


def proj_factory(width, ox, oy):
    sx = width / (LON1 - LON0)
    sy = sx / math.cos(math.radians(36))
    return lambda lon, lat: (ox + (lon - LON0) * sx, oy + (LAT1 - lat) * sy), (LAT1 - LAT0) * sy


@lru_cache(None)
def map_layers(width=1000, ss=2):
    """Devuelve (vecinos, china_relleno, china_contorno, glow, alto, proj)."""
    proj, hh = proj_factory(width * ss, 0, 0)
    size = (width * ss, int(hh) + 2)
    nb = Image.new("RGBA", size, (0, 0, 0, 0))
    cf = Image.new("RGBA", size, (0, 0, 0, 0))
    co = Image.new("RGBA", size, (0, 0, 0, 0))
    dn, dc, do = ImageDraw.Draw(nb), ImageDraw.Draw(cf), ImageDraw.Draw(co)
    for name, rings in MAP.items():
        china = name in ("China", "Hong Kong", "Macao")
        for r in rings:
            pts = [proj(x, y) for x, y in r]
            if len(pts) < 3:
                continue
            if china:
                dc.polygon(pts, fill=RED + (255,))
                do.line(pts + [pts[0]], fill=(255, 190, 195, 255), width=3 * ss)
            else:
                dn.polygon(pts, fill=(18, 36, 68, 255), outline=(52, 82, 130, 255))
    small = lambda im: im.resize((width, int(size[1] / ss)), Image.LANCZOS)  # noqa: E731
    nb, cf, co = small(nb), small(cf), small(co)
    yy, xx = np.mgrid[0:nb.height, 0:nb.width].astype(np.float32)
    fx = np.clip(np.minimum(xx, nb.width - xx) / (nb.width * 0.12), 0, 1)
    fy = np.clip(np.minimum(yy, nb.height - yy) / (nb.height * 0.14), 0, 1)
    nb.putalpha(Image.fromarray((np.asarray(nb.getchannel("A")) * fx * fy).astype(np.uint8)))
    glow = cf.filter(ImageFilter.GaussianBlur(22))
    proj1, _ = proj_factory(width, 0, 0)
    return nb, cf, co, glow, nb.height, proj1


# ------------------------------------------------------------------ ilustraciones vectoriales
SS = 2


def _layer(w, h):
    return Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))


def _down(im):
    return im.resize((im.width // SS, im.height // SS), Image.LANCZOS)


LINE = (210, 222, 240, 255)
FILL = (22, 48, 92, 255)
FILL2 = (30, 62, 115, 255)


@lru_cache(None)
def mosque_parts(w=1000, h=620):
    """Mezquita esquemática: partes separadas para animarlas."""
    s = SS
    cx = w / 2 * s
    ground = (h - 30) * s
    parts = {}
    # base
    im = _layer(w, h)
    d = ImageDraw.Draw(im)
    bx0, bx1, by0 = cx - 260 * s, cx + 260 * s, ground - 250 * s
    d.rectangle((bx0, by0, bx1, ground), fill=FILL, outline=LINE, width=4 * s)
    # arcos
    for i in range(5):
        ax = bx0 + (60 + i * 100) * s
        d.rectangle((ax - 26 * s, ground - 120 * s, ax + 26 * s, ground), fill=NAVY_D + (255,), outline=LINE, width=3 * s)
        d.pieslice((ax - 26 * s, ground - 150 * s, ax + 26 * s, ground - 90 * s), 180, 360, fill=NAVY_D + (255,), outline=LINE, width=3 * s)
    d.line((bx0 - 40 * s, ground, bx1 + 40 * s, ground), fill=LINE, width=4 * s)
    parts["base"] = _down(im)
    # tambor + cúpula
    im = _layer(w, h)
    d = ImageDraw.Draw(im)
    d.rectangle((cx - 120 * s, by0 - 50 * s, cx + 120 * s, by0), fill=FILL2, outline=LINE, width=4 * s)
    d.chord((cx - 150 * s, by0 - 250 * s, cx + 150 * s, by0 + 50 * s), 180, 360, fill=FILL2, outline=LINE, width=4 * s)
    d.arc((cx - 110 * s, by0 - 215 * s, cx + 40 * s, by0 + 20 * s), 200, 250, fill=(120, 150, 200, 255), width=5 * s)
    d.line((cx, by0 - 205 * s, cx, by0 - 250 * s), fill=LINE, width=4 * s)
    parts["dome"] = _down(im)
    # minaretes
    im = _layer(w, h)
    d = ImageDraw.Draw(im)
    for mx in (cx - 360 * s, cx + 360 * s):
        d.rectangle((mx - 26 * s, ground - 430 * s, mx + 26 * s, ground), fill=FILL2, outline=LINE, width=4 * s)
        d.rectangle((mx - 40 * s, ground - 330 * s, mx + 40 * s, ground - 310 * s), fill=FILL2, outline=LINE, width=3 * s)
        d.polygon([(mx - 30 * s, ground - 430 * s), (mx + 30 * s, ground - 430 * s), (mx, ground - 520 * s)], fill=FILL2, outline=LINE)
    parts["minaret"] = _down(im)
    # media luna sobre el portal
    im = _layer(w, h)
    d = ImageDraw.Draw(im)
    py = by0 - 20 * s
    d.polygon([(cx - 90 * s, by0), (cx + 90 * s, by0), (cx, by0 - 60 * s)], fill=FILL, outline=LINE)
    r = 34 * s
    cyc = by0 - 105 * s
    d.ellipse((cx - r, cyc - r, cx + r, cyc + r), fill=(240, 200, 90, 255))
    d.ellipse((cx - r + 16 * s, cyc - r - 6 * s, cx + r + 16 * s, cyc + r - 6 * s), fill=(0, 0, 0, 0))
    d.line((cx, by0 - 60 * s, cx, cyc + r - 4 * s), fill=LINE, width=3 * s)
    del py
    parts["crescent"] = _down(im)
    # banda de escritura árabe (caligrafía estilizada)
    im = _layer(w, h)
    d = ImageDraw.Draw(im)
    yb = ground - 200 * s
    d.rectangle((bx0 + 20 * s, yb - 26 * s, bx1 - 20 * s, yb + 26 * s), fill=(14, 30, 60, 255), outline=(240, 200, 90, 255), width=2 * s)
    xx = bx0 + 40 * s
    rr = np.random.default_rng(3)
    pts = []
    while xx < bx1 - 40 * s:
        pts.append((xx, yb + rr.uniform(-12, 14) * s))
        if rr.random() < 0.25:
            d.line((xx, yb + 10 * s, xx, yb - 20 * s), fill=(240, 200, 90, 255), width=3 * s)
        if rr.random() < 0.2:
            d.ellipse((xx - 3 * s, yb - 22 * s, xx + 3 * s, yb - 16 * s), fill=(240, 200, 90, 255))
        xx += rr.uniform(10, 22) * s
    d.line(pts, fill=(240, 200, 90, 255), width=3 * s, joint="curve")
    parts["script"] = _down(im)
    # techo de pagoda china
    im = _layer(w, h)
    d = ImageDraw.Draw(im)
    roof_c = (40, 44, 54, 255)

    def roof(y, half, hgt):
        d.polygon([(cx - half - 50 * s, y), (cx - half, y - 22 * s), (cx - half * 0.7, y - hgt), (cx + half * 0.7, y - hgt),
                   (cx + half, y - 22 * s), (cx + half + 50 * s, y), (cx + half + 10 * s, y - 6 * s), (cx - half - 10 * s, y - 6 * s)],
                  fill=roof_c, outline=RED + (255,))
        d.line((cx - half - 50 * s, y, cx + half + 50 * s, y), fill=RED + (255,), width=5 * s)

    roof(by0 + 4 * s, 280 * s, 90 * s)
    d.rectangle((cx - 150 * s, by0 - 160 * s, cx + 150 * s, by0 - 86 * s), fill=(120, 30, 36, 255), outline=LINE, width=3 * s)
    roof(by0 - 150 * s, 170 * s, 80 * s)
    d.ellipse((cx - 10 * s, by0 - 255 * s, cx + 10 * s, by0 - 235 * s), fill=RED + (255,))
    parts["pagoda"] = _down(im)
    return parts


@lru_cache(None)
def shadian_before(w=1000, h=697):
    """Ilustración (no foto) de la Gran Mezquita de Shadian con su diseño anterior."""
    s = SS
    im = _layer(w, h)
    d = ImageDraw.Draw(im)
    # cielo
    for y in range(h * s):
        k = y / (h * s)
        d.line((0, y, w * s, y), fill=(int(20 + 30 * k), int(40 + 40 * k), int(70 + 40 * k), 255))
    cx, ground = w / 2 * s, (h - 90) * s
    d.rectangle((0, ground, w * s, h * s), fill=(40, 52, 70, 255))
    dome = (70, 120, 115, 255)
    line = (225, 232, 240, 255)
    # cuerpo
    d.rectangle((cx - 300 * s, ground - 220 * s, cx + 300 * s, ground), fill=(205, 210, 215, 255), outline=line, width=3 * s)
    for i in range(7):
        ax = cx + (-270 + i * 90) * s
        d.rectangle((ax - 22 * s, ground - 110 * s, ax + 22 * s, ground), fill=(60, 80, 100, 255))
        d.pieslice((ax - 22 * s, ground - 132 * s, ax + 22 * s, ground - 88 * s), 180, 360, fill=(60, 80, 100, 255))
    # cúpula central
    d.rectangle((cx - 130 * s, ground - 280 * s, cx + 130 * s, ground - 220 * s), fill=(215, 220, 225, 255), outline=line, width=3 * s)
    d.chord((cx - 170 * s, ground - 560 * s, cx + 170 * s, ground - 200 * s), 180, 360, fill=dome, outline=line, width=3 * s)
    d.line((cx, ground - 380 * s, cx, ground - 430 * s), fill=(240, 200, 90, 255), width=4 * s)
    r = 16 * s
    d.ellipse((cx - r, ground - 455 * s - r, cx + r, ground - 455 * s + r), fill=(240, 200, 90, 255))
    d.ellipse((cx - r + 8 * s, ground - 459 * s - r, cx + r + 8 * s, ground - 459 * s + r), fill=dome)
    # cúpulas pequeñas
    for dx in (-220, 220):
        d.chord(((cx + (dx - 60) * s), ground - 300 * s, (cx + (dx + 60) * s), ground - 180 * s), 180, 360, fill=dome, outline=line, width=3 * s)
    # 4 minaretes
    for mx in (-430, -360, 360, 430):
        x = cx + mx * s
        top = ground - (520 if abs(mx) == 360 else 470) * s
        d.rectangle((x - 18 * s, top, x + 18 * s, ground), fill=(215, 220, 225, 255), outline=line, width=2 * s)
        d.rectangle((x - 28 * s, top + 60 * s, x + 28 * s, top + 74 * s), fill=(215, 220, 225, 255), outline=line, width=2 * s)
        d.chord((x - 20 * s, top - 40 * s, x + 20 * s, top + 4 * s), 180, 360, fill=dome)
        d.line((x, top - 20 * s, x, top - 48 * s), fill=(240, 200, 90, 255), width=3 * s)
    im = _down(im)
    return grade(im, 0.6, 0.95).convert("RGBA")


def icon(kind, size=84):
    s = 4
    im = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S_ = size * s
    c = (225, 232, 245, 255)
    lw = 5 * s
    if kind == "dome":
        d.chord((S_ * 0.15, S_ * 0.2, S_ * 0.85, S_ * 0.9), 180, 360, outline=c, width=lw)
        d.line((S_ * 0.12, S_ * 0.55, S_ * 0.88, S_ * 0.55), fill=c, width=lw)
        d.rectangle((S_ * 0.2, S_ * 0.55, S_ * 0.8, S_ * 0.78), outline=c, width=lw)
    elif kind == "minaret":
        d.rectangle((S_ * 0.42, S_ * 0.3, S_ * 0.58, S_ * 0.88), outline=c, width=lw)
        d.polygon([(S_ * 0.38, S_ * 0.3), (S_ * 0.62, S_ * 0.3), (S_ * 0.5, S_ * 0.08)], outline=c, width=lw)
        d.line((S_ * 0.34, S_ * 0.48, S_ * 0.66, S_ * 0.48), fill=c, width=lw)
    elif kind == "crescent":
        d.ellipse((S_ * 0.18, S_ * 0.18, S_ * 0.82, S_ * 0.82), fill=c)
        d.ellipse((S_ * 0.34, S_ * 0.1, S_ * 0.96, S_ * 0.72), fill=(0, 0, 0, 0))
    elif kind == "script":
        rr = np.random.default_rng(5)
        pts = [(S_ * (0.1 + 0.8 * i / 14), S_ * (0.6 + rr.uniform(-0.08, 0.08))) for i in range(15)]
        d.line(pts, fill=c, width=lw, joint="curve")
        for x in (0.25, 0.48, 0.7):
            d.line((S_ * x, S_ * 0.6, S_ * x, S_ * 0.25), fill=c, width=lw)
        d.ellipse((S_ * 0.58, S_ * 0.32, S_ * 0.64, S_ * 0.38), fill=c)
    return im.resize((size, size), Image.LANCZOS)


# ------------------------------------------------------------------ escena 1: cúpula que se desintegra
DOME_Y = 830


@lru_cache(None)
def s1_data():
    src = photo("foto1_cupula.jpg", over=1.12, sat=0.55, dark=0.9)
    rng = np.random.default_rng(11)
    bw, bh = W // 8 + 1, H // 8 + 1
    blk = rng.random((bh, bw)).astype(np.float32)
    blk = np.kron(blk, np.ones((8, 8), np.float32))[:H, :W]
    fine = rng.random((H, W)).astype(np.float32)
    y = np.arange(H, dtype=np.float32)[:, None] / DOME_Y
    thr = np.clip(0.72 * y + 0.2 * blk + 0.08 * fine, 0, 1.5)
    # partículas
    n = 3200
    py = rng.uniform(BAR, DOME_Y, n)
    px = rng.uniform(0, W, n)
    pthr = thr[py.astype(int), px.astype(int)]
    frame0 = np.asarray(kenburns(src, W, H, 1.0, 0.5, 0.45).convert("RGB"))
    cols = frame0[py.astype(int), px.astype(int)]
    vel = np.stack([rng.uniform(-60, 140, n), rng.uniform(-260, -60, n)], 1)
    size = rng.integers(3, 8, n)
    return src, thr, dict(px=px, py=py, thr=pthr, col=cols, vel=vel, size=size)


def s1_progress(t):
    return eio(lin(t, 0.80, 2.9)) * 0.98


def scene1(base, t):
    src, thr, P = s1_data()
    z = 1.0 + 0.06 * lin(t, 0, 5.5)
    bg = kenburns(src, W, H, z, 0.5, 0.45 - 0.02 * lin(t, 0, 5.5))
    prog = s1_progress(t)
    if prog > 0:
        a = np.asarray(bg).copy()
        gone = thr < prog
        edge = (thr < prog + 0.025) & ~gone
        # fondo vacío: degradado azul marino oscuro
        yy = np.arange(H)[:, None]
        void = np.zeros((H, 1, 3), np.float32)
        void[..., 0], void[..., 1], void[..., 2] = 6 + 6 * (yy / H), 12 + 12 * (yy / H), 26 + 30 * (yy / H)
        a[..., :3] = np.where(gone[..., None], np.broadcast_to(void, (H, W, 3)).astype(np.uint8), a[..., :3])
        a[edge, 0] = 255
        a[edge, 1] = 140
        a[edge, 2] = 140
        bg = Image.fromarray(a, "RGBA")
    base.alpha_composite(bg)
    # partículas
    if prog > 0:
        tt = (t - (0.80 + P["thr"] / 1.12 * 2.1))
        act = (tt > 0) & (tt < 1.6)
        if act.any():
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            idx = np.nonzero(act)[0]
            for i in idx:
                k = tt[i]
                x = P["px"][i] + P["vel"][i, 0] * k + 30 * math.sin(k * 3 + i)
                y = P["py"][i] + P["vel"][i, 1] * k - 40 * k * k
                al = int(255 * (1 - k / 1.6) ** 1.5)
                c = P["col"][i]
                r = P["size"][i] * (1 - 0.5 * k / 1.6)
                d.rectangle((x, y, x + r, y + r), fill=(int(c[0]) + 40, int(c[1]) + 30, int(c[2]) + 30, al))
            base.alpha_composite(lay)
    # texto: MILES DE / MEZQUITAS
    for txt, ts, y, col, sz in (("MILES DE", 1.48, 470, WHITE, 150), ("MEZQUITAS", 2.08, 640, RED, 190)):
        p = lin(t, ts, ts + 0.3)
        if p > 0:
            im = text_img(txt, F_ANTON, sz, col, shadow=10)
            paste(base, im, W / 2, y, 1.3 - 0.3 * eback(p), min(1, p * 2))
    # nota de imagen ilustrativa
    note = text_img("Imagen ilustrativa · Santa Sofía, Estambul (Turquía)", F_P5, 24, (190, 196, 206))
    paste(base, note, 40, 1700, anchor="l", alpha=0.85)


# ------------------------------------------------------------------ escena 2: mapa
MAP_Y = 560


@lru_cache(None)
def s2_dist():
    nb, cf, co, glow, mh, proj = map_layers()
    bx, by = proj(116.4, 39.9)
    yy, xx = np.mgrid[0:mh, 0:nb.width]
    return np.hypot(xx - bx, yy - by) / 900.0


def scene2(base, t):
    # fondo
    overlay_fill(base, NAVY_D, 1)
    nb, cf, co, glow, mh, proj = map_layers()
    z = 1.0 + 0.07 * lin(t, 5.5, 14.1)
    lay = Image.new("RGBA", (nb.width, mh), (0, 0, 0, 0))
    lay.alpha_composite(with_alpha(nb, eo(lin(t, 5.5, 6.3))))
    prog = eio(lin(t, 5.65, 7.2)) * 1.15
    if prog > 0:
        dist = s2_dist()
        m = np.clip((prog - dist) / 0.08, 0, 1)
        mask = Image.fromarray((m * 255).astype(np.uint8))
        pulse = 0.75 + 0.25 * math.sin(t * 3.2)
        g = glow.copy()
        g.putalpha(Image.fromarray((np.asarray(glow.getchannel("A")) * m * pulse).astype(np.uint8)))
        lay.alpha_composite(g)
        lay.alpha_composite(g)
        c = cf.copy()
        c.putalpha(Image.fromarray((np.asarray(cf.getchannel("A")) * m).astype(np.uint8)))
        lay.alpha_composite(c)
        o = co.copy()
        o.putalpha(Image.fromarray((np.asarray(co.getchannel("A")) * m).astype(np.uint8)))
        lay.alpha_composite(o)
        del mask
        # Pekín
        bx, by = proj(116.4, 39.9)
        d = ImageDraw.Draw(lay)
        rr = 10 + 26 * ((t * 0.8) % 1)
        d.ellipse((bx - 8, by - 8, bx + 8, by + 8), fill=(255, 255, 255, 255))
        d.ellipse((bx - rr, by - rr, bx + rr, by + rr), outline=(255, 255, 255, int(255 * (1 - (t * 0.8) % 1))), width=3)
    lay = lay.resize((int(lay.width * z), int(lay.height * z)), Image.BICUBIC)
    paste(base, lay, W / 2, MAP_Y + mh / 2)
    # etiqueta "CHINA"
    paste(base, text_img("C H I N A", F_P8, 34, (255, 230, 232)), W / 2 - 40, MAP_Y + mh / 2 + 20, alpha=lin(t, 7.0, 7.5) * 0.9)
    # SINIZACIÓN
    p = lin(t, 8.10, 8.55)
    if p > 0:
        sp = int(4 + 18 * (1 - eo(p)))
        im = text_img("SINIZACIÓN", F_ANTON, 170, RED, shadow=10, spacing=sp)
        paste(base, im, W / 2, 380, 1.15 - 0.15 * eo(p), min(1, p * 2))
        paste(base, text_img("de las religiones", F_P7, 40, (200, 210, 230)), W / 2, 500, alpha=lin(t, 9.3, 9.7))
    else:
        im = text_img("2016", F_ANTON, 210, WHITE, shadow=10)
        p0 = lin(t, 5.7, 6.0)
        paste(base, im, W / 2, 390, 1.2 - 0.2 * eo(p0), p0 * (1 - lin(t, 7.9, 8.1)))
    # rótulo
    lower_third(base, t, 6.8, "2016 — XI JINPING", "Presidente de China", 1260, t1=10.1)
    # "hacerlas más chinas" + influencia extranjera tachada
    paste(base, text_img("hacerlas «más chinas»", F_P7, 46, (220, 228, 240)), W / 2, 1290, alpha=lin(t, 10.4, 10.8))
    p = lin(t, 12.25, 12.6)
    if p > 0:
        im = text_img("INFLUENCIA EXTRANJERA", F_ANTON, 92, WHITE, shadow=6)
        cy = 1410
        paste(base, im, W / 2, cy, alpha=p * (1 - 0.45 * lin(t, 13.2, 13.5)))
        s = eo(lin(t, 13.1, 13.45))
        if s > 0:
            d = ImageDraw.Draw(base)
            x0 = W / 2 - im.width / 2 - 20
            d.line((x0, cy + 8, x0 + (im.width + 40) * s, cy - 4), fill=RED, width=14)


# ------------------------------------------------------------------ escena 3: contador + satélite
def scene3(base, t):
    src = photo("foto4_mezquita_sinizada.jpg", over=1.1, sat=0.35, dark=0.55)
    k = lin(t, 14.1, 21.0)
    bg = kenburns(src, W, H, 1.0 + 0.1 * k, 0.45 + 0.12 * k, 0.5)
    base.alpha_composite(bg)
    overlay_fill(base, (4, 12, 28), 0.35)
    # HUD satelital
    d = ImageDraw.Draw(base)
    gcol = (140, 190, 255, 60)
    for x in range(0, W, 90):
        d.line((x, BAR, x, H - BAR), fill=gcol, width=1)
    for y in range(BAR, H - BAR, 90):
        d.line((0, y, W, y), fill=gcol, width=1)
    sy = BAR + ((t - 14.1) * 420) % (H - 2 * BAR)
    d.rectangle((0, sy - 2, W, sy + 2), fill=(160, 210, 255, 120))
    for (x, y, dx, dy) in ((60, 210, 1, 1), (W - 60, 210, -1, 1), (60, H - 210, 1, -1), (W - 60, H - 210, -1, -1)):
        d.line((x, y, x + 70 * dx, y), fill=(220, 235, 255, 220), width=5)
        d.line((x, y, x, y + 70 * dy), fill=(220, 235, 255, 220), width=5)
    rec = text_img("● IMG SAT · ANÁLISIS", F_P7, 26, (255, 120, 128))
    paste(base, rec, 80, 248, anchor="l", alpha=0.6 + 0.4 * (int(t * 2) % 2))
    # tarjeta FT
    source_card(base, t, 14.35, "Financial Times", "Análisis de imágenes satelitales", 380)
    # contador
    p = lin(t, 14.3, 15.36)
    v = int(1000 * eo(p))
    num = f"{v:,}".replace(",", ".")
    if p >= 1:
        num = "1.000+"
    im = text_img(num, F_ANTON, 230, WHITE, shadow=10)
    pop = 1 + 0.08 * (1 - eo(lin(t, 15.36, 15.6))) if t > 15.36 else 1
    yc = 640 - 60 * eio(lin(t, 18.0, 18.4))
    paste(base, im, W / 2, yc, pop, lin(t, 14.25, 14.4))
    lab = lin(t, 15.36, 15.7)
    if lab > 0:
        paste(base, text_img("MILES DE MEZQUITAS", F_ANTON, 84, RED, shadow=6), W / 2, yc + 175, 1, lab)
    # alteradas / cerradas / demolidas
    for i, (w_, ts) in enumerate((("ALTERADAS", 18.32), ("CERRADAS", 19.2), ("DEMOLIDAS", 20.0))):
        p = lin(t, ts, ts + 0.18)
        if p <= 0:
            continue
        txt = text_img(w_, F_ANTON, 112, WHITE)
        box = rect_layer(txt.width + 70, txt.height + 6, RED + (230,), radius=6)
        paste(box, txt, box.width / 2, box.height / 2)
        paste(base, box, W / 2, 960 + i * 165, 1.6 - 0.6 * eo(p), min(1, p * 1.5), rot=(-3 + 3 * i) * 0.6)


# ------------------------------------------------------------------ escena 4: el método
CHECK = [("dome", "CÚPULA", 23.34), ("minaret", "MINARETE", 24.9), ("crescent", "MEDIA LUNA", 26.54), ("script", "ESCRITURA ÁRABE", 27.46)]


def scene4(base, t):
    # fondo
    overlay_fill(base, NAVY_D, 1)
    g = Image.new("RGBA", (W, 900), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((90, 120, 990, 820), fill=NAVY + (150,))
    paste(base, g.filter(ImageFilter.GaussianBlur(90)), W / 2, 640)
    # título
    p = lin(t, 21.25, 21.6)
    paste(base, text_img("EL MÉTODO", F_ANTON, 120, WHITE, shadow=6), W / 2, 285, 1.2 - 0.2 * eo(p), p)
    if p > 0:
        ImageDraw.Draw(base).rectangle((W / 2 - 160 * eo(p), 365, W / 2 + 160 * eo(p), 375), fill=RED)
    paste(base, text_img("paso a paso", F_P7, 36, (180, 195, 220)), W / 2, 410, alpha=lin(t, 21.7, 22.0))
    # ilustración
    parts = mosque_parts()
    il = Image.new("RGBA", parts["base"].size, (0, 0, 0, 0))

    def removal(ts):
        k = lin(t, ts, ts + 0.6)
        return k

    order = [("minaret", 24.9), ("dome", 23.34), ("base", None), ("script", 27.46), ("crescent", 26.54)]
    for name, ts in order:
        im = parts[name]
        if ts is None:
            il.alpha_composite(im)
            continue
        k = removal(ts)
        if k >= 1:
            continue
        flash = lin(t, ts - 0.25, ts) * (1 - k)
        if flash > 0 and k == 0:
            red = Image.new("RGBA", im.size, RED + (0,))
            red.putalpha(im.getchannel("A").point(lambda v: int(v * flash * 0.8)))
            im = Image.alpha_composite(im, red)
        dy = int(260 * k * k)
        im = with_alpha(im, 1 - k)
        il.alpha_composite(im, (0, dy)) if dy < im.height else None
    pk = eo(lin(t, 28.8, 29.4))
    if pk > 0:
        pg = parts["pagoda"]
        il.alpha_composite(with_alpha(pg, min(1, pk * 1.5)), (0, 0)) if pk >= 1 else paste(il, pg, pg.width / 2, pg.height / 2 - 200 * (1 - pk), alpha=min(1, pk * 1.5))
    paste(base, il, W / 2, 470 + il.height / 2)
    # lista
    for i, (ic, label, ts) in enumerate(CHECK):
        y = 1150 + i * 108
        a = lin(t, 21.9 + i * 0.15, 22.2 + i * 0.15)
        if a <= 0:
            continue
        hit = lin(t, ts, ts + 0.25)
        col = WHITE if hit < 1 else (150, 158, 172)
        circ = rect_layer(86, 86, (30, 60, 110, 255) if hit < 0.5 else (90, 20, 28, 255), radius=43)
        paste(base, circ, 200, y, alpha=a)
        paste(base, icon(ic, 62), 200, y, alpha=a)
        lt = text_img(label, F_P9, 54, col)
        paste(base, lt, 270, y, anchor="l", alpha=a)
        if hit > 0:
            d = ImageDraw.Draw(base)
            d.line((265, y + 2, 265 + (lt.width + 10) * eo(hit), y + 2), fill=RED, width=9)
            xs = text_img("✕", "Poppins-900.woff", 10, RED) if False else None
            del xs
            s = 1.6 - 0.6 * eo(hit)
            r = 30 * s
            d.line((200 - r, y - r, 200 + r, y + r), fill=RED, width=12)
            d.line((200 - r, y + r, 200 + r, y - r), fill=RED, width=12)
    # transición a la foto de estilo chino
    k = lin(t, 29.7, 30.2)
    if k > 0:
        src = photo("foto2_estilo_chino.jpg", over=1.15, sat=0.55, dark=0.85)
        ph = kenburns(src, W, H, 1.0 + 0.07 * lin(t, 29.7, 32.0), 0.5, 0.42)
        base.alpha_composite(with_alpha(ph, eio(k)))
        overlay_fill(base, (0, 0, 0), 0.25 * k)
        p1 = lin(t, 29.76, 30.1)
        paste(base, text_img("TECHOS Y PAGODAS", F_ANTON, 120, WHITE, shadow=10), W / 2, 380, 1.2 - 0.2 * eo(p1), p1)
        p2 = lin(t, 30.9, 31.2)
        paste(base, text_img("DE ESTILO CHINO", F_ANTON, 120, RED, shadow=10), W / 2, 520, 1.2 - 0.2 * eo(p2), p2)
        paste(base, text_img("Gran Mezquita de Xi'an · estilo chino tradicional", F_P5, 24, (200, 205, 214)), 40, 1700, anchor="l", alpha=k * 0.9)


# ------------------------------------------------------------------ escena 5: Shadian antes/después
PANEL_W, PANEL_H = 1000, 697
PANEL_Y = 820


def scene5(base, t):
    bgsrc = photo("foto3_shadian.jpg", over=1.1, sat=0.4, dark=0.45, blur=30)
    base.alpha_composite(kenburns(bgsrc, W, H, 1.0, 0.6, 0.5))
    overlay_fill(base, NAVY_D, 0.35)
    k = lin(t, 32.0, 37.0)
    after_src = photo("foto3_shadian.jpg", cover_w=PANEL_W, cover_h=PANEL_H, over=1.12, sat=0.6, dark=0.95)
    after = kenburns(after_src, PANEL_W, PANEL_H, 1.0 + 0.05 * k, 0.55, 0.45)
    before = shadian_before()
    # deslizador: 33.3-35.3 de derecha a izquierda; luego vuelve al centro
    if t < 33.3:
        sx = PANEL_W
    elif t < 35.3:
        sx = PANEL_W * (1 - eio(lin(t, 33.3, 35.3)))
    else:
        sx = PANEL_W * 0.5 * eio(lin(t, 35.4, 36.2))
    sx = int(sx)
    panel = after.copy()
    if sx > 0:
        panel.paste(before.crop((0, 0, sx, PANEL_H)), (0, 0))
    d = ImageDraw.Draw(panel)
    if 0 < sx < PANEL_W:
        d.rectangle((sx - 3, 0, sx + 3, PANEL_H), fill=(255, 255, 255))
        d.ellipse((sx - 34, PANEL_H / 2 - 34, sx + 34, PANEL_H / 2 + 34), fill=(255, 255, 255), outline=RED, width=4)
        d.polygon([(sx - 8, PANEL_H / 2 - 12), (sx - 8, PANEL_H / 2 + 12), (sx - 22, PANEL_H / 2)], fill=NAVY)
        d.polygon([(sx + 8, PANEL_H / 2 - 12), (sx + 8, PANEL_H / 2 + 12), (sx + 22, PANEL_H / 2)], fill=NAVY)
    frame = rect_layer(PANEL_W + 12, PANEL_H + 12, (240, 242, 246, 255), radius=6)
    pin = eo(lin(t, 32.05, 32.6))
    paste(base, frame, W / 2, PANEL_Y, 0.9 + 0.1 * pin, pin)
    paste(base, panel, W / 2, PANEL_Y, 0.9 + 0.1 * pin, pin)
    # etiquetas
    def tag(txt, sub, x, anchor, col):
        im = text_img(txt, F_P9, 38, WHITE)
        b = rect_layer(im.width + 36, 58, col + (235,), radius=4)
        paste(b, im, b.width / 2, 30)
        paste(base, b, x, PANEL_Y - PANEL_H / 2 + 50, anchor=anchor, alpha=pin)
        if sub:
            paste(base, text_img(sub, F_P5, 24, WHITE, shadow=3), x + (10 if anchor == "l" else -10), PANEL_Y - PANEL_H / 2 + 105, anchor=anchor, alpha=pin * 0.9)

    if sx > 60:
        tag("ANTES", "ilustración", W / 2 - PANEL_W / 2 + 20, "l", NAVY)
    if sx < PANEL_W - 60:
        tag("HOY", "foto", W / 2 + PANEL_W / 2 - 20, "r", RED)
    # rótulo de lugar
    lp = eo(lin(t, 33.25, 33.7))
    if lp > 0:
        pi = pin_icon(58)
        paste(base, pi, 110, 330 - 30 * (1 - lp), alpha=lp)
        paste(base, text_img("SHADIAN, YUNNAN", F_ANTON, 92, WHITE, shadow=6), 160, 322, anchor="l", alpha=lp)
        paste(base, text_img("Gran Mezquita de Shadian · una de las más grandes del país", F_P7, 28, (215, 222, 235), shadow=3), 165, 400, anchor="l", alpha=lin(t, 34.0, 34.5))
    # minimapa
    mp = lin(t, 34.3, 34.8)
    if mp > 0:
        nb, cf, co, glow, mh, proj = map_layers(420)
        m = Image.new("RGBA", nb.size, (0, 0, 0, 0))
        m.alpha_composite(with_alpha(nb, 0.7))
        m.alpha_composite(with_alpha(cf, 0.55))
        m.alpha_composite(co)
        x, y = proj(103.3, 23.6)
        dd = ImageDraw.Draw(m)
        ph = (t * 1.2) % 1
        dd.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(255, 255, 255))
        dd.ellipse((x - 7 - 22 * ph, y - 7 - 22 * ph, x + 7 + 22 * ph, y + 7 + 22 * ph), outline=(255, 255, 255, int(255 * (1 - ph))), width=3)
        paste(base, m, W / 2, 1180 + mh / 2 + 10, alpha=mp)


# ------------------------------------------------------------------ escena 6: documento filtrado
DOC_W, DOC_H = 860, 980
DOC_LINES = [
    ("h", "INSTRUCCIONES INTERNAS"),
    ("h2", "Qué decir a los estudiantes que vuelven a casa"),
    ("bar", [0.9]),
    ("bar", [0.55, 0.3]),
    ("t", ["Sus", "familiares", "están"]),
    ("t", ["#INFECTADOS", "por", "el", "#VIRUS"]),
    ("t", ["del", "extremismo", "religioso."]),
    ("bar", [0.4, 0.45]),
    ("bar", [0.8]),
    ("t", ["No", "podrán", "volver", "hasta"]),
    ("t", ["#CURARSE."]),
    ("bar", [0.6, 0.25]),
    ("bar", [0.35]),
]
HL_T = {"INFECTADOS": 45.96, "VIRUS": 47.6, "CURARSE.": 51.88}


@lru_cache(None)
def doc_base():
    """Papel + texto. Devuelve imagen y posiciones de palabras resaltables."""
    rng = np.random.default_rng(2)
    paper = np.ones((DOC_H, DOC_W, 3), np.float32) * np.array([226, 224, 216], np.float32)
    paper += rng.normal(0, 6, (DOC_H, DOC_W, 1))
    paper = np.clip(paper, 0, 255).astype(np.uint8)
    im = Image.fromarray(paper).convert("RGBA")
    d = ImageDraw.Draw(im)
    ink = (34, 34, 38, 255)
    d.line((60, 150, DOC_W - 60, 150), fill=ink, width=3)
    f_h = font(F_ELITE, 46)
    f_h2 = font(F_ELITE, 30)
    f_t = font(F_ELITE, 50)
    y = 70
    pos = {}
    for kind, val in DOC_LINES:
        if kind == "h":
            d.text((60, y), val, font=f_h, fill=ink)
            y += 100
        elif kind == "h2":
            d.text((60, y), val, font=f_h2, fill=(70, 70, 76, 255))
            y += 80
        elif kind == "bar":
            x = 60
            for w_ in val:
                ww = int((DOC_W - 120) * w_)
                d.rectangle((x, y + 8, x + ww, y + 44), fill=(22, 22, 24, 255))
                x += ww + 22
            y += 66
        else:
            x = 60
            for wd in val:
                hl = wd.startswith("#")
                wd = wd.lstrip("#")
                wl = f_t.getlength(wd)
                if hl:
                    pos[wd] = (x, y, wl)
                d.text((x, y), wd, font=f_t, fill=ink)
                x += wl + f_t.getlength(" ")
            y += 72
    # sello lateral de folio
    d.text((60, DOC_H - 70), "Ref. ███-2019 · pág. 3/12", font=font(F_ELITE, 26), fill=(90, 90, 96, 255))
    return im, pos


@lru_cache(None)
def stamp_img():
    txt = "CONFIDENCIAL — 2019"
    f = font(F_ANTON, 78)
    tw = int(f.getlength(txt))
    w, h = tw + 80, 150
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (200, 30, 40, 255)
    d.rounded_rectangle((6, 6, w - 6, h - 6), radius=10, outline=col, width=8)
    d.rounded_rectangle((20, 20, w - 20, h - 20), radius=6, outline=col, width=3)
    d.text((40, 22), txt, font=f, fill=col)
    a = np.asarray(im).copy()
    rng = np.random.default_rng(4)
    holes = rng.random(a.shape[:2]) < 0.18
    a[..., 3] = np.where(holes, (a[..., 3] * 0.25).astype(np.uint8), a[..., 3])
    return Image.fromarray(a)


def scene6(base, t):
    overlay_fill(base, (3, 6, 14), 1)
    # "PERO HAY ALGO MÁS"
    p = lin(t, 37.06, 37.3)
    out = 1 - lin(t, 38.25, 38.5)
    if p > 0 and out > 0:
        shake = 6 * (1 - lin(t, 37.06, 37.5)) * math.sin(t * 90)
        paste(base, text_img("PERO HAY", F_ANTON, 160, WHITE, shadow=8), W / 2 + shake, 820, 1.1 - 0.1 * eo(p), p * out)
        p2 = lin(t, 37.54, 37.8)
        paste(base, text_img("ALGO MÁS", F_ANTON, 190, RED, shadow=8), W / 2 - shake, 1000, 1.1 - 0.1 * eo(p2), p2 * out)
    # documento
    dp = eo(lin(t, 38.45, 39.1))
    if dp <= 0:
        return
    doc, pos = doc_base()
    doc = doc.copy()
    dd = ImageDraw.Draw(doc)
    for wd, ts in HL_T.items():
        x, y, wl = pos[wd]
        h = lin(t, ts, ts + 0.35)
        if h > 0:
            dd.rectangle((x - 8, y + 2, x - 8 + (wl + 16) * eo(h), y + 62), fill=RED + (235,))
            if h >= 1:
                dd.text((x, y), wd, font=font(F_ELITE, 50), fill=(255, 255, 255, 255))
    # extremismo subrayado
    # cámara: zoom hacia la zona resaltada
    zk = eio(lin(t, 45.5, 46.6))
    sc = (0.82 + 0.06 * lin(t, 38.5, 45.5)) + 0.12 * zk - 0.1 * eio(lin(t, 52.2, 53.1))
    yc = 870 + (1 - dp) * 500 - 90 * zk * (1 - 0.4 * lin(t, 49.5, 51.5)) + 50 * eio(lin(t, 52.2, 53.1)) * zk
    rot = -2.0 + 1.0 * lin(t, 38.5, 53)
    dim = 1 - 0.55 * lin(t, 53.15, 53.4)
    shadow = rect_layer(DOC_W + 40, DOC_H + 40, (0, 0, 0, 160), radius=20).filter(ImageFilter.GaussianBlur(18))
    paste(base, shadow, W / 2 + 14, yc + 20, sc, dp * 0.8, rot=rot)
    paste(base, doc, W / 2, yc, sc, dp, rot=rot)
    overlay_fill(base, (0, 0, 0), 0.55 * (1 - dim))
    # sello
    sp = lin(t, 40.6, 40.78)
    if sp > 0:
        paste(base, stamp_img(), W / 2 + 120, 540 + yc - 870, 2.0 - 1.0 * eo(sp), min(1, sp * 2) * (0.95 * dim + 0.05), rot=-11)
    # tarjeta NYT (arriba)
    source_card(base, t, 38.7, "The New York Times", "Documentos internos filtrados", 300, t1=45.2)
    # aclaración
    ap = lin(t, 48.3, 48.7) * (1 - lin(t, 53.1, 53.3))
    if ap > 0:
        b = rect_layer(820, 60, (0, 0, 0, 170), radius=8)
        paste(base, b, W / 2, 1490, alpha=ap)
        paste(base, text_img("Se referían al «extremismo religioso»", F_P7, 32, (235, 238, 244)), W / 2, 1490, alpha=ap)
    paste(base, text_img("Recreación gráfica basada en documentos filtrados (NYT, 2019)", F_P5, 22, (170, 176, 186)), 40, 1712, anchor="l", alpha=dp * 0.85 * (1 - lin(t, 53.1, 53.3)))
    # COMO EL SARS
    cp = lin(t, 53.2, 53.42)
    if cp > 0:
        shake = 8 * (1 - lin(t, 53.2, 53.8)) * math.sin(t * 110)
        paste(base, text_img("COMO EL", F_ANTON, 150, WHITE, shadow=10), W / 2 + shake, 780, 1.25 - 0.25 * eo(cp), cp)
        paste(base, text_img("SARS", F_ANTON, 330, RED, shadow=12), W / 2 - shake, 1000, 1.3 - 0.3 * eo(lin(t, 53.3, 53.55)), lin(t, 53.3, 53.5))


# ------------------------------------------------------------------ escena 7: versión del gobierno
def scene7(base, t):
    src = photo("foto5_banderas.jpg", over=1.12, sat=0.25, dark=0.45, blur=6)
    k = lin(t, 54.38, 61.4)
    base.alpha_composite(kenburns(src, W, H, 1.0 + 0.05 * k, 0.45, 0.4 + 0.1 * k))
    overlay_fill(base, (20, 22, 26), 0.45)
    p = eo(lin(t, 54.5, 55.0))
    cw, ch = 940, 720
    card = rect_layer(cw, ch, (206, 209, 214, 248), radius=14)
    d = ImageDraw.Draw(card)
    dark = (38, 42, 48)
    paste(card, text_img("VERSIÓN DEL GOBIERNO CHINO", F_P9, 44, dark), 60, 92, anchor="l")
    d.line((60, 140, cw - 60, 140), fill=(140, 145, 152), width=3)
    lines = [
        ("Combate al extremismo", 56.0),
        ("y al terrorismo.", 57.6),
        ("Llama «difamación»", 58.86),
        ("a las denuncias.", 59.6),
    ]
    y = 230
    for i, (ln, ts) in enumerate(lines):
        a = lin(t, ts, ts + 0.35)
        if a > 0:
            paste(card, text_img(ln, F_P7, 60, dark), 60 + 20 * (1 - eo(a)), y, anchor="l", alpha=a)
        y += 92 if i != 1 else 150
    paste(card, text_img("Postura oficial de Pekín", F_P5, 28, (100, 106, 116)), 60, ch - 60, anchor="l", alpha=lin(t, 55.4, 55.8))
    paste(base, card, W / 2, 860 + (1 - p) * 60, 1, p)


# ------------------------------------------------------------------ escena 8: pregunta + encuesta
@lru_cache(None)
def dust():
    rng = np.random.default_rng(9)
    return rng.uniform(0, 1, (160, 4))


def scene8(base, t):
    yy = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array(NAVY, np.float32), np.array((3, 8, 22), np.float32)
    grad = (top * (1 - yy) * 0.8 + bot * (0.2 + yy * 0.8)).astype(np.uint8)
    base.alpha_composite(Image.fromarray(np.broadcast_to(grad, (H, W, 3)).copy()).convert("RGBA"))
    d = ImageDraw.Draw(base)
    for x, y, s, sp in dust():
        px = x * W + 20 * math.sin(t * 0.5 + y * 10)
        py = (y * H - t * 25 * sp) % H
        r = 1 + 2.5 * s
        d.ellipse((px - r, py - r, px + r, py + r), fill=(200, 215, 240, int(60 + 80 * s)))
    items = [("¿PROTEGER", 62.44, 470, WHITE, 160), ("LA CULTURA", 63.0, 640, WHITE, 160), ("O", 63.48, 770, (170, 182, 205), 90),
             ("BORRAR", 64.04, 900, RED, 170), ("UNA FE?", 64.4, 1075, RED, 170)]
    lift = eio(lin(t, 64.9, 65.3))
    for txt, ts, y, col, sz in items:
        p = lin(t, ts, ts + 0.25)
        if p > 0:
            sc = (1.3 - 0.3 * eback(p)) * (1 - 0.15 * lift)
            paste(base, text_img(txt, F_ANTON, sz, col, shadow=10), W / 2, y - 150 * lift - (y - 770) * 0.12 * lift, sc, min(1, p * 2))
    # encuesta
    for i, (txt, col) in enumerate((("1 = Proteger la cultura", NAVY), ("2 = Borrar una fe", RED))):
        p = eo(lin(t, 64.95 + i * 0.15, 65.35 + i * 0.15))
        if p > 0:
            im = text_img(txt, F_P8, 50, WHITE)
            b = rect_layer(820, 104, col + (255,), radius=52, outline=(255, 255, 255, 200), width=3)
            paste(b, im, b.width / 2, 52)
            paste(base, b, W / 2 + (1 - p) * (220 if i else -220), 1180 + i * 130, 1, p)
    p = lin(t, 65.26, 65.6)
    if p > 0:
        bubble = Image.new("RGBA", (72, 64), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bubble)
        bd.rounded_rectangle((2, 2, 70, 48), radius=14, fill=WHITE)
        bd.polygon([(16, 46), (34, 46), (14, 62)], fill=WHITE)
        for k in range(3):
            bd.ellipse((18 + k * 14, 21, 26 + k * 14, 29), fill=NAVY)
        tx = text_img("Te leo en los comentarios", F_P8, 48, WHITE)
        tot = bubble.width + 20 + tx.width
        x0 = W / 2 - tot / 2
        paste(base, bubble, x0, 1468, anchor="tl", alpha=p)
        paste(base, tx, x0 + bubble.width + 20, 1496, anchor="l", alpha=p)


# ------------------------------------------------------------------ post-proceso
@lru_cache(None)
def vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = (xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)
    r = np.sqrt(nx ** 2 * 1.0 + ny ** 2 * 0.75)
    v = 1 - 0.62 * np.clip((r - 0.45) / 0.85, 0, 1) ** 1.6
    return v[..., None].astype(np.float32)


@lru_cache(None)
def grain_bank():
    rng = np.random.default_rng(1)
    g = rng.normal(0, 1, (6, H // 2, W // 2)).astype(np.float32)
    return [np.kron(x, np.ones((2, 2), np.float32))[..., None] * 7.0 for x in g]


FLASHES = [(5.5, 0.5), (14.1, 0.9), (21.0, 0.9), (32.0, 0.8), (66.62, 1.0)]
DIPS = [(4.8, 5.45, 5.9), (36.6, 37.0, 37.06), (54.05, 54.38, 54.65), (61.0, 61.35, 61.7)]


def black_level(t):
    m = 1.0
    for a, b, c in DIPS:
        if a <= t < b:
            m = min(m, 1 - eio(lin(t, a, b)))
        elif b <= t < c:
            m = min(m, eio(lin(t, b, c)))
    m = min(m, eio(lin(t, 0.0, 0.35)))
    return m


def flash_level(t):
    f = 0.0
    for at, s in FLASHES:
        if at - 0.08 <= t < at + 0.5:
            if t < at:
                f = max(f, s * lin(t, at - 0.08, at))
            else:
                f = max(f, s * (1 - eo(lin(t, at, at + 0.5))))
    return f


def top_bar_text(base, t):
    a = 0.75
    paste(base, text_img("CAPITAL CURIOSO", F_P8, 26, (200, 208, 222), spacing=3), 48, BAR - 46, anchor="l", alpha=a)
    paste(base, text_img("INVESTIGACIÓN", F_P7, 26, RED, spacing=3), W - 48, BAR - 46, anchor="r", alpha=a)


SCENES = [(0, 5.45, scene1), (5.45, 14.1, scene2), (14.1, 21.0, scene3), (21.0, 32.0, scene4),
          (32.0, 37.0, scene5), (37.0, 54.38, scene6), (54.38, 61.35, scene7), (61.35, INTRO_T, scene8)]


@lru_cache(None)
def intro_frame(i):
    i = max(1, min(105, i + 1))
    return np.asarray(Image.open(B("intro", f"{i:04d}.png")).convert("RGB"))


def render(t):
    if t >= INTRO_T:
        fr = intro_frame(int((t - INTRO_T) * FPS)).astype(np.float32)
        f = flash_level(t)
        fr = fr * (1 - f) + 255 * f
        return np.clip(fr, 0, 255).astype(np.uint8)
    base = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    for a, b, fn in SCENES:
        if a <= t < b:
            fn(base, t)
            break
    draw_captions(base, t)
    a = np.asarray(base.convert("RGB")).astype(np.float32)
    a *= vignette()
    a += grain_bank()[int(t * FPS) % 6]
    a *= black_level(t)
    f = flash_level(t)
    if f > 0:
        a = a * (1 - f) + np.array([255, 250, 240], np.float32) * f
    a = np.clip(a, 0, 255).astype(np.uint8)
    a[:BAR] = 0
    a[H - BAR:] = 0
    im = Image.fromarray(a).convert("RGBA")
    top_bar_text(im, t)
    return np.asarray(im.convert("RGB"))


def worker(args):
    idx, f0, f1 = args
    out = B(f"seg_{idx:02d}.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for fr in range(f0, f1):
        p.stdin.write(render(fr / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return out


def main():
    os.makedirs(B(), exist_ok=True)
    if len(sys.argv) > 2 and sys.argv[1] == "--still":
        os.makedirs(B("stills"), exist_ok=True)
        for s in sys.argv[2:]:
            Image.fromarray(render(float(s))).save(B("stills", f"t{float(s):06.2f}.png"))
        return
    nseg = 16
    step = math.ceil(NFRAMES / nseg)
    jobs = [(i, i * step, min(NFRAMES, (i + 1) * step)) for i in range(nseg)]
    with Pool(int(os.environ.get("JOBS", os.cpu_count() or 4))) as pool:
        segs = pool.map(worker, jobs)
    with open(B("segs.txt"), "w") as f:
        for s in segs:
            f.write(f"file '{s}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", B("segs.txt"), "-c", "copy",
                    B("video_sin_audio.mp4")], check=True)
    print("ok", NFRAMES, "frames")


if __name__ == "__main__":
    main()
