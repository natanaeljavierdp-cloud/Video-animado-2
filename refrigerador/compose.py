# Composicion 2D: fondo degradado, sombra, render 3D, etiquetas, textos y subtitulos.
import json, sys, os, math, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FB = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
RED = (232, 28, 36); WHITE = (255, 255, 255); BLACK = (0, 0, 0)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def sstep(a, b, t):
    x = clamp((t - a) / (b - a)); return x * x * (3 - 2 * x)
def back_out(x, s=2.0):
    x = clamp(x) - 1; return 1 + x * x * ((s + 1) * x + s)

_fonts = {}
def font(sz):
    if sz not in _fonts: _fonts[sz] = ImageFont.truetype(FB, sz)
    return _fonts[sz]

# ------------------------------------------------ subtitulos (* = palabra clave)
CHUNKS = """Tu refrigerador|no fabrica *frío,|lo que hace es|sacar el *calor|de adentro|y botarlo por detrás.|Mira cómo.|Por dentro tiene|un *circuito *cerrado|de tubos|y por ellos viaja|un líquido especial,|el *refrigerante.|Dentro del refrigerador,|el *refrigerante pasa|por unos tubos|llamados *evaporador.|Ahí *hierve|a muy baja temperatura|y al evaporarse|*absorbe el *calor|de tu comida.|Ese gas,|ya cargado de *calor,|viaja hasta el *compresor,|el motor que está abajo,|en la parte de atrás.|El *compresor|lo *aprieta con fuerza|y al apretarlo|se *calienta todavía más.|Luego pasa por|la parrilla negra|de atrás,|el *condensador.|Ahí suelta el *calor|al aire de tu cocina|y vuelve a ser *líquido,|por eso la parte|de atrás|se siente *tibia.|Después cruza|un tubo *finito|que le baja|la *presión de golpe.|El refrigerante|se *enfría muchísimo|y regresa adentro|listo para atrapar|más *calor.|Un *termostato|vigila la temperatura.|Cuando ya está|bien *frío,|*apaga el compresor.|Cuando sube,|lo vuelve a *encender.|Ese es el *zumbido|que escuchas|de vez en cuando.|Por eso no conviene|pegarlo a la *pared.|El *calor necesita|*espacio para salir.""".split('|')

def build_subs():
    words = json.load(open(os.path.join(HERE, 'words.json')))
    words = words[:-7]  # "Síguenos para ver más cosas. Por dentro." -> texto de cierre
    subs = []; k = 0
    for ch in CHUNKS:
        toks = ch.split()
        st = words[k][1]; en = words[k + len(toks) - 1][2]
        for j, tk in enumerate(toks):
            a = tk.strip('*,.').lower(); b = words[k + j][0].strip(',.').lower()
            if a != b and not (a == 'apaga' and b == 'apague'):
                raise SystemExit('desfase %s %s' % (a, b))
        k += len(toks)
        subs.append([st, en, toks])
    assert k == len(words), (k, len(words))
    for i, s in enumerate(subs):
        nxt = subs[i + 1][0] if i + 1 < len(subs) else 68.6
        s[1] = min(nxt, s[1] + 0.45)
        if nxt - s[1] < 0.25: s[1] = nxt
    return subs
SUBS = build_subs()

def render_words(toks, sz, fill_default, stroke_col, stroke_w, keyword_col=RED):
    f = font(sz)
    parts = []
    for tk in toks:
        kw = tk.startswith('*'); txt = tk.lstrip('*')
        parts.append((txt, keyword_col if kw else fill_default))
    space = f.getlength(' ')
    widths = [f.getlength(p[0]) for p in parts]
    tw = int(sum(widths) + space * (len(parts) - 1)) + 2 * stroke_w + 8
    asc, desc = f.getmetrics()
    th = asc + desc + 2 * stroke_w + 8
    im = Image.new('RGBA', (tw, th), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = stroke_w + 4
    for (txt, col), w in zip(parts, widths):
        d.text((x, stroke_w + 4), txt, font=f, fill=col, stroke_width=stroke_w, stroke_fill=stroke_col)
        x += w + space
    return im

def paste_center(canvas, im, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if alpha < 1.0:
        a = im.getchannel('A').point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def lines_block(lines, sz, fill, stroke, sw, gap=6):
    ims = [render_words(l.split(), sz, fill, stroke, sw) for l in lines]
    w = max(i.width for i in ims); h = sum(i.height for i in ims) + gap * (len(ims) - 1)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0)); y = 0
    for i in ims:
        out.alpha_composite(i, ((w - i.width) // 2, y)); y += i.height + gap
    return out

_cache = {}
def cached(key, fn):
    if key not in _cache: _cache[key] = fn()
    return _cache[key]

def draw_subs(canvas, t):
    if t >= 68.6: return
    for st, en, toks in SUBS:
        if st - 0.02 <= t < en:
            im = cached(('sub', st), lambda: render_words(toks, 84, BLACK, WHITE, 11))
            if im.width > W - 60:
                im = cached(('subfit', st), lambda: im.resize((W - 60, int(im.height * (W - 60) / im.width)), Image.LANCZOS))
            u = (t - st) / 0.16
            sc = 0.72 + 0.28 * back_out(u)
            al = clamp(u * 1.6) * (1 - sstep(en - 0.08, en, t))
            paste_center(canvas, im, W / 2, 285 - 18 * (1 - clamp(u)), sc, al)
            break

# ------------------------------------------------ etiquetas con linea
LABELS = [  # partes, ancla, t0, t1, posicion (dx,dy) relativa al ancla
    (['*REFRIGERANTE'], 'refrig', 12.7, 15.0, (-300, 330)),
    (['*EVAPORADOR'], 'evap', 17.8, 24.2, (-60, 470)),
    (['*COMPRESOR'], 'comp', 27.1, 35.3, (-40, -420)),
    (['*CONDENSADOR'], 'cond', 37.9, 45.2, (0, 560)),
    (['BAJA', 'LA', '*PRESIÓN'], 'cap', 47.2, 50.6, (40, 520)),
    (['*TERMOSTATO'], 'termo', 54.1, 63.4, (-60, -330)),
]
def draw_labels(canvas, t, meta):
    d = ImageDraw.Draw(canvas)
    for parts, key, t0, t1, (dx, dy) in LABELS:
        if not (t0 <= t < t1): continue
        ax, ay, az = meta[key]
        if az <= 0: continue
        al = sstep(t0, t0 + 0.25, t) * (1 - sstep(t1 - 0.25, t1, t))
        im = cached(('lab', key), lambda: render_words(parts, 76, WHITE, BLACK, 9))
        lx = clamp(ax + dx, im.width / 2 + 30, W - im.width / 2 - 30)
        ly = clamp(ay + dy, 470, 1780)
        u = clamp((t - t0) / 0.3)
        # linea: del ancla al borde del texto
        ex = lx; ey = ly - im.height / 2 + 10 if ly > ay else ly + im.height / 2 - 10
        px = ax + (ex - ax) * u; py = ay + (ey - ay) * u
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
        ld.line([(ax, ay), (px, py)], fill=(0, 0, 0, 255), width=9)
        ld.line([(ax, ay), (px, py)], fill=(255, 255, 255, 255), width=4)
        r = 11; ld.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=4)
        if al < 1:
            layer.putalpha(layer.getchannel('A').point(lambda v: int(v * al)))
        canvas.alpha_composite(layer)
        sc = 0.6 + 0.4 * back_out(clamp((t - t0 - 0.1) / 0.25))
        if t - t0 > 0.1:
            paste_center(canvas, im, lx, ly, sc, al)

# ------------------------------------------------ textos flotantes
def draw_float(canvas, t):
    if 0.9 <= t < 6.6:
        im = cached('f1', lambda: render_words(['*NO', 'fabrica', 'frío'], 104, WHITE, BLACK, 11))
        u = (t - 0.9) / 0.3
        paste_center(canvas, im, W / 2, 1600 + 8 * math.sin(t * 2.2), 0.6 + 0.4 * back_out(u),
                     clamp(u) * (1 - sstep(6.3, 6.6, t)))
    if 66.1 <= t < 68.6:
        im = cached('f2', lambda: render_words(['DÉJALE', '*ESPACIO'], 104, WHITE, BLACK, 11))
        u = (t - 66.1) / 0.3
        paste_center(canvas, im, W / 2, 1600 + 8 * math.sin(t * 2.2), 0.6 + 0.4 * back_out(u),
                     clamp(u) * (1 - sstep(68.3, 68.6, t)))
    if t >= 68.75:
        im = cached('f3', lambda: lines_block(['Síguenos para ver', 'más cosas…', '*por *dentro.'], 92, WHITE, BLACK, 10))
        u = (t - 68.75) / 0.35
        paste_center(canvas, im, W / 2, 330, 0.6 + 0.4 * back_out(u), clamp(u))

# ------------------------------------------------ fondo y sombra
def background():
    y = np.linspace(0, 1, H)[:, None]
    top = np.array([214, 224, 236], np.float32); bot = np.array([150, 166, 186], np.float32)
    g = top * (1 - y[..., None]) + bot * y[..., None]
    g = np.broadcast_to(g, (H, W, 3)).copy()
    # vineta suave
    xx = np.linspace(-1, 1, W)[None, :]; yy = np.linspace(-1, 1, H)[:, None]
    v = 1 - 0.10 * (xx ** 2 + 0.6 * yy ** 2)
    g *= v[..., None]
    return Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert('RGBA')
BG = background()

def draw_shadow(canvas, sh):
    if any(p[2] <= 0.05 for p in sh): return
    pts = [(p[0], p[1]) for p in sh]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    if max(xs) - min(xs) > 2.2 * W: return
    s = 4
    m = Image.new('L', (W // s, H // s), 0)
    ImageDraw.Draw(m).polygon([(x / s, y / s) for x, y in pts], fill=110)
    m = m.filter(ImageFilter.GaussianBlur(28 / s)).resize((W, H), Image.BILINEAR)
    sh_img = Image.new('RGBA', (W, H), (40, 52, 70, 0)); sh_img.putalpha(m)
    canvas.alpha_composite(sh_img)

def frame(f, rdir, meta):
    t = f / FPS
    canvas = BG.copy()
    draw_shadow(canvas, meta['shadow'])
    r = Image.open(os.path.join(rdir, 'f%05d.png' % f)).convert('RGBA')
    canvas.alpha_composite(r)
    draw_labels(canvas, t, meta)
    draw_float(canvas, t)
    draw_subs(canvas, t)
    out = canvas.convert('RGB')
    fade = sstep(70.65, 71.2, t)
    if fade > 0:
        out = Image.blend(out, Image.new('RGB', (W, H), (0, 0, 0)), fade)
    return out

def load_meta(rdir):
    meta = {}
    for fn in glob.glob(os.path.join(rdir, 'meta_*.json')):
        for k, v in json.load(open(fn)).items(): meta[int(k)] = v
    return meta

if __name__ == '__main__':
    rdir = sys.argv[1]; mode = sys.argv[2]
    meta = load_meta(rdir)
    if mode == 'stills':
        outd = sys.argv[3]; os.makedirs(outd, exist_ok=True)
        for f in sorted(meta):
            if os.path.exists(os.path.join(rdir, 'f%05d.png' % f)):
                frame(f, rdir, meta[f]).save(os.path.join(outd, 'c%05d.png' % f))
    else:  # video: escribe rgb crudo a stdout
        n = int(sys.argv[3])
        for f in range(n):
            sys.stdout.buffer.write(frame(f, rdir, meta[f]).tobytes())
