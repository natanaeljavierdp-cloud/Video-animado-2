# Capital Curioso — "Ningún avión despega" (vertical 1080x1920, 30 fps)
# Renders frames with Pillow and pipes them to ffmpeg. Audio is mixed by audio.py.
import json, math, random, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
DUR = 76.0
NAVY = (10, 22, 48); NAVY2 = (18, 40, 84); NAVY3 = (34, 62, 112)
RED = (226, 30, 48); WHITE = (255, 255, 255); GREY = (170, 182, 200)
FD = '/usr/share/fonts/opentype/inter/'
FONTS = {'black': FD + 'Inter-Black.otf', 'xb': FD + 'Inter-ExtraBold.otf', 'b': FD + 'Inter-Bold.otf',
         'sb': FD + 'Inter-SemiBold.otf', 'm': FD + 'Inter-Medium.otf'}
EMOJI = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'

# ---------------------------------------------------------------- utils
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def p(t, a, b): return clamp((t - a) / (b - a))
def eo(x): return 1 - (1 - x) ** 3
def eio(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def back(x):
    c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def lerp(a, b, x): return a + (b - a) * x
def lerpc(c1, c2, x): return tuple(int(lerp(a, b, x)) for a, b in zip(c1, c2))

@lru_cache(None)
def F(k, s): return ImageFont.truetype(FONTS[k], s)

@lru_cache(4096)
def T(s, k, size, color=WHITE, stroke=0, scol=(0, 0, 0), shadow=True):
    f = F(k, size)
    l, t, r, b = f.getbbox(s, stroke_width=stroke)
    pad = 30 if shadow else 4
    w, h = r - l + pad * 2, b - t + pad * 2
    im = Image.new('RGBA', (max(w, 1), max(h, 1)), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l, pad - t + 6), s, font=f, fill=(0, 0, 0, 170), stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        im = sh.filter(ImageFilter.GaussianBlur(9))
    ImageDraw.Draw(im).text((pad - l, pad - t), s, font=f, fill=color, stroke_width=stroke, stroke_fill=scol)
    return im

def tw(s, k, size):
    l, t, r, b = F(k, size).getbbox(s); return r - l

def put(fr, tile, x, y, a=1.0, anchor='mm', scale=1.0):
    if a <= 0.004: return
    if abs(scale - 1) > 1e-3:
        tile = tile.resize((max(1, int(tile.width * scale)), max(1, int(tile.height * scale))), Image.BILINEAR)
    w, h = tile.size
    ox = {'l': 0, 'm': w / 2, 'r': w}[anchor[0]]
    oy = {'t': 0, 'm': h / 2, 'b': h}[anchor[1]]
    m = tile.getchannel('A')
    if a < 0.999: m = m.point(lambda v: int(v * a))
    fr.paste(tile, (int(x - ox), int(y - oy)), m)

def text(fr, s, x, y, k='black', size=60, color=WHITE, a=1, anchor='mm', scale=1, stroke=0, shadow=True):
    put(fr, T(s, k, size, color, stroke, (0, 0, 0), shadow), x, y, a, anchor, scale)

def fit_size(s, k, size, maxw):
    while size > 20 and tw(s, k, size) > maxw: size -= 2
    return size

# ---------------------------------------------------------------- images
IMG = {}
def img(name):
    if name not in IMG:
        IMG[name] = Image.open(os.path.join(HERE, 'imagenes', name + '.jpg')).convert('RGB')
    return IMG[name]

def view(name, w, h, z=1.0, fx=.5, fy=.5):
    src = img(name); sw, sh = src.size
    if sw / sh > w / h: ch = sh; cw = sh * w / h
    else: cw = sw; ch = sw * h / w
    cw /= z; ch /= z
    x0 = clamp(fx * sw - cw / 2, 0, sw - cw); y0 = clamp(fy * sh - ch / 2, 0, sh - ch)
    return src.resize((w, h), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))

def grad_overlay():
    a = np.zeros((H, W), np.float32)
    y = np.arange(H)[:, None]
    a += np.clip((620 - y) / 620, 0, 1) ** 1.3 * 200
    a += np.clip((y - 1250) / 670, 0, 1) ** 1.4 * 200
    xx = (np.arange(W)[None, :] - W / 2) / (W / 2)
    a += (np.abs(xx) ** 3) * 60
    a = np.clip(a, 0, 235).astype(np.uint8)
    im = Image.new('RGBA', (W, H), NAVY + (0,)); im.putalpha(Image.fromarray(a)); return im
GRAD = grad_overlay()
NAVY_IMG = Image.new('RGB', (W, H), NAVY)

def graded(name, z, fx=.5, fy=.5, tint=.35, dark=0.0):
    f = view(name, W, H, z, fx, fy)
    f = Image.blend(f, NAVY_IMG, tint)
    if dark: f = Image.blend(f, Image.new('RGB', (W, H), (4, 8, 18)), dark)
    f.paste(GRAD, (0, 0), GRAD)
    return f

def make_grid_bg():
    g = np.zeros((H + 80, W, 3), np.float32)
    y = np.arange(H + 80)[:, None]; x = np.arange(W)[None, :]
    r = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * .45) / H) ** 2)
    for i, c in enumerate(NAVY2):
        g[..., i] = lerp(c, 4, 0) * (1 - np.clip(r * 1.5, 0, 1)) + 5 * np.clip(r * 1.5, 0, 1) + NAVY[i] * .5
    im = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im, 'RGBA')
    for gx in range(0, W + 1, 80): d.line([(gx, 0), (gx, H + 80)], fill=(120, 160, 230, 18), width=1)
    for gy in range(0, H + 81, 80): d.line([(0, gy), (W, gy)], fill=(120, 160, 230, 18), width=1)
    return im
GRID = make_grid_bg()
def grid_bg(t):
    o = int(t * 18) % 80
    return GRID.crop((0, o, W, o + H))

def dark_bg():
    a = np.zeros((H, W, 3), np.uint8); a[...] = (5, 9, 20)
    a[::4] = (9, 15, 30)
    return Image.fromarray(a)
DARK = dark_bg()

def panel(fr, im, x, y, r=26, border=4):
    w, h = im.size
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    sh = Image.new('RGBA', (w + 80, h + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((40, 50, w + 40, h + 50), r, fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(18)); put(fr, sh, x - 40, y - 40, anchor='lt')
    fr.paste(im, (int(x), int(y)), m)
    ImageDraw.Draw(fr, 'RGBA').rounded_rectangle((x, y, x + w - 1, y + h - 1), r, outline=(255, 255, 255, 230), width=border)

def pill(fr, s, x, y, size=34, bg=RED, fg=WHITE, a=1, anchor='m'):
    tile = T(s, 'black', size, fg, 0, (0, 0, 0), False)
    w, h = tile.width + 28, tile.height + 8
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), 10, fill=bg + (255,))
    im.alpha_composite(tile, (14, 4))
    put(fr, im, x, y, a, anchor + 'm')

# ---------------------------------------------------------------- geo
def topo_rings(path, obj):
    t = json.load(open(path)); tr = t.get('transform'); arcs = []
    for a in t['arcs']:
        x = y = 0; o = []
        for q in a:
            if tr: x += q[0]; y += q[1]; o.append((x * tr['scale'][0] + tr['translate'][0], y * tr['scale'][1] + tr['translate'][1]))
            else: o.append((q[0], q[1]))
        arcs.append(o)
    def ring(ix):
        pts = []
        for i in ix:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(a if not pts else a[1:])
        return pts
    out = []
    for g in t['objects'][obj]['geometries']:
        if g['type'] == 'Polygon': polys = [g['arcs']]
        elif g['type'] == 'MultiPolygon': polys = g['arcs']
        else: continue
        out.append((g.get('id'), g.get('properties', {}).get('name'), [ring(pp[0]) for pp in polys]))
    return out

def simplify(pts):
    o = []
    for x, y in pts:
        q = (round(x, 1), round(y, 1))
        if not o or abs(q[0] - o[-1][0]) + abs(q[1] - o[-1][1]) >= 1.2: o.append(q)
    return o if len(o) >= 3 else None

# US states (pre-projected Albers, 975x610)
US = []
_rng = random.Random(7)
for sid, name, rings in topo_rings(os.path.join(HERE, 'data/states-albers-10m.json'), 'states'):
    rr = [r for r in (simplify([(x * 960 / 975, y * 960 / 975) for x, y in ring]) for ring in rings) if r]
    if not rr: continue
    cx = np.mean([q[0] for r in rr for q in r]); cy = np.mean([q[1] for r in rr for q in r])
    US.append({'rings': rr, 'cx': cx, 'cy': cy, 'key': cx / 960 + _rng.uniform(-.12, .12)})
order = sorted(range(len(US)), key=lambda i: -US[i]['key'])  # east -> west
for rank, i in enumerate(order): US[i]['t'] = 8.3 + 5.2 * rank / len(US)
US_LAND = [(s['cx'], s['cy']) for s in US]

def draw_us(fr, ox, oy, t, lit=True, a=1.0):
    d = ImageDraw.Draw(fr, 'RGBA')
    for s in US:
        k = p(t, s['t'], s['t'] + .45) if lit else 0
        c = lerpc(NAVY3, RED, k)
        for r in s['rings']:
            pts = [(ox + x, oy + y) for x, y in r]
            d.polygon(pts, fill=c + (int(255 * a),))
            d.line(pts + [pts[0]], fill=(220, 230, 245, int(150 * a)), width=2)

# World (equirectangular), lat 84..-58
WM_W = 960; LAT0, LAT1 = 84, -58; WM_H = int(WM_W * (LAT0 - LAT1) / 360)
WORLD = []
for cid, name, rings in topo_rings(os.path.join(HERE, 'data/countries-110m.json'), 'countries'):
    rr = []
    for ring in rings:
        pts = [((lon + 180) / 360 * WM_W, (LAT0 - lat) / (LAT0 - LAT1) * WM_H) for lon, lat in ring]
        if any(abs(pts[i][0] - pts[i - 1][0]) > WM_W / 2 for i in range(1, len(pts))):
            pts = [(x + WM_W if x < WM_W / 2 else x, y) for x, y in pts]
        s_ = simplify(pts)
        if s_: rr.append(s_)
    if rr and name != 'Antarctica': WORLD.append({'rings': rr, 'name': name})
_rng = random.Random(3)
lit_idx = list(range(len(WORLD))); _rng.shuffle(lit_idx)
force = [i for i, c in enumerate(WORLD) if c['name'] in ('United States of America', 'Brazil', 'Mexico', 'Germany', 'India', 'Australia', 'United Kingdom', 'Japan', 'Colombia', 'Dominican Rep.', 'Spain', 'France', 'Canada', 'Argentina')]
lit_idx = force + [i for i in lit_idx if i not in force]
for c in WORLD: c['t'] = None
for k, i in enumerate(lit_idx[:74]): WORLD[i]['t'] = 35.0 + 1.35 * k / 74

def draw_world(fr, ox, oy, t, a=1.0):
    wm = Image.new('RGBA', (WM_W, WM_H), (0, 0, 0, 0)); d = ImageDraw.Draw(wm)
    for c in WORLD:
        k = p(t, c['t'], c['t'] + .25) if c['t'] else 0
        col = lerpc(NAVY3, RED, k)
        for r in c['rings']:
            d.polygon(r, fill=col + (255,), outline=(160, 180, 215, 255))
    m = wm.getchannel('A')
    if a < 1: m = m.point(lambda v: int(v * a))
    fr.paste(wm, (int(ox), int(oy)), m)

# Hispaniola
HISP = json.load(open(os.path.join(HERE, 'data/hispaniola.json')))
DR_LON0, DR_LON1, DR_LAT0 = -72.25, -68.20, 20.05
DR_K = 940 / ((DR_LON1 - DR_LON0) * math.cos(math.radians(19)))
def dr_proj(lon, lat): return ((lon - DR_LON0) * math.cos(math.radians(19)) * DR_K, (DR_LAT0 - lat) * DR_K)
HISP_P = {k: [simplify([dr_proj(*q) for q in r]) for r in v] for k, v in HISP.items()}
CITIES = [('SANTO DOMINGO', 18.4861, -69.9312, 62.78, 'r'), ('SANTIAGO', 19.4517, -70.6970, 63.72, 'l'), ('PUNTA CANA', 18.5601, -68.3725, 64.44, 'u')]

# ---------------------------------------------------------------- icons
def plane_tile(sz=46):
    S = 200; im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((88, 15, 112, 185), 12, fill=WHITE)
    d.polygon([(100, 70), (10, 120), (10, 135), (100, 110), (190, 135), (190, 120)], fill=WHITE)
    d.polygon([(100, 160), (60, 185), (60, 195), (100, 185), (140, 195), (140, 185)], fill=WHITE)
    return im.resize((sz, sz), Image.LANCZOS)
PLANE = plane_tile()
_rng = random.Random(11)
PLANES = []
for i in range(46):
    cx, cy = US_LAND[_rng.randrange(len(US_LAND))]
    hd = _rng.uniform(0, 360)
    PLANES.append({'x': cx + _rng.uniform(-30, 30), 'y': cy + _rng.uniform(-25, 25), 'hd': hd,
                   'tile': PLANE.rotate(-hd, Image.BICUBIC, expand=True), 't': 11.4 + _rng.uniform(0, 1.6)})

def antenna(d, x, y, on, s=1.0):
    col = (235, 242, 255, 255) if on else (85, 95, 115, 255)
    d.polygon([(x, y - 34 * s), (x - 15 * s, y + 26 * s), (x + 15 * s, y + 26 * s)], outline=col, width=4)
    d.line([(x - 8 * s, y), (x + 8 * s, y)], fill=col, width=3)
    d.ellipse((x - 6 * s, y - 42 * s, x + 6 * s, y - 30 * s), fill=col)
    if on:
        for rr in (20, 32):
            d.arc((x - rr * s, y - 36 * s - rr * s, x + rr * s, y - 36 * s + rr * s), 200, 340, fill=(120, 190, 255, 230), width=4)
    else:
        d.line([(x + 14 * s, y - 50 * s), (x + 30 * s, y - 34 * s)], fill=RED + (255,), width=5)
        d.line([(x + 30 * s, y - 50 * s), (x + 14 * s, y - 34 * s)], fill=RED + (255,), width=5)

@lru_cache(None)
def emoji(ch, size):
    f = ImageFont.truetype(EMOJI, 109)
    im = Image.new('RGBA', (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((size, int(size * im.height / im.width)), Image.LANCZOS)

# 7-segment clock
SEG = {'a': (0, 0, 1, 0), 'b': (1, 0, 1, 1), 'c': (1, 1, 1, 2), 'd': (0, 2, 1, 2), 'e': (0, 1, 0, 2), 'f': (0, 0, 0, 1), 'g': (0, 1, 1, 1)}
DIG = {'3': 'abcdg', '5': 'afgcd', '4': 'fgbc', '8': 'abcdefg'}
def seg_digit(d, x, y, ch, w=120, h=210, th=24, col=RED + (255,)):
    for sname in DIG[ch]:
        x0, y0, x1, y1 = SEG[sname]
        X0, Y0, X1, Y1 = x + x0 * w, y + y0 * h / 2, x + x1 * w, y + y1 * h / 2
        if Y0 == Y1: d.polygon([(X0 + th * .6, Y0), (X0 + th, Y0 - th / 2), (X1 - th, Y0 - th / 2), (X1 - th * .6, Y0), (X1 - th, Y0 + th / 2), (X0 + th, Y0 + th / 2)], fill=col)
        else: d.polygon([(X0, Y0 + th * .6), (X0 + th / 2, Y0 + th), (X0 + th / 2, Y1 - th), (X0, Y1 - th * .6), (X0 - th / 2, Y1 - th), (X0 - th / 2, Y0 + th)], fill=col)

def clock_tile(colon):
    cw, ch = 860, 330
    im = Image.new('RGBA', (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    xs = [40, 270, 450]  # digits: 3 : 5 4
    dim = Image.new('RGBA', (cw, ch), (0, 0, 0, 0)); dd = ImageDraw.Draw(dim)
    for x in xs: seg_digit(dd, x, 60, '8', w=130, col=(42, 10, 18, 255))
    for x, c in zip(xs, '354'): seg_digit(d, x, 60, c, w=130)
    if colon:
        d.ellipse((196, 105, 224, 133), fill=RED + (255,)); d.ellipse((196, 200, 224, 228), fill=RED + (255,))
    d.text((640, 196), 'PM', font=F('black', 90), fill=RED + (255,))
    glow = im.filter(ImageFilter.GaussianBlur(18))
    out = dim
    out.alpha_composite(glow); out.alpha_composite(glow); out.alpha_composite(im)
    return out
CLOCK = {True: clock_tile(True), False: clock_tile(False)}

def logo(size, prog=1.0, q=1.0, handle=1.0):
    S = 600; im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy, R = 260, 255, 175
    if handle > 0:
        L = 210 * handle; a = math.radians(45)
        x0, y0 = cx + (R + 10) * math.cos(a), cy + (R + 10) * math.sin(a)
        x1, y1 = x0 + L * math.cos(a), y0 + L * math.sin(a)
        d.line([(x0, y0), (x1, y1)], fill=RED + (255,), width=62)
        d.ellipse((x1 - 31, y1 - 31, x1 + 31, y1 + 31), fill=RED + (255,))
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=NAVY2 + (255,)) if prog >= 1 else None
    if prog > 0: d.arc((cx - R, cy - R, cx + R, cy + R), -90, -90 + 360 * prog, fill=WHITE + (255,), width=40)
    if q > 0:
        qt = T('?', 'black', 260, RED, 0, (0, 0, 0), False)
        qt = qt.resize((max(1, int(qt.width * q)), max(1, int(qt.height * q))), Image.BILINEAR)
        im.alpha_composite(qt, (int(cx - qt.width / 2), int(cy - qt.height / 2 + 8)))
    return im.resize((size, size), Image.LANCZOS)
LOGO_SMALL = logo(64)

# ---------------------------------------------------------------- subtitles
WORDS = json.load(open(os.path.join(HERE, 'data/words.json')))
FIX = {'7000': '7,000', '3000': '3,000', 'sólo': 'solo', 'La': '¿La', 'Coincidencia': '¿Coincidencia', '¿Hay': '¿Hay'}
def clean(w):
    w = FIX.get(w, w)
    if w not in ('7,000', '3,000'): w = w.rstrip('.,')
    return w.upper()
CHUNKS = []
cur = []
for i, (w, s, e) in enumerate(WORDS):
    cur.append((clean(w), s, e))
    nxt = WORDS[i + 1][1] if i + 1 < len(WORDS) else 999
    if len(cur) >= 3 or w[-1] in '.,?' or nxt - e > .35:
        CHUNKS.append(cur); cur = []
if cur: CHUNKS.append(cur)
for i, c in enumerate(CHUNKS):
    nxt = CHUNKS[i + 1][0][1] if i + 1 < len(CHUNKS) else 999
    c_end = min(c[-1][2] + .35, nxt)
    CHUNKS[i] = (c, c[0][1], c_end)

def subtitles(fr, t):
    for words, s, e in CHUNKS:
        if s - .02 <= t < e: break
    else: return
    size = 70; gap = 22
    while sum(tw(w, 'black', size) for w, _, _ in words) + gap * (len(words) - 1) > 960: size -= 4
    widths = [tw(w, 'black', size) for w, _, _ in words]
    total = sum(widths) + gap * (len(words) - 1)
    x = W / 2 - total / 2; y = 335
    a = p(t, s - .02, s + .08)
    d = ImageDraw.Draw(fr, 'RGBA')
    for (w, ws, we), wd in zip(words, widths):
        active = ws <= t < (we + .12) or (w == words[-1][0] and t >= ws)
        if active:
            pop = 1 + .08 * (1 - eo(p(t, ws, ws + .12)))
            pw, ph = (wd + 30) * pop, (size + 34) * pop
            d.rounded_rectangle((x + wd / 2 - pw / 2, y - ph / 2, x + wd / 2 + pw / 2, y + ph / 2), 14, fill=RED + (int(255 * a),))
        text(fr, w, x + wd / 2, y, 'black', size, WHITE, a, stroke=0 if active else 5)
        x += wd + gap

# ---------------------------------------------------------------- scenes
def s1(t):
    if t < 3.38:
        fr = DARK.copy()
        a = p(t, 0, .35) * (0.55 if int(t * 30) in (4, 7, 9) else 1)
        put(fr, CLOCK[(t % 1.0) < .6], W / 2, 830, a)
        s = 'VIERNES 13 · NOV 2026'; n = int(len(s) * p(t, .5, 1.7))
        if n: text(fr, s[:n], 140, 1060, 'xb', 62, WHITE, 1, 'lm')
        lw = 800 * eo(p(t, 1.6, 2.4))
        if lw > 1: ImageDraw.Draw(fr).rectangle((140, 1110, 140 + lw, 1118), fill=RED)
        text(fr, 'HORA DEL ESTE · EE.UU.', 140, 1160, 'sb', 34, GREY, p(t, 2.0, 2.4), 'lm')
        return fr
    z = 1.04 + .16 * eio(p(t, 3.38, 8.2))
    fr = graded('aeropuerto', z, .44, .55, .28)
    pill(fr, 'EE.UU. · 3:54 PM', W / 2, 560, 36, a=p(t, 3.5, 3.8))
    if t >= 4.9:
        k = p(t, 4.9, 5.08); sc = lerp(1.7, 1.0, eo(k))
        text(fr, 'NINGÚN AVIÓN', W / 2, 900, 'black', 124, WHITE, k, scale=sc)
        k2 = p(t, 5.5, 5.68); sc2 = lerp(1.7, 1.0, eo(k2))
        if k2 > 0:
            tile = T('DESPEGA', 'black', 150, WHITE, 0, (0, 0, 0), False)
            box = Image.new('RGBA', (tile.width + 50, tile.height + 10), RED + (255,)); box.alpha_composite(tile, (25, 5))
            put(fr, box, W / 2, 1065, k2, scale=sc2)
    return fr

def s2(t):
    fr = grid_bg(t)
    mapa = t < 15.6
    fade = 1 - p(t, 15.0, 15.6)
    if mapa:
        mx, my = 60, 760 - 30 * p(t, 11.0, 11.6)
        layer = fr.copy()
        draw_us(layer, mx, my, t)
        for pl in PLANES:
            k = p(t, pl['t'], pl['t'] + .25)
            if k <= 0: continue
            dt = t - pl['t']; r = math.radians(pl['hd'])
            put(layer, pl['tile'], mx + pl['x'] + math.sin(r) * dt * 9, my + pl['y'] - math.cos(r) * dt * 9, k, scale=lerp(1.6, 1, eo(k)))
        fr = Image.blend(fr, layer, fade) if fade < 1 else layer
        # 7,000 counter
        k = p(t, 8.06, 9.9); n = int(round(7000 * eo(k) / 10) * 10)
        a = p(t, 8.0, 8.2) * fade
        text(fr, 'CASI', W / 2, 500, 'xb', 44, GREY, a)
        text(fr, f'{n:,}', W / 2, 600, 'black', 160, RED, a)
        text(fr, 'VUELOS RETRASADOS O CANCELADOS', W / 2, 705, 'xb', 42, WHITE, a * p(t, 8.9, 9.2))
        k = p(t, 11.38, 12.4); n = int(3100 * eo(k))
        a = p(t, 11.38, 11.55) * fade
        if a > 0:
            text(fr, f'{n:,}', W / 2, 1450, 'black', 140, WHITE, a)
            pill(fr, 'AVIONES EN EL AIRE', W / 2, 1555, 40, a=a)
    if t >= 15.0:
        a = p(t, 15.1, 15.4)
        text(fr, 'EN ESTE SIGLO', W / 2, 610, 'xb', 50, GREY, a)
        k = p(t, 16.2, 16.4)
        text(fr, 'SOLO 2 VECES', W / 2, 715, 'black', 120, WHITE, k, scale=lerp(1.4, 1, eo(k)))
        d = ImageDraw.Draw(fr, 'RGBA'); ly = 1120
        xs = [170, 540, 910]
        x_end = lerp(90, 600, eio(p(t, 17.0, 18.6))) + (910 - 600 + 80) * eio(p(t, 20.9, 21.6))
        if x_end > 92: d.rounded_rectangle((90, ly - 5, x_end, ly + 5), 5, fill=(200, 215, 240, 255))
        pts = [(18.45, '11 SEP', '2001', WHITE), (20.62, 'ENE', '2023', WHITE), (21.45, '13 NOV', '2026', RED)]
        for (tt, l1, l2, col), x in zip(pts, xs):
            k = p(t, tt, tt + .3)
            if k <= 0: continue
            r = 26 * back(k)
            if col == RED:
                pr = (t - tt) % 1.0
                d.ellipse((x - 26 - 50 * pr, ly - 26 - 50 * pr, x + 26 + 50 * pr, ly + 26 + 50 * pr), outline=RED + (int(255 * (1 - pr)),), width=5)
            d.ellipse((x - r, ly - r, x + r, ly + r), fill=col + (255,), outline=WHITE + (255,), width=5)
            text(fr, l1, x, ly - 130, 'black', 52, col, k)
            text(fr, l2, x, ly - 75, 'black', 52, col, k)
            if col == RED: pill(fr, 'HOY', x, ly + 85, 40, a=k)
    return fr

def s3(t):
    z = 1.05 + .18 * eio(p(t, 22.4, 31.3))
    fr = graded('torre', z, .74, .45, .38, .15)
    pill(fr, 'CAUSA OFICIAL', W / 2, 530, 40, a=p(t, 22.75, 23.0))
    a = p(t, 24.04, 24.3)
    text(fr, 'FALLA DE COMUNICACIONES', W / 2, 625, 'black', fit_size('FALLA DE COMUNICACIONES', 'black', 66, 960), WHITE, a)
    out = 1 - p(t, 28.3, 28.6)
    if t >= 25.7 and out > 0:
        k = p(t, 25.78, 25.98)
        text(fr, '22', W / 2, 870, 'black', 280, WHITE, k * out, scale=lerp(1.6, 1, eo(k)))
        text(fr, 'CENTROS DE CONTROL', W / 2, 1050, 'black', 64, WHITE, p(t, 26.1, 26.3) * out, stroke=3)
        d = ImageDraw.Draw(fr, 'RGBA')
        for i in range(22):
            row, col = divmod(i, 11)
            x = 130 + col * 82; y = 1220 + row * 130
            ka = p(t, 25.9 + i * .015, 26.1 + i * .015)
            if ka <= 0 or out < .5: continue
            on = t < 26.4 + i * .085
            antenna(d, x, y, on, .95)
    if t >= 28.4:
        k = eo(p(t, 28.4, 28.85)); y0 = 940 + (1 - k) * 900
        cw, ch = 960, 560
        card = Image.new('RGBA', (cw, ch), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((0, 0, cw - 1, ch - 1), 28, fill=(248, 249, 252, 255))
        cd.rounded_rectangle((0, 0, 18, ch - 1), 9, fill=RED + (255,))
        cd.text((50, -40), '“', font=F('black', 220), fill=RED + (255,))
        cd.text((60, 150), 'Es solo una falla de', font=F('xb', 62), fill=NAVY + (255,))
        cd.text((60, 225), 'telecomunicaciones”', font=F('xb', 62), fill=NAVY + (255,))
        cd.line((60, 345, cw - 60, 345), fill=(200, 205, 215, 255), width=3)
        cd.text((60, 375), 'MARKWAYNE MULLIN', font=F('black', 44), fill=RED + (255,))
        cd.text((60, 435), 'Secretario de Seguridad Nacional de EE.UU.', font=F('sb', 32), fill=NAVY2 + (255,))
        cd.text((60, 490), 'Fuente: AP', font=F('m', 28), fill=(120, 128, 145, 255))
        sh = Image.new('RGBA', (cw + 80, ch + 80), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((40, 55, cw + 40, ch + 55), 28, fill=(0, 0, 0, 170))
        put(fr, sh.filter(ImageFilter.GaussianBlur(20)), 20, y0 - 40, anchor='lt')
        put(fr, card, 60, y0, anchor='lt')
    return fr

# --- coincidences cards (ox = horizontal offset)
def card_a(fr, t, ox):
    pill(fr, 'COINCIDENCIA 1/3', W / 2 + ox, 500, 34)
    name = 'pantalla-error' if t < 34.38 else 'microsoft'
    im = view(name, 960, 500, 1.04 + .08 * p(t, 33.2, 37.5), .5, .45 if name == 'microsoft' else .5)
    if 34.3 < t < 34.6 or 33.3 < t < 33.45:
        arr = np.array(im); rs = random.Random(int(t * 30))
        for _ in range(6):
            y = rs.randrange(0, 480); hh = rs.randrange(8, 40); arr[y:y + hh] = np.roll(arr[y:y + hh], rs.randrange(-80, 80), axis=1)
        arr[..., 0] = np.roll(arr[..., 0], 8, axis=1); im = Image.fromarray(arr)
    panel(fr, im, 60 + ox, 545)
    text(fr, '12 NOV: SE CAE MICROSOFT', W / 2 + ox, 1115, 'black', fit_size('12 NOV: SE CAE MICROSOFT', 'black', 64, 960), WHITE, p(t, 34.38, 34.6))
    draw_world(fr, 60 + ox, 1175, t, p(t, 34.6, 35.0))
    k = p(t, 35.0, 36.4)
    if t >= 35.0:
        n = int(74 * eo(k))
        text(fr, f'{n}', 210 + ox, 1440, 'black', 140, WHITE, p(t, 35.0, 35.15), stroke=4)
        text(fr, 'PAÍSES', 390 + ox, 1470, 'black', 50, RED, p(t, 35.0, 35.15), 'lm', stroke=3)

def card_b(fr, t, ox):
    pill(fr, 'COINCIDENCIA 2/3', W / 2 + ox, 500, 34)
    panel(fr, view('mochila', 960, 500, 1.02 + .1 * p(t, 37.4, 45.0), .5, .4), 60 + ox, 545)
    text(fr, 'GUARDAR AGUA Y COMIDA PARA:', W / 2 + ox, 1115, 'black', fit_size('GUARDAR AGUA Y COMIDA PARA:', 'black', 54, 960), WHITE, p(t, 40.4, 40.7))
    d = ImageDraw.Draw(fr, 'RGBA')
    # bar 1
    a1 = p(t, 41.0, 41.3); k1 = eo(p(t, 41.2, 42.4))
    if a1 > 0:
        text(fr, '72 HORAS', 70 + ox, 1205, 'black', 50, WHITE, a1, 'lm')
        text(fr, '(estándar)', 70 + ox + tw('72 HORAS', 'black', 50) + 16, 1210, 'sb', 36, GREY, a1, 'lm')
        L = 270 * k1
        d.rounded_rectangle((70 + ox, 1245, 70 + ox + max(L, 12), 1335), 12, fill=(214, 224, 242, int(255 * a1)))
        if k1 > .05: text(fr, f'{int(72 * k1)} h', 70 + ox + L + 20, 1290, 'black', 48, WHITE, a1, 'lm')
    a2 = p(t, 43.1, 43.4); k2 = eo(p(t, 43.25, 44.5))
    if a2 > 0:
        text(fr, '10 DÍAS', 70 + ox, 1405, 'black', 50, RED, a2, 'lm')
        text(fr, '(Alemania)', 70 + ox + tw('10 DÍAS', 'black', 50) + 16, 1410, 'sb', 36, GREY, a2, 'lm')
        L = 900 * k2
        d.rounded_rectangle((70 + ox, 1445, 70 + ox + max(L, 12), 1545), 12, fill=RED + (int(255 * a2),))
        if k2 > .3: text(fr, f'{max(1, int(round(10 * k2)))} DÍAS', 70 + ox + L - 20, 1495, 'black', 50, WHITE, a2, 'rm')

def card_c(fr, t, ox):
    pill(fr, 'COINCIDENCIA 3/3', W / 2 + ox, 500, 34)
    panel(fr, view('petro', 960, 690, 1.0 + .12 * p(t, 44.9, 53.3), .5, .3), 60 + ox, 545)
    k = eo(p(t, 47.84, 48.2))
    if k > 0:
        lx = 60 + ox - (1 - k) * 700
        nt = T('GUSTAVO PETRO', 'black', 54, WHITE, 0, (0, 0, 0), False)
        rt = T('Expresidente de Colombia', 'sb', 36, WHITE, 0, (0, 0, 0), False)
        d = ImageDraw.Draw(fr, 'RGBA')
        d.rectangle((lx, 1095, lx + nt.width + 30, 1095 + nt.height + 10), fill=RED + (255,))
        put(fr, nt, lx + 15, 1100, anchor='lt')
        d.rectangle((lx, 1095 + nt.height + 10, lx + rt.width + 30, 1095 + nt.height + 20 + rt.height), fill=NAVY + (240,))
        put(fr, rt, lx + 15, 1100 + nt.height + 10, anchor='lt')
    text(fr, 'RECOMENDÓ GUARDAR', W / 2 + ox, 1305, 'xb', 44, WHITE, p(t, 50.7, 50.95))
    k = p(t, 51.84, 52.02)
    if k > 0:
        text(fr, '2 MESES', W / 2 + ox, 1410, 'black', 160, RED, k, scale=lerp(1.6, 1, eo(k)), stroke=3)
        text(fr, 'DE ALIMENTOS', W / 2 + ox, 1515, 'black', 52, WHITE, p(t, 52.2, 52.4))
        text(fr, 'Fuente: su cuenta de X', W / 2 + ox, 1572, 'm', 28, GREY, p(t, 52.3, 52.5))

def s4(t):
    if t < 33.28:
        fr = graded('error-azul', 1.0 + .1 * p(t, 31.2, 33.4), .5, .5, .15, .25)
        k = p(t, 31.6, 31.8)
        jit = (random.Random(int(t * 30)).randint(-18, 18) if t < 32.0 else 0)
        text(fr, 'LAS', W / 2 + jit, 830, 'black', 80, WHITE, p(t, 31.36, 31.5))
        sz = fit_size('COINCIDENCIAS', 'black', 140, 960)
        text(fr, 'COINCIDENCIAS', W / 2 - jit, 950, 'black', sz, WHITE, k, scale=lerp(1.4, 1, eo(k)))
        lw = 900 * eo(p(t, 32.0, 32.5))
        if lw > 1: ImageDraw.Draw(fr).rectangle((W / 2 - lw / 2, 1040, W / 2 + lw / 2, 1052), fill=RED)
        return fr
    fr = grid_bg(t)
    cards = [(33.28, card_a), (37.5, card_b), (44.98, card_c)]
    for i, (st, fn) in enumerate(cards):
        en = cards[i + 1][0] if i + 1 < len(cards) else 99
        if t < st or t >= en + .4: continue
        ox = W * (1 - eo(p(t, st, st + .4))) - W * eo(p(t, en, en + .4))
        fn(fr, t, ox)
    return fr

NODES = [(random.Random(i).uniform(80, 1000), random.Random(i * 7 + 1).uniform(480, 1650)) for i in range(20)]
EDGES = [(i, j) for i in range(20) for j in range(i + 1, 20) if math.dist(NODES[i], NODES[j]) < 330]
def s5(t):
    fr = grid_bg(t); d = ImageDraw.Draw(fr, 'RGBA')
    broken = t >= 55.72
    for n, (i, j) in enumerate(EDGES):
        k = p(t, 53.3 + n * .03, 53.8 + n * .03)
        if k <= 0: continue
        (x0, y0), (x1, y1) = NODES[i], NODES[j]
        if broken and n % 2 == 0: k = min(k, 0.45)
        col = (RED if broken else (120, 170, 240)) + (70,)
        d.line([(x0, y0), (lerp(x0, x1, k), lerp(y0, y1, k))], fill=col, width=3)
    for i, (x, y) in enumerate(NODES):
        r = 7 + 3 * math.sin(t * 4 + i)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(150, 190, 255, 110))
    for line, y, st in (('¿ESTÁ TODO', 740, 53.4), ('CONECTADO?', 870, 54.2)):
        n = int(len(line) * p(t, st, st + .6))
        if n:
            x0 = W / 2 - tw(line, 'black', 120) / 2
            text(fr, line[:n], x0, y, 'black', 120, WHITE, 1, 'lm')
    if t >= 55.72:
        k = p(t, 55.72, 55.88)
        put(fr, STAMP, W / 2, 1200, k, scale=lerp(2.3, 1, eo(k)))
    a = p(t, 57.48, 57.8)
    if a > 0:
        text(fr, 'Autoridades: son hechos separados', W / 2, 1460, 'sb', fit_size('Autoridades: son hechos separados', 'sb', 46, 940), GREY, a)
    return fr

def make_stamp():
    w, h = 860, 300
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 6, w - 6, h - 6), 20, outline=RED + (255,), width=12)
    d.rounded_rectangle((28, 28, w - 28, h - 28), 12, outline=RED + (255,), width=4)
    for s, y, sz in (('SIN PRUEBAS', 105, 104), ('HASTA AHORA', 215, 76)):
        f = F('black', sz); l, tt, r, b = f.getbbox(s)
        d.text((w / 2 - (r - l) / 2 - l, y - (b - tt) / 2 - tt), s, font=f, fill=RED + (255,))
    rs = np.random.RandomState(5)
    noise = rs.rand(h, w) > .12
    a = np.array(im.getchannel('A')) * noise
    im.putalpha(Image.fromarray(a.astype(np.uint8)))
    big = Image.new('RGBA', (w + 120, h + 220), (0, 0, 0, 0)); big.alpha_composite(im, (60, 110))
    return big.rotate(8, Image.BICUBIC)
STAMP = make_stamp()

def s6(t):
    fr = graded('aila', 1.05 + .1 * p(t, 60, 65.6), .5, .5, .4, .35)
    pill(fr, 'REPÚBLICA DOMINICANA', W / 2, 530, 40, a=p(t, 60.15, 60.4))
    ox, oy = 70, 720
    k = eo(p(t, 60.1, 60.8))
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    for name, rings in HISP_P.items():
        dr = name.startswith('Dominican')
        for r in rings:
            if not r: continue
            pts = [(ox + x, oy + y + (1 - k) * 60) for x, y in r]
            d.polygon(pts, fill=(NAVY2 + (235,)) if dr else (40, 50, 70, 150))
            d.line(pts + [pts[0]], fill=(255, 255, 255, 255) if dr else (150, 160, 180, 160), width=4 if dr else 2, joint='curve')
    m = layer.getchannel('A').point(lambda v: int(v * k)); fr.paste(layer, (0, 0), m)
    text(fr, 'HAITÍ', ox + 30, oy + 330, 'b', 32, GREY, k * .8)
    d = ImageDraw.Draw(fr, 'RGBA')
    for name, lat, lon, tt, side in CITIES:
        kk = p(t, tt, tt + .25)
        if kk <= 0: continue
        x, y = dr_proj(lon, lat); x += ox; y += oy
        for ph in (0, .5):
            pr = ((t - tt) * 1.1 + ph) % 1.0
            rr = 16 + 60 * pr
            d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=RED + (int(220 * (1 - pr) * kk),), width=5)
        r = 16 * back(kk)
        d.ellipse((x - r, y - r, x + r, y + r), fill=RED + (255,), outline=WHITE + (255,), width=4)
        if side == 'r': text(fr, name, x - 10, y + 60, 'black', 38, WHITE, kk, 'mm')
        elif side == 'l': text(fr, name, x - 20, y - 55, 'black', 38, WHITE, kk, 'mm')
        else: text(fr, name, x - 40, y - 55, 'black', 38, WHITE, kk, 'mm')
    a = p(t, 62.0, 62.3)
    text(fr, 'RETRASOS EN VUELOS', W / 2, 1360, 'black', 76, WHITE, a)
    text(fr, 'HACIA EE.UU.', W / 2, 1455, 'black', 76, RED, p(t, 62.2, 62.5), stroke=2)
    return fr

def button(label, letter, bg, w=900, h=150):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 34, fill=bg + (255,), outline=WHITE + (255,), width=5)
    e = emoji(letter, 92); im.alpha_composite(e, (40, (h - e.height) // 2))
    tt = T(label, 'black', 60, WHITE, 0, (0, 0, 0), False)
    im.alpha_composite(tt, (160, (h - tt.height) // 2))
    return im
BTN_A = button('Coincidencia', '🅰', NAVY2)
BTN_B = button('Nos ocultan algo', '🅱', RED)

def s7(t):
    fr = graded('multitud', 1.05 + .08 * p(t, 65.5, 72), .5, .5, .55, .35)
    for line, y, st, col in (('¿COINCIDENCIA', 600, 65.6, WHITE), ('O NOS OCULTAN', 710, 66.4, WHITE), ('ALGO?', 820, 67.5, RED)):
        k = p(t, st, st + .2)
        text(fr, line, W / 2, y, 'black', 100, col, k, scale=lerp(1.3, 1, eo(k)), stroke=2)
    for btn, y, st, ph in ((BTN_A, 1060, 65.7, 0), (BTN_B, 1250, 66.96, math.pi)):
        k = p(t, st, st + .35)
        if k <= 0: continue
        sc = back(k) * (1 + (.025 * math.sin((t - st) * 5 + ph) if t > st + .4 else 0))
        put(fr, btn, W / 2, y, min(1, k * 3), scale=sc)
    k = p(t, 68.92, 69.15)
    if k > 0:
        text(fr, 'Comenta', W / 2 - 60, 1450, 'black', 72, WHITE, k, scale=lerp(1.3, 1, eo(k)))
        put(fr, emoji('👇', 76), W / 2 + 190, 1450 + 12 * math.sin(t * 9), k)
    a = p(t, 70.4, 70.7)
    text(fr, 'Síguenos  @capitalcuriosoo', W / 2, 1560, 'xb', 40, GREY, a)
    return fr

def s8(t):
    fr = grid_bg(t)
    pr = eio(p(t, 72.05, 72.65)); hd = eo(p(t, 72.55, 72.85)); q = back(p(t, 72.75, 73.05))
    lg = logo(560, pr, q if t > 72.75 else 0, hd if t > 72.55 else 0)
    put(fr, lg, W / 2 + 30, 860)
    k1 = eo(p(t, 73.0, 73.3)); k2 = eo(p(t, 73.15, 73.45))
    text(fr, 'CAPITAL', W / 2, 1230 + 60 * (1 - k1), 'black', 130, WHITE, k1)
    text(fr, 'CURIOSO', W / 2, 1360 + 60 * (1 - k2), 'black', 130, RED, k2)
    text(fr, '@capitalcuriosoo', W / 2, 1480, 'xb', 46, GREY, p(t, 73.5, 73.8))
    if t > 75.5:
        fr = Image.blend(fr, Image.new('RGB', (W, H), (0, 0, 0)), p(t, 75.5, 76.0))
    return fr

SCENES = [(0, 8.0, s1), (8.0, 22.5, s2), (22.5, 31.2, s3), (31.2, 53.2, s4), (53.2, 60.0, s5), (60.0, 65.5, s6), (65.5, 72.0, s7), (72.0, 99, s8)]
CUTS = [3.38, 8.0, 22.5, 31.2, 53.2, 60.0, 65.5, 72.0]
SHAKES = [4.9, 5.5, 25.78, 31.6, 51.84, 55.72]

def frame(i):
    t = i / FPS
    for a, b, fn in SCENES:
        if a <= t < b: fr = fn(t); break
    if t < 72.0:
        put(fr, LOGO_SMALL, 60, 1700, .85, 'lm')
        text(fr, '@capitalcuriosoo', 132, 1700, 'b', 30, WHITE, .85, 'lm')
        subtitles(fr, t)
    arr = None
    for c in CUTS:
        dt = t - c
        if 0 <= dt < .17:
            arr = np.array(fr) if arr is None else arr
            rs = random.Random(i)
            for _ in range(7):
                y = rs.randrange(0, H - 60); hh = rs.randrange(20, 110)
                arr[y:y + hh] = np.roll(arr[y:y + hh], rs.randrange(-120, 120), axis=1)
            arr[..., 0] = np.roll(arr[..., 0], 14, axis=1); arr[..., 2] = np.roll(arr[..., 2], -14, axis=1)
            fl = (1 - dt / .17) * .55
            arr = (arr * (1 - fl) + 255 * fl).astype(np.uint8)
    for s in SHAKES:
        dt = t - s
        if 0 <= dt < .35:
            arr = np.array(fr) if arr is None else arr
            amp = 26 * (1 - dt / .35); rs = random.Random(i * 3)
            arr = np.roll(arr, (int(rs.uniform(-amp, amp)), int(rs.uniform(-amp, amp))), axis=(0, 1))
    if arr is not None: return arr.tobytes()
    return fr.tobytes()

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'build/video_mudo.mp4')
    frames = range(int(DUR * FPS))
    if len(sys.argv) > 2:  # preview: list of seconds -> PNGs
        for s in sys.argv[2].split(','):
            Image.frombytes('RGB', (W, H), frame(int(float(s) * FPS))).save(f'{out}_{s}.png')
        sys.exit()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for n, b in enumerate(pool.imap(frame, frames, chunksize=6)):
            ff.stdin.write(b)
            if n % 300 == 0: print(f'frame {n}/{len(frames)}', flush=True)
    ff.stdin.close(); ff.wait()
    print('ok', out)
