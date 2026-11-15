# -*- coding: utf-8 -*-
"""Capital Curioso - Dominicanos varados por la falla de la FAA.
Video vertical 1080x1920 @30fps. Dibuja cada cuadro con Skia y lo envia a ffmpeg.

Uso: python3 render.py <dir_imagenes> <words.json> <geo.json> <salida.mp4> [t_inicio t_fin | --frames t1,t2,...]
"""
import json, math, os, subprocess, sys
import numpy as np
import skia
from PIL import Image, ImageFilter, ImageEnhance

W, H, FPS = 1080, 1920, 30
VOFF = 0.5            # la voz arranca 0.5 s despues del "ding"
TOTAL = 76.0          # duracion total del video (s)
OUTRO = 70.95         # inicio del cierre (tiempo de voz)

IMG_DIR, WORDS_F, GEO_F, OUT = sys.argv[1:5]
WORDS = json.load(open(WORDS_F))
GEO = json.load(open(GEO_F))

# ---------------------------------------------------------------- colores
def C(hexv, a=1.0):
    return skia.ColorSetARGB(int(max(0, min(1, a)) * 255), (hexv >> 16) & 255, (hexv >> 8) & 255, hexv & 255)

NAVY = 0x0A1F44
NAVY2 = 0x13305E
NAVYD = 0x040C1E
RED = 0xD21F2C
DRBLUE = 0x002D62
WHITE = 0xFFFFFF
LIGHT = 0xAFC3E6
AMBER = 0xF2A900
INK = 0x0B1428

# ---------------------------------------------------------------- fuentes
FD = '/usr/share/fonts/opentype/inter/'
TF = {
    'black': skia.Typeface.MakeFromFile(FD + 'InterDisplay-Black.otf'),
    'xbold': skia.Typeface.MakeFromFile(FD + 'InterDisplay-ExtraBold.otf'),
    'bold': skia.Typeface.MakeFromFile(FD + 'InterDisplay-Bold.otf'),
    'semi': skia.Typeface.MakeFromFile(FD + 'Inter-SemiBold.otf'),
    'med': skia.Typeface.MakeFromFile(FD + 'Inter-Medium.otf'),
    'reg': skia.Typeface.MakeFromFile(FD + 'Inter-Regular.otf'),
    'ital': skia.Typeface.MakeFromFile(FD + 'Inter-MediumItalic.otf'),
    'mono': skia.Typeface.MakeFromFile('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'),
}
_fc = {}
def font(tf, size):
    k = (tf, round(size, 1))
    if k not in _fc:
        f = skia.Font(TF[tf], size)
        f.setSubpixel(True)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        _fc[k] = f
    return _fc[k]

def tw(s, tf, size):
    return font(tf, size).measureText(s)

def text(c, s, x, y, size, tf='xbold', color=WHITE, a=1.0, align='l', shadow=0, stroke=0, stroke_col=0x000000, stroke_a=0.7):
    f = font(tf, size)
    w = f.measureText(s)
    if align == 'c':
        x -= w / 2
    elif align == 'r':
        x -= w
    if stroke:
        sp = skia.Paint(AntiAlias=True, Color=C(stroke_col, stroke_a * a), Style=skia.Paint.kStroke_Style,
                        StrokeWidth=stroke, StrokeJoin=skia.Paint.kRound_Join)
        c.drawString(s, x, y, f, sp)
    p = skia.Paint(AntiAlias=True, Color=C(color, a))
    if shadow:
        p.setImageFilter(skia.ImageFilters.DropShadow(0, shadow * 0.4, shadow, shadow, C(0x000000, 0.55 * a)))
    c.drawString(s, x, y, f, p)
    return w

# ---------------------------------------------------------------- easing
def cl(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x
def pr(t, a, d):
    return cl((t - a) / d)
def eo(x):
    x = cl(x); return 1 - (1 - x) ** 3
def eio(x):
    x = cl(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def back(x, s=1.70158):
    x = cl(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2
def lerp(a, b, x):
    return a + (b - a) * x

def P(color, a=1.0, **kw):
    return skia.Paint(AntiAlias=True, Color=C(color, a), **kw)
def SP(color, w, a=1.0, cap=skia.Paint.kRound_Cap):
    return skia.Paint(AntiAlias=True, Color=C(color, a), Style=skia.Paint.kStroke_Style, StrokeWidth=w,
                      StrokeCap=cap, StrokeJoin=skia.Paint.kRound_Join)

def rrect(c, x, y, w, h, r, paint):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), paint)

def layer(c, a):
    c.saveLayer(None, skia.Paint(Alphaf=cl(a)))

# ---------------------------------------------------------------- imagenes
SC = 1.18  # margen para zoom/paneo
def load_cover(name, blur=0, bright=1.0, sat=1.0, fx=0.5, fy=0.5):
    im = Image.open(os.path.join(IMG_DIR, name)).convert('RGB')
    tw_, th_ = int(W * SC), int(H * SC)
    s = max(tw_ / im.width, th_ / im.height)
    im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    x0 = int((im.width - tw_) * fx); y0 = int((im.height - th_) * fy)
    im = im.crop((x0, y0, x0 + tw_, y0 + th_))
    if sat != 1: im = ImageEnhance.Color(im).enhance(sat)
    if bright != 1: im = ImageEnhance.Brightness(im).enhance(bright)
    if blur: im = im.filter(ImageFilter.GaussianBlur(blur))
    a = np.array(im.convert('RGBA'))
    return skia.Image.fromarray(a, colorType=skia.kRGBA_8888_ColorType)

def load_card(name, w, h, fx=0.5, fy=0.5):
    im = Image.open(os.path.join(IMG_DIR, name)).convert('RGB')
    s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    x0 = int((im.width - w) * fx); y0 = int((im.height - h) * fy)
    im = im.crop((x0, y0, x0 + w, y0 + h))
    return skia.Image.fromarray(np.array(im.convert('RGBA')), colorType=skia.kRGBA_8888_ColorType)

SAMP = skia.SamplingOptions(skia.FilterMode.kLinear)
def draw_bg(c, img, z=1.0, px=0, py=0, a=1.0):
    w, h = W * z, H * z
    c.drawImageRect(img, skia.Rect.MakeXYWH(W / 2 - w / 2 + px, H / 2 - h / 2 + py, w, h), SAMP, skia.Paint(Alphaf=a))

def tint(c, color=NAVY, a=0.5):
    c.drawRect(skia.Rect.MakeWH(W, H), P(color, a))

def grad_v(c, y0, y1, c0, a0, c1, a1):
    p = skia.Paint(Shader=skia.GradientShader.MakeLinear([skia.Point(0, y0), skia.Point(0, y1)], [C(c0, a0), C(c1, a1)]))
    c.drawRect(skia.Rect.MakeLTRB(0, min(y0, y1), W, max(y0, y1)), p)

def vignette(c):
    p = skia.Paint(Shader=skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), H * 0.72,
                                                         [C(0, 0), C(0, 0), C(NAVYD, 0.75)], [0, 0.55, 1]))
    c.drawRect(skia.Rect.MakeWH(W, H), p)

# ---------------------------------------------------------------- bandera RD
def dr_flag(c, x, y, w, h, a=1.0):
    cw = h * 0.2
    hw, hh = (w - cw) / 2, (h - cw) / 2
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), P(WHITE, a))
    c.drawRect(skia.Rect.MakeXYWH(x, y, hw, hh), P(DRBLUE, a))
    c.drawRect(skia.Rect.MakeXYWH(x + hw + cw, y, hw, hh), P(RED, a))
    c.drawRect(skia.Rect.MakeXYWH(x, y + hh + cw, hw, hh), P(RED, a))
    c.drawRect(skia.Rect.MakeXYWH(x + hw + cw, y + hh + cw, hw, hh), P(DRBLUE, a))

def flag_bar(c, y, h=8, a=1.0):
    gap = 10
    c.drawRect(skia.Rect.MakeXYWH(0, y, W / 2 - gap / 2, h), P(DRBLUE, a))
    c.drawRect(skia.Rect.MakeXYWH(W / 2 - gap / 2, y, gap, h), P(WHITE, a))
    c.drawRect(skia.Rect.MakeXYWH(W / 2 + gap / 2, y, W / 2, h), P(RED, a))

# ---------------------------------------------------------------- iconos (caja 100x100)
def poly(pts, close=True):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if close: p.close()
    return p

def union(paths):
    out = paths[0]
    for q in paths[1:]:
        out = skia.Op(out, q, skia.PathOp.kUnion_PathOp)
    return out

def rr_path(x, y, w, h, r):
    p = skia.Path(); p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)); return p
def circ_path(x, y, r):
    p = skia.Path(); p.addCircle(x, y, r); return p

def limb(x1, y1, x2, y2, w1, w2=None):
    w2 = w1 if w2 is None else w2
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    p = poly([(x1 + nx * w1 / 2, y1 + ny * w1 / 2), (x2 + nx * w2 / 2, y2 + ny * w2 / 2),
              (x2 - nx * w2 / 2, y2 - ny * w2 / 2), (x1 - nx * w1 / 2, y1 - ny * w1 / 2)])
    return union([p, circ_path(x1, y1, w1 / 2), circ_path(x2, y2, w2 / 2)])

PLANE = union([rr_path(44, 4, 12, 90, 6),
               poly([(50, 34), (96, 58), (96, 66), (50, 56), (4, 66), (4, 58)]),
               poly([(50, 78), (70, 90), (70, 96), (50, 91), (30, 96), (30, 90)])])

def icon(c, name, cx, cy, size, col=WHITE, a=1.0, rot=0, acc=RED):
    c.save()
    c.translate(cx, cy)
    if rot: c.rotate(rot)
    c.scale(size / 100, size / 100)
    c.translate(-50, -50)
    f = P(col, a); s = SP(col, 8, a)
    if name == 'plane':
        c.drawPath(PLANE, f)
    elif name == 'clock':
        c.drawCircle(50, 50, 42, s)
        c.drawLine(50, 50, 50, 22, SP(col, 8, a)); c.drawLine(50, 50, 70, 58, SP(acc, 7, a))
        c.drawCircle(50, 50, 5, f)
    elif name == 'suitcase':
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(36, 14, 64, 34), 6, 6), SP(col, 7, a))
        rrect(c, 12, 28, 76, 62, 10, f)
        c.drawLine(32, 36, 32, 82, SP(acc, 6, a)); c.drawLine(68, 36, 68, 82, SP(acc, 6, a))
    elif name == 'briefcase':
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(36, 16, 64, 34), 6, 6), SP(col, 7, a))
        rrect(c, 8, 30, 84, 58, 10, f)
        c.drawRect(skia.Rect.MakeLTRB(8, 52, 92, 57), P(acc, a))
        rrect(c, 44, 48, 12, 14, 3, P(acc, a))
    elif name == 'bed':
        rrect(c, 6, 26, 10, 64, 3, f)
        rrect(c, 6, 56, 88, 16, 4, f)
        rrect(c, 84, 66, 10, 22, 3, f)
        rrect(c, 20, 42, 22, 13, 6, f)
        rrect(c, 44, 44, 50, 12, 4, P(acc, a))
    elif name == 'food':
        c.drawCircle(52, 52, 28, s); c.drawCircle(52, 52, 15, SP(col, 5, a))
        c.drawLine(12, 16, 12, 88, SP(col, 7, a))
        for xx in (6, 12, 18):
            c.drawLine(xx, 14, xx, 34, SP(col, 4, a))
        c.drawPath(poly([(88, 14), (95, 30), (95, 52), (90, 52), (90, 88), (86, 88), (86, 14)]), f)
    elif name == 'car':
        c.drawPath(union([rr_path(6, 46, 88, 30, 10), poly([(22, 48), (32, 26), (68, 26), (80, 48)])]), f)
        c.drawPath(poly([(31, 46), (37, 32), (48, 32), (48, 46)]), P(INK, a * 0.8))
        c.drawPath(poly([(53, 46), (53, 32), (64, 32), (71, 46)]), P(INK, a * 0.8))
        for xx in (28, 72):
            c.drawCircle(xx, 78, 11, P(INK, a)); c.drawCircle(xx, 78, 11, SP(col, 5, a))
    elif name == 'stamp':
        c.drawCircle(50, 18, 13, f)
        rrect(c, 43, 28, 14, 24, 3, f)
        rrect(c, 20, 50, 60, 18, 5, f)
        rrect(c, 12, 68, 76, 12, 3, P(acc, a))
    elif name == 'moon':
        m = skia.Op(circ_path(50, 50, 36), circ_path(66, 38, 32), skia.PathOp.kDifference_PathOp)
        c.drawPath(m, f)
        for (xx, yy, r) in ((78, 66, 4), (86, 22, 3), (70, 84, 2.5)):
            c.drawCircle(xx, yy, r, f)
    elif name == 'calendar':
        rrect(c, 8, 16, 84, 76, 10, f)
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(8, 16, 92, 38), 10, 10), P(acc, a))
        c.drawRect(skia.Rect.MakeLTRB(8, 30, 92, 38), P(acc, a))
        rrect(c, 26, 6, 8, 20, 4, f); rrect(c, 66, 6, 8, 20, 4, f)
        text(c, '13', 50, 82, 40, 'black', INK, a, 'c')
    elif name == 'people':
        c.drawCircle(34, 32, 13, f); c.drawPath(rr_path(14, 48, 40, 40, 16), f)
        c.drawCircle(68, 28, 15, f); c.drawPath(rr_path(46, 46, 46, 46, 18), f)
    elif name == 'info':
        c.drawCircle(50, 50, 42, s)
        c.drawCircle(50, 30, 6, f); rrect(c, 45, 42, 10, 32, 4, f)
    elif name == 'bubble':
        c.drawPath(union([rr_path(6, 10, 88, 62, 16), poly([(26, 66), (22, 92), (48, 68)])]), f)
        for xx in (30, 50, 70):
            c.drawCircle(xx, 41, 6, P(acc, a))
    elif name == 'lupa':
        c.drawCircle(42, 42, 30, SP(col, 10, a))
        c.drawPath(limb(64, 64, 90, 90, 14), f)
    c.restore()

def tower_path():
    return union([poly([(42, 44), (58, 44), (63, 96), (37, 96)]),
                  poly([(22, 24), (78, 24), (70, 44), (30, 44)]),
                  poly([(34, 12), (66, 12), (76, 24), (24, 24)]),
                  rr_path(48.5, 0, 3, 14, 1.5)])
TOWER = tower_path()

# ---------------------------------------------------------------- siluetas
def maritza_path():
    parts = [circ_path(150, 82, 46),                       # cabeza
             skia.Path(),
             rr_path(110, 70, 26, 70, 13),                  # cola de caballo
             rr_path(137, 118, 26, 36, 8),                  # cuello
             rr_path(92, 146, 116, 200, 44),                # torso / chaqueta
             limb(196, 174, 226, 278, 34, 30), limb(226, 278, 250, 372, 30, 26),   # brazo der.
             limb(104, 174, 88, 276, 34, 30), limb(88, 276, 98, 362, 30, 26),      # brazo izq.
             poly([(102, 330), (150, 330), (146, 652), (112, 652)]),
             poly([(152, 330), (198, 330), (190, 652), (156, 652)]),
             rr_path(102, 640, 54, 26, 12), rr_path(152, 640, 60, 26, 12)]
    hair = skia.Path(); hair.addOval(skia.Rect.MakeLTRB(100, 30, 200, 112))
    parts[1] = hair
    return union([q for q in parts if not q.isEmpty()])

def maritza_case():
    handle = union([rr_path(246, 366, 8, 104, 3), rr_path(276, 366, 8, 104, 3), rr_path(246, 362, 38, 10, 4)])
    body = rr_path(220, 466, 92, 178, 16)
    return handle, body

def diomedes_path():
    # sentado, de perfil mirando a la derecha, algo encorvado
    return union([circ_path(312, 96, 42),
                  rr_path(296, 128, 26, 30, 8),
                  limb(300, 160, 290, 300, 100, 92),           # torso
                  limb(296, 296, 430, 304, 64, 58),             # muslo
                  limb(430, 304, 436, 446, 52, 44),             # pierna
                  rr_path(418, 436, 76, 26, 12),                # zapato
                  limb(312, 176, 360, 262, 30, 28), limb(360, 262, 418, 282, 28, 24)])  # brazo

def seats_path():
    parts = []
    for i, x in enumerate((70, 240, 410)):
        parts.append(rr_path(x, 130, 150, 180, 26))        # respaldo
        parts.append(rr_path(x - 6, 300, 162, 40, 14))     # asiento
    parts.append(rr_path(60, 350, 530, 18, 6))              # viga
    parts.append(rr_path(110, 360, 16, 120, 5)); parts.append(rr_path(520, 360, 16, 120, 5))
    parts.append(rr_path(80, 470, 76, 14, 6)); parts.append(rr_path(490, 470, 76, 14, 6))
    return union(parts)

MARITZA = maritza_path(); M_HANDLE, M_CASE = maritza_case()
DIOMEDES = diomedes_path(); SEATS = seats_path()

def silhouette(c, path, x, y, s, a=1.0, top=0x23497F, bot=0x0B1D40, rim=0x8FB2E8):
    c.save(); c.translate(x, y); c.scale(s, s)
    b = path.computeTightBounds()
    sh = skia.GradientShader.MakeLinear([skia.Point(0, b.top()), skia.Point(0, b.bottom())], [C(top, a), C(bot, a)])
    glow = skia.Paint(AntiAlias=True, Color=C(rim, 0.35 * a), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
    c.drawPath(path, glow)
    c.drawPath(path, skia.Paint(AntiAlias=True, Shader=sh))
    c.drawPath(path, SP(rim, 3 / s, 0.75 * a))
    c.restore()

# ---------------------------------------------------------------- piezas graficas
def chip(c, s, x, y, size=34, bg=RED, fg=WHITE, a=1.0, align='c', ic=None, tf='xbold', padx=26, h=None):
    w = tw(s, tf, size)
    h = h or size * 1.9
    iw = size * 1.25 if ic else 0
    tot = w + padx * 2 + iw
    x0 = x - tot / 2 if align == 'c' else x
    rrect(c, x0, y, tot, h, h / 2 if h < 90 else 18, P(bg, a))
    if ic:
        icon(c, ic, x0 + padx + iw * 0.38, y + h / 2, size * 1.05, fg, a)
    text(c, s, x0 + padx + iw, y + h / 2 + size * 0.36, size, tf, fg, a)
    return tot

def rotulo(c, t, t0, name, role, y, x=60):
    k = eo(pr(t, t0, 0.55))
    if k <= 0: return
    nw = tw(name, 'black', 54); rw = tw(role, 'semi', 34)
    w = max(nw, rw) + 120
    xs = x - (1 - k) * (w + 80)
    c.save(); c.clipRect(skia.Rect.MakeLTRB(x, y - 10, W, y + 170))
    rrect(c, xs, y, w, 150, 14, P(NAVY, 0.94))
    c.drawRect(skia.Rect.MakeXYWH(xs, y, 14, 150), P(RED))
    dr_flag(c, xs + w - 66, y + 20, 44, 30)
    k2 = eo(pr(t, t0 + 0.2, 0.5))
    text(c, name, xs + 46, y + 72, 54, 'black', WHITE, k2)
    text(c, role, xs + 46, y + 120, 34, 'semi', LIGHT, k2)
    c.restore()

# ---------------------------------------------------------------- subtitulos palabra por palabra
FIX = {'Sólo': 'Solo', 'deben': '¿Deben'}
def build_chunks():
    ws = [[a, b, FIX.get(w, w)] for a, b, w in WORDS]
    chunks, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w)
        txt = ' '.join(x[2] for x in cur)
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        if (w[2][-1] in '.,?' or len(cur) >= 3 or len(txt) >= 15 or nxt is None
                or (nxt and nxt[0] - w[1] > 0.5)):
            chunks.append(cur); cur = []
    out = []
    for i, ch in enumerate(chunks):
        st = ch[0][0]
        en = chunks[i + 1][0][0] if i + 1 < len(chunks) else ch[-1][1] + 0.3
        en = min(en, ch[-1][1] + 0.45)
        out.append((st, en, ch))
    return out
CHUNKS = build_chunks()

def subtitles(c, t):
    if t > OUTRO - 0.05: return
    for st, en, ch in CHUNKS:
        if st - 0.02 <= t < en:
            break
    else:
        return
    size = 70
    words = [w[2].upper() for w in ch]
    sp = 22
    widths = [tw(w, 'black', size) for w in words]
    tot = sum(widths) + sp * (len(words) - 1)
    if tot > 990:
        size = size * 990 / tot
        widths = [tw(w, 'black', size) for w in words]; sp = sp * 990 / tot
        tot = sum(widths) + sp * (len(words) - 1)
    x = W / 2 - tot / 2
    yb = 330
    for i, (w, wd) in enumerate(zip(words, widths)):
        ws, we = ch[i][0], ch[i][1]
        if t < ws - 0.03:
            break
        k = back(pr(t, ws - 0.03, 0.16))
        nxt = ch[i + 1][0] if i + 1 < len(ch) else en
        active = ws - 0.03 <= t < max(we, nxt - 0.02)
        c.save()
        c.translate(x + wd / 2, yb - size * 0.35)
        sc = 0.6 + 0.4 * k
        c.scale(sc, sc)
        c.translate(-(x + wd / 2), -(yb - size * 0.35))
        if active:
            rrect(c, x - 12, yb - size * 0.86, wd + 24, size * 1.12, 14, P(RED, 0.95))
            text(c, w, x, yb, size, 'black', WHITE, cl(k * 1.4))
        else:
            text(c, w, x, yb, size, 'black', WHITE, cl(k * 1.4), stroke=10, stroke_col=NAVYD, stroke_a=0.85)
        c.restore()
        x += wd + sp

def brand_bug(c, t):
    if t > OUTRO - 0.2: return
    a = 0.9
    icon(c, 'lupa', 74, 150, 40, WHITE, a)
    text(c, '?', 70, 152, 22, 'black', RED, a, 'c')
    text(c, 'CAPITAL CURIOSO', 104, 161, 28, 'black', WHITE, a)

# ---------------------------------------------------------------- recursos por escena
print('Cargando imagenes...', file=sys.stderr)
IM1 = load_cover('1A_Pantalla_salidas.jpg', bright=0.8, sat=0.9)
IM2 = load_cover('2B_Torre_de_control.jpg', bright=0.55, sat=0.8, fy=0.4)
IM3 = load_cover('3_Maritza_pasajera_esperando.jpg', blur=14, bright=0.45, sat=0.7, fx=0.55)
IM4 = load_cover('4A_Diomedes_durmiendo_aeropuerto.jpg', blur=12, bright=0.45, fx=0.6)
IM5 = load_cover('5A_Terminal_llena.jpg', bright=0.45, sat=0.8)
IM6 = load_card('6B_Aeropuerto_Las_Americas_letrero.jpg', 960, 330, fy=0.55)

# ---------------------------------------------------------------- mapa
LON0, LON1, LAT0, LAT1 = -86.5, -61.5, 15.5, 45.0
MX0, MY0, MX1, MY1 = 20, 500, 1060, 1640
def merc(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
_ym0, _ym1 = merc(LAT0), merc(LAT1)
_sx = (MX1 - MX0) / math.radians(LON1 - LON0)
_sy = (MY1 - MY0) / (_ym1 - _ym0)
MS = min(_sx, _sy)
_cx = (MX0 + MX1) / 2 - MS * math.radians((LON0 + LON1) / 2)
_cy = (MY0 + MY1) / 2 + MS * (_ym0 + _ym1) / 2
def proj(lon, lat):
    return (_cx + MS * math.radians(lon), _cy - MS * merc(lat))

def build_land():
    land, dr = skia.Path(), skia.Path()
    for name, rings in GEO.items():
        tgt = dr if name == 'Dominican Rep.' else land
        for ring in rings:
            pts = [proj(x, y) for x, y in ring]
            tgt.addPoly([skia.Point(*q) for q in pts], True)
    return land, dr
LAND, DRLAND = build_land()

SDQ = proj(-69.67, 18.43)
CITIES = [  # nombre, lon, lat, t_voz, curvatura, lado etiqueta
    ('NUEVA YORK', -73.78, 40.64, 23.5, 0.16, 'r'),
    ('BOSTON', -71.01, 42.36, 25.0, 0.22, 'r'),
    ('MIAMI', -80.29, 25.79, 26.0, -0.18, 'l'),
    ('ORLANDO', -81.31, 28.43, 26.86, -0.12, 'l'),
    ('NEWARK', -74.17, 40.69, 27.8, -0.07, 'l'),
    ('SAN JUAN', -66.00, 18.44, 28.32, -0.45, 'r'),
]
def bez(p0, p1, bend, n=80):
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy)
    cx, cy = mx - dy / L * bend * L, my + dx / L * bend * L
    pts = []
    for i in range(n + 1):
        u = i / n
        pts.append(((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * cx + u * u * p1[0],
                    (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * cy + u * u * p1[1]))
    return pts
ROUTES = [(nm, proj(lo, la), bez(SDQ, proj(lo, la), bd), t0, side) for nm, lo, la, t0, bd, side in CITIES]

def draw_x(c, x, y, s, a=1.0):
    for dx in (-1, 1):
        c.drawLine(x - s * dx, y - s, x + s * dx, y + s, SP(WHITE, s * 0.75, a))
    for dx in (-1, 1):
        c.drawLine(x - s * dx, y - s, x + s * dx, y + s, SP(RED, s * 0.42, a))

def draw_map(c, t, a):
    layer(c, a)
    # reticula
    for lon in range(-85, -60, 5):
        x0, _ = proj(lon, LAT0)
        c.drawLine(x0, MY0 - 40, x0, MY1 + 40, SP(LIGHT, 1.2, 0.10))
    for lat in range(20, 46, 5):
        _, y0 = proj(LON0, lat)
        c.drawLine(0, y0, W, y0, SP(LIGHT, 1.2, 0.10))
    c.drawPath(LAND, P(0x1A3B6E))
    c.drawPath(LAND, SP(0x5D82BE, 2, 0.8))
    c.drawPath(DRLAND, P(RED))
    c.drawPath(DRLAND, SP(WHITE, 2.5))
    # pulso SDQ
    for k in range(2):
        ph = ((t * 0.8 + k * 0.5) % 1.0)
        c.drawCircle(SDQ[0], SDQ[1], 12 + ph * 60, SP(RED, 4, (1 - ph) * 0.8))
    for nm, dest, pts, t0, side in ROUTES:
        k = eio(pr(t, t0, 0.75))
        if k <= 0: continue
        n = max(2, int(len(pts) * k))
        path = poly(pts[:n], close=False)
        c.drawPath(path, SP(RED, 13, 0.25))
        c.drawPath(path, SP(RED, 6))
        if k < 1:
            (x1, y1), (x2, y2) = pts[n - 2], pts[n - 1]
            ang = math.degrees(math.atan2(y2 - y1, x2 - x1)) + 90
            icon(c, 'plane', x2, y2, 46, WHITE, 1, rot=ang)
        else:
            kx = back(pr(t, t0 + 0.75, 0.3), 2.5)
            c.drawCircle(dest[0], dest[1], 9, P(WHITE))
            if kx > 0:
                draw_x(c, dest[0], dest[1], 22 * kx)
            kl = eo(pr(t, t0 + 0.6, 0.4))
            fs = 34
            lw = tw(nm, 'black', fs) + 30
            if side == 'r':
                lx, ly = dest[0] + 34, dest[1] - 26
            elif side == 'l':
                lx, ly = dest[0] - 34 - lw, dest[1] - 26
            else:
                lx, ly = dest[0] - lw / 2 + 30, dest[1] + 34
            if nm == 'NEWARK': ly += 44
            if nm == 'NUEVA YORK': ly += 34
            if nm == 'BOSTON': ly -= 30
            if nm == 'SAN JUAN': lx -= 40; ly -= 52
            rrect(c, lx, ly, lw, 52, 10, P(NAVYD, 0.9 * kl))
            text(c, nm, lx + 15, ly + 38, fs, 'black', WHITE, kl)
    c.drawCircle(SDQ[0], SDQ[1], 14, P(WHITE)); c.drawCircle(SDQ[0], SDQ[1], 8, P(RED))
    rrect(c, SDQ[0] - 170, SDQ[1] + 30, 290, 52, 10, P(WHITE, 0.95))
    text(c, 'SANTO DOMINGO', SDQ[0] - 25, SDQ[1] + 68, 32, 'black', NAVY, 1, 'c')
    c.restore()

# ---------------------------------------------------------------- escenas (t = tiempo de voz)
def scene1(c, t):
    k = pr(t, -0.5, 7.0)
    draw_bg(c, IM1, 1.0 + 0.12 * eio(k), 0, -40 * k)
    tint(c, NAVY, 0.25)
    vignette(c)
    grad_v(c, 0, 520, NAVYD, 0.85, NAVYD, 0)
    grad_v(c, 980, H, NAVYD, 0, NAVYD, 0.9)
    # tablero de salidas
    a0 = eo(pr(t, -0.4, 0.5))
    bx, by, bw, bh = 60, 1010, 960, 600
    c.save(); c.translate(0, (1 - a0) * 80)
    layer(c, a0)
    rrect(c, bx, by, bw, bh, 22, P(INK, 0.93))
    rrect(c, bx, by, bw, 92, 22, P(0x16264A))
    c.drawRect(skia.Rect.MakeXYWH(bx, by + 70, bw, 22), P(0x16264A))
    icon(c, 'plane', bx + 60, by + 46, 46, AMBER, 1, rot=60)
    text(c, 'SALIDAS', bx + 100, by + 60, 40, 'mono', AMBER)
    text(c, 'LAS AMÉRICAS · SDQ', bx + bw - 34, by + 58, 28, 'mono', LIGHT, 1, 'r')
    text(c, 'DESTINO', bx + 40, by + 136, 24, 'mono', LIGHT, 0.7)
    text(c, 'ESTADO', bx + bw - 40, by + 136, 24, 'mono', LIGHT, 0.7, 'r')
    dests = ['NUEVA YORK', 'BOSTON', 'MIAMI', 'ORLANDO', 'NEWARK', 'SAN JUAN']
    for i, d in enumerate(dests):
        y = by + 196 + i * 66
        ki = eo(pr(t, -0.2 + i * 0.18, 0.3))
        c.drawRect(skia.Rect.MakeXYWH(bx + 30, y + 22, bw - 60, 2), P(LIGHT, 0.12))
        text(c, d, bx + 40, y, 38, 'mono', WHITE, ki)
        blink = 1.0 if (int((t + i * 0.13) * 2.2) % 2 == 0) else 0.25
        if ki > 0:
            sw = tw('CANCELADO', 'mono', 34) + 28
            rrect(c, bx + bw - 40 - sw, y - 36, sw, 50, 6, P(RED, blink * ki))
            text(c, 'CANCELADO', bx + bw - 54, y, 34, 'mono', WHITE, ki * (0.35 + 0.65 * blink), 'r')
    c.restore(); c.restore()
    # chip de pais
    kc = eo(pr(t, 3.0, 0.45))
    if kc > 0:
        layer(c, kc)
        cw = tw('DOMINICANOS ATRAPADOS', 'black', 40) + 120
        x0 = W / 2 - cw / 2
        rrect(c, x0, 880 + (1 - kc) * 30, cw, 82, 41, P(NAVY, 0.95))
        dr_flag(c, x0 + 28, 880 + (1 - kc) * 30 + 22, 54, 38)
        text(c, 'DOMINICANOS ATRAPADOS', x0 + 98, 880 + (1 - kc) * 30 + 56, 40, 'black', WHITE)
        c.restore()

def signal_arcs(c, cx, cy, t, broken_k):
    for side in (-1, 1):
        for i in range(3):
            r = 60 + i * 46
            ph = (t * 1.6 - i * 0.25) % 1.0
            a = 0.35 + 0.65 * max(0, 1 - abs(ph - 0.3) * 3)
            col = WHITE
            if broken_k > 0:
                flick = 1.0 if (int(t * 22 + i * 3 + side) % 3) else 0.0
                a *= (1 - broken_k) * flick
                col = RED
            if a <= 0.01: continue
            rect = skia.Rect.MakeLTRB(cx - r, cy - r, cx + r, cy + r)
            start = -40 if side > 0 else 140
            path = skia.Path(); path.addArc(rect, start, 80)
            c.drawPath(path, SP(col, 12, a))

def scene2(c, t):
    k = pr(t, 6.0, 11.5)
    draw_bg(c, IM2, 1.04 + 0.1 * k, 0, 30 - 60 * k)
    tint(c, NAVY, 0.45)
    vignette(c)
    grad_v(c, 0, 520, NAVYD, 0.85, NAVYD, 0)
    # fecha
    kd = back(pr(t, 6.6, 0.5))
    if kd > 0:
        c.save(); c.translate(W / 2, 600); c.scale(kd, kd); c.translate(-W / 2, -600)
        rrect(c, 90, 470, 900, 250, 26, P(NAVY, 0.92))
        c.drawRect(skia.Rect.MakeXYWH(90, 470, 900, 10), P(RED))
        icon(c, 'calendar', 230, 598, 170, WHITE, 1, acc=RED)
        text(c, 'VIERNES', 350, 560, 54, 'xbold', LIGHT)
        text(c, '13 NOV', 345, 680, 136, 'black', WHITE)
        c.restore()
    # torre
    tk = eo(pr(t, 7.2, 0.6))
    broken = pr(t, 14.14, 0.45)
    jit = (math.sin(t * 90) * 10) if 14.14 < t < 14.6 else 0
    if tk > 0:
        layer(c, tk)
        cx, cy = W / 2 + jit, 1000
        c.drawCircle(cx, cy, 190, P(NAVYD, 0.55))
        c.save(); c.translate(cx - 150, cy - 165); c.scale(3.0, 3.0)
        c.drawPath(TOWER, P(WHITE))
        c.drawRect(skia.Rect.MakeLTRB(30, 28, 70, 37), P(NAVY if broken <= 0 else RED))
        c.restore()
        signal_arcs(c, cx, cy - 165, t, broken)
        if broken > 0:
            kb = back(pr(t, 14.4, 0.35))
            c.drawCircle(cx + 120, cy - 150, 46 * kb, P(RED))
            c.drawLine(cx + 120 - 22 * kb, cy - 150 - 22 * kb, cx + 120 + 22 * kb, cy - 150 + 22 * kb, SP(WHITE, 9))
            c.drawLine(cx + 120 + 22 * kb, cy - 150 - 22 * kb, cx + 120 - 22 * kb, cy - 150 + 22 * kb, SP(WHITE, 9))
        c.restore()
    # chips de datos
    k1 = eo(pr(t, 12.3, 0.4)); k2 = eo(pr(t, 15.0, 0.4))
    if k1 > 0 and k2 < 1:
        layer(c, k1 * (1 - k2))
        chip(c, 'VUELOS NACIONALES DETENIDOS', W / 2, 1215 + (1 - k1) * 30, 36, NAVY, WHITE, ic='plane')
        c.restore()
    if k2 > 0:
        layer(c, k2)
        chip(c, 'FALLA EN TELECOMUNICACIONES', W / 2, 1215 + (1 - k2) * 30, 36, RED, WHITE)
        c.restore()
    rotulo(c, t, 8.36, 'FAA', 'Administración Federal de Aviación', 1360)

def scene3(c, t):
    c.drawRect(skia.Rect.MakeWH(W, H), P(NAVY))
    gp = skia.Paint(Shader=skia.GradientShader.MakeRadial(skia.Point(W / 2, 1000), 1100, [C(0x1A3D75), C(NAVYD)]))
    c.drawRect(skia.Rect.MakeWH(W, H), gp)
    # parte A: contador
    ka = 1 - eio(pr(t, 23.2, 0.35))
    if ka > 0:
        layer(c, ka)
        c.save(); c.translate(0, -(1 - ka) * 120)
        ki = eo(pr(t, 16.9, 0.6))
        c.save()
        c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(60, 450, 960, 330), 22, 22), True)
        c.drawImageRect(IM6, skia.Rect.MakeXYWH(60 - 30 * (1 - ki), 450, 960 * (1 + 0.06 * (1 - ki)), 330 * (1 + 0.06 * (1 - ki))), SAMP, skia.Paint(Alphaf=ki))
        grad_v(c, 600, 780, NAVYD, 0, NAVYD, 0.85 * ki)
        c.restore()
        if ki > 0:
            chip(c, 'AEROPUERTO DE LAS AMÉRICAS', 90, 700, 30, RED, WHITE, ki, align='l')
        kn = eo(pr(t, 17.8, 0.4))
        n = int(round(19 * cl((t - 19.2) / 0.96)))
        pulse = 1 + 0.06 * max(0, 1 - (t - 20.16) * 4) if t > 20.16 else 1
        c.save(); c.translate(W / 2, 1030); c.scale(pulse, pulse); c.translate(-W / 2, -1030)
        text(c, str(n), W / 2, 1130, 330, 'black', WHITE if n < 19 else WHITE, kn, 'c', shadow=18)
        c.restore()
        if n >= 19:
            draw_x(c, W / 2 + tw('19', 'black', 330) / 2 + 30, 900, 26 * back(pr(t, 20.2, 0.3), 2.5))
        text(c, 'VUELOS CANCELADOS', W / 2, 1225, 66, 'black', WHITE, kn, 'c')
        text(c, 'EN LAS AMÉRICAS', W / 2, 1290, 44, 'semi', LIGHT, kn, 'c')
        for i, (lab, val, t0, ic, rot) in enumerate((('SALIDAS', 12, 21.5, 'plane', 45), ('LLEGADAS', 7, 22.74, 'plane', 135))):
            y = 1360 + i * 130
            kb = eo(pr(t, t0 - 0.15, 0.3))
            if kb <= 0: continue
            layer(c, kb)
            icon(c, ic, 110, y + 46, 52, WHITE, 1, rot=rot)
            text(c, lab, 155, y + 62, 40, 'black', WHITE)
            bx0, bmax = 420, 470
            kw = eo(pr(t, t0, 0.7))
            rrect(c, bx0, y + 18, bmax, 56, 12, P(WHITE, 0.10))
            rrect(c, bx0, y + 18, max(24, bmax * val / 12 * kw), 56, 12, P(RED if i == 0 else 0x3E6FB8))
            text(c, str(int(round(val * kw))), bx0 + bmax + 70, y + 66, 58, 'black', WHITE, 1, 'c')
            c.restore()
        c.restore(); c.restore()
    # parte B: mapa
    kb = eo(pr(t, 23.25, 0.5))
    if kb > 0:
        draw_map(c, t, kb)
        kt = eo(pr(t, 23.4, 0.4)) * (1 - eo(pr(t, 28.7, 0.3)))
        layer(c, kt)
        chip(c, 'RUTAS AFECTADAS DESDE RD', W / 2, 425, 34, NAVY, WHITE, ic='plane')
        c.restore()
        kr = eo(pr(t, 28.8, 0.4))
        if kr > 0:
            layer(c, kr)
            rrect(c, 120, 405 + (1 - kr) * 30, 840, 100, 20, P(RED, 0.95))
            text(c, '6 RUTAS', 160, 475 + (1 - kr) * 30, 56, 'black', WHITE)
            text(c, 'entre las más afectadas', 410, 471 + (1 - kr) * 30, 38, 'semi', WHITE)
            c.restore()

def scene4(c, t):
    k = pr(t, 31.0, 12)
    draw_bg(c, IM3, 1.03 + 0.06 * k, -20 * k, 0)
    tint(c, NAVY, 0.5)
    vignette(c)
    grad_v(c, 0, 520, NAVYD, 0.85, NAVYD, 0)
    ks = eo(pr(t, 31.2, 0.6))
    layer(c, ks)
    sx, sy, ss = 40 - (1 - ks) * 60, 470, 0.92
    silhouette(c, MARITZA, sx, sy, ss, 1)
    c.save(); c.translate(sx, sy); c.scale(ss, ss)
    c.drawPath(M_HANDLE, P(0x9AA7BF)); c.drawPath(M_CASE, P(RED)); c.drawPath(M_CASE, SP(WHITE, 3, 0.6))
    c.drawLine(244, 500, 288, 500, SP(0x7A0E16, 6)); c.drawLine(244, 610, 288, 610, SP(0x7A0E16, 6))
    c.drawCircle(238, 650, 10, P(INK)); c.drawCircle(294, 650, 10, P(INK))
    c.restore(); c.restore()
    rotulo(c, t, 31.54, 'MARITZA', 'Pasajera', 1130)
    # linea de tiempo
    lx = 430
    nodes = [(33.58, '5:00 AM', 'Llegó al aeropuerto', 'clock', WHITE),
             (35.58, '10:00 AM', 'Hora de su vuelo', 'plane', WHITE),
             (36.58, 'POSPUESTO', 'varias veces', None, AMBER),
             (38.9, 'CANCELADO', '', None, RED)]
    ys = [500, 650, 800, 950]
    kl = eo(pr(t, 32.6, 0.5))
    c.drawLine(lx, ys[0], lx, ys[0] + (ys[-1] - ys[0]) * 0, SP(WHITE, 6, 0.3 * kl))
    c.drawLine(lx, ys[0] - 10, lx, ys[-1] + 10, SP(WHITE, 5, 0.22 * kl))
    for i, (t0, big, small, ic, col) in enumerate(nodes):
        kn = eo(pr(t, t0 - 0.1, 0.4))
        if i > 0:
            kp = eio(pr(t, t0 - 0.45, 0.4))
            c.drawLine(lx, ys[i - 1], lx, lerp(ys[i - 1], ys[i], kp), SP(col if i >= 2 else WHITE, 6))
        if kn <= 0: continue
        y = ys[i]
        c.drawCircle(lx, y, 18 * back(pr(t, t0 - 0.1, 0.35)), P(col))
        c.drawCircle(lx, y, 8 * kn, P(NAVY))
        layer(c, kn)
        x = lx + 44 + (1 - kn) * 40
        if ic:
            icon(c, ic, x + 34, y, 60, WHITE, 1, rot=45 if ic == 'plane' else 0)
            text(c, big, x + 84, y + 10, 60, 'black', WHITE)
            text(c, small, x + 86, y + 56, 30, 'semi', LIGHT)
        else:
            if i == 3:
                sc = 1 + 0.5 * (1 - back(pr(t, t0 - 0.1, 0.35)))
                c.save(); c.translate(x + 200, y); c.rotate(-4); c.scale(sc, sc); c.translate(-(x + 200), -y)
                rrect(c, x, y - 48, 410, 96, 12, P(RED))
                text(c, big, x + 205, y + 26, 66, 'black', WHITE, 1, 'c')
                c.restore()
            else:
                rrect(c, x, y - 44, 380, 88, 12, P(AMBER))
                text(c, big, x + 190, y + 22, 58, 'black', INK, 1, 'c')
                text(c, small, x + 400, y + 12, 30, 'semi', AMBER)
        c.restore()
    # sello de migracion x2
    km = eo(pr(t, 40.3, 0.4))
    if km > 0:
        layer(c, km)
        rrect(c, 60, 1310, 960, 300, 24, P(NAVY, 0.9))
        text(c, 'PASÓ POR', 110, 1400, 36, 'semi', LIGHT)
        text(c, 'MIGRACIÓN', 110, 1470, 70, 'black', WHITE)
        for j, ts in enumerate((41.0, 41.54)):
            if t < ts - 0.25: continue
            down = pr(t, ts - 0.25, 0.25)
            mx, my = 610 + j * 40, 1440 + j * 30
            if t < ts:
                icon(c, 'stamp', mx + 60, my - 150 + 150 * down ** 2 - 40, 130, WHITE, 1, acc=RED)
            else:
                kk = back(pr(t, ts, 0.25), 2)
                c.save(); c.translate(mx + 60, my + 30); c.rotate(-12 + j * 16)
                c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-95, -40, 190, 80), 10, 10), SP(RED, 6, 0.9 * min(1, kk)))
                text(c, 'SELLADO', 0, 12, 34, 'black', RED, 0.9 * min(1, kk), 'c')
                c.restore()
                up = eo(pr(t, ts, 0.3))
                if j == 0 or t < ts + 0.3:
                    icon(c, 'stamp', mx + 60, my - 40 - 120 * up, 130, WHITE, 1 - up, acc=RED)
        kx = back(pr(t, 41.54, 0.35), 2.2)
        if kx > 0:
            c.save(); c.translate(925, 1460); c.scale(kx, kx)
            c.drawCircle(0, 0, 82, P(RED))
            text(c, 'x2', 0, 30, 84, 'black', WHITE, 1, 'c')
            c.restore()
        c.restore()

def scene5(c, t):
    k = pr(t, 42.8, 12)
    draw_bg(c, IM4, 1.03 + 0.06 * k, 20 * k, 0)
    tint(c, NAVY, 0.55)
    vignette(c)
    grad_v(c, 0, 520, NAVYD, 0.85, NAVYD, 0)
    ks = eo(pr(t, 42.9, 0.6))
    layer(c, ks)
    ox, oy = 210, 440 + (1 - ks) * 40
    c.save(); c.translate(ox, oy)
    c.drawPath(SEATS, P(0x2B4A7A, 0.95)); c.drawPath(SEATS, SP(0x8FB2E8, 2, 0.6))
    c.restore()
    silhouette(c, DIOMEDES, ox, oy - 20, 1.0)
    # maleta a sus pies
    icon(c, 'suitcase', ox + 600, oy + 410, 120, RED, 1, acc=0x7A0E16)
    c.restore()
    # noche en el aeropuerto
    kmn = eo(pr(t, 46.6, 0.45))
    if kmn > 0:
        layer(c, kmn)
        chip(c, 'UNA NOCHE EN UN ASIENTO', W / 2, 920 + (1 - kmn) * 20, 34, NAVYD, WHITE, ic='moon')
        c.restore()
    rotulo(c, t, 43.18, 'DIOMEDES GONZÁLEZ', 'Pasajero', 1020)
    kc = eo(pr(t, 44.2, 0.5))
    text(c, 'Viajaba tras la muerte de su suegra', 70, 1218, 34, 'ital', WHITE, kc * 0.9)
    cells = [(49.42, 'briefcase', '2 DÍAS', 'de trabajo perdidos'),
             (51.42, 'food', 'COMIDA', ''),
             (52.28, 'bed', 'HOSPEDAJE', ''),
             (52.86, 'car', 'TRANSPORTE', '')]
    for i, (t0, ic, big, small) in enumerate(cells):
        kk = back(pr(t, t0 - 0.12, 0.4))
        if kk <= 0: continue
        cx = 60 + (i % 2) * 490; cy = 1260 + (i // 2) * 190
        c.save(); c.translate(cx + 235, cy + 85); c.scale(0.7 + 0.3 * kk, 0.7 + 0.3 * kk); c.translate(-(cx + 235), -(cy + 85))
        layer(c, min(1, kk))
        rrect(c, cx, cy, 470, 170, 20, P(NAVY, 0.92))
        c.drawRect(skia.Rect.MakeXYWH(cx, cy + 20, 8, 130), P(RED))
        c.drawCircle(cx + 92, cy + 85, 62, P(RED if i == 0 else 0x1E3F75))
        icon(c, ic, cx + 92, cy + 85, 78, WHITE, 1, acc=WHITE if i == 0 else RED)
        if small:
            text(c, big, cx + 175, cy + 82, 54, 'black', WHITE)
            text(c, 'de trabajo', cx + 177, cy + 118, 28, 'semi', LIGHT)
            text(c, 'perdidos', cx + 177, cy + 150, 28, 'semi', LIGHT)
        else:
            text(c, big, cx + 175, cy + 100, 44 if len(big) > 8 else 50, 'black', WHITE)
        c.restore(); c.restore()
    kb = eo(pr(t, 53.4, 0.35))
    if kb > 0:
        layer(c, kb)
        c.save(); c.translate(W / 2, 1640); c.rotate(-3)
        chip(c, 'PAGADO DE SU BOLSILLO', 0, -45, 40, RED, WHITE)
        c.restore(); c.restore()

def scene6(c, t):
    k = pr(t, 54.0, 8)
    draw_bg(c, IM5, 1.04 + 0.08 * k, 0, -30 * k)
    tint(c, NAVY, 0.55)
    vignette(c)
    grad_v(c, 0, 520, NAVYD, 0.85, NAVYD, 0)
    kq = eo(pr(t, 54.4, 0.55))
    if kq > 0:
        layer(c, kq)
        c.save(); c.translate(0, (1 - kq) * 90)
        rrect(c, 70, 470, 940, 560, 30, P(WHITE, 0.97))
        c.drawRect(skia.Rect.MakeXYWH(70, 470, 940, 12), P(RED))
        text(c, '“', 110, 690, 300, 'black', RED, 1)
        full = 'La causa fue externa'
        n = int(len(full) * cl((t - 55.6) / 1.0))
        shown = full[:n]
        l1 = shown[:12]; l2 = shown[13:] if n > 13 else ''
        text(c, l1, 130, 780, 96, 'black', NAVY)
        text(c, l2, 130, 885, 96, 'black', NAVY)
        if 55.6 < t < 56.8 and int(t * 6) % 2 == 0:
            cxp = 130 + tw(l2 if l2 else l1, 'black', 96)
            c.drawRect(skia.Rect.MakeXYWH(cxp + 6, (885 if l2 else 780) - 78, 8, 90), P(RED))
        ka = eo(pr(t, 54.6, 0.4))
        c.drawRect(skia.Rect.MakeXYWH(130, 925, 120 * ka, 6), P(RED))
        text(c, '— JetBlue', 130, 985, 46, 'black', RED, ka)
        text(c, 'Fuente: Infobae', 960, 985, 30, 'semi', 0x5A6B8C, ka, 'r')
        c.restore(); c.restore()
    kp = eo(pr(t, 57.5, 0.5))
    if kp > 0:
        layer(c, kp)
        y = 1110 + (1 - kp) * 60
        rrect(c, 70, y, 940, 330, 30, P(NAVY, 0.95))
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(70, y, 940, 330), 30, 30), SP(RED, 5))
        icon(c, 'people', 190, y + 110, 120, WHITE)
        text(c, 'PASAJEROS:', 290, y + 130, 64, 'black', WHITE)
        kf = eo(pr(t, 59.6, 0.5))
        text(c, 'Falta de información', 120, y + 222, 58, 'xbold', LIGHT, kp)
        text(c, 'clara', 120, y + 290, 58, 'xbold', LIGHT, kp)
        # icono info tachado
        ix, iy = 880, y + 230
        icon(c, 'info', ix, iy, 110, WHITE, 0.95)
        if kf > 0:
            c.drawLine(ix - 50, iy + 50, ix - 50 + 100 * kf, iy + 50 - 100 * kf, SP(RED, 12))
        c.restore()

def scene7(c, t):
    c.drawRect(skia.Rect.MakeWH(W, H), P(NAVY))
    gp = skia.Paint(Shader=skia.GradientShader.MakeRadial(skia.Point(W / 2, 900), 1200, [C(0x1A3D75), C(NAVYD)]))
    c.drawRect(skia.Rect.MakeWH(W, H), gp)
    # bandera dominicana sutil de fondo
    c.save(); c.translate(W / 2, 960); c.rotate(-8)
    a = 0.07
    c.drawRect(skia.Rect.MakeLTRB(-60, -1400, 60, 1400), P(WHITE, a))
    c.drawRect(skia.Rect.MakeLTRB(-1400, -60, 1400, 60), P(WHITE, a))
    c.drawRect(skia.Rect.MakeLTRB(60, -1400, 1400, -60), P(RED, 0.10))
    c.drawRect(skia.Rect.MakeLTRB(-1400, 60, -60, 1400), P(RED, 0.10))
    c.restore()
    kk = eo(pr(t, 61.8, 0.4))
    if kk > 0:
        chip(c, 'LA PREGUNTA', W / 2, 455, 34, RED, WHITE, kk, ic='bubble')
    lines = [(63.5, '¿Deben las', WHITE), (64.0, 'aerolíneas', WHITE), (64.55, 'compensar', RED), (65.15, 'a los pasajeros?', WHITE)]
    for i, (t0, s, col) in enumerate(lines):
        kl = eo(pr(t, t0, 0.4))
        if kl <= 0: continue
        y = 650 + i * 118
        size = 104 if i < 3 else 88
        if col == RED:
            wdt = tw(s, 'black', size)
            rrect(c, W / 2 - wdt / 2 - 22, y - 92 + (1 - kl) * 40, (wdt + 44) * kl, 118, 14, P(RED, 1))
            text(c, s, W / 2, y + (1 - kl) * 40, size, 'black', WHITE, kl, 'c')
        else:
            text(c, s, W / 2, y + (1 - kl) * 40, size, 'black', col, kl, 'c', shadow=10)
    ka = eo(pr(t, 65.9, 0.5))
    text(c, '…aunque la falla no fue suya', W / 2, 1150, 40, 'ital', LIGHT, ka, 'c')
    kp = eo(pr(t, 68.5, 0.45))
    if kp > 0:
        layer(c, kp)
        c.save(); c.translate(0, (1 - kp) * 80)
        text(c, 'COMENTA 1 O 2', W / 2, 1265, 52, 'black', WHITE, 1, 'c')
        for j, (lab, col, t0) in enumerate((('SÍ', DRBLUE, 68.96), ('NO', RED, 70.08))):
            x = 70 + j * 480
            hi = max(0, 1 - abs(t - t0 - 0.25) * 2.2) if t > t0 - 0.2 else 0
            sc = 1 + 0.07 * hi
            c.save(); c.translate(x + 230, 1440); c.scale(sc, sc); c.translate(-(x + 230), -1440)
            rrect(c, x, 1320, 460, 240, 28, P(col if j else 0x1D4C9A))
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, 1320, 460, 240), 28, 28), SP(WHITE, 4 + 4 * hi, 0.5 + 0.5 * hi))
            c.drawCircle(x + 110, 1440, 74, P(WHITE))
            text(c, str(j + 1), x + 110, 1477, 104, 'black', col if j else 0x1D4C9A, 1, 'c')
            text(c, '=', x + 228, 1470, 80, 'black', WHITE, 0.8, 'c')
            text(c, lab, x + 340, 1477, 104, 'black', WHITE, 1, 'c')
            c.restore()
        c.restore(); c.restore()

def outro(c, t):
    u = t - OUTRO
    c.drawRect(skia.Rect.MakeWH(W, H), P(NAVYD))
    gp = skia.Paint(Shader=skia.GradientShader.MakeRadial(skia.Point(W / 2, 860), 900, [C(0x1D4580), C(NAVYD)]))
    c.drawRect(skia.Rect.MakeWH(W, H), gp)
    # rayos sutiles
    c.save(); c.translate(W / 2, 860); c.rotate(u * 8)
    for i in range(12):
        c.rotate(30)
        c.drawPath(poly([(0, 0), (-60, -1300), (60, -1300)]), P(WHITE, 0.025))
    c.restore()
    cx, cy, r = W / 2 - 30, 830, 175
    kc = eio(pr(u, 0.1, 0.7))
    path = skia.Path(); path.addArc(skia.Rect.MakeLTRB(cx - r, cy - r, cx + r, cy + r), -90, 360 * kc)
    c.drawCircle(cx, cy, r, P(WHITE, 0.08 * kc))
    c.drawPath(path, SP(WHITE, 36))
    kh = eo(pr(u, 0.6, 0.4))
    if kh > 0:
        a0 = math.radians(45)
        x1, y1 = cx + (r + 18) * math.cos(a0), cy + (r + 18) * math.sin(a0)
        L = 190 * kh
        c.drawPath(limb(x1, y1, x1 + L * math.cos(a0), y1 + L * math.sin(a0), 56), P(RED))
    kq = back(pr(u, 0.75, 0.45), 2.2)
    if kq > 0:
        c.save(); c.translate(cx, cy); c.scale(kq, kq); c.rotate((1 - kq) * -30)
        text(c, '?', 0, 88, 250, 'black', WHITE, 1, 'c')
        c.restore()
    # destello
    gl = pr(u, 1.3, 0.6)
    if 0 < gl < 1:
        c.save(); c.clipPath(circ_path(cx, cy, r - 18), doAntiAlias=True)
        gx = cx - r + 2 * r * gl
        c.drawPath(poly([(gx - 30, cy - r), (gx + 30, cy - r), (gx - 70, cy + r), (gx - 130, cy + r)]), P(WHITE, 0.35))
        c.restore()
    k1 = eo(pr(u, 1.0, 0.5)); k2 = eo(pr(u, 1.2, 0.5)); k3 = eo(pr(u, 1.6, 0.5))
    text(c, 'CAPITAL', W / 2, 1250 + (1 - k1) * 50, 140, 'black', WHITE, k1, 'c')
    text(c, 'CURIOSO', W / 2, 1385 + (1 - k2) * 50, 140, 'black', RED, k2, 'c')
    if k3 > 0:
        chip(c, '@capitalcuriosoo', W / 2, 1450 + (1 - k3) * 30, 40, WHITE, NAVY, k3, tf='black')
    flag_bar(c, 1590, 10, k3)
    if u > TOTAL - VOFF - OUTRO - 0.5:
        c.drawRect(skia.Rect.MakeWH(W, H), P(0, pr(u, TOTAL - VOFF - OUTRO - 0.5, 0.5)))

SCENES = [(-9, scene1), (6.3, scene2), (17.0, scene3), (31.25, scene4), (43.0, scene5),
          (54.2, scene6), (61.5, scene7), (OUTRO, outro)]
WIPES = [6.3, 17.0, 23.3, 31.25, 43.0, 54.2, 61.5, OUTRO]

def wipe(c, t):
    for T in WIPES:
        u = (t - (T - 0.28)) / 0.56
        if 0 <= u <= 1:
            x = lerp(-1.6 * W, 1.6 * W, eio(u))
            c.save(); c.translate(x + W / 2, H / 2); c.skew(-0.25, 0)
            bw = W * 1.55
            c.drawRect(skia.Rect.MakeLTRB(-bw / 2, -H, bw / 2, H), P(NAVY))
            c.drawRect(skia.Rect.MakeLTRB(bw / 2 - 40, -H, bw / 2, H), P(RED))
            c.drawRect(skia.Rect.MakeLTRB(bw / 2 - 52, -H, bw / 2 - 40, H), P(WHITE))
            c.drawRect(skia.Rect.MakeLTRB(-bw / 2, -H, -bw / 2 + 24, H), P(DRBLUE))
            c.restore()

def render(c, tvid):
    t = tvid - VOFF
    fn = SCENES[0][1]
    for st, f in SCENES:
        if t >= st: fn = f
    c.clear(C(NAVYD))
    fn(c, t)
    if t < OUTRO:
        flag_bar(c, 0, 8, 0.9)
        brand_bug(c, t)
        subtitles(c, t)
    wipe(c, t)

def main():
    args = sys.argv[5:]
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr, colorType=skia.kRGBA_8888_ColorType)
    if args and args[0] == '--frames':
        for ts in args[1].split(','):
            with surf as c:
                render(c, float(ts))
            Image.fromarray(arr[:, :, :3].copy()).save(OUT.replace('.png', '') + f'_{float(ts):05.1f}.png')
        return
    t0 = float(args[0]) if args else 0.0
    t1 = float(args[1]) if len(args) > 1 else TOTAL
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}',
                           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                           '-pix_fmt', 'yuv420p', OUT], stdin=subprocess.PIPE)
    n0, n1 = int(round(t0 * FPS)), int(round(t1 * FPS))
    for i in range(n0, n1):
        with surf as c:
            render(c, i / FPS)
        ff.stdin.write(arr.tobytes())
        if i % 150 == 0:
            print(f'frame {i}/{n1}', file=sys.stderr)
    ff.stdin.close(); ff.wait()

if __name__ == '__main__':
    main()
