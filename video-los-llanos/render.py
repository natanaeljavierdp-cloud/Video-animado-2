"""Renderizador del video vertical "Los Llanos" (1080x1920, 30 fps).
Python + Pillow + numpy; FFmpeg codifica. Uso:
  python3 render.py --start 0 --end 20 --out preview_20s.mp4
  python3 render.py --out los_llanos_final.mp4
  python3 render.py --still 21.5          (guarda build/still_21.5.png)
"""
import argparse, json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
TL = json.load(open("timeline.json"))
TOTAL = TL["total"]
SC = TL["scenes"]
SUBS = json.load(open("build/subs.json"))
FD = "/usr/share/fonts/opentype/inter/"

WHITE = (245, 245, 240)
GRAY = (160, 170, 190)
RED = (206, 17, 38)
GREEN = (46, 170, 110)
YELLOW = (235, 190, 70)
FLAG_BLUE = (0, 45, 98)
BAR_BLUE = (58, 112, 205)
BLACK = (0, 0, 0)
CX = 540  # centro horizontal; ancho útil 80..940 (zona segura derecha 140 px)

# ----------------------------------------------------------------------------
# utilidades
# ----------------------------------------------------------------------------
_fonts = {}


def F(weight, size):
    k = (weight, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(FD + f"Inter-{weight}.otf", size)
    return _fonts[k]


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def spring(x, w=13.0, z=0.62):
    if x <= 0:
        return 0.0
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * x) * (math.cos(wd * x) + (z * w / wd) * math.sin(wd * x))


_tcache = {}


def txt(text, weight="ExtraBold", size=80, fill=WHITE, stroke=0, stroke_fill=BLACK,
        shadow=True, maxw=860):
    key = (text, weight, size, fill, stroke, shadow, maxw)
    if key in _tcache:
        return _tcache[key]
    font = F(weight, size)
    while maxw and font.getlength(text) + 2 * stroke > maxw and size > 20:
        size -= 2
        font = F(weight, size)
    asc, desc = font.getmetrics()
    pad = 24 + stroke
    w = int(font.getlength(text)) + 2 * pad
    h = asc + desc + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((pad, pad), text, font=font, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    if shadow:
        a = im.getchannel("A").filter(ImageFilter.GaussianBlur(10))
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sh.putalpha(a.point(lambda v: int(v * 0.75)))
        sh = sh.transform(sh.size, Image.AFFINE, (1, 0, 0, 0, 1, -5))
        im = Image.alpha_composite(sh, im)
    im.info["pad"] = pad
    _tcache[key] = im
    return im


def put(fr, spr, cx, cy, alpha=1.0, scale=1.0, anchor="c"):
    if alpha <= 0.004 or spr is None:
        return None
    if abs(scale - 1) > 1e-3:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BICUBIC)
    if alpha < 0.996:
        spr = spr.copy()
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * alpha)))
    x = int(round(cx - spr.width / 2)) if anchor == "c" else int(round(cx))
    y = int(round(cy - spr.height / 2))
    sx0, sy0 = max(0, -x), max(0, -y)
    ex, ey = min(spr.width, W - x), min(spr.height, H - y)
    if ex > sx0 and ey > sy0:
        fr.alpha_composite(spr, dest=(x + sx0, y + sy0), source=(sx0, sy0, ex, ey))
    return (x, y, spr.width, spr.height)


def show(fr, spr, cx, cy, t, t0, t1=None, dy=46, fo=0.25, pop=None, anchor="c"):
    """Entrada con spring + fade (sube desde abajo) o 'pop' (escala). Devuelve opacidad."""
    x = t - t0
    if x < 0 or (t1 is not None and t > t1):
        return 0.0
    a = ease_out(x / 0.3)
    if t1 is not None:
        a *= clamp((t1 - t) / fo)
    if pop:
        sc = pop + (1 - pop) * spring(x, w=17, z=0.55)
        put(fr, spr, cx, cy, a, sc, anchor)
    else:
        put(fr, spr, cx, cy + dy * (1 - spring(x)), a, 1.0, anchor)
    return a


def strike(fr, spr, cx, cy, prog, color=RED, thick=10, alpha=1.0):
    if prog <= 0:
        return
    pad = spr.info.get("pad", 24)
    w = spr.width - 2 * pad
    x0 = cx - w / 2 - 12
    x1 = x0 + (w + 24) * ease_io(prog)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    off = 0.06 * spr.height
    ImageDraw.Draw(ov).rectangle([x0, cy - thick / 2 + off, x1, cy + thick / 2 + off],
                                 fill=color + (int(255 * alpha),))
    fr.alpha_composite(ov)


def rect(fr, box, color, alpha=1.0, radius=0):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    c = color + (int(255 * clamp(alpha)),)
    if radius:
        d.rounded_rectangle(box, radius, fill=c)
    else:
        d.rectangle(box, fill=c)
    fr.alpha_composite(ov)


def darken(fr, alpha):
    if alpha > 0:
        fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * clamp(alpha)))))


def crop_zoom(src, zoom, cx=0.5, cy=0.5):
    """Recorta src (proporción ~9:16) con zoom >=1 centrado en (cx,cy) relativo, a W x H."""
    sw, sh = src.size
    bw, bh = sw / zoom, sh / zoom
    x0 = clamp(cx * sw - bw / 2, 0, sw - bw)
    y0 = clamp(cy * sh - bh / 2, 0, sh - bh)
    return src.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + bw, y0 + bh))


# ----------------------------------------------------------------------------
# recursos generados (se precalculan una vez y se guardan en build/)
# ----------------------------------------------------------------------------
def vnoise(rng, h, w, ch, cw):
    a = (rng.random((ch, cw)) * 255).astype(np.uint8)
    return np.asarray(Image.fromarray(a).resize((w, h), Image.BICUBIC), np.float32) / 255


def gen_asphalt(seed, w=1400, h=2500, n_cracks=14, potholes=0):
    rng = np.random.default_rng(seed)
    base = (0.40 * vnoise(rng, h, w, 9, 5) + 0.30 * vnoise(rng, h, w, 40, 22)
            + 0.18 * vnoise(rng, h, w, 180, 100) + 0.12 * vnoise(rng, h, w, 700, 400))
    sp = rng.random((h, w))
    g = 55 + 70 * base + rng.normal(0, 9, (h, w))
    g += (sp > 0.992) * 45 - (sp < 0.01) * 30
    plain = g.copy()
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)

    def walk(x, y, ang, width, steps):
        pts = [(x, y)]
        for _ in range(steps):
            ang += rng.normal(0, 0.45)
            L = rng.uniform(10, 26)
            x += math.cos(ang) * L
            y += math.sin(ang) * L
            pts.append((x, y))
            if rng.random() < 0.07 and width > 2:
                walk(x, y, ang + rng.choice([-1, 1]) * rng.uniform(0.6, 1.3), max(2, width - 2),
                     int(steps * 0.5))
        d.line(pts, fill=255, width=int(width), joint="curve")

    for _ in range(n_cracks):
        walk(rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0, 2 * math.pi), rng.uniform(4, 9),
             int(rng.uniform(25, 70)))
    for _ in range(potholes):
        pm = Image.new("L", (w, h), 0)
        pd = ImageDraw.Draw(pm)
        px, py = rng.uniform(150, w - 150), rng.uniform(300, h - 300)
        r = rng.uniform(70, 170)
        pts = [(px + math.cos(a) * r * rng.uniform(0.7, 1.25), py + math.sin(a) * r * 0.6 * rng.uniform(0.7, 1.25))
               for a in np.linspace(0, 2 * math.pi, 18)]
        pd.polygon(pts, fill=255)
        pmf = np.asarray(pm.filter(ImageFilter.GaussianBlur(8)), np.float32) / 255
        g = g * (1 - 0.6 * pmf) + rng.normal(0, 6, (h, w)) * pmf
    cm = np.asarray(m.filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
    hl = np.roll(np.roll(cm, 3, 0), 3, 1)
    g = g * (1 - 0.85 * cm) + 30 * np.clip(hl - cm, 0, 1)
    return np.clip(g, 0, 255), np.clip(plain, 0, 255)


def tint(gray, mul, add=(0, 0, 0)):
    rgb = gray[..., None] * np.array(mul, np.float32)[None, None, :] + np.array(add, np.float32)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


def gen_unfinished_road():
    w, h = 1300, 2311
    hz = int(h * 0.40)
    img = Image.new("RGB", (w, h))
    a = np.zeros((h, w, 3), np.float32)
    yy = np.arange(h)[:, None]
    sky = np.clip(yy / hz, 0, 1)
    for i, (c0, c1) in enumerate(zip((22, 26, 34), (78, 82, 92))):
        a[..., i] = c0 + (c1 - c0) * sky
    rng = np.random.default_rng(3)
    ground = 58 + 26 * vnoise(rng, h, w, 30, 17) + rng.normal(0, 7, (h, w))
    gmask = (yy >= hz)
    for i, m in enumerate((1.0, 0.92, 0.82)):
        a[..., i] = np.where(gmask, ground * m, a[..., i])
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    asp, _ = gen_asphalt(11, w, h, n_cracks=22, potholes=3)
    asp_img = tint(asp * 0.95, (0.95, 0.97, 1.02))
    vp = (w / 2, hz)
    road = [(-250, h), (w + 250, h), (vp[0] + 24, hz), (vp[0] - 24, hz)]
    yend = hz + 0.30 * (h - hz)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon(road, fill=255)
    dirt = Image.fromarray(np.clip(np.stack([ground * 1.15, ground * 1.0, ground * 0.85], -1), 0, 255).astype(np.uint8))
    img.paste(dirt, (0, 0), mask)
    pm = mask.copy()
    ImageDraw.Draw(pm).rectangle([0, 0, w, yend], fill=0)
    img.paste(asp_img, (0, 0), pm)
    d = ImageDraw.Draw(img)

    def road_x(y, s):  # s en [-1,1] a lo ancho de la vía
        k = (y - hz) / (h - hz)
        half = 24 + k * (w / 2 + 250 - 24)
        return vp[0] + s * half

    # línea central discontinua solo en la parte pavimentada
    y = h
    while y > yend + 10:
        k = (y - hz) / (h - hz)
        L = 150 * k
        y2 = max(y - L, yend)
        wl, wl2 = 16 * k, 16 * (y2 - hz) / (h - hz)
        d.polygon([(road_x(y, 0) - wl, y), (road_x(y, 0) + wl, y), (road_x(y2, 0) + wl2, y2), (road_x(y2, 0) - wl2, y2)],
                  fill=(170, 165, 140))
        y = y2 - L * 0.9
    # barrera de obra
    k = (yend - hz) / (h - hz)
    bx0, bx1 = road_x(yend, -0.75), road_x(yend, 0.75)
    bh = 60 * k + 10
    by = yend - 140 * k
    for lx in (bx0 + 20, bx1 - 20):
        d.rectangle([lx - 5, by, lx + 5, yend], fill=(120, 115, 105))
    stripe = Image.new("RGB", (int(bx1 - bx0), int(bh)), (200, 195, 185))
    sd = ImageDraw.Draw(stripe)
    for sx in range(-int(bh), stripe.width + int(bh), int(bh * 1.4)):
        sd.polygon([(sx, bh), (sx + bh * 0.7, bh), (sx + bh * 1.4, 0), (sx + bh * 0.7, 0)], fill=(170, 60, 40))
    img.paste(stripe, (int(bx0), int(by)))
    # conos
    for s in (-0.55, 0.45, 0.8):
        yc = yend + 160 + abs(s) * 60
        kk = (yc - hz) / (h - hz)
        xc = road_x(yc, s)
        ch, cw = 120 * kk, 50 * kk
        d.polygon([(xc - cw, yc), (xc + cw, yc), (xc + cw * 0.2, yc - ch), (xc - cw * 0.2, yc - ch)], fill=(175, 80, 45))
        d.polygon([(xc - cw * 0.6, yc - ch * 0.45), (xc + cw * 0.6, yc - ch * 0.45),
                   (xc + cw * 0.45, yc - ch * 0.62), (xc - cw * 0.45, yc - ch * 0.62)], fill=(215, 210, 200))
    # desaturar
    arr = np.asarray(img, np.float32)
    lum = arr.mean(-1, keepdims=True)
    arr = lum + 0.35 * (arr - lum)
    arr *= np.array([0.92, 0.96, 1.04])
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def gen_orderly(w=W, h=H):
    """Pueblo ordenado (mitad derecha de la comparación): calle limpia, aceras, casas, árboles."""
    hz = int(h * 0.44)
    vp = (w * 0.75, hz)
    a = np.zeros((h, w, 3), np.float32)
    yy = np.arange(h)[:, None] / hz
    s = np.clip(yy, 0, 1)
    for i, (c0, c1) in enumerate(zip((40, 70, 90), (150, 185, 180))):
        a[..., i] = c0 + (c1 - c0) * s
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.rectangle([0, hz, w, h], fill=(70, 95, 80))
    road = [(w * 0.30, h), (w * 1.25, h), (vp[0] + 14, hz), (vp[0] - 14, hz)]
    walk_l = [(w * 0.12, h), (w * 0.30, h), (vp[0] - 14, hz), (vp[0] - 20, hz)]
    walk_r = [(w * 1.25, h), (w * 1.45, h), (vp[0] + 20, hz), (vp[0] + 14, hz)]
    d.polygon(walk_l, fill=(165, 165, 155))
    d.polygon(walk_r, fill=(165, 165, 155))
    d.polygon(road, fill=(72, 76, 82))

    def lerp(p, q, k):
        return (p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k)

    # líneas de carril
    bot = (w * 0.775, h)
    k = 0.0
    while k < 0.95:
        k2 = k + 0.07 * (1 - k)
        p1, p2 = lerp(bot, vp, k), lerp(bot, vp, k2)
        ww = 10 * (1 - k)
        ww2 = 10 * (1 - k2)
        d.polygon([(p1[0] - ww, p1[1]), (p1[0] + ww, p1[1]), (p2[0] + ww2, p2[1]), (p2[0] - ww2, p2[1])], fill=(235, 235, 225))
        k = k2 + 0.06 * (1 - k2)
    # casas a la izquierda de la calle (hacia el punto de fuga)
    cols = [(196, 160, 120), (150, 180, 170), (210, 200, 170), (170, 150, 180), (200, 175, 140)]
    for i in range(6):
        k = 0.12 + i * 0.14
        base = lerp((w * 0.10, h * 0.93), (vp[0] - 30, hz), k)
        sc = 1 - k * 0.95
        hw, hh = 260 * sc, 300 * sc
        x1 = base[0]
        d.rectangle([x1 - hw, base[1] - hh, x1, base[1]], fill=cols[i % 5])
        d.polygon([(x1 - hw - 10 * sc, base[1] - hh), (x1 + 10 * sc, base[1] - hh), (x1 - hw / 2, base[1] - hh - 90 * sc)],
                  fill=(150, 80, 60))
        for wx in (0.25, 0.65):
            d.rectangle([x1 - hw + hw * wx, base[1] - hh * 0.7, x1 - hw + hw * wx + 40 * sc, base[1] - hh * 0.45], fill=(70, 90, 110))
        # árbol y farola
        tb = lerp((w * 0.27, h * 0.98), (vp[0] - 10, hz), k + 0.05)
        ts = 1 - (k + 0.05) * 0.95
        d.rectangle([tb[0] - 6 * ts, tb[1] - 160 * ts, tb[0] + 6 * ts, tb[1]], fill=(80, 60, 45))
        d.ellipse([tb[0] - 70 * ts, tb[1] - 260 * ts, tb[0] + 70 * ts, tb[1] - 120 * ts], fill=(60, 140, 85))
    arr = np.asarray(img, np.float32)
    lum = arr.mean(-1, keepdims=True)
    arr = lum + 0.65 * (arr - lum)
    rng = np.random.default_rng(5)
    arr += rng.normal(0, 4, arr.shape)
    return Image.fromarray(np.clip(arr * 0.92, 0, 255).astype(np.uint8))


def gen_sunset():
    w, h = 1300, 2311
    hz = 1240
    a = np.zeros((h, w, 3), np.float32)
    y = np.arange(h)[:, None].astype(np.float32)
    stops = [(0, (14, 18, 40)), (650, (60, 40, 75)), (1000, (150, 70, 70)), (hz, (232, 140, 70))]
    for i in range(3):
        a[..., i] = np.interp(y[:, 0], [s[0] for s in stops], [s[1][i] for s in stops])[:, None]
    xs = np.arange(w)[None, :]
    sun_d = np.sqrt((xs - w / 2) ** 2 + (y - hz) ** 2)
    glow = np.exp(-sun_d / 260)[..., None] * np.array([90, 60, 20])
    a += glow
    disk = (sun_d < 85)[..., None] * np.array([255, 205, 130])
    a = np.where(sun_d[..., None] < 85, disk, a)
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(9)
    for layer, col, amp, base in ((0, (70, 40, 70), 70, hz - 40), (1, (45, 28, 50), 45, hz - 5)):
        pts = [(0, h)]
        for xx in range(0, w + 40, 40):
            pts.append((xx, base - amp * (0.5 + 0.5 * math.sin(xx / 170 + layer * 2)) - rng.uniform(0, 12)))
        pts.append((w, h))
        d.polygon(pts, fill=col)
    d.rectangle([0, hz, w, h], fill=(26, 20, 30))
    vp = (w / 2, hz)
    d.polygon([(-200, h), (w + 200, h), (vp[0] + 10, hz), (vp[0] - 10, hz)], fill=(44, 38, 46))
    k = 0.0
    while k < 0.97:
        k2 = k + 0.06 * (1 - k)
        y1 = h - (h - hz) * k
        y2 = h - (h - hz) * k2
        ww, ww2 = 12 * (1 - k), 12 * (1 - k2)
        d.polygon([(vp[0] - ww, y1), (vp[0] + ww, y1), (vp[0] + ww2, y2), (vp[0] - ww2, y2)], fill=(200, 150, 90))
        k = k2 + 0.05 * (1 - k2)
    # postes de luz
    for i in range(7):
        k = 0.08 + i * 0.13
        sc = 1 - k
        yb = h - (h - hz) * k
        xb = vp[0] + (w / 2 + 260) * sc
        d.rectangle([xb - 5 * sc, yb - 420 * sc, xb + 5 * sc, yb], fill=(20, 16, 24))
        d.line([(xb, yb - 420 * sc), (xb - 80 * sc, yb - 400 * sc)], fill=(20, 16, 24), width=max(1, int(6 * sc)))
    arr = np.asarray(img, np.float32) * 0.82
    lum = arr.mean(-1, keepdims=True)
    arr = lum + 0.75 * (arr - lum)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), hz


def gen_bus():
    s = 2
    w, h = 460 * s, 420 * s
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([20 * s, 20 * s, 440 * s, 360 * s], 28 * s, fill=(38, 40, 52))
    d.rounded_rectangle([20 * s, 20 * s, 440 * s, 60 * s], 20 * s, fill=(70, 62, 70))
    d.rounded_rectangle([55 * s, 75 * s, 405 * s, 200 * s], 12 * s, fill=(22, 22, 30))
    d.polygon([(250 * s, 75 * s), (330 * s, 75 * s), (230 * s, 200 * s), (150 * s, 200 * s)], fill=(120, 75, 60))
    for x in (60, 360):
        d.rounded_rectangle([x * s, 250 * s, (x + 40) * s, 300 * s], 8 * s, fill=(230, 40, 40))
    d.rectangle([150 * s, 240 * s, 310 * s, 280 * s], fill=(200, 190, 160))
    d.rectangle([10 * s, 320 * s, 450 * s, 350 * s], fill=(25, 25, 32))
    for x in (40, 360):
        d.rounded_rectangle([x * s, 340 * s, (x + 60) * s, 410 * s], 10 * s, fill=(12, 12, 16))
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for x in (60, 360):
        gd.ellipse([(x - 40) * s, 225 * s, (x + 80) * s, 325 * s], fill=(255, 40, 30, 120))
    glow = glow.filter(ImageFilter.GaussianBlur(20 * s))
    im = Image.alpha_composite(glow, im)
    return im.resize((w // s, h // s), Image.LANCZOS)


def gen_youth():
    s = 2
    w, h = 900 * s, 700 * s
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (12, 10, 16, 255)
    for (x, y, sc) in ((180, 260, 1.0), (450, 300, 0.92), (700, 250, 1.05)):
        x, y = x * s, y * s
        r = 62 * sc * s
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)
        d.rounded_rectangle([x - 55 * sc * s, y + r - 10 * s, x + 55 * sc * s, y + r + 40 * s], 20 * s, fill=c)
        d.rounded_rectangle([x - 150 * sc * s, y + r + 20 * s, x + 150 * sc * s, h + 200 * s], 110 * sc * s, fill=c)
    rim = im.getchannel("A").filter(ImageFilter.GaussianBlur(6 * s))
    glow = Image.new("RGBA", (w, h), (240, 140, 70, 0))
    glow.putalpha(rim.point(lambda v: int(min(255, v) * 0.5)))
    glow = glow.transform(glow.size, Image.AFFINE, (1, 0, 0, 0, 1, 5 * s))
    im = Image.alpha_composite(glow, im)
    return im.resize((w // s, h // s), Image.LANCZOS)


def prep():
    os.makedirs("build/res", exist_ok=True)

    def need(n):
        return not os.path.exists(f"build/res/{n}")

    if need("hook_cracked.png"):
        cracked, plain = gen_asphalt(1, n_cracks=18, potholes=1)
        tint(cracked, (0.86, 0.93, 1.05)).save("build/res/hook_cracked.png")
        tint(plain, (0.86, 0.93, 1.05)).save("build/res/hook_plain.png")
    if need("asph_b.png"):
        g, _ = gen_asphalt(2, n_cracks=26, potholes=2)
        tint(g, (0.9, 0.94, 1.03)).save("build/res/asph_b.png")
        g, _ = gen_asphalt(4, n_cracks=34, potholes=0)
        tint(g * 0.9, (0.9, 0.94, 1.03)).save("build/res/asph_e.png")
        g, _ = gen_asphalt(6, n_cracks=16, potholes=4)
        tint(g * 0.85, (0.82, 0.9, 1.05)).save("build/res/asph_rain.png")
        tint(g, (1.0, 0.94, 0.85)).save("build/res/asph_dust.png")
        g, _ = gen_asphalt(8, w=1080, h=1920, n_cracks=24, potholes=3)
        tint(g * 0.85, (1.08, 0.82, 0.8)).save("build/res/cmp_left.png")
    if need("road_unfinished.png"):
        gen_unfinished_road().save("build/res/road_unfinished.png")
    if need("cmp_right.png"):
        gen_orderly().save("build/res/cmp_right.png")
    if need("sunset.png"):
        img, hz = gen_sunset()
        img.save("build/res/sunset.png")
        gen_bus().save("build/res/bus.png")
        gen_youth().save("build/res/youth.png")
    if need("sepia1844.png"):
        src = Image.open("assets/ilustracion_1844.png").convert("RGB")
        k = 1.45 * W / src.width
        src = src.resize((int(src.width * k), int(src.height * k)), Image.LANCZOS)
        a = np.asarray(src, np.float32)
        sep = a @ np.array([[0.393, 0.349, 0.272], [0.769, 0.686, 0.534], [0.189, 0.168, 0.131]], np.float32)
        a = 0.55 * a + 0.45 * sep
        Image.fromarray(np.clip(a * 0.92, 0, 255).astype(np.uint8)).save("build/res/sepia1844.png")


R = {}


def load_res():
    for n in ("hook_cracked", "hook_plain", "asph_b", "asph_e", "asph_rain", "asph_dust", "cmp_left",
              "cmp_right", "road_unfinished", "sunset", "sepia1844"):
        R[n] = Image.open(f"build/res/{n}.png").convert("RGB")
    R["bus"] = Image.open("build/res/bus.png").convert("RGBA")
    R["youth"] = Image.open("build/res/youth.png").convert("RGBA")
    g = np.zeros((H, W, 3), np.float32)
    k = np.linspace(0, 1, H)[:, None]
    for i, (c0, c1) in enumerate(zip((12, 20, 38), (20, 32, 58))):
        g[..., i] = c0 + (c1 - c0) * k
    xs = np.linspace(-1, 1, W)[None, :]
    ys = np.linspace(-1, 1, H)[:, None]
    g *= (1 - 0.25 * np.clip(xs ** 2 + (ys * 0.8) ** 2, 0, 1))[..., None]
    R["bg"] = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert("RGBA")
    v = np.clip(np.sqrt((xs * 1.05) ** 2 + (ys * 0.95) ** 2) - 0.45, 0, 1) / 0.95
    va = (np.clip(v, 0, 1) ** 1.6 * 235).astype(np.uint8)
    vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vig.putalpha(Image.fromarray(va))
    R["vig"] = vig
    rng = np.random.default_rng(1)
    R["grain"] = [rng.normal(0, 4.0, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]
    yy, xx = np.mgrid[0:2500, 0:1400]
    R["hook_dist"] = np.sqrt((xx - 760) ** 2 + (yy - 1300) ** 2).astype(np.float32)


def bg():
    return R["bg"].copy()


def label_ilustrativa(fr):
    s = txt("Imagen ilustrativa", "Medium", 26, WHITE, shadow=False, maxw=0)
    rect(fr, (40, 70, 40 + s.width - 2 * s.info["pad"] + 32, 70 + 44), (0, 0, 0), 0.55, 12)
    put(fr, s, 40 + 16 - s.info["pad"], 92, 0.92, anchor="l")


def source(fr, text, a=1.0):
    s = txt(text, "Medium", 27, GRAY, shadow=False)
    put(fr, s, CX - 40, 1572, 0.9 * a)


# ----------------------------------------------------------------------------
# escenas
# ----------------------------------------------------------------------------
def scene1(t):
    z = 1.0 + 0.16 * (t / 13.15)
    src = R["hook_cracked"]
    if t < 4.0:  # las grietas "se abren" desde un punto
        r = 2600 * ease_io(t / 3.6)
        m = (R["hook_dist"] < r)
        a = np.where(m[..., None], np.asarray(src), np.asarray(R["hook_plain"]))
        src = Image.fromarray(a)
    fr = crop_zoom(src, z, 0.54, 0.52).convert("RGBA")
    flick = 0.04 * math.sin(t * 9.1) * math.sin(t * 3.7)
    darken(fr, 0.42 + flick + 0.25 * ease_io((t - 9.4) / 0.6))
    fr.alpha_composite(R["vig"])
    # gancho
    if t < 4.05:
        a1 = show(fr, txt("¿Sabías esto de", "ExtraBold", 82), CX, 640, t, 0.15, 4.05, pop=1.5)
        show(fr, txt("Los Llanos?", "ExtraBold", 118, YELLOW), CX, 760, t, 0.15, 4.05, pop=1.5)
        if 0.15 < t < 0.3:
            rect(fr, (0, 0, W, H), WHITE, 0.25 * (1 - (t - 0.15) / 0.15))
    if 4.15 < t < 6.6:
        show(fr, txt("UN DÍA ANTES", "ExtraBold", 104), CX, 680, t, 4.2, 6.6)
        show(fr, txt("QUE LA CAPITAL", "ExtraBold", 104, YELLOW), CX, 800, t, 5.15, 6.6)
    if 6.85 < t < 9.5:
        show(fr, txt("CASI 200 AÑOS", "ExtraBold", 100), CX, 680, t, 6.9, 9.5)
        show(fr, txt("DESPUÉS…", "ExtraBold", 100, GRAY), CX, 800, t, 8.0, 9.5)
    if t >= 9.55:
        show(fr, txt("SAN JOSÉ DE", "ExtraBold", 66, GRAY), CX, 560, t, 9.6, dy=30)
        show(fr, txt("LOS LLANOS", "ExtraBold", 150), CX, 680, t, 9.75, pop=1.25)
        w = 640 * ease_out((t - 10.2) / 0.6)
        if w > 1:
            rect(fr, (CX - w / 2, 772, CX + w / 2, 780), RED)
        show(fr, txt("El primer pueblo libre…", "Medium", 54), CX, 850, t, 10.6)
        show(fr, txt("¿el último en avanzar?", "ExtraBoldItalic", 64, YELLOW), CX, 935, t, 11.3)
    return fr


def scene2(t):
    T = t
    z = 1.04 + 0.16 * ease_io((T - 13.15) / 18.3)
    fr = crop_zoom(R["sepia1844"], z, 0.5, 0.62 - 0.22 * ease_io((T - 13.15) / 18.3)).convert("RGBA")
    darken(fr, 0.5)
    fr.alpha_composite(R["vig"])
    label_ilustrativa(fr)
    # contador 1600 -> 1844
    if 14.9 < T < 26.4:
        if T < 19.75:
            val = 1600
        else:
            val = int(round(1600 + 244 * ease_out((T - 19.75) / 1.5)))
        a = show(fr, txt(str(val), "ExtraBold", 250), CX, 760, T, 15.0, 26.4, pop=0.85)
        show(fr, txt("PRINCIPIOS DE LOS", "ExtraBold", 50, GRAY), CX, 580, T, 15.0, 19.6)
        show(fr, txt("Uno de los pueblos más", "Medium", 46), CX, 935, T, 16.9, 19.6)
        show(fr, txt("antiguos del Este", "Medium", 46), CX, 995, T, 17.1, 19.6)
        show(fr, txt("26 DE FEBRERO", "ExtraBold", 66, YELLOW if False else WHITE), CX, 580, T, 19.8, 26.4)
        show(fr, txt("Primeros en proclamar", "Medium", 46), CX, 935, T, 22.3, 26.4)
        show(fr, txt("la independencia", "Medium", 46), CX, 993, T, 22.4, 26.4)
        show(fr, txt("Un día antes que la capital", "ExtraBold", 54, YELLOW), CX, 1075, T, 23.0, 26.4)
    if 26.5 < T < 31.4:
        show(fr, txt("TENEMOS", "ExtraBold", 48, GRAY), CX, 520, T, 26.55, 31.4)
        for i, (wd, t0) in enumerate((("HISTORIA", 26.75), ("TIERRA", 28.05), ("GENTE", 29.45))):
            show(fr, txt(wd, "ExtraBold", 130), CX, 680 + i * 170, T, t0, 31.4, pop=1.3)
    if T >= 31.4:
        fr = Image.new("RGBA", (W, H), (4, 6, 12, 255))
        show(fr, txt("Entonces…", "Medium", 54, GRAY), CX, 660, T, 31.5)
        show(fr, txt("¿Qué nos pasó?", "ExtraBold", 120), CX, 800, T, 32.55, pop=1.15)
    return fr


def rain_overlay(fr, t, fi):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    rng = np.random.default_rng(1000 + fi)
    for _ in range(170):
        x, y = rng.uniform(-100, W), rng.uniform(-100, H)
        L = rng.uniform(40, 110)
        d.line([(x, y), (x + L * 0.18, y + L)], fill=(200, 212, 235, int(rng.uniform(50, 130))), width=2)
    rng2 = np.random.default_rng(77)
    for i in range(26):
        px, py = rng2.uniform(80, W - 80), rng2.uniform(900, 1800)
        ph = (t * 1.6 + rng2.random()) % 1.0
        r = 8 + 70 * ph
        d.ellipse([px - r, py - r * 0.35, px + r, py + r * 0.35], outline=(190, 205, 230, int(140 * (1 - ph))), width=2)
    fr.alpha_composite(ov)


def dust_overlay(fr, t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.polygon([(200, -50), (520, -50), (980, H), (520, H)], fill=(255, 225, 170, 28))
    d.polygon([(620, -50), (760, -50), (1150, H), (930, H)], fill=(255, 225, 170, 18))
    rng = np.random.default_rng(55)
    for _ in range(160):
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        vx, vy = rng.uniform(15, 60), rng.uniform(-25, 10)
        sz = rng.uniform(2, 6)
        x = (x0 + vx * t + 20 * math.sin(t + x0)) % W
        y = (y0 + vy * t) % H
        d.ellipse([x - sz, y - sz, x + sz, y + sz], fill=(220, 200, 165, int(rng.uniform(60, 150))))
    ov = ov.filter(ImageFilter.GaussianBlur(1.5))
    fr.alpha_composite(ov)
    fr.alpha_composite(Image.new("RGBA", (W, H), (150, 125, 90, 45)))


def scene3(t, fi):
    T = t
    if T >= 50.3:
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        show(fr, txt("NOS", "ExtraBold", 150), CX, 700, T, 50.38, pop=1.2)
        show(fr, txt("ACOSTUMBRAMOS", "ExtraBold", 150, YELLOW), CX, 850, T, 50.5, pop=1.2)
        return fr
    shots = [(33.85, "asph_b", (0.4, 0.4)), (37.35, "road_unfinished", (0.5, 0.55)), (41.4, "asph_rain", (0.5, 0.6)),
             (43.75, "asph_dust", (0.55, 0.45)), (46.75, "asph_e", (0.5, 0.5))]
    i = max(k for k in range(len(shots)) if shots[k][0] <= T)
    t0, name, (cx, cy) = shots[i]
    lt = T - t0
    z = 1.05 + 0.035 * lt + 0.05 * (1 - ease_out(lt / 0.25))  # pequeño "golpe" de zoom en cada corte
    fr = crop_zoom(R[name], z, cx, cy).convert("RGBA")
    if name == "asph_rain":
        rain_overlay(fr, T, fi)
    if name == "asph_dust":
        dust_overlay(fr, T)
    darken(fr, 0.38)
    fr.alpha_composite(R["vig"])
    if lt < 0.1:
        darken(fr, 0.6 * (1 - lt / 0.1))
    if 34.2 < T < 37.35:
        show(fr, txt("CALLES PEOR", "ExtraBold", 112), CX, 640, T, 34.3, 37.35, pop=1.3)
        show(fr, txt("QUE ANTES", "ExtraBold", 112, RED, stroke=0), CX, 770, T, 35.4, 37.35, pop=1.3)
        w = 560 * ease_out((T - 35.7) / 0.4)
        if w > 1:
            rect(fr, (CX - w / 2, 850, CX + w / 2, 858), WHITE, 0.9)
    if 37.35 < T < 41.4:
        show(fr, txt("Se prometen.", "ExtraBold", 92), CX, 520, T, 37.45, 41.4)
        show(fr, txt("Nunca se terminan.", "ExtraBold", 92, YELLOW), CX, 640, T, 40.1, 41.4)
    if 41.4 < T < 43.75:
        show(fr, txt("Llueve…", "ExtraBold", 100), CX, 600, T, 41.5, 43.75)
        show(fr, txt("los barrios se inundan", "ExtraBold", 74, YELLOW), CX, 720, T, 42.4, 43.75)
    if 43.75 < T < 46.75:
        show(fr, txt("Hace sol…", "ExtraBold", 100), CX, 600, T, 43.85, 46.75)
        show(fr, txt("el polvo entra en las casas", "ExtraBold", 66, YELLOW), CX, 720, T, 44.9, 46.75)
    if 46.75 < T < 50.3:
        show(fr, txt("Y nos acostumbramos.", "ExtraBold", 80), CX, 680, T, 46.85, 50.3)
        show(fr, txt("Ese es el verdadero problema.", "Medium", 50, GRAY), CX, 790, T, 48.4, 50.3)
    return fr


def draw_header_sismap(fr, t):
    show(fr, txt("RANKING SISMAP MUNICIPAL", "ExtraBold", 54), CX, 250, t, 51.8, dy=24)
    show(fr, txt("Junio 2026", "Medium", 40, GRAY), CX, 318, t, 52.0, dy=24)
    rect(fr, (CX - 40, 360, CX + 40, 366), RED, clamp((t - 52.1) / 0.3))


def scene4(t):
    T = t
    fr = bg()
    # rejilla tenue
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(0, H, 90):
        d.line([(0, y), (W, y)], fill=(255, 255, 255, 8))
    fr.alpha_composite(ov)
    draw_header_sismap(fr, T)
    source(fr, "Fuente: Informes SISMAP Municipal 2023–2026", clamp((T - 52) / 0.5))
    if T < 59.1:
        show(fr, txt("El Gobierno evalúa a", "Medium", 48, GRAY), CX, 560, T, 52.0, 59.1)
        if T > 53.1:
            val = int(round(160 * ease_out((T - 53.1) / 0.8)))
            show(fr, txt(str(val), "ExtraBold", 230), CX, 740, T, 53.1, 59.1, pop=0.9)
        show(fr, txt("AYUNTAMIENTOS", "ExtraBold", 64), CX, 900, T, 53.7, 59.1)
        show(fr, txt("Mide cómo se gestiona", "Medium", 46, GRAY), CX, 1030, T, 56.7, 59.1)
        show(fr, txt("cada municipio", "Medium", 46, GRAY), CX, 1088, T, 56.9, 59.1)
    elif T < 63.4:
        show(fr, txt("LOS LLANOS · PUESTO", "ExtraBold", 54, GRAY), CX, 540, T, 59.2, 63.4)
        if T > 59.35:
            val = max(1, int(round(146 * ease_out((T - 59.35) / 1.15))))
            punch = 1 + 0.12 * math.exp(-(T - 60.5) * 7) if T > 60.5 else 1
            col = RED
            spr = txt(str(val), "ExtraBold", 330, col)
            a = clamp((63.4 - T) / 0.25) * ease_out((T - 59.35) / 0.2)
            put(fr, spr, CX, 780, a, punch)
        show(fr, txt("de 160 ayuntamientos", "ExtraBold", 62), CX, 1010, T, 61.9, 63.4)
    elif T < 68.25:
        show(fr, txt("Puntuación SISMAP", "Medium", 46, GRAY), CX, 520, T, 63.45, 68.25)
        for i, (name, val, col, t0) in enumerate((("Los Llanos", 30.5, RED, 63.6), ("Promedio nacional", 55.0, BAR_BLUE, 65.4))):
            y = 680 + i * 240
            a = show(fr, txt(name, "ExtraBold", 50), 100 - 24, y - 70, T, t0 - 0.1, 68.25, dy=20, anchor="l")
            if a <= 0:
                continue
            rect(fr, (100, y, 900, y + 76), (255, 255, 255), 0.10 * a, 14)
            p = ease_out((T - t0) / 1.1)
            wv = 800 * val / 100 * p
            if wv > 2:
                rect(fr, (100, y, 100 + wv, y + 76), col, a, 14)
            put(fr, txt(f"{val * p:.1f}%" if p < 1 else f"{val:.1f}%".replace(".0%", "%"), "ExtraBold", 56), 100 + wv + 20 - 24, y + 38,
                a, anchor="l")
    else:
        show(fr, txt("Vamos para atrás", "ExtraBold", 84, RED), CX, 470, T, 68.3, dy=30)
        chart(fr, T)
    return fr


def chart(fr, T):
    s = 2
    x0, y0, cw, ch = 60, 560, 900, 760  # región de la capa
    L = Image.new("RGBA", (cw * s, ch * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    top, bot = 70, 560  # dentro de la capa (escala 1)
    xl, xr = 180, 830
    a = ease_out((T - 68.3) / 0.4)
    def ry(rank):
        return top + (rank - 1) / 159 * (bot - top)
    for r in (1, 40, 80, 120, 160):
        y = ry(r)
        d.line([(xl - 20) * s, y * s, (xr + 30) * s, y * s], fill=(255, 255, 255, int(28 * a)), width=2 * s)
    pts = [(210, 82, 68.6), (520, 142, 71.9), (800, 146, 73.0)]
    P = [(x, ry(r)) for x, r, _ in pts]
    # segmentos
    for i in range(2):
        p = ease_io((T - pts[i + 1][2]) / 0.55)
        if p > 0:
            xa, ya = P[i]
            xb, yb = P[i + 1]
            d.line([xa * s, ya * s, (xa + (xb - xa) * p) * s, (ya + (yb - ya) * p) * s], fill=RED + (255,), width=9 * s)
    for i, (x, r, tt) in enumerate(pts):
        if T > tt:
            q = spring(T - tt, w=16)
            rr = (13 if i < 2 else 17) * q
            col = WHITE if i == 0 else RED
            d.ellipse([(x - rr) * s, (ry(r) - rr) * s, (x + rr) * s, (ry(r) + rr) * s], fill=col + (255,))
    L = L.resize((cw, ch), Image.LANCZOS)
    fr.alpha_composite(L, dest=(x0, y0))
    for r, lab in ((1, "#1"), (160, "#160")):
        put(fr, txt(lab, "Medium", 30, GRAY, shadow=False), x0 + xl - 50, y0 + ry(r), a, anchor="c")
    put(fr, txt("mejor", "Medium", 24, GRAY, shadow=False), x0 + xl - 50, y0 + ry(1) + 34, 0.7 * a)
    put(fr, txt("peor", "Medium", 24, GRAY, shadow=False), x0 + xl - 50, y0 + ry(160) - 34, 0.7 * a)
    for i, (x, r, tt) in enumerate(pts):
        lab = txt(f"#{r}", "ExtraBold", 60 if i == 2 else 50, WHITE if i == 0 else RED)
        show(fr, lab, x0 + x, y0 + ry(r) - 62, T, tt, dy=16)
        show(fr, txt(("Sep 2023", "Dic 2024", "Jun 2026")[i], "Medium", 34, GRAY), x0 + x, y0 + bot + 60, T, tt, dy=10)
    show(fr, txt("mitad de la tabla", "Medium", 30, GRAY), x0 + 210, y0 + ry(82) + 50, T, 70.4, dy=10)


def scene5(t):
    T = t
    if T < 86.7:
        fr = bg()
        op = ease_io((T - 74.45) / 1.1)
        half = int(540 * op)
        if half > 0:
            L = R["cmp_left"].crop((540 - half, 0, 540, H))
            Rr = R["cmp_right"].crop((540, 0, 540 + half, H))
            fr.paste(L, (540 - half, 0))
            fr.paste(Rr, (540, 0))
            rect(fr, (537, 0, 543, H), WHITE, 0.9)
        dim = 0.25 + 0.5 * ease_io((T - 76.6) / 0.5)
        darken(fr, dim)
        fr.alpha_composite(R["vig"])
        label_ilustrativa(fr)
        for (lab, col, x, t0) in (("LOS LLANOS", RED, 270, 74.9), ("SAN JOSÉ DE", GREEN, 715, 75.0)):
            s = txt(lab, "ExtraBold", 40, WHITE, maxw=360)
            a = show(fr, s, x, 230, T, t0, dy=20)
        show(fr, txt("LAS MATAS", "ExtraBold", 40, WHITE), 715, 280, T, 75.1, dy=20)
        rect(fr, (190, 266, 350, 272), RED, clamp((T - 75.1) / 0.3))
        rect(fr, (635, 316, 795, 322), GREEN, clamp((T - 75.2) / 0.3))
        show(fr, txt("Santiago", "Medium", 34, GRAY), 715, 352, T, 76.1, dy=14)
        rows = [("Nació a inicios de los 1600", 76.95), ("Pueblo desde 1844", 79.45), ("No tiene playa", 82.6),
                ("No es cabecera de provincia", 83.75)]
        show(fr, txt("TAMBIÉN…", "ExtraBold", 50, GRAY), CX, 520, T, 76.9, 86.7)
        for i, (r, t0) in enumerate(rows):
            y = 640 + i * 105
            a = show(fr, txt(r, "ExtraBold", 50, maxw=700), 165 - 24, y, T, t0, 86.7, dy=20, anchor="l")
            if a > 0:
                ck = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
                cd = ImageDraw.Draw(ck)
                p = ease_out((T - t0 - 0.1) / 0.35)
                cd.line([(20, 62), (48, 90)], fill=GREEN + (255,), width=14)
                if p > 0:
                    cd.line([(42, 90), (42 + 58 * p, 90 - 66 * p)], fill=GREEN + (255,), width=14)
                put(fr, ck.resize((60, 60), Image.LANCZOS), 110, y + 4, a)
        show(fr, txt("IGUAL QUE NOSOTROS.", "ExtraBold", 72, YELLOW), CX, 1110, T, 85.4, 86.7, pop=1.2)
        return fr
    fr = bg()
    if T < 95.6:
        source(fr, "Fuente: Informe SISMAP Municipal, junio 2026")
        show(fr, txt("MISMO ORIGEN.", "ExtraBold", 76), CX, 250, T, 92.1)
        show(fr, txt("DISTINTO DESTINO.", "ExtraBold", 76, YELLOW), CX, 345, T, 93.7)
        base, hmax, bw = 1250, 420, 150
        cols = [(270, "Los Llanos", "San Pedro de Macorís", "#146", 30.5, RED, 86.8, 87.1),
                (690, "San José de las Matas", "Santiago", "#42", 70.5, GREEN, 88.75, 90.65)]
        for (x, name, prov, rank, val, col, tr, tv) in cols:
            show(fr, txt(name, "ExtraBold", 44, maxw=400), x, 470, T, 86.8, dy=20)
            show(fr, txt(prov, "Medium", 30, GRAY, maxw=400), x, 522, T, 86.9, dy=20)
            show(fr, txt(rank, "ExtraBold", 120, col), x, 650, T, tr, pop=1.3)
            rect(fr, (x - bw / 2, base - hmax, x + bw / 2, base), (255, 255, 255), 0.08 * clamp((T - 86.8) / 0.3), 10)
            p = ease_out((T - tv) / 1.2)
            hh = hmax * val / 100 * p
            if hh > 2:
                rect(fr, (x - bw / 2, base - hh, x + bw / 2, base), col, 1.0, 10)
                put(fr, txt(f"{val * p:.1f}%", "ExtraBold", 54), x, base - hh - 46, clamp((T - tv) / 0.2))
        rect(fr, (80, 1252, 940, 1256), GRAY, 0.4 * clamp((T - 86.8) / 0.3))
        return fr
    # la diferencia
    source(fr, "Fuente: Informe SISMAP Municipal, junio 2026")
    show(fr, txt("La diferencia no es", "Medium", 52, GRAY), CX, 470, T, 95.7)
    g = txt("LA GEOGRAFÍA", "ExtraBold", 80, GRAY)
    show(fr, g, CX, 570, T, 96.85)
    strike(fr, g, CX, 570, clamp((T - 97.35) / 0.35))
    if T > 97.95:
        punch = 1 + 0.10 * math.exp(-(T - 98.05) * 6)
        a = ease_out((T - 97.95) / 0.15)
        sc = 1.6 - 0.6 * spring(T - 97.95, w=16, z=0.55)
        put(fr, txt("GESTIÓN", "ExtraBold", 200, YELLOW, maxw=880), CX, 800, a, sc * punch)
    show(fr, txt("y la exigencia de su gente", "ExtraBold", 54), CX, 1000, T, 99.0)
    return fr


def scene6(t):
    T = t
    lt = T - 100.65
    base = R["sunset"].copy().convert("RGBA")
    bw, bh = base.size
    hz = 1240
    # jóvenes de espaldas (se van cuando arranca la guagua)
    ya = 1 - ease_io((T - 110.1) / 0.8)
    # guagua
    u = ease_io((T - 110.0) / 5.4) if T > 110.0 else 0.0
    dpt = 1 / (1 + 14 * u ** 1.15)
    vp = (bw / 2, hz)
    x0, y0, s0 = bw / 2 + 170, hz + 0.42 * (bh - hz), 0.95
    bx = vp[0] + (x0 - vp[0]) * dpt
    by = vp[1] + (y0 - vp[1]) * dpt
    sc = s0 * dpt
    bus = R["bus"]
    b = bus.resize((max(1, int(bus.width * sc)), max(1, int(bus.height * sc))), Image.BICUBIC)
    base.alpha_composite(b, dest=(int(bx - b.width / 2), int(by - b.height)))
    if ya > 0.01:
        y = R["youth"]
        if ya < 1:
            y = y.copy()
            y.putalpha(y.getchannel("A").point(lambda v: int(v * ya)))
        base.alpha_composite(y, dest=(-60, bh - y.height + 40))
    z = 1.2 - 0.2 * ease_io(lt / 15.1)  # zoom hacia afuera
    fr = crop_zoom(base.convert("RGB"), z, 0.5, 0.56).convert("RGBA")
    # degradado oscuro arriba para el texto
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad = np.zeros((H, 1), np.uint8)
    grad[:, 0] = np.clip(np.interp(np.arange(H), [0, 400, 1100], [200, 150, 0]), 0, 255).astype(np.uint8)
    ov.putalpha(Image.fromarray(grad).resize((W, H)))
    fr.alpha_composite(ov)
    fr.alpha_composite(R["vig"])
    if T < 108.1:
        show(fr, txt("¿Qué oportunidad tiene", "ExtraBold", 62), CX, 270, T, 100.75, 108.1)
        show(fr, txt("un joven en Los Llanos hoy?", "ExtraBold", 62, YELLOW), CX, 350, T, 101.2, 108.1)
        for i, (wd, t0, ts) in enumerate((("EMPRESAS", 103.3, 103.9), ("EMPLEO", 104.6, 105.0), ("ESPACIOS", 105.3, 106.4))):
            y = 520 + i * 125
            s = txt(wd, "ExtraBold", 100)
            a = show(fr, s, CX, y, T, t0, 108.1, dy=30)
            strike(fr, s, CX, y, clamp((T - ts) / 0.35), alpha=a, thick=12)
    if T > 108.1 and T < 112.4:
        show(fr, txt("Muchos terminan", "ExtraBold", 66), CX, 300, T, 108.2, 112.4)
        show(fr, txt("montándose en una guagua…", "ExtraBold", 62, YELLOW), CX, 385, T, 110.1, 112.4)
        show(fr, txt("y no vuelven.", "ExtraBold", 66), CX, 470, T, 111.6, 112.4)
    if T > 112.5:
        show(fr, txt("Un pueblo que pierde", "ExtraBold", 72), CX, 300, T, 112.6)
        show(fr, txt("a sus jóvenes,", "ExtraBold", 72), CX, 390, T, 113.0)
        show(fr, txt("pierde su futuro.", "ExtraBold", 84, YELLOW), CX, 500, T, 114.05, pop=1.2)
    return fr


def scene7(t):
    T = t
    fr = bg()
    if T < 125.0:
        if T < 119.6:
            show(fr, txt("DE ESTE PUEBLO", "ExtraBold", 84), CX, 640, T, 115.85, 119.6)
            show(fr, txt("han salido personas que", "Medium", 52), CX, 750, T, 116.6, 119.6)
            show(fr, txt("llegaron a lo más alto del país.", "Medium", 52), CX, 815, T, 117.6, 119.6)
        elif T < 122.5:
            show(fr, txt("Y hoy hay", "Medium", 56), CX, 620, T, 119.7, 122.5)
            show(fr, txt("LLANEROS", "ExtraBold", 130, YELLOW), CX, 740, T, 120.5, 122.5, pop=1.2)
            show(fr, txt("en cargos importantes.", "Medium", 56), CX, 860, T, 121.0, 122.5)
        else:
            show(fr, txt("Aun así…", "ExtraBold", 90, GRAY), CX, 660, T, 122.6, 125.0)
            show(fr, txt("el pueblo sigue igual.", "ExtraBold", 80), CX, 790, T, 123.6, 125.0)
        return fr
    if T < 129.85:
        if T > 125.05:
            x = T - 125.05
            sc = 2.4 - 1.4 * spring(x, w=15, z=0.6)
            punch = 1 + 0.06 * math.exp(-(T - 125.2) * 6) if T > 125.2 else 1
            put(fr, txt("2028", "ExtraBold", 330), CX, 560, ease_out(x / 0.12) * clamp((129.85 - T) / 0.2), sc * punch)
        show(fr, txt("elegimos", "Medium", 48, GRAY), CX, 790, T, 126.0, 129.85)
        for i, (wd, t0) in enumerate((("ALCALDE", 126.5), ("REGIDORES", 127.4), ("DIPUTADOS", 128.1), ("PRESIDENTE", 128.9))):
            y = 890 + i * 92
            a = show(fr, txt(wd, "ExtraBold", 64), CX, y, T, t0, 129.85, dy=24)
            if a > 0:
                rect(fr, (CX - 230, y - 4, CX - 216, y + 10), RED, a, 3)
        return fr
    if T < 137.45:
        show(fr, txt("Votar no es escoger", "Medium", 54, GRAY), CX, 400, T, 129.9, 137.45)
        show(fr, txt("un equipo de pelota.", "Medium", 54, GRAY), CX, 465, T, 130.3, 137.45)
        for i, (ph, t0, ts) in enumerate((("No se vota por camiseta", 132.6, 133.45), ("No se vota por un favor", 134.2, 135.05),
                                          ("No se vota por costumbre", 135.7, 136.6))):
            y = 680 + i * 150
            s = txt(ph, "ExtraBold", 64)
            a = show(fr, s, CX, y, T, t0, 137.45, dy=30)
            strike(fr, s, CX, y, clamp((T - ts) / 0.35), alpha=a, thick=10)
        return fr
    if T < 139.35:
        show(fr, txt("Antes de votar,", "Medium", 64, GRAY), CX, 680, T, 137.5)
        show(fr, txt("PREGUNTA:", "ExtraBold", 130, YELLOW), CX, 820, T, 138.5, pop=1.25)
        return fr
    if T < 142.95:
        for (q1, q2, t0, t1) in (("¿Qué ha hecho?", None, 139.35, 140.25), ("¿Qué propone?", None, 140.25, 141.25),
                                 ("¿Cómo va a", "rendir cuentas?", 141.25, 142.95)):
            if t0 <= T < t1:
                if q2:
                    show(fr, txt(q1, "ExtraBold", 110), CX, 700, T, t0, pop=1.15)
                    show(fr, txt(q2, "ExtraBold", 110), CX, 830, T, t0 + 0.05, pop=1.15)
                else:
                    show(fr, txt(q1, "ExtraBold", 116), CX, 770, T, t0, pop=1.15)
        return fr
    if T < 147.35:
        show(fr, txt("Los Llanos fue el primero", "ExtraBold", 70), CX, 620, T, 143.0)
        show(fr, txt("en ser libre.", "ExtraBold", 70), CX, 705, T, 144.4)
        show(fr, txt("Que no sea el último", "ExtraBold", 80, YELLOW), CX, 850, T, 145.6, pop=1.15)
        show(fr, txt("en exigir.", "ExtraBold", 80, YELLOW), CX, 945, T, 146.4, pop=1.15)
        w = 700 * ease_out((T - 146.6) / 0.5)
        if w > 1:
            rect(fr, (CX - w / 2, 1030, CX + w / 2, 1038), RED)
        return fr
    # cierre
    a_out = 1.0
    items = (("Infórmate.", WHITE, 147.45), ("Pregunta.", WHITE, 147.75), ("Exige.", YELLOW, 148.05))
    sprs = [txt(wd, "ExtraBold", 66, col) for wd, col, _ in items]
    ws = [s_.width - 2 * s_.info["pad"] for s_ in sprs]
    x = CX - 20 - (sum(ws) + 28 * 2) / 2
    for s_, w_, (_, _, t0) in zip(sprs, ws, items):
        show(fr, s_, x + w_ / 2, 660, T, t0, pop=1.2)
        x += w_ + 28
    w = 700 * ease_out((T - 148.2) / 0.5)
    if w > 1:
        rect(fr, (CX - w / 2, 750, CX + w / 2, 758), RED)
    a = show(fr, txt("Comparte si eres de Los Llanos", "Medium", 48), CX - 75, 850, T, 148.5)
    if a > 0:
        flag = Image.new("RGBA", (84, 56), (0, 0, 0, 0))
        fd = ImageDraw.Draw(flag)
        fd.rectangle([0, 0, 35, 22], fill=FLAG_BLUE)
        fd.rectangle([48, 0, 83, 22], fill=RED)
        fd.rectangle([0, 33, 35, 55], fill=RED)
        fd.rectangle([48, 33, 83, 55], fill=FLAG_BLUE)
        fd.rectangle([36, 0, 47, 55], fill=WHITE)
        fd.rectangle([0, 23, 83, 32], fill=WHITE)
        sw = txt("Comparte si eres de Los Llanos", "Medium", 48)
        put(fr, flag, CX - 75 + (sw.width - 2 * sw.info["pad"]) / 2 + 60, 852, a)
    return fr


# ----------------------------------------------------------------------------
# subtítulos, transiciones, glitch, grano
# ----------------------------------------------------------------------------
HIDE_SUBS = [(32.5, 33.85), (50.3, 51.65), (139.3, 150.0)]
_scache = {}


def sub_sprite(gi, active):
    k = (gi, active)
    if k in _scache:
        return _scache[k]
    g = SUBS[gi]["words"]
    size = 64
    font = F("ExtraBold", size)
    space = font.getlength(" ")
    total = sum(font.getlength(w["w"]) for w in g) + space * (len(g) - 1)
    while total > 820:
        size -= 2
        font = F("ExtraBold", size)
        space = font.getlength(" ")
        total = sum(font.getlength(w["w"]) for w in g) + space * (len(g) - 1)
    pad = 30
    asc, desc = font.getmetrics()
    im = Image.new("RGBA", (int(total) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for i, w in enumerate(g):
        col = YELLOW if i == active else WHITE
        d.text((x, pad), w["w"], font=font, fill=col, stroke_width=7, stroke_fill=(0, 0, 0))
        x += font.getlength(w["w"]) + space
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.6)))
    sh = sh.transform(sh.size, Image.AFFINE, (1, 0, 0, 0, 1, -6))
    im = Image.alpha_composite(sh, im)
    _scache[k] = im
    return im


def subtitles(fr, t):
    if any(a <= t < b for a, b in HIDE_SUBS):
        return
    for gi, s in enumerate(SUBS):
        if s["start"] <= t < s["end"]:
            act = -1
            for i, w in enumerate(s["words"]):
                nxt = s["words"][i + 1]["s"] if i + 1 < len(s["words"]) else s["end"]
                if w["s"] <= t < max(nxt, w["e"]):
                    act = i
            x = t - s["start"]
            sc = 0.9 + 0.1 * ease_out(x / 0.12)
            put(fr, sub_sprite(gi, act), CX, 1420, ease_out(x / 0.08), sc)
            return


GLITCH = [(32.55, 0.22, 1.0), (32.95, 0.06, 0.5), (33.4, 0.05, 0.4), (50.38, 0.12, 0.6), (60.48, 0.10, 0.5),
          (98.0, 0.12, 0.6), (125.15, 0.12, 0.6), (13.12, 0.08, 0.35), (51.62, 0.06, 0.3), (74.37, 0.06, 0.3),
          (100.62, 0.06, 0.3), (115.72, 0.06, 0.3)]


def glitch(arr, t, fi):
    k = 0
    for (g0, d, s) in GLITCH:
        if g0 <= t < g0 + d:
            k = max(k, s)
    if k == 0:
        return arr
    rng = np.random.default_rng(fi * 13 + 5)
    dx = int(14 * k)
    out = arr.copy()
    out[..., 0] = np.roll(arr[..., 0], dx, 1)
    out[..., 2] = np.roll(arr[..., 2], -dx, 1)
    for _ in range(int(6 * k) + 1):
        y0 = int(rng.uniform(0, H - 80))
        hh = int(rng.uniform(10, 90))
        out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], int(rng.uniform(-60, 60) * k), 1)
    return out


def frame(fi):
    t = fi / FPS
    if t < SC[1]:
        fr = scene1(t)
    elif t < SC[2]:
        fr = scene2(t)
    elif t < SC[3]:
        fr = scene3(t, fi)
    elif t < SC[4]:
        fr = scene4(t)
    elif t < SC[5]:
        fr = scene5(t)
    elif t < SC[6]:
        fr = scene6(t)
    else:
        fr = scene7(t)
    subtitles(fr, t)
    # cortes a negro breves (~7 frames) entre escenas
    blk = 0.0
    for b in SC[1:-1]:
        d = abs(t - b)
        blk = max(blk, clamp(1 - (d - 0.08) / 0.06))
    darken(fr, blk)
    # fundido final
    if t > TOTAL - 1.2:
        darken(fr, (t - (TOTAL - 1.2)) / 1.2)
    # franja de la bandera
    ImageDraw.Draw(fr).rectangle([0, 0, W // 2, 11], fill=FLAG_BLUE)
    ImageDraw.Draw(fr).rectangle([W // 2, 0, W, 11], fill=RED)
    arr = np.asarray(fr.convert("RGB"))
    arr = glitch(arr, t, fi)
    gr = R["grain"][fi % len(R["grain"])]
    gr = np.repeat(np.repeat(gr, 2, 0), 2, 1)[..., None]
    arr = np.clip(arr.astype(np.float32) + gr, 0, 255).astype(np.uint8)
    return arr


def worker(args):
    k, f0, f1, out = args
    load_res()
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", "9M", "-bufsize", "18M", "-pix_fmt", "yuv420p",
                          "-threads", "2", out], stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        p.stdin.write(frame(fi).tobytes())
        if (fi - f0) % 150 == 0:
            print(f"[w{k}] {fi - f0}/{f1 - f0}", flush=True)
    p.stdin.close()
    p.wait()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--end", type=float, default=TOTAL)
    ap.add_argument("--out", default="los_llanos_final.mp4")
    ap.add_argument("--still", type=float, nargs="*")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    prep()
    if a.still:
        load_res()
        for s in a.still:
            Image.fromarray(frame(int(round(s * FPS)))).save(f"build/still_{s}.png")
        return
    f0, f1 = int(a.start * FPS), int(round(a.end * FPS))
    n = a.jobs
    step = math.ceil((f1 - f0) / n)
    parts = [(k, f0 + k * step, min(f1, f0 + (k + 1) * step), f"build/part_{k}.mp4") for k in range(n)]
    with Pool(n) as pool:
        outs = pool.map(worker, parts)
    with open("build/parts.txt", "w") as f:
        for o in outs:
            f.write(f"file '{os.path.basename(o)}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "build/parts.txt",
                    "-ss", str(a.start), "-t", str(a.end - a.start), "-i", "build/mezcla.wav",
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", "-shortest", a.out], check=True)
    print("listo:", a.out)


if __name__ == "__main__":
    main()
