"""Utilidades compartidas: colores, easing, cámara, polilíneas y primitivas de dibujo estilo cómic."""
import math
import random
import cairo
import numpy as np

W, H, FPS = 1080, 1920, 30


def C(h, a=1.0):
    h = h.lstrip('#')
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def mix(c1, c2, t):
    t = clamp(t)
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(4))


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def ss(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def eio(t):
    t = clamp(t)
    return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2


def lin(t):
    return clamp(t)


def back(t):
    t = clamp(t)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def prog(t, a, b, f=ss):
    if b <= a:
        return 1.0 if t >= b else 0.0
    return f((t - a) / (b - a))


def pulse(t, a, b):
    """0 -> 1 -> 0 en [a,b]."""
    if t <= a or t >= b:
        return 0.0
    u = (t - a) / (b - a)
    return math.sin(u * math.pi)


def window(t, a, b, fi=0.3, fo=0.3):
    return prog(t, a, a + fi) * (1 - prog(t, b - fo, b))


# ---------------------------------------------------------------- paleta
PAL = dict(
    ink=C('#1d1d22'),
    sky1=C('#7fbfe3'), sky2=C('#cdeaf6'),
    cloud=C('#ffffff'), cloud_sh=C('#d5e6f0'),
    grass=C('#a9d36e'), grass2=C('#93c25c'), grass3=C('#bfe08a'),
    wall_pink=C('#f0bfb1'), wall_pink2=C('#e3a99b'),
    wall_beige=C('#f1dcbc'), wall_beige2=C('#e2c8a2'),
    roof=C('#d77e68'), roof2=C('#b9644f'),
    tile=C('#bfe2ec'), tile2=C('#b2d9e5'), grout=C('#9ccad8'),
    porcelain=C('#fbfbf8'), porc_sh=C('#dbe2e7'), porc_sh2=C('#c4cfd7'),
    inner=C('#dbe5ec'), inner2=C('#cad7e0'),
    water=C('#6fcaf2'), water2=C('#3fa9df'), water_hi=C('#c8f0ff'),
    used=C('#8ea9c0'), used2=C('#6a8aa5'),
    soil=C('#dcc39d'), soil2=C('#c8aa7f'), soil3=C('#b8976b'),
    concrete=C('#cfc9c0'), concrete2=C('#b9b2a7'),
    pipe=C('#e3e5e2'), pipe_in=C('#6f7d87'),
    chrome=C('#c9d4dc'), chrome2=C('#9fb0bc'),
    red=C('#e2504a'), red_soft=C('#ec7b78'),
    green=C('#6cbf57'), green2=C('#4f9f3f'),
    odor=C('#a9d48c'), odor2=C('#86b86b'),
    rubber=C('#c75a50'), float=C('#f2a65a'),
    street=C('#a7a8a6'), street2=C('#8f908e'), side=C('#e6dcc8'),
    skin=C('#f3c9a2'), skin2=C('#dea67f'), sleeve=C('#8fc3e0'),
    white=C('#ffffff'),
)


def setc(ctx, c, a=None):
    if a is None:
        ctx.set_source_rgba(*c)
    else:
        ctx.set_source_rgba(c[0], c[1], c[2], c[3] * a)


class Pen:
    """Estado de dibujo: zoom actual para que los contornos sean finos y estables en pantalla."""
    z = 1.0

    @staticmethod
    def L(px):
        return px * (Pen.z ** 0.35) / Pen.z


def fs(ctx, fill, lw=3.0, stroke=None, preserve=False):
    """Rellena y contornea el path actual."""
    if fill is not None:
        setc(ctx, fill)
        ctx.fill_preserve()
    if lw:
        setc(ctx, stroke or PAL['ink'])
        ctx.set_line_width(Pen.L(lw))
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke_preserve()
    if not preserve:
        ctx.new_path()


def rrect(ctx, x0, y0, x1, y1, r):
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    ctx.new_sub_path()
    ctx.arc(x1 - r, y0 + r, r, -math.pi / 2, 0)
    ctx.arc(x1 - r, y1 - r, r, 0, math.pi / 2)
    ctx.arc(x0 + r, y1 - r, r, math.pi / 2, math.pi)
    ctx.arc(x0 + r, y0 + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def poly(ctx, pts, close=True):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    if close:
        ctx.close_path()


def lgrad(x0, y0, x1, y1, stops):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for o, c in stops:
        g.add_color_stop_rgba(o, *c)
    return g


def rgrad(cx, cy, r0, r1, stops):
    g = cairo.RadialGradient(cx, cy, r0, cx, cy, r1)
    for o, c in stops:
        g.add_color_stop_rgba(o, *c)
    return g


# ---------------------------------------------------------------- polilíneas
def bez(p0, p1, p2, p3, n=20):
    out = []
    for i in range(1, n + 1):
        u = i / n
        a = (1 - u) ** 3
        b = 3 * (1 - u) ** 2 * u
        c = 3 * (1 - u) * u * u
        d = u ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                    a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


class PL:
    """Polilínea con longitud de arco."""

    def __init__(self, start, *segs):
        pts = [start]
        for s in segs:
            if len(s) == 1:
                pts.append(s[0])
            else:
                pts += bez(pts[-1], s[0], s[1], s[2])
        self.p = pts
        self.cum = [0.0]
        for i in range(1, len(pts)):
            self.cum.append(self.cum[-1] + math.dist(pts[i - 1], pts[i]))
        self.len = self.cum[-1]

    def at(self, s):
        s = clamp(s, 0, self.len)
        for i in range(1, len(self.p)):
            if self.cum[i] >= s:
                seg = self.cum[i] - self.cum[i - 1]
                u = 0 if seg == 0 else (s - self.cum[i - 1]) / seg
                a, b = self.p[i - 1], self.p[i]
                return (lerp(a[0], b[0], u), lerp(a[1], b[1], u))
        return self.p[-1]

    def tangent(self, s):
        a = self.at(s - 2)
        b = self.at(s + 2)
        d = math.dist(a, b) or 1
        return ((b[0] - a[0]) / d, (b[1] - a[1]) / d)

    def path(self, ctx, s0=0, s1=None):
        if s1 is None:
            s1 = self.len
        s0 = clamp(s0, 0, self.len)
        s1 = clamp(s1, 0, self.len)
        if s1 <= s0:
            return False
        ctx.move_to(*self.at(s0))
        for i in range(len(self.p)):
            if s0 < self.cum[i] < s1:
                ctx.line_to(*self.p[i])
        ctx.line_to(*self.at(s1))
        return True

    def stroke(self, ctx, col, w, s0=0, s1=None, cap=cairo.LINE_CAP_BUTT, px=False):
        if self.path(ctx, s0, s1):
            setc(ctx, col)
            ctx.set_line_width(Pen.L(w) if px else w)
            ctx.set_line_cap(cap)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.stroke()


# ---------------------------------------------------------------- cámara
class Cam:
    """Spline de Hermite sobre (t, cx, cy, zoom) -> movimiento continuo sin paradas bruscas."""

    def __init__(self, keys):
        self.k = sorted(keys)

    def at(self, t):
        k = self.k
        if t <= k[0][0]:
            return k[0][1:]
        if t >= k[-1][0]:
            return k[-1][1:]
        i = 0
        while k[i + 1][0] < t:
            i += 1
        t0, t1 = k[i][0], k[i + 1][0]
        u = (t - t0) / (t1 - t0)
        dt = t1 - t0

        def v(j, c):
            x = k[j][c]
            return math.log(x) if c == 3 else x

        out = []
        for c in (1, 2, 3):
            p0, p1 = v(i, c), v(i + 1, c)
            m0 = (v(i + 1, c) - v(i - 1, c)) / (k[i + 1][0] - k[i - 1][0]) if i > 0 else (p1 - p0) / dt * 0.5
            m1 = (v(i + 2, c) - v(i, c)) / (k[i + 2][0] - k[i][0]) if i + 2 < len(k) else (p1 - p0) / dt * 0.5
            h00 = 2 * u ** 3 - 3 * u ** 2 + 1
            h10 = u ** 3 - 2 * u ** 2 + u
            h01 = -2 * u ** 3 + 3 * u ** 2
            h11 = u ** 3 - u ** 2
            x = h00 * p0 + h10 * dt * m0 + h01 * p1 + h11 * dt * m1
            out.append(math.exp(x) if c == 3 else x)
        return out


def apply_cam(ctx, cx, cy, z, t, drift=1.0):
    # pequeño vaivén tipo dron: la cámara nunca está quieta
    cx += drift * 9 / z * math.sin(t * 0.61)
    cy += drift * 7 / z * math.sin(t * 0.47 + 1.3)
    ctx.translate(W / 2, H / 2)
    ctx.rotate(drift * 0.006 * math.sin(t * 0.33))
    ctx.scale(z, z)
    ctx.translate(-cx, -cy)
    Pen.z = z


# ---------------------------------------------------------------- adornos de cómic
def sparkle(ctx, x, y, r, a=1.0, col=None):
    if a <= 0 or r <= 0:
        return
    col = col or PAL['white']
    ctx.save()
    ctx.translate(x, y)
    ctx.move_to(0, -r)
    for k in range(4):
        ang = k * math.pi / 2
        ctx.curve_to(r * 0.12 * math.sin(ang) + 0, -r * 0.12 * math.cos(ang) + 0,
                     0, 0, 0, 0)
    ctx.new_path()
    # estrella de 4 puntas
    pts = []
    for k in range(8):
        ang = k * math.pi / 4 - math.pi / 2
        rr = r if k % 2 == 0 else r * 0.28
        pts.append((rr * math.cos(ang), rr * math.sin(ang)))
    poly(ctx, pts)
    setc(ctx, col, a)
    ctx.fill()
    ctx.restore()


def cloud_shape(ctx, x, y, s):
    """Nube de caricatura (path)."""
    bumps = [(-0.9, 0.15, 0.45), (-0.45, -0.2, 0.55), (0.15, -0.35, 0.65), (0.7, -0.05, 0.5), (1.0, 0.2, 0.38)]
    ctx.new_sub_path()
    ctx.move_to(x - 1.25 * s, y + 0.45 * s)
    for bx, by, br in bumps:
        pass
    ctx.new_path()
    for bx, by, br in bumps:
        ctx.new_sub_path()
        ctx.arc(x + bx * s, y + by * s, br * s, 0, 2 * math.pi)
    rrect(ctx, x - 1.3 * s, y - 0.05 * s, x + 1.35 * s, y + 0.55 * s, 0.3 * s)


def cloud(ctx, x, y, s, a=1.0):
    if a <= 0:
        return
    ctx.push_group()
    # contorno: dibujar sombra/contorno ensanchado
    cloud_shape(ctx, x, y, s)
    setc(ctx, PAL['ink'])
    ctx.set_line_width(Pen.L(3.2) * 2)
    ctx.stroke_preserve()
    setc(ctx, PAL['cloud'])
    ctx.fill()
    # sombreado inferior
    ctx.save()
    cloud_shape(ctx, x, y, s)
    ctx.clip()
    setc(ctx, PAL['cloud_sh'])
    ctx.rectangle(x - 2 * s, y + 0.25 * s, 4 * s, s)
    ctx.fill()
    ctx.restore()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)


def arrow(ctx, pl, s0, s1, w=14, col=None, a=1.0):
    """Flecha de movimiento a lo largo de una polilínea (relleno + contorno)."""
    if a <= 0 or s1 - s0 < 5:
        return
    col = col or PAL['white']
    ctx.save()
    ctx.push_group()
    head = w * 1.9
    pl.path(ctx, s0, s1 - head * 0.7)
    setc(ctx, PAL['ink'])
    ctx.set_line_width(w + Pen.L(3) * 2)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    tip = pl.at(s1)
    tx, ty = pl.tangent(s1 - 3)
    nx, ny = -ty, tx
    bx, by = tip[0] - tx * head, tip[1] - ty * head
    tri = [tip, (bx + nx * head * 0.75, by + ny * head * 0.75), (bx - nx * head * 0.75, by - ny * head * 0.75)]
    poly(ctx, tri)
    ctx.set_line_width(Pen.L(3) * 2)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke_preserve()
    ctx.fill()
    pl.path(ctx, s0, s1 - head * 0.7)
    setc(ctx, col)
    ctx.set_line_width(w)
    ctx.stroke()
    poly(ctx, tri)
    ctx.fill()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def burst(ctx, x, y, r, a, n=10, col=None, lw=4):
    """Líneas radiales tipo 'impacto' de cómic."""
    if a <= 0:
        return
    col = col or PAL['ink']
    setc(ctx, col, a)
    ctx.set_line_width(Pen.L(lw))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for k in range(n):
        ang = k * 2 * math.pi / n + 0.3
        ctx.move_to(x + math.cos(ang) * r * 0.6, y + math.sin(ang) * r * 0.6)
        ctx.line_to(x + math.cos(ang) * r, y + math.sin(ang) * r)
    ctx.stroke()


def check_badge(ctx, x, y, r, s):
    """Check verde con pop."""
    if s <= 0:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.arc(4, 6, r, 0, 2 * math.pi)
    setc(ctx, C('#000000', 0.18))
    ctx.fill()
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source(rgrad(-r * .3, -r * .3, 0, r * 1.2, [(0, C('#8fd77a')), (1, PAL['green2'])]))
    ctx.fill_preserve()
    setc(ctx, PAL['ink'])
    ctx.set_line_width(Pen.L(3.5))
    ctx.stroke()
    poly(ctx, [(-r * .45, 0), (-r * .1, r * .35), (r * .5, -r * .35)], close=False)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    setc(ctx, PAL['ink'])
    ctx.set_line_width(r * 0.34)
    ctx.stroke_preserve()
    setc(ctx, PAL['white'])
    ctx.set_line_width(r * 0.22)
    ctx.stroke()
    ctx.restore()


def odor_cloud(ctx, x, y, s, a=1.0, wob=0.0):
    """Nubecita verde de olor (caricatura, con carita gruñona)."""
    if a <= 0:
        return
    ctx.push_group()
    pts = [(-0.55, 0.1, 0.5), (0.0, -0.25, 0.6), (0.55, 0.05, 0.5), (0.05, 0.3, 0.5)]
    for bx, by, br in pts:
        ctx.new_sub_path()
        ctx.arc(x + bx * s, y + by * s, br * s * (1 + 0.06 * math.sin(wob * 6 + bx * 4)), 0, 2 * math.pi)
    setc(ctx, PAL['ink'])
    ctx.set_line_width(Pen.L(3) * 2)
    ctx.stroke_preserve()
    setc(ctx, PAL['odor'])
    ctx.fill()
    # carita
    setc(ctx, PAL['ink'])
    for ex in (-0.22, 0.22):
        ctx.arc(x + ex * s, y - 0.02 * s, 0.075 * s, 0, 2 * math.pi)
        ctx.fill()
    ctx.set_line_width(Pen.L(2.5))
    ctx.move_to(x - 0.36 * s, y - 0.22 * s)
    ctx.line_to(x - 0.1 * s, y - 0.14 * s)
    ctx.move_to(x + 0.36 * s, y - 0.22 * s)
    ctx.line_to(x + 0.1 * s, y - 0.14 * s)
    ctx.stroke()
    ctx.arc(x, y + 0.24 * s, 0.13 * s, math.pi * 1.1, math.pi * 1.9)
    ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)


def x_mark(ctx, x, y, r, s):
    if s <= 0:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    for w, col in ((r * 0.5, PAL['ink']), (r * 0.32, PAL['red'])):
        setc(ctx, col)
        ctx.set_line_width(w)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(-r, -r)
        ctx.line_to(r, r)
        ctx.move_to(r, -r)
        ctx.line_to(-r, r)
        ctx.stroke()
    ctx.restore()


def shield(ctx, x, y, r, s):
    if s <= 0:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(0, -r)
    ctx.curve_to(r * .5, -r * .75, r * .85, -r * .8, r * .9, -r * .75)
    ctx.curve_to(r * .95, r * .1, r * .55, r * .7, 0, r)
    ctx.curve_to(-r * .55, r * .7, -r * .95, r * .1, -r * .9, -r * .75)
    ctx.curve_to(-r * .85, -r * .8, -r * .5, -r * .75, 0, -r)
    ctx.close_path()
    ctx.set_source(lgrad(0, -r, 0, r, [(0, C('#9bdcff')), (1, C('#3f9fd8'))]))
    ctx.fill_preserve()
    setc(ctx, PAL['ink'])
    ctx.set_line_width(Pen.L(3.5))
    ctx.stroke()
    poly(ctx, [(-r * .35, 0), (-r * .05, r * .3), (r * .45, -r * .3)], close=False)
    setc(ctx, PAL['white'])
    ctx.set_line_width(r * 0.18)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.restore()


def tree(ctx, x, y, s, seed=0):
    """Árbol de caricatura con base en (x, y)."""
    rnd = random.Random(seed)
    ctx.save()
    ctx.arc(x, y, 0.55 * s, 0, 2 * math.pi)
    ctx.save()
    ctx.scale(1, 0.45)
    ctx.restore()
    ctx.new_path()
    ctx.save()
    ctx.translate(x + 0.2 * s, y)
    ctx.scale(1, 0.42)
    ctx.arc(0, 0, 0.75 * s, 0, 2 * math.pi)
    ctx.restore()
    setc(ctx, C('#000000', 0.14))
    ctx.fill()
    rrect(ctx, x - 0.12 * s, y - 1.0 * s, x + 0.12 * s, y + 0.05 * s, 0.06 * s)
    fs(ctx, C('#a07850'), 2.5)
    blobs = [(0, -1.55, 0.62), (-0.45, -1.2, 0.48), (0.45, -1.2, 0.5), (0.05, -2.0, 0.45)]
    for bx, by, br in blobs:
        ctx.new_sub_path()
        ctx.arc(x + bx * s, y + by * s, br * s, 0, 2 * math.pi)
    setc(ctx, PAL['ink'])
    ctx.set_line_width(Pen.L(3) * 2)
    ctx.stroke_preserve()
    hue = rnd.choice([C('#8fc463'), C('#7db85a'), C('#9acb6b')])
    ctx.set_source(lgrad(x - s, y - 2.4 * s, x + s, y - 0.7 * s, [(0, mix(hue, C('#d8f0a0'), .35)), (1, mix(hue, C('#4c8a3a'), .35))]))
    ctx.fill()
    for bx, by, br in blobs[:2]:
        ctx.arc(x + bx * s - br * s * .25, y + by * s - br * s * .3, br * s * .28, 0, 2 * math.pi)
        setc(ctx, C('#ffffff', 0.25))
        ctx.fill()
    ctx.restore()
