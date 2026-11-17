"""Renderizador del video vertical Capital Curioso · NSA (1080x1920, 30 fps).
Uso: python3 video.py WORKDIR START_FRAME END_FRAME OUT.mp4
"""
import sys, json, math, os, functools
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from timeline import *

WORK = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(WORK, '..', 'assets', 'Capital_Curioso_NSA')
FONTS = os.path.join(WORK, 'fonts')
W, H = 1080, 1920
NAVY = (10, 18, 40); DEEP = (3, 6, 15); RED = (228, 30, 45); WHITE = (242, 242, 242)
COOL = (150, 175, 215)

# ---------------------------------------------------------------- utilidades
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lin(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= a)
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def eout(x): x = clamp(x); return 1 - (1 - x) ** 3
def back(x):
    x = clamp(x); c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def hrand(*k):  # pseudo-aleatorio determinista
    h = hash(k) & 0xffffffff
    return np.random.default_rng(h)

@functools.lru_cache(None)
def font(name, size): return ImageFont.truetype(os.path.join(FONTS, name + '.ttf'), size)

@functools.lru_cache(512)
def text_rgba(txt, fname, size, fill=WHITE, stroke=0, sfill=(0, 0, 0), spacing=0, shadow=0):
    f = font(fname, size)
    if spacing:
        widths = [f.getbbox(c)[2] - f.getbbox(c)[0] if c != ' ' else size * 0.3 for c in txt]
        tw = int(sum(widths) + spacing * (len(txt) - 1)) + 2 * stroke + 8
    else:
        bb = f.getbbox(txt, stroke_width=stroke); tw = bb[2] - bb[0] + 8
    asc, desc = f.getmetrics(); th = asc + desc + 2 * stroke + 8
    pad = shadow * 2
    im = Image.new('RGBA', (tw + pad * 2, th + pad * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    def draw(dr, col, scol):
        if spacing:
            x = stroke + 4 + pad
            for c, w_ in zip(txt, widths):
                dr.text((x, 4 + pad), c, font=f, fill=col, stroke_width=stroke, stroke_fill=scol); x += w_ + spacing
        else:
            dr.text((4 + pad - f.getbbox(txt, stroke_width=stroke)[0], 4 + pad), txt, font=f, fill=col,
                    stroke_width=stroke, stroke_fill=scol)
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); draw(ImageDraw.Draw(sh), (0, 0, 0, 200), (0, 0, 0, 200))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(shadow)))
        d = ImageDraw.Draw(im)
    draw(d, fill, sfill)
    return np.array(im)

def overlay(base, rgba, cx, cy, alpha=1.0, scale=1.0, anchor='c'):
    """Compone un RGBA (np) sobre base (np RGB uint8) centrado en cx,cy."""
    if alpha <= 0.003 or rgba is None: return base
    if scale != 1.0:
        h0, w0 = rgba.shape[:2]
        nw, nh = max(1, int(w0 * scale)), max(1, int(h0 * scale))
        rgba = cv2.resize(rgba, (nw, nh), interpolation=cv2.INTER_LINEAR)
    h, w = rgba.shape[:2]
    if anchor == 'c': x0, y0 = int(cx - w / 2), int(cy - h / 2)
    elif anchor == 'l': x0, y0 = int(cx), int(cy - h / 2)
    else: x0, y0 = int(cx), int(cy)
    xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + w), min(H, y0 + h)
    if xb <= xa or yb <= ya: return base
    src = rgba[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    a = src[..., 3:4] / 255.0 * alpha
    reg = base[ya:yb, xa:xb].astype(np.float32)
    base[ya:yb, xa:xb] = (reg * (1 - a) + src[..., :3] * a).astype(np.uint8)
    return base

def canvas(color=DEEP): return np.full((H, W, 3), color, np.uint8)

def rgba_layer(): return Image.new('RGBA', (W, H), (0, 0, 0, 0))

def comp_layer(base, layer, alpha=1.0):
    return overlay(base, np.array(layer), 0, 0, alpha, anchor='tl')

def darken(img, k): return (img.astype(np.float32) * k).astype(np.uint8)

def mix(a, b, k):
    if k <= 0: return a
    if k >= 1: return b
    return (a.astype(np.float32) * (1 - k) + b.astype(np.float32) * k).astype(np.uint8)

# --------------------------------------------------------- etalonaje de fotos
def grade(arr, red_keep=True, dark=0.82):
    a = arr.astype(np.float32) / 255
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    redmask = np.clip((r - np.maximum(g, b) - 0.12) * 4, 0, 1) if red_keep else 0
    gray = lum[..., None]
    cool = gray * np.array([0.78, 0.92, 1.12], np.float32)
    out = cool * 0.85 + a * 0.15
    if red_keep:
        redc = np.stack([np.clip(lum * 1.6 + 0.15, 0, 1), lum * 0.18, lum * 0.22], -1)
        out = out * (1 - redmask[..., None]) + redc * redmask[..., None]
    out = np.clip(out, 0, 1) ** 1.35 * dark
    shadow = np.array([0.02, 0.04, 0.09], np.float32)
    out = out + shadow * (1 - np.clip(lum, 0, 1))[..., None] * 0.9
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)

@functools.lru_cache(None)
def photo(name, **kw):
    im = Image.open(os.path.join(IMG, name)).convert('RGB')
    w, h = im.size; s = max(W / w, H / h) * 1.45  # margen para zoom
    if s < 1: im = im.resize((int(w * s), int(h * s)), Image.LANCZOS)
    return grade(np.array(im), **kw)

def kb(arr, t, z0=1.0, z1=1.12, c0=(0.5, 0.5), c1=(0.5, 0.5), fit='cover', bg=DEEP):
    """Movimiento de cámara lento (Ken Burns). t en 0..1."""
    ih, iw = arr.shape[:2]; e = ease(t)
    z = z0 + (z1 - z0) * e; cx = c0[0] + (c1[0] - c0[0]) * e; cy = c0[1] + (c1[1] - c0[1]) * e
    base = max(W / iw, H / ih) if fit == 'cover' else min(W / iw, H / ih)
    s = base * z
    # mantener el encuadre dentro de la imagen (cover)
    if fit == 'cover':
        hw, hh = W / (2 * s), H / (2 * s)
        px = np.clip(cx * iw, hw, iw - hw); py = np.clip(cy * ih, hh, ih - hh)
    else:
        px, py = cx * iw, cy * ih
    M = np.float32([[s, 0, W / 2 - px * s], [0, s, H / 2 - py * s]])
    return cv2.warpAffine(arr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=bg)

def red_tint(img, k):
    f = img.astype(np.float32)
    lum = f @ np.array([0.3, 0.59, 0.11], np.float32)
    red = np.stack([lum * 1.25 + 20, lum * 0.15, lum * 0.18], -1)
    return np.clip(f * (1 - k) + red * k, 0, 255).astype(np.uint8)

# --------------------------------------------------------- elementos gráficos
def stamp(base, txt, t, cx, cy, size=120, angle=-12, color=RED, sub=None):
    """Sello rojo que cae con golpe. t = tiempo desde que aparece."""
    if t < 0: return base
    f = font('Anton', size)
    bb = f.getbbox(txt); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = int(size * 0.35)
    im = Image.new('RGBA', (tw + pad * 2 + 40, th + pad * 2 + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    bw = max(6, size // 14)
    d.rounded_rectangle([20, 20, im.width - 20, im.height - 20], radius=size // 8, outline=color + (255,), width=bw)
    d.rounded_rectangle([20 + bw * 2, 20 + bw * 2, im.width - 20 - bw * 2, im.height - 20 - bw * 2], radius=size // 10,
                        outline=color + (255,), width=max(2, bw // 3))
    d.text((20 + pad - bb[0], 20 + pad - bb[1]), txt, font=f, fill=color + (255,))
    # textura gastada del sello
    a = np.array(im); rng = np.random.default_rng(len(txt))
    holes = rng.random(a.shape[:2]) > 0.975
    holes = cv2.dilate(holes.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    a[..., 3] = np.where(holes, a[..., 3] * 0.25, a[..., 3]).astype(np.uint8)
    im = Image.fromarray(a).rotate(angle, expand=True, resample=Image.BICUBIC)
    k = eout(t / 0.18); sc = 1.9 - 0.9 * k
    shake = (1 - lin(t, 0, 0.35)) * 10
    rng = hrand('st', int(t * 30))
    return overlay(base, np.array(im), cx + rng.uniform(-shake, shake), cy + rng.uniform(-shake, shake),
                   alpha=min(1, t / 0.08), scale=sc)

def lower_third(base, t, title, subtitle, y=1480, red_word=None):
    """Rótulo periodístico: barra roja + título + subtítulo."""
    if t < 0: return base
    k = eout(t / 0.45)
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    x0 = 70
    bar_w = int(940 * k)
    d.rectangle([x0, y - 70, x0 + bar_w, y + 78], fill=(5, 9, 22, 215))
    d.rectangle([x0, y - 70, x0 + 12, y + 78], fill=RED + (255,))
    base = comp_layer(base, lay)
    if k > 0.4:
        a = lin(t, 0.18, 0.5)
        tr = text_rgba(title, 'Oswald-700', 62, WHITE)
        base = overlay(base, tr, x0 + 40 - (1 - a) * 30, y - 28, alpha=a, anchor='l')
        sr = text_rgba(subtitle, 'Oswald-300', 40, COOL)
        base = overlay(base, sr, x0 + 42 - (1 - a) * 30, y + 38, alpha=lin(t, 0.3, 0.6), anchor='l')
    return base

def big_label(base, t, txt, cy=1450, size=150, color=WHITE, glow=True, fname='Bebas'):
    if t < 0: return base
    a = min(1, t / 0.12); sc = 1.25 - 0.25 * eout(t / 0.2)
    if glow:
        g = text_rgba(txt, fname, size, RED)
        gb = cv2.GaussianBlur(g, (0, 0), 18)
        base = overlay(base, gb, W / 2, cy, alpha=a * 0.7, scale=sc)
    return overlay(base, text_rgba(txt, fname, size, color, stroke=3, sfill=(0, 0, 0)), W / 2, cy, alpha=a, scale=sc)

def card(base, t, lines, cy=1380, w=900, accent=RED):
    """Tarjeta con fondo oscuro; lines = [(texto, fuente, tamaño, color)]."""
    if t < 0: return base
    k = eout(t / 0.35)
    hs = [s + 26 for _, _, s, _ in lines]; hh = sum(hs) + 60
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    x0 = (W - w) // 2; y0 = int(cy - hh / 2)
    sh = int(hh * k)
    d.rectangle([x0, y0 + (hh - sh) // 2, x0 + w, y0 + (hh + sh) // 2], fill=(4, 8, 20, 225), outline=accent + (255,), width=4)
    base = comp_layer(base, lay)
    y = y0 + 30
    for i, ((txt, fn, sz, col), hgt) in enumerate(zip(lines, hs)):
        a = lin(t, 0.2 + i * 0.12, 0.45 + i * 0.12)
        base = overlay(base, text_rgba(txt, fn, sz, col), W / 2, y + hgt / 2, alpha=a)
        y += hgt
    return base

@functools.lru_cache(None)
def emoji(cp, size):
    im = Image.open(os.path.join(FONTS, f'emo_{cp}.png')).convert('RGBA').resize((size, size), Image.LANCZOS)
    return np.array(im)

def person_icon(size, color=(235, 240, 250)):
    im = Image.new('RGBA', (size, int(size * 1.9)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    r = size * 0.24
    d.ellipse([size / 2 - r, 0, size / 2 + r, 2 * r], fill=color + (255,))
    d.rounded_rectangle([size * 0.14, 2 * r + size * 0.08, size * 0.86, size * 1.9], radius=int(size * 0.3), fill=color + (255,))
    return np.array(im)

def eye_icon(size, color=RED):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    w = size; h = size * 0.55; cy = size / 2
    pts_top = [(w * x / 40, cy - h / 2 * math.sin(math.pi * x / 40)) for x in range(41)]
    pts_bot = [(w * x / 40, cy + h / 2 * math.sin(math.pi * x / 40)) for x in range(40, -1, -1)]
    d.polygon(pts_top + pts_bot, fill=(255, 255, 255, 235))
    d.ellipse([w / 2 - h * 0.42, cy - h * 0.42, w / 2 + h * 0.42, cy + h * 0.42], fill=color + (255,))
    d.ellipse([w / 2 - h * 0.17, cy - h * 0.17, w / 2 + h * 0.17, cy + h * 0.17], fill=(0, 0, 0, 255))
    return np.array(im)

# -------------------------------------------------------------- mapas
COUNTRIES = json.load(open(os.path.join(WORK, 'countries.json')))
LATAM = ['Mexico', 'Guatemala', 'Belize', 'Honduras', 'El Salvador', 'Nicaragua', 'Costa Rica', 'Panama', 'Colombia',
         'Venezuela', 'Ecuador', 'Peru', 'Brazil', 'Bolivia', 'Paraguay', 'Chile', 'Argentina', 'Uruguay', 'Guyana',
         'Suriname', 'Cuba', 'Dominican Rep.', 'Haiti', 'Puerto Rico', 'Jamaica', 'Bahamas', 'Trinidad and Tobago',
         'United States of America', 'Fr. S. Antarctic Lands', 'Falkland Is.']

def proj_latam(lon, lat):  # Latinoamérica a pantalla completa
    return (lon + 118) * 11.9 + 45, (34 - lat) * 12.2 + 400

def proj_world(lon, lat, cx_lon=40, s=5.4):
    y = (75 - lat) * s * 1.08 + 620
    return (lon - cx_lon) * s + W / 2, y

def draw_countries(d, proj, names=None, fill=(12, 22, 48, 255), outline=(60, 90, 140, 255), width=2, highlight=None):
    highlight = highlight or {}
    for name, polys in COUNTRIES.items():
        if names is not None and name not in names: continue
        for ring in polys:
            pts = [proj(x, y) for x, y in ring]
            if len(pts) < 3: continue
            xs = [p[0] for p in pts]
            if max(xs) < -50 or min(xs) > W + 50: continue
            col = highlight.get(name, fill)
            d.polygon(pts, fill=col, outline=outline)
            if width > 1: d.line(pts + [pts[0]], fill=outline, width=width)

@functools.lru_cache(8)
def latam_map(hl_key=()):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    hl = {n: RED + (255,) for n in hl_key}
    draw_countries(d, proj_latam, LATAM, highlight=hl)
    return np.array(lay)

def centroid(name, proj):
    ring = max(COUNTRIES[name], key=len); pts = np.array([proj(x, y) for x, y in ring])
    return pts.mean(0)

def map_bg():
    b = canvas((4, 8, 20))
    # retícula tenue
    b[::60, :] = (10, 20, 42); b[:, ::60] = (10, 20, 42)
    return b

# ------------------------------------------------------------- red de nodos
_r = np.random.default_rng(11)
NODES = []
while len(NODES) < 26:
    p = (_r.uniform(120, 960), _r.uniform(560, 1260))
    if all(math.hypot(p[0] - q[0], p[1] - q[1]) > 120 for q in NODES): NODES.append(p)
EDGES = [(i, j) for i in range(len(NODES)) for j in range(i + 1, len(NODES))
         if math.hypot(NODES[i][0] - NODES[j][0], NODES[i][1] - NODES[j][1]) < 230]
DIE = {i: 10.9 + k * (2.75 / len(NODES)) for k, i in enumerate(_r.permutation(len(NODES)))}

def network(base, t):
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    appear = lin(t, 8.2, 9.2)
    def state(i):
        dt = t - DIE[i]
        if dt < 0: return 1.0, False
        if dt < 0.25: return (1.0 if int(dt * 30) % 2 else 0.3), True
        return 0.0, True
    for i, j in EDGES:
        si, _ = state(i); sj, _ = state(j); a = min(si, sj) * appear
        if a > 0: d.line([NODES[i], NODES[j]], fill=(120, 170, 255, int(140 * a)), width=2)
        elif appear: d.line([NODES[i], NODES[j]], fill=(120, 30, 40, 50), width=1)
    pulse = 0.5 + 0.5 * math.sin(t * 6)
    for i, (x, y) in enumerate(NODES):
        s, dying = state(i)
        if appear * s > 0:
            col = RED if dying else (150, 200, 255)
            r = 9 + 3 * pulse
            d.ellipse([x - r * 2.2, y - r * 2.2, x + r * 2.2, y + r * 2.2], fill=col + (int(40 * appear * s),))
            d.ellipse([x - r, y - r, x + r, y + r], fill=col + (int(255 * appear * s),))
        elif appear:
            d.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(140, 30, 40, 160), width=2)
    return comp_layer(base, lay)

# ----------------------------------------------------------------- ESCENAS
CODE = '> nsanet.core --sync node[07]  ██ status: OK'

def scene1(t):
    b = canvas((0, 0, 0))
    # línea de código congelada -> glitch -> se apaga
    if t < 1.0:
        txt = CODE + ('_' if t < 0.3 and int(t * 6) % 2 == 0 else '')
        im = text_rgba(txt, 'JetBrainsMono-Bold' if os.path.exists(os.path.join(FONTS, 'JetBrainsMono-Bold.ttf')) else 'Oswald-300', 34, (120, 170, 230))
        if t < 0.8:
            b = overlay(b, im, W / 2, H / 2)
        else:  # apagado tipo CRT: se aplasta en una línea
            k = lin(t, 0.8, 0.98)
            sq = cv2.resize(im, (int(im.shape[1] * (1 - 0.3 * k)), max(1, int(im.shape[0] * (1 - k)))))
            b = overlay(b, sq, W / 2, H / 2, alpha=1 - k * 0.5)
            if k > 0.6: cv2.line(b, (int(W / 2 - 300 * (1 - k) * 3), H // 2), (int(W / 2 + 300 * (1 - k) * 3), H // 2), (200, 220, 255), 2)
    # fecha a máquina de escribir
    a, e = TYPE_T
    if t >= a:
        full = '17 NOV 2026'; n = int(clamp((t - a) / (e - a)) * len(full) + 0.999)
        txt = full[:n]
        flick = 1.0
        if 3.22 <= t < 3.6: flick = 0.2 if int(t * 40) % 3 else 1.0
        elif t >= 3.6: flick = 0.55 - 0.35 * lin(t, 3.6, 6.0)
        if t >= 6.0: flick = 0
        if txt and flick > 0:
            cur = '_' if int(t * 3) % 2 == 0 and t < 3.2 else ' '
            im = text_rgba(txt + cur, 'SpecialElite', 120, WHITE)
            b = overlay(b, im, W / 2, H / 2 - 40, alpha=flick)
            if t > 2.3:
                b = overlay(b, text_rgba('ARCHIVO CLASIFICADO', 'Oswald-300', 34, (130, 140, 160), spacing=10),
                            W / 2, H / 2 + 70, alpha=flick * lin(t, 2.3, 2.8))
    # "NSA" rojo parpadeando como señal perdida
    if t >= 6.9:
        dt = t - 6.9
        rng = hrand('nsa', int(t * 30))
        on = rng.random() > (0.25 if dt > 0.3 else 0.0)
        if on:
            im = text_rgba('NSA', 'Anton', 330, RED)
            gl = cv2.GaussianBlur(im, (0, 0), 25)
            jx = rng.normal(0, 8); sc = 1.0 + 0.04 * math.exp(-dt * 4)
            b = overlay(b, gl, W / 2 + jx, H / 2 - 20, alpha=0.8, scale=sc)
            b = overlay(b, im, W / 2 + jx, H / 2 - 20, alpha=0.75 + 0.25 * rng.random(), scale=sc)
            # líneas de escaneo
            b[::4] = (b[::4] * 0.55).astype(np.uint8)
        sig = text_rgba('SEÑAL PERDIDA', 'Oswald-500', 38, (200, 60, 70), spacing=12)
        b = overlay(b, sig, W / 2, H / 2 + 230, alpha=0.8 if int(t * 4) % 2 else 0.3)
    return b

def scene2(t):  # 8.14 – 15.64 sede NSA
    b = kb(photo('01_sede_NSA.jpg'), lin(t, 8.14, 15.7), 1.0, 1.18, (0.45, 0.55), (0.5, 0.52))
    b = darken(b, 0.85 - 0.25 * lin(t, 11, 14.2))
    b = network(b, t)
    b = lower_third(b, t - 8.35, 'NSA', 'Agencia de Seguridad Nacional de EE. UU.', y=1460)
    if t >= 14.30:
        b = darken(b, 1 - 0.35 * lin(t, 14.3, 14.6))
        b = stamp(b, 'NSA NET: OFFLINE', t - 14.30, W / 2, 900, size=92, angle=-9)
    return b

def scene3(t):  # 15.64 – 18.98 servidores
    lt = t - 15.64
    b = kb(photo('07_servidores.jpg'), lin(t, 15.64, 19), 1.05, 1.15, (0.5, 0.45), (0.5, 0.5))
    rng = hrand('srv', int(t * 15))
    off = lin(t, 15.8, 18.6)
    flick = 1.0 if rng.random() > 0.2 + 0.5 * off else 0.45
    b = darken(b, (1 - 0.6 * off) * flick)
    # LEDs que parpadean y se apagan
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    r2 = np.random.default_rng(3)
    for k in range(70):
        x = r2.uniform(60, 1020); y = r2.uniform(300, 1700); die = r2.uniform(15.9, 18.6)
        if t < die and hrand('led', k, int(t * 12)).random() > 0.35:
            col = (255, 40, 50) if k % 3 == 0 else (90, 160, 255)
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=col + (230,)); d.ellipse([x - 14, y - 14, x + 14, y + 14], fill=col + (50,))
    b = comp_layer(b, lay)
    # puerta y personas entrando por turnos
    door_x, door_y = W / 2 + 150, 1240
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    d.rectangle([door_x - 70, door_y - 170, door_x + 70, door_y + 150], fill=(160, 190, 240, 70), outline=(190, 215, 255, 255), width=5)
    base = comp_layer(b, lay)
    icon = person_icon(64)
    for k in range(5):
        st = 16.0 + k * 0.62
        p = (t - st) / 0.9
        if p < -0.05: x = door_x - 260 - k * 95 + 0  # en fila
        else: x = door_x - 260 + eout(p) * 260
        x = (door_x - 260 - (k - max(0, int((t - 16.0) / 0.62))) * 95) if p < 0 else x
        a = 1.0 if p < 0.85 else max(0, 1 - (p - 0.85) / 0.15)
        if a > 0: base = overlay(base, icon, x, door_y + 30, alpha=a * 0.9)
    base = overlay(base, text_rgba('ENTRADA POR TURNOS', 'Bebas', 120, WHITE, stroke=3), W / 2, 1520,
                   alpha=lin(t, 16.9, 17.1))
    cnt = clamp(int((t - 16.0) / 0.62) + 1, 0, 5) if t > 16 else 0
    if cnt: base = overlay(base, text_rgba(f'TURNO {int(cnt):02d}', 'JetBrainsMono-Bold' if False else 'Oswald-500', 46, RED, spacing=6), W / 2, 1620,
                           alpha=lin(t, 16.9, 17.1))
    return base

def scene4(t):  # 18.98 – 29.12 Snowden + mapa
    if t < 22.84:
        b = kb(photo('02_Edward_Snowden.jpg'), lin(t, 18.98, 23), 1.0, 1.15, (0.5, 0.35), (0.48, 0.3))
        b = red_tint(b, 0.25)
        # escaneo rojo
        y = int(((t - 18.98) * 700) % (H + 300)) - 150
        lay = rgba_layer(); d = ImageDraw.Draw(lay)
        for k in range(60): d.line([(0, y - k * 3), (W, y - k * 3)], fill=(255, 30, 40, int(70 * (1 - k / 60))), width=3)
        d.line([(0, y), (W, y)], fill=(255, 60, 70, 255), width=4)
        for gy in range(0, H, 6): d.line([(0, gy), (W, gy)], fill=(0, 0, 0, 40))
        # recuadro de identificación
        a = lin(t, 19.6, 20.0); cx, cy, s = 540, 640, 230
        if a:
            col = RED + (int(255 * a),)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    d.line([(cx + sx * s, cy + sy * s), (cx + sx * (s - 60), cy + sy * s)], fill=col, width=6)
                    d.line([(cx + sx * s, cy + sy * s), (cx + sx * s, cy + sy * (s - 60))], fill=col, width=6)
        b = comp_layer(b, lay)
        if t > 20.2:
            m = 'IDENTIFICADO' if t > 21.5 else ('ANALIZANDO' + '.' * (int(t * 4) % 4))
            b = overlay(b, text_rgba(m, 'Oswald-500', 40, RED, spacing=8), 540, 920, alpha=lin(t, 20.2, 20.4))
        b = lower_third(b, t - 21.54, 'Edward Snowden', 'Exanalista de inteligencia', y=1470)
        return b
    # mapa de Latinoamérica
    b = map_bg()
    hl = []
    if t >= 25.14: hl.append('Brazil')
    if t >= 26.28: hl.append('Mexico')
    m = latam_map(tuple(hl))
    zoom = 1.0 + 0.05 * lin(t, 22.84, 29.2)
    b = overlay(b, m, W / 2, H / 2 + 20, alpha=lin(t, 22.84, 23.4), scale=zoom)
    for name, t0 in (('Brazil', 25.14), ('Mexico', 26.28)):
        if t >= t0:
            cx, cy = centroid(name, proj_latam)
            cx = W / 2 + (cx - W / 2) * zoom; cy = H / 2 + 20 + (cy - H / 2) * zoom
            if name == 'Brazil': cx, cy = cx + 40, cy - 80
            if name == 'Mexico': cx, cy = cx + 20, cy - 10
            dt = t - t0
            # pulso
            lay = rgba_layer(); d = ImageDraw.Draw(lay)
            r = 40 + (dt * 220) % 200
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=RED + (int(200 * (1 - ((dt * 220) % 200) / 200)),), width=4)
            b = comp_layer(b, lay)
            b = overlay(b, eye_icon(130), cx, cy, alpha=min(1, dt / 0.15), scale=0.6 + 0.4 * back(dt / 0.3))
            lbl = 'BRASIL' if name == 'Brazil' else 'MÉXICO'
            b = overlay(b, text_rgba(lbl, 'Oswald-700', 50, WHITE, stroke=2), cx, cy + 95, alpha=min(1, dt / 0.2))
    b = card(b, t - 26.64, [('ESPIONAJE A PRESIDENTES', 'Bebas', 92, WHITE),
                            ('Documentos de Snowden', 'Oswald-300', 42, COOL)], cy=1560)
    return b

# --- montaje de caídas
TL_DAYS = [(30.66, 0, 'OUTLOOK'), (31.90, 1, 'VUELOS'), (34.26, 2, 'UNITED'), (36.68, 4, 'BANCOS'), (39.45, 5, 'NSA')]

def timeline_bar(b, t):
    y = 560; x0, x1 = 110, 970
    a = lin(t, 29.12, 29.5)
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    d.rectangle([60, y - 75, 1020, y + 85], fill=(3, 6, 15, int(200 * a)))
    prog = lin(t, 29.2, 40.0)
    d.line([(x0, y), (x1, y)], fill=(90, 100, 120, int(255 * a)), width=4)
    d.line([(x0, y), (x0 + (x1 - x0) * prog, y)], fill=RED + (int(255 * a),), width=8)
    b = comp_layer(b, lay)
    for k in range(6):
        x = x0 + (x1 - x0) * k / 5
        b = overlay(b, text_rgba(f'DÍA {k + 1}', 'Oswald-500', 28, (170, 180, 200)), x, y - 42, alpha=a)
        lay = rgba_layer(); d = ImageDraw.Draw(lay)
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(200, 205, 215, int(255 * a)))
        b = comp_layer(b, lay)
    for t0, k, name in TL_DAYS:
        if t >= t0:
            x = x0 + (x1 - x0) * k / 5; dt = t - t0
            b = overlay(b, emoji('274c', 64), x, y, scale=1.6 - 0.6 * eout(dt / 0.2), alpha=min(1, dt / 0.08))
            b = overlay(b, text_rgba(name, 'Oswald-500', 24, RED), x, y + 50, alpha=min(1, dt / 0.2))
    return b

def phone(t):
    lay = Image.new('RGBA', (560, 1060), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, 559, 1059], radius=70, fill=(12, 14, 20, 255), outline=(70, 80, 95, 255), width=6)
    d.rounded_rectangle([24, 24, 535, 1035], radius=52, fill=(16, 22, 40, 255))
    d.rounded_rectangle([210, 44, 350, 74], radius=15, fill=(5, 6, 10, 255))
    d.ellipse([200, 300, 360, 460], outline=RED + (255,), width=10)
    d.line([(280, 335), (280, 400)], fill=RED + (255,), width=12); d.ellipse([272, 420, 288, 436], fill=RED + (255,))
    f1 = font('Oswald-700', 52); f2 = font('Oswald-300', 36)
    for txt, f, y, col in (('Error', f1, 520, WHITE), ('Please try again', f2, 600, (200, 205, 220)), ('later', f2, 645, (200, 205, 220))):
        w = d.textlength(txt, font=f); d.text((280 - w / 2, y), txt, font=f, fill=col)
    d.rounded_rectangle([90, 760, 470, 840], radius=40, fill=(40, 50, 75, 255))
    w = d.textlength('Retry', font=f2); d.text((280 - w / 2, 775), 'Retry', font=f2, fill=(160, 170, 190))
    # spinner
    ang = (t * 400) % 360
    d.arc([250, 900, 310, 960], ang, ang + 270, fill=(150, 160, 180, 255), width=6)
    return np.array(lay)

def scene5(t):  # 29.12 – 41.08
    if t < 31.74:  # Outlook
        b = kb(photo('06_correo_laptop.jpg'), lin(t, 29.12, 31.8), 1.0, 1.15, (0.5, 0.5), (0.55, 0.45))
        if t >= 30.56:
            logo = np.array(Image.open(os.path.join(IMG, '03_logo_Outlook.jpg')).convert('RGBA'))
            logo[..., :3] = (logo[..., :3].astype(np.float32) * 0.85).astype(np.uint8)
            dt = t - 30.56
            sh = hrand('ol', int(t * 30)).normal(0, 6 if dt > 0.4 else 0)
            b = overlay(b, logo, W / 2 + sh, 1000, scale=1.15, alpha=min(1, dt / 0.1))
            if dt > 0.35 and int(t * 10) % 3 == 0: b = red_tint(b, 0.6)
        b = big_label(b, t - 30.66, 'OUTLOOK', 1350)
    elif t < 34.02:  # vuelos
        if t < 32.95:
            b = kb(photo('09_tablero_vuelos.jpg'), lin(t, 31.74, 33), 1.1, 1.25, (0.45, 0.4), (0.5, 0.45))
            lay = rgba_layer(); d = ImageDraw.Draw(lay)
            for k in range(7):
                tk = 31.85 + k * 0.12
                if t > tk:
                    y = 880 + k * 92
                    d.rectangle([600, y, 960, y + 66], fill=(160, 10, 20, 235))
                    f = font('Oswald-700', 48); d.text((618, y + 2), 'CANCELED', font=f, fill=WHITE)
            b = comp_layer(b, lay)
        else:
            b = kb(photo('08_aeropuerto_filas.jpg'), lin(t, 32.95, 34.1), 1.0, 1.1, (0.35, 0.5), (0.6, 0.5))
        b = big_label(b, t - 31.90, 'VUELOS DETENIDOS', 1420, size=130)
    elif t < 35.56:
        b = kb(photo('11_avion_pista.jpg'), lin(t, 34.02, 35.6), 1.0, 1.12, (0.5, 0.55), (0.5, 0.5))
        b = big_label(b, t - 34.26, 'UNITED AIRLINES', 1420, size=130)
    elif t < 39.45:
        if t < 37.0:
            b = kb(photo('05_Chase.jpg'), lin(t, 35.56, 37.1), 1.0, 1.12, (0.5, 0.35), (0.5, 0.42))
        elif t < 37.95:
            b = kb(photo('10_Bank_of_America.jpg'), lin(t, 37.0, 38), 1.0, 1.1, (0.48, 0.5), (0.52, 0.5))
        else:
            b = cv2.GaussianBlur(kb(photo('10_Bank_of_America.jpg'), 1, 1.1, 1.1, (0.52, 0.5), (0.52, 0.5)), (0, 0), 18)
            b = darken(b, 0.6)
            dt = t - 37.95
            b = overlay(b, phone(t), W / 2, 1060 + 80 * (1 - eout(dt / 0.3)), alpha=min(1, dt / 0.15), scale=0.95)
        names = [n for n, t0 in (('CHASE', 36.68), ('BANK OF AMERICA', 37.06), ('ZELLE', 37.98)) if t >= t0]
        if names:
            y0 = 1420 if t < 37.95 else 1700
            b = big_label(b, 0.5, ' · '.join(names), y0, size=96 if len(names) < 3 else 82)
    elif t < 40.1:
        b = kb(photo('01_sede_NSA.jpg'), lin(t, 39.45, 40.1), 1.15, 1.25)
        b = red_tint(b, 0.9)
        b = big_label(b, t - 39.45, 'NSA', 1400, size=220)
    else:
        b = canvas((4, 4, 8))
        dt = t - 40.1
        n = min(5, 1 + int(dt / 0.06))
        b = overlay(b, text_rgba(str(n), 'Anton', 420, RED), W / 2, 1000, scale=1.15 - 0.15 * eout(dt / 0.3))
        b = overlay(b, text_rgba('CAÍDAS EN 6 DÍAS', 'Bebas', 120, WHITE, spacing=4), W / 2, 1280, alpha=lin(t, 40.15, 40.3))
    if t < 40.1: b = timeline_bar(b, t)
    return b

def scene6(t):  # 41.08 – 45.96
    b = kb(photo('14_hombre_frustrado.jpg'), lin(t, 41.08, 46), 1.0, 1.12, (0.45, 0.4), (0.42, 0.38))
    b = darken(b, 0.85)
    b = big_label(b, t - 41.30, '¿CIBERATAQUE?', 1080, size=150, glow=False)
    if t >= 42.94:
        dt = t - 42.94
        b = overlay(b, emoji('274c', 110), 300, 1270, scale=1.5 - 0.5 * eout(dt / 0.2), alpha=min(1, dt / 0.1))
        b = overlay(b, text_rgba('SIN PRUEBAS', 'Bebas', 130, RED, stroke=3), 610, 1275, alpha=min(1, dt / 0.1),
                    scale=1.2 - 0.2 * eout(dt / 0.2))
    b = overlay(b, text_rgba('Versión oficial: “errores técnicos”', 'Oswald-300', 44, COOL), W / 2, 1420, alpha=lin(t, 44.3, 44.6))
    return b

# --- portada: cámara por fotogramas clave (centro en px de la portada, zoom en px pantalla / px portada)
COVER_KEYS = [(45.96, 627, 627, 0.86), (47.1, 627, 627, 0.90), (51.1, 627, 615, 1.15), (52.0, 628, 600, 2.6),
              (58.45, 628, 600, 3.05), (59.1, 205, 760, 2.5), (60.25, 200, 755, 2.6), (60.75, 925, 225, 2.7),
              (61.1, 930, 220, 2.85), (61.6, 170, 435, 2.9), (62.6, 170, 432, 3.1)]
COVER_KEYS2 = [(69.0, 900, 600, 1.4), (69.8, 1010, 585, 3.1), (70.6, 1010, 585, 3.3)]

@functools.lru_cache(None)
def cover():
    im = np.array(Image.open(os.path.join(IMG, '04_portada_Economist_2027.png')).convert('RGB')).astype(np.float32) / 255
    lum = im @ np.array([0.3, 0.59, 0.11], np.float32)
    r, g, b_ = im[..., 0], im[..., 1], im[..., 2]
    redm = np.clip((r - np.maximum(g, b_) - 0.15) * 4, 0, 1)[..., None]
    paper = np.array([0.20, 0.25, 0.36], np.float32); ink = np.array([0.01, 0.015, 0.03], np.float32)
    out = ink + (paper - ink) * lum[..., None]
    out = out * (1 - redm) + np.array([0.86, 0.1, 0.14], np.float32) * redm
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)

def cam(keys, t):
    if t <= keys[0][0]: return keys[0][1:]
    for (t0, *a), (t1, *b) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            e = ease((t - t0) / (t1 - t0)); return tuple(x + (y - x) * e for x, y in zip(a, b))
    return keys[-1][1:]

def cover_view(t, keys):
    cx, cy, z = cam(keys, t)
    M = np.float32([[z, 0, W / 2 - cx * z], [0, z, H / 2 - cy * z]])
    b = cv2.warpAffine(cover(), M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=DEEP)
    return b, (cx, cy, z)

def to_screen(px, py, c):
    cx, cy, z = c; return W / 2 + (px - cx) * z, H / 2 + (py - cy) * z

def brain_pulse(b, t, c):
    x, y = to_screen(628, 600, c)
    p = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 1.3)
    r = 80 * c[2]
    lay = np.zeros((H, W), np.float32)
    cv2.circle(lay, (int(x), int(y)), int(r), 1.0, -1)
    lay = cv2.GaussianBlur(lay, (0, 0), r * 0.35)
    f = b.astype(np.float32)
    k = (0.35 + 0.45 * p) * lay[..., None]
    lum = f @ np.array([0.3, 0.59, 0.11], np.float32)
    redglow = np.stack([np.clip(lum * 1.5 + 90, 0, 255), lum * 0.2, lum * 0.25], -1)
    return np.clip(f * (1 - k) + redglow * k, 0, 255).astype(np.uint8)

def tag(b, txt, x, y, a):
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    s = 90
    col = RED + (int(255 * a),)
    for sx in (-1, 1):
        for sy in (-1, 1):
            d.line([(x + sx * s, y + sy * s), (x + sx * (s - 30), y + sy * s)], fill=col, width=5)
            d.line([(x + sx * s, y + sy * s), (x + sx * s, y + sy * (s - 30))], fill=col, width=5)
    b = comp_layer(b, lay)
    return overlay(b, text_rgba(txt, 'Oswald-700', 48, WHITE, stroke=2), x, y + s + 40, alpha=a)

def world_map(t):
    b = map_bg()
    lon_c = 30 + 30 * ease(lin(t, 62.6, 66.5))
    proj = lambda lo, la: proj_world(lo, la, lon_c, 5.6)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    hot = {'Iran': (150, 20, 30, 255), 'China': (150, 20, 30, 255), 'Taiwan': (230, 30, 45, 255),
           'United States of America': (40, 50, 80, 255)}
    draw_countries(d, proj, None, fill=(14, 24, 50, 255), outline=(50, 75, 120, 255), width=1, highlight=hot)
    b = comp_layer(b, lay, lin(t, 62.6, 62.9))
    pts = {'usa': (-95, 38), 'iran': (53, 32), 'china': (105, 35), 'taiwan': (121, 23.7), 'israel': (35, 31.5),
           'russia': (60, 58)}
    links = [('iran', 'israel', 62.9), ('usa', 'iran', 63.1), ('china', 'taiwan', 63.4), ('usa', 'china', 63.8),
             ('russia', 'iran', 64.3), ('china', 'iran', 64.7)]
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    for a_, b_, t0 in links:
        k = ease(lin(t, t0, t0 + 0.8))
        if k <= 0: continue
        p0 = proj(*pts[a_]); p1 = proj(*pts[b_])
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 - abs(p1[0] - p0[0]) * 0.25
        seg = []
        for i in range(int(40 * k) + 1):
            u = i / 40
            seg.append(((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * mx + u * u * p1[0],
                        (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * my + u * u * p1[1]))
        if len(seg) > 1:
            fl = 0.6 + 0.4 * math.sin(t * 9 + t0)
            d.line(seg, fill=RED + (int(90 * fl),), width=14); d.line(seg, fill=(255, 80, 90, int(255 * fl)), width=4)
    for name, (lo, la) in pts.items():
        x, y = proj(lo, la); p = (t * 1.5) % 1
        d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=RED + (255,))
        d.ellipse([x - 10 - 40 * p, y - 10 - 40 * p, x + 10 + 40 * p, y + 10 + 40 * p], outline=RED + (int(200 * (1 - p)),), width=3)
    b = comp_layer(b, lay)
    for name, lbl in (('iran', 'IRÁN'), ('china', 'CHINA'), ('taiwan', 'TAIWÁN')):
        x, y = proj(*pts[name])
        b = overlay(b, text_rgba(lbl, 'Oswald-700', 34, WHITE, stroke=2), x, y + 40, alpha=lin(t, 63, 63.4))
    b = overlay(b, text_rgba('UN MUNDO TENSO', 'Bebas', 130, WHITE, stroke=3), W / 2, 1450, alpha=lin(t, 63.08, 63.3))
    return b

def scene7_8(t):  # 45.96 – 69.06
    if t < 62.6:
        b, c = cover_view(t, COVER_KEYS)
        if t > 51.0: b = brain_pulse(b, t, c) if t < 59.0 else b
        if 54.04 <= t < 58.6:
            b = card(b, t - 54.04, [('IA · RIESGOS · CIBERATAQUES', 'Bebas', 96, WHITE)], cy=1500)
        if t < 58.6:
            b = overlay(b, text_rgba('Fuente: The Economist, 16 nov 2026', 'Oswald-300', 36, COOL), 80, 1690,
                        alpha=lin(t, 48.2, 48.6), anchor='l')
        if 59.3 <= t < 60.3: b = tag(b, 'MISILES', *to_screen(190, 765, c), lin(t, 59.3, 59.5))
        if 60.75 <= t < 61.15: b = tag(b, 'IRÁN', *to_screen(925, 225, c), lin(t, 60.75, 60.85))
        if 61.6 <= t: b = tag(b, 'CHINA', *to_screen(165, 432, c), lin(t, 61.6, 61.75))
        return b
    if t < 66.75:
        return world_map(t)
    # computadoras oscuras como transición
    b = kb(photo('12_computadoras_oscuras.jpg'), lin(t, 66.75, 69.1), 1.15, 1.0)
    fl = 0.4 if hrand('pc', int(t * 20)).random() < 0.3 else 1.0
    b = darken(b, 0.8 * fl)
    return b

# --- escena 9
def oil_chart(b, t):
    b = map_bg()
    b = overlay(b, latam_map(()), W / 2, H / 2 + 120, alpha=0.75 * lin(t, 70.58, 70.9))
    # panel del gráfico
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = 90, 520, 990, 1020
    d.rectangle([x0, y0, x1, y1], fill=(3, 6, 15, 225), outline=(60, 80, 120, 255), width=3)
    for k in range(1, 5): d.line([(x0, y0 + k * 100), (x1, y0 + k * 100)], fill=(40, 55, 85, 255), width=1)
    k = ease(lin(t, 70.8, 73.8))
    rng = np.random.default_rng(5)
    n = 60; xs = np.linspace(x0 + 30, x1 - 30, n)
    ys = y1 - 60 - np.linspace(0, 360, n) ** 1.0 * (np.linspace(0, 1, n) ** 1.6) - rng.normal(0, 12, n)
    m = max(2, int(n * k))
    pts = list(zip(xs[:m], ys[:m]))
    d.polygon(pts + [(xs[m - 1], y1 - 20), (xs[0], y1 - 20)], fill=(200, 20, 35, 70))
    d.line(pts, fill=RED + (255,), width=8)
    d.ellipse([xs[m - 1] - 12, ys[m - 1] - 12, xs[m - 1] + 12, ys[m - 1] + 12], fill=WHITE + (255,))
    b = comp_layer(b, lay)
    b = overlay(b, text_rgba('PETRÓLEO', 'Bebas', 90, WHITE), x0 + 30, y0 + 60, anchor='l', alpha=lin(t, 70.6, 70.9))
    if t > 70.6:
        lay = rgba_layer(); d = ImageDraw.Draw(lay); ax = x0 + 330; ay = y0 + 60
        d.polygon([(ax, ay - 30), (ax - 28, ay + 22), (ax + 28, ay + 22)], fill=RED + (255,)); b = comp_layer(b, lay, lin(t, 70.6, 70.9))
    # iconos sobre el mapa
    icons = [('26fd', 72.12, -102, 22), ('26fd', 72.25, -74, 5), ('26fd', 72.38, -64, -22), ('1f6d2', 72.58, -48, -12),
             ('1f6d2', 72.72, -77, -10), ('1f6d2', 72.86, -64, -36), ('26fd', 73.0, -56, -28), ('1f6d2', 73.1, -90, 15)]
    for cp, t0, lo, la in icons:
        if t >= t0:
            x, y = proj_latam(lo, la); y = y + 120 + (y - H / 2) * 0; dt = t - t0
            b = overlay(b, emoji(cp, 100), x, y, scale=back(dt / 0.25), alpha=min(1, dt / 0.08))
    if t >= 73.6:
        b = big_label(b, t - 73.6, 'LATINOAMÉRICA', 1720, size=110)
    return b

def scene9(t):  # 69.06 – 80.62
    if t < 70.58:
        b, c = cover_view(t, COVER_KEYS2)
        return tag(b, 'OLEODUCTO', *to_screen(1010, 580, c), lin(t, 69.7, 69.9))
    if t < 74.56:
        return oil_chart(None, t)
    if t < 77.4:
        b = kb(photo('13_dolares.jpg'), lin(t, 74.56, 77.5), 1.0, 1.15, (0.5, 0.45), (0.5, 0.52))
    else:
        b = kb(photo('15_viajera_esperando.jpg'), lin(t, 77.4, 80.7), 1.08, 1.0, (0.62, 0.5), (0.55, 0.5))
    b = darken(b, 0.9)
    if t >= 75.44:
        dt = t - 75.44
        b = card(b, dt, [('NAVIDAD', 'Bebas', 120, WHITE), ('VUELOS Y BANCOS', 'Bebas', 96, RED)], cy=1450, w=820)
        b = overlay(b, emoji('1f384', 120), W / 2 + 270, 1385, alpha=lin(dt, 0.3, 0.5), scale=back(lin(dt, 0.3, 0.6)))
    return b

def scene10(t):  # 80.62 – 85.32
    b = canvas((5, 9, 22))
    b[::60, :] = (9, 16, 34)
    lay = rgba_layer(); d = ImageDraw.Draw(lay)
    a = lin(t, 80.62, 80.9)
    d.rectangle([110, 760, 970, 1130], fill=(10, 18, 40, int(255 * a)), outline=(80, 100, 140, int(255 * a)), width=4)
    b = comp_layer(b, lay)
    b = overlay(b, text_rgba('ALERTA VIRAL', 'Oswald-500', 38, COOL, spacing=10), W / 2, 830, alpha=a)
    b = overlay(b, text_rgba('APAGÓN 17 NOV', 'Anton', 140, WHITE), W / 2, 960, alpha=a)
    if t >= 83.22:
        b = darken(b, 1 - 0.45 * lin(t, 83.22, 83.4))
        b = stamp(b, 'FALSO', t - 83.22, W / 2, 960, size=240, angle=-14)
    b = overlay(b, text_rgba('Fue una prueba de alerta (FEMA)', 'Oswald-500', 54, WHITE), W / 2, 1290,
                alpha=lin(t, 83.9, 84.2))
    return b

def scene11(t):  # 85.32 – 88.35
    b = canvas((0, 0, 0))
    sc = 1.15 - 0.15 * eout((t - 85.32) / 0.3)
    b = overlay(b, cv2.GaussianBlur(text_rgba('¿QUÉ ESTÁ', 'Anton', 165, RED), (0, 0), 20), W / 2, 760, alpha=0.6 * lin(t, 85.32, 85.5), scale=sc)
    b = overlay(b, text_rgba('¿QUÉ ESTÁ', 'Anton', 165, WHITE), W / 2, 760, alpha=lin(t, 85.32, 85.45), scale=sc)
    b = overlay(b, text_rgba('PASANDO?', 'Anton', 190, RED), W / 2, 960, alpha=lin(t, 85.4, 85.55), scale=sc)
    opts = [('A', 'Coincidencia'), ('B', 'Exceso de tecnología'), ('C', 'Algo más')]
    for i, (l, txt) in enumerate(opts):
        t0 = 86.38 + i * 0.22
        if t < t0: continue
        dt = t - t0; y = 1210 + i * 135
        lay = rgba_layer(); d = ImageDraw.Draw(lay)
        w = int(820 * eout(dt / 0.3))
        d.rounded_rectangle([130, y - 52, 130 + max(w, 60), y + 52], radius=52, fill=(12, 22, 48, 255), outline=(90, 110, 150, 255), width=3)
        d.ellipse([140, y - 42, 224, y + 42], fill=RED + (255,))
        b = comp_layer(b, lay)
        b = overlay(b, text_rgba(l, 'Oswald-700', 50, WHITE), 182, y)
        b = overlay(b, text_rgba(txt, 'Oswald-500', 50, WHITE), 260, y, anchor='l', alpha=lin(dt, 0.15, 0.3))
    b = overlay(b, text_rgba('ENCUESTA · COMENTA TU RESPUESTA', 'Oswald-300', 32, COOL, spacing=4), W / 2, 1640, alpha=lin(t, 86.9, 87.2))
    return b

_cierre = None
def cierre(t):
    global _cierre
    if _cierre is None:
        cap = cv2.VideoCapture(os.path.join(WORK, '..', 'assets', 'cierre.mp4')); fr = []
        while True:
            ok, f = cap.read()
            if not ok: break
            fr.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        _cierre = fr
    # los 2 s de animación se aceleran para caber en el final
    lt = (t - CIERRE_T) * 1.55
    i = min(len(_cierre) - 1, int(lt * 30))
    return _cierre[i].copy()

def scene(t):
    if t < 8.14: return scene1(t)
    if t < 15.64: return scene2(t)
    if t < 18.98: return scene3(t)
    if t < 29.12: return scene4(t)
    if t < 41.08: return scene5(t)
    if t < 45.96: return scene6(t)
    if t < 69.06: return scene7_8(t)
    if t < 80.62: return scene9(t)
    if t < 85.32: return scene10(t)
    if t < CIERRE_T: return scene11(t)
    return cierre(t)

# ----------------------------------------------------------- subtítulos
WORDS = json.load(open(os.path.join(WORK, 'words.json')))
FIX = {'Cell': 'Zelle'}
for w in WORDS: w['w'] = FIX.get(w['w'], w['w'])
KEY = {'nsa', 'apagó', 'secreta', '17', 'noviembre', 'vigila', 'servicio', 'turnos', 'snowden', 'espió', 'presidentes',
       'brasil', 'méxico', 'sola', 'seis', 'outlook', 'vuelos', 'united', 'chase', 'zelle', 'dinero',
       'ciberataque', 'pruebas', 'técnicos', 'esto', 'economist', '2027', 'cerebro', 'circuitos', 'riesgos',
       'inteligencia', 'ciberataques', 'misiles', 'irán', 'china', 'taiwán', 'tenso', 'fallar', 'nosotros',
       'petróleo', 'gasolina', 'comida', 'latinoamérica', 'navidad', 'bancos', 'falso', 'alerta',
       'otra', 'pasando', 'comentarios', 'secretos', 'interna'}
def norm(w): return w.strip('¿?¡!.,;:"').lower()

CHUNKS = []; cur = []
for i, w in enumerate(WORDS):
    if cur and (len(cur) >= 3 or cur[-1]['w'][-1] in '.,?!' or w['s'] - cur[-1]['e'] > 0.35):
        CHUNKS.append(cur); cur = []
    cur.append(w)
CHUNKS.append(cur)
for k, c in enumerate(CHUNKS):
    c_end = CHUNKS[k + 1][0]['s'] if k + 1 < len(CHUNKS) else c[-1]['e'] + 0.6
    for w in c: w['chunk_end'] = min(c_end, c[-1]['e'] + 0.8)

SUB_Y = 330
def subtitles(b, t):
    for c in CHUNKS:
        if c[0]['s'] <= t < c[0]['chunk_end']: break
    else: return b
    vis = [w for w in c if t >= w['s']]
    if not vis: return b
    # disposición en una o dos líneas
    size = 84; f = font('Anton', size); space = 22
    items = []
    for w in c:
        txt = w['w'].upper().strip(',.;:')
        if txt.endswith('?') or txt.startswith('¿'): pass
        items.append((w, txt, f.getlength(txt)))
    lines = [[]]; lw = 0
    for it in items:
        if lines[-1] and lw + space + it[2] > 960: lines.append([]); lw = 0
        lines[-1].append(it); lw += (space if len(lines[-1]) > 1 else 0) + it[2]
    y = SUB_Y - (len(lines) - 1) * 50
    for line in lines:
        tot = sum(i[2] for i in line) + space * (len(line) - 1); x = (W - tot) / 2
        for w, txt, wl in line:
            if t >= w['s']:
                is_key = norm(w['w']) in KEY
                col = RED if is_key else WHITE
                im = text_rgba(txt, 'Anton', size, col, stroke=6, sfill=(0, 0, 0), shadow=6)
                dt = t - w['s']; sc = 1.0 + 0.18 * (1 - eout(dt / 0.12))
                b = overlay(b, im, x + wl / 2, y, scale=sc, alpha=min(1, dt / 0.05 + 0.3))
            x += wl + space
        y += 100
    return b

# ----------------------------------------------------- efectos globales
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.78 * np.clip(((XX - W / 2) / (W * 0.62)) ** 2 + ((YY - H / 2) / (H * 0.6)) ** 2, 0, 1) ** 1.3)[..., None]
_gr = np.random.default_rng(99)
GRAIN = [(_gr.normal(0, 1, (H // 2, W // 2)).astype(np.float32)) for _ in range(12)]
GRAIN = [cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)[..., None] for g in GRAIN]

def glitch(b, amt, seed):
    rng = np.random.default_rng(seed)
    out = b.copy()
    dx = int(28 * amt)
    out[..., 0] = np.roll(b[..., 0], dx, 1); out[..., 2] = np.roll(b[..., 2], -dx, 1)
    for _ in range(int(4 + 14 * amt)):
        y = rng.integers(0, H - 20); h = rng.integers(8, int(30 + 120 * amt))
        out[y:y + h] = np.roll(out[y:y + h], int(rng.normal(0, 140 * amt)), 1)
    for _ in range(int(3 * amt)):
        y = rng.integers(0, H - 60); x = rng.integers(0, W - 200); h = rng.integers(10, 60); w = rng.integers(80, 400)
        col = RED if rng.random() < 0.5 else (90, 200, 255)
        out[y:y + h, x:x + w] = (out[y:y + h, x:x + w] * 0.3 + np.array(col) * 0.7).astype(np.uint8)
    if rng.random() < 0.3 * amt:
        y = rng.integers(0, H - 200); out[y:y + 150] = 255 - out[y:y + 150]
    return out

def glitch_amount(t):
    a = 0.0
    for t0, d, s in GLITCHES:
        if t0 <= t < t0 + d: a = max(a, s * (0.6 + 0.4 * math.sin((t - t0) * 50) ** 2))
    return a

def frame(i):
    t = i / FPS
    b = scene(t)
    if t < CIERRE_T:
        b = (b.astype(np.float32) * VIG).astype(np.uint8)
    b = subtitles(b, t)
    g = glitch_amount(t)
    if g > 0: b = glitch(b, g, i)
    # destello rojo tenue en los golpes
    for t0, s in BOOMS:
        if t0 <= t < t0 + 0.25 and s >= 0.9:
            k = (1 - (t - t0) / 0.25) * 0.18
            b = np.clip(b.astype(np.float32) * (1 - k) + np.array(RED, np.float32) * k, 0, 255).astype(np.uint8)
    # grano
    gr = GRAIN[i % len(GRAIN)]
    f = b.astype(np.float32) + gr * 9.0
    # parpadeo de proyector muy leve
    f *= 1 + 0.015 * math.sin(i * 1.7)
    return np.clip(f, 0, 255).astype(np.uint8)

if __name__ == '__main__':
    s, e, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    import subprocess
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', out],
                         stdin=subprocess.PIPE)
    for i in range(s, e):
        p.stdin.write(frame(i).tobytes())
    p.stdin.close(); p.wait()
