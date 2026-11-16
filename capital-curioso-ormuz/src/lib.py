import skia, math, json, os
import numpy as np

W, H, FPS = 1080, 1920, 30
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(BASE, 'imgs/imagenes_video_ormuz')
FONTS = os.path.join(BASE, 'fonts')

# ---------- colors ----------
def rgba(h, a=1.0):
    h = h.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return skia.ColorSetARGB(int(max(0, min(1, a)) * 255), r, g, b)

NAVY_D = '#06132E'
NAVY = '#0C2557'
NAVY_L = '#16397A'
BLUE = '#3D6FD1'
SKY = '#9DB9F0'
RED = '#EE3B4F'
RED_D = '#B01F33'
WHITE = '#FFFFFF'
GOLD = '#FFC94A'

# ---------- easing ----------
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x

def prog(t, a, b):
    if b <= a:
        return 1.0 if t >= a else 0.0
    return clamp((t - a) / (b - a))

def eo(x):  # ease out cubic
    x = clamp(x); return 1 - (1 - x) ** 3

def eio(x):
    x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2

def eback(x, s=1.70158):
    x = clamp(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2

def lerp(a, b, p):
    return a + (b - a) * p

def fade(t, a, b, fi=0.25, fo=0.25):
    """alpha that fades in at a and out at b"""
    return min(prog(t, a, a + fi), 1 - prog(t, b - fo, b)) if fo > 0 else prog(t, a, a + fi)

# ---------- paints ----------
def P(color, stroke=0, blur=0, cap_round=True):
    p = skia.Paint(AntiAlias=True, Color=color)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        if cap_round:
            p.setStrokeCap(skia.Paint.kRound_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p

SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)

# ---------- fonts ----------
_tf = {}
def face(name):
    if name not in _tf:
        path = {'anton': 'Anton.ttf', 'mont': 'Montserrat.ttf', 'oswald': 'Oswald.ttf', 'bebas': 'BebasNeue.ttf',
                'emoji': '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'}[name]
        if not path.startswith('/'):
            path = os.path.join(FONTS, path)
        _tf[name] = skia.Typeface.MakeFromFile(path)
    return _tf[name]

_fc = {}
def font(name, size):
    k = (name, round(size, 1))
    if k not in _fc:
        f = skia.Font(face(name), size)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        f.setSubpixel(True)
        _fc[k] = f
    return _fc[k]

def tw(s, name, size, track=0):
    f = font(name, size)
    return f.measureText(s) + track * max(0, len(s) - 1)

def text(c, s, x, y, name='mont', size=40, color=WHITE, alpha=1.0, align='center', shadow=0.0, track=0, stroke=0, stroke_color=NAVY_D):
    """y = vertical center of capitals"""
    if alpha <= 0.003 or not s:
        return 0
    f = font(name, size)
    m = f.getMetrics()
    cap = m.fCapHeight if m.fCapHeight > 0 else size * 0.7
    w = tw(s, name, size, track)
    if align == 'center':
        x0 = x - w / 2
    elif align == 'right':
        x0 = x - w
    else:
        x0 = x
    base = y + cap / 2

    def draw(paint, dx=0, dy=0):
        if track == 0:
            c.drawString(s, x0 + dx, base + dy, f, paint)
        else:
            xx = x0
            for ch in s:
                c.drawString(ch, xx + dx, base + dy, f, paint)
                xx += f.measureText(ch) + track
    if shadow > 0:
        draw(P(rgba('#000000', 0.75 * alpha * shadow), blur=size * 0.12), 0, size * 0.05)
    if stroke:
        draw(P(rgba(stroke_color, alpha), stroke=stroke))
    draw(P(rgba(color, alpha)))
    return w

def emoji(c, ch, x, y, size, alpha=1.0, scale=1.0):
    if alpha <= 0.003:
        return
    f = font('emoji', 109)  # bitmap strike size
    w = f.measureText(ch)
    s = size / 109 * scale
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(alpha))
    c.drawString(ch, -w / 2, 109 * 0.36, f, p)
    c.restore()

def wrap(s, name, size, maxw):
    words = s.split(' ')
    lines, cur = [], ''
    for w_ in words:
        cand = (cur + ' ' + w_).strip()
        if tw(cand, name, size) <= maxw or not cur:
            cur = cand
        else:
            lines.append(cur); cur = w_
    if cur:
        lines.append(cur)
    return lines

# ---------- shapes ----------
def rrect(c, x, y, w, h, r, color, alpha=1.0, stroke=0, blur=0):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), P(rgba(color, alpha), stroke=stroke, blur=blur))

def panel(c, x, y, w, h, alpha=1.0, r=26, fill=NAVY_D, fa=0.82, border=BLUE, accent=RED):
    if alpha <= 0.003:
        return
    rrect(c, x, y + 10, w, h, r, '#000000', 0.45 * alpha, blur=22)
    rrect(c, x, y, w, h, r, fill, fa * alpha)
    rrect(c, x, y, w, h, r, border, 0.55 * alpha, stroke=2)
    if accent:
        c.save()
        c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), doAntiAlias=True)
        c.drawRect(skia.Rect.MakeXYWH(x, y, 10, h), P(rgba(accent, alpha)))
        c.restore()

def circle(c, x, y, r, color, alpha=1.0, stroke=0, blur=0):
    c.drawCircle(x, y, r, P(rgba(color, alpha), stroke=stroke, blur=blur))

def glow_dot(c, x, y, r, color, alpha=1.0):
    circle(c, x, y, r * 2.6, color, 0.35 * alpha, blur=r * 1.4)
    circle(c, x, y, r, color, alpha)
    circle(c, x, y, r * 0.45, WHITE, alpha * 0.9)

def pulse(c, x, y, t, color=RED, maxr=80, period=1.2, n=2, alpha=1.0, width=4):
    for i in range(n):
        ph = ((t / period) + i / n) % 1.0
        r = maxr * eo(ph)
        circle(c, x, y, r, color, alpha * (1 - ph) * 0.9, stroke=width)

def line(c, pts, color, width, alpha=1.0, p=1.0, dash=None, blur=0, glow=False):
    """draw polyline partially (p in 0..1 by length)"""
    if p <= 0 or len(pts) < 2 or alpha <= 0:
        return None
    pts = [tuple(q) for q in pts]
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg)
    target = total * clamp(p)
    path = skia.Path(); path.moveTo(*pts[0])
    acc = 0; end = pts[0]; ang = 0
    for i, L in enumerate(seg):
        if acc + L >= target:
            f = (target - acc) / L if L > 0 else 0
            end = (lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f))
            path.lineTo(*end)
            ang = math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0])
            break
        path.lineTo(*pts[i + 1]); acc += L
        end = pts[i + 1]
        ang = math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0])
    if glow:
        c.drawPath(path, P(rgba(color, alpha * 0.5), stroke=width * 2.5, blur=width * 1.5))
    pt = P(rgba(color, alpha), stroke=width, blur=blur)
    if dash:
        pt.setPathEffect(skia.DashPathEffect.Make(dash, 0))
    c.drawPath(path, pt)
    return end, ang

def smooth(pts, n=12):
    """catmull-rom smoothing"""
    pts = [np.array(p, float) for p in pts]
    if len(pts) < 3:
        return [tuple(p) for p in pts]
    out = []
    P_ = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P_) - 2):
        p0, p1, p2, p3 = P_[i - 1], P_[i], P_[i + 1], P_[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append(tuple(q))
    out.append(tuple(pts[-1]))
    return out

def point_at(pts, p):
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg); target = total * clamp(p); acc = 0
    for i, L in enumerate(seg):
        if acc + L >= target:
            f = (target - acc) / L if L > 0 else 0
            return (lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f)), math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0])
        acc += L
    return pts[-1], 0

def arrowhead(c, x, y, ang, size, color, alpha=1.0):
    path = skia.Path()
    path.moveTo(x + math.cos(ang) * size, y + math.sin(ang) * size)
    path.lineTo(x + math.cos(ang + 2.5) * size * 0.8, y + math.sin(ang + 2.5) * size * 0.8)
    path.lineTo(x + math.cos(ang - 2.5) * size * 0.8, y + math.sin(ang - 2.5) * size * 0.8)
    path.close()
    c.drawPath(path, P(rgba(color, alpha)))

def flash(c, x, y, t0, t, size=90, color='#FFB347'):
    """explosion / impact flash at time t0"""
    d = t - t0
    if d < 0 or d > 1.0:
        return
    p = d / 1.0
    a = (1 - p) ** 1.5
    circle(c, x, y, size * (0.4 + 1.4 * eo(p)), color, 0.55 * a, blur=size * 0.5)
    circle(c, x, y, size * 0.5 * (1 - p) + 4, WHITE, a, blur=6)
    circle(c, x, y, size * (0.3 + 1.6 * eo(p)), RED, 0.9 * a, stroke=5)
    # sparks
    for k in range(10):
        ang = k * 2 * math.pi / 10 + t0 * 3
        r1 = size * 0.4 + size * 1.3 * eo(p)
        r0 = r1 * 0.75
        c.drawLine(x + math.cos(ang) * r0, y + math.sin(ang) * r0, x + math.cos(ang) * r1, y + math.sin(ang) * r1,
                   P(rgba(GOLD, a), stroke=3))

def xmark(c, x, y, size, p, color=RED, width=16, alpha=1.0):
    if p <= 0:
        return
    p1, p2 = clamp(p * 2), clamp(p * 2 - 1)
    s = size / 2
    circle(c, x, y, size * 0.8, color, 0.35 * alpha * clamp(p * 2), blur=size * 0.4)
    for (a, b, pp) in [((x - s, y - s), (x + s, y + s), p1), ((x + s, y - s), (x - s, y + s), p2)]:
        if pp > 0:
            e = (lerp(a[0], b[0], pp), lerp(a[1], b[1], pp))
            c.drawLine(a[0], a[1], e[0], e[1], P(rgba(WHITE, alpha), stroke=width + 8))
            c.drawLine(a[0], a[1], e[0], e[1], P(rgba(color, alpha), stroke=width))

def label_box(c, x, y, s, alpha=1.0, size=30, color=WHITE, bg=NAVY_D, accent=RED, name='mont', align='center', pad=18):
    w = tw(s, name, size) + pad * 2
    h = size * 1.55
    x0 = x - w / 2 if align == 'center' else (x if align == 'left' else x - w)
    rrect(c, x0, y - h / 2 + 4, w, h, 8, '#000000', 0.4 * alpha, blur=10)
    rrect(c, x0, y - h / 2, w, h, 8, bg, 0.9 * alpha)
    if accent:
        rrect(c, x0, y - h / 2, 7, h, 3, accent, alpha)
    text(c, s, x0 + w / 2 + (3 if accent else 0), y, name, size, color, alpha)
    return x0, w, h

def marker(c, x, y, label, t, t0, color=RED, side='up', dist=110, size=30, sub=None):
    p = prog(t, t0, t0 + 0.5)
    if p <= 0:
        return
    a = eo(p)
    pulse(c, x, y, t - t0, color, 46, 1.4, 2, a, 3)
    glow_dot(c, x, y, 9 * eback(p), color, a)
    dx, dy = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0),
              'ul': (-0.7, -0.7), 'ur': (0.7, -0.7), 'dl': (-0.7, 0.7), 'dr': (0.7, 0.7)}[side]
    ex, ey = x + dx * dist * eo(prog(t, t0 + 0.05, t0 + 0.4)), y + dy * dist * eo(prog(t, t0 + 0.05, t0 + 0.4))
    c.drawLine(x, y, ex, ey, P(rgba(WHITE, a * 0.9), stroke=3))
    pa = prog(t, t0 + 0.25, t0 + 0.6)
    if pa > 0:
        al = 'center'
        lx = ex
        if dx > 0.5: al = 'left'
        if dx < -0.5: al = 'right'
        if abs(dx) > 0.1 and abs(dy) > 0.1:
            al = 'left' if dx > 0 else 'right'
        ly = ey + (-size * 0.9 if dy < 0 and abs(dx) < 0.5 else 0) + (size * 0.9 if dy > 0 and abs(dx) < 0.5 else 0)
        c.save(); c.translate(lx, ly); s = lerp(0.7, 1, eback(pa)); c.scale(s, s)
        label_box(c, 0, 0, label, eo(pa), size, align=al, accent=color)
        if sub:
            text(c, sub, 0 if al == 'center' else (12 if al == 'left' else -12), size * 1.45, 'mont', size * 0.62, SKY, eo(pa), align=al, shadow=1)
        c.restore()

def source(c, s, t, t0, t1):
    a = fade(t, t0, t1, 0.4, 0.2)
    if a <= 0:
        return
    text(c, 'FUENTE: ' + s.upper(), 46, 1668, 'mont', 22, SKY, a * 0.95, align='left', shadow=1, track=1)

# ---------- photos ----------
_imgs = {}
def img(name):
    if name not in _imgs:
        _imgs[name] = skia.Image.open(os.path.join(IMG, name + '.jpg')).withDefaultMipmaps()
    return _imgs[name]

def photo(c, name, p, z0=1.0, z1=1.15, c0=None, c1=None, dark=0.3, tint=0.25, alpha=1.0):
    im = img(name)
    iw, ih = im.width(), im.height()
    sc = max(W / iw, H / ih)
    z = lerp(z0, z1, p)
    s = sc * z
    c0 = c0 or (iw / 2, ih / 2); c1 = c1 or c0
    cx, cy = lerp(c0[0], c1[0], p), lerp(c0[1], c1[1], p)
    hw, hh = W / 2 / s, H / 2 / s
    cx = clamp(cx, hw, iw - hw) if iw > 2 * hw else iw / 2
    cy = clamp(cy, hh, ih - hh) if ih > 2 * hh else ih / 2
    if alpha < 1:
        c.saveLayerAlpha(None, int(alpha * 255))
    c.save()
    c.translate(W / 2, H / 2); c.scale(s, s); c.translate(-cx, -cy)
    c.drawImage(im, 0, 0, SAMP)
    c.restore()
    # grade
    c.drawRect(skia.Rect.MakeWH(W, H), P(rgba('#000000', dark)))
    c.drawRect(skia.Rect.MakeWH(W, H), P(rgba(NAVY, tint)))
    vignette(c)
    if alpha < 1:
        c.restore()
    return (lambda x, y: ((x - cx) * s + W / 2, (y - cy) * s + H / 2)), s

def vignette(c, strength=1.0):
    sh = skia.GradientShader.MakeRadial((W / 2, H / 2), H * 0.72,
                                        [rgba('#000000', 0), rgba('#000000', 0.25 * strength), rgba('#000000', 0.88 * strength)],
                                        [0.0, 0.55, 1.0])
    p = skia.Paint(Shader=sh); c.drawRect(skia.Rect.MakeWH(W, H), p)
    # top band for subtitles readability, bottom band
    sh2 = skia.GradientShader.MakeLinear([(0, 0), (0, 520)], [rgba(NAVY_D, 0.85 * strength), rgba(NAVY_D, 0)])
    c.drawRect(skia.Rect.MakeWH(W, 520), skia.Paint(Shader=sh2))
    sh3 = skia.GradientShader.MakeLinear([(0, H - 520), (0, H)], [rgba(NAVY_D, 0), rgba(NAVY_D, 0.9 * strength)])
    c.drawRect(skia.Rect.MakeXYWH(0, H - 520, W, 520), skia.Paint(Shader=sh3))

def navy_bg(c, t, grid=True):
    sh = skia.GradientShader.MakeRadial((W / 2, H * 0.45), H * 0.8, [rgba(NAVY_L), rgba(NAVY), rgba(NAVY_D)], [0, 0.45, 1])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
    if grid:
        p = P(rgba(SKY, 0.07), stroke=1.5)
        off = (t * 20) % 90
        for x in range(-90, W + 90, 90):
            c.drawLine(x + off, 0, x + off, H, p)
        for y in range(-90, H + 90, 90):
            c.drawLine(0, y + off, W, y + off, p)

# ---------- geo ----------
GEO = os.path.join(BASE, 'geo')
_geo = {}
def countries(res='50'):
    if res not in _geo:
        d = json.load(open(os.path.join(GEO, f'countries{res}.geojson')))
        out = []
        for f in d['features']:
            g = f['geometry']
            if g is None:
                continue
            polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
            rings = []
            for poly in polys:
                for ring in poly:
                    rings.append(np.array(ring, float))
            out.append((f['properties']['name'], rings))
        _geo[res] = out
    return _geo[res]

class RegionMap:
    def __init__(self, lon0, lon1, lat0, lat1, rect, res='50', fit='contain'):
        self.lon0, self.lon1, self.lat0, self.lat1 = lon0, lon1, lat0, lat1
        x, y, w, h = rect
        self.rect = rect
        self.cosl = math.cos(math.radians((lat0 + lat1) / 2))
        kx = w / ((lon1 - lon0) * self.cosl)
        ky = h / (lat1 - lat0)
        self.k = min(kx, ky) if fit == 'contain' else max(kx, ky)
        self.cx, self.cy = x + w / 2, y + h / 2
        self.lonc, self.latc = (lon0 + lon1) / 2, (lat0 + lat1) / 2
        self.paths = {}
        pad = 25
        for name, rings in countries(res):
            path = skia.Path(); used = False
            for r in rings:
                if (r[:, 0].max() < lon0 - pad or r[:, 0].min() > lon1 + pad or
                        r[:, 1].max() < lat0 - pad or r[:, 1].min() > lat1 + pad):
                    continue
                xs = self.cx + (r[:, 0] - self.lonc) * self.cosl * self.k
                ys = self.cy - (r[:, 1] - self.latc) * self.k
                path.moveTo(xs[0], ys[0])
                for i in range(1, len(xs)):
                    path.lineTo(xs[i], ys[i])
                path.close(); used = True
            if used:
                self.paths[name] = path

    def xy(self, lon, lat):
        return (self.cx + (lon - self.lonc) * self.cosl * self.k, self.cy - (lat - self.latc) * self.k)

    def draw(self, c, alpha=1.0, hl=None, t=0, land='#1C3A70', border='#5B86D6', ocean='#071A3C', dim=None, clip=True, rr=24, grid=True):
        """hl: dict name -> (color, strength)"""
        if alpha <= 0.003:
            return
        x, y, w, h = self.rect
        c.save()
        if clip:
            c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), rr, rr), doAntiAlias=True)
        if alpha < 1:
            c.saveLayerAlpha(None, int(alpha * 255))
        if ocean:
            sh = skia.GradientShader.MakeRadial((x + w / 2, y + h / 2), max(w, h) * 0.75, [rgba('#0B2552'), rgba(ocean)], [0, 1])
            c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), skia.Paint(Shader=sh))
        if grid:
            gp = P(rgba(SKY, 0.10), stroke=1)
            for lon in range(int(self.lon0) - 20, int(self.lon1) + 20):
                if lon % 5 == 0:
                    a = self.xy(lon, self.lat0 - 20); b = self.xy(lon, self.lat1 + 20)
                    c.drawLine(a[0], a[1], b[0], b[1], gp)
            for lat in range(int(self.lat0) - 20, int(self.lat1) + 20):
                if lat % 5 == 0:
                    a = self.xy(self.lon0 - 20, lat); b = self.xy(self.lon1 + 20, lat)
                    c.drawLine(a[0], a[1], b[0], b[1], gp)
        fillp = P(rgba(land)); bp = P(rgba(border, 0.8), stroke=1.6)
        for name, path in self.paths.items():
            c.drawPath(path, fillp)
        hl = hl or {}
        for name, (col, st) in hl.items():
            if name in self.paths and st > 0:
                c.drawPath(self.paths[name], P(rgba(col, 0.55 * st), blur=14))
                c.drawPath(self.paths[name], P(rgba(col, 0.75 * st)))
        for name, path in self.paths.items():
            c.drawPath(path, bp)
        for name, (col, st) in hl.items():
            if name in self.paths and st > 0:
                c.drawPath(self.paths[name], P(rgba('#FFD0D6', st), stroke=3))
        if alpha < 1:
            c.restore()
        c.restore()
        if clip:
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), rr, rr), P(rgba(BLUE, 0.7 * alpha), stroke=2.5))

    def clip(self, c, rr=24):
        x, y, w, h = self.rect
        c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), rr, rr), doAntiAlias=True)

# ---------- icons ----------
def _poly(pts, sx, sy, x, y, rot=0):
    path = skia.Path()
    cr, sr = math.cos(rot), math.sin(rot)
    for i, (px, py) in enumerate(pts):
        qx, qy = px * sx, py * sy
        X, Y = x + qx * cr - qy * sr, y + qx * sr + qy * cr
        (path.moveTo if i == 0 else path.lineTo)(X, Y)
    path.close()
    return path

def carrier(c, x, y, size, color=WHITE, alpha=1.0, flip=False):
    """side profile aircraft carrier, size = length"""
    f = -1 if flip else 1
    hull = [(-0.5, -0.04), (0.5, -0.04), (0.5, 0.0), (0.38, 0.13), (-0.44, 0.13), (-0.5, 0.03)]
    c.drawPath(_poly(hull, size * f, size, x, y), P(rgba(color, alpha)))
    island = [(0.08, -0.04), (0.08, -0.17), (0.12, -0.21), (0.2, -0.21), (0.2, -0.04)]
    c.drawPath(_poly(island, size * f, size, x, y), P(rgba(color, alpha)))
    c.drawLine(x + 0.14 * size * f, y - 0.21 * size, x + 0.14 * size * f, y - 0.3 * size, P(rgba(color, alpha), stroke=max(2, size * 0.015)))
    # little jets on deck
    for jx in (-0.38, -0.25, -0.12, 0.3):
        jet = [(jx, -0.04), (jx + 0.06, -0.04), (jx + 0.035, -0.075)]
        c.drawPath(_poly(jet, size * f, size, x, y), P(rgba(color, alpha * 0.9)))

def tanker(c, x, y, size, color=WHITE, alpha=1.0, flip=False, accent=RED):
    f = -1 if flip else 1
    hull = [(-0.5, -0.02), (0.5, -0.06), (0.42, 0.12), (-0.46, 0.12)]
    c.drawPath(_poly(hull, size * f, size, x, y), P(rgba(color, alpha)))
    stripe = [(-0.47, 0.06), (0.45, 0.06), (0.43, 0.09), (-0.46, 0.09)]
    c.drawPath(_poly(stripe, size * f, size, x, y), P(rgba(accent, alpha)))
    house = [(-0.44, -0.02), (-0.44, -0.2), (-0.28, -0.2), (-0.28, -0.02)]
    c.drawPath(_poly(house, size * f, size, x, y), P(rgba(color, alpha)))
    stack = [(-0.41, -0.2), (-0.41, -0.28), (-0.35, -0.28), (-0.35, -0.2)]
    c.drawPath(_poly(stack, size * f, size, x, y), P(rgba(accent, alpha)))
    for k in range(4):
        tx = -0.18 + k * 0.16
        tank = [(tx, -0.03), (tx, -0.09), (tx + 0.12, -0.09), (tx + 0.12, -0.035)]
        c.drawPath(_poly(tank, size * f, size, x, y), P(rgba(color, alpha * 0.85)))

def warship(c, x, y, size, color=WHITE, alpha=1.0, flip=False):
    f = -1 if flip else 1
    hull = [(-0.5, -0.02), (0.5, -0.05), (0.38, 0.1), (-0.46, 0.1)]
    c.drawPath(_poly(hull, size * f, size, x, y), P(rgba(color, alpha)))
    sup = [(-0.25, -0.02), (-0.2, -0.16), (0.05, -0.16), (0.12, -0.03)]
    c.drawPath(_poly(sup, size * f, size, x, y), P(rgba(color, alpha)))
    c.drawLine(x - 0.08 * size * f, y - 0.16 * size, x - 0.08 * size * f, y - 0.3 * size, P(rgba(color, alpha), stroke=max(2, size * 0.02)))
    c.drawLine(x + 0.25 * size * f, y - 0.05 * size, x + 0.4 * size * f, y - 0.09 * size, P(rgba(color, alpha), stroke=max(2, size * 0.025)))

def ship_top(c, x, y, ang, size, color=WHITE, alpha=1.0):
    pts = [(0.5, 0), (0.25, 0.16), (-0.5, 0.16), (-0.5, -0.16), (0.25, -0.16)]
    c.drawPath(_poly(pts, size, size, x, y, ang), P(rgba(color, alpha)))

def drone(c, x, y, ang, size, color=WHITE, alpha=1.0):
    pts = [(0.55, 0), (-0.1, 0.5), (-0.3, 0.5), (-0.15, 0.08), (-0.45, 0.06), (-0.45, -0.06), (-0.15, -0.08), (-0.3, -0.5), (-0.1, -0.5)]
    c.drawPath(_poly(pts, size, size, x, y, ang), P(rgba(color, alpha)))

def missile(c, x, y, size, color=WHITE, alpha=1.0, rot=0):
    body = [(0, -0.5), (0.07, -0.36), (0.07, 0.38), (0.16, 0.5), (-0.16, 0.5), (-0.07, 0.38), (-0.07, -0.36)]
    c.drawPath(_poly(body, size, size, x, y, rot), P(rgba(color, alpha)))
    tip = [(0, -0.5), (0.07, -0.36), (-0.07, -0.36)]
    c.drawPath(_poly(tip, size, size, x, y, rot), P(rgba(RED, alpha)))

def container_icon(c, x, y, w, h, color=RED, alpha=1.0):
    rrect(c, x - w / 2, y - h / 2, w, h, 6, color, alpha)
    for k in range(1, 8):
        xx = x - w / 2 + k * w / 8
        c.drawLine(xx, y - h / 2 + 8, xx, y + h / 2 - 8, P(rgba('#000000', 0.35 * alpha), stroke=4))
    rrect(c, x - w / 2, y - h / 2, w, h, 6, WHITE, 0.8 * alpha, stroke=3)

# ---------- flags ----------
def flag(c, kind, x, y, w, alpha=1.0, wave_t=None):
    h = w * 0.62
    x0, y0 = x - w / 2, y - h / 2
    c.save()
    if alpha < 1:
        c.saveLayerAlpha(None, int(alpha * 255))
    rrect(c, x0, y0 + 6, w, h, 8, '#000000', 0.45, blur=12)
    c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0, y0, w, h), 8, 8), doAntiAlias=True)
    R = lambda xx, yy, ww, hh, col: c.drawRect(skia.Rect.MakeXYWH(xx, yy, ww, hh), P(rgba(col)))
    if kind == 'us':
        for i in range(13):
            R(x0, y0 + i * h / 13, w, h / 13 + 0.5, '#B22234' if i % 2 == 0 else '#FFFFFF')
        R(x0, y0, w * 0.4, h * 7 / 13, '#3C3B6E')
        for i in range(5):
            for j in range(6):
                circle(c, x0 + w * 0.4 * (j + 0.5) / 6, y0 + h * 7 / 13 * (i + 0.5) / 5, w * 0.012, WHITE)
    elif kind == 'il':
        R(x0, y0, w, h, '#FFFFFF')
        R(x0, y0 + h * 0.1, w, h * 0.15, '#0038B8'); R(x0, y0 + h * 0.75, w, h * 0.15, '#0038B8')
        r = h * 0.2
        for rot in (0, math.pi):
            pts = [(math.sin(rot + k * 2 * math.pi / 3) * r, -math.cos(rot + k * 2 * math.pi / 3) * r) for k in range(3)]
            path = skia.Path(); path.moveTo(x + pts[0][0], y + pts[0][1]); path.lineTo(x + pts[1][0], y + pts[1][1]); path.lineTo(x + pts[2][0], y + pts[2][1]); path.close()
            c.drawPath(path, P(rgba('#0038B8'), stroke=w * 0.025, cap_round=False))
    elif kind == 'ir':
        R(x0, y0, w, h / 3, '#239F40'); R(x0, y0 + h / 3, w, h / 3, '#FFFFFF'); R(x0, y0 + 2 * h / 3, w, h / 3 + 1, '#DA0000')
        circle(c, x, y, h * 0.11, '#DA0000', stroke=w * 0.02)
        c.drawLine(x, y - h * 0.13, x, y + h * 0.13, P(rgba('#DA0000'), stroke=w * 0.02))
    elif kind == 'do':
        R(x0, y0, w, h, '#FFFFFF')
        cw, ch = w * 0.43, h * 0.4
        R(x0, y0, cw, ch, '#002D62'); R(x0 + w - cw, y0, cw, ch, '#CE1126')
        R(x0, y0 + h - ch, cw, ch, '#CE1126'); R(x0 + w - cw, y0 + h - ch, cw, ch, '#002D62')
        circle(c, x, y, h * 0.09, '#2E7D32')
    # sheen
    sh = skia.GradientShader.MakeLinear([(x0, y0), (x0 + w, y0 + h)], [rgba('#FFFFFF', 0.18), rgba('#FFFFFF', 0), rgba('#000000', 0.15)], [0, 0.5, 1])
    c.drawRect(skia.Rect.MakeXYWH(x0, y0, w, h), skia.Paint(Shader=sh))
    if alpha < 1:
        c.restore()
    c.restore()
    rrect(c, x0, y0, w, h, 8, WHITE, 0.5 * alpha, stroke=2)

def radar(c, x, y, r, t, alpha=1.0, color='#4CFF9A'):
    if alpha <= 0:
        return
    circle(c, x, y, r, '#04140C', 0.55 * alpha)
    for k in (1, 2, 3):
        circle(c, x, y, r * k / 3, color, 0.45 * alpha, stroke=2)
    c.drawLine(x - r, y, x + r, y, P(rgba(color, 0.3 * alpha), stroke=1.5))
    c.drawLine(x, y - r, x, y + r, P(rgba(color, 0.3 * alpha), stroke=1.5))
    ang = (t * 220) % 360
    sh = skia.GradientShader.MakeSweep(x, y, [rgba(color, 0), rgba(color, 0), rgba(color, 0.65 * alpha)], [0, 0.75, 1.0],
                                       localMatrix=skia.Matrix.RotateDeg(ang, (x, y)))
    c.drawCircle(x, y, r, skia.Paint(AntiAlias=True, Shader=sh))
    a = math.radians(ang)
    c.drawLine(x, y, x + math.cos(a) * r, y + math.sin(a) * r, P(rgba(color, alpha), stroke=3))
    circle(c, x, y, r, color, 0.9 * alpha, stroke=3)

def donut(c, x, y, r, p, alpha=1.0, width=46):
    circle(c, x, y, r, NAVY_L, 0.9 * alpha, stroke=width)
    rect = skia.Rect.MakeXYWH(x - r, y - r, 2 * r, 2 * r)
    if p > 0:
        c.drawArc(rect, -90, 360 * p, False, P(rgba(RED, 0.5 * alpha), stroke=width + 10, blur=12, cap_round=False))
        c.drawArc(rect, -90, 360 * p, False, P(rgba(RED, alpha), stroke=width, cap_round=False))

def crack(c, x0, y0, x1, y1, p, seed=3, color=WHITE, alpha=1.0, width=6):
    rng = np.random.RandomState(seed)
    n = 9
    pts = []
    for i in range(n + 1):
        f = i / n
        jx = rng.uniform(-28, 28) if 0 < i < n else 0
        pts.append((lerp(x0, x1, f) + jx, lerp(y0, y1, f) + rng.uniform(-10, 10)))
    line(c, pts, RED, width * 2.2, alpha, p, glow=True)
    line(c, pts, color, width * 0.6, alpha, p)
    # branches
    for i in range(2, n - 1, 2):
        if p * n > i:
            bx, by = pts[i]
            ang = rng.uniform(-1, 1) + (math.pi / 2 if rng.rand() > .5 else -math.pi / 2)
            L = rng.uniform(30, 70)
            q = clamp(p * n - i)
            c.drawLine(bx, by, bx + math.cos(ang) * L * q, by + math.sin(ang) * L * q, P(rgba(color, alpha * 0.8), stroke=width * 0.4))
