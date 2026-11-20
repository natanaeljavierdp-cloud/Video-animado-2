"""Mundo A: barrio isométrico (vista aérea tipo dron) con alcantarillado en rayos X y planta de tratamiento."""
import math
import random
import cairo
from common import *

S = 40.0
K = 0.8660254


def iso(X, Y, Z=0.0):
    return ((X - Y) * S * K, (X + Y) * S * 0.5 - Z * S)


def ipoly(ctx, pts3):
    poly(ctx, [iso(*p) for p in pts3])


MAIN = (-1, 2)                    # casa principal (X0, Y0)
ROW1 = [-26, -14, -1, 12, 25]
ROW2 = [-26, -14, -1, 12, 25]
SEWER_Y = 11.75
ISL = (-34, 66, -12, 36)

HOUSE_COLS = [
    (PAL['wall_pink'], PAL['wall_pink2'], PAL['roof'], PAL['roof2']),
    (PAL['wall_beige'], PAL['wall_beige2'], C('#c98a6c'), C('#a96e55')),
    (C('#f3d2c4'), C('#e2b9a8'), C('#cf7a63'), C('#ad604c')),
    (C('#efe2c9'), C('#dccaa9'), C('#d48f6e'), C('#b47257')),
]


def houses():
    out = []
    for i, x in enumerate(ROW1):
        out.append(dict(X0=x, Y0=2, w=6, d=5, h=3.2, rh=2.3, col=HOUSE_COLS[0] if x == MAIN[0] else HOUSE_COLS[(i + 1) % 4], main=(x == MAIN[0])))
    for i, x in enumerate(ROW2):
        out.append(dict(X0=x + 1, Y0=16.5, w=5.5, d=5, h=3.0, rh=2.1, col=HOUSE_COLS[(i + 2) % 4], main=False))
    return out


HOUSES = houses()
rnd = random.Random(11)
TREES = []
for x in (-31, -20, -8, 6, 19, 31):
    TREES.append((x + rnd.uniform(-.8, .8), 0.0 + rnd.uniform(-.5, .5)))
    TREES.append((x + rnd.uniform(-.8, .8), 24.5 + rnd.uniform(-.5, .5)))
for y in range(-9, 35, 4):
    TREES.append((59.0 + rnd.uniform(-.4, .4), y + rnd.uniform(-1, 1)))
    TREES.append((65.0 + rnd.uniform(-.3, .3), y + 2 + rnd.uniform(-1, 1)))
for k in range(8):
    TREES.append((rnd.uniform(-32, 30), rnd.uniform(27.5, 34)))
    TREES.append((rnd.uniform(-32, 30), rnd.uniform(-10, -3)))

TANKS = [(44, 7.5, 3.0, 'grey'), (52.5, 7.5, 3.0, 'mid'), (48.5, 17.5, 3.4, 'clean')]


def laterals():
    out = []
    for hs in HOUSES:
        cx = hs['X0'] + hs['w'] / 2
        if hs['Y0'] < 10:
            out.append(((cx, hs['Y0'] + hs['d']), (cx, SEWER_Y), hs['main']))
        else:
            out.append(((cx, hs['Y0']), (cx, SEWER_Y), False))
    return out


LATS = laterals()
MAINLINE = [(-30, SEWER_Y), (38.5, SEWER_Y), (41.5, 7.5)]


# ----------------------------------------------------------------------- primitivas iso
def box(ctx, X0, Y0, X1, Y1, Z0, Z1, top, right, left, lw=3):
    # cara +Y (izquierda-abajo)
    ipoly(ctx, [(X0, Y1, Z0), (X1, Y1, Z0), (X1, Y1, Z1), (X0, Y1, Z1)])
    fs(ctx, left, lw)
    # cara +X (derecha-abajo)
    ipoly(ctx, [(X1, Y0, Z0), (X1, Y1, Z0), (X1, Y1, Z1), (X1, Y0, Z1)])
    fs(ctx, right, lw)
    ipoly(ctx, [(X0, Y0, Z1), (X1, Y0, Z1), (X1, Y1, Z1), (X0, Y1, Z1)])
    fs(ctx, top, lw)


def face_rect_y(ctx, Y, X0, X1, Z0, Z1, col, lw=2.5):
    ipoly(ctx, [(X0, Y, Z0), (X1, Y, Z0), (X1, Y, Z1), (X0, Y, Z1)])
    fs(ctx, col, lw)


def face_rect_x(ctx, X, Y0, Y1, Z0, Z1, col, lw=2.5):
    ipoly(ctx, [(X, Y0, Z0), (X, Y1, Z0), (X, Y1, Z1), (X, Y0, Z1)])
    fs(ctx, col, lw)


def window_y(ctx, Y, X0, X1, Z0, Z1):
    face_rect_y(ctx, Y, X0 - .12, X1 + .12, Z0 - .12, Z1 + .12, PAL['white'])
    ipoly(ctx, [(X0, Y, Z0), (X1, Y, Z0), (X1, Y, Z1), (X0, Y, Z1)])
    x0, y0 = iso(X0, Y, Z1)
    x1, y1 = iso(X1, Y, Z0)
    ctx.set_source(lgrad(x0, y0, x1, y1, [(0, C('#cdeefc')), (1, C('#7cbfe0'))]))
    ctx.fill_preserve()
    fs(ctx, None, 2.2)
    xm = (X0 + X1) / 2
    ctx.move_to(*iso(xm, Y, Z0))
    ctx.line_to(*iso(xm, Y, Z1))
    setc(ctx, PAL['white'])
    ctx.set_line_width(Pen.L(3))
    ctx.stroke()


def window_x(ctx, X, Y0, Y1, Z0, Z1):
    face_rect_x(ctx, X, Y0 - .12, Y1 + .12, Z0 - .12, Z1 + .12, PAL['white'])
    ipoly(ctx, [(X, Y0, Z0), (X, Y1, Z0), (X, Y1, Z1), (X, Y0, Z1)])
    x0, y0 = iso(X, Y0, Z1)
    x1, y1 = iso(X, Y1, Z0)
    ctx.set_source(lgrad(x0, y0, x1, y1, [(0, C('#d5f1fd')), (1, C('#86c6e4'))]))
    ctx.fill_preserve()
    fs(ctx, None, 2.2)


def house(ctx, hs, roof_alpha=1.0):
    X0, Y0, w, d, h, rh = hs['X0'], hs['Y0'], hs['w'], hs['d'], hs['h'], hs['rh']
    X1, Y1 = X0 + w, Y0 + d
    wall, wall2, roof, roof2 = hs['col']
    # sombra
    ipoly(ctx, [(X0 + .3, Y1, 0), (X1 + 1.6, Y1, 0), (X1 + 1.6, Y0 + 1.2, 0), (X1, Y0, 0), (X0 + .3, Y0, 0)])
    setc(ctx, C('#000000', 0.12))
    ctx.fill()
    # muros
    face_rect_y(ctx, Y1, X0, X1, 0, h, wall2, 3)
    face_rect_x(ctx, X1, Y0, Y1, 0, h, wall, 3)
    # hastial
    ipoly(ctx, [(X1, Y0, h), (X1, Y1, h), (X1, (Y0 + Y1) / 2, h + rh)])
    fs(ctx, wall, 3)
    # puerta y ventanas
    face_rect_y(ctx, Y1, X0 + w * 0.42, X0 + w * 0.42 + 1.1, 0, 1.9, C('#b98563'), 2.5)
    ctx.arc(*iso(X0 + w * 0.42 + 0.9, Y1, 1.0), Pen.L(2.5) * 1.3, 0, 2 * math.pi)
    setc(ctx, PAL['ink'])
    ctx.fill()
    window_y(ctx, Y1, X0 + 0.7, X0 + 1.9, 1.2, 2.3)
    window_y(ctx, Y1, X1 - 1.9, X1 - 0.7, 1.2, 2.3)
    window_x(ctx, X1, Y0 + 1.0, Y0 + 2.1, 1.2, 2.3)
    window_x(ctx, X1, Y1 - 2.1, Y1 - 1.0, 1.2, 2.3)
    # tejado
    o = 0.35
    Ym = (Y0 + Y1) / 2
    ctx.push_group()
    ipoly(ctx, [(X0 - o, Ym, h + rh), (X1 + o, Ym, h + rh), (X1 + o, Y0 - o, h - .25), (X0 - o, Y0 - o, h - .25)])
    fs(ctx, roof2, 3)
    ipoly(ctx, [(X0 - o, Ym, h + rh), (X1 + o, Ym, h + rh), (X1 + o, Y1 + o, h - .25), (X0 - o, Y1 + o, h - .25)])
    a = iso(X0, Ym, h + rh)
    b = iso(X0, Y1 + o, h - .25)
    ctx.set_source(lgrad(a[0], a[1], b[0], b[1], [(0, roof), (1, mix(roof, roof2, .5))]))
    ctx.fill_preserve()
    fs(ctx, None, 3)
    # líneas de tejas
    for k in range(1, 4):
        u = k / 4
        p0 = (X0 - o, lerp(Ym, Y1 + o, u), lerp(h + rh, h - .25, u))
        p1 = (X1 + o, p0[1], p0[2])
        ctx.move_to(*iso(*p0))
        ctx.line_to(*iso(*p1))
    setc(ctx, roof2)
    ctx.set_line_width(Pen.L(2))
    ctx.stroke()
    # borde frontal del alero
    ipoly(ctx, [(X1 + o, Ym, h + rh), (X1 + o, Y1 + o, h - .25), (X1 + o, Y1 + o, h - .55), (X1 + o, Ym, h + rh - .3)])
    fs(ctx, roof2, 2.5)
    # chimenea
    box(ctx, X0 + 1.0, Ym - 1.5, X0 + 1.8, Ym - 0.8, h + rh - 1.0, h + rh + 0.9, C('#e6d3c0'), C('#d8bfa8'), C('#c9ad93'), 2.5)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(roof_alpha)


def cylinder(ctx, Xc, Yc, r, h, side, top, water=None, wcol=None, t=0):
    cx, cy = iso(Xc, Yc, 0)
    rx, ry = 1.2247 * r * S, 0.7071 * r * S
    hh = h * S
    # sombra
    ctx.save()
    ctx.translate(cx + 25, cy + 14)
    ctx.scale(rx * 1.05, ry * 1.05)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    setc(ctx, C('#000000', 0.12))
    ctx.fill()
    # cuerpo
    ctx.move_to(cx - rx, cy - hh)
    ctx.line_to(cx - rx, cy)
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(rx, ry)
    ctx.arc_negative(0, 0, 1, math.pi, 0)
    ctx.restore()
    ctx.line_to(cx + rx, cy - hh)
    ctx.close_path()
    ctx.set_source(lgrad(cx - rx, 0, cx + rx, 0, [(0, mix(side, PAL['white'], .3)), (0.6, side), (1, mix(side, C('#000000'), .15))]))
    ctx.fill_preserve()
    fs(ctx, None, 3)
    # tapa
    ctx.save()
    ctx.translate(cx, cy - hh)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    fs(ctx, top, 3)
    if water is not None:
        ctx.save()
        ctx.translate(cx, cy - hh + 4)
        ctx.scale(rx * 0.86, ry * 0.86)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        setc(ctx, wcol)
        ctx.fill_preserve()
        fs(ctx, None, 2.5)
        # brazo giratorio del clarificador
        ang = t * 0.8
        ctx.move_to(cx, cy - hh + 4)
        ctx.line_to(cx + math.cos(ang) * rx * 0.86, cy - hh + 4 + math.sin(ang) * ry * 0.86)
        setc(ctx, PAL['ink'])
        ctx.set_line_width(Pen.L(4))
        ctx.stroke()
        for k in range(5):
            a2 = k * 1.3 + t * 0.6
            sparkle(ctx, cx + math.cos(a2) * rx * 0.5, cy - hh + 4 + math.sin(a2) * ry * 0.5, 9, 0.7 * (0.5 + 0.5 * math.sin(t * 3 + k)))


# ----------------------------------------------------------------------- mundo
def draw(ctx, t, xray=0.0, flow_all=0.0, flow_main=0.0, roof_fade=0.0, toplant=0.0):
    # cielo
    ctx.rectangle(-9000, -9000, 20000, 20000)
    ctx.set_source(lgrad(0, -3500, 0, 3500, [(0, C('#76b8e0')), (0.6, PAL['sky2']), (1, C('#e6f4fa'))]))
    ctx.fill()
    for i, (x, y, s) in enumerate([(-2100, -900, 210), (1900, -1300, 260), (-2600, 1500, 240), (2900, 700, 220), (300, -2300, 280),
                                   (-1200, -2400, 200), (2400, -2600, 230), (-300, 2900, 260), (1800, 2800, 240), (-2900, -2000, 180)]):
        cloud(ctx, x + 60 * math.sin(t * 0.15 + i), y, s)

    X0, X1, Y0, Y1 = ISL
    T = 7
    # costados de la isla (tierra en capas)
    ipoly(ctx, [(X0, Y1, 0), (X1, Y1, 0), (X1, Y1, -T), (X0, Y1, -T)])
    a = iso(X0, Y1, 0)
    b = iso(X0, Y1, -T)
    ctx.set_source(lgrad(a[0], a[1], b[0], b[1], [(0, PAL['soil']), (1, PAL['soil3'])]))
    ctx.fill_preserve()
    fs(ctx, None, 3.5)
    ipoly(ctx, [(X1, Y0, 0), (X1, Y1, 0), (X1, Y1, -T), (X1, Y0, -T)])
    ctx.set_source(lgrad(a[0], a[1], b[0], b[1], [(0, PAL['soil2']), (1, C('#a98a62'))]))
    ctx.fill_preserve()
    fs(ctx, None, 3.5)
    r = random.Random(5)
    for _ in range(90):
        if r.random() < .5:
            p = iso(r.uniform(X0, X1), Y1, r.uniform(-T + .5, -.6))
        else:
            p = iso(X1, r.uniform(Y0, Y1), r.uniform(-T + .5, -.6))
        ctx.arc(p[0], p[1], r.uniform(6, 14), 0, 2 * math.pi)
        setc(ctx, C('#b8976b'))
        ctx.fill()
    # franja de pasto en el borde
    ipoly(ctx, [(X0, Y1, 0), (X1, Y1, 0), (X1, Y1, -0.6), (X0, Y1, -0.6)])
    fs(ctx, PAL['grass2'], 3)
    ipoly(ctx, [(X1, Y0, 0), (X1, Y1, 0), (X1, Y1, -0.6), (X1, Y0, -0.6)])
    fs(ctx, C('#86b552'), 3)
    # superficie
    ipoly(ctx, [(X0, Y0, 0), (X1, Y0, 0), (X1, Y1, 0), (X0, Y1, 0)])
    ctx.set_source(lgrad(*iso(X0, Y0), *iso(X1, Y1), [(0, PAL['grass3']), (1, PAL['grass'])]))
    ctx.fill_preserve()
    fs(ctx, None, 3.5)
    # franjas de césped
    for k in range(int(X0), int(X1), 4):
        ipoly(ctx, [(k, Y0, 0), (k + 2, Y0, 0), (k + 2, Y1, 0), (k, Y1, 0)])
        setc(ctx, C('#ffffff', 0.06))
        ctx.fill()
    # río
    ipoly(ctx, [(60, Y0, 0), (64, Y0, 0), (64, Y1, 0), (60, Y1, 0)])
    ctx.set_source(lgrad(*iso(60, 0), *iso(64, 0), [(0, C('#8fd6f5')), (1, C('#4fb1e0'))]))
    ctx.fill_preserve()
    fs(ctx, None, 3)
    for k in range(14):
        yy = (Y0 + (k * 3.3 + t * 1.6) % (Y1 - Y0))
        xx = 61 + (k % 3) * 1.0
        ctx.move_to(*iso(xx, yy))
        ctx.line_to(*iso(xx, yy + 1.2))
        setc(ctx, C('#ffffff', 0.8))
        ctx.set_line_width(Pen.L(4))
        ctx.stroke()
    ipoly(ctx, [(60, Y1, 0), (64, Y1, 0), (64, Y1, -T), (60, Y1, -T)])
    ctx.set_source(lgrad(*iso(60, Y1, 0), *iso(60, Y1, -T), [(0, C('#8fd6f5', 0.95)), (1, C('#bfe8fa', 0.4))]))
    ctx.fill()
    # calle y aceras
    ipoly(ctx, [(X0, 9, 0), (36, 9, 0), (36, 14.5, 0), (X0, 14.5, 0)])
    fs(ctx, PAL['side'], 3)
    ipoly(ctx, [(X0, 10, 0), (36, 10, 0), (36, 13.5, 0), (X0, 13.5, 0)])
    fs(ctx, PAL['street'], 3)
    for k in range(int(X0), 36, 3):
        ipoly(ctx, [(k, 11.6, 0), (k + 1.4, 11.6, 0), (k + 1.4, 11.9, 0), (k, 11.9, 0)])
        setc(ctx, PAL['white'])
        ctx.fill()
    # caminos a las casas
    for hs in HOUSES:
        cx = hs['X0'] + hs['w'] * 0.42 + 0.55
        if hs['Y0'] < 10:
            ipoly(ctx, [(cx - .6, hs['Y0'] + hs['d'], 0), (cx + .6, hs['Y0'] + hs['d'], 0), (cx + .6, 9, 0), (cx - .6, 9, 0)])
        else:
            ipoly(ctx, [(cx - .6, 14.5, 0), (cx + .6, 14.5, 0), (cx + .6, hs['Y0'], 0), (cx - .6, hs['Y0'], 0)])
        fs(ctx, PAL['side'], 2.5)
    # planta: plataforma
    ipoly(ctx, [(36, 1.5, 0), (58, 1.5, 0), (58, 24, 0), (36, 24, 0)])
    fs(ctx, C('#d9d6cf'), 3)
    for k in range(37, 58, 3):
        ctx.move_to(*iso(k, 1.5))
        ctx.line_to(*iso(k, 24))
    setc(ctx, C('#c5c1b8'))
    ctx.set_line_width(Pen.L(2))
    ctx.stroke()
    # tubo de salida al río
    ctx.move_to(*iso(51, 17.5))
    ctx.line_to(*iso(61, 17.5))
    setc(ctx, PAL['ink'])
    ctx.set_line_width(26 + Pen.L(3) * 2)
    ctx.stroke()
    ctx.move_to(*iso(51, 17.5))
    ctx.line_to(*iso(61, 17.5))
    setc(ctx, C('#9bd8f2'))
    ctx.set_line_width(26)
    ctx.stroke()

    # ---- rayos X: alcantarillado bajo la calle y conexiones
    if xray > 0:
        ctx.push_group()
        routes = [(a, b, m) for a, b, m in LATS] + [(MAINLINE[0], MAINLINE[1], False), (MAINLINE[1], MAINLINE[2], False)]
        for a, b, m in routes:
            wdt = 0.7 if (a, b) not in ((MAINLINE[0], MAINLINE[1]), (MAINLINE[1], MAINLINE[2])) else 1.1
            ctx.move_to(*iso(*a))
            ctx.line_to(*iso(*b))
            setc(ctx, PAL['ink'])
            ctx.set_line_width(wdt * S * 1.6 + Pen.L(3) * 2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()
        for a, b, m in routes:
            wdt = 0.7 if (a, b) not in ((MAINLINE[0], MAINLINE[1]), (MAINLINE[1], MAINLINE[2])) else 1.1
            ctx.move_to(*iso(*a))
            ctx.line_to(*iso(*b))
            setc(ctx, C('#8a6a48'))
            ctx.set_line_width(wdt * S * 1.6)
            ctx.stroke()
        for a, b, m in routes:
            big = (a, b) in ((MAINLINE[0], MAINLINE[1]), (MAINLINE[1], MAINLINE[2]))
            wdt = 1.1 if big else 0.7
            ctx.move_to(*iso(*a))
            ctx.line_to(*iso(*b))
            setc(ctx, PAL['pipe_in'])
            ctx.set_line_width(wdt * S * 0.95)
            ctx.stroke()
            fl = flow_main if (m or big) else flow_all
            if big:
                fl = max(flow_main, flow_all)
            if fl > 0:
                ctx.move_to(*iso(*a))
                ctx.line_to(*iso(*b))
                setc(ctx, PAL['used'], fl)
                ctx.set_line_width(wdt * S * 0.62)
                ctx.stroke()
                ctx.move_to(*iso(*a))
                ctx.line_to(*iso(*b))
                setc(ctx, C('#d9e6ee', fl))
                ctx.set_line_width(wdt * S * 0.22)
                ctx.set_dash([28, 36], -t * 140)
                ctx.stroke()
                ctx.set_dash([])
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(xray)
        # flechas de dirección
        if flow_main > 0:
            fa = flow_main * xray
            for (a, b) in ((LATS[2][0], LATS[2][1]),):
                pl = PL(iso(*a), (iso(*b),))
                ph = (t * 0.8) % 1
                arrow(ctx, pl, pl.len * ph * 0.5, pl.len * (0.3 + ph * 0.5), w=14, a=fa * 0.9, col=PAL['used'])
        if toplant > 0:
            pl = PL(iso(16, SEWER_Y), (iso(37, SEWER_Y),))
            ph = (t * 0.6) % 1
            arrow(ctx, pl, pl.len * ph * 0.6, pl.len * (0.35 + ph * 0.6), w=20, a=toplant * xray, col=PAL['used'])

    # ---- objetos ordenados por profundidad
    objs = []
    for hs in HOUSES:
        objs.append((hs['X0'] + hs['w'] + hs['Y0'] + hs['d'] - 2, 'house', hs))
    for (x, y) in TREES:
        objs.append((x + y, 'tree', (x, y)))
    for tk in TANKS:
        objs.append((tk[0] + tk[1] + tk[2], 'tank', tk))
    objs.append((42 + 21 - 1, 'bld', None))
    objs.sort(key=lambda o: o[0])
    for _, kind, o in objs:
        if kind == 'house':
            ra = 1.0 - roof_fade if o['main'] else 1.0
            house(ctx, o, ra)
        elif kind == 'tree':
            x, y = o
            p = iso(x, y)
            tree(ctx, p[0], p[1], 46, seed=int(x * 7 + y * 13))
        elif kind == 'tank':
            Xc, Yc, rr, typ = o
            wc = {'grey': PAL['used'], 'mid': mix(PAL['used'], PAL['water'], .35), 'clean': PAL['water']}[typ]
            cylinder(ctx, Xc, Yc, rr, 1.4, C('#dcd8d0'), C('#c7c2b8'), water=True, wcol=wc, t=t)
        elif kind == 'bld':
            box(ctx, 37.5, 17, 42.5, 22.5, 0, 3, C('#e9e4da'), C('#d9d2c4'), C('#c9c0b0'))
            window_y(ctx, 22.5, 38.3, 39.6, 1.2, 2.2)
            window_y(ctx, 22.5, 40.4, 41.7, 1.2, 2.2)
            window_x(ctx, 42.5, 18, 19.4, 1.2, 2.2)
            window_x(ctx, 42.5, 20.3, 21.7, 1.2, 2.2)
    # tubos entre tanques (sobre suelo)
    for (a, b) in (((45.5, 9.5), (51, 9.5)), ((52.5, 10.3), (50, 14.5))):
        ctx.move_to(*iso(*a, 0.6))
        ctx.line_to(*iso(*b, 0.6))
        setc(ctx, PAL['ink'])
        ctx.set_line_width(18 + Pen.L(3) * 2)
        ctx.stroke()
        ctx.move_to(*iso(*a, 0.6))
        ctx.line_to(*iso(*b, 0.6))
        setc(ctx, C('#c9c3b8'))
        ctx.set_line_width(18)
        ctx.stroke()

    # nubes "cercanas" a la altura del dron
    for i, (X, Y, Z, s) in enumerate([(-8, -2, 16, 120), (10, 18, 18, 140), (30, 0, 15, 110), (-20, 22, 17, 130), (48, 28, 16, 120)]):
        p = iso(X + 0.6 * math.sin(t * 0.2 + i), Y, Z)
        cloud(ctx, p[0], p[1], s, 0.95 * clamp(1.5 - Pen.z))


def overlay_clouds(ctx, t, z, a):
    """Nubes en primer plano (espacio de pantalla) que pasan cuando el dron desciende/asciende."""
    if a <= 0:
        return
    k = math.log(max(z, 1e-3) / 0.45)
    for i, (x, y, s) in enumerate([(-0.35, -0.3, 1.0), (0.4, 0.25, 1.2), (-0.2, 0.42, 0.9), (0.35, -0.38, 0.8)]):
        sc = math.exp(k * 1.6)
        px = W / 2 + x * W * sc + 30 * math.sin(t * 0.3 + i)
        py = H / 2 + y * H * sc
        ss_ = 150 * s * sc
        al = a * clamp(1.6 - sc * 0.5) * 0.9
        Pen.z = 1.0
        cloud(ctx, px, py, ss_, al)
