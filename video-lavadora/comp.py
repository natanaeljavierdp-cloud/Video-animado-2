# Composicion 2D: fondo de estudio, sombra, etiquetas, subtitulos, textos flotantes.
# Uso: python3 comp.py FRAMES_DIR WORDS_JSON OUT_RAW_PIPE(stdout)
import sys, json, math, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FR = sys.argv[1]
WORDS = json.load(open(sys.argv[2]))
ONLY = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 and sys.argv[3] != '-' else None
PREVIEW_DIR = sys.argv[4] if len(sys.argv) > 4 else None
W, H, FPS = 1080, 1920, 30
DUR = 72.672653
NFR = int(math.ceil(DUR * FPS))
FONT = '/usr/share/fonts/truetype/montserrat/Montserrat-Black.ttf'
_fc = {}
def font(sz):
    sz = int(sz)
    if sz not in _fc: _fc[sz] = ImageFont.truetype(FONT, sz)
    return _fc[sz]

RED = (235, 30, 35, 255)
BLACK = (15, 15, 20, 255)
WHITEC = (255, 255, 255, 255)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def sstep(a, b, x):
    u = clamp((x - a) / (b - a)); return u * u * (3 - 2 * u)
def ease_back(u):
    u = clamp(u); c = 1.7
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2

# ---------------------------------------------------------------- subtitulos
CHUNKS = """¿ALGUNA VEZ|TE HAS PREGUNTADO|QUÉ PASA DENTRO|DE TU *LAVADORA|MIENTRAS *LAVA?|¡VAMOS POR *DENTRO!|POR DENTRO TIENE|DOS *TINAS,|UNA DE *AFUERA,|QUE GUARDA EL *AGUA,|Y UN *TAMBOR|DE ADENTRO,|LLENO DE *AGUJERITOS|DONDE VA LA *ROPA.|PRIMERO SE ABRE|UNA *VÁLVULA|Y ENTRA EL *AGUA.|UN *SENSOR MIDE|HASTA DONDE SUBE,|Y CUANDO LLEGA|AL *NIVEL *JUSTO,|LA *CIERRA.|EN EL CAMINO,|EL AGUA PASA|POR EL *CAJÓN|DEL *DETERGENTE|Y SE LO LLEVA|HACIA ADENTRO.|AHORA EMPIEZA|EL *LAVADO.|UN *MOTOR|HACE GIRAR EL *TAMBOR|HACIA UN LADO,|Y HACIA EL *OTRO.|LA ROPA *SUBE,|*CAE Y SE *FROTA|CON EL AGUA|Y EL *JABÓN.|ASÍ SE SUELTA|LA *SUCIEDAD.|CUANDO TERMINA,|UNA *BOMBA|SACA EL AGUA *SUCIA|POR LA *MANGUERA.|LUEGO ENTRA|AGUA *LIMPIA|PARA *ENJUAGAR|Y SE REPITE|EL MOVIMIENTO.|Y LLEGA LO MEJOR,|EL *CENTRIFUGADO.|EL TAMBOR GIRA|*RAPIDÍSIMO,|EN MUCHAS LAVADORAS|A MÁS DE *MIL|VUELTAS POR MINUTO.|ESA *FUERZA|EMPUJA EL AGUA|HACIA *AFUERA|POR LOS *AGUJERITOS|Y LA ROPA|SE QUEDA ADENTRO,|CASI *SECA.|¿Y POR QUÉ NO|SALE *CAMINANDO?|PORQUE TIENE|*RESORTES,|*AMORTIGUADORES|Y MUCHAS…|HASTA UN BLOQUE|PESADO DE *CONCRETO|QUE LA MANTIENE|*FIRME.|POR ESO NO CONVIENE|*LLENARLA DE MÁS.|LA ROPA NECESITA|*ESPACIO|PARA MOVERSE.|*SÍGUENOS|PARA VER MÁS COSAS|POR *DENTRO."""
SUBS = []
wi = 0
for ch in CHUNKS.split('|'):
    toks = ch.split(' ')
    n = len(toks)
    ws = WORDS[wi:wi + n]
    SUBS.append(dict(toks=[(t.lstrip('*'), t.startswith('*')) for t in toks], t0=ws[0][0], t1=ws[-1][1]))
    wi += n
assert wi == len(WORDS), (wi, len(WORDS))
for i, s in enumerate(SUBS):  # mantener hasta el siguiente
    nxt = SUBS[i + 1]['t0'] if i + 1 < len(SUBS) else DUR
    s['t0'] = max(0.0, s['t0'] - 0.05)
    s['t1'] = min(nxt - 0.02, s['t1'] + 0.45)

# ---------------------------------------------------------------- etiquetas
# (clave ancla, t0, t1, partes, dx, dy)
LABELS = [
    ('tina', 6.9, 9.5, [('TINA', 1), (' NO GIRA', 0)], 120, -330),
    ('tambor', 9.8, 13.1, [('TAMBOR', 1), (' SÍ GIRA', 0)], -40, 330),
    ('valvula', 14.2, 16.3, [('VÁLVULA', 1), (' DE AGUA', 0)], -150, -260),
    ('sensor', 16.0, 20.3, [('SENSOR', 1), (' DE NIVEL', 0)], 0, -280),
    ('detergente', 22.6, 24.6, [('CAJÓN DEL ', 0), ('DETERGENTE', 1)], 80, 330),
    ('motor', 26.9, 29.6, [('MOTOR', 1), (' + CORREA', 0)], 120, 260),
    ('bomba', 37.7, 40.0, [('BOMBA', 1), (' DE DESAGÜE', 0)], 200, 230),
    ('resortes', 59.1, 64.9, [('RESORTES', 1)], 60, -260),
    ('amortiguadores', 60.1, 64.9, [('AMORTIGUADORES', 1)], -120, 260),
    ('concreto', 63.5, 65.2, [('CONCRETO', 1)], -240, -200),
]

# ---------------------------------------------------------------- textos flotantes
FLOATS = [
    (0.25, 4.35, [[('¿QUÉ PASA ', 0), ('ADENTRO', 1), ('?', 0)]], 1560, 104),
    (41.35, 43.7, [[('ENJUAGUE', 1)]], 1620, 120),
    (49.2, 51.95, [[('+', 0), ('1,000', 1)], [('VUELTAS POR MINUTO', 0)]], 1640, 130),
    (65.3, 69.95, [[('NO LA LLENES ', 0), ('DE MÁS', 1)]], 1600, 96),
    (70.15, 72.7, [[('Síguenos para ver', 0)], [('más cosas… ', 0), ('por dentro.', 1)]], 1520, 82),
]

def text_w(parts, f, stroke):
    return sum(f.getlength(t) for t, _ in parts)

def draw_parts(d, x, y, parts, f, fillw, stroke, sw, anchor_center=True):
    total = text_w(parts, f, sw)
    cx = x - total / 2 if anchor_center else x
    for t, red in parts:
        d.text((cx, y), t, font=f, fill=(RED if red else fillw), stroke_width=sw, stroke_fill=stroke, anchor='ls')
        cx += f.getlength(t)
    return total

def render_text_block(lines, size, fillw, stroke, sw, max_w=1000):
    """devuelve imagen RGBA con las lineas centradas"""
    f = font(size)
    widths = [text_w(l, f, sw) for l in lines]
    mw = max(widths)
    if mw > max_w:
        size = size * max_w / mw; f = font(size)
        widths = [text_w(l, f, sw) for l in lines]; mw = max(widths)
    lh = size * 1.12
    im = Image.new('RGBA', (int(mw + 4 * sw + 20), int(lh * len(lines) + 4 * sw + size * 0.35)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        draw_parts(d, im.width / 2, 2 * sw + size * 0.95 + i * lh, l, f, fillw, stroke, sw)
    return im

_cache = {}
def cached_block(key, *a, **k):
    if key not in _cache: _cache[key] = render_text_block(*a, **k)
    return _cache[key]

def paste_scaled(base, im, cx, cy, sc, alpha):
    if sc <= 0.01 or alpha <= 0.01: return
    w, h = max(1, int(im.width * sc)), max(1, int(im.height * sc))
    im2 = im.resize((w, h), Image.LANCZOS) if abs(sc - 1) > 0.01 else im
    if alpha < 0.99:
        a = im2.getchannel('A').point(lambda v: int(v * alpha)); im2 = im2.copy(); im2.putalpha(a)
    base.alpha_composite(im2, (int(cx - w / 2), int(cy - h / 2)))

# fondo degradado azul grisaceo
def make_bg():
    g = Image.new('RGBA', (1, H))
    for y in range(H):
        u = y / (H - 1)
        u2 = u
        c = (int(198 - 58 * u2), int(208 - 52 * u2), int(222 - 44 * u2), 255)
        g.putpixel((0, y), c)
    bg = g.resize((W, H))
    # vineta suave
    v = Image.new('L', (W // 8, H // 8), 0)
    dv = ImageDraw.Draw(v)
    dv.ellipse((-W // 16, -H // 24, W // 8 + W // 16, H // 8 + H // 24), fill=255)
    v = v.filter(ImageFilter.GaussianBlur(18)).resize((W, H))
    dark = Image.new('RGBA', (W, H), (95, 105, 125, 255))
    return Image.composite(bg, dark, v.point(lambda p: int(255 - (255 - p) * 0.45)))
BG = make_bg()

def shadow_layer(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    cx, cy = sum(xs) / 4, sum(ys) / 4 + 10
    rx = (max(xs) - min(xs)) / 2 * 0.95; ry = max((max(ys) - min(ys)) / 2 * 0.8, 20)
    if rx > 3000 or ry > 3000 or cy < -500 or cy > H + 800: return None
    s = 4
    L = Image.new('L', (W // s, H // s), 0)
    d = ImageDraw.Draw(L)
    d.ellipse(((cx - rx) / s, (cy - ry) / s, (cx + rx) / s, (cy + ry) / s), fill=120)
    L = L.filter(ImageFilter.GaussianBlur(28 / s * 1.0)).resize((W, H), Image.BILINEAR)
    lay = Image.new('RGBA', (W, H), (40, 48, 65, 0))
    lay.putalpha(L)
    return lay

def draw_label(base, d, anchor, parts, dx, dy, t, t0, t1):
    ax, ay, az = anchor
    if az < 0: return
    a = sstep(t0, t0 + 0.2, t) * (1 - sstep(t1 - 0.2, t1, t))
    if a < 0.02: return
    pop = ease_back(clamp((t - t0) / 0.3))
    lx, ly = ax + dx, ay + dy
    blk = cached_block(('lab',) + tuple(parts), [parts], 68, WHITEC, BLACK, 8, max_w=980)
    lx = clamp(lx, blk.width / 2 + 30, W - blk.width / 2 - 30)
    ly = clamp(ly, 440, H - 160)
    # linea fina hacia la pieza
    ex = lx; ey = ly + (blk.height / 2 - 12 if ay > ly else -blk.height / 2 + 12)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    k = clamp((t - t0) / 0.25)
    px, py = ax + (ex - ax) * k, ay + (ey - ay) * k
    dl.line((ax, ay, px, py), fill=BLACK, width=9)
    dl.line((ax, ay, px, py), fill=WHITEC, width=4)
    dl.ellipse((ax - 11, ay - 11, ax + 11, ay + 11), fill=BLACK)
    dl.ellipse((ax - 6, ay - 6, ax + 6, ay + 6), fill=(255, 215, 0, 255))
    if a < 0.99:
        lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
    base.alpha_composite(lay)
    paste_scaled(base, blk, lx, ly, pop, a)

def draw_mark(base, kind, t, t0, t1, cx, cy):
    a = sstep(t0, t0 + 0.15, t) * (1 - sstep(t1 - 0.2, t1, t))
    if a < 0.02: return
    sc = ease_back(clamp((t - t0) / 0.35))
    S = 260
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((10, 10, S - 10, S - 10), fill=(255, 255, 255, 255), outline=BLACK, width=8)
    if kind == 'x':
        for (x0, y0, x1, y1) in ((70, 70, S - 70, S - 70), (S - 70, 70, 70, S - 70)):
            d.line((x0, y0, x1, y1), fill=BLACK, width=46)
            d.line((x0, y0, x1, y1), fill=(230, 30, 35, 255), width=32)
    else:
        pts = [(62, 135), (108, 182), (198, 80)]
        d.line(pts, fill=BLACK, width=46, joint='curve')
        d.line(pts, fill=(40, 185, 70, 255), width=32, joint='curve')
    paste_scaled(base, im, cx, cy, sc, a)

def compose(f):
    t = f / FPS
    base = BG.copy()
    mp = os.path.join(FR, 'm%05d.json' % f)
    meta = json.load(open(mp)) if os.path.exists(mp) else None
    if meta:
        sl = shadow_layer(meta['shadow'])
        if sl: base.alpha_composite(sl)
    fp = os.path.join(FR, 'f%05d.png' % f)
    if os.path.exists(fp):
        base.alpha_composite(Image.open(fp).convert('RGBA'))
    d = ImageDraw.Draw(base)
    if meta:
        for key, t0, t1, parts, dx, dy in LABELS:
            if t0 - 0.1 <= t <= t1 + 0.1:
                draw_label(base, d, meta[key], parts, dx, dy, t, t0, t1)
    # marcas X / check
    draw_mark(base, 'x', t, 65.9, 67.35, 830, 560)
    draw_mark(base, 'v', t, 67.9, 69.95, 830, 560)
    # textos flotantes
    for t0, t1, lines, y, size in FLOATS:
        if t0 <= t <= t1:
            a = sstep(t0, t0 + 0.2, t) * (1 - sstep(t1 - 0.25, t1, t))
            sc = ease_back(clamp((t - t0) / 0.4))
            blk = cached_block(('fl', t0), lines, size, WHITEC, BLACK, 9)
            bob = 10 * math.sin((t - t0) * 2.6)
            paste_scaled(base, blk, W / 2, y + bob, sc, a)
    # subtitulos (arriba al centro)
    for s in SUBS:
        if s['t0'] <= t <= s['t1']:
            u = clamp((t - s['t0']) / 0.16)
            sc = 0.75 + 0.25 * ease_back(u)
            a = clamp(u * 1.5) * (1 - sstep(s['t1'] - 0.08, s['t1'], t))
            parts = [(w + (' ' if i < len(s['toks']) - 1 else ''), r) for i, (w, r) in enumerate(s['toks'])]
            blk = cached_block(('sub', s['t0']), [parts], 88, BLACK, WHITEC, 11, max_w=1000)
            paste_scaled(base, blk, W / 2, 270 - 18 * (1 - u), sc, a)
    # fundido a negro
    fb = sstep(71.85, 72.6, t)
    if fb > 0:
        base = Image.blend(base, Image.new('RGBA', (W, H), (0, 0, 0, 255)), fb)
    return base.convert('RGB')

if __name__ == '__main__':
    frames = ONLY if ONLY else range(NFR)
    out = sys.stdout.buffer
    for f in frames:
        im = compose(f)
        if PREVIEW_DIR:
            im.save(os.path.join(PREVIEW_DIR, 'c%05d.png' % f))
        else:
            out.write(im.tobytes())
