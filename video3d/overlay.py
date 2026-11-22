"""Composite rendered frames: gradient studio background, floor shadow, labels,
subtitles, counters, fade; pipe to ffmpeg."""
import json, glob, math, os, sys, subprocess
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FR = os.environ.get('FRAMES', os.path.join(HERE, 'frames'))
W, H, FPS = 1080, 1920, 30
DUR = 84.43
NF = int(math.ceil(DUR * FPS))
FONT = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
RED = (235, 30, 38)
_fonts = {}


def font(sz):
    if sz not in _fonts:
        _fonts[sz] = ImageFont.truetype(FONT, sz)
    return _fonts[sz]


def clamp(x, a, b):
    return max(a, min(b, x))


def ramp(t, a, b):
    return clamp((t - a) / (b - a), 0, 1) if b != a else float(t >= b)


def smooth(x):
    x = clamp(x, 0, 1)
    return x * x * (3 - 2 * x)


def back_out(x, s=1.70158):
    x = clamp(x, 0, 1) - 1
    return x * x * ((s + 1) * x + s) + 1


# ------------------------------------------------------------------ subtitles
WORDS = json.load(open(os.path.join(HERE, 'words.json')))
CHUNKS = [("*BULIN 47*", 2), ("acaba de comprarse", 3), ("un *Lamborghini*", 2), ("*Huracán Tecnica*", 2), ("Pero...", 1),
          ("¿qué tiene por dentro", 4), ("esta *máquina*?", 2), ("¡Vamos por *dentro*!", 3),
          ("El *motor* no va", 4), ("*adelante*:", 1), ("va *detrás*", 2), ("de los *asientos*,", 3), ("en el *centro*", 3),
          ("del carro.", 2), ("Así el *peso*", 3), ("queda *equilibrado*", 2), ("y el carro se", 4), ("*agarra* mejor", 2),
          ("en las *curvas*.", 3),
          ("Es un *V10*:", 3), ("*10* cilindros,", 2), ("*sin turbo*,", 2), ("con *640*", 2), ("*caballos* de fuerza.", 3),
          ("El *aire* entra", 3), ("por estas *tomas*", 3), ("*laterales*,", 1), ("se mezcla con", 3), ("*gasolina*,", 1),
          ("una *chispa*", 2), ("lo *enciende*...", 2), ("y cada *explosión*", 3), ("empuja un *pistón*.", 3),
          ("Esos *pistones*", 2), ("hacen girar", 2), ("el *cigüeñal*,", 2), ("que le pasa", 3), ("la *fuerza*", 2),
          ("a una *caja*", 3), ("de *7* cambios", 3), ("con *doble embrague*:", 3), ("mientras usas", 2), ("un cambio,", 2),
          ("el *siguiente*", 2), ("ya está *listo*.", 3), ("Por eso cambia", 3), ("en un *parpadeo*.", 3),
          ("Toda esa *fuerza*", 3), ("va *solo*", 2), ("a las ruedas", 3), ("de *atrás*.", 2), ("*Resultado*:", 1),
          ("de *0 a 100*", 4), ("en *3.2*", 3), ("*segundos*.", 1),
          ("Y ahora,", 2), ("lo que va a", 4), ("disfrutar *Bulin*.", 2), ("Las *ruedas de atrás*", 4), ("también *giran*.", 2),
          ("En la *ciudad*,", 3), ("giran *al revés*", 3), ("de las de *adelante*.", 4), ("Así da la vuelta", 4),
          ("en *menos espacio*.", 3), ("En la *autopista*,", 3), ("giran hacia", 2), ("el *mismo lado*,", 3),
          ("y el carro va", 4), ("más *estable*.", 2),
          ("Con un *botón*,", 3), ("cambia la", 2), ("*personalidad* del carro:", 3), ("*Strada*,", 1),
          ("para pasear tranquilo", 3), ("por *Santo Domingo*.", 3), ("*Sport*,", 1), ("para más *emoción*.", 3),
          ("Y *Corsa*,", 2), ("para la *pista*.", 3),
          ("Y ese *alerón*", 3), ("de atrás,", 2), ("junto con los", 3), ("*conductos*", 1), ("de la carrocería,", 3),
          ("usa el *aire*", 3), ("para *pegar* el carro", 4), ("al *piso*", 2), ("cuando va *rápido*.", 3),
          ("Para él,", 2), ("no es solo", 3), ("un carro.", 2), ("Es un *sueño*", 3), ("que empezó", 2),
          ("en *Capotillo*.", 2), ("*Síguenos*", 1), ("para ver más", 3), ("cosas...", 1), ("¡por *dentro*!", 2)]


def build_subs():
    out = []
    i = 0
    for text, n in CHUNKS:
        start = WORDS[i][0]
        end = WORDS[i + n - 1][1]
        out.append([start, end, text.upper()])
        i += n
    assert i == len(WORDS), (i, len(WORDS))
    for k in range(len(out)):
        nxt = out[k + 1][0] if k + 1 < len(out) else DUR
        out[k][1] = min(nxt, out[k][1] + 0.55) if nxt - out[k][1] > 0.6 else nxt
    out[0][0] = 0.0
    return out


SUBS = build_subs()


def parse_marked(text):
    """'*red* normal' -> list of (word, is_red)."""
    segs = []
    red = False
    for part in text.split('*'):
        if part:
            for wd in part.split(' '):
                if wd:
                    segs.append((wd, red))
        red = not red
    return segs


def draw_rich(img, segs, cx, cy, size, fill, keyfill, stroke_fill, stroke_w, scale=1.0, alpha=1.0, max_w=980):
    """Draw centered (possibly wrapped) rich text on a separate layer, scaled about its center."""
    sz = max(8, int(size * scale))
    f = font(sz)
    sw = max(1, int(stroke_w * scale))
    sp = f.getlength(' ') + sw * 1.3
    # wrap into lines
    lines, cur, cw = [], [], 0
    for wd, red in segs:
        punct = all(not ch.isalnum() for ch in wd)
        wl = f.getlength(wd) + sw * 0.6
        gap = 0 if (punct or not cur) else sp
        if cur and not punct and cw + gap + wl > max_w:
            lines.append((cur, cw))
            cur, cw, gap = [], 0, 0
        cw = cw + gap + wl
        cur.append((wd, red, wl, gap))
    if cur:
        lines.append((cur, cw))
    lh = int(sz * 1.12)
    tot = lh * len(lines)
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y = cy - tot / 2
    for ln, lw in lines:
        x = cx - lw / 2
        for wd, red, wl, gap in ln:
            x += gap
            d.text((x, y), wd, font=f, fill=keyfill if red else fill, stroke_width=sw, stroke_fill=stroke_fill)
            x += wl
        y += lh
    if alpha < 1:
        a = layer.getchannel('A').point(lambda v: int(v * alpha))
        layer.putalpha(a)
    img.alpha_composite(layer)
    return tot, max(lw for _, lw in lines)


def draw_subs(img, t):
    for s0, s1, text in SUBS:
        if s0 <= t < s1:
            k = ramp(t, s0, s0 + 0.12)
            sc = 0.82 + 0.18 * back_out(k, 2.5)
            draw_rich(img, parse_marked(text), W / 2, 300, 92, (12, 12, 14), RED, (255, 255, 255), 11, sc, min(1, k * 2.5))
            return


# ------------------------------------------------------------------ labels
# (t0, t1, text, anchor, dx, dy)  or anchor None with absolute pos (x,y)
LABELS = [
    (10.40, 13.25, "*MOTOR* CENTRAL", 'engine', 0, -330),
    (13.95, 15.15, "PESO *EQUILIBRADO*", 'balance', 0, 330),
    (17.95, 20.10, "*V10*", 'v10', -170, -330),
    (20.18, 21.30, "*SIN* TURBO", 'turbo', 170, -330),
    (24.00, 25.60, "TOMA DE *AIRE*", 'intake_L', -60, -330),
    (29.45, 31.35, "*PISTÓN*", 'piston_c', 200, 260),
    (32.94, 34.50, "*CIGÜEÑAL*", 'crank', -80, 380),
    (35.55, 37.45, "*7* CAMBIOS", 'gears', -120, 380),
    (36.56, 40.45, "DOBLE *EMBRAGUE*", 'clutch', 60, -420),
    (43.30, 45.05, "TRACCIÓN *TRASERA*", 'rear_wheel', 0, -360),
    (51.40, 53.20, "RUEDAS *TRASERAS*", 'rear_wheel', None, (540, 1560)),
    (53.45, 57.60, "CIUDAD: *GIRO AL REVÉS*", 'car_center', None, (540, 1620)),
    (58.20, 61.70, "AUTOPISTA: *MÁS ESTABLE*", 'car_center', None, (540, 1620)),
    (71.30, 76.45, "*ALERÓN*", 'wing', -40, -360),
    (72.80, 76.45, "*CONDUCTOS*", 'duct', 160, 300),
    (74.40, 76.45, "CARGA *AERODINÁMICA*", 'down', None, (540, 1680)),
]
MODES = [(64.50, 67.30, "STRADA", (40, 190, 90)), (67.36, 69.20, "SPORT", (255, 140, 20)), (69.26, 70.95, "CORSA", (235, 35, 40))]


def draw_label(img, t, lab, anchors):
    t0, t1, text, an, dx, dy = lab
    if not (t0 <= t < t1) or an not in anchors:
        return
    ax, ay, az = anchors[an]
    if az <= 0:
        return
    k = back_out(ramp(t, t0, t0 + 0.22), 2.0)
    fade = 1 - smooth(ramp(t, t1 - 0.18, t1))
    if dx is None:
        lx, ly = dy
    else:
        lx, ly = ax + dx, ay + dy
    lx = clamp(lx, 200, W - 200)
    ly = clamp(ly, 470, H - 140)
    d = ImageDraw.Draw(img)
    # leader line (grows), with small dot on the part
    lk = smooth(ramp(t, t0, t0 + 0.25))
    ex, ey = ax + (lx - ax) * lk, ay + (ly - ay) * lk
    col = (255, 255, 255, int(255 * fade))
    blk = (0, 0, 0, int(255 * fade))
    d.line([(ax, ay), (ex, ey)], fill=blk, width=7)
    d.line([(ax, ay), (ex, ey)], fill=col, width=3)
    r = 9
    d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=col, outline=blk, width=3)
    segs = parse_marked(text)
    draw_rich(img, segs, lx, ly, 62, (255, 255, 255), RED, (0, 0, 0), 7, max(0.05, k), fade, max_w=900)


def draw_mode(img, t):
    for t0, t1, name, col in MODES:
        if t0 <= t < t1:
            k = back_out(ramp(t, t0, t0 + 0.25), 2.2)
            fade = 1 - smooth(ramp(t, t1 - 0.15, t1))
            draw_rich(img, [(name, True)], W / 2, 560, 120, col, col, (255, 255, 255), 10, max(0.05, k), fade)


def draw_counter(img, t):
    a, b = 21.36, 23.75
    if not (a <= t < b):
        return
    v = int(round(640 * smooth(ramp(t, a, a + 1.25))))
    k = back_out(ramp(t, a, a + 0.25), 2.0)
    fade = 1 - smooth(ramp(t, b - 0.2, b))
    pop = 1 + 0.12 * math.sin(math.pi * ramp(t, a + 1.25, a + 1.55))
    draw_rich(img, [(str(v), True), ('CV', False)], W / 2, 1560, 150, (255, 255, 255), RED, (0, 0, 0), 9, k * pop, fade)


def draw_gauges(img, t):
    a, b = 45.40, 49.0
    if not (a - 0.3 <= t < b):
        return
    k = back_out(ramp(t, a - 0.3, a), 1.6)
    fade = 1 - smooth(ramp(t, b - 0.3, b))
    ts = clamp((t - a) / 2.6 * 3.2, 0, 3.2)
    kmh = 100 * ts / 3.2
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # speedometer (left)
    cx, cy, R = 290, 1470, 190
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(255, 255, 255, 235), outline=(0, 0, 0, 255), width=8)
    for i in range(11):
        ang = math.radians(220 - i * 26)
        r1, r2 = R - 18, R - (48 if i % 5 == 0 else 34)
        d.line([(cx + r1 * math.cos(ang), cy - r1 * math.sin(ang)), (cx + r2 * math.cos(ang), cy - r2 * math.sin(ang))], fill=(0, 0, 0, 255), width=6)
    ang = math.radians(220 - kmh / 100 * 260)
    d.line([(cx, cy), (cx + (R - 40) * math.cos(ang), cy - (R - 40) * math.sin(ang))], fill=RED + (255,), width=12)
    d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=(0, 0, 0, 255))
    f = font(70)
    txt = '%d' % int(round(kmh))
    d.text((cx, cy + 95), txt, font=f, fill=(0, 0, 0, 255), anchor='mm')
    d.text((cx, cy + 148), 'km/h', font=font(34), fill=(0, 0, 0, 255), anchor='mm')
    # stopwatch (right)
    sx, sy, SR = 790, 1470, 170
    d.rectangle([sx - 30, sy - SR - 50, sx + 30, sy - SR + 4], fill=(0, 0, 0, 255))
    d.ellipse([sx - SR, sy - SR, sx + SR, sy + SR], fill=(255, 255, 255, 235), outline=(0, 0, 0, 255), width=8)
    ang = math.radians(90 - ts / 3.2 * 360)
    d.line([(sx, sy), (sx + (SR - 30) * math.cos(ang), sy - (SR - 30) * math.sin(ang))], fill=(0, 0, 0, 255), width=8)
    done = ts >= 3.2
    pk = back_out(ramp(t, a + 2.6, a + 2.85), 3.0) if done else 0
    fs = int(66 * (1 + 0.35 * math.sin(math.pi * ramp(t, a + 2.6, a + 2.95)))) if done else 66
    d.text((sx, sy + 105), ('%.1f s' % ts), font=font(fs), fill=(RED if done else (0, 0, 0)) + (255,), anchor='mm', stroke_width=4 if done else 0, stroke_fill=(255, 255, 255, 255))
    # scale in/out about center bottom
    sc = max(0.05, k)
    if sc < 0.999:
        layer = layer.resize((int(W * sc), int(H * sc)))
        L2 = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        L2.paste(layer, (int(540 - 540 * sc), int(1470 - 1470 * sc)))
        layer = L2
    if fade < 1:
        layer.putalpha(layer.getchannel('A').point(lambda v: int(v * fade)))
    img.alpha_composite(layer)


# ------------------------------------------------------------------ background
def make_bg():
    import numpy as np
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(-1, 1, W)[None, :]
    top = np.array([214, 224, 235])
    bot = np.array([140, 158, 180])
    g = y ** 0.9
    col = top[None, None, :] * (1 - g[..., None]) + bot[None, None, :] * g[..., None]
    vig = 1 - 0.10 * (x ** 2)[..., None]
    col = col * vig
    return Image.fromarray(np.clip(col, 0, 255).astype('uint8'), 'RGB').convert('RGBA')


BG = None
META = {}


def load_meta():
    m = {}
    for f in sorted(glob.glob(os.path.join(FR, 'meta_*.json'))):
        for k, v in json.load(open(f)).items():
            m[int(k)] = v
    return m


def init():
    global BG, META
    BG = make_bg()
    META = load_meta()


def compose(f):
    t = f / FPS
    img = BG.copy()
    meta = META.get(f, {'a': {}, 'foot': [], 'studio': 0})
    # soft floor shadow in studio
    if meta.get('studio', 0) > 0.5 and meta.get('foot'):
        pts = [(p[0], p[1]) for p in meta['foot'] if p[2] > 0]
        if len(pts) == 4:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            cx, cy = sum(xs) / 4, sum(ys) / 4
            rx = (max(xs) - min(xs)) / 2 * 0.98
            ry = max(18, (max(ys) - min(ys)) / 2 * 0.98)
            sh = Image.new('L', (W, H), 0)
            ImageDraw.Draw(sh).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=95)
            sh = sh.filter(ImageFilter.GaussianBlur(max(10, ry * 0.35)))
            blk = Image.new('RGBA', (W, H), (25, 30, 40, 0))
            blk.putalpha(sh)
            img.alpha_composite(blk)
    fp = os.path.join(FR, 'f_%05d.png' % f)
    if os.path.exists(fp):
        rim = Image.open(fp).convert('RGBA')
        if rim.size != (W, H):
            rim = rim.resize((W, H))
        img.alpha_composite(rim)
    anchors = meta.get('a', {})
    for lab in LABELS:
        draw_label(img, t, lab, anchors)
    draw_mode(img, t)
    draw_counter(img, t)
    draw_gauges(img, t)
    draw_subs(img, t)
    # fade to black at the end
    fb = smooth(ramp(t, 83.55, 84.35))
    out = img.convert('RGB')
    if fb > 0:
        out = Image.blend(out, Image.new('RGB', (W, H), (0, 0, 0)), fb)
    # fade in from the first frame? (none: starts on the car)
    return out.tobytes()


if __name__ == '__main__':
    out = sys.argv[1]
    f0 = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    f1 = int(sys.argv[3]) if len(sys.argv) > 3 else NF
    step = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    if out.endswith('.png') or out.endswith('/'):
        init()
        os.makedirs(out, exist_ok=True)
        for f in range(f0, f1, step):
            Image.frombytes('RGB', (W, H), compose(f)).save(os.path.join(out, 'c_%05d.png' % f))
        sys.exit()
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', out],
                          stdin=subprocess.PIPE)
    with Pool(4, initializer=init) as pool:
        for i, b in enumerate(pool.imap(compose, range(f0, f1), chunksize=4)):
            ff.stdin.write(b)
            if i % 300 == 0:
                print('composited', i, flush=True)
    ff.stdin.close()
    ff.wait()
