"""Renderiza el video vertical 1080x1920 (sin audio) cuadro a cuadro.

Uso: python3 render.py <carpeta_imagenes> <words.json> <fonts_dir> <topojson> <salida.mp4> [t_ini t_fin]
"""
import sys, os, json, math, subprocess, functools
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import *

IMG_DIR, WORDS, FONTS, TOPO, OUT = sys.argv[1:6]
RANGE = (float(sys.argv[6]), float(sys.argv[7])) if len(sys.argv) > 7 else (0, MAIN_END)

NAVY = (11, 40, 88)
CORAL = (242, 71, 90)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GOLD = (255, 205, 0)
BLUE = (60, 130, 255)
RED = (230, 30, 45)

# ------------------------------------------------------------------ utilidades
def clamp01(x): return max(0.0, min(1.0, x))
def ease_out(x): x = clamp01(x); return 1 - (1 - x) ** 3
def ease_in_out(x): x = clamp01(x); return x * x * (3 - 2 * x)
def ease_back(x):
    x = clamp01(x); c1 = 1.9; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def lerp(a, b, u): return a + (b - a) * u
def prog(t, t0, dur): return clamp01((t - t0) / dur)


@functools.lru_cache(None)
def font(weight, size):
    return ImageFont.truetype(os.path.join(FONTS, f"Poppins-{weight}.ttf"), size)


@functools.lru_cache(512)
def text_sprite(text, size, color=WHITE, weight=800, stroke=0, stroke_color=BLACK,
                shadow=True, glow=None, spacing=0):
    f = font(weight, size)
    pad = stroke + 30
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    l, t_, r, b = tmp.textbbox((0, 0), text, font=f, stroke_width=stroke)
    w, h = r - l + 2 * pad, b - t_ + 2 * pad
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l + 4, pad - t_ + 8), text, font=f, fill=(0, 0, 0, 170),
                                stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(9)))
    if glow:
        gl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(gl).text((pad - l, pad - t_), text, font=f, fill=glow + (255,), stroke_width=stroke + 6,
                                stroke_fill=glow + (255,))
        gl = gl.filter(ImageFilter.GaussianBlur(16))
        img = Image.alpha_composite(img, gl)
        img = Image.alpha_composite(img, gl)
    ImageDraw.Draw(img).text((pad - l, pad - t_), text, font=f, fill=color + (255,),
                             stroke_width=stroke, stroke_fill=stroke_color + (255,))
    return np.array(img)


def blit(F, spr, cx, cy, alpha=1.0, scale=1.0, angle=0.0):
    """Pega un sprite RGBA centrado en (cx, cy)."""
    if alpha <= 0.003 or scale <= 0.01:
        return
    if scale != 1.0 or angle != 0.0:
        h, w = spr.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
        nw = int(abs(w * scale * math.cos(math.radians(angle))) + abs(h * scale * math.sin(math.radians(angle)))) + 2
        nh = int(abs(h * scale * math.cos(math.radians(angle))) + abs(w * scale * math.sin(math.radians(angle)))) + 2
        M[0, 2] += nw / 2 - w / 2; M[1, 2] += nh / 2 - h / 2
        spr = cv2.warpAffine(spr, M, (nw, nh), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    h, w = spr.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    x1, y1 = x0 + w, y0 + h
    fx0, fy0, fx1, fy1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if fx0 >= fx1 or fy0 >= fy1:
        return
    s = spr[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
    a = s[..., 3:4].astype(np.float32) * (alpha / 255.0)
    roi = F[fy0:fy1, fx0:fx1]
    roi[:] = (roi * (1 - a) + s[..., :3] * a).astype(np.uint8)


def rounded_rect_sprite(w, h, r, fill, border=None, bw=0, alpha=255):
    img = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 26, 20 + w, 26 + h), r, fill=(0, 0, 0, 140))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((20, 20, 20 + w, 20 + h), r, fill=fill + (alpha,),
                        outline=(border + (255,)) if border else None, width=bw)
    return np.array(img)


@functools.lru_cache(256)
def chip(text, size=44, fg=WHITE, bg=CORAL, weight=800, padx=34, pady=16, border=None):
    f = font(weight, size)
    l, t_, r, b = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=f)
    w, h = r - l + 2 * padx, b - t_ + 2 * pady
    img = Image.fromarray(rounded_rect_sprite(w, h, min(h // 2, 22), bg, border, 4 if border else 0))
    ImageDraw.Draw(img).text((20 + padx - l, 20 + pady - t_), text, font=f, fill=fg + (255,))
    return np.array(img)


def stamp_sprite(text, size, color=RED, weight=900):
    return _stamp(text, size, color, weight)


@functools.lru_cache(32)
def _stamp(text, size, color, weight):
    f = font(weight, size)
    l, t_, r, b = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=f)
    pad = 34
    w, h = r - l + 2 * pad, b - t_ + 2 * pad
    img = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((10, 10, 10 + w, 10 + h), 16, outline=color + (255,), width=12)
    d.rounded_rectangle((26, 26, w - 6, h - 6), 8, outline=color + (200,), width=4)
    d.text((10 + pad - l, 10 + pad - t_), text, font=f, fill=color + (255,))
    a = np.array(img)
    # textura de sello: agujeros aleatorios en el alfa
    rng = np.random.default_rng(len(text))
    holes = (rng.random(a.shape[:2]) > 0.86).astype(np.float32)
    holes = cv2.GaussianBlur(holes, (0, 0), 1.6)
    a[..., 3] = (a[..., 3] * (1 - np.clip(holes * 1.6, 0, 0.75))).astype(np.uint8)
    return a


# ------------------------------------------------------------------ imágenes
def grade(img):
    x = img.astype(np.float32) / 255
    lum = x.mean(axis=2, keepdims=True)
    x = lum + (x - lum) * 0.82                       # leve desaturación
    x = np.clip((x - 0.5) * 1.12 + 0.5, 0, 1)        # contraste
    sh = (1 - lum) ** 2
    x[..., 2] += 0.05 * sh[..., 0]; x[..., 0] -= 0.02 * sh[..., 0]   # sombras frías (RGB)
    x *= 0.88
    return (np.clip(x, 0, 1) * 255).astype(np.uint8)


@functools.lru_cache(None)
def load(name):
    im = cv2.cvtColor(cv2.imread(os.path.join(IMG_DIR, name)), cv2.COLOR_BGR2RGB)
    return grade(im)


@functools.lru_cache(None)
def cover_base(name, margin=1.0):
    im = load(name)
    h, w = im.shape[:2]
    s = max(W / w, H / h) * margin
    return cv2.resize(im, (int(w * s + 0.5), int(h * s + 0.5)), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)


@functools.lru_cache(None)
def blurred_bg(name):
    b = cover_base(name)
    h, w = b.shape[:2]
    x0, y0 = (w - W) // 2, (h - H) // 2
    c = b[y0:y0 + H, x0:x0 + W]
    c = cv2.GaussianBlur(cv2.resize(c, (W // 4, H // 4)), (0, 0), 6)
    c = cv2.resize(c, (W, H))
    return (c * 0.45).astype(np.uint8)


@functools.lru_cache(None)
def card_base(name, fw):
    im = load(name)
    h, w = im.shape[:2]
    s = fw / w
    return cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)


def warp(src, ow, oh, zoom, fx, fy):
    """Zoom (>=1) sobre el punto relativo (fx, fy) de src, salida ow x oh."""
    h, w = src.shape[:2]
    sx, sy = fx * w, fy * h
    # limitar para que no se vea borde
    half_w, half_h = ow / (2 * zoom), oh / (2 * zoom)
    sx = min(max(sx, half_w), w - half_w); sy = min(max(sy, half_h), h - half_h)
    M = np.float32([[zoom, 0, ow / 2 - zoom * sx], [0, zoom, oh / 2 - zoom * sy]])
    return cv2.warpAffine(src, M, (ow, oh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def photo(F, sh, t, punch=0.0):
    u = clamp01((t - sh["t0"]) / (sh["t1"] - sh["t0"]))
    z0, z1 = sh.get("zoom", (1.0, 1.12))
    z = lerp(z0, z1, ease_in_out(u) * 0.6 + u * 0.4) * (1 + punch)
    f0 = sh.get("f0", (0.5, 0.5)); f1 = sh.get("f1", f0)
    fx, fy = lerp(f0[0], f1[0], u), lerp(f0[1], f1[1], u)
    if sh.get("mode", "cover") == "cover":
        F[:] = warp(cover_base(sh["img"]), W, H, z, fx, fy)
        if sh.get("dark"):
            F[:] = (F * (1 - sh["dark"])).astype(np.uint8)
        if sh.get("blur"):
            F[:] = (cv2.GaussianBlur(F, (0, 0), sh["blur"]) * 0.38).astype(np.uint8)
    else:  # tarjeta: fondo desenfocado + foto horizontal al centro
        F[:] = blurred_bg(sh["img"])
        fw = sh.get("fw", W)
        base = card_base(sh["img"], fw)
        bh, bw = base.shape[:2]
        ow = min(bw, W - 0)
        card = warp(base, ow, bh, z, fx, fy)
        cy = sh.get("cy", 820)
        y0 = int(cy - bh / 2); x0 = (W - ow) // 2
        # sombra
        sh_y0 = max(y0 - 30, 0)
        F[sh_y0:y0 + bh + 40] = (F[sh_y0:y0 + bh + 40] * 0.7).astype(np.uint8)
        F[y0:y0 + bh, x0:x0 + ow] = card
        cv2.line(F, (0, y0), (W, y0), CORAL, 5)
        cv2.line(F, (0, y0 + bh), (W, y0 + bh), CORAL, 5)


# ------------------------------------------------------------------ mapas
def load_topo(path):
    T = json.load(open(path))
    sc, tr = T["transform"]["scale"], T["transform"]["translate"]
    arcs = []
    for a in T["arcs"]:
        a = np.cumsum(np.array(a, dtype=np.float64), axis=0)
        arcs.append(a * sc + tr)
    def ring(idx):
        pts = []
        for i in idx:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.append(a if not pts else a[1:])
        return np.concatenate(pts)
    countries = {}
    for g in T["objects"]["countries"]["geometries"]:
        name = g["properties"]["name"]
        polys = g["arcs"] if g["type"] == "MultiPolygon" else ([g["arcs"]] if g["type"] == "Polygon" else [])
        rings = [ring(p[0]) for p in polys]  # sólo anillo exterior
        countries[name] = rings
    return countries

COUNTRIES = None

def merc(lat):
    lat = np.clip(lat, -80, 80)
    return np.degrees(np.log(np.tan(np.pi / 4 + np.radians(lat) / 2)))


def project(lonlat, cam, unwrap=False):
    lon = lonlat[:, 0].copy()
    if unwrap:
        lon = np.where(lon < 0, lon + 360, lon)
    x = (lon - cam[0]) * cam[2] + W / 2
    y = -(merc(lonlat[:, 1]) - merc(cam[1])) * cam[2] + cam[3]
    return np.stack([x, y], 1)


def draw_map(F, cam, colors, unwrap=False, default=(26, 52, 92), edge=(70, 110, 170)):
    # océano
    F[:] = ocean_bg()
    # retícula
    for lon in range(-180, 360, 10):
        p = project(np.array([[lon if not unwrap else lon, -80.0], [lon, 80.0]]), cam, False)
        cv2.line(F, tuple(p[0].astype(int)), tuple(p[1].astype(int)), (20, 42, 78), 1, cv2.LINE_AA)
    for lat in range(-80, 81, 10):
        p = project(np.array([[cam[0] - 400, lat], [cam[0] + 400, lat]], dtype=float), cam, False)
        cv2.line(F, (0, int(p[0, 1])), (W, int(p[0, 1])), (20, 42, 78), 1, cv2.LINE_AA)
    lon_view = (W / 2) / cam[2]
    for name, rings in COUNTRIES.items():
        if name == "Antarctica":
            continue
        col = colors.get(name, default)
        for r in rings:
            lon = r[:, 0]
            if unwrap:
                lon = np.where(lon < 0, lon + 360, lon)
                if lon.max() - lon.min() > 180:
                    continue
            if lon.max() < cam[0] - lon_view - 5 or lon.min() > cam[0] + lon_view + 5:
                continue
            p = project(r, cam, unwrap)
            if p[:, 1].max() < -50 or p[:, 1].min() > H + 50:
                continue
            pts = np.round(p * 8).astype(np.int32).reshape(-1, 1, 2)
            cv2.fillPoly(F, [pts], col, cv2.LINE_AA, shift=3)
            cv2.polylines(F, [pts], True, edge, 2, cv2.LINE_AA, shift=3)


@functools.lru_cache(None)
def ocean_bg():
    y = np.linspace(0, 1, H)[:, None, None]
    top = np.array([6, 14, 32], np.float32); bot = np.array([10, 28, 60], np.float32)
    g = top + (bot - top) * y
    return np.broadcast_to(g, (H, W, 3)).astype(np.uint8).copy()


def pin(F, x, y, t_since, color=CORAL, label=None, lx=0, ly=-90, size=46):
    if t_since < 0:
        return
    a = ease_back(t_since / 0.4)
    for k in range(3):  # pulsos
        ph = ((t_since * 0.9 + k / 3) % 1)
        r = int(16 + ph * 90)
        ov = F.copy()
        cv2.circle(ov, (int(x), int(y)), r, color, 4, cv2.LINE_AA)
        cv2.addWeighted(ov, (1 - ph) * 0.8, F, 1 - (1 - ph) * 0.8, 0, F)
    cv2.circle(F, (int(x), int(y)), int(15 * a), WHITE, -1, cv2.LINE_AA)
    cv2.circle(F, (int(x), int(y)), int(10 * a), color, -1, cv2.LINE_AA)
    if label:
        tx, ty = x + lx, y + ly
        cv2.line(F, (int(x), int(y)), (int(tx), int(ty + 30 * np.sign(-ly) if ly else ty)), WHITE, 3, cv2.LINE_AA)
        blit(F, chip(label, size, WHITE, color), tx, ty, scale=a)


# ------------------------------------------------------------------ subtítulos
FIX = {"vietel": "VIETTEL", "lea": "LEAH", "it": "HAITÍ"}

def build_captions():
    ws = json.load(open(WORDS))
    words = []
    for w in ws:
        txt = w["w"].strip()
        if txt == "%" and words:
            words[-1]["w"] += "%"; words[-1]["e"] = w["e"]; continue
        core = txt.strip(".,¿?").lower()
        if core in FIX:
            txt = txt.lower().replace(core, FIX[core])
        words.append(dict(w=txt.upper(), s=w["s"], e=w["e"]))
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        end_punct = w["w"][-1] in ".,?"
        if (len(cur) >= 3 or end_punct or nxt is None or nxt["s"] - w["e"] > 0.35
                or sum(len(x["w"]) for x in cur) > 16):
            chunks.append(cur); cur = []
    out = []
    for i, c in enumerate(chunks):
        s = c[0]["s"]
        e = chunks[i + 1][0]["s"] if i + 1 < len(chunks) else c[-1]["e"] + 0.4
        e = min(e, c[-1]["e"] + 0.6)
        out.append((s, e, c))
    return out


@functools.lru_cache(512)
def caption_sprite(words_tuple, active):
    size = 78
    f = font(800, size)
    texts = [w.rstrip(",.") for w in words_tuple]
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    space = 22
    widths = [tmp.textbbox((0, 0), x, font=f, stroke_width=8)[2] for x in texts]
    total = sum(widths) + space * (len(texts) - 1)
    if total > 1000:
        size = int(size * 1000 / total); f = font(800, size)
        widths = [tmp.textbbox((0, 0), x, font=f, stroke_width=8)[2] for x in texts]
        total = sum(widths) + space * (len(texts) - 1)
    hgt = size + 60
    img = Image.new("RGBA", (total + 60, hgt + 30), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img); ds = ImageDraw.Draw(sh)
    x = 30
    for i, (tx, wd) in enumerate(zip(texts, widths)):
        ds.text((x + 3, 22), tx, font=f, fill=(0, 0, 0, 200), stroke_width=8, stroke_fill=(0, 0, 0, 200))
        x += wd + space
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(img)
    x = 30
    for i, (tx, wd) in enumerate(zip(texts, widths)):
        col = (255, 214, 0) if i == active else WHITE
        d.text((x, 14), tx, font=f, fill=col + (255,), stroke_width=8, stroke_fill=(0, 0, 0, 255))
        x += wd + space
    return np.array(img)


CAPS = None

def draw_captions(F, t, y=1250):
    for s, e, c in CAPS:
        if s <= t < e:
            act = max([i for i, w in enumerate(c) if w["s"] <= t + 0.03] or [0])
            spr = caption_sprite(tuple(w["w"] for w in c), act)
            sc = lerp(0.82, 1.0, ease_back((t - s) / 0.16))
            blit(F, spr, W / 2, y, scale=sc)
            return


# ------------------------------------------------------------------ elementos de marca
@functools.lru_cache(None)
def logo_sprite():
    S = 4
    img = Image.new("RGBA", (420 * S, 120 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy, r = 52 * S, 52 * S, 34 * S
    d.ellipse((cx - r - 6 * S, cy - r - 6 * S, cx + r + 6 * S, cy + r + 6 * S), fill=(0, 0, 0, 90))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=WHITE + (255,), width=9 * S)
    d.line((cx + 25 * S, cy + 25 * S, cx + 46 * S, cy + 46 * S), fill=CORAL + (255,), width=12 * S)
    q = font(900, 44 * S)
    d.text((cx, cy + 2 * S), "?", font=q, fill=CORAL + (255,), anchor="mm")
    f = font(800, 30 * S)
    d.text((112 * S, 18 * S), "CAPITAL", font=f, fill=WHITE + (255,), stroke_width=1 * S, stroke_fill=(0, 0, 0, 120))
    d.text((112 * S, 52 * S), "CURIOSO", font=f, fill=CORAL + (255,), stroke_width=1 * S, stroke_fill=(0, 0, 0, 120))
    img = img.resize((420, 120), Image.LANCZOS)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 130), (0, 0), img)
    out = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), img)
    return np.array(out)


@functools.lru_cache(None)
def vignette():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W * 0.75)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2)
    v = 1 - np.clip(d - 0.45, 0, 1) ** 1.6 * 0.95
    return v[..., None].astype(np.float32)


@functools.lru_cache(None)
def grain_tiles():
    r = np.random.default_rng(3)
    return [r.normal(0, 7, (H // 2, W // 2)).astype(np.int16) for _ in range(6)]


def finish(F, fi):
    x = F.astype(np.float32) * vignette()
    g = grain_tiles()[fi % 6]
    g = cv2.resize(g.astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST)
    x += g[..., None]
    return np.clip(x, 0, 255).astype(np.uint8)


def glitch(F, amount, seed):
    r = np.random.default_rng(seed)
    dx = int(amount * 26)
    out = F.copy()
    out[..., 0] = np.roll(F[..., 0], dx, axis=1)
    out[..., 2] = np.roll(F[..., 2], -dx, axis=1)
    for _ in range(int(3 + amount * 8)):
        y = r.integers(0, H - 80); h = r.integers(10, 90)
        out[y:y + h] = np.roll(out[y:y + h], int(r.integers(-80, 80) * amount), axis=1)
    return out


# ------------------------------------------------------------------ plano de tomas
SHOTS = [
    dict(t0=4.5, t1=7.7, img="02_firma_indotel.jpg", mode="card", fw=1280, cy=750, zoom=(1.0, 1.08), f0=(0.5, 0.5)),
    dict(t0=7.7, t1=9.6, img="02_apreton_indotel.jpg", mode="card", fw=1380, cy=760, zoom=(1.0, 1.1), f0=(0.55, 0.5)),
    dict(t0=9.6, t1=12.3, img="02_firma.jpg", zoom=(1.05, 1.25), f0=(0.45, 0.55), f1=(0.5, 0.5), dark=0.35),
    dict(t0=12.3, t1=14.5, img="02_antena_5g.jpg", zoom=(1.0, 1.15), f0=(0.5, 0.6), f1=(0.5, 0.35)),
    dict(t0=14.5, t1=16.0, img="02_antena_5g_2.jpg", zoom=(1.18, 1.0), f0=(0.5, 0.3)),
    dict(t0=16.0, t1=17.4, img="03_viettel_sede_noche_2.jpg", mode="card", fw=1380, cy=760, zoom=(1.0, 1.12), f0=(0.5, 0.45)),
    dict(t0=17.4, t1=18.9, img="03_viettel_global_edificio.jpg", mode="card", fw=1300, cy=760, zoom=(1.12, 1.0), f0=(0.3, 0.6)),
    dict(t0=18.9, t1=21.75, img="03_hanoi.jpg", zoom=(1.0, 1.15), f0=(0.5, 0.45), dark=0.3),
    dict(t0=21.75, t1=29.1, img="04_leah_campos.jpg", zoom=(1.0, 1.14), f0=(0.5, 0.42), f1=(0.5, 0.36)),
    dict(t0=29.1, t1=33.0, img="04_servidores_2.jpg", zoom=(1.0, 1.15), f0=(0.5, 0.5), dark=0.25),
    dict(t0=33.0, t1=38.9, img="04_servidores.jpg", zoom=(1.15, 1.0), f0=(0.4, 0.5), dark=0.45),
    dict(t0=38.9, t1=42.5, img="04_santo_domingo.jpg", zoom=(1.0, 1.15), f0=(0.5, 0.55), dark=0.2),
    dict(t0=42.5, t1=46.6, img="04_santo_domingo_2.jpg", zoom=(1.12, 1.0), f0=(0.5, 0.5), dark=0.2),
    dict(t0=55.7, t1=59.4, img="06_torre_telecom.jpg", zoom=(1.0, 1.15), f0=(0.5, 0.65), f1=(0.5, 0.45)),
    dict(t0=63.0, t1=65.6, img="07_celular_2.jpg", zoom=(1.0, 1.15), f0=(0.45, 0.45)),
    dict(t0=65.6, t1=68.6, img="07_celular.jpg", zoom=(1.08, 1.25), f0=(0.6, 0.5), f1=(0.62, 0.42)),
    dict(t0=68.6, t1=MAIN_END, img="03_viettel_sede_noche.jpg", zoom=(1.0, 1.1), f0=(0.5, 0.45), blur=10),
]


def shot_at(t):
    for s in SHOTS:
        if s["t0"] <= t < s["t1"]:
            return s
    return None


# ------------------------------------------------------------------ escenas gráficas
def scene_hook(F, t):
    F[:] = ocean_bg()
    # retícula animada + resplandor rojo pulsante
    off = int(t * 40) % 80
    for y in range(-80 + off, H, 80):
        cv2.line(F, (0, y), (W, y), (18, 36, 70), 1)
    for x in range(0, W, 80):
        cv2.line(F, (x, 0), (x, H), (18, 36, 70), 1)
    pulse = 0.5 + 0.5 * math.sin(t * 6)
    glow = np.zeros((H // 8, W // 8, 3), np.float32)
    cv2.circle(glow, (W // 16, 1100 // 8), 60, (120, 10, 20), -1)
    glow = cv2.resize(cv2.GaussianBlur(glow, (0, 0), 20), (W, H))
    F[:] = np.clip(F + glow * (0.5 + 0.5 * pulse), 0, 255).astype(np.uint8)
    # triángulo de advertencia
    a = ease_back(t / 0.35)
    if a > 0:
        tri = warning_sprite()
        blit(F, tri, W / 2, 520, scale=a * (1 + 0.04 * pulse))
    for txt, at, y, size, col in (("ESTADOS UNIDOS", 0.0, 760, 104, WHITE),
                                  ("LO ADVIRTIÓ", 0.72, 890, 112, CORAL),
                                  ("REPÚBLICA DOMINICANA", 1.9, 1130, 74, WHITE)):
        u = (t - at) / 0.22
        if u > 0:
            blit(F, text_sprite(txt, size, col, 900), W / 2, y, alpha=clamp01(u), scale=lerp(1.6, 1.0, ease_out(u)))
    u = (t - 3.08) / 0.18
    if u > 0:
        blit(F, stamp_sprite("FIRMÓ IGUAL", 110), W / 2, 1350, alpha=clamp01(u * 2),
             scale=lerp(2.4, 1.0, ease_out(u)), angle=7)


@functools.lru_cache(None)
def warning_sprite():
    S = 3; s = 230
    img = Image.new("RGBA", (s * S, s * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(s * S / 2, 12 * S), (s * S - 12 * S, s * S - 24 * S), (12 * S, s * S - 24 * S)]
    d.polygon(pts, fill=CORAL + (255,))
    d.line(pts + [pts[0]], fill=WHITE + (255,), width=10 * S, joint="curve")
    d.text((s * S / 2, s * S * 0.6), "!", font=font(900, 120 * S), fill=WHITE + (255,), anchor="mm")
    img = img.resize((s, s), Image.LANCZOS)
    gl = Image.new("RGBA", (s + 120, s + 120), (0, 0, 0, 0))
    gl.paste(img, (60, 60), img)
    glow = gl.filter(ImageFilter.GaussianBlur(25))
    return np.array(Image.alpha_composite(glow, gl))


def lower_third(F, t, t0, name, role):
    u = ease_out((t - t0) / 0.45)
    if u <= 0:
        return
    y = 1500
    bar_w = int(940 * u)
    ov = F.copy()
    cv2.rectangle(ov, (60, y - 70), (60 + bar_w, y + 70), NAVY, -1)
    cv2.addWeighted(ov, 0.92, F, 0.08, 0, F)
    cv2.rectangle(F, (60, y - 70), (74, y + 70), CORAL, -1)
    if u > 0.5:
        a = clamp01((u - 0.5) * 2)
        n = text_sprite(name, 62, WHITE, 900, shadow=False)
        r = text_sprite(role, 34, (210, 220, 240), 600, shadow=False)
        blit(F, n, 100 + n.shape[1] / 2 - 30, y - 22, alpha=a)
        blit(F, r, 100 + r.shape[1] / 2 - 30, y + 36, alpha=a)


def counter(F, t):
    if t < 9.7:
        return
    u = ease_out((t - 10.06) / 0.9)
    val = int(round(107 * u))
    a = clamp01((t - 9.7) / 0.25)
    blit(F, text_sprite("US$", 70, WHITE, 800), W / 2, 470, alpha=a)
    blit(F, text_sprite(f"{val}", 300, (255, 214, 0), 900, glow=(255, 150, 0)), W / 2, 680, alpha=a,
         scale=1 + 0.08 * math.exp(-max(0, t - 10.96) * 8) * (t > 10.96))
    blit(F, text_sprite("MILLONES", 96, WHITE, 900), W / 2, 880, alpha=clamp01((t - 10.78) / 0.2),
         scale=lerp(1.4, 1, ease_out((t - 10.78) / 0.2)))


def badges(F, t):
    for txt, at, x in (("4G", 13.54, 330), ("5G", 14.64, 750)):
        u = (t - at) / 0.35
        if u <= 0:
            continue
        s = ease_back(u)
        spr = badge_sprite(txt)
        blit(F, spr, x, 560, scale=s * (1 + 0.03 * math.sin(t * 5)))
    u = (t - 12.92) / 0.3
    if u > 0:
        blit(F, chip("RED PROPIA", 52, WHITE, NAVY, border=CORAL), W / 2, 330, alpha=clamp01(u), scale=ease_back(u))


@functools.lru_cache(None)
def badge_sprite(txt):
    s = 300
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((40, 40, s - 40, s - 40), fill=CORAL + (255,), outline=WHITE + (255,), width=10)
    d.text((s / 2, s / 2 + 4), txt, font=font(900, 100), fill=WHITE + (255,), anchor="mm")
    gl = img.filter(ImageFilter.GaussianBlur(18))
    return np.array(Image.alpha_composite(gl, img))


@functools.lru_cache(None)
def vn_flag_sprite():
    w, h = 210, 140
    img = Image.new("RGBA", (w, h), RED + (255,))
    d = ImageDraw.Draw(img)
    cx, cy, R, r = w / 2, h / 2 + 4, 50, 20
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rr = R if k % 2 == 0 else r
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=GOLD + (255,))
    return np.array(img)


def ministry_card(F, t):
    u = (t - 19.1) / 0.3
    if u <= 0:
        return
    blit(F, text_sprite("PERTENECE AL", 56, WHITE, 800), W / 2, 330, alpha=clamp01(u))
    u2 = (t - 19.66) / 0.25
    if u2 > 0:
        blit(F, stamp_sprite("MINISTERIO DE DEFENSA", 70, CORAL), W / 2, 500, alpha=clamp01(u2 * 2),
             scale=lerp(2.0, 1.0, ease_out(u2)), angle=-3)
    u3 = (t - 20.7) / 0.3
    if u3 > 0:
        blit(F, vn_flag_sprite(), W / 2 - 230, 720, scale=ease_back(u3))
        blit(F, text_sprite("DE VIETNAM", 84, WHITE, 900), W / 2 + 110, 720, alpha=clamp01(u3))


def ring(F, t):
    if t < 35.3:
        return
    a = clamp01((t - 35.3) / 0.3)
    cx, cy, R = W // 2, 700, 250
    ov = F.copy()
    cv2.circle(ov, (cx, cy), R + 40, (8, 16, 34), -1, cv2.LINE_AA)
    cv2.addWeighted(ov, 0.75 * a, F, 1 - 0.75 * a, 0, F)
    cv2.ellipse(F, (cx, cy), (R, R), -90, 0, 360, (70, 80, 100), 38, cv2.LINE_AA)
    fill = ease_out((t - 36.95) / 0.7) * 72  # 20 % = 72°
    if fill > 0:
        cv2.ellipse(F, (cx, cy), (R, R), -90, 0, fill, CORAL, 40, cv2.LINE_AA)
    pct = int(round(fill / 3.6))
    blit(F, text_sprite(f"{pct}%", 170, WHITE, 900), cx, cy - 10, alpha=a)
    blit(F, text_sprite("SOLO CUBRE", 64, WHITE, 900), cx, cy - R - 120, alpha=clamp01((t - 35.8) / 0.25))


def check_list(F, t):
    u = (t - 39.2) / 0.35
    if u > 0:
        blit(F, chip("INDOTEL RESPONDE", 58, WHITE, NAVY, border=CORAL), W / 2, 340, scale=ease_back(u))
    if t < 42.5:
        items = (("✓  LEGAL", 42.08), ("✓  TRANSPARENTE", 42.54))
    else:
        items = (("+  COMPETENCIA", 44.62), ("+  MEJORES PRECIOS", 45.38))
    for k, (txt, at) in enumerate(items):
        v = (t - at) / 0.3
        if v > 0:
            blit(F, chip(txt.replace("✓", "✔"), 60, NAVY, WHITE, padx=40) if False else check_chip(txt), W / 2 - (1 - ease_out(v)) * 200,
                 540 + k * 150, alpha=clamp01(v * 2))


@functools.lru_cache(None)
def check_chip(txt):
    sym, label = txt.split("  ")
    f = font(800, 58)
    l, t_, r, b = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), label, font=f)
    w, h = r - l + 160, 110
    img = Image.fromarray(rounded_rect_sprite(w, h, 22, WHITE))
    d = ImageDraw.Draw(img)
    d.ellipse((38, 38, 38 + 74, 38 + 74), fill=(40, 170, 90, 255) if sym == "✓" else CORAL + (255,))
    if sym == "✓":
        d.line([(56, 76), (70, 92), (96, 58)], fill=WHITE + (255,), width=10, joint="curve")
    else:
        d.line([(75, 54), (75, 96)], fill=WHITE + (255,), width=10); d.line([(54, 75), (96, 75)], fill=WHITE + (255,), width=10)
    d.text((20 + 120 - l, 20 + (h - (b - t_)) / 2 - t_), label, font=f, fill=NAVY + (255,))
    return np.array(img)


def china_tag(F, t):
    u = (t - 35.46) / 0.2
    if 35.46 <= t < 38.9 and u > 0:
        spr = chip("CHINA", 56, WHITE, RED)
        blit(F, spr, W / 2, 1460, scale=ease_back(u))


def restriction_title(F, t):
    u = (t - 30.66) / 0.3
    if u > 0:
        blit(F, chip("RESTRICCIÓN", 58, WHITE, CORAL), W / 2, 360, scale=ease_back(u))
    v = (t - 31.8) / 0.35
    if v > 0:
        blit(F, text_sprite("tecnología de países", 60, WHITE, 700), W / 2, 520, alpha=clamp01(v))
        blit(F, text_sprite("NO CONFIABLES", 92, CORAL, 900), W / 2, 620, alpha=clamp01((t - 34.1) / 0.25),
             scale=lerp(1.5, 1, ease_out((t - 34.1) / 0.25)))


def scene_map_viettel(F, t):
    u = ease_in_out((t - 46.9) / 2.6)
    cam = (lerp(-70.5, -76, u), lerp(19, 2, u), lerp(70, 13, u), lerp(800, 860, u))
    colors = {}
    for name in ("Dominican Rep.",):
        if t > 47.0:
            colors[name] = CORAL
    if t > 49.5: colors["Haiti"] = (255, 140, 40)
    if t > 50.08: colors["Peru"] = (255, 140, 40)
    draw_map(F, cam, colors)
    def P(lon, lat):
        p = project(np.array([[lon, lat]], float), cam)[0]; return p[0], p[1]
    x, y = P(-70.2, 18.8)
    pin(F, x, y, t - 47.6, CORAL, "RD · AQUÍ", 120, -110, 44)
    x, y = P(-72.6, 18.9)
    pin(F, x, y, t - 49.5, (255, 140, 40), "HAITÍ", -150, -190, 44)
    x, y = P(-75.5, -10)
    pin(F, x, y, t - 50.08, (255, 140, 40), "PERÚ", -170, 120, 44)
    v = (t - 48.6) / 0.35
    if v > 0:
        blit(F, chip("VIETTEL YA OPERA EN…", 54, WHITE, RED), W / 2, 300, scale=ease_back(v))
    w = (t - 46.7) / 0.3
    if w > 0 and t < 48.6:
        blit(F, text_sprite("NO PASA SOLO AQUÍ", 70, WHITE, 900), W / 2, 300, alpha=clamp01(w))


CABLE = np.array([[-71.6, -33.0], [-90, -32], [-115, -26], [-145, -16], [-175, -6], [165, 4],
                  [145, 13], [128, 19], [114.2, 22.3]])


def cable_path():
    lon = np.where(CABLE[:, 0] < 0, CABLE[:, 0] + 360, CABLE[:, 0])
    pts = np.stack([lon, CABLE[:, 1]], 1)
    # interpolación suave
    s = np.linspace(0, 1, len(pts)); ss = np.linspace(0, 1, 300)
    return np.stack([np.interp(ss, s, pts[:, 0]), np.interp(ss, s, pts[:, 1])], 1)


def scene_chile(F, t):
    u = ease_in_out((t - 53.9) / 1.15)
    cam = (lerp(288.5, 205, u), lerp(-33, -2, u), lerp(16, 4.6, u), lerp(880, 820, u))
    colors = {"Chile": CORAL, "China": RED} if t > 50.9 else {}
    draw_map(F, cam, colors, unwrap=True)
    path = cable_path()
    p = project(path, cam)  # ya está desenvuelto
    k = int(len(p) * ease_out((t - 54.0) / 1.0))
    if k > 1:
        pts = np.round(p[:k] * 8).astype(np.int32)
        ov = F.copy()
        cv2.polylines(ov, [pts], False, (255, 214, 0), 16, cv2.LINE_AA, shift=3)
        ov = cv2.GaussianBlur(ov, (0, 0), 6)
        F[:] = np.maximum(F, (ov * 0.9).astype(np.uint8))
        for j in range(0, k - 1, 6):  # línea discontinua
            if (j // 6 + int(t * 12)) % 2 == 0:
                cv2.line(F, tuple(pts[j] // 8), tuple(pts[min(j + 6, k - 1)] // 8), (255, 230, 90), 5, cv2.LINE_AA)
    pc = project(np.array([[288.4, -33.0]]), cam)[0]
    pin(F, pc[0], pc[1], t - 50.94, CORAL, "CHILE", -60, 140, 50)
    if t > 54.9:
        ph = project(np.array([[114.2, 22.3]]), cam)[0]
        pin(F, ph[0], ph[1], t - 54.95, RED, "CHINA", 60, -110, 50)
    if t > 54.36:
        blit(F, chip("CABLE SUBMARINO", 54, NAVY, (255, 214, 0)), W / 2, 1480, scale=ease_back((t - 54.36) / 0.35))
    # visa revocada
    v = (t - 52.5) / 0.22
    if v > 0 and t < 54.4:
        a = 1 - clamp01((t - 54.1) / 0.3)
        blit(F, passport_sprite(), W / 2, 470, alpha=a * clamp01((t - 51.6) / 0.25))
        blit(F, stamp_sprite("VISA REVOCADA", 74, RED), W / 2 + 20, 520, alpha=a * clamp01(v * 2),
             scale=lerp(2.3, 1, ease_out(v)), angle=-12)
    elif 51.6 < t < 52.5:
        blit(F, passport_sprite(), W / 2, 470, alpha=clamp01((t - 51.6) / 0.25),
             scale=ease_back((t - 51.6) / 0.35))


@functools.lru_cache(None)
def passport_sprite():
    w, h = 360, 460
    img = Image.fromarray(rounded_rect_sprite(w, h, 24, NAVY, (200, 170, 90), 6))
    d = ImageDraw.Draw(img)
    d.text((20 + w / 2, 20 + 90), "VISA", font=font(900, 64), fill=(220, 190, 110, 255), anchor="mm")
    cx, cy = 20 + w / 2, 20 + 240
    d.ellipse((cx - 80, cy - 80, cx + 80, cy + 80), outline=(220, 190, 110, 255), width=8)
    d.ellipse((cx - 30, cy - 50, cx + 30, cy + 10), fill=(220, 190, 110, 255))
    d.pieslice((cx - 60, cy + 10, cx + 60, cy + 120), 180, 360, fill=(220, 190, 110, 255))
    d.text((20 + w / 2, 20 + 400), "MINISTRO", font=font(800, 40), fill=(220, 190, 110, 255), anchor="mm")
    return np.array(img)


def panama(F, t):
    u = (t - 56.3) / 0.35
    if u > 0:
        blit(F, chip("PANAMÁ", 64, WHITE, NAVY, border=CORAL), W / 2, 340, scale=ease_back(u))
    v = (t - 57.4) / 0.3
    if v > 0:
        blit(F, text_sprite("REEMPLAZANDO TORRES DE", 54, WHITE, 800), W / 2, 500, alpha=clamp01(v))
    v2 = (t - 58.4) / 0.25
    if v2 > 0:
        blit(F, text_sprite("HUAWEI", 140, WHITE, 900), W / 2, 650, alpha=clamp01(v2), scale=lerp(1.4, 1, ease_out(v2)))
    x = ease_out((t - 58.75) / 0.3)
    if x > 0:
        cv2.line(F, (250, 720), (int(250 + 580 * x), int(720 - 140 * x)), RED, 22, cv2.LINE_AA)
        cv2.line(F, (250, 580), (int(250 + 580 * x), int(580 + 140 * x)), RED, 22, cv2.LINE_AA)


def scene_powers(F, t):
    cam = (lerp(-78, -72, prog(t, 59.4, 3.6)), lerp(-8, -12, prog(t, 59.4, 3.6)), 11.5, 900)
    latam = ["Mexico", "Guatemala", "Belize", "Honduras", "El Salvador", "Nicaragua", "Costa Rica", "Panama",
             "Colombia", "Venezuela", "Guyana", "Suriname", "Ecuador", "Peru", "Brazil", "Bolivia", "Paraguay",
             "Chile", "Argentina", "Uruguay", "Cuba", "Dominican Rep.", "Haiti", "Jamaica", "Puerto Rico"]
    colors = {}
    for i, n in enumerate(latam):
        ph = math.sin(t * 7 + i * 1.7)
        if t > 60.0:
            colors[n] = (40, 90, 200) if ph > 0 else (190, 30, 45)
        else:
            colors[n] = (60, 80, 120)
    colors["United States of America"] = (30, 70, 170)
    colors["China"] = (190, 30, 45)
    draw_map(F, cam, colors)
    blit(F, chip("LATINOAMÉRICA", 60, WHITE, NAVY, border=CORAL), W / 2, 300, scale=ease_back((t - 59.46) / 0.35))
    u = (t - 61.3) / 0.25
    if u > 0:
        sh = 1 + 0.05 * math.sin(t * 30) * math.exp(-(t - 61.3) * 4)
        blit(F, text_sprite("EE.UU.", 110, (120, 170, 255), 900, glow=(40, 90, 255)), 260, 520, scale=ease_back(u) * sh)
        blit(F, text_sprite("VS", 90, WHITE, 900), W / 2, 520, scale=ease_back((t - 61.5) / 0.25))
        blit(F, text_sprite("CHINA", 110, (255, 110, 120), 900, glow=(255, 30, 50)), 830, 520,
             scale=ease_back((t - 61.6) / 0.25) * sh)


def sovereignty(F, t):
    u = (t - 66.5) / 0.25
    if u > 0:
        blit(F, text_sprite("SOBERANÍA", 130, WHITE, 900, glow=(60, 120, 255)), W / 2, 420, alpha=clamp01(u),
             scale=lerp(1.4, 1, ease_out(u)))
    v = (t - 67.2) / 0.2
    if v > 0:
        blit(F, text_sprite("o", 80, WHITE, 700), W / 2, 560, alpha=clamp01(v))
    w = (t - 67.65) / 0.2
    if w > 0:
        jitter = (np.random.default_rng(int(t * 30)).integers(-14, 14) if t < 68.3 else 0)
        blit(F, text_sprite("RIESGO", 150, CORAL, 900, glow=(255, 0, 30)), W / 2 + jitter, 710, alpha=clamp01(w),
             scale=lerp(1.6, 1, ease_out(w)))
    p = (t - 63.6) / 0.3
    if 63.6 < t < 65.6:
        blit(F, text_sprite("EN TU MANO", 96, WHITE, 900), W / 2, 420, alpha=clamp01(p), scale=lerp(1.3, 1, ease_out(p)))


def final_question(F, t):
    u = (t - 68.64) / 0.3
    if u > 0:
        blit(F, chip("COMENTA", 60, WHITE, CORAL), W / 2, 380, scale=ease_back(u))
    v = (t - 69.5) / 0.3
    if v > 0:
        blit(F, text_sprite("¿CONFÍAS EN", 104, WHITE, 900), W / 2, 590, alpha=clamp01(v), scale=lerp(1.3, 1, ease_out(v)))
        blit(F, text_sprite("VIETTEL?", 170, CORAL, 900, glow=(255, 30, 60)), W / 2, 760, alpha=clamp01(v),
             scale=lerp(1.3, 1, ease_out((t - 70.1) / 0.3)) if t > 70.1 else 0.001 + 0)
    for txt, at, x, bg, fg in (("SÍ", 70.66, 320, WHITE, NAVY), ("NO", 71.68, 760, CORAL, WHITE)):
        w = (t - at) / 0.35
        if w > 0:
            pul = 1 + 0.05 * math.sin((t - at) * 9)
            blit(F, button_sprite(txt, bg, fg), x, 1030, scale=ease_back(w) * pul)
    a = (t - 70.0) / 0.4
    if a > 0:
        yy = 1230 + 18 * math.sin(t * 8)
        blit(F, arrow_sprite(), W / 2, yy, alpha=clamp01(a))


@functools.lru_cache(None)
def button_sprite(txt, bg, fg):
    img = Image.fromarray(rounded_rect_sprite(320, 170, 40, bg))
    ImageDraw.Draw(img).text((20 + 160, 20 + 88), txt, font=font(900, 110), fill=fg + (255,), anchor="mm")
    return np.array(img)


@functools.lru_cache(None)
def arrow_sprite():
    img = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(80, 20), (80, 120)], fill=WHITE + (255,), width=16)
    d.polygon([(30, 90), (130, 90), (80, 145)], fill=WHITE + (255,))
    return np.array(img)


def date_and_names(F, t):
    u = (t - 4.74) / 0.35
    if u > 0 and t < 7.7:
        blit(F, chip("16 DE NOVIEMBRE", 56, WHITE, CORAL), W / 2, 300, scale=ease_back(u))
    v = (t - 5.2) / 0.4
    if v > 0 and t < 7.7:
        blit(F, text_sprite("Firma de la concesión · Claro, Indotel y Viettel", 36, (220, 225, 235), 600),
             W / 2, 1370 - 8 * ease_out(v), alpha=clamp01(v))
    w = (t - 7.76) / 0.3
    if w > 0 and t < 9.6:
        blit(F, text_sprite("VIETTEL", 150, CORAL, 900, glow=(255, 20, 40)), W / 2, 330, alpha=clamp01(w),
             scale=lerp(1.5, 1, ease_out(w)))
    x = (t - 16.05) / 0.3
    if 16.0 <= t < 18.9 and x > 0:
        blit(F, chip("¿QUIÉN ES VIETTEL?", 56, WHITE, RED), W / 2, 330, scale=ease_back(x))


def leah(F, t):
    lower_third(F, t, 23.5, "LEAH CAMPOS", "Embajadora de EE.UU. en República Dominicana")
    u = (t - 27.5) / 0.3
    if u > 0:
        blit(F, chip("DÍAS ANTES DE LA FIRMA", 52, WHITE, CORAL), W / 2, 330, scale=ease_back(u))
    v = (t - 25.6) / 0.25
    if 25.6 < t < 27.5 and v > 0:
        blit(F, chip("SE LO ADVIRTIÓ", 52, WHITE, NAVY, border=CORAL), W / 2, 330, scale=ease_back(v))


# ------------------------------------------------------------------ composición
def shake_offset(t):
    dx = dy = 0.0
    for at, kind in HITS:
        if kind in ("impact", "stamp", "impact_soft", "glitch") and 0 <= t - at < 0.35:
            k = (1 - (t - at) / 0.35) * (22 if kind == "impact" else 12)
            r = np.random.default_rng(int(t * 1000))
            dx += r.uniform(-k, k); dy += r.uniform(-k, k)
    return dx, dy


def render_base(F, t):
    """Fondo (foto o escena gráfica) + gráficos de la escena."""
    if t < 4.5:
        scene_hook(F, t); return
    if 46.6 <= t < 50.75:
        scene_map_viettel(F, t); return
    if 50.75 <= t < 55.7:
        scene_chile(F, t); return
    if 59.4 <= t < 63.0:
        scene_powers(F, t); return
    sh = shot_at(t)
    punch = 0.0
    if sh and sh["t0"] in SHOT_CUTS:
        punch = 0.10 * (1 - ease_out((t - sh["t0"]) / 0.3))
    if sh:
        photo(F, sh, t, punch)


def overlays(F, t):
    if 4.5 <= t < 16.0:
        date_and_names(F, t)
        if 9.6 <= t < 12.3: counter(F, t)
        if 12.3 <= t < 16.0: badges(F, t)
    elif 16.0 <= t < 21.75:
        date_and_names(F, t)
        if t >= 18.9: ministry_card(F, t)
    elif 21.75 <= t < 29.1:
        leah(F, t)
    elif 29.1 <= t < 33.0:
        restriction_title(F, t)
    elif 33.0 <= t < 38.9:
        ring(F, t); china_tag(F, t)
    elif 38.9 <= t < 46.6:
        check_list(F, t)
    elif 55.7 <= t < 59.4:
        panama(F, t)
    elif 63.0 <= t < 68.6:
        sovereignty(F, t)
    elif t >= 68.6:
        final_question(F, t)


def frame(fi):
    t = fi / FPS
    F = np.zeros((H, W, 3), np.uint8)
    render_base(F, t)
    # fundido corto en cortes internos
    for c in SHOT_CUTS:
        if 0 <= t - c < 0.12:
            P = np.zeros_like(F); render_base(P, c - 0.001)
            a = (t - c) / 0.12
            F[:] = (F * a + P * (1 - a)).astype(np.uint8)
    overlays(F, t)
    if 4.5 <= t < 68.6:
        cap_y = 1250 if not (33.0 <= t < 38.9) else 1300
        draw_captions(F, t, cap_y)
    # marca
    blit(F, logo_sprite(), 240, 120, alpha=0.95)
    F = finish(F, fi)
    # barra de progreso
    pw = int(W * min(t / MAIN_END, 1))
    F[0:8, :pw] = CORAL
    # glitch + destello en cortes de escena
    for c in SCENE_CUTS:
        d = t - c
        if -0.1 <= d < 0.13:
            amt = 1 - abs(d) / 0.13
            F = glitch(F, amt, fi)
            if 0 <= d < 0.07:
                F = np.clip(F.astype(np.int16) + int(110 * (1 - d / 0.07)), 0, 255).astype(np.uint8)
    for at, kind in HITS:
        if kind == "glitch" and 0 <= t - at < 0.25:
            F = glitch(F, 0.8 * (1 - (t - at) / 0.25), fi)
    dx, dy = shake_offset(t)
    if dx or dy:
        M = np.float32([[1.03, 0, dx - W * 0.015], [0, 1.03, dy - H * 0.015]])
        F = cv2.warpAffine(F, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    # fundido a azul de marca hacia el cierre
    fo = clamp01((t - (MAIN_END - 0.35)) / 0.35)
    if fo > 0:
        F = (F * (1 - fo) + np.array(NAVY, np.float32) * fo).astype(np.uint8)
    return F.tobytes()


def init():
    global COUNTRIES, CAPS
    COUNTRIES = load_topo(TOPO)
    CAPS = build_captions()


if __name__ == "__main__":
    from multiprocessing import Pool
    init()
    f0, f1 = int(RANGE[0] * FPS), int(round(RANGE[1] * FPS))
    if OUT.endswith(".png"):
        for fi in range(f0, f1):
            init()
            Image.frombytes("RGB", (W, H), frame(fi)).save(OUT.replace(".png", f"_{fi:05d}.png"))
        sys.exit()
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                           "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
    with Pool(os.cpu_count(), initializer=init) as pool:
        for k, b in enumerate(pool.imap(frame, range(f0, f1), chunksize=4)):
            ff.stdin.write(b)
            if k % 150 == 0:
                print(f"{(f0 + k) / FPS:.1f}s", flush=True)
    ff.stdin.close(); ff.wait()
    print("listo", OUT)
