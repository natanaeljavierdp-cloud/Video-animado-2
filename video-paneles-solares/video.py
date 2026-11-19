import cairo, math, json, sys, os, subprocess
import numpy as np

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
DUR = float(open(os.path.join(HERE, "dur.txt")).read())
WORDS = json.load(open(os.path.join(HERE, "words.json")))
B = [0, 7.4, 16.45, 27.45, 39.7, 48.05, 58.4, 68.2, DUR]
XF = 0.3  # half crossfade

# ---------------------------------------------------------------- utils
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lin(t, a, b): return clamp((t - a) / (b - a)) if b > a else (1.0 if t >= a else 0.0)
def sm(x): x = clamp(x); return x * x * (3 - 2 * x)
def eio(x):
    x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def eout(x): x = clamp(x); return 1 - (1 - x) ** 3
def eback(x):
    x = clamp(x); c1 = 1.9; c3 = c1 + 1; return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def P(t, a, d=0.5, f=eout): return f(lin(t, a, a + d))
def lerp(a, b, u): return a + (b - a) * u

def hx(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
def mix(c1, c2, u): return tuple(lerp(a, b, u) for a, b in zip(c1, c2))
def dk(c, k=0.72): return tuple(v * k for v in c)
def lt(c, k=0.35): return tuple(v + (1 - v) * k for v in c)

SKY_T, SKY_B = hx('#3FA9F5'), hx('#BDE6FF')
NIGHT_T, NIGHT_B = hx('#0A1633'), hx('#2A3D74')
SUN, SUN_D = hx('#FFD23F'), hx('#F5A524')
PANEL, PANEL_L, PANEL_HI = hx('#1E3A6E'), hx('#5B8BD6'), hx('#3F7FE0')
GRASS, GRASS_D = hx('#79CF5F'), hx('#57AE48')
WALL, ROOF = hx('#FFF3DC'), hx('#EF7B5C')
GLASS, LITC = hx('#A9DCF7'), hx('#FFE27A')
EY, EG = hx('#FFE34D'), hx('#4CF08A')
WHITE, INK = (1, 1, 1), hx('#1D2A44')
GREEN = hx('#2ECC71')
ORANGE = hx('#FF8A3D')

def rgba(ctx, c, a=1.0): ctx.set_source_rgba(c[0], c[1], c[2], a)

def rrect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()

def poly(ctx, pts):
    ctx.move_to(*pts[0])
    for p in pts[1:]: ctx.line_to(*p)
    ctx.close_path()

def shade(ctx, c, a=1.0, lw=6, oc=None):
    rgba(ctx, c, a); ctx.fill_preserve()
    rgba(ctx, oc if oc else dk(c, 0.62), a); ctx.set_line_width(lw)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke()

def circle(ctx, x, y, r):
    ctx.new_sub_path(); ctx.arc(x, y, r, 0, 2 * math.pi)

def glow(ctx, x, y, r, c, a=0.6):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, c[0], c[1], c[2], a)
    g.add_color_stop_rgba(1, c[0], c[1], c[2], 0)
    ctx.set_source(g); circle(ctx, x, y, r); ctx.fill()

def font(ctx, size, face="Inter Black"):
    ctx.select_font_face(face, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)

def text(ctx, s, x, y, size, col=WHITE, align='c', outline=None, ow=0, alpha=1.0, face="Inter Black"):
    font(ctx, size, face)
    xa = ctx.text_extents(s).x_advance
    x0 = x - xa / 2 if align == 'c' else (x if align == 'l' else x - xa)
    ctx.move_to(x0, y); ctx.text_path(s)
    if outline is not None:
        rgba(ctx, outline, alpha); ctx.set_line_width(ow)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke_preserve()
    rgba(ctx, col, alpha); ctx.fill()
    return xa

def pushscale(ctx, x, y, s):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.translate(-x, -y)

def label(ctx, s, x, y, size, t0, t, bg=WHITE, fg=INK, d=0.45, arrow=None, t1=None):
    """pill label centred at (x,y) popping in at t0 (and out at t1)"""
    p = P(t, t0, d, eback)
    if t1 is not None: p *= 1 - P(t, t1, 0.3, eio)
    if p <= 0.001: return
    a = clamp(lin(t, t0, t0 + 0.2))
    if t1 is not None: a *= 1 - clamp(lin(t, t1, t1 + 0.3))
    font(ctx, size)
    w = ctx.text_extents(s).x_advance + size * 1.1
    h = size * 1.55
    pushscale(ctx, x, y, max(p, 0.01))
    if arrow:
        ax, ay = arrow
        rgba(ctx, bg, a); poly(ctx, [(x - 18, y), (x + 18, y), (ax, ay)]); ctx.fill()
    ctx.save(); ctx.translate(0, 6); rrect(ctx, x - w / 2, y - h / 2, w, h, h / 2)
    rgba(ctx, (0, 0, 0), 0.18 * a); ctx.fill(); ctx.restore()
    rrect(ctx, x - w / 2, y - h / 2, w, h, h / 2); shade(ctx, bg, a, 5, dk(bg, 0.8) if bg != WHITE else hx('#C9D6E8'))
    text(ctx, s, x, y + size * 0.36, size, fg, alpha=a)
    ctx.restore()

# ---------------------------------------------------------------- paths & energy
_pc = {}
def resample(pts, step=3.0):
    key = tuple((round(a, 1), round(b, 1)) for a, b in pts)
    if key in _pc: return _pc[key]
    xs, ys = [pts[0][0]], [pts[0][1]]
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L / step))
        for i in range(1, n + 1):
            xs.append(x0 + (x1 - x0) * i / n); ys.append(y0 + (y1 - y0) * i / n)
    xs, ys = np.array(xs), np.array(ys)
    d = np.hypot(np.diff(xs), np.diff(ys)); ss = np.concatenate([[0], np.cumsum(d)])
    tx = np.gradient(xs); ty = np.gradient(ys); nn = np.hypot(tx, ty) + 1e-9
    nx, ny = -ty / nn, tx / nn
    _pc[key] = (xs, ys, ss, nx, ny)
    if len(_pc) > 400: _pc.clear()
    return _pc[key]

def sag(p0, p1, depth, n=24):
    return [(lerp(p0[0], p1[0], i / n), lerp(p0[1], p1[1], i / n) + depth * 4 * (i / n) * (1 - i / n)) for i in range(n + 1)]

def wire(ctx, pts, reveal=1.0, col=hx('#3C4A63'), lw=9, alpha=1.0):
    if reveal <= 0: return
    xs, ys, ss, _, _ = resample(pts)
    m = ss <= reveal * ss[-1] + 0.01
    ctx.move_to(xs[0], ys[0])
    for x, y in zip(xs[m][1:], ys[m][1:]): ctx.line_to(x, y)
    rgba(ctx, col, alpha); ctx.set_line_width(lw)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke()

def flow(ctx, pts, t, reveal=1.0, alpha=1.0, speed=300, spacing=64, wave=0.0, wavelen=110, size=1.0):
    """The single, consistent representation of electricity: glowing yellow/green
    line + travelling yellow/green particles."""
    if reveal <= 0 or alpha <= 0: return
    xs, ys, ss, nx, ny = resample(pts)
    if wave:
        off = wave * np.sin(2 * math.pi * (ss - t * speed) / wavelen)
        xs = xs + nx * off; ys = ys + ny * off
    L = ss[-1]; R = reveal * L
    m = ss <= R + 0.01
    if m.sum() >= 2:
        ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        for lw, c, a in ((22 * size, EG, 0.22), (10 * size, EG, 0.55), (4 * size, EY, 0.95)):
            ctx.move_to(xs[0], ys[0])
            for x, y in zip(xs[m][1:], ys[m][1:]): ctx.line_to(x, y)
            rgba(ctx, c, a * alpha); ctx.set_line_width(lw); ctx.stroke()
    ph = t * speed
    k0 = math.ceil((0 - ph) / spacing)
    k = k0
    while True:
        s = ph + k * spacing
        if s > R: break
        if s >= 0:
            x = np.interp(s, ss, xs); y = np.interp(s, ss, ys)
            c = EY if k % 2 == 0 else EG
            glow(ctx, x, y, 26 * size, c, 0.75 * alpha)
            rgba(ctx, lt(c, 0.6), alpha); circle(ctx, x, y, 7.5 * size); ctx.fill()
        k += 1

# ---------------------------------------------------------------- scenery
def sky(ctx, night=0.0, t=0.0):
    top, bot = mix(SKY_T, NIGHT_T, night), mix(SKY_B, NIGHT_B, night)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *top); g.add_color_stop_rgb(1, *bot)
    ctx.set_source(g); ctx.paint()
    if night > 0.01:
        rng = np.random.RandomState(7)
        for i in range(70):
            x, y = rng.rand() * W, rng.rand() * 1050
            tw = 0.55 + 0.45 * math.sin(t * 3 + i * 1.7)
            a = night * tw
            glow(ctx, x, y, 10, (1, 1, .9), 0.5 * a)
            rgba(ctx, (1, 1, 0.92), a); circle(ctx, x, y, 2.5 + (i % 3)); ctx.fill()

def cloud(ctx, x, y, s, a=0.95):
    rgba(ctx, WHITE, a)
    for dx, dy, r in ((0, 0, 55), (60, -25, 65), (125, 0, 50), (60, 15, 55), (-40, 15, 40), (165, 15, 38)):
        circle(ctx, x + dx * s, y + dy * s, r * s); ctx.fill()

def clouds(ctx, t, a=0.95, night=0.0):
    c = (a * (1 - night) ** 2)
    for i, (x0, y, s, v) in enumerate(((100, 420, 0.9, 14), (620, 260, 0.7, 10), (900, 560, 0.6, 18), (350, 640, 0.5, 12))):
        x = (x0 + t * v) % (W + 400) - 200
        cloud(ctx, x, y, s, c)

def ground(ctx, y, night=0.0, t=0.0):
    c1, c2 = mix(GRASS, hx('#1E4A3A'), night), mix(GRASS_D, hx('#16382C'), night)
    ctx.move_to(0, y + 30)
    ctx.curve_to(300, y - 40, 700, y + 40, W, y - 10)
    ctx.line_to(W, H); ctx.line_to(0, H); ctx.close_path()
    rgba(ctx, c1); ctx.fill()
    ctx.move_to(0, y + 170)
    ctx.curve_to(350, y + 110, 760, y + 200, W, y + 140)
    ctx.line_to(W, H); ctx.line_to(0, H); ctx.close_path()
    rgba(ctx, c2); ctx.fill()

def sun(ctx, x, y, r, t, alpha=1.0, face=True, scale=1.0):
    if alpha <= 0 or scale <= 0: return
    pushscale(ctx, x, y, scale)
    glow(ctx, x, y, r * 2.6, SUN, 0.45 * alpha)
    ctx.save(); ctx.translate(x, y); ctx.rotate(t * 0.35)
    for i in range(12):
        ctx.save(); ctx.rotate(i * math.pi / 6)
        L = r * (1.45 + 0.1 * math.sin(t * 4 + i))
        rrect(ctx, -r * 0.09, r * 1.12, r * 0.18, L - r * 1.12 + r * 0.25, r * 0.09)
        rgba(ctx, SUN, alpha); ctx.fill(); ctx.restore()
    ctx.restore()
    circle(ctx, x, y, r); shade(ctx, SUN, alpha, max(4, r * 0.06), SUN_D)
    circle(ctx, x - r * 0.3, y - r * 0.35, r * 0.25); rgba(ctx, WHITE, 0.35 * alpha); ctx.fill()
    if face:
        blink = 1.0 if (t % 3.7) > 0.12 else 0.2
        ctx.set_line_width(r * 0.07); ctx.set_line_cap(cairo.LINE_CAP_ROUND); rgba(ctx, hx('#7A4A00'), alpha)
        for ex in (-0.32, 0.32):
            ctx.save(); ctx.translate(x + ex * r, y - r * 0.12); ctx.scale(1, blink)
            ctx.arc(0, 0, r * 0.12, math.pi * 1.1, math.pi * 1.9); ctx.restore(); ctx.stroke()
        ctx.arc(x, y + r * 0.08, r * 0.38, math.pi * 0.15, math.pi * 0.85); ctx.stroke()
        for ex in (-0.55, 0.55):
            rgba(ctx, hx('#FF8C69'), 0.5 * alpha); circle(ctx, x + ex * r, y + r * 0.18, r * 0.12); ctx.fill()
    ctx.restore()

def moon(ctx, x, y, r, a):
    if a <= 0: return
    glow(ctx, x, y, r * 2.4, (1, 1, .85), 0.35 * a)
    ctx.push_group()
    rgba(ctx, hx('#FFF6C9')); circle(ctx, x, y, r); ctx.fill()
    ctx.set_operator(cairo.OPERATOR_CLEAR); circle(ctx, x + r * 0.45, y - r * 0.25, r * 0.85); ctx.fill()
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)

def roof_pt(u, v):
    left, right = lerp(-226, -150, v), lerp(226, 150, v)
    return (lerp(left, right, u), lerp(-270, -410, v))

HOUSE_PANELS = [(c, r) for r in range(2) for c in range(4)]

def house(ctx, cx, by, s, lit=0.0, pglow=0.0, t=0.0, night=0.0, cut=False):
    ctx.save(); ctx.translate(cx, by); ctx.scale(s, s)
    # shadow
    ctx.save(); ctx.scale(1, 0.12); circle(ctx, 0, 30, 270); rgba(ctx, (0, 0, 0), 0.12); ctx.fill(); ctx.restore()
    # chimney
    rrect(ctx, 95, -455, 48, 120, 6); shade(ctx, mix(hx('#C8664F'), hx('#4a2a24'), night * 0.5))
    # walls
    wc = mix(WALL, hx('#8F95B5'), night * 0.6)
    rrect(ctx, -200, -268, 400, 268, 10); shade(ctx, wc, 1, 6, dk(WALL, 0.6))
    # roof
    rc = mix(ROOF, hx('#7B3B33'), night * 0.5)
    ctx.move_to(-240, -262); ctx.line_to(-152, -418); ctx.line_to(152, -418); ctx.line_to(240, -262); ctx.close_path()
    shade(ctx, rc, 1, 7)
    # panels
    for c, r in HOUSE_PANELS:
        u0, u1 = 0.07 + c * 0.215, 0.07 + c * 0.215 + 0.2
        v0, v1 = 0.12 + r * 0.4, 0.12 + r * 0.4 + 0.36
        q = [roof_pt(u0, v0), roof_pt(u1, v0), roof_pt(u1, v1), roof_pt(u0, v1)]
        pc = mix(PANEL, hx('#11203F'), night * 0.7)
        poly(ctx, q); shade(ctx, pc, 1, 3.5, hx('#C7D3E6'))
        rgba(ctx, PANEL_L, 0.55 * (1 - night * 0.7)); ctx.set_line_width(1.6)
        for k in (1, 2):
            a, b = roof_pt(lerp(u0, u1, k / 3), v0), roof_pt(lerp(u0, u1, k / 3), v1)
            ctx.move_to(*a); ctx.line_to(*b); ctx.stroke()
        a, b = roof_pt(u0, (v0 + v1) / 2), roof_pt(u1, (v0 + v1) / 2)
        ctx.move_to(*a); ctx.line_to(*b); ctx.stroke()
        if pglow > 0:
            sh = (t * 0.6 + c * 0.12 + r * 0.2) % 1.6
            if sh < 1:
                poly(ctx, q); ctx.save(); ctx.clip()
                xx = lerp(-260, 260, sh)
                g = cairo.LinearGradient(xx - 60, 0, xx + 60, 0)
                g.add_color_stop_rgba(0, 1, 1, 1, 0); g.add_color_stop_rgba(.5, 1, 1, 1, 0.55 * pglow); g.add_color_stop_rgba(1, 1, 1, 1, 0)
                ctx.set_source(g); ctx.paint(); ctx.restore()
            poly(ctx, q); rgba(ctx, EY, 0.10 * pglow); ctx.fill()
    # door
    ctx.move_to(-42, 0); ctx.line_to(-42, -120); ctx.arc(0, -120, 42, math.pi, 0); ctx.line_to(42, 0); ctx.close_path()
    shade(ctx, mix(hx('#F4A261'), hx('#6a4a3a'), night * 0.5))
    rgba(ctx, hx('#7A4A1F')); circle(ctx, 26, -70, 6); ctx.fill()
    # windows
    for wx in (-160, 70):
        gc = mix(mix(GLASS, hx('#40507a'), night), LITC, lit)
        if lit > 0:
            glow(ctx, wx + 45, -175, 120, LITC, 0.35 * lit * (1 + night))
        rrect(ctx, wx, -220, 90, 90, 10); shade(ctx, gc, 1, 6, hx('#FFFFFF') if night < .5 else hx('#D6DCEB'))
        rgba(ctx, WHITE, 0.95); ctx.set_line_width(6)
        ctx.move_to(wx + 45, -220); ctx.line_to(wx + 45, -130); ctx.move_to(wx, -175); ctx.line_to(wx + 90, -175); ctx.stroke()
        if lit < 0.5:
            rgba(ctx, WHITE, 0.5 * (1 - night)); ctx.set_line_width(5)
            ctx.move_to(wx + 12, -150); ctx.line_to(wx + 30, -205); ctx.stroke()
    ctx.restore()

def house_pt(cx, by, s, x, y): return (cx + x * s, by + y * s)

def pole(ctx, x, by, h, night=0.0):
    c = mix(hx('#9C6B43'), hx('#4b3626'), night)
    rrect(ctx, x - 12, by - h, 24, h, 6); shade(ctx, c)
    rrect(ctx, x - 80, by - h + 40, 160, 16, 6); shade(ctx, c)
    for dx in (-62, 0, 62):
        rrect(ctx, x + dx - 8, by - h + 16, 16, 26, 5); shade(ctx, hx('#BFD7EA'))
    return (x, by - h + 24)

# ---------------------------------------------------------------- icons
def bolt(ctx, x, y, s, a=1.0, c=EY):
    pts = [(10, -100), (-45, 10), (-5, 10), (-20, 100), (45, -20), (5, -20), (25, -100)]
    pts = [(x + px * s, y + py * s) for px, py in pts]
    poly(ctx, pts); shade(ctx, c, a, 7 * s, hx('#E2A100'))

def bulb(ctx, x, y, s, on, t):
    # y = top of socket
    if on > 0:
        glow(ctx, x, y + 85 * s, 230 * s, LITC, 0.55 * on)
        ctx.save(); ctx.translate(x, y + 85 * s)
        rgba(ctx, EY, 0.9 * on); ctx.set_line_width(7 * s); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for i in range(8):
            a = i * math.pi / 4 + 0.2
            r0 = 75 * s; r1 = (100 + 10 * math.sin(t * 6 + i)) * s
            ctx.move_to(r0 * math.cos(a), r0 * math.sin(a)); ctx.line_to(r1 * math.cos(a), r1 * math.sin(a))
        ctx.stroke(); ctx.restore()
    rrect(ctx, x - 20 * s, y, 40 * s, 36 * s, 6 * s); shade(ctx, hx('#9AA6B8'))
    circle(ctx, x, y + 85 * s, 52 * s)
    shade(ctx, mix(hx('#EEF3F9'), LITC, on), 1, 6 * s, mix(hx('#9AA6B8'), SUN_D, on))
    rgba(ctx, WHITE, 0.7); circle(ctx, x - 18 * s, y + 68 * s, 12 * s); ctx.fill()

def fridge(ctx, x, y, w, h, on, t):
    sh = math.sin(t * 40) * 1.5 * on * (1 - lin(t % 2, 0, 0.4)) if on > 0 else 0
    ctx.save(); ctx.translate(sh, 0)
    if on > 0: glow(ctx, x + w / 2, y + h / 2, w * 1.2, hx('#9FE3FF'), 0.35 * on)
    rrect(ctx, x, y, w, h, 18); shade(ctx, hx('#F2F6FB'), 1, 6, hx('#8C9BB0'))
    rgba(ctx, hx('#8C9BB0')); ctx.set_line_width(5); ctx.move_to(x, y + h * 0.36); ctx.line_to(x + w, y + h * 0.36); ctx.stroke()
    for yy, hh in ((y + 30, h * 0.36 - 60), (y + h * 0.36 + 30, h * 0.4)):
        rrect(ctx, x + w - 30, yy, 12, hh, 6); shade(ctx, hx('#B6C2D3'))
    # led + snowflake
    rgba(ctx, mix(hx('#9AA6B8'), GREEN, on)); circle(ctx, x + 30, y + 30, 9); ctx.fill()
    cx, cy = x + w * 0.42, y + h * 0.62
    ctx.set_line_width(6); ctx.set_line_cap(cairo.LINE_CAP_ROUND); rgba(ctx, mix(hx('#C5D0DE'), hx('#2FA8F0'), on))
    for i in range(3):
        a = i * math.pi / 3 + (t * 0.8 if on > 0 else 0)
        ctx.move_to(cx - 28 * math.cos(a), cy - 28 * math.sin(a)); ctx.line_to(cx + 28 * math.cos(a), cy + 28 * math.sin(a))
    ctx.stroke()
    ctx.restore()

def tv(ctx, x, y, w, h, on, t):
    if on > 0: glow(ctx, x + w / 2, y + h / 2, w * 0.9, hx('#7FD0FF'), 0.35 * on)
    rrect(ctx, x, y, w, h, 16); shade(ctx, hx('#263142'))
    sx, sy, sw, shh = x + 14, y + 14, w - 28, h - 28
    rrect(ctx, sx, sy, sw, shh, 8)
    rgba(ctx, hx('#3A4458')); ctx.fill_preserve()
    if on > 0:
        ctx.save(); ctx.clip()
        g = cairo.LinearGradient(0, sy, 0, sy + shh)
        g.add_color_stop_rgba(0, *SKY_T, on); g.add_color_stop_rgba(1, *SKY_B, on)
        ctx.set_source(g); ctx.paint()
        sun(ctx, sx + sw * 0.25, sy + shh * 0.38 + 6 * math.sin(t * 2), shh * 0.17, t, on, face=True)
        ctx.move_to(sx, sy + shh * 0.8); ctx.curve_to(sx + sw * 0.3, sy + shh * 0.6, sx + sw * 0.7, sy + shh * 0.9, sx + sw, sy + shh * 0.7)
        ctx.line_to(sx + sw, sy + shh); ctx.line_to(sx, sy + shh); ctx.close_path(); rgba(ctx, GRASS, on); ctx.fill()
        cloud(ctx, sx + (sw * 0.5 + t * 30) % (sw + 80) - 40, sy + shh * 0.3, 0.28, on)
        ctx.restore()
    else:
        ctx.new_path()
    rrect(ctx, x + w / 2 - 50, y + h, 100, 18, 4); shade(ctx, hx('#263142'))

def ac_unit(ctx, x, y, w, h, on, t):
    if on > 0:
        ctx.set_line_width(6); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for i in range(4):
            ph = (t * 0.9 + i * 0.25) % 1
            a = on * math.sin(ph * math.pi)
            xx = x + 30 + i * (w - 60) / 3
            ctx.move_to(xx, y + h + 10 + ph * 60)
            for k in range(1, 9):
                yy = y + h + 10 + ph * 60 + k * 14
                ctx.line_to(xx + 10 * math.sin(k * 0.9 + t * 5), yy)
            rgba(ctx, hx('#7FD3FF'), a); ctx.stroke()
    rrect(ctx, x, y, w, h, 18); shade(ctx, hx('#F7FAFD'), 1, 6, hx('#8C9BB0'))
    rgba(ctx, hx('#B6C2D3')); ctx.set_line_width(4)
    for k in range(3):
        ctx.move_to(x + 20, y + h - 14 - k * 9); ctx.line_to(x + w - 20, y + h - 14 - k * 9); ctx.stroke()
    rgba(ctx, mix(hx('#9AA6B8'), GREEN, on)); circle(ctx, x + w - 26, y + 22, 8); ctx.fill()

def inverter(ctx, x, y, w, h, t, s=1.0, active=1.0):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    ctx.save(); ctx.translate(8, 10); rrect(ctx, 0, 0, w, h, 24); rgba(ctx, (0, 0, 0), 0.15); ctx.fill(); ctx.restore()
    rrect(ctx, 0, 0, w, h, 24); shade(ctx, hx('#EEF3FA'), 1, 7, hx('#5B6B82'))
    rrect(ctx, 0, 0, w, 34, 24); rgba(ctx, hx('#2E86DE')); ctx.fill()
    rgba(ctx, hx('#2E86DE')); ctx.rectangle(0, 18, w, 16); ctx.fill()
    # screen with DC -> AC
    sx, sy, sw, sh = 24, 50, w - 48, h * 0.38
    rrect(ctx, sx, sy, sw, sh, 12); shade(ctx, hx('#16253F'), 1, 4)
    ctx.set_line_width(5); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    my = sy + sh / 2
    rgba(ctx, EY); ctx.move_to(sx + 16, my); ctx.line_to(sx + sw * 0.32, my); ctx.stroke()
    rgba(ctx, WHITE, 0.9); ctx.move_to(sx + sw * 0.40, my); ctx.line_to(sx + sw * 0.52, my); ctx.stroke()
    ctx.move_to(sx + sw * 0.47, my - 8); ctx.line_to(sx + sw * 0.53, my); ctx.line_to(sx + sw * 0.47, my + 8); ctx.stroke()
    rgba(ctx, EG); ctx.move_to(sx + sw * 0.6, my)
    for i in range(1, 31):
        u = i / 30
        ctx.line_to(sx + sw * (0.6 + 0.34 * u), my - 14 * math.sin(u * 4 * math.pi + t * 6 * active))
    ctx.stroke()
    text(ctx, "Inversor", w / 2, h - 34, 44, INK)
    rgba(ctx, mix(hx('#9AA6B8'), GREEN, active)); circle(ctx, w - 30, 17, 7); ctx.fill()
    ctx.restore()

def battery(ctx, x, y, w, h, level, t, active=1.0):
    ctx.save(); ctx.translate(8, 10); rrect(ctx, x, y, w, h, 26); rgba(ctx, (0, 0, 0), 0.18); ctx.fill(); ctx.restore()
    rrect(ctx, x, y, w, h, 26); shade(ctx, hx('#2F3E56'), 1, 7, hx('#18223A'))
    rrect(ctx, x + w * 0.3, y - 20, w * 0.4, 26, 8); shade(ctx, hx('#2F3E56'), 1, 6, hx('#18223A'))
    col = mix(hx('#FF6B4A'), mix(hx('#FFC93C'), GREEN, clamp((level - 0.35) / 0.3)), clamp((level - 0.1) / 0.25))
    ix, iy, iw, ih = x + 22, y + 70, w - 44, h - 92
    rrect(ctx, ix, iy, iw, ih, 12); rgba(ctx, hx('#1A2436')); ctx.fill()
    n = 5
    for i in range(n):
        seg_lo = i / n
        f = clamp((level - seg_lo) * n)
        sh_ = (ih - 12) / n
        yy = iy + ih - 6 - (i + 1) * sh_
        rrect(ctx, ix + 8, yy + 4, iw - 16, sh_ - 8, 6); rgba(ctx, col, 0.18); ctx.fill()
        if f > 0:
            rrect(ctx, ix + 8, yy + 4 + (sh_ - 8) * (1 - f), iw - 16, (sh_ - 8) * f, 6); rgba(ctx, col); ctx.fill()
    text(ctx, f"{int(round(level * 100))}%", x + w / 2, y + 50, 36, WHITE)

# ---------------------------------------------------------------- scenes
def cam(ctx, z, fx, fy, sx, sy):
    ctx.translate(sx, sy); ctx.scale(z, z); ctx.translate(-fx, -fy)

def scene1(ctx, t):
    sky(ctx, 0, t)
    HX, HB, HS = 540, 1230, 1.35
    roof = house_pt(HX, HB, HS, 0, -340)
    zz = eio(lin(t, 6.5, 7.75))
    z = 1 + 0.05 * lin(t, 0, 6.5) + 1.9 * zz
    ctx.save()
    cam(ctx, z, lerp(540, roof[0], zz), lerp(960, roof[1], zz), 540, lerp(960, 820, zz))
    clouds(ctx, t)
    sx, sy, sr = 230, 330 + 8 * math.sin(t * 1.5), 105
    sun(ctx, sx, sy, sr, t, scale=P(t, 0.0, 0.9, eback))
    ground(ctx, 1200, 0, t)
    house(ctx, HX, HB, HS, lit=P(t, 3.9, 0.7, sm), pglow=P(t, 2.8, 1.0), t=t)
    # light beams sun -> roof
    bp = P(t, 2.3, 0.8)
    if bp > 0:
        targets = [house_pt(HX, HB, HS, *roof_pt(u, 0.5)) for u in (0.2, 0.5, 0.8)]
        for i, (tx, ty) in enumerate(targets):
            ex, ey = lerp(sx, tx, bp), lerp(sy, ty, bp)
            ang = math.atan2(ey - sy, ex - sx); wdt = 26
            nx, ny = -math.sin(ang), math.cos(ang)
            g = cairo.LinearGradient(sx, sy, ex, ey)
            g.add_color_stop_rgba(0, *SUN, 0.0); g.add_color_stop_rgba(0.3, *SUN, 0.45); g.add_color_stop_rgba(1, *LITC, 0.65)
            ctx.set_source(g)
            poly(ctx, [(sx + nx * 6, sy + ny * 6), (ex + nx * wdt, ey + ny * wdt), (ex - nx * wdt, ey - ny * wdt), (sx - nx * 6, sy - ny * 6)])
            ctx.fill()
            for k in range(4):
                u = ((t - 2.3) * 0.9 + k / 4 + i * 0.13) % 1
                if u < bp:
                    glow(ctx, lerp(sx, tx, u), lerp(sy, ty, u), 22, (1, 1, .8), 0.8)
        if t > 3.0:
            for u in (0.2, 0.5, 0.8):
                px, py = house_pt(HX, HB, HS, *roof_pt(u, 0.5))
                glow(ctx, px, py, 60 + 10 * math.sin(t * 7 + u * 9), (1, 1, .85), 0.5 * P(t, 3.0, 0.5))
    ctx.restore()

def panel_geom():
    x, y, w, h = 150, 380, 740, 900
    cols, rows, m, g = 6, 8, 26, 9
    cw = (w - 2 * m - (cols - 1) * g) / cols; ch = (h - 2 * m - (rows - 1) * g) / rows
    cells = [(x + m + c * (cw + g), y + m + r * (ch + g), cw, ch, c, r) for r in range(rows) for c in range(cols)]
    return (x, y, w, h), cells

def scene2(ctx, t):
    sky(ctx, 0, t)
    clouds(ctx, t + 20, 0.8)
    sun(ctx, 120, 150 + 6 * math.sin(t * 1.5), 85, t)
    (px, py, pw, ph), cells = panel_geom()
    # zoom into one cell at end
    focus = cells[3 * 6 + 2]
    fx, fy = focus[0] + focus[2] / 2, focus[1] + focus[3] / 2
    zz = eio(lin(t, 15.85, 16.75))
    ent = P(t, 7.1, 1.3, eback)
    ctx.save()
    cam(ctx, (0.35 + 0.65 * ent) * (1 + 5 * zz), lerp(540, fx, zz), lerp(830, fy, zz), lerp(540, 540, zz), lerp(830, 900, zz))
    # mount legs
    for lx in (px + 120, px + pw - 120):
        rrect(ctx, lx - 14, py + ph - 20, 28, 140, 8); shade(ctx, hx('#9AA6B8'))
    ctx.save(); ctx.translate(14, 18); rrect(ctx, px, py, pw, ph, 26); rgba(ctx, (0, 0, 0), 0.2); ctx.fill(); ctx.restore()
    rrect(ctx, px, py, pw, ph, 26); shade(ctx, hx('#D9E2EE'), 1, 7, hx('#8A99B0'))
    react = P(t, 14.5, 0.6)
    N = len(cells)
    for i, (x, y, w, h, c, r) in enumerate(cells):
        th = 10.95 + i * (1.6 / N)
        hl = clamp(1 - abs(t - th - 0.15) / 0.35) if t < th + 0.6 else 0
        sel = P(t, th, 0.3)
        col = mix(PANEL, PANEL_HI, 0.25 * sel + 0.6 * hl)
        if react > 0:
            pulse = 0.5 + 0.5 * math.sin(t * 5 - (c + r) * 0.7)
            col = mix(col, hx('#4D86E8'), 0.35 * react * pulse)
        rrect(ctx, x, y, w, h, 7); shade(ctx, col, 1, 3, hx('#0F2147'))
        rgba(ctx, PANEL_L, 0.55); ctx.set_line_width(1.5)
        for k in (1, 2, 3):
            ctx.move_to(x + w * k / 4, y + 6); ctx.line_to(x + w * k / 4, y + h - 6)
        ctx.stroke()
        if hl > 0:
            rrect(ctx, x - 3, y - 3, w + 6, h + 6, 9); rgba(ctx, WHITE, 0.9 * hl); ctx.set_line_width(6); ctx.stroke()
            glow(ctx, x + w / 2, y + h / 2, w, (0.7, 0.9, 1), 0.5 * hl)
    # sheen
    sh = ((t - 7.5) * 0.45) % 1.4
    rrect(ctx, px, py, pw, ph, 26); ctx.save(); ctx.clip()
    xx = lerp(px - 300, px + pw + 300, sh)
    g = cairo.LinearGradient(xx - 120, py, xx + 120, py + 260)
    g.add_color_stop_rgba(0, 1, 1, 1, 0); g.add_color_stop_rgba(.5, 1, 1, 1, 0.28); g.add_color_stop_rgba(1, 1, 1, 1, 0)
    ctx.set_source(g); ctx.paint(); ctx.restore()
    # sparkles reacting to light
    if react > 0:
        for i in range(14):
            ph_ = (t * 0.8 + i * 0.37) % 1
            x, y, w, h, c, r = cells[(i * 17) % N]
            a = react * math.sin(ph_ * math.pi)
            cx_, cy_ = x + w / 2, y + h / 2
            glow(ctx, cx_, cy_, 50, (1, 1, .8), 0.7 * a)
            rgba(ctx, WHITE, a); ctx.set_line_width(4)
            L = 22 * a
            ctx.move_to(cx_ - L, cy_); ctx.line_to(cx_ + L, cy_); ctx.move_to(cx_, cy_ - L); ctx.line_to(cx_, cy_ + L); ctx.stroke()
        # light rays from sun
        for k in range(4):
            u = ((t - 14.5) * 0.7 + k * 0.25) % 1
            x0, y0 = 120, 150
            tx, ty = px + 150 + k * 150, py + 200 + k * 140
            glow(ctx, lerp(x0, tx, u), lerp(y0, ty, u), 26, (1, 1, .75), 0.9 * react)
    ctx.restore()
    hl_last = cells[3 * 6 + 2]
    label(ctx, "Celdas de silicio", 486, 270, 60, 13.25, t, bg=hx('#FFD23F'), fg=INK,
          arrow=(hl_last[0] + hl_last[2] / 2, 380) if zz < 0.05 else None)
    label(ctx, "Panel solar", 486, 270, 60, 9.3, t, t1=12.9)

ELEC = []
_rng = np.random.RandomState(3)
for r, yy in enumerate((560, 760, 960, 1160)):
    for k in range(5):
        x0 = 110 + k * 200 + (r % 2) * 100
        ELEC.append((x0, yy, 19.95 + ((r * 5 + k) * 0.618 % 1) * 2.7))

def scene3(ctx, t):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *hx('#14306A')); g.add_color_stop_rgb(1, *hx('#0C1C40'))
    ctx.set_source(g); ctx.paint()
    zin = P(t, 16.15, 0.9)
    pushscale(ctx, 540, 900, 1.25 - 0.25 * zin)
    # lattice
    off = (t * 6) % 100
    ctx.set_line_width(3); rgba(ctx, hx('#3A5DA8'), 0.5)
    for i in range(-1, 13):
        ctx.move_to(i * 100 - off, 0); ctx.line_to(i * 100 - off, H)
    for j in range(0, 21):
        ctx.move_to(0, j * 100 + 50); ctx.line_to(W, j * 100 + 50)
    ctx.stroke()
    for i in range(-1, 13):
        for j in range(0, 21):
            x, y = i * 100 - off, j * 100 + 50
            rgba(ctx, hx('#5677C2'), 0.85); circle(ctx, x, y, 13); ctx.fill()
            rgba(ctx, hx('#8FA9E6'), 0.6); circle(ctx, x - 4, y - 4, 4); ctx.fill()
    ctx.restore()
    # electrons
    move_all = P(t, 23.2, 1.2)
    flows_on = P(t, 24.4, 0.8)
    for r, yy in enumerate((560, 760, 960, 1160)):
        flow(ctx, [(-40, yy), (W + 40, yy)], t, reveal=flows_on, alpha=0.9 * flows_on, speed=300, spacing=110)
    for i, (x0, y0, te) in enumerate(ELEC):
        excited = t >= te
        if excited:
            dt = t - te
            v = 80 * min(dt, 1) + 240 * move_all
            x = x0 + 40 * dt * dt * (dt < 1) + (40 if dt >= 1 else 0)
            x = x0 + (v * dt if dt > 0 else 0)
            x = (x + 60) % (W + 120) - 60
            y = y0 + 4 * math.sin(t * 9 + i)
        else:
            x = x0 + 5 * math.sin(t * 7 + i * 2.1); y = y0 + 5 * math.cos(t * 6.3 + i * 1.3)
        if excited:
            glow(ctx, x, y, 48, hx('#7FC4FF'), 0.55)
        circle(ctx, x, y, 22); shade(ctx, hx('#3D9BFF'), 1, 5, hx('#0F4FA8'))
        rgba(ctx, WHITE, 0.95); ctx.set_line_width(5); ctx.move_to(x - 9, y); ctx.line_to(x + 9, y); ctx.stroke()
        rgba(ctx, WHITE, 0.5); circle(ctx, x - 8, y - 9, 5); ctx.fill()
        # impact burst
        if 0 <= t - te < 0.5:
            u = (t - te) / 0.5
            rgba(ctx, (1, 1, .8), 1 - u); ctx.set_line_width(6 * (1 - u) + 1)
            circle(ctx, x, y, 22 + 60 * u); ctx.stroke()
        # photon coming to hit this electron
        tf = 0.9
        if te - tf <= t < te:
            u = (t - (te - tf)) / tf
            ux = eio(u) * 0 + u
            px_, py_ = lerp(x0 - 260, x0, ux), lerp(y0 - 520, y0, ux)
            photon(ctx, px_, py_, -260, -520)
    # ambient photons (before collisions)
    amb = P(t, 16.7, 0.6) * (1 - P(t, 22.5, 1.0))
    if amb > 0:
        for k in range(12):
            per = 1.6
            ph_ = ((t - 16.7) / per + k / 12) % 1
            x0 = 80 + (k * 137) % 900
            px_, py_ = x0 + 200 * ph_, -60 + ph_ * 700
            photon(ctx, px_, py_, 200, 700, a=amb * (1 - ph_ ** 4))
    label(ctx, "Fotones (luz)", 486, 260, 56, 18.3, t, bg=hx('#FFD23F'), t1=26.3)
    label(ctx, "Electrones", 486, 1290, 56, 22.4, t, bg=hx('#3D9BFF'), fg=WHITE, t1=26.3)
    # final electricity
    e = P(t, 26.6, 0.6, eback)
    if e > 0:
        rgba(ctx, hx('#0C1C40'), 0.55 * clamp(lin(t, 26.6, 27.0))); ctx.paint()
        glow(ctx, 486, 700, 360, EY, 0.55 * clamp(e))
        glow(ctx, 486, 700, 240, EG, 0.35 * clamp(e))
        pushscale(ctx, 486, 700, e * (1 + 0.04 * math.sin(t * 8)))
        bolt(ctx, 486, 700, 2.1)
        ctx.restore()
        a = clamp(lin(t, 26.75, 27.0))
        pushscale(ctx, 486, 1000, e)
        text(ctx, "Electricidad", 486, 1030, 92, EY, outline=INK, ow=14, alpha=a)
        ctx.restore()

def photon(ctx, x, y, dx, dy, a=1.0):
    L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
    g = cairo.LinearGradient(x - ux * 110, y - uy * 110, x, y)
    g.add_color_stop_rgba(0, *SUN, 0); g.add_color_stop_rgba(1, *SUN, 0.75 * a)
    ctx.set_source(g); ctx.set_line_width(16); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(x - ux * 110, y - uy * 110); ctx.line_to(x, y); ctx.stroke()
    glow(ctx, x, y, 40, SUN, 0.8 * a)
    rgba(ctx, hx('#FFF3B0'), a); circle(ctx, x, y, 15); ctx.fill()

def wall_bg(ctx, t):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *hx('#DFF1FF')); g.add_color_stop_rgb(1, *hx('#F4FAFF'))
    ctx.set_source(g); ctx.paint()
    rgba(ctx, hx('#CFE6FA'), 0.6)
    for i in range(12):
        y = (i * 180 + t * 12) % (H + 200) - 100
        x = 120 + (i * 263) % 840
        circle(ctx, x, y, 30 + (i % 3) * 12); ctx.fill()

def mini_panel(ctx, x, y, w, h, t, glow_=1.0):
    sk = 40
    q = [(x + sk, y), (x + w + sk, y), (x + w - sk, y + h), (x - sk, y + h)]
    poly(ctx, q); shade(ctx, PANEL, 1, 6, hx('#C7D3E6'))
    rgba(ctx, PANEL_L, 0.7); ctx.set_line_width(2.5)
    for k in range(1, 6):
        u = k / 6
        ctx.move_to(lerp(q[0][0], q[1][0], u), y); ctx.line_to(lerp(q[3][0], q[2][0], u), y + h)
    for k in (1, 2):
        v = k / 3
        ctx.move_to(lerp(q[0][0], q[3][0], v), lerp(y, y + h, v)); ctx.line_to(lerp(q[1][0], q[2][0], v), lerp(y, y + h, v))
    ctx.stroke()
    sh = (t * 0.5) % 1.5
    if sh < 1 and glow_ > 0:
        poly(ctx, q); ctx.save(); ctx.clip()
        xx = lerp(x - 100, x + w + 100, sh)
        g = cairo.LinearGradient(xx - 80, 0, xx + 80, 0)
        g.add_color_stop_rgba(0, 1, 1, 1, 0); g.add_color_stop_rgba(.5, 1, 1, 1, 0.5 * glow_); g.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g); ctx.paint(); ctx.restore()

def card(ctx, x, y, w, h, t0, t, title, kind):
    p = P(t, t0, 0.5, eback)
    if p <= 0: return
    a = clamp(lin(t, t0, t0 + 0.2))
    pushscale(ctx, x + w / 2, y + h / 2, p)
    ctx.save(); ctx.translate(6, 8); rrect(ctx, x, y, w, h, 26); rgba(ctx, (0, 0, 0), 0.12 * a); ctx.fill(); ctx.restore()
    rrect(ctx, x, y, w, h, 26); shade(ctx, WHITE, a, 5, hx('#C9D6E8'))
    gx, gy, gw = x + 34, y + 40 + (h - 110) / 2, w - 68
    rgba(ctx, hx('#E4ECF6'), a); ctx.set_line_width(3)
    ctx.move_to(gx, gy); ctx.line_to(gx + gw, gy); ctx.stroke()
    if kind == 'dc':
        flow(ctx, [(gx, gy - 6), (gx + gw, gy - 6)], t, alpha=a, speed=200, spacing=70, size=0.8)
    else:
        flow(ctx, [(gx, gy), (gx + gw, gy)], t, alpha=a, speed=200, spacing=70, wave=34, wavelen=130, size=0.8)
    text(ctx, title, x + w / 2, y + h - 30, 38, INK, alpha=a)
    ctx.restore()

def scene4(ctx, t):
    wall_bg(ctx, t)
    sun(ctx, 120, 120 + 6 * math.sin(t * 1.5), 75, t, scale=P(t, 27.2, 0.6))
    ent = P(t, 27.15, 0.8, eback)
    CX = 490
    pushscale(ctx, CX, 280, max(ent, 0.01))
    mini_panel(ctx, CX - 210, 180, 420, 170, t)
    ctx.restore()
    inv_p = P(t, 35.75, 0.55, eback)
    top = [(CX, 350), (CX, 680)]
    bot = [(CX, 950), (CX, 1155)]
    wire(ctx, top, reveal=P(t, 27.4, 0.6))
    wire(ctx, bot, reveal=P(t, 31.4, 0.5))
    flow(ctx, top, t, reveal=P(t, 28.0, 1.0), speed=260)
    # house icon
    hp = P(t, 31.5, 0.6, eback)
    if hp > 0:
        house(ctx, CX, 1340, 0.42 * hp, lit=P(t, 38.5, 0.6, sm), t=t)
    # slot / inverter
    if inv_p < 1:
        a = 1 - inv_p
        pulse = 0.5 + 0.5 * math.sin(t * 5)
        ctx.set_dash([18, 12]); rrect(ctx, CX - 140, 680, 280, 270, 24)
        rgba(ctx, hx('#5B6B82'), 0.7 * a * P(t, 28.3, 0.5)); ctx.set_line_width(5); ctx.stroke(); ctx.set_dash([])
        text(ctx, "?", CX, 860, 140 + 10 * pulse, hx('#5B6B82'), alpha=0.8 * a * P(t, 28.4, 0.5))
    if inv_p > 0:
        glow(ctx, CX, 815, 260, EG, 0.25 * P(t, 37.0, 0.6))
        inverter(ctx, CX - 140 + 140 * (1 - inv_p), 680 + 135 * (1 - inv_p), 280, 270, t, s=max(inv_p, 0.01), active=P(t, 36.9, 0.5))
    flow(ctx, bot, t, reveal=P(t, 37.0, 0.9), speed=220, spacing=60, wave=20, wavelen=80)
    card(ctx, 40, 410, 400, 230, 30.1, t, "Corriente continua", 'dc')
    card(ctx, 540, 990, 400, 230, 32.2, t, "Corriente alterna", 'ac')

def scene5(ctx, t):
    sky(ctx, 0, t)
    clouds(ctx, t + 40, 0.8)
    ground(ctx, 1300, 0, t)
    # house cutaway
    X0, X1, Y0, Y1 = 60, 920, 430, 1300
    ctx.move_to(25, Y0 + 6); ctx.line_to(190, 215); ctx.line_to(790, 215); ctx.line_to(955, Y0 + 6); ctx.close_path()
    shade(ctx, ROOF, 1, 7)
    for c in range(5):
        for r in range(2):
            u0 = 0.06 + c * 0.18; u1 = u0 + 0.165; v0 = 0.12 + r * 0.42; v1 = v0 + 0.36
            def rp(u, v): return (lerp(lerp(40, 940, u), lerp(205, 775, u), v), lerp(Y0 - 6, 230, v))
            q = [rp(u0, v0), rp(u1, v0), rp(u1, v1), rp(u0, v1)]
            poly(ctx, q); shade(ctx, PANEL, 1, 3.5, hx('#C7D3E6'))
            sh = (t * 0.6 + c * 0.1 + r * 0.2) % 1.6
            if sh < 1:
                poly(ctx, q); ctx.save(); ctx.clip()
                xx = lerp(0, 1000, sh)
                g = cairo.LinearGradient(xx - 60, 0, xx + 60, 0)
                g.add_color_stop_rgba(0, 1, 1, 1, 0); g.add_color_stop_rgba(.5, 1, 1, 1, 0.5); g.add_color_stop_rgba(1, 1, 1, 1, 0)
                ctx.set_source(g); ctx.paint(); ctx.restore()
    rrect(ctx, X0, Y0, X1 - X0, Y1 - Y0, 14); shade(ctx, hx('#E9D9BF'), 1, 8, hx('#A8906C'))
    bright = P(t, 44.6, 0.5)
    rrect(ctx, X0 + 22, Y0 + 18, X1 - X0 - 44, Y1 - Y0 - 40, 10)
    g = cairo.LinearGradient(0, Y0, 0, Y1)
    g.add_color_stop_rgb(0, *mix(hx('#C9CFE0'), hx('#FFF6E2'), bright)); g.add_color_stop_rgb(1, *mix(hx('#B7BDD1'), hx('#FCEFD6'), bright))
    ctx.set_source(g); ctx.fill()
    rgba(ctx, hx('#B98A5E')); ctx.rectangle(X0 + 22, 1232, X1 - X0 - 44, 46); ctx.fill()
    # window in back
    rrect(ctx, 520, 700, 170, 140, 10); shade(ctx, GLASS, 1, 6, WHITE)
    rgba(ctx, WHITE); ctx.set_line_width(6); ctx.move_to(605, 700); ctx.line_to(605, 840); ctx.stroke()
    # electrical panel
    PX, PY, PW, PH = 95, 640, 140, 200
    ctx.save(); ctx.translate(5, 7); rrect(ctx, PX, PY, PW, PH, 16); rgba(ctx, (0, 0, 0), .15); ctx.fill(); ctx.restore()
    rrect(ctx, PX, PY, PW, PH, 16); shade(ctx, hx('#DDE4EE'), 1, 6, hx('#5B6B82'))
    for i in range(4):
        on = P(t, [44.4, 45.05, 45.8, 46.7][i], 0.2)
        rrect(ctx, PX + 22, PY + 24 + i * 42, PW - 44, 28, 6); shade(ctx, mix(hx('#9AA6B8'), GREEN, on), 1, 3)
    pa = P(t, 40.8, 0.4)
    wires = {
        'bulb': [(PX + PW, 690), (330, 690), (330, 452), (520, 452), (520, 520)],
        'ac':   [(PX + PW, 720), (360, 720), (360, 478), (790, 478), (790, 525)],
        'fridge': [(PX + PW, 790), (375, 790), (375, 905)],
        'tv':   [(PX + PW, 815), (265, 815), (265, 1255), (720, 1255), (720, 1215)],
    }
    inpath = [(150, Y0 - 30), (150, 560), (165, 560), (165, PY)]
    wire(ctx, inpath)
    flow(ctx, inpath, t, reveal=P(t, 39.75, 1.0), speed=280)
    wt = {'bulb': 44.64, 'fridge': 45.30, 'tv': 46.06, 'ac': 46.94}
    for k, pts in wires.items():
        wire(ctx, pts, reveal=P(t, 42.7, 1.1, sm))
    for k, pts in wires.items():
        flow(ctx, pts, t, reveal=P(t, wt[k] - 0.45, 0.45, sm), speed=320, spacing=56)
    on = {k: P(t, v, 0.3) for k, v in wt.items()}
    ac_unit(ctx, 690, 525, 210, 92, on['ac'], t)
    fridge(ctx, 290, 905, 170, 330, on['fridge'], t)
    rrect(ctx, 560, 1110, 320, 122, 12); shade(ctx, hx('#C08A5A'))
    tv(ctx, 580, 900, 280, 170, on['tv'], t)
    rgba(ctx, hx('#5B6B82')); ctx.set_line_width(4); ctx.move_to(520, 440); ctx.line_to(520, 520); ctx.stroke()
    bulb(ctx, 520, 520, 0.85, on['bulb'], t)
    label(ctx, "Panel eléctrico", 215, 600, 40, 40.9, t, bg=hx('#2E86DE'), fg=WHITE)

def bars_card(ctx, t, a_out):
    x, y, w, h = 540, 250, 390, 380
    p = P(t, 48.3, 0.5, eback) * (1 - a_out)
    if p <= 0.01: return
    pushscale(ctx, x + w / 2, y + h / 2, p)
    rrect(ctx, x, y, w, h, 26); shade(ctx, WHITE, 1, 5, hx('#C9D6E8'))
    base = y + h - 80
    hp = 220 * P(t, 48.7, 0.8) + 6 * math.sin(t * 4)
    hg = 120 * P(t, 50.0, 0.6)
    rrect(ctx, x + 60, base - hp, 110, hp, 14); shade(ctx, GREEN)
    rrect(ctx, x + 220, base - hg, 110, max(hg, 1), 14); shade(ctx, ORANGE)
    text(ctx, "Produces", x + 115, base + 50, 32, INK)
    text(ctx, "Gastas", x + 275, base + 50, 32, INK)
    if t > 49.0:
        pp = P(t, 49.0, 0.4, eback)
        pushscale(ctx, x + 115, base - hp - 40, pp)
        text(ctx, "+", x + 115, base - hp - 10, 80, GREEN, outline=WHITE, ow=8)
        ctx.restore()
    ctx.restore()

def scene6(ctx, t):
    sky(ctx, 0, t)
    clouds(ctx, t + 60, 0.8)
    sun(ctx, 150, 200 + 6 * math.sin(t * 1.5), 90, t)
    ground(ctx, 1180, 0, t)
    HX, HB, HS = 290, 1200, 0.95
    p1 = pole(ctx, 680, 1210, 560)
    p2 = pole(ctx, 1040, 1230, 560)
    hp = house_pt(HX, HB, HS, 200, -230)
    c1 = sag(hp, p1, 40); c2 = sag(p1, p2, 70); c3 = sag(p2, (1200, p2[1] + 20), 30)
    for c in (c1, c2, c3): wire(ctx, c, lw=6, col=hx('#334155'))
    house(ctx, HX, HB, HS, lit=0.4, pglow=1, t=t)
    # meter on wall
    mx, my = house_pt(HX, HB, HS, 160, -60)
    circle(ctx, mx, my, 22); shade(ctx, WHITE, 1, 5, hx('#5B6B82'))
    rgba(ctx, INK); ctx.set_line_width(3); ctx.move_to(mx, my); ctx.line_to(mx + 14 * math.cos(-t * 4), my + 14 * math.sin(-t * 4)); ctx.stroke()
    if t > 54.4:
        glow(ctx, mx, my, 70, EY, 0.6 * (0.5 + 0.5 * math.sin(t * 6)) * (1 - P(t, 58, 0.4)))
    # surplus sparkles from panels
    sp = P(t, 50.8, 0.6)
    if sp > 0:
        for k in range(8):
            u = ((t - 50.8) * 0.8 + k / 8) % 1
            rx, ry = house_pt(HX, HB, HS, *roof_pt(0.1 + 0.8 * ((k * 0.37) % 1), 0.6))
            glow(ctx, rx + 20 * math.sin(k + t * 3), ry - 140 * u, 22, EY if k % 2 else EG, 0.85 * sp * (1 - u))
    # flow to grid
    rv = P(t, 52.9, 0.9, sm)
    full = c1 + c2[1:] + c3[1:]
    flow(ctx, full, t, reveal=rv, speed=360, spacing=70)
    if rv > 0:
        for k, base in enumerate((560, 860)):
            ax = base + ((t * 120) % 60)
            ay = np.interp(ax, [p[0] for p in full], [p[1] for p in full]) - 45
            a = rv
            rgba(ctx, GREEN, a); ctx.set_line_width(9); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(ax - 26, ay - 18); ctx.line_to(ax, ay); ctx.line_to(ax - 26, ay + 18); ctx.stroke()
    label(ctx, "Red eléctrica", 760, 800, 46, 53.45, t, bg=hx('#2E86DE'), fg=WHITE)
    # cards
    out1 = P(t, 52.6, 0.4)
    bars_card(ctx, t, out1)
    mp = P(t, 54.55, 0.5, eback)
    mo = P(t, 56.1, 0.45, eio)
    if mp > 0 and mo < 1:
        x, y, w, h = 540 + 520 * mo, 250, 390, 330
        pushscale(ctx, x + w / 2, y + h / 2, mp)
        rrect(ctx, x, y, w, h, 26); shade(ctx, WHITE, 1, 5, hx('#C9D6E8'))
        text(ctx, "Medidor", x + w / 2, y + 66, 42, INK)
        rrect(ctx, x + 35, y + 100, w - 70, 120, 16); shade(ctx, hx('#16253F'))
        val = 1250 - 85 * eio(lin(t, 54.8, 56.6))
        text(ctx, f"{int(val):05d}", x + w / 2 - 20, y + 185, 64, EG, face="Inter Black")
        text(ctx, "kWh", x + w / 2, y + 275, 34, hx('#5B6B82'))
        ay = y + 160 + 8 * math.sin(t * 6)
        rgba(ctx, GREEN); ctx.set_line_width(9); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(x + w - 60, ay - 22); ctx.line_to(x + w - 60, ay + 22)
        ctx.move_to(x + w - 76, ay + 6); ctx.line_to(x + w - 60, ay + 22); ctx.line_to(x + w - 44, ay + 6); ctx.stroke()
        ctx.restore()
    bp = P(t, 56.25, 0.6, eout)
    if bp > 0:
        x, y, w, h = 560 + 520 * (1 - bp), 230, 360, 470
        ctx.save(); ctx.translate(x + w / 2, y + h / 2); ctx.rotate(0.05 * (1 - bp) + 0.02 * math.sin(t * 2)); ctx.translate(-(x + w / 2), -(y + h / 2))
        ctx.save(); ctx.translate(8, 10); rrect(ctx, x, y, w, h, 22); rgba(ctx, (0, 0, 0), .15); ctx.fill(); ctx.restore()
        rrect(ctx, x, y, w, h, 22); shade(ctx, WHITE, 1, 5, hx('#C9D6E8'))
        rrect(ctx, x, y, w, 80, 22); rgba(ctx, hx('#2E86DE')); ctx.fill()
        rgba(ctx, hx('#2E86DE')); ctx.rectangle(x, y + 50, w, 30); ctx.fill()
        text(ctx, "Factura", x + w / 2, y + 56, 42, WHITE)
        rgba(ctx, hx('#DCE4EF'));
        for i in range(4):
            rrect(ctx, x + 36, y + 115 + i * 40, (w - 72) * (0.9 - 0.15 * (i % 2)), 16, 8); ctx.fill()
        text(ctx, "Total", x + 36, y + 320, 34, hx('#5B6B82'), align='l')
        dp = eio(lin(t, 57.0, 58.0))
        val = 120 - 75 * dp
        col = mix(hx('#E74C3C'), GREEN, dp)
        text(ctx, f"${val:.0f}", x + 36, y + 420, 86, col, align='l')
        ay = y + 370 + 10 * math.sin(t * 6)
        rgba(ctx, GREEN, dp); ctx.set_line_width(12); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(x + w - 60, ay - 34); ctx.line_to(x + w - 60, ay + 30)
        ctx.move_to(x + w - 84, ay + 6); ctx.line_to(x + w - 60, ay + 30); ctx.line_to(x + w - 36, ay + 6); ctx.stroke()
        ctx.restore()

def scene7(ctx, t):
    night = P(t, 58.3, 1.4, eio)
    sky(ctx, night, t)
    clouds(ctx, t + 80, 0.7, night)
    sun(ctx, 160, 200 + 600 * night, 90, t, alpha=1 - night)
    moon(ctx, 790, 260 + 10 * math.sin(t), 75, P(t, 58.9, 1.0))
    ground(ctx, 1180, night, t)
    HX, HB, HS = 560, 1200, 1.08
    pt = pole(ctx, 950, 1220, 560, night)
    hpt = house_pt(HX, HB, HS, 200, -230)
    cab = sag(pt, hpt, 45)
    wire(ctx, cab, lw=6, col=hx('#1F2A3A'))
    # battery
    bp = P(t, 62.3, 0.6, eback)
    bx, by, bw, bh = 70, 840, 200, 310
    bpath = [(bx + bw, 1040), (HX - 200 * HS - 5, 1040)]
    if bp > 0:
        wire(ctx, bpath, reveal=bp)
    house(ctx, HX, HB, HS, lit=1.0, pglow=1 - night, t=t, night=night)
    # zzz over panels
    zp = P(t, 59.8, 0.5)
    if zp > 0:
        for k in range(3):
            u = ((t - 59.8) * 0.5 + k / 3) % 1
            rx, ry = house_pt(HX, HB, HS, 60 + 30 * k, -440)
            text(ctx, "z", rx + 40 * u, ry - 120 * u, 50 + 20 * k, WHITE, outline=INK, ow=6, alpha=zp * math.sin(u * math.pi) * (1 - P(t, 63.0, 0.6)))
        label(ctx, "Sin sol: 0 producción", 486, 520, 44, 59.9, t, bg=hx('#5B6B82'), fg=WHITE, t1=62.1)
    if bp > 0:
        level = 1 - 0.82 * eio(lin(t, 63.1, 66.3))
        pushscale(ctx, bx + bw / 2, by + bh, bp)
        battery(ctx, bx, by, bw, bh, level, t)
        ctx.restore()
        bf = P(t, 62.9, 0.5) * (1 - P(t, 65.0, 0.6))
        flow(ctx, bpath, t, reveal=bf, alpha=bf, speed=200, spacing=50)
        label(ctx, "Batería", bx + bw / 2, by - 70, 44, 63.0, t, bg=GREEN, fg=WHITE)
    gr = P(t, 65.2, 0.9, sm)
    flow(ctx, cab, t, reveal=gr, speed=300, spacing=64)
    label(ctx, "Red eléctrica", 740, 560, 46, 66.4, t, bg=hx('#2E86DE'), fg=WHITE)

def node_icon(ctx, kind, x, y, t, s=1.0):
    if kind == 'sol':
        sun(ctx, x, y, 42 * s, t, face=True)
    elif kind == 'panel':
        mini_panel(ctx, x - 52 * s, y - 32 * s, 104 * s, 64 * s, t)
    elif kind == 'inv':
        inverter(ctx, x - 50 * s, y - 50 * s, 280, 270, t, s=0.36 * s)
    elif kind == 'casa':
        house(ctx, x, y + 50 * s, 0.24 * s, lit=1, t=t)
    elif kind == 'red':
        ctx.save(); ctx.translate(x, y + 60 * s); ctx.scale(0.2 * s, 0.2 * s)
        pole(ctx, 0, 0, 560); ctx.restore()

def scene8(ctx, t):
    day = P(t, 68.0, 1.2, eio)
    sky(ctx, 1 - day, t)
    clouds(ctx, t + 100, 0.8 * day)
    fin = P(t, 73.85, 0.8, eio)
    # summary layer
    if fin < 1:
        pushscale(ctx, 486, 700, 1 - 0.3 * fin)
        ctx.push_group()
        nodes = [('sol', 'Sol', 150, 330), ('panel', 'Panel', 320, 570), ('inv', 'Inversor', 490, 330),
                 ('casa', 'Casa', 660, 570), ('red', 'Red', 830, 330)]
        times = [68.35, 68.85, 69.35, 69.85, 70.35]
        for i in range(4):
            (_, _, x0, y0), (_, _, x1, y1) = nodes[i], nodes[i + 1]
            ang = math.atan2(y1 - y0, x1 - x0)
            a0 = (x0 + 100 * math.cos(ang), y0 + 100 * math.sin(ang))
            a1 = (x1 - 100 * math.cos(ang), y1 - 100 * math.sin(ang))
            rv = P(t, times[i] + 0.25, 0.4)
            flow(ctx, [a0, a1], t, reveal=rv, speed=200, spacing=50)
            if rv >= 1:
                ctx.save(); ctx.translate(*a1); ctx.rotate(ang)
                poly(ctx, [(4, 0), (-22, -16), (-22, 16)]); rgba(ctx, EG); ctx.fill(); ctx.restore()
        for (k, name, x, y), t0 in zip(nodes, times):
            p = P(t, t0, 0.5, eback)
            if p <= 0: continue
            pushscale(ctx, x, y, p)
            ctx.save(); ctx.translate(0, 8); circle(ctx, x, y, 88); rgba(ctx, (0, 0, 0), .12); ctx.fill(); ctx.restore()
            circle(ctx, x, y, 88); shade(ctx, WHITE, 1, 6, hx('#C9D6E8'))
            node_icon(ctx, k, x, y, t)
            text(ctx, name, x, y + 140, 38, WHITE, outline=INK, ow=9)
            ctx.restore()
        badges = [('gear', "Sin piezas", "móviles", 180, 69.0), ('mute', "Sin ruido", None, 486, 70.0), ('25', "años de", "vida útil", 792, 72.2)]
        for kind, l1, l2, x, t0 in badges:
            p = P(t, t0, 0.5, eback)
            if p <= 0: continue
            y = 960
            pushscale(ctx, x, y, p)
            circle(ctx, x, y, 92); shade(ctx, hx('#FFD23F') if kind == '25' else GREEN, 1, 6)
            if kind == 'gear':
                ctx.save(); ctx.translate(x, y)
                rgba(ctx, WHITE)
                for i in range(8):
                    ctx.save(); ctx.rotate(i * math.pi / 4); rrect(ctx, -11, -52, 22, 20, 4); ctx.fill(); ctx.restore()
                circle(ctx, 0, 0, 38); ctx.fill(); rgba(ctx, GREEN); circle(ctx, 0, 0, 15); ctx.fill()
                ctx.restore()
                rgba(ctx, hx('#E74C3C')); ctx.set_line_width(11); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.move_to(x - 50, y - 50); ctx.line_to(x + 50, y + 50); ctx.stroke()
            elif kind == 'mute':
                rgba(ctx, WHITE)
                poly(ctx, [(x - 48, y - 18), (x - 26, y - 18), (x, y - 44), (x, y + 44), (x - 26, y + 18), (x - 48, y + 18)]); ctx.fill()
                ctx.set_line_width(10); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.move_to(x + 16, y - 20); ctx.line_to(x + 52, y + 20); ctx.move_to(x + 52, y - 20); ctx.line_to(x + 16, y + 20); ctx.stroke()
            else:
                text(ctx, "25+", x, y + 24, 64, INK)
            text(ctx, l1, x, y + 150, 38, WHITE, outline=INK, ow=9)
            if l2: text(ctx, l2, x, y + 196, 38, WHITE, outline=INK, ow=9)
            ctx.restore()
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(1 - fin)
        ctx.restore()
    # closing
    if fin > 0:
        z = 1 + 0.06 * lin(t, 74.0, DUR)
        pushscale(ctx, 540, 1000, (0.8 + 0.2 * fin) * z)
        ctx.push_group()
        sun(ctx, 486, 330 + 8 * math.sin(t * 1.5), 125, t)
        ground(ctx, 1230, 0, t)
        house(ctx, 486, 1250, 1.3, lit=1, pglow=1, t=t)
        for k in range(10):
            u = (t * 0.5 + k / 10) % 1
            ang = k * 2 * math.pi / 10 + t * 0.3
            glow(ctx, 486 + math.cos(ang) * (300 + 80 * u), 900 + math.sin(ang) * (260 + 60 * u), 22, EY if k % 2 else EG, 0.9 * math.sin(u * math.pi))
        for u in (0.25, 0.5, 0.75):
            px, py = house_pt(486, 1250, 1.3, *roof_pt(u, 0.5))
            glow(ctx, px, py, 70 + 10 * math.sin(t * 6 + u * 10), (1, 1, .85), 0.55)
        ctx.pop_group_to_source(); ctx.paint_with_alpha(fin)
        ctx.restore()

SCENES = [scene1, scene2, scene3, scene4, scene5, scene6, scene7, scene8]

# ---------------------------------------------------------------- subtitles
def build_chunks():
    words = [(s, e, w.strip()) for s, e, w in WORDS]
    chunks, cur = [], []
    for i, (s, e, w) in enumerate(words):
        if cur:
            prev = cur[-1]
            chars = sum(len(x[2]) + 1 for x in cur) + len(w)
            if (len(cur) >= 5 or (prev[2][-1] in ',.?!' and len(cur) >= 2) or s - prev[1] > 0.45 or chars > 27
                    or prev[2][-1] in '.?!'):
                chunks.append(cur); cur = []
        cur.append((s, e, w))
    if cur: chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        st = c[0][0] - 0.05
        en = c[-1][1] + 0.5
        if i + 1 < len(chunks): en = min(en, chunks[i + 1][0][0] - 0.05)
        out.append((st, en, c))
    return out
CHUNKS = build_chunks()

def subtitles(ctx, t):
    for st, en, c in CHUNKS:
        if st <= t < en:
            size = 76
            font(ctx, size)
            sp = ctx.text_extents(" ").x_advance + 10
            ws = [ctx.text_extents(w).x_advance for _, _, w in c]
            lines, cur, cw = [], [], 0
            for i, wd in enumerate(ws):
                if cur and cw + sp + wd > 860:
                    lines.append(cur); cur, cw = [], 0
                cur.append(i); cw += (sp if len(cur) > 1 else 0) + wd
            lines.append(cur)
            p = P(t, st, 0.15, eback)
            a = clamp(lin(t, st, st + 0.08)) * (1 - clamp(lin(t, en - 0.08, en)))
            base = 1560 - (len(lines) - 1) * 92
            pushscale(ctx, 486, 1520, 0.85 + 0.15 * p)
            for li, line in enumerate(lines):
                lw_ = sum(ws[i] for i in line) + sp * (len(line) - 1)
                x = 486 - lw_ / 2; y = base + li * 92
                for i in line:
                    s, e, w = c[i]
                    nxt = c[i + 1][0] if i + 1 < len(c) else en
                    col = EY if (s - 0.03 <= t < min(nxt, max(e, s + 0.15) + 0.25) - 0.03) else WHITE
                    ctx.move_to(x, y); ctx.text_path(w)
                    rgba(ctx, (0, 0, 0), a); ctx.set_line_width(15); ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke_preserve()
                    rgba(ctx, col, a); ctx.fill()
                    x += ws[i] + sp
            ctx.restore()
            break

# ---------------------------------------------------------------- frame
def render(t, ctx):
    ctx.set_operator(cairo.OPERATOR_OVER)
    idx = max(i for i in range(8) if t >= B[i] - (XF if i > 0 else 0)) if t >= 0 else 0
    # main scene: the last one whose (start - XF) <= t
    cur = None
    for i in range(8):
        if t >= B[i] - XF or i == 0: cur = i
    prev = cur - 1 if cur > 0 and t < B[cur] + XF else None
    if prev is not None:
        SCENES[prev](ctx, t)
        a = sm((t - (B[cur] - XF)) / (2 * XF))
        ctx.push_group();
        pushscale(ctx, 540, 960, 1.06 - 0.06 * a)
        SCENES[cur](ctx, t)
        ctx.restore()
        ctx.pop_group_to_source(); ctx.paint_with_alpha(a)
    else:
        SCENES[cur](ctx, t)
    subtitles(ctx, t)

def main():
    mode = sys.argv[1]
    if mode == 'png':
        for ts in sys.argv[2:]:
            t = float(ts)
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
            render(t, ctx); surf.write_to_png(os.path.join(HERE, 'frames', f"f_{t:06.2f}.png"))
    else:
        f0, f1, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(FPS),
                              '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        for f in range(f0, f1):
            ctx = cairo.Context(surf)
            ctx.set_source_rgb(0, 0, 0); ctx.paint()
            render(f / FPS, ctx)
            surf.flush()
            p.stdin.write(bytes(surf.get_data()))
        p.stdin.close(); p.wait()

if __name__ == '__main__':
    main()
