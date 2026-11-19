"""Renderiza el video vertical 1080x1920 @30fps de Capital Curioso (escala 6x1).
Uso:
  python3 render.py                 # render completo -> capital_curioso_6x1.mp4
  python3 render.py --frames 1.0 9.5 # guarda fotogramas sueltos en build/preview/
"""
import os, sys, math, json, subprocess, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from timeline import *

W, H, FPS = 1080, 1920, 30
NFRAMES = int(round(TOTAL * FPS))
BUILD = os.path.join(HERE, "build")
os.makedirs(BUILD, exist_ok=True)
A = lambda p: os.path.join(HERE, "assets", p)

NAVY = (11, 31, 58); NAVY2 = (7, 20, 39); RED = (214, 40, 40); WHITE = (255, 255, 255)
PURPLE = (128, 62, 170); BLUE = (40, 110, 220); GREEN = (40, 180, 90); LAND = (25, 54, 94)
LAND_EDGE = (70, 104, 150); DARKRED = (150, 30, 36)

# ----------------------------------------------------------------- utilidades
FONT_FILES = {
    "anton": A("fonts/Anton.ttf"), "pblack": A("fonts/Poppins-Black.ttf"),
    "pxb": A("fonts/Poppins-ExtraBold.ttf"), "pb": A("fonts/Poppins-Bold.ttf"),
    "psb": A("fonts/Poppins-SemiBold.ttf"), "emoji": "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
}


@functools.lru_cache(None)
def font(k, size):
    return ImageFont.truetype(FONT_FILES[k], size)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else float(t >= a)


def eo3(u): return 1 - (1 - u) ** 3
def eio(u): return u * u * (3 - 2 * u)
def eback(u, c1=1.70158):
    c3 = c1 + 1
    return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2
def lerp(a, b, u): return a + (b - a) * u
def lerpc(c1, c2, u): return tuple(int(round(lerp(a, b, u))) for a, b in zip(c1, c2))


def with_alpha(im, a):
    if a >= 0.999: return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda p: int(p * a)))
    return im


def paste(cv, im, x0, y0):
    """alpha_composite tolerante a coordenadas fuera del lienzo."""
    x0, y0 = int(round(x0)), int(round(y0))
    w, h = im.size
    sx, sy = max(0, -x0), max(0, -y0)
    ex, ey = min(w, cv.width - x0), min(h, cv.height - y0)
    if ex <= sx or ey <= sy: return
    src = im if (sx, sy, ex, ey) == (0, 0, w, h) else im.crop((sx, sy, ex, ey))
    cv.alpha_composite(src, (x0 + sx, y0 + sy))


def place(cv, im, x, y, s=1.0, a=1.0, rot=0.0, anchor="mm"):
    if a <= 0.004 or s <= 0.01: return
    if abs(s - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    im = with_alpha(im, a)
    w, h = im.size
    ax = {"l": 0, "m": 0.5, "r": 1}[anchor[0]]
    ay = {"t": 0, "m": 0.5, "b": 1}[anchor[1]]
    paste(cv, im, x - w * ax, y - h * ay)


@functools.lru_cache(4096)
def text_img(s, fk, size, fill=WHITE, stroke=0, stroke_fill=(0, 0, 0), alpha=255):
    f = font(fk, size)
    l, t, r, b = f.getbbox(s, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + 4, b - t + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((-l + 2, -t + 2), s, font=f, fill=fill + (alpha,), stroke_width=stroke,
                            stroke_fill=stroke_fill + (alpha,))
    return im


@functools.lru_cache(64)
def emoji_img(ch, size):
    f = font("emoji", 109)
    im = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((6, 6), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((int(im.width * size / 109), int(im.height * size / 109)), Image.LANCZOS)


def shadow_of(im, radius=18, opacity=0.55, offset=(0, 10)):
    pad = radius * 3
    sh = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    a = Image.new("L", sh.size, 0)
    a.paste(im.getchannel("A"), (pad + offset[0], pad + offset[1]))
    a = a.filter(ImageFilter.GaussianBlur(radius)).point(lambda p: int(p * opacity))
    sh.putalpha(a)
    sh.alpha_composite(im, (pad, pad))
    return sh


def rrect(size, r, fill, outline=None, width=0, ss=2):
    w, h = size
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=fill, outline=outline, width=width * ss)
    return im.resize((w, h), Image.LANCZOS)


def kb(img, z, pan=(0.0, 0.0), out=(W, H)):
    """Ken Burns: ventana de zoom z (1 = imagen completa) con paneo pan∈[-1,1]."""
    iw, ih = img.size
    ww, wh = iw / z, ih / z
    cx = iw / 2 + pan[0] * (iw - ww) / 2
    cy = ih / 2 + pan[1] * (ih - wh) / 2
    x0, y0 = cx - ww / 2, cy - wh / 2
    return img.transform(out, Image.AFFINE, (ww / out[0], 0, x0, 0, wh / out[1], y0), resample=Image.BILINEAR)


def load_cover(path, S=1.3, focus=(0.5, 0.5), bright=0.5, tint=0.3, sat=0.85, blur=0, size=(W, H)):
    im = Image.open(path)
    tw, th = int(size[0] * S), int(size[1] * S)
    im.draft("RGB", (tw, th))
    im = im.convert("RGB")
    sc = max(tw / im.width, th / im.height)
    im = im.resize((max(tw, int(im.width * sc + 0.5)), max(th, int(im.height * sc + 0.5))), Image.LANCZOS)
    x0 = int(clamp(focus[0] * im.width - tw / 2, 0, im.width - tw))
    y0 = int(clamp(focus[1] * im.height - th / 2, 0, im.height - th))
    im = im.crop((x0, y0, x0 + tw, y0 + th))
    if blur: im = im.filter(ImageFilter.GaussianBlur(blur))
    im = ImageEnhance.Color(im).enhance(sat)
    im = ImageEnhance.Brightness(im).enhance(bright)
    if tint: im = Image.blend(im, Image.new("RGB", im.size, NAVY), tint)
    return im.convert("RGBA")


def gradient_bg():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(-1, 1, W)[None, :]
    r = np.sqrt(x ** 2 + ((y - 0.5) * 1.8) ** 2)
    top = np.array(NAVY, float); bot = np.array(NAVY2, float)
    base = top[None, None, :] * (1 - y[..., None]) + bot[None, None, :] * y[..., None]
    base = base + (1 - np.clip(r, 0, 1))[..., None] * np.array([10, 22, 40.0])
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    return im


# ----------------------------------------------------------------- recursos globales
BG = {}


def prep():
    if BG: return
    BG["trab"] = load_cover(A("img/trabajadores.jpg"), focus=(0.6, 0.55), bright=0.55, tint=0.35, sat=1)
    BG["bandera"] = load_cover(A("img/bandera.jpg"), focus=(0.35, 0.35), bright=0.45, tint=0.35, blur=14)
    BG["planalto"] = load_cover(A("img/planalto.jpg"), focus=(0.5, 0.45), bright=0.5, tint=0.45, blur=9)
    BG["fabrica"] = load_cover(A("img/fabrica.jpg"), focus=(0.36, 0.5), bright=0.5, tint=0.3)
    BG["familia"] = load_cover(A("img/familia.jpg"), focus=(0.55, 0.62), bright=0.55, tint=0.25, sat=0.9)
    BG["saopaulo"] = load_cover(A("img/saopaulo.jpg"), focus=(0.5, 0.5), bright=0.45, tint=0.35)
    BG["calendario"] = load_cover(A("img/calendario.jpg"), focus=(0.45, 0.55), bright=0.42, tint=0.45, blur=8)
    BG["grad"] = gradient_bg()
    lula = Image.open(A("img/lula.jpg")).convert("RGB")
    BG["lula"] = lula.resize((int(880 * 1.12), int(880 * 1.12 * lula.height / lula.width)), Image.LANCZOS).convert("RGBA")
    # grano de película y viñeta
    rng = np.random.default_rng(3)
    BG["grain"] = [np.asarray(Image.fromarray((rng.normal(128, 40, (H // 2, W // 2))).clip(0, 255).astype(np.uint8))
                              .resize((W, H), Image.BILINEAR), np.float32)[..., None] - 128 for _ in range(6)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 * 0.9 + ((yy - H / 2) / (H / 2)) ** 2)
    BG["vig"] = (1 - 0.55 * np.clip((r - 0.55) / 0.9, 0, 1) ** 1.6)[..., None].astype(np.float32)
    # clip de cierre
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", A("capital_curioso_cierre.mp4"), "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    BG["close"] = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    prep_map()


# ----------------------------------------------------------------- mapa
MAP = {}


def merc(lat):
    lat = max(-80, min(80, lat))
    return math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def prep_map():
    d = json.load(open(A("data/countries.geojson"), encoding="utf-8"))
    polys = []
    for f in d["features"]:
        code = f["properties"]["ADM0_A3"]
        g = f["geometry"]
        rings = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in rings:
            ring = np.array(poly[0], float)
            if ring[:, 0].max() < -180 or ring[:, 0].min() > -10: continue
            if ring[:, 1].min() > 75: continue
            p = np.stack([ring[:, 0], np.vectorize(merc)(ring[:, 1])], 1)
            polys.append((code, p))
    MAP["polys"] = polys


def map_layer(clon, clat, ppd, fills, cy=1080, glow=None, ss=2):
    cm = merc(clat)
    lay = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    # retícula
    for lon in range(-180, 0, 10):
        x = (W / 2 + (lon - clon) * ppd) * ss
        if 0 <= x <= W * ss: d.line([(x, 0), (x, H * ss)], fill=(255, 255, 255, 14), width=ss)
    for lat in range(-60, 81, 10):
        y = (cy - (merc(lat) - cm) * ppd) * ss
        if 0 <= y <= H * ss: d.line([(0, y), (W * ss, y)], fill=(255, 255, 255, 14), width=ss)
    glow_l = None
    if glow:
        glow_l = Image.new("RGBA", (W // 2, H // 2), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_l)
    for code, p in MAP["polys"]:
        xs = W / 2 + (p[:, 0] - clon) * ppd
        ys = cy - (p[:, 1] - cm) * ppd
        if xs.max() < -50 or xs.min() > W + 50 or ys.max() < -50 or ys.min() > H + 50: continue
        pts = list(zip((xs * ss).tolist(), (ys * ss).tolist()))
        if len(pts) < 3: continue
        d.polygon(pts, fill=fills.get(code, LAND + (255,)), outline=LAND_EDGE + (255,), width=ss)
        if glow and code in glow:
            gd.polygon(list(zip((xs / 2).tolist(), (ys / 2).tolist())), fill=glow[code])
    lay = lay.reduce(ss)
    if glow_l is not None:
        g = glow_l.filter(ImageFilter.GaussianBlur(14)).resize((W, H), Image.BILINEAR)
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.alpha_composite(g); out.alpha_composite(g); out.alpha_composite(lay)
        return out
    return lay


def map_xy(lon, lat, clon, clat, ppd, cy=1080):
    return W / 2 + (lon - clon) * ppd, cy - (merc(lat) - merc(clat)) * ppd


# ----------------------------------------------------------------- iconos
@functools.lru_cache(None)
def person_icon(color, s=1.0):
    ss = 4; w, h = int(64 * s), int(92 * s)
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hr = 16 * s * ss
    d.ellipse((w * ss / 2 - hr, 2 * ss, w * ss / 2 + hr, 2 * ss + 2 * hr), fill=color + (255,))
    d.rounded_rectangle((2 * s * ss, 42 * s * ss, (w - 2 * s) * ss, (h + 30) * ss), radius=28 * s * ss, fill=color + (255,))
    return im.resize((w, h), Image.LANCZOS)


@functools.lru_cache(None)
def briefcase_icon(color=WHITE, s=1.0):
    ss = 4; w, h = int(70 * s), int(56 * s)
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    S = lambda v: v * s * ss
    d.rounded_rectangle((S(22), S(2), S(48), S(16)), radius=S(5), outline=color + (255,), width=int(S(5)))
    d.rounded_rectangle((S(2), S(12), S(68), S(54)), radius=S(8), fill=color + (255,))
    d.rectangle((S(2), S(28), S(68), S(31)), fill=(0, 0, 0, 0))
    return im.resize((w, h), Image.LANCZOS)


@functools.lru_cache(None)
def sun_icon(color=(255, 214, 90), s=1.0):
    ss = 4; w = int(72 * s)
    im = Image.new("RGBA", (w * ss, w * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = w * ss / 2; r = 15 * s * ss
    d.ellipse((c - r, c - r, c + r, c + r), fill=color + (255,))
    for k in range(8):
        a = k * math.pi / 4
        d.line([(c + math.cos(a) * r * 1.5, c + math.sin(a) * r * 1.5), (c + math.cos(a) * r * 2.25, c + math.sin(a) * r * 2.25)],
               fill=color + (255,), width=int(5 * s * ss))
    return im.resize((w, w), Image.LANCZOS)


@functools.lru_cache(None)
def check_badge(d_=64, bg=GREEN):
    ss = 4; s = d_ * ss
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, 0, s - 1, s - 1), fill=bg + (255,), outline=WHITE + (255,), width=int(s * 0.07))
    d.line([(s * 0.27, s * 0.52), (s * 0.44, s * 0.68), (s * 0.74, s * 0.34)], fill=WHITE + (255,), width=int(s * 0.12), joint="curve")
    return im.resize((d_, d_), Image.LANCZOS)


@functools.lru_cache(None)
def mini_cal(label):
    w, h = 116, 124
    im = rrect((w, h), 16, WHITE + (255,))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, 40), 16, fill=RED + (255,)); d.rectangle((0, 22, w - 1, 40), fill=RED + (255,))
    for x in (30, w - 30):
        d.rounded_rectangle((x - 5, -2, x + 5, 14), 4, fill=NAVY + (255,))
    t = text_img(label, "pxb", 40, NAVY)
    im.alpha_composite(t, ((w - t.width) // 2, 52))
    return im


@functools.lru_cache(None)
def bill_img():
    w, h = 270, 140
    im = rrect((w, h), 14, (62, 160, 96, 255))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, w - 11, h - 11), 10, outline=(200, 240, 210, 255), width=3)
    d.ellipse((w / 2 - 44, h / 2 - 44, w / 2 + 44, h / 2 + 44), fill=(40, 120, 70, 255), outline=(200, 240, 210, 255), width=3)
    t = text_img("R$", "pxb", 44, (230, 255, 235))
    im.alpha_composite(t, (int(w / 2 - t.width / 2), int(h / 2 - t.height / 2)))
    for x in (34, w - 34):
        d.ellipse((x - 9, h / 2 - 9, x + 9, h / 2 + 9), outline=(200, 240, 210, 255), width=3)
    return im


@functools.lru_cache(None)
def lupa_logo(sz=68):
    ss = 4; s = sz * ss
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, 0, s - 1, s - 1), fill=NAVY + (255,))
    c = s * 0.45; r = s * 0.24
    d.line([(c + r * 0.7, c + r * 0.7), (s * 0.8, s * 0.8)], fill=(242, 66, 76, 255), width=int(s * 0.1))
    d.ellipse((c - r, c - r, c + r, c + r), outline=WHITE + (255,), width=int(s * 0.07))
    im = im.resize((sz, sz), Image.LANCZOS)
    q = text_img("?", "pxb", int(sz * 0.34), (242, 66, 76))
    im.alpha_composite(q, (int(sz * 0.45 - q.width / 2), int(sz * 0.45 - q.height / 2)))
    return im


# ----------------------------------------------------------------- ESCENA 1: gancho
CELLS = []
for i in range(7):
    if i < 4: x0, y0 = 67 + i * 242, 1000
    else: x0, y0 = 188 + (i - 4) * 242, 1242
    CELLS.append((x0, y0, x0 + 220, y0 + 220))
DAYS = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
CELL_ORDER = [0, 1, 2, 3, 4, 5]  # rojas; la 6 (DOM) es azul
IMPACT_C = (540, 1230)


@functools.lru_cache(None)
def cell_img(i):
    red = i < 6
    col = RED if red else (30, 95, 200)
    im = shadow_of(rrect((220, 220), 22, col + (255,)), 14, 0.5, (0, 8))
    pad = (im.width - 220) // 2
    t = text_img(DAYS[i], "pb", 34, (255, 255, 255), alpha=220)
    im.alpha_composite(t, (pad + 18, pad + 14))
    ic = briefcase_icon(WHITE, 1.0) if red else sun_icon((255, 214, 90), 1.15)
    im.alpha_composite(ic, (pad + 110 - ic.width // 2, pad + 102 - ic.height // 2))
    lab = text_img("TRABAJO" if red else "DESCANSO", "pxb", 30 if red else 28, WHITE)
    im.alpha_composite(lab, (pad + 110 - lab.width // 2, pad + 160))
    return im


def make_shards():
    rng = np.random.default_rng(11)
    shards = []
    for i in range(6):
        x0, y0, x1, y1 = CELLS[i]
        n = 4
        gx = np.linspace(x0, x1, n); gy = np.linspace(y0, y1, n)
        P = np.zeros((n, n, 2))
        for a in range(n):
            for b in range(n):
                jx = rng.uniform(-22, 22) if 0 < a < n - 1 else 0
                jy = rng.uniform(-22, 22) if 0 < b < n - 1 else 0
                P[a, b] = (gx[a] + jx, gy[b] + jy)
        for a in range(n - 1):
            for b in range(n - 1):
                q = [P[a, b], P[a + 1, b], P[a + 1, b + 1], P[a, b + 1]]
                for tri in ([q[0], q[1], q[2]], [q[0], q[2], q[3]]):
                    tri = np.array(tri); c = tri.mean(0)
                    v = c - np.array(IMPACT_C); v = v / (np.linalg.norm(v) + 1e-6)
                    vel = v * rng.uniform(500, 1400) + np.array([rng.uniform(-150, 150), -rng.uniform(250, 650)])
                    shade = rng.uniform(0.75, 1.15)
                    col = tuple(int(clamp(ch * shade, 0, 255)) for ch in RED)
                    shards.append((tri - c, c, vel, rng.uniform(-9, 9), col))
    return shards


SHARDS = make_shards()


def scene1(t):
    cv = kb(BG["trab"], lerp(1.0, 1.22, t / S1[1]), (0.1, -0.2 * t / S1[1]))
    cv = cv.copy()
    # contador 83 AÑOS
    u = eo3(prog(t, 0.1, 1.15))
    val = int(round(83 * u))
    mv = eio(prog(t, 2.35, 2.85))
    pop = 1 + 0.12 * math.sin(math.pi * prog(t, 1.15, 1.4))
    num = text_img(str(val), "anton", 360, WHITE, 0)
    place(cv, shadow_of(num, 20, 0.6), 540, lerp(760, 610, mv), lerp(1.0, 0.58, mv) * pop, prog(t, 0.0, 0.15))
    ao = text_img("AÑOS", "anton", 150, RED)
    ua = prog(t, 1.0, 1.3)
    place(cv, shadow_of(ao, 16, 0.6), 540, lerp(1010, 790, mv), lerp(1.0, 0.62, mv) * lerp(1.5, 1, eo3(ua)), ua)
    pill = rrect((560, 76), 38, NAVY + (235,))
    pt = text_img("CON ESCALA 6x1 EN BRASIL", "pb", 34, WHITE)
    pill = pill.copy(); pill.alpha_composite(pt, ((560 - pt.width) // 2, (76 - pt.height) // 2))
    up = prog(t, 1.5, 1.8)
    place(cv, pill, 540, 1140 + 30 * (1 - eo3(up)), 1, up * (1 - prog(t, 2.3, 2.5)))
    # calendario semanal
    if t >= 2.45:
        hu = eo3(prog(t, 2.45, 2.75))
        head = rrect((946, 74), 18, NAVY + (230,)).copy()
        ImageDraw.Draw(head).rectangle((0, 0, 946, 8), fill=RED + (255,))
        ht = text_img("UNA SEMANA CON LA ESCALA 6x1", "pxb", 36, WHITE)
        head.alpha_composite(ht, ((946 - ht.width) // 2, 14 + (60 - ht.height) // 2))
        place(cv, head, 540, 945 - 20 * (1 - hu), 1, hu)
        imp = T["acabo"]
        for i in range(7):
            x0, y0, x1, y1 = CELLS[i]
            ts = 2.75 + i * 0.12 if i < 6 else T["descansar"] + 0.05
            if t < ts: continue
            cu = prog(t, ts, ts + 0.3)
            if i < 6 and t >= imp:
                # hueco punteado donde estaba la casilla
                d = ImageDraw.Draw(cv)
                a = int(120 * prog(t, imp + 0.25, imp + 0.6))
                if a > 0:
                    for k in range(0, 220, 22):
                        for (xa, ya, xb, yb) in ((x0 + k, y0, x0 + k + 11, y0), (x0 + k, y1, x0 + k + 11, y1),
                                                 (x0, y0 + k, x0, y0 + k + 11), (x1, y0 + k, x1, y0 + k + 11)):
                            d.line([(xa, ya), (xb, yb)], fill=(255, 255, 255, a), width=3)
                continue
            s = eback(cu) if cu < 1 else 1
            if i == 6 and t > imp:
                s *= 1 + 0.08 * math.sin(math.pi * prog(t, imp + 0.1, imp + 0.5))
            place(cv, cell_img(i), (x0 + x1) / 2, (y0 + y1) / 2 + 4, max(0.01, s * 0.5 + 0.5 if cu < 1 else s), min(1, cu * 2.5))
        if t >= imp:
            dt = t - imp
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            a = 1 - prog(dt, 0.45, 0.9)
            for rel, c, vel, w, col in SHARDS:
                pos = c + vel * dt + np.array([0, 0.5 * 2600 * dt * dt])
                ang = w * dt; ca, sa = math.cos(ang), math.sin(ang)
                pts = [(pos[0] + p[0] * ca - p[1] * sa, pos[1] + p[0] * sa + p[1] * ca) for p in rel]
                d.polygon(pts, fill=col + (int(255 * a),))
            cv.alpha_composite(lay)
    # impacto: destello + temblor
    if T["acabo"] <= t < T["acabo"] + 0.14:
        fl = Image.new("RGBA", (W, H), (255, 255, 255, int(150 * (1 - prog(t, T["acabo"], T["acabo"] + 0.14)))))
        cv.alpha_composite(fl)
    return cv


def shake(t):
    """desplazamiento por impacto"""
    out = (0, 0)
    for t0, amp, dur in ((T["acabo"], 34, 0.4), (T["vigente"] + 0.22, 14, 0.25)):
        if t0 <= t < t0 + dur:
            k = (1 - (t - t0) / dur) ** 2
            out = (amp * k * math.sin((t - t0) * 90), amp * k * math.cos((t - t0) * 73))
    return out


# ----------------------------------------------------------------- ESCENA 2: la noticia
@functools.lru_cache(None)
def lower_third():
    t1 = text_img("LUIZ INÁCIO LULA DA SILVA", "pxb", 46, WHITE)
    t2 = text_img("Presidente de Brasil", "psb", 38, WHITE)
    w1, w2 = t1.width + 60, t2.width + 60
    a = Image.new("RGBA", (max(w1, w2) + 20, 160), (0, 0, 0, 0))
    b1 = rrect((w1, 86), 6, RED + (255,)); b1.alpha_composite(t1, (30, (86 - t1.height) // 2))
    b2 = rrect((w2, 64), 6, NAVY + (245,)); b2.alpha_composite(t2, (30, (64 - t2.height) // 2))
    ImageDraw.Draw(b2).rectangle((0, 0, 8, 64), fill=WHITE + (255,))
    return b1, b2


@functools.lru_cache(None)
def decree_card(ul):
    w, h = 900, 470
    im = rrect((w, h), 18, (250, 248, 242, 255)).copy()
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 10), fill=(0, 146, 63, 255))
    d.rectangle((0, 10, w, 18), fill=(254, 221, 0, 255))
    t = text_img("REPÚBLICA FEDERATIVA DO BRASIL · DIÁRIO OFICIAL", "pb", 24, (110, 110, 120))
    im.alpha_composite(t, (50, 44))
    t = text_img("DECRETO 13.173/2026", "anton", 92, NAVY)
    im.alpha_composite(t, (48, 88))
    t2 = text_img("Fin de la escala 6x1", "pxb", 54, RED)
    im.alpha_composite(t2, (50, 212))
    if ul > 0:
        x0 = 50 + text_img("Fin de la escala ", "pxb", 54, RED).width - 6
        x1 = 50 + t2.width
        d.rounded_rectangle((x0, 286, x0 + (x1 - x0) * ul, 298), 6, fill=RED + (255,))
    for k, ln in enumerate((760, 700, 740)):
        d.rounded_rectangle((50, 330 + k * 30, 50 + ln, 342 + k * 30), 6, fill=(205, 208, 215, 255))
    d.line([(560, 440), (840, 440)], fill=(120, 120, 130, 255), width=2)
    return shadow_of(im.rotate(1.6, Image.BICUBIC, expand=True), 22, 0.6, (0, 14))


@functools.lru_cache(None)
def stamp_img():
    w, h = 470, 230
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    col = (200, 24, 30, 255)
    d.rounded_rectangle((6, 6, w - 7, h - 7), 22, outline=col, width=10)
    d.rounded_rectangle((22, 22, w - 23, h - 23), 14, outline=col, width=4)
    t1 = text_img("VIGENTE", "anton", 74, (200, 24, 30)); t2 = text_img("DESDE 1943", "anton", 74, (200, 24, 30))
    im.alpha_composite(t1, ((w - t1.width) // 2, 30)); im.alpha_composite(t2, ((w - t2.width) // 2, 112))
    rng = np.random.default_rng(5)
    noise = rng.random((h // 3, w // 3))
    m = Image.fromarray((noise > 0.2).astype(np.uint8) * 255).resize((w, h), Image.NEAREST).filter(ImageFilter.GaussianBlur(1.2))
    a = np.minimum(np.asarray(im.getchannel("A")), np.asarray(m)).astype(np.uint8)
    im.putalpha(Image.fromarray((a * 0.92).astype(np.uint8)))
    return im.rotate(12, Image.BICUBIC, expand=True)


def scene2(t):
    t_lula = T["lula"]
    if t < t_lula + 0.25:
        cv = BG["grad"].copy()
        u = eio(prog(t, S2[0] + 0.05, t_lula - 0.1))
        clon, clat, ppd = lerp(-60, -53, u), lerp(-22, -13, u), lerp(5.6, 11.5, u)
        ru = prog(t, 9.15, 9.6)
        pulse = 0.5 + 0.5 * math.sin((t - 9.15) * 7)
        fills = {"BRA": lerpc(LAND, RED, ru) + (255,)}
        glow = {"BRA": RED + (int(200 * ru * (0.7 + 0.3 * pulse)),)} if ru > 0 else None
        cv.alpha_composite(map_layer(clon, clat, ppd, fills, 1080, glow))
        lu = prog(t, 9.55, 9.85)
        if lu > 0:
            x, y = map_xy(-52, -10.5, clon, clat, ppd, 1080)
            place(cv, shadow_of(text_img("BRASIL", "anton", 120, WHITE), 14, 0.7), x, y, eback(lu), lu)
        if t > t_lula - 0.1:  # salida del mapa
            o = prog(t, t_lula - 0.1, t_lula + 0.25)
            base = cv
            cv = kb(BG["bandera"], 1.0)
            cv = cv.copy()
            place(cv, base, W / 2, H / 2, 1 + 0.5 * o, 1 - o)
        if t < t_lula - 0.1: return cv
    else:
        cv = kb(BG["bandera"], lerp(1.0, 1.15, prog(t, t_lula, S2[1])), (0, -0.3)).copy()
    # tarjeta de Lula
    cu = eo3(prog(t, t_lula - 0.05, t_lula + 0.45))
    lz = lerp(1.0, 1.1, prog(t, t_lula, S2[1]))
    photo = kb(BG["lula"], lz, (0, -0.6), out=(880, 1190))
    fr = Image.new("RGBA", (892, 1202), WHITE + (255,)); fr.paste(photo, (6, 6))
    fr = shadow_of(fr, 24, 0.65, (0, 16))
    place(cv, fr, 540, 1068 + 260 * (1 - cu), 1, cu)
    # rótulo de nombre
    b1, b2 = lower_third()
    lu1 = eo3(prog(t, t_lula + 0.3, t_lula + 0.65)); lu2 = eo3(prog(t, t_lula + 0.45, t_lula + 0.8))
    if lu1 > 0:
        cw = int(b1.width * lu1)
        if cw > 2: paste(cv, b1.crop((0, 0, cw, b1.height)), 60, 1060)
    if lu2 > 0:
        cw = int(b2.width * lu2)
        if cw > 2: paste(cv, b2.crop((0, 0, cw, b2.height)), 60, 1150)
    # documento del decreto
    du = prog(t, T["decreto"] - 0.1, T["decreto"] + 0.35)
    if du > 0:
        ul = round(eio(prog(t, T["x61"], T["x61"] + 0.45)) * 12) / 12
        place(cv, decree_card(ul), 540, 1490 + 700 * (1 - eback(du)), 1, min(1, du * 3))
    # sello VIGENTE DESDE 1943
    land = T["vigente"] + 0.22
    su = prog(t, land - 0.2, land)
    if su > 0:
        s = lerp(2.6, 1.0, su ** 2)
        place(cv, stamp_img(), 790, 1700, s, min(1, su * 2.2))
    return cv


# ----------------------------------------------------------------- ESCENA 3: qué cambia
BARS = [  # (x centro, valor, etiqueta, color, t_inicio, t_final)
    (245, 44, "HOY", RED, T["h44"] - 0.35, T["h44"] + 0.3),
    (540, 42, "16 DIC 2026", PURPLE, T["h42"] - 0.35, T["h42"] + 0.3),
    (835, 40, "DIC 2027", BLUE, T["h40"] - 0.6, T["h40"] + 0.25),
]
BASE_Y = 1170; PXH = 9.4


@functools.lru_cache(None)
def bar_img(color, h):
    w = 210
    im = Image.new("RGBA", (w, max(2, h)), (0, 0, 0, 0))
    if h < 2: return im
    arr = np.zeros((max(2, h), w, 4), np.uint8)
    g = np.linspace(1.25, 0.85, max(2, h))[:, None]
    for c in range(3): arr[..., c] = np.clip(color[c] * g, 0, 255)
    arr[..., 3] = 255
    im = Image.fromarray(arr, "RGBA")
    m = rrect((w, max(2, h) + 20), 16, (255, 255, 255, 255)).crop((0, 0, w, max(2, h))).getchannel("A")
    im.putalpha(m)
    return im


def scene3(t):
    t0 = S3[0]
    cv = kb(BG["planalto"], lerp(1.0, 1.18, prog(t, t0, S3[1])), (0, 0.2)).copy()
    # título
    tu = prog(t, T["que_cambia"] - 0.05, T["que_cambia"] + 0.3)
    mv = eio(prog(t, 18.0, 18.5))
    title = shadow_of(text_img("¿QUÉ CAMBIA?", "anton", 150, WHITE), 16, 0.6)
    ty = lerp(820, 500, mv)
    place(cv, title, 540, ty, lerp(1, 0.6, mv) * lerp(1.4, 1, eo3(tu)), tu)
    lw = 420 * eo3(prog(t, T["que_cambia"] + 0.2, T["que_cambia"] + 0.5)) * lerp(1, 0.6, mv)
    if lw > 1:
        ImageDraw.Draw(cv).rounded_rectangle((540 - lw / 2, ty + lerp(98, 60, mv), 540 + lw / 2, ty + lerp(98, 60, mv) + lerp(14, 9, mv)), 5, fill=RED + (255,))
    # chip de fecha
    cu = prog(t, T["dic16"], T["dic16"] + 0.3)
    if cu > 0:
        chip = rrect((500, 64), 32, RED + (255,)).copy()
        ct = text_img("DESDE EL 16 DE DICIEMBRE", "pb", 30, WHITE)
        chip.alpha_composite(ct, ((500 - ct.width) // 2, (64 - ct.height) // 2))
        place(cv, chip, 540, 605, eback(cu), cu)
    # panel del gráfico
    pu = prog(t, 20.2, 20.6)
    if pu > 0:
        panel = rrect((960, 600), 28, NAVY + (200,))
        place(cv, panel, 540, 955 + 40 * (1 - eo3(pu)), 1, pu)
        d = ImageDraw.Draw(cv)
        d.line([(100, BASE_Y), (980, BASE_Y)], fill=(255, 255, 255, int(160 * pu)), width=3)
        for (x, v, lab, col, a, b) in BARS:
            gu = eo3(prog(t, a, b))
            if t < a - 0.25: continue
            lu = prog(t, a - 0.25, a + 0.05)
            place(cv, text_img(lab, "pb", 34, WHITE), x, BASE_Y + 36, 1, lu)
            h = int(v * PXH * gu)
            if h > 1:
                bi = bar_img(col, h)
                paste(cv, bi, x - bi.width / 2, BASE_Y - h)
                num = text_img(f"{int(round(v * gu))} h", "anton", 82, WHITE)
                place(cv, shadow_of(num, 10, 0.5, (0, 4)), x, BASE_Y - h - 56, 1, min(1, gu * 3))
        for (x, v, delta, tt) in ((540, 42, "-2 h", T["h42"] + 0.45), (835, 40, "-4 h", T["h40"] + 0.4)):
            du = prog(t, tt, tt + 0.25)
            if du > 0:
                b = rrect((120, 52), 26, WHITE + (255,)).copy()
                bt = text_img(delta, "pxb", 32, RED)
                b.alpha_composite(bt, ((120 - bt.width) // 2, (52 - bt.height) // 2))
                place(cv, b, x, BASE_Y - v * PXH + 40, eback(du), du)
    # 2 días de descanso pagados
    iu = prog(t, T["dos_dias"] - 0.1, T["dos_dias"] + 0.25)
    if iu > 0:
        place(cv, rrect((960, 180), 26, NAVY + (215,)), 540, 1330, 1, iu)
        for k, (lab, tt) in enumerate((("SÁB", T["dos_dias"]), ("DOM", T["dos_dias"] + 0.25))):
            cu = prog(t, tt, tt + 0.3)
            x = 150 + k * 140
            place(cv, mini_cal(lab), x, 1334, eback(cu), cu)
            bu = prog(t, T["pagados"] - 0.1 + k * 0.12, T["pagados"] + 0.15 + k * 0.12)
            place(cv, check_badge(50), x + 48, 1290, eback(bu), bu)
        txu = prog(t, T["dos_dias"] + 0.3, T["dos_dias"] + 0.6)
        place(cv, text_img("2 DÍAS DE DESCANSO", "pxb", 46, WHITE), 380, 1300, 1, txu, anchor="lm")
        place(cv, text_img("PAGADOS POR SEMANA", "pxb", 46, (120, 230, 150)), 380, 1362, 1, prog(t, T["pagados"] - 0.2, T["pagados"] + 0.1), anchor="lm")
    # salario igual
    su = prog(t, T["sin_bajar"] - 0.05, T["sin_bajar"] + 0.3)
    if su > 0:
        place(cv, rrect((960, 200), 26, NAVY + (215,)), 540, 1545, 1, su)
        place(cv, shadow_of(bill_img(), 10, 0.5, (0, 6)), 210, 1545 + 40 * (1 - eo3(su)), 1, su, rot=-6)
        cu = prog(t, T["sin_bajar"] + 0.4, T["sin_bajar"] + 0.65)
        place(cv, check_badge(84), 320, 1478, eback(cu) if cu < 1 else 1, cu)
        place(cv, text_img("SALARIO:", "pxb", 52, WHITE), 420, 1505, 1, prog(t, T["sin_bajar"] + 0.15, T["sin_bajar"] + 0.4), anchor="lm")
        gu = prog(t, T["sin_bajar"] + 0.45, T["sin_bajar"] + 0.7)
        place(cv, text_img("IGUAL", "anton", 104, (120, 230, 150)), 420, 1585, lerp(1.3, 1, eo3(gu)), gu, anchor="lm")
    return cv


# ----------------------------------------------------------------- ESCENA 4: impacto
GRID = [(144 + (i % 10) * 88, 1180 + (i // 10) * 104) for i in range(50)]


def scene4(t):
    t0 = S4[0]
    z = lerp(1.0, 1.2, prog(t, t0, S4[1]))
    a = kb(BG["fabrica"], z, (-0.2, 0))
    cs, ce = T["por_fin"] + 0.05, T["por_fin"] + 0.65
    cu = eio(prog(t, cs, ce))
    if cu > 0:
        b = kb(BG["familia"], lerp(1.0, 1.12, prog(t, cs, S4[1])), (0, 0.3))
        xe = int(W * cu)
        a = a.copy()
        if xe > 0: a.paste(b.crop((0, 0, xe, H)), (0, 0))
        if 0 < cu < 1:
            d = ImageDraw.Draw(a)
            d.rectangle((xe - 6, 0, xe + 10, H), fill=RED + (255,))
            d.rectangle((xe + 10, 0, xe + 14, H), fill=WHITE + (255,))
    cv = a.copy()
    # contador 14,8 MILLONES
    u = eo3(prog(t, T["m15"] - 0.1, T["m15"] + 1.2))
    v = 14.8 * u
    s = f"{v:.1f}".replace(".", ",")
    pop = 1 + 0.1 * math.sin(math.pi * prog(t, T["m15"] + 1.2, T["m15"] + 1.45))
    place(cv, shadow_of(text_img(s, "anton", 280, WHITE), 18, 0.6), 540, 700, pop, prog(t, t0 + 0.05, t0 + 0.25))
    mu = prog(t, T["m15"] + 0.4, T["m15"] + 0.7)
    place(cv, shadow_of(text_img("MILLONES", "anton", 130, RED), 14, 0.6), 540, 915, lerp(1.4, 1, eo3(mu)), mu)
    swap = prog(t, T["fin_semana"] - 0.1, T["fin_semana"] + 0.2)
    l1 = shadow_of(text_img("trabajan hoy 6 días a la semana", "psb", 50, WHITE), 10, 0.7)
    l2 = shadow_of(text_img("tendrán un fin de semana completo", "psb", 50, WHITE), 10, 0.7)
    lu = prog(t, T["trabajan"] - 0.4, T["trabajan"] - 0.1)
    place(cv, l1, 540, 1035, 1, lu * (1 - swap))
    place(cv, l2, 540, 1035, 1, swap)
    # íconos de personas que se multiplican
    for i, (x, y) in enumerate(GRID):
        ts = T["m15"] + 0.8 + i * 0.045
        pu = prog(t, ts, ts + 0.22)
        if pu <= 0: continue
        ru = prog(t, T["fin_semana"] - 0.2 + i * 0.022, T["fin_semana"] + 0.0 + i * 0.022)
        col = RED if ru < 0.5 else WHITE
        place(cv, person_icon(col), x, y, eback(pu), pu)
    place(cv, text_img("cada ícono ≈ 300.000 personas", "psb", 30, WHITE, alpha=200), 540, 1715, 1, prog(t, T["m15"] + 2.8, T["m15"] + 3.1))
    place(cv, text_img("Fuente: Gobierno de Brasil vía Infobae", "psb", 28, WHITE, alpha=190), 540, 1795, 1, prog(t, t0 + 0.6, t0 + 0.9))
    return cv


# ----------------------------------------------------------------- ESCENA 5: comparación
CAM5 = (-80.0, 4.0, 9.2)
LABELS = [  # code, lon, lat, t, titulo, linea principal, linea secundaria, posición de tarjeta (x, y, ancla)
    ("BRA", -51, -10, T["brasil"], "BRASIL", "44 h → 40 h", "40 h en 2027", (1040, 1480, "rm")),
    ("COL", -73.5, 4, T["colombia"], "COLOMBIA", "42 h", None, (40, 1150, "lm")),
    ("CHL", -70.5, -28, T["chile"], "CHILE", "42 h", "40 h en 2028", (40, 1440, "lm")),
    ("MEX", -102, 23.5, T["mexico"], "MÉXICO", "48 h", "→ 40 h en 2030", (40, 930, "lm")),
    ("USA", -98, 39, T["eeuu"], "ESTADOS UNIDOS", "40 h", "semana estándar", (1040, 720, "rm")),
]


@functools.lru_cache(None)
def label_card(title, main, sub, sub_on):
    t1 = text_img(title, "pxb", 30, (255, 200, 200))
    t2 = text_img(main, "anton", 72, WHITE)
    t3 = text_img(sub, "psb", 30, WHITE) if (sub and sub_on) else None
    w = max(t1.width, t2.width, t3.width if t3 else 0) + 56
    h = 30 + t1.height + 4 + t2.height + (t3.height + 6 if t3 else 0) + 22
    im = rrect((w, h), 18, NAVY + (240,)).copy()
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 10, h - 1), 5, fill=RED + (255,))
    d.rounded_rectangle((0, 0, w - 1, h - 1), 18, outline=(255, 255, 255, 60), width=2)
    y = 22
    im.alpha_composite(t1, (32, y)); y += t1.height + 4
    im.alpha_composite(t2, (30, y)); y += t2.height + 6
    if t3: im.alpha_composite(t3, (32, y))
    return shadow_of(im, 14, 0.6, (0, 8))


RANK = [("BRASIL", 44, RED), ("COLOMBIA", 42, (70, 120, 210)), ("CHILE", 42, (70, 120, 210)),
        ("MÉXICO", 48, (70, 120, 210)), ("EE. UU.", 40, (70, 120, 210))]
RANK_SORTED = sorted(range(5), key=lambda i: -RANK[i][1])


def scene5(t):
    t0 = S5[0]
    cv = BG["grad"].copy()
    u = eo3(prog(t, t0, t0 + 1.0))
    clon, clat = CAM5[0], CAM5[1]
    ppd = lerp(7.4, CAM5[2], u) + 0.25 * prog(t, t0 + 1, S5[1])
    fills, glow = {}, {}
    for code, lon, lat, tm, *_ in LABELS:
        hu = prog(t, tm - 0.05, tm + 0.25)
        if hu > 0:
            nxt = [l[3] for l in LABELS if l[3] > tm]
            active = not nxt or t < min(nxt) + 0.1
            col = lerpc(LAND, RED if active else DARKRED, hu)
            fills[code] = col + (255,)
            if active: glow[code] = RED + (int(190 * hu * (0.75 + 0.25 * math.sin(t * 7))),)
    rk = prog(t, T["ranking"], T["ranking"] + 0.45)
    cv.alpha_composite(map_layer(clon, clat, ppd, fills, 1100, glow or None))
    # etiquetas
    d = ImageDraw.Draw(cv)
    for code, lon, lat, tm, title, main, sub, (cx, cy, anc) in LABELS:
        lu = prog(t, tm, tm + 0.3)
        if lu <= 0: continue
        if code == "MEX":
            card = label_card(title, "48 h" if t < T["h40mx"] else "48 h → 40 h", "en 2030", t >= T["y2030"] - 0.1)
        else:
            card = label_card(title, main, sub, True)
        ax, ay = map_xy(lon, lat, clon, clat, ppd, 1100)
        ex = cx + (card.width - 50) * (0 if anc == "lm" else -1) + (card.width - 50) / 2
        a = min(1, lu * 2)
        d.line([(ax, ay), (ex, cy)], fill=(255, 255, 255, int(170 * a)), width=3)
        r = 9 + 4 * math.sin(t * 6)
        d.ellipse((ax - r - 4, ay - r - 4, ax + r + 4, ay + r + 4), fill=RED + (int(255 * a),))
        d.ellipse((ax - 6, ay - 6, ax + 6, ay + 6), fill=WHITE + (int(255 * a),))
        place(cv, card, cx, cy, eback(lu), a, anchor=anc)
    # ranking
    if rk > 0:
        ov = Image.new("RGBA", (W, H), (5, 14, 28, int(110 * rk)))
        cv.alpha_composite(ov)
        py = 1500 + 700 * (1 - eo3(rk))
        panel = rrect((980, 600), 30, (9, 24, 46, 245)).copy()
        pd = ImageDraw.Draw(panel)
        pd.rounded_rectangle((0, 0, 979, 599), 30, outline=(255, 255, 255, 50), width=2)
        tt = text_img("HORAS LEGALES POR SEMANA · HOY", "pxb", 36, WHITE)
        panel.alpha_composite(tt, ((980 - tt.width) // 2, 28))
        pd.rectangle((390, 82, 590, 88), fill=RED + (255,))
        su = eio(prog(t, T["ranking"] + 0.95, T["ranking"] + 1.6))
        gu = eo3(prog(t, T["ranking"] + 0.3, T["ranking"] + 0.9))
        for i, (name, v, col) in enumerate(RANK):
            yi = lerp(i, RANK_SORTED.index(i), su)
            y = 120 + yi * 92
            nt = text_img(name, "pb", 36, WHITE)
            panel.alpha_composite(nt, (36, int(y + (70 - nt.height) / 2)))
            bw = int(560 * v / 48 * gu)
            if bw > 4:
                pd.rounded_rectangle((250, y + 10, 250 + bw, y + 60), 12, fill=col + (255,))
                vt = text_img(f"{v} h", "anton", 50, WHITE)
                panel.alpha_composite(vt, (250 + bw + 16, int(y + (70 - vt.height) / 2)))
        place(cv, shadow_of(panel, 20, 0.6), 540, py, 1, min(1, rk * 2))
    return cv


# ----------------------------------------------------------------- ESCENA 6: la pregunta
QUOTE = [  # (palabra, línea, rojo, tiempo)
    ("¿Trabajar", 0, False, 54.98), ("menos", 0, False, 55.46),
    ("realmente", 1, False, 55.76), ("funciona…", 1, False, 56.48),
    ("o", 2, True, 57.36), ("lo", 2, True, 58.16), ("pagará", 2, True, 58.74),
    ("el", 3, True, 60.08), ("trabajador?", 3, True, 60.6),
]


@functools.lru_cache(None)
def clock_img(step):
    s = 220; ss = 3
    im = Image.new("RGBA", (s * ss, s * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = s * ss / 2; r = c - 8 * ss
    d.ellipse((c - r, c - r, c + r, c + r), fill=NAVY + (230,), outline=WHITE + (255,), width=8 * ss)
    for k in range(12):
        a = k * math.pi / 6
        r1 = r * (0.78 if k % 3 == 0 else 0.84)
        d.line([(c + math.cos(a) * r1, c + math.sin(a) * r1), (c + math.cos(a) * r * 0.92, c + math.sin(a) * r * 0.92)],
               fill=WHITE + (255,), width=(6 if k % 3 == 0 else 3) * ss)
    d.line([(c, c), (c + math.cos(-math.pi / 2 + 0.9) * r * 0.45, c + math.sin(-math.pi / 2 + 0.9) * r * 0.45)], fill=WHITE + (255,), width=9 * ss)
    a = -math.pi / 2 + step * math.pi / 15
    d.line([(c - math.cos(a) * r * 0.15, c - math.sin(a) * r * 0.15), (c + math.cos(a) * r * 0.8, c + math.sin(a) * r * 0.8)], fill=RED + (255,), width=5 * ss)
    d.ellipse((c - 12 * ss, c - 12 * ss, c + 12 * ss, c + 12 * ss), fill=RED + (255,))
    return im.resize((s, s), Image.LANCZOS)


def scene6(t):
    t0 = S6[0]
    cv = kb(BG["saopaulo"], lerp(1.0, 1.22, prog(t, t0, S6[1])), (0, -0.2)).copy()
    hu = prog(t, T["gran_pregunta"] - 0.2, T["gran_pregunta"] + 0.15)
    chip = rrect((500, 70), 35, RED + (255,)).copy()
    ct = text_img("LA GRAN PREGUNTA", "pxb", 36, WHITE)
    chip.alpha_composite(ct, ((500 - ct.width) // 2, (70 - ct.height) // 2))
    place(cv, chip, 540, 610, eback(hu), hu)
    cu = prog(t, t0 + 0.15, t0 + 0.5)
    card = rrect((960, 640), 30, NAVY + (225,)).copy()
    ImageDraw.Draw(card).rounded_rectangle((0, 0, 12, 639), 6, fill=RED + (255,))
    place(cv, shadow_of(card, 22, 0.6), 540, 1040 + 60 * (1 - eo3(cu)), 1, cu)
    qu = prog(t, t0 + 0.35, t0 + 0.65)
    place(cv, text_img("“", "anton", 330, RED), 120, 790, eback(qu), qu, anchor="lm")
    xs = [110, 110, 110, 110]; ys = [930, 1020, 1110, 1200]
    for w, ln, red, tw in QUOTE:
        wu = prog(t, tw - 0.12, tw + 0.12)
        im = text_img(w, "pxb", 68, RED if red else WHITE)
        if wu > 0:
            place(cv, im, xs[ln], ys[ln] + 18 * (1 - eo3(wu)), 1, wu, anchor="lm")
        xs[ln] += im.width + 18
    # reloj con tic-tac
    step = int(max(0, t - (t0 + 0.2)) / 0.5)
    ku = prog(t, t0 + 0.4, t0 + 0.7)
    place(cv, shadow_of(clock_img(step % 30), 14, 0.6), 540, 1530, eback(ku) * (1 + 0.03 * (1 - prog((t - t0 - 0.2) % 0.5, 0, 0.15))), ku)
    return cv


# ----------------------------------------------------------------- ESCENA 7: encuesta
OPTS = ["5 días", "6 días", "7 días", "Depende de la semana"]


@functools.lru_cache(None)
def opt_img(i, hl):
    w, h = 780, 104
    im = rrect((w, h), 52, (238, 241, 246, 255), (214, 40, 40, 255) if hl else (210, 216, 226, 255), 5 if hl else 3).copy()
    d = ImageDraw.Draw(im)
    d.ellipse((30, h / 2 - 20, 70, h / 2 + 20), outline=(RED if hl else (150, 160, 175)) + (255,), width=5)
    if hl: d.ellipse((40, h / 2 - 10, 60, h / 2 + 10), fill=RED + (255,))
    t = text_img(OPTS[i], "pb", 42, NAVY)
    im.alpha_composite(t, (96, (h - t.height) // 2))
    return im


@functools.lru_cache(None)
def poll_card():
    w, h = 900, 860
    im = rrect((w, h), 40, WHITE + (255,)).copy()
    im.alpha_composite(lupa_logo(72), (44, 36))
    im.alpha_composite(text_img("capitalcuriosoo", "pb", 34, NAVY), (134, 40))
    im.alpha_composite(text_img("Responde en comentarios", "psb", 26, (120, 128, 140)), (134, 84))
    chip = rrect((170, 52), 26, RED + (255,)).copy()
    ct = text_img("ENCUESTA", "pxb", 24, WHITE); chip.alpha_composite(ct, ((170 - ct.width) // 2, (52 - ct.height) // 2))
    im.alpha_composite(chip, (w - 214, 50))
    q1 = text_img("¿Cuántos días a la semana", "pxb", 52, NAVY); q2 = text_img("trabajas?", "pxb", 52, NAVY)
    im.alpha_composite(q1, ((w - q1.width) // 2, 158)); im.alpha_composite(q2, ((w - q2.width) // 2, 228))
    return shadow_of(im, 26, 0.6, (0, 16))


@functools.lru_cache(None)
def comment_icon():
    ss = 4; w, h = 150, 130
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * ss, 98 * ss), 30 * ss, fill=RED + (255,))
    d.polygon([(34 * ss, 90 * ss), (34 * ss, 128 * ss), (74 * ss, 92 * ss)], fill=RED + (255,))
    for k in range(3):
        cx = (44 + k * 31) * ss
        d.ellipse((cx - 10 * ss, 49 * ss - 10 * ss, cx + 10 * ss, 49 * ss + 10 * ss), fill=WHITE + (255,))
    return im.resize((w, h), Image.LANCZOS)


def scene7(t):
    t0 = S7[0]
    cv = kb(BG["calendario"], lerp(1.0, 1.15, prog(t, t0, S7[1] + 0.3)), (0.2, 0)).copy()
    cu = prog(t, t0 + 0.05, t0 + 0.45)
    pc = poll_card()
    cy = 1000 + 80 * (1 - eo3(cu))
    place(cv, pc, 540, cy, lerp(0.9, 1, eo3(cu)), cu)
    top = cy - pc.height / 2
    hl = int((t - 64.3) / 0.45) % 4 if t >= 64.3 else -1
    for i in range(4):
        ts = T["cuantos"] + 0.2 + i * 0.22
        ou = prog(t, ts, ts + 0.3)
        if ou <= 0: continue
        y = top + 78 + 386 + i * 124
        sc = 1.04 if i == hl else 1.0
        place(cv, opt_img(i, i == hl), 540 + 200 * (1 - eo3(ou)), y, sc, ou)
    bu = prog(t, T["te_leo"] - 0.15, T["te_leo"] + 0.15)
    if bu > 0:
        dt = max(0, t - T["te_leo"])
        bounce = abs(math.sin(dt * 7)) * 34 * math.exp(-dt * 0.6)
        place(cv, shadow_of(comment_icon(), 12, 0.5), 540, 1540 - bounce, eback(bu), bu)
        tx = text_img("Te leo en los comentarios", "pb", 48, WHITE)
        em = emoji_img("👇", 52)
        row = Image.new("RGBA", (tx.width + em.width + 16, max(tx.height, em.height)), (0, 0, 0, 0))
        row.alpha_composite(tx, (0, (row.height - tx.height) // 2)); row.alpha_composite(em, (tx.width + 16, (row.height - em.height) // 2))
        place(cv, shadow_of(row, 10, 0.7, (0, 4)), 540, 1700, 1, prog(t, T["te_leo"], T["te_leo"] + 0.3))
    return cv


# ----------------------------------------------------------------- ESCENA 8: cierre
def scene8(t):
    lt = t - S8[0]
    fr = BG["close"]
    i = min(len(fr) - 1, int(lt * 30))
    cv = Image.fromarray(fr[i], "RGB").convert("RGBA")
    u = prog(lt, 1.7, 2.1)
    if u > 0:
        a = text_img("Síguenos para más historias", "psb", 48, WHITE)
        b = text_img("de Latinoamérica", "psb", 48, WHITE)
        place(cv, a, 540, 1575 + 30 * (1 - eo3(u)), 1, u)
        place(cv, b, 540, 1640 + 30 * (1 - eo3(u)), 1, u)
        lw = 120 * eo3(prog(lt, 2.0, 2.4))
        if lw > 1: ImageDraw.Draw(cv).rounded_rectangle((540 - lw, 1700, 540 + lw, 1708), 4, fill=(242, 66, 76, 255))
    return cv


# ----------------------------------------------------------------- subtítulos
def clean_words():
    out = []
    for w in WORDS:
        s = w["w"]
        if s == "¿La": s = "La"
        if s == "es,": s = "es:"
        out.append(dict(w=s, s=w["s"], e=w["e"]))
    return out


def build_chunks():
    ws = clean_words(); chunks = []; cur = []
    for i, w in enumerate(ws):
        cur.append(w)
        gap = ws[i + 1]["s"] - w["e"] if i + 1 < len(ws) else 9
        chars = sum(len(x["w"]) + 1 for x in cur)
        nxt = len(ws[i + 1]["w"]) if i + 1 < len(ws) else 0
        if len(cur) >= 3 or w["w"][-1] in ".,?!:;…" or gap > 0.3 or chars + nxt > 18:
            chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    res = []
    for k, c in enumerate(chunks):
        st = c[0]["s"]
        en = c[-1]["e"] + 0.35
        if k + 1 < len(chunks): en = min(en if chunks[k + 1][0]["s"] - c[-1]["e"] > 0.6 else chunks[k + 1][0]["s"], chunks[k + 1][0]["s"])
        res.append((st, en, c))
    return res


CHUNKS = build_chunks()


def up(s):
    return s if s.lower() == "6x1" or s.lower().startswith("6x1") else s.upper()


@functools.lru_cache(2048)
def sub_img(ci, active):
    st, en, c = CHUNKS[ci]
    f = 80
    ims = [text_img(up(w["w"]), "pblack", f, RED if k == active else WHITE, 10, (0, 0, 0)) for k, w in enumerate(c)]
    sp = 18; maxw = 1000
    lines = [[]]; lw = 0
    for im in ims:
        if lines[-1] and lw + sp + im.width > maxw:
            lines.append([]); lw = 0
        lines[-1].append(im); lw += (sp if lw else 0) + im.width
    lh = 104
    out = Image.new("RGBA", (maxw + 40, lh * len(lines) + 20), (0, 0, 0, 0))
    for li, ln in enumerate(lines):
        tw = sum(i.width for i in ln) + sp * (len(ln) - 1)
        x = (out.width - tw) // 2
        for im in ln:
            out.alpha_composite(im, (x, li * lh + 10 + (lh - im.height) // 2)); x += im.width + sp
    return shadow_of(out, 10, 0.55, (0, 6))


def draw_subs(cv, t):
    if t >= NARR_END: return
    for ci, (st, en, c) in enumerate(CHUNKS):
        if st - 0.02 <= t < en:
            act = 0
            for k, w in enumerate(c):
                if t >= w["s"] - 0.02: act = k
            im = sub_img(ci, act)
            u = prog(t, st - 0.02, st + 0.1)
            place(cv, im, 540, 310, lerp(0.85, 1, eo3(u)), min(1, u * 2))
            return


# ----------------------------------------------------------------- transiciones
def wipe(cv, t):
    for c in CUTS:
        if abs(t - c) < 0.22:
            u = eio((t - c + 0.22) / 0.44)
            lead = lerp(-300, 3380, u); Wb = 2000; sl = 300
            d = ImageDraw.Draw(cv)
            d.polygon([(lead - Wb, 0), (lead, 0), (lead - sl, H), (lead - Wb - sl, H)], fill=NAVY + (255,))
            d.polygon([(lead, 0), (lead + 50, 0), (lead + 50 - sl, H), (lead - sl, H)], fill=RED + (255,))
            d.polygon([(lead + 50, 0), (lead + 62, 0), (lead + 62 - sl, H), (lead + 50 - sl, H)], fill=WHITE + (255,))
            d.polygon([(lead - Wb - 40, 0), (lead - Wb, 0), (lead - Wb - sl, H), (lead - Wb - sl - 40, H)], fill=RED + (255,))


SCENES = [(S1, scene1), (S2, scene2), (S3, scene3), (S4, scene4), (S5, scene5), (S6, scene6), (S7, scene7), (S8, scene8)]


def frame(t):
    for (a, b), fn in SCENES:
        if a <= t < b or fn is scene8 and t >= a:
            cv = fn(t); break
    cv = cv.convert("RGBA") if cv.mode != "RGBA" else cv
    dx, dy = shake(t)
    if dx or dy:
        big = cv.resize((int(W * 1.06), int(H * 1.06)), Image.BILINEAR)
        ox, oy = (big.width - W) / 2 - dx, (big.height - H) / 2 - dy
        cv = big.crop((int(ox), int(oy), int(ox) + W, int(oy) + H))
    wipe(cv, t)
    arr = np.asarray(cv.convert("RGB"), np.float32)
    g = BG["grain"][int(t * FPS) % len(BG["grain"])]
    arr = arr * BG["vig"] + g * (0.10 if t >= S8[0] else 0.16)
    cv = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    draw_subs(cv, t)
    return cv.convert("RGB")


def render_range(args):
    idx, f0, f1 = args
    prep()
    path = os.path.join(BUILD, f"seg_{idx:02d}.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
                          "-profile:v", "high", path], stdin=subprocess.PIPE)
    for i in range(f0, f1):
        p.stdin.write(frame(i / FPS).tobytes())
        if (i - f0) % 60 == 0: print(f"[{idx}] {i - f0}/{f1 - f0}", flush=True)
    p.stdin.close(); p.wait()
    return path


def main():
    if "--frames" in sys.argv:
        prep()
        od = os.path.join(BUILD, "preview"); os.makedirs(od, exist_ok=True)
        for s in sys.argv[sys.argv.index("--frames") + 1:]:
            frame(float(s)).save(os.path.join(od, f"f_{float(s):06.2f}.png"))
        return
    from multiprocessing import Pool
    nw = int(os.environ.get("WORKERS", os.cpu_count() or 4))
    nseg = nw * 2
    step = math.ceil(NFRAMES / nseg)
    jobs = [(k, k * step, min(NFRAMES, (k + 1) * step)) for k in range(nseg) if k * step < NFRAMES]
    prep()
    with Pool(nw) as pool:
        segs = pool.map(render_range, jobs, chunksize=1)
    lst = os.path.join(BUILD, "segs.txt")
    open(lst, "w").write("".join(f"file '{s}'\n" for s in segs))
    mix = os.path.join(BUILD, "mix.wav")
    out = os.path.join(HERE, "capital_curioso_6x1.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", mix,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-t", f"{NFRAMES / FPS:.3f}", "-movflags", "+faststart", out], check=True)
    print("OK", out)


if __name__ == "__main__":
    main()
