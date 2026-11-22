"""Composite rendered frames + overlays -> 1080x1920 PNG stream piped to ffmpeg.
usage: python3 compose.py [--frames a,b,c] [--out final.mp4] [--preview DIR]"""
import sys, os, json, math, glob, argparse, subprocess, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import timeline as T

W, H = 1080, 1920
FPS = 30
FR = os.environ.get("FR", "/home/user/work/frames")
FONT_BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
FONT_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
RED = (232, 28, 36)
WHITE = (255, 255, 255)
GREEN = (40, 200, 90)

_fonts = {}


def font(path, size):
    k = (path, int(size))
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, int(size))
    return _fonts[k]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ss(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out_back(x):
    x = clamp(x)
    c1 = 1.70158 * 0.8
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


# ------------------------------------------------------------------ subtitles
CHUNKS = """¿Alguna vez|te has preguntado|qué pasa dentro|de una bicicleta|cuando cambias|de velocidad?|Vamos por dentro.|Todo empieza|en tu mano.|Cuando presionas|el cambio,|jalas un cable|de acero|muy delgado.|Ese cable viaja|por dentro|del cuadro|hasta la rueda|de atrás,|y mueve una pieza|llamada desviador.|El desviador|empuja la cadena|hacia un piñón|más grande.|Los dientes|tienen rampas|especiales|que ayudan|a la cadena|a subir|sin que dejes|de pedalear.|Si sueltas|el cable,|un resorte|devuelve el desviador,|y la cadena|baja a un piñón|más pequeño.|Adelante|pasa lo mismo,|pero con los platos|grandes|que están junto|a los pedales.|¿Y para qué sirve?|Plato grande|y piñón pequeño:|con cada pedalada,|la rueda gira|más de cuatro veces.|Vas rápido,|pero cuesta más.|Plato pequeño|y piñón grande:|la rueda da|una sola vuelta|por pedalada.|Vas más lento,|pero subes|la cuesta|sin sufrir.|Por eso|los ciclistas|cambian todo el tiempo:|buscan|el esfuerzo justo|para cada camino.|Síguenos|para ver más cosas…|por dentro.""".split("|")
KEYWORDS = {"velocidad", "dentro", "mano", "cambio", "cable", "cuadro", "desviador", "cadena", "piñón", "grande",
            "rampas", "resorte", "pequeño", "platos", "pedales", "cuatro", "veces", "rápido", "lento", "cuesta",
            "esfuerzo", "justo", "sirve", "acero", "subir", "baja", "plato"}


def norm(w):
    return "".join(c for c in w.lower() if c.isalnum() or c in "áéíóúñü")


def build_subs():
    words = json.load(open("/home/user/work/words.json"))
    i = 0
    subs = []
    for ch in CHUNKS:
        toks = ch.split()
        times = []
        for tk in toks:
            if i < len(words) and norm(words[i]["w"]) == norm(tk):
                times.append((words[i]["s"], words[i]["e"]))
                i += 1
            else:
                # word not in transcript (e.g. elided "a"): borrow neighbour timing
                prev = times[-1] if times else (words[i]["s"], words[i]["s"])
                times.append((prev[1], prev[1]))
        subs.append(dict(text=ch, toks=toks, t0=times[0][0], t1=times[-1][1], wt=times))
    assert i == len(words), (i, len(words))
    for k, s in enumerate(subs):
        nxt = subs[k + 1]["t0"] if k + 1 < len(subs) else T.DUR
        s["show0"] = max(0.0, s["t0"] - 0.06)
        s["show1"] = min(nxt - 0.02, s["t1"] + 0.55) if nxt - s["t1"] > 0.6 else nxt - 0.02
    return subs


SUBS = None


def draw_sub(img, t):
    for s in SUBS:
        if s["show0"] <= t < s["show1"]:
            break
    else:
        return
    age = t - s["show0"]
    p = ease_out_back(age / 0.16)
    alpha = clamp(age / 0.08) * clamp((s["show1"] - t) / 0.06)
    size = 92
    toks = s["toks"]
    f = font(FONT_BLACK, size)
    sp = f.getlength(" ") + size * 0.14
    widths = [f.getlength(tk) for tk in toks]
    total = sum(widths) + sp * (len(toks) - 1)
    maxw = W - 120
    lines = [list(range(len(toks)))]
    if total > maxw:
        # try two lines
        best = None
        for cut in range(1, len(toks)):
            a = sum(widths[:cut]) + sp * (cut - 1)
            b = sum(widths[cut:]) + sp * (len(toks) - cut - 1)
            m = max(a, b)
            if best is None or m < best[0]:
                best = (m, cut)
        cut = best[1]
        lines = [list(range(cut)), list(range(cut, len(toks)))]
        if best[0] > maxw:
            size = int(size * maxw / best[0])
            f = font(FONT_BLACK, size)
            sp = f.getlength(" ") + size * 0.14
            widths = [f.getlength(tk) for tk in toks]
    # render onto layer then scale for pop
    lh = int(size * 1.12)
    layer = Image.new("RGBA", (W, lh * len(lines) + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    stroke = max(8, int(size * 0.12))
    for li, idxs in enumerate(lines):
        lw = sum(widths[k] for k in idxs) + sp * (len(idxs) - 1)
        x = (W - lw) / 2
        y = 30 + li * lh
        for k in idxs:
            tk = toks[k]
            col = RED if norm(tk) in KEYWORDS else (10, 10, 12)
            d.text((x, y), tk, font=f, fill=col, stroke_width=stroke, stroke_fill=WHITE)
            x += widths[k] + sp
    # soft shadow under halo
    sh = layer.split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.45))
    shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    shadow.putalpha(sh)
    comp = Image.alpha_composite(shadow, layer)
    sc = 0.86 + 0.14 * p
    nw, nh = int(comp.width * sc), int(comp.height * sc)
    comp = comp.resize((nw, nh), Image.LANCZOS)
    if alpha < 1:
        a = comp.split()[3].point(lambda v: int(v * alpha))
        comp.putalpha(a)
    cy = 300
    img.alpha_composite(comp, (int((W - nw) / 2), int(cy - nh / 2)))


# ------------------------------------------------------------------ labels
LABELS = [  # (key word, sub, anchor, t0, t1, dx, dy) offsets in px for label from anchor
    ("CABLE", "DE ACERO", "cable", 9.75, 11.55, -330, 330),
    ("DESVIADOR", "TRASERO", "rd", 16.65, 19.10, -60, 430),
    ("PIÑONES", "TRASEROS", "cassette", 19.75, 21.75, 120, 300),
    ("RAMPAS", "EN LOS DIENTES", "ramp", 22.05, 25.95, 80, 420),
    ("RESORTE", "DE RETORNO", "spring", 27.80, 31.30, 60, 400),
    ("PLATOS", "DELANTEROS", "rings", 33.95, 36.35, 40, 430),
    ("50", "DIENTES", "ring_top", 37.70, 42.45, 120, -330),
    ("11", "DIENTES", "cog_top", 38.55, 42.45, -60, -470),
    ("34", "DIENTES", "ring_top", 44.95, 49.35, 120, -330),
    ("34", "DIENTES", "cog_top", 45.75, 49.35, -60, -470),
]
SMOOTH = {}


def draw_label(img, key, sub, ax, ay, t, t0, t1, dx, dy, lid):
    age = t - t0
    if age < 0 or t > t1:
        return
    fade = clamp(age / 0.25) * clamp((t1 - t) / 0.3)
    grow = ss(age / 0.45)
    # smooth anchor (avoid jitter)
    sx, sy = SMOOTH.get(lid, (ax, ay))
    sx, sy = sx + (ax - sx) * 0.5, sy + (ay - sy) * 0.5
    SMOOTH[lid] = (sx, sy)
    ax, ay = sx, sy
    lx, ly = ax + dx, ay + dy
    fk = font(FONT_BLACK, 74 if not key.isdigit() else 110)
    fs = font(FONT_XB, 40)
    kw = fk.getlength(key)
    sw = fs.getlength(sub)
    bw = max(kw, sw)
    # keep label inside safe area & below subtitle zone
    lx = clamp(lx, 70 + bw / 2, W - 70 - bw / 2)
    ly = clamp(ly, 520, H - 260)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # line from anchor to label (elbow)
    ex = lx
    ey = ly - (60 if dy > 0 else -60) - (0 if dy > 0 else 40)
    if dy < 0:
        ey = ly + (fk.size * 0.95 + 40 if key.isdigit() else 120)
    pts = [(ax, ay), (ax + (ex - ax) * grow, ay + (ey - ay) * grow)]
    d.line(pts, fill=(255, 255, 255, int(235 * fade)), width=4)
    r = 11
    d.ellipse((ax - r, ay - r, ax + r, ay + r), outline=(255, 255, 255, int(255 * fade)), width=4)
    d.ellipse((ax - 5, ay - 5, ax + 5, ay + 5), fill=(232, 28, 36, int(255 * fade)))
    if grow > 0.6:
        tf = clamp((grow - 0.6) / 0.4) * fade
        off = (1 - ss((grow - 0.6) / 0.4)) * 30
        ty = ly - (fk.size * 0.55 if dy > 0 else 0)
        if dy < 0:
            ty = ly - fk.size * 0.2
        # keyword (red, white halo for legibility)
        x0 = lx - kw / 2
        d.text((x0, ty + off), key, font=fk, fill=(232, 28, 36, int(255 * tf)), stroke_width=5,
               stroke_fill=(255, 255, 255, int(255 * tf)))
        d.text((lx - sw / 2, ty + fk.size * 1.02 + off), sub, font=fs, fill=(255, 255, 255, int(255 * tf)),
               stroke_width=3, stroke_fill=(0, 0, 0, int(200 * tf)))
    sh = layer.split()[3].filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.5))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(sh)
    img.alpha_composite(shadow)
    img.alpha_composite(layer)


# ------------------------------------------------------------------ counters & icons
def draw_counter(img, t, a, beta, base):
    """S7 / S8 wheel-turn counter"""
    specs = [(39.30, 42.50, T.TURN1, 50 / 11, "main"), (46.60, 49.40, T.TURN2, 1.0, "B")]
    for (t0, t1, turn, ratio, did) in specs:
        if not (t0 <= t <= t1 + 0.1):
            continue
        fade = clamp((t - t0) / 0.3) * clamp((t1 + 0.1 - t) / 0.3)
        b0 = base.get(did)
        if b0 is None:
            continue
        crank_turns = clamp((beta["ring"] - b0[0]) / (2 * math.pi), 0, 1.0)
        wheel_turns = max(0.0, (beta["cog"] - b0[1]) / (2 * math.pi))
        if crank_turns >= 0.999:
            wheel_turns = ratio
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        # panel
        px, py, pw, ph = 70, 1480, W - 140, 300
        d.rounded_rectangle((px, py, px + pw, py + ph), 36, fill=(10, 10, 12, int(185 * fade)),
                            outline=(255, 255, 255, int(60 * fade)), width=2)
        # pedal progress ring
        cx, cy, R = px + 150, py + ph / 2, 92
        d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(255, 255, 255, int(70 * fade)), width=14)
        if crank_turns > 0.002:
            d.arc((cx - R, cy - R, cx + R, cy + R), -90, -90 + 360 * crank_turns, fill=(255, 255, 255, int(255 * fade)), width=14)
        fn = font(FONT_BLACK, 64)
        txt = "1" if crank_turns >= 0.999 else "%d%%" % int(crank_turns * 100)
        d.text((cx - fn.getlength(txt) / 2, cy - 40), txt, font=fn, fill=(255, 255, 255, int(255 * fade)))
        fs = font(FONT_XB, 34)
        d.text((cx - fs.getlength("PEDALADA") / 2, py + ph - 54), "PEDALADA", font=fs, fill=(255, 255, 255, int(220 * fade)))
        # wheel turns number
        val = wheel_turns
        txt = ("%.1f" % (math.floor(val * 10 + 1e-6) / 10)) if ratio > 1.5 else ("%.1f" % min(val, 1.0) if val < 0.999 else "1")
        if ratio > 1.5 and crank_turns >= 0.999:
            txt = "4.5"
        fb = font(FONT_BLACK, 150)
        col = (232, 28, 36, int(255 * fade))
        tx = px + 330
        d.text((tx, py + 40), txt, font=fb, fill=col, stroke_width=4, stroke_fill=(255, 255, 255, int(255 * fade)))
        tw = fb.getlength(txt)
        ft = font(FONT_XB, 40)
        lab = "VUELTAS" if txt != "1" else "VUELTA"
        d.text((tx + tw + 24, py + 78), lab, font=ft, fill=(255, 255, 255, int(255 * fade)))
        d.text((tx + tw + 24, py + 126), "DE LA RUEDA", font=ft, fill=(255, 255, 255, int(255 * fade)))
        img.alpha_composite(layer)


def leg_icon(color, effort, size=260):
    S_ = 4
    s = size * S_
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = color + (255,)
    # circle badge
    d.ellipse((0, 0, s - 1, s - 1), fill=(12, 12, 14, 215), outline=c, width=int(8 * S_))
    # leg: thigh, shin, foot as thick rounded lines (cyclist pedaling pose)
    hip = (0.36 * s, 0.30 * s)
    knee = (0.66 * s, 0.46 * s) if effort else (0.62 * s, 0.42 * s)
    ankle = (0.50 * s, 0.74 * s) if effort else (0.50 * s, 0.72 * s)
    toe = (0.70 * s, 0.77 * s)
    wdt = int(0.11 * s)
    for a, b in ((hip, knee), (knee, ankle)):
        d.line((a, b), fill=c, width=wdt)
    for p in (hip, knee, ankle):
        r = wdt / 2
        d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=c)
    # pedal crank circle under the foot
    pc = (0.47 * s, 0.70 * s); pr = 0.16 * s
    d.ellipse((pc[0] - pr, pc[1] - pr, pc[0] + pr, pc[1] + pr), outline=(255, 255, 255, 150), width=int(0.02 * s))
    d.line((ankle, toe), fill=c, width=int(wdt * 0.75))
    r = wdt * 0.375
    d.ellipse((toe[0] - r, toe[1] - r, toe[0] + r, toe[1] + r), fill=c)
    if effort:
        # strain marks around the thigh
        for k, (x, y, ang) in enumerate(((0.52, 0.18, -60), (0.70, 0.24, -30), (0.82, 0.38, 0))):
            L = 0.09 * s
            cx, cy = x * s, y * s
            dx, dy = math.cos(math.radians(ang)) * L / 2, math.sin(math.radians(ang)) * L / 2
            d.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=c, width=int(0.035 * s))
        # sweat drop
        dx0, dy0 = 0.24 * s, 0.52 * s
        d.ellipse((dx0 - 0.04 * s, dy0, dx0 + 0.04 * s, dy0 + 0.08 * s), fill=c)
        d.polygon([(dx0 - 0.036 * s, dy0 + 0.03 * s), (dx0, dy0 - 0.05 * s), (dx0 + 0.036 * s, dy0 + 0.03 * s)], fill=c)
    else:
        # check mark
        pts = [(0.20 * s, 0.56 * s), (0.27 * s, 0.63 * s), (0.38 * s, 0.50 * s)]
        d.line(pts, fill=c, width=int(0.04 * s), joint="curve")
    return im.resize((size, size), Image.LANCZOS)


ICONS = {}


def draw_icon(img, t):
    specs = [(42.85, 44.70, "red"), (49.45, 52.15, "green")]
    for t0, t1, kind in specs:
        if t0 <= t <= t1:
            if kind not in ICONS:
                ICONS[kind] = leg_icon(RED if kind == "red" else GREEN, kind == "red")
            ic = ICONS[kind]
            p = ease_out_back((t - t0) / 0.35)
            fade = clamp((t1 - t) / 0.25)
            sz = max(2, int(ic.width * (0.5 + 0.5 * p)))
            im = ic.resize((sz, sz), Image.LANCZOS)
            if fade < 1:
                im.putalpha(im.split()[3].point(lambda v: int(v * fade)))
            img.alpha_composite(im, (int(W - 90 - ic.width / 2 - sz / 2), int(1560 - sz / 2)))
            # caption
            f = font(FONT_BLACK, 46)
            txt = "MÁS ESFUERZO" if kind == "red" else "MENOS ESFUERZO"
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            col = (RED if kind == "red" else GREEN) + (int(255 * fade * clamp((t - t0) / 0.3)),)
            tw = f.getlength(txt)
            d.text((W - 90 - ic.width / 2 - tw / 2, 1700), txt, font=f, fill=col, stroke_width=4,
                   stroke_fill=(255, 255, 255, int(255 * fade * clamp((t - t0) / 0.3))))
            img.alpha_composite(layer)


# ------------------------------------------------------------------ FX
rng = np.random.default_rng(11)
DUST = [dict(x=rng.random(), y=rng.random(), z=rng.random(), ph=rng.random() * 6.28, sp=0.3 + rng.random())
        for _ in range(140)]
DUST_SPRITES = {}


def dust_sprite(r, blur):
    k = (r, blur)
    if k not in DUST_SPRITES:
        s = int(r * 2 + blur * 4 + 4)
        im = Image.new("L", (s, s), 0)
        d = ImageDraw.Draw(im)
        c = s / 2
        d.ellipse((c - r, c - r, c + r, c + r), fill=255)
        if blur:
            im = im.filter(ImageFilter.GaussianBlur(blur))
        DUST_SPRITES[k] = im
    return DUST_SPRITES[k]


def draw_dust(arr, t, strength):
    if strength <= 0:
        return arr
    acc = np.zeros((H, W), np.float32)
    for p in DUST:
        z = p["z"]
        x = (p["x"] + 0.004 * t * p["sp"] + 0.01 * math.sin(t * 0.4 + p["ph"])) % 1.0
        y = (p["y"] - 0.006 * t * p["sp"] * (0.3 + z) + 0.008 * math.cos(t * 0.3 + p["ph"])) % 1.0
        # depth: near particles large & blurred (bokeh), far ones tiny & sharp
        if z > 0.85:
            r, blur, a = 9 + 10 * (z - 0.85) / 0.15, 6, 0.16
        elif z > 0.5:
            r, blur, a = 2.5, 1, 0.45
        else:
            r, blur, a = 1.4, 0, 0.6
        r = round(r)
        tw = 0.6 + 0.4 * math.sin(t * 2.0 * p["sp"] + p["ph"])
        spr = np.asarray(dust_sprite(r, blur), np.float32) / 255.0
        cx, cy = int(x * W), int(y * H)
        s = spr.shape[0]
        x0, y0 = cx - s // 2, cy - s // 2
        x1, y1 = x0 + s, y0 + s
        if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
            continue
        acc[y0:y1, x0:x1] += spr * a * tw
    # brighter where image is lit (dust visible in light)
    lum = arr[..., :3].mean(2) / 255.0
    lightmask = 0.35 + 0.65 * np.clip(lum * 2.2, 0, 1)
    add = (acc * lightmask * strength * 255)[..., None] * np.array([1.0, 0.97, 0.92])
    out = arr.astype(np.float32)
    out[..., :3] = np.clip(out[..., :3] + add, 0, 255)
    return out.astype(np.uint8)


def speed_lines(img, t, strength):
    if strength <= 0:
        return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = np.random.default_rng(5)
    for k in range(38):
        y = r.random() * H
        if 0.20 * H < y < 0.30 * H:
            continue
        L = 160 + r.random() * 520
        spd = 2600 + r.random() * 2400
        x = W + 400 - ((t * spd + r.random() * 4000) % (W + 1200))
        a = int((60 + r.random() * 120) * strength)
        wdt = 2 if r.random() < 0.7 else 4
        d.line((x, y, x + L, y), fill=(255, 255, 255, a), width=wdt)
    layer = layer.filter(ImageFilter.GaussianBlur(1.2))
    img.alpha_composite(layer)


def sparkle(img, x, y, k, size=1.0):
    """metal glint star, k in [0,1] life"""
    if k <= 0 or k >= 1:
        return
    a = math.sin(math.pi * k)
    L = (60 + 80 * a) * size
    layer = Image.new("RGBA", (int(L * 2 + 40), int(L * 2 + 40)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = layer.width / 2
    rot = k * 1.2
    for ang, ln, wd in ((0, L, 4), (math.pi / 2, L, 4), (math.pi / 4, L * 0.45, 3), (3 * math.pi / 4, L * 0.45, 3)):
        dx, dy = math.cos(ang + rot) * ln, math.sin(ang + rot) * ln
        d.line((c - dx, c - dy, c + dx, c + dy), fill=(255, 255, 255, int(230 * a)), width=wd)
    d.ellipse((c - 10 * a, c - 10 * a, c + 10 * a, c + 10 * a), fill=(255, 255, 255, int(255 * a)))
    layer = layer.filter(ImageFilter.GaussianBlur(1.5))
    glow = layer.filter(ImageFilter.GaussianBlur(10))
    img.alpha_composite(glow, (int(x - c), int(y - c)))
    img.alpha_composite(layer, (int(x - c), int(y - c)))


def click_ring(img, x, y, k):
    if k <= 0 or k >= 1:
        return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    R = 30 + 120 * k
    d.ellipse((x - R, y - R, x + R, y + R), outline=(255, 255, 255, int(220 * (1 - k))), width=5)
    img.alpha_composite(layer)


# ------------------------------------------------------------------ grading
VIG = None


def grade(arr):
    global VIG
    if VIG is None:
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.70)) ** 2)
        VIG = np.clip(1.0 - 0.45 * np.clip(r - 0.35, 0, 1) ** 1.6, 0, 1).astype(np.float32)[..., None]
    f = arr.astype(np.float32) / 255.0
    # bloom on highlights
    hi = np.clip(f - 0.72, 0, 1)
    him = Image.fromarray((hi * 255 * 3).clip(0, 255).astype(np.uint8))
    bl = np.asarray(him.filter(ImageFilter.GaussianBlur(18)), np.float32) / 255.0
    f = f + bl * 0.20
    f = f * VIG
    # subtle grain
    g = np.random.default_rng().normal(0, 0.008, (H // 2, W // 2)).astype(np.float32)
    g = np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None]
    f = f + g
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)


# ------------------------------------------------------------------ main
def load_meta():
    meta = {}
    for fn in sorted(glob.glob(os.path.join(FR, "meta_*.jsonl")), key=os.path.getmtime):
        for line in open(fn):
            try:
                m = json.loads(line)
            except Exception:
                continue
            meta[(m["f"], m["shot"])] = m
    return meta


def main():
    global SUBS
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="")
    ap.add_argument("--preview", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    SUBS = build_subs()
    meta = load_meta()
    T.explode_final(55.0)
    landings = dict(T.LANDINGS)
    frames = [int(x) for x in args.frames.split(",")] if args.frames else list(range(T.NFRAMES))
    # counters need beta at the start of each turn
    base = {}
    for did, tstart, shot in (("main", T.TURN1[0], "gears1"), ("B", T.TURN2[0], "gears2")):
        f0 = int(math.floor(tstart * FPS))
        m = meta.get((f0, shot))
        if m:
            b = m["a"]["beta"]
            # chain speed is ~0 at turn start; use frame value
            base[did] = (b["ring"], b["cog"])
    proc = None
    if args.out:
        proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                 "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-", "-i", "/home/user/work/mix.wav",
                                 "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                                 "-profile:v", "high", "-movflags", "+faststart",
                                 "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                                 "-shortest", args.out], stdin=subprocess.PIPE)
    for f in frames:
        t = f / FPS
        layers = T.shots_at(t)
        acc = None
        anch = None
        beta = None
        road_w = 0.0
        for name, fn, w in layers:
            p = os.path.join(FR, name, "%05d.png" % f)
            im = Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS)
            a = np.asarray(im, np.float32)
            acc = a * w if acc is None else acc + a * w
            m = meta.get((f, name))
            if m and (anch is None or w >= 0.5):
                anch = m["a"]
                beta = m["a"]["beta"]
            if name in ("road", "hill"):
                road_w += w
        base_img = Image.fromarray(acc.clip(0, 255).astype(np.uint8)).filter(ImageFilter.UnsharpMask(2, 60, 2))
        arr = grade(np.asarray(base_img))
        # dust (studio mostly)
        arr = draw_dust(arr, t, 1.0 - 0.6 * road_w)
        img = Image.fromarray(arr).convert("RGBA")
        speed_lines(img, t, road_w if 42.4 < t < 44.9 else 0.0)
        if anch:
            # click flash at the ratchet
            rx, ry = anch["ratchet"][0] * W, anch["ratchet"][1] * H
            click_ring(img, rx, ry, (t - 8.84) / 0.35)
            # reassembly glints
            for name, tl in landings.items():
                k = (t - tl + 0.05) / 0.45
                if 0 < k < 1 and name in anch["parts"]:
                    (px, py, pz), e = anch["parts"][name]
                    if pz > 0:
                        sparkle(img, px * W, py * H, k, 0.7 if name.startswith("bolt") else 1.0)
            for i, (key, sub, an, t0, t1, dx, dy) in enumerate(LABELS):
                if t0 <= t <= t1 and an in anch:
                    ax, ay, az = anch[an]
                    draw_label(img, key, sub, ax * W, ay * H, t, t0, t1, dx, dy, i)
            if beta:
                draw_counter(img, t, anch, beta, base)
        draw_icon(img, t)
        draw_sub(img, t)
        out = img.convert("RGB")
        # fades
        k = 1.0
        if t < 0.35:
            k = ss(t / 0.35)
        if t > 59.2:
            k = 1 - ss((t - 59.2) / 0.95)
        if k < 1:
            out = Image.fromarray((np.asarray(out, np.float32) * k).astype(np.uint8))
        if args.preview:
            os.makedirs(args.preview, exist_ok=True)
            out.save(os.path.join(args.preview, "%05d.png" % f))
        if proc:
            proc.stdin.write(out.tobytes())
        if f % 60 == 0:
            print("composed", f, flush=True)
    if proc:
        proc.stdin.close()
        proc.wait()


if __name__ == "__main__":
    main()
