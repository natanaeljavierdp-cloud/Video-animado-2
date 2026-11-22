# Compositor 2D: fondo, sombra, render 3D, etiquetas, marcas, subtítulos -> ffmpeg
import json, glob, math, sys, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from multiprocessing import Pool

W, H, FPS = 1080, 1920, 30
DUR = 59.40
NFR = int(round(DUR * FPS))
RDIR = sys.argv[1] if len(sys.argv) > 1 else '/tmp/claude-0/w/R'
ADIR = sys.argv[2] if len(sys.argv) > 2 else RDIR
FB = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
RED = (235, 28, 36)
_fc = {}
def font(sz):
    if sz not in _fc: _fc[sz] = ImageFont.truetype(FB, sz)
    return _fc[sz]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def sm(x): x = clamp(x); return x * x * x * (x * (x * 6 - 15) + 10)
def ramp(t, a, b): return sm((t - a) / (b - a))
def back_out(x, s=1.7):
    x = clamp(x); x -= 1; return 1 + x * x * ((s + 1) * x + s)

# ---------------------------------------------------------------- datos
A = {}
for f in glob.glob(os.path.join(ADIR, 'anch_*.json')):
    A.update({int(k): v for k, v in json.load(open(f)).items()})

# subtítulos: (inicio, texto, palabras clave en rojo)
SUBS = [
    (0.00, '¿ALGUNA VEZ', []), (0.60, 'TE HAS PREGUNTADO', []), (1.54, 'QUÉ PASA DENTRO', ['DENTRO']),
    (2.44, 'DE UNA CERRADURA', ['CERRADURA']), (3.32, 'CUANDO METES LA LLAVE?', ['LLAVE?']),
    (4.90, 'VAMOS POR DENTRO.', ['DENTRO.']),
    (6.12, 'POR FUERA', []), (6.62, 'PARECE SIMPLE,', ['SIMPLE,']), (7.54, 'PERO POR DENTRO', []),
    (8.50, 'HAY UN CILINDRO', ['CILINDRO']), (9.38, 'QUE GIRA,', ['GIRA,']), (10.22, 'METIDO DENTRO', []),
    (10.92, 'DE OTRO', []), (11.36, 'QUE NO SE MUEVE.', ['MUEVE.']),
    (12.70, 'ATRAVESANDO LOS DOS', []), (13.68, 'HAY CINCO FILAS', ['CINCO']), (14.84, 'DE PINES:', ['PINES:']),
    (15.66, 'UN PIN DE ABAJO,', ['ABAJO,']), (16.82, 'UN PIN DE ARRIBA', ['ARRIBA']), (17.60, 'Y UN RESORTE', ['RESORTE']),
    (18.54, 'QUE LOS EMPUJA', ['EMPUJA']), (19.34, 'HACIA ABAJO.', []),
    (20.30, 'SIN LLAVE,', ['LLAVE,']), (21.12, 'LOS PINES DE ARRIBA', ['ARRIBA']), (21.88, 'QUEDAN CRUZADOS', ['CRUZADOS']),
    (22.82, 'ENTRE LOS DOS CILINDROS.', []), (24.24, 'POR ESO EL CILINDRO', []), (25.34, 'NO PUEDE GIRAR.', ['NO', 'GIRAR.']),
    (26.50, 'CUANDO METES LA LLAVE,', ['LLAVE,']), (27.98, 'CADA DIENTE', ['DIENTE']), (28.46, 'EMPUJA UNA FILA', []),
    (29.62, 'DE PINES', ['PINES']), (30.02, 'HASTA UNA ALTURA EXACTA.', ['EXACTA.']),
    (31.04, 'CON LA LLAVE CORRECTA,', ['CORRECTA,']), (33.14, 'LA UNIÓN', ['UNIÓN']), (33.48, 'ENTRE CADA PIN', []),
    (34.28, 'DE ABAJO', []), (34.72, 'Y EL DE ARRIBA', []), (35.50, 'QUEDA JUSTO', ['JUSTO']), (36.28, 'EN LA LÍNEA', ['LÍNEA']),
    (36.82, 'DONDE SE JUNTAN', []), (37.64, 'LOS DOS CILINDROS.', []),
    (39.02, 'AHORA NADA LO TRABA:', ['NADA']), (40.50, 'EL CILINDRO GIRA,', ['GIRA,']), (41.72, 'UNA PIEZA DE ATRÁS', []),
    (42.54, 'JALA EL PESTILLO…', ['PESTILLO…']), (43.54, 'Y LA PUERTA', []), (44.46, 'SE ABRE.', ['ABRE.']),
    (45.32, '¿Y CON UNA LLAVE', []), (46.30, 'EQUIVOCADA?', ['EQUIVOCADA?']), (47.42, 'BASTA UN SOLO PIN', ['SOLO']),
    (48.54, 'A LA ALTURA INCORRECTA,', ['INCORRECTA,']), (49.66, 'Y EL CILINDRO', []), (50.50, 'NO SE MUEVE.', ['NO', 'MUEVE.']),
    (51.52, 'POR ESO CADA LLAVE', []), (52.66, 'TIENE SUS DIENTES', ['DIENTES']), (53.52, 'DISTINTOS:', ['DISTINTOS:']),
    (54.45, 'HAY MILES', ['MILES']), (54.94, 'DE COMBINACIONES', ['COMBINACIONES']), (55.80, 'POSIBLES.', []),
    (56.80, 'SÍGUENOS', ['SÍGUENOS']), (57.14, 'PARA VER MÁS COSAS…', []), (58.72, 'POR DENTRO.', ['DENTRO.']),
]
SUB_END = {38.08 + 0.6: None}
PAUSE_ENDS = [(4.38, 4.90), (12.06, 12.70), (19.64, 20.30), (25.80, 26.50), (31.48, 31.04), (38.08, 39.02), (44.78, 45.32), (50.98, 51.52), (55.80 + 0.6, 56.80)]

# etiquetas: (texto, rojo, ancla, t0, t1, dx, dy)
LABELS = [
    ('CILINDRO QUE GIRA', ['GIRA'], 'plugface', 9.0, 12.55, 0, 330),
    ('CUERPO FIJO', ['FIJO'], 'body', 10.9, 12.55, -60, -300),
    ('PIN DE ABAJO', ['ABAJO'], 'red4', 15.6, 20.15, 120, 420),
    ('PIN DE ARRIBA', ['ARRIBA'], 'blue2', 16.8, 20.15, -120, -380),
    ('RESORTE', ['RESORTE'], 'spring0', 17.9, 20.15, 120, -330),
    ('BLOQUEADO', ['BLOQUEADO'], 'plugface', 25.25, 26.4, 0, 330),
    ('DIENTES DE LA LLAVE', ['DIENTES'], 'keyteeth', 27.9, 31.2, 0, 380),
    ('PESTILLO', ['PESTILLO'], 'latch', 41.9, 43.1, 120, -300),
]

# ---------------------------------------------------------------- fondo
yy = np.linspace(0, 1, H)[:, None]
top = np.array([214, 224, 236]); bot = np.array([128, 146, 170])
g = top + (bot - top) * (yy ** 0.9)[..., None]
xx = np.linspace(-1, 1, W)[None, :]
vig = 1 - 0.10 * (xx ** 2)[..., None]
BG = Image.fromarray(np.clip(g * vig, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')

def text_runs(txt, reds):
    words = txt.split(' ')
    return [(w, w in reds) for w in words]

def draw_rich(img, cx, cy, txt, reds, size, fill=(20, 20, 20), redc=RED, stroke=(255, 255, 255), sw=10, alpha=1.0, scale=1.0, glow=True):
    sz = max(8, int(size * scale))
    f = font(sz)
    runs = text_runs(txt, reds)
    sp = f.getlength(' ')
    widths = [f.getlength(w) for w, _ in runs]
    tw = sum(widths) + sp * (len(runs) - 1)
    if tw > W - 70 and scale == 1.0:
        return draw_rich(img, cx, cy, txt, reds, size * (W - 70) / tw, fill, redc, stroke, sw, alpha, 1.0, glow)
    pad = sw * 3 + 20
    layer = Image.new('RGBA', (int(tw) + 2 * pad, sz + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = pad
    sws = max(2, int(sw * scale))
    for (w, isr), ww in zip(runs, widths):
        d.text((x, pad), w, font=f, fill=(redc if isr else fill), stroke_width=sws, stroke_fill=stroke)
        x += ww + sp
    if glow:
        a = layer.split()[3].filter(ImageFilter.GaussianBlur(sws * 1.2))
        halo = Image.new('RGBA', layer.size, stroke + (0,)); halo.putalpha(a.point(lambda v: min(255, v * 1.6)))
        halo.alpha_composite(layer); layer = halo
    if alpha < 1:
        layer.putalpha(layer.split()[3].point(lambda v: int(v * alpha)))
    asc = f.getbbox('ÁG')[1]
    img.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - (sz + 2 * pad) / 2 - asc / 2 + 4)))
    return tw * 1.0, sz

def subtitle(img, t):
    cur = None
    for i, (s, txt, reds) in enumerate(SUBS):
        if t >= s: cur = i
    if cur is None: return
    s, txt, reds = SUBS[cur]
    nxt = SUBS[cur + 1][0] if cur + 1 < len(SUBS) else DUR
    end = nxt
    for a, b in PAUSE_ENDS:
        if s < a < nxt and b == nxt: end = a + 0.35
    if t > end: return
    k = (t - s) / 0.16
    sc = 0.72 + 0.28 * back_out(k, 2.2)
    al = clamp(k * 1.5) * (1 - clamp((t - (end - 0.08)) / 0.08))
    draw_rich(img, W / 2, 255, txt, reds, 92, alpha=al, scale=sc)

def P(a, key):
    v = a.get(key); return (v[0], v[1]) if v else None

def label(img, d, a, t, txt, reds, key, t0, t1, dx, dy):
    if not (t0 <= t <= t1 + 0.25): return
    p = P(a, key)
    if p is None: return
    k = ramp(t, t0, t0 + 0.35) * (1 - ramp(t, t1, t1 + 0.25))
    f = font(46); tw = f.getlength(txt); th = 46
    lx = clamp(p[0] + dx, tw / 2 + 24, W - tw / 2 - 24)
    ly = clamp(p[1] + dy, 430, H - 90)
    # línea fina hacia la pieza
    ex, ey = lx, (ly + th * 0.75) if dy < 0 else (ly - th * 0.75)
    q = (p[0] + (ex - p[0]) * (1 - k * 0 ) , 0)
    gx = ex + (p[0] - ex) * ramp(t, t0 + 0.05, t0 + 0.4); gy = ey + (p[1] - ey) * ramp(t, t0 + 0.05, t0 + 0.4)
    al = int(255 * k)
    d.line([(ex, ey), (gx, gy)], fill=(0, 0, 0, al), width=7)
    d.line([(ex, ey), (gx, gy)], fill=(255, 255, 255, al), width=3)
    if ramp(t, t0 + 0.05, t0 + 0.4) > 0.95:
        d.ellipse([p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9], fill=(255, 255, 255, al), outline=(0, 0, 0, al), width=3)
    draw_rich(img, lx, ly, txt, reds, 46, fill=(255, 255, 255), redc=(255, 40, 40), stroke=(0, 0, 0), sw=6, alpha=k, scale=0.85 + 0.15 * back_out(k), glow=False)

def check(d, x, y, r, al, col=(34, 197, 94)):
    a = int(255 * al)
    d.ellipse([x - r - 4, y - r - 4, x + r + 4, y + r + 4], fill=(0, 0, 0, a))
    d.ellipse([x - r, y - r, x + r, y + r], fill=col + (a,))
    pts = [(x - r * 0.5, y + r * 0.02), (x - r * 0.12, y + r * 0.42), (x + r * 0.55, y - r * 0.42)]
    d.line(pts, fill=(255, 255, 255, a), width=max(3, int(r * 0.28)), joint='curve')

def xmark(d, x, y, r, al, w=None):
    a = int(255 * al); w = w or int(r * 0.32)
    for col, ww in (((0, 0, 0), w + 10), ((235, 28, 36), w)):
        d.line([(x - r, y - r), (x + r, y + r)], fill=col + (a,), width=ww)
        d.line([(x - r, y + r), (x + r, y - r)], fill=col + (a,), width=ww)

def sparkle(d, x, y, r, al):
    a = int(255 * al)
    for rot, rr in ((0, r), (45, r * 0.55)):
        pts = []
        for k in range(8):
            ang = math.radians(rot + k * 45)
            rad = rr if k % 2 == 0 else rr * 0.18
            pts.append((x + rad * math.cos(ang), y + rad * math.sin(ang)))
        d.polygon(pts, fill=(255, 250, 200, a))

def rrect(d, box, col, al, width=6, fill=None, rad=16):
    d.rounded_rectangle(box, radius=rad, outline=col + (int(255 * al),), width=width, fill=fill)

def pin_box(a, i, which, pad=10):
    if which == 'blue':
        t, b = P(a, 'bluetop%d' % i), P(a, 'bluebot%d' % i)
    elif which == 'red':
        t, b = P(a, 'junc%d' % i), P(a, 'redbot%d' % i)
    else:
        t, b = P(a, 'springtop%d' % i), P(a, 'redbot%d' % i)
    r = abs(P(a, 'pinr%d' % i)[0] - P(a, 'blue%d' % i)[0]) + pad
    cx = (t[0] + b[0]) / 2
    return [cx - r, min(t[1], b[1]) - pad, cx + r, max(t[1], b[1]) + pad]

def shadow_layer(a, t):
    s = Image.new('L', (W // 4, H // 4), 0)
    d = ImageDraw.Draw(s)
    att = a['attach']
    if a['door_z'] > -20:
        L, R = P(a, 'doorbotL'), P(a, 'doorbotR')
        if L and R:
            cx = (L[0] + R[0]) / 2; cy = max(L[1], R[1]) + 10; w = abs(R[0] - L[0]) * 0.65 + 40
            al = int(110 * clamp(1 + a['door_z'] / 20))
            d.ellipse([(cx - w) / 4, (cy - w * 0.09) / 4, (cx + w) / 4, (cy + w * 0.09) / 4], fill=al)
    if att < 0.6:
        L, R = P(a, 'lockbotL'), P(a, 'lockbotR')
        cx = (L[0] + R[0]) / 2; cy = max(L[1], R[1]) + 70; w = abs(R[0] - L[0]) * 0.62 + 30
        al = int(95 * (1 - att / 0.6))
        d.ellipse([(cx - w) / 4, (cy - w * 0.12) / 4, (cx + w) / 4, (cy + w * 0.12) / 4], fill=al)
    s = s.filter(ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR)
    sh = Image.new('RGBA', (W, H), (30, 40, 60, 0)); sh.putalpha(s)
    return sh

def frame(f):
    t = f / FPS
    a = A[f]
    img = BG.copy()
    img.alpha_composite(shadow_layer(a, t))
    rp = os.path.join(RDIR, 'f%05d.png' % f)
    if os.path.exists(rp):
        img.alpha_composite(Image.open(rp).convert('RGBA'))
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    # escena 3: filas resaltadas una por una
    for i in range(5):
        c = 14.15 + 0.3 * i
        x = (t - c) / 0.28
        p = math.exp(-x * x * 2.5) if -2 < x < 2 else 0.0
        if t > 15.6: p = 0
        if p > 0.02:
            rrect(d, pin_box(a, i, 'col', 16), (255, 220, 0), p, 7, fill=(255, 230, 0, int(60 * p)))
    # escena 4: borde rojo en pines azules cruzados
    for i in range(5):
        t0 = 21.3 + 0.12 * i
        if t0 <= t <= 26.4:
            al = ramp(t, t0, t0 + 0.2) * (1 - ramp(t, 26.1, 26.4))
            rrect(d, pin_box(a, i, 'blue', 9), (235, 28, 36), al, 7)
    # X de bloqueo
    for tx in (25.1, 50.2):
        if tx <= t <= tx + 1.25:
            k = back_out((t - tx) / 0.22, 2.5); al = 1 - ramp(t, tx + 1.0, tx + 1.25)
            c = P(a, 'shear2'); xmark(d, c[0], c[1] - 10, 120 * k, al)
    # escena 6: checks verdes uno por uno con destello
    order = sorted(range(5), key=lambda i: a['junc%d' % i][0])
    for n, i in enumerate(order):
        t0 = 36.0 + 0.35 * n
        if t0 <= t <= 38.85:
            j = P(a, 'junc%d' % i)
            sp = (t - t0) / 0.35
            if sp < 1: sparkle(d, j[0], j[1], 70 * math.sin(math.pi * sp), 1 - sp * 0.5)
            al = 1 - ramp(t, 38.6, 38.85)
            k = back_out((t - t0) / 0.25, 2.2)
            check(d, j[0], j[1] - 0 - 2, 24 * k, al)
    # escena 8: una unión desalineada (fila 1) en rojo, 4 bien
    if 48.95 <= t <= 51.45:
        al = ramp(t, 48.95, 49.15) * (1 - ramp(t, 51.2, 51.45))
        for i in range(5):
            j = P(a, 'junc%d' % i)
            if i == 1:
                rrect(d, pin_box(a, i, 'red', 9), (235, 28, 36), al, 8)
                s = P(a, 'shear%d' % i)
                d.line([(j[0] - 34, j[1]), (j[0] + 34, j[1])], fill=(235, 28, 36, int(255 * al)), width=7)
                xmark(d, j[0] + 0, j[1] - 52, 20 * back_out((t - 49.0) / 0.25), al, 9)
            else:
                check(d, j[0], j[1], 17 * back_out((t - 49.0 - 0.06 * i) / 0.25), al)
    # brillo de la línea amarilla al aparecer / al nombrarla
    for t0, t1 in ((20.3, 21.6), (36.25, 37.4), (47.5, 48.5)):
        if t0 <= t <= t1:
            al = math.sin(math.pi * (t - t0) / (t1 - t0))
            L, R = P(a, 'shearL'), P(a, 'shearR')
            gl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
            gd.line([L, R], fill=(255, 240, 60, int(170 * al)), width=26)
            gl = gl.filter(ImageFilter.GaussianBlur(10))
            img.alpha_composite(gl)

    # etiquetas
    img.alpha_composite(ov)
    ov2 = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d2 = ImageDraw.Draw(ov2)
    for L_ in LABELS:
        label(ov2, d2, a, t, *L_)
    img.alpha_composite(ov2)

    # contador escena 9
    if 54.45 <= t <= 56.5:
        k = ramp(t, 54.5, 55.6)
        n = int(round(7776 * k))
        s = f'{n:,}'.replace(',', '.')
        al = ramp(t, 54.45, 54.65) * (1 - ramp(t, 56.2, 56.5))
        draw_rich(img, W / 2, 1480, s, [], 170, fill=(20, 20, 20), alpha=al, scale=0.9 + 0.1 * back_out((t - 54.45) / 0.2))
        draw_rich(img, W / 2, 1640, 'MILES DE COMBINACIONES', ['MILES'], 62, fill=(20, 20, 20), alpha=al, sw=8)

    subtitle(img, t)
    out = img.convert('RGB')
    if t > 58.7:
        k = ramp(t, 58.7, 59.35)
        out = Image.blend(out, Image.new('RGB', (W, H), (0, 0, 0)), k)
    return out.tobytes()

if __name__ == '__main__':
    mode = sys.argv[3] if len(sys.argv) > 3 else 'video'
    if mode == 'stills':
        for f in [int(x) for x in sys.argv[4].split(',')]:
            Image.frombytes('RGB', (W, H), frame(f)).save(os.environ.get('SDIR','/tmp/claude-0/w/S')+'/s%05d.jpg' % f, quality=88)
        sys.exit()
    out = sys.argv[4] if len(sys.argv) > 4 else '/tmp/claude-0/w/video_noaudio.mp4'
    p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(frame, range(NFR), chunksize=4)):
            p.stdin.write(b)
            if i % 100 == 0: print('comp', i, flush=True)
    p.stdin.close(); p.wait()
    print('done')
