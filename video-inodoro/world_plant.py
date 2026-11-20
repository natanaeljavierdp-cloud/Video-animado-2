"""Mundo C: planta de tratamiento en corte (rejillas, bacterias buenas, clarificador y río)."""
import math
import random
import cairo
from common import *

GROUND = 1000
rnd = random.Random(21)
# partículas grises que llegan a la rejilla
SOLIDS = [(rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(10, 18)) for _ in range(12)]
# partículas de suciedad en el tanque de bacterias y quién se las come
DIRT = []
for i in range(16):
    DIRT.append(dict(x=rnd.uniform(960, 1640), y=rnd.uniform(1080, 1400), r=rnd.uniform(9, 15), eat=56.3 + i * 0.12 + rnd.uniform(0, .25)))
BACT = [dict(x=rnd.uniform(980, 1620), y=rnd.uniform(1080, 1400), ph=rnd.uniform(0, 6.28), col=rnd.choice([C('#8fd36f'), C('#7cc95f'), C('#a2db7e')])) for _ in range(7)]
for i, d in enumerate(DIRT):
    d['b'] = i % len(BACT)
BUBBLES = [(rnd.uniform(940, 1660), rnd.uniform(0, 1), rnd.uniform(4, 9)) for _ in range(30)]


def concrete_tank(ctx, x0, x1, ytop, ybot, wall=34):
    # paredes de concreto en corte (forma de U)
    ctx.move_to(x0 - wall, ytop - 30)
    ctx.line_to(x0, ytop - 30)
    ctx.line_to(x0, ybot)
    ctx.line_to(x1, ybot)
    ctx.line_to(x1, ytop - 30)
    ctx.line_to(x1 + wall, ytop - 30)
    ctx.line_to(x1 + wall, ybot + wall)
    ctx.line_to(x0 - wall, ybot + wall)
    ctx.close_path()
    fs(ctx, PAL['concrete'], 3.5)
    r = random.Random(int(x0))
    for _ in range(30):
        side = r.random()
        if side < .4:
            x, y = r.uniform(x0 - wall + 6, x0 - 6), r.uniform(ytop - 20, ybot + wall - 6)
        elif side < .8:
            x, y = r.uniform(x1 + 6, x1 + wall - 6), r.uniform(ytop - 20, ybot + wall - 6)
        else:
            x, y = r.uniform(x0, x1), r.uniform(ybot + 6, ybot + wall - 6)
        ctx.arc(x, y, r.uniform(2, 4), 0, 2 * math.pi)
        setc(ctx, PAL['concrete2'])
        ctx.fill()


def round_tank_back(ctx, x0, x1, ytop, ybot):
    """Tanque redondo cortado a la mitad: pared trasera curva visible."""
    cx = (x0 + x1) / 2
    rx = (x1 - x0) / 2
    ry = rx * 0.22
    ctx.rectangle(x0, ytop, x1 - x0, ybot - ytop)
    ctx.set_source(lgrad(x0, 0, x1, 0, [(0, C('#c9c3b8')), (0.5, C('#e3ded5')), (1, C('#c3bdb1'))]))
    ctx.fill()
    ctx.save()
    ctx.translate(cx, ytop)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, math.pi, 2 * math.pi)
    ctx.restore()
    fs(ctx, C('#d6d0c6'), 3)


def round_tank_front(ctx, x0, x1, ytop, ybot, wall=28):
    """Cara de corte del tanque redondo (perfil en U) + borde elíptico."""
    cx = (x0 + x1) / 2
    rx = (x1 - x0) / 2
    ry = rx * 0.22
    # paredes de corte
    for xa, xb in ((x0 - wall, x0), (x1, x1 + wall)):
        ctx.rectangle(xa, ytop, wall, ybot - ytop + wall)
        fs(ctx, PAL['concrete'], 3.5)
    ctx.rectangle(x0 - wall, ybot, x1 - x0 + 2 * wall, wall)
    fs(ctx, PAL['concrete'], 3.5)
    # base elíptica (piso del tanque)
    ctx.save()
    ctx.translate(cx, ybot)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, math.pi)
    ctx.restore()
    setc(ctx, PAL['ink'])
    ctx.set_line_width(Pen.L(3))
    ctx.stroke()


def water_block(ctx, x0, x1, level, ybot, top, bot, t, amp=4):
    ctx.move_to(x0, ybot)
    ctx.line_to(x0, level)
    n = 30
    for i in range(n + 1):
        x = lerp(x0, x1, i / n)
        ctx.line_to(x, level + amp * math.sin(x * 0.03 + t * 4))
    ctx.line_to(x1, ybot)
    ctx.close_path()
    ctx.set_source(lgrad(0, level, 0, ybot, [(0, top), (1, bot)]))
    ctx.fill()
    ctx.move_to(x0, level)
    for i in range(n + 1):
        x = lerp(x0, x1, i / n)
        ctx.line_to(x, level + amp * math.sin(x * 0.03 + t * 4))
    setc(ctx, C('#ffffff', 0.75))
    ctx.set_line_width(Pen.L(4))
    ctx.stroke()


def pipe(ctx, pl, flow, col, t, w=46, speed=300):
    pl.stroke(ctx, PAL['ink'], w + 8, cap=cairo.LINE_CAP_BUTT)
    pl.stroke(ctx, PAL['pipe'], w + 2)
    pl.stroke(ctx, PAL['pipe_in'], w - 14)
    if flow > 0:
        ctx.push_group()
        pl.stroke(ctx, col, w - 22)
        if pl.path(ctx):
            setc(ctx, C('#ffffff', 0.7))
            ctx.set_line_width(6)
            ctx.set_dash([24, 30], -t * speed)
            ctx.stroke()
            ctx.set_dash([])
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(flow)


def bacterium(ctx, x, y, r, col, chomp, t, ph):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(0.15 * math.sin(t * 3 + ph))
    # pelitos/cilios
    for k in range(10):
        a = k * 2 * math.pi / 10 + t * 0.6
        ctx.move_to(math.cos(a) * r, math.sin(a) * r)
        ctx.line_to(math.cos(a + 0.15 * math.sin(t * 8 + k)) * r * 1.3, math.sin(a + 0.15 * math.sin(t * 8 + k)) * r * 1.3)
    setc(ctx, PAL['ink'])
    ctx.set_line_width(Pen.L(2.5))
    ctx.stroke()
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source(rgrad(-r * .35, -r * .35, r * .1, r * 1.2, [(0, mix(col, PAL['white'], .45)), (1, mix(col, C('#2f6e2a'), .3))]))
    ctx.fill_preserve()
    fs(ctx, None, 3)
    # ojos
    for ex in (-0.32, 0.32):
        ctx.arc(ex * r, -0.2 * r, 0.2 * r, 0, 2 * math.pi)
        fs(ctx, PAL['white'], 2)
        ctx.arc(ex * r + 0.05 * r, -0.17 * r, 0.1 * r, 0, 2 * math.pi)
        setc(ctx, PAL['ink'])
        ctx.fill()
    # boca: sonrisa o mordida
    if chomp > 0.05:
        ctx.save()
        ctx.translate(0, 0.28 * r)
        ctx.scale(1, 0.25 + 0.75 * chomp)
        ctx.arc(0, 0, 0.3 * r, 0, 2 * math.pi)
        ctx.restore()
        fs(ctx, C('#6b2a2a'), 2)
    else:
        ctx.arc(0, 0.12 * r, 0.32 * r, 0.2 * math.pi, 0.8 * math.pi)
        setc(ctx, PAL['ink'])
        ctx.set_line_width(Pen.L(3))
        ctx.stroke()
    # mejillas
    for ex in (-0.55, 0.55):
        ctx.arc(ex * r, 0.18 * r, 0.12 * r, 0, 2 * math.pi)
        setc(ctx, C('#f39a9a', 0.6))
        ctx.fill()
    ctx.restore()


def grey_blob(ctx, x, y, r, a=1.0):
    if r <= 0.5 or a <= 0:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(1, 0.85)
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source(rgrad(x - r * .3, y - r * .3, 1, r * 1.2, [(0, C('#a9adb1', a)), (1, C('#7a8087', a))]))
    ctx.fill_preserve()
    setc(ctx, PAL['ink'], a)
    ctx.set_line_width(Pen.L(2.5))
    ctx.stroke()


IN_PIPE = PL((-600, 1120), ((300, 1120),))
P12 = PL((784, 1110), ((870, 1110),), ((900, 1110), (915, 1120), (930, 1140)))
P23 = PL((1700, 1150), ((1880, 1150),))
P_OUT = PL((2560, 1060), ((2700, 1060),))


def draw(ctx, t):
    # cielo y fondo
    ctx.rectangle(-3000, -3000, 9000, 4100)
    ctx.set_source(lgrad(0, -800, 0, 1000, [(0, PAL['sky1']), (1, PAL['sky2'])]))
    ctx.fill()
    for i, (x, y, s) in enumerate([(-300, 300, 120), (700, 120, 150), (1700, 260, 130), (2600, 80, 160), (3400, 320, 120)]):
        cloud(ctx, x + 40 * math.sin(t * 0.25 + i), y, s)
    # colinas lejanas
    ctx.move_to(-3000, 1000)
    for x in range(-3000, 6001, 200):
        ctx.line_to(x, 860 - 60 * math.sin(x * 0.0021) - 30 * math.sin(x * 0.006))
    ctx.line_to(6000, 1000)
    ctx.close_path()
    fs(ctx, C('#bfe08a'), 3)
    for i, x in enumerate((2200, 2050, 820, 120, -200, 1780)):
        tree(ctx, x, GROUND - 6, 52, seed=i * 5 + 2)
    # suelo en corte
    ctx.rectangle(-3000, GROUND, 9000, 2400)
    ctx.set_source(lgrad(0, GROUND, 0, 2200, [(0, PAL['soil']), (1, PAL['soil3'])]))
    ctx.fill()
    ctx.rectangle(-3000, GROUND - 14, 9000, 40)
    fs(ctx, PAL['grass'], 3)
    r = random.Random(9)
    for _ in range(140):
        x = r.uniform(-1500, 4200)
        y = r.uniform(1060, 2000)
        ctx.arc(x, y, r.uniform(4, 12), 0, 2 * math.pi)
        setc(ctx, PAL['soil2'])
        ctx.fill()

    # ------------------ 1) rejilla
    x0, x1, yb = 300, 760, 1380
    concrete_tank(ctx, x0, x1, GROUND, yb)
    ctx.rectangle(x0, GROUND - 30, x1 - x0, yb - GROUND + 30)
    setc(ctx, C('#e4e9ec'))
    ctx.fill()
    water_block(ctx, x0, x1, 1060, yb, PAL['used'], PAL['used2'], t)
    pipe(ctx, IN_PIPE, 1.0, PAL['used'], t)
    # barras de la rejilla
    for k in range(7):
        bx = 520 + k * 22
        ctx.move_to(bx - 60, 960)
        ctx.line_to(bx + 40, yb - 10)
    setc(ctx, PAL['ink'])
    ctx.set_line_width(12 + Pen.L(3) * 2)
    ctx.stroke()
    for k in range(7):
        bx = 520 + k * 22
        ctx.move_to(bx - 60, 960)
        ctx.line_to(bx + 40, yb - 10)
    setc(ctx, C('#9aa7b1'))
    ctx.set_line_width(12)
    ctx.stroke()
    # sólidos atrapados
    sep = prog(t, 54.4, 55.9)
    for i, (u, v, rr) in enumerate(SOLIDS):
        arrive = 54.3 + i * 0.12
        k = prog(t, arrive, arrive + 0.6)
        sx = lerp(300, 440 + v * 60 + (1 - u) * 20, k)
        sy = lerp(1120, 1080 + u * 260, k) + 4 * math.sin(t * 3 + i)
        grey_blob(ctx, sx, sy, rr, min(1, k * 4 + 0.0) if t > arrive else 0)
    if sep > 0:
        pl = PL((340, 1250), ((700, 1250),))
        ph = (t * 0.9) % 1
        arrow(ctx, pl, pl.len * ph * 0.4, pl.len * (0.45 + ph * 0.55), w=16, a=window(t, 54.6, 57.0, .3, .5), col=PAL['white'])
    pipe(ctx, P12, 1.0, PAL['used'], t)

    # ------------------ 2) tanque de bacterias (aireación)
    x0, x1, yb = 930, 1680, 1440
    round_tank_back(ctx, x0, x1, GROUND - 40, yb)
    clean2 = prog(t, 57.4, 59.0) * 0.45
    water_block(ctx, x0, x1, 1050, yb, mix(PAL['used'], PAL['water'], clean2), mix(PAL['used2'], PAL['water2'], clean2), t)
    for (bx, u, rr) in BUBBLES:
        ph = (u + t * 0.35) % 1
        by = lerp(yb - 20, 1060, ph)
        ctx.arc(bx + 8 * math.sin(t * 2 + u * 9), by, rr, 0, 2 * math.pi)
        setc(ctx, C('#ffffff', 0.75 * (1 - ph * 0.6)))
        ctx.set_line_width(Pen.L(2))
        ctx.stroke()
    # bacterias se comen la suciedad
    bpos = []
    for j, b in enumerate(BACT):
        x = b['x'] + 40 * math.sin(t * 0.7 + b['ph'])
        y = b['y'] + 30 * math.cos(t * 0.9 + b['ph'])
        # moverse hacia la próxima partícula
        targets = [d for d in DIRT if d['b'] == j]
        chomp = 0
        for d in targets:
            k = prog(t, d['eat'] - 0.55, d['eat'])
            if 0 < k < 1:
                x = lerp(x, d['x'] - 26, k)
                y = lerp(y, d['y'], k)
            chomp = max(chomp, pulse(t, d['eat'] - 0.15, d['eat'] + 0.2))
        grow = 1 + 0.08 * sum(1 for d in targets if t > d['eat'])
        bpos.append((x, y, 30 * grow, b['col'], chomp, b['ph']))
    for d in DIRT:
        k = prog(t, d['eat'] - 0.05, d['eat'] + 0.2)
        grey_blob(ctx, d['x'] + 3 * math.sin(t * 2 + d['x']), d['y'], d['r'] * (1 - k))
        if 0 < k < 1:
            burst(ctx, d['x'], d['y'], 30, pulse(k, 0, 1), n=6, col=PAL['white'], lw=3)
    bact_in = prog(t, 55.4, 56.1)
    for (x, y, rr, col, ch, ph) in bpos:
        bacterium(ctx, x, y, rr * back(bact_in), col, ch, t, ph) if bact_in > 0 else None
    round_tank_front(ctx, x0, x1, GROUND - 40, yb)
    pipe(ctx, P23, 1.0, mix(PAL['used'], PAL['water'], clean2), t)

    # ------------------ 3) clarificador: el agua se vuelve limpia
    x0, x1, yb = 1880, 2500, 1400
    round_tank_back(ctx, x0, x1, GROUND - 40, yb)
    cl = prog(t, 58.2, 59.6)
    water_block(ctx, x0, x1, 1040, yb, mix(mix(PAL['used'], PAL['water'], 0.3), PAL['water'], cl), mix(PAL['used2'], PAL['water2'], cl), t)
    for k in range(12):
        sx = 1920 + (k * 53) % 560
        sy = 1080 + (k * 97) % 300
        sparkle(ctx, sx, sy, 16 * (0.5 + 0.5 * math.sin(t * 4 + k)), cl)
    # lodo que se asienta abajo (sin detalle desagradable)
    ctx.save()
    ctx.translate((x0 + x1) / 2, yb - 4)
    ctx.scale(1, 0.12)
    ctx.arc(0, 0, (x1 - x0) / 2 - 10, math.pi, 2 * math.pi)
    ctx.restore()
    setc(ctx, C('#9ca3a8', 0.9))
    ctx.fill()
    round_tank_front(ctx, x0, x1, GROUND - 40, yb)
    if cl > 0:
        burst(ctx, 2190, 1220, 160, pulse(t, 59.0, 59.9), n=12, col=PAL['white'], lw=6)

    # ------------------ 4) salida al río
    pipe(ctx, P_OUT, 1.0, mix(PAL['used'], PAL['water'], cl), t)
    # río en corte
    rx0, rx1 = 2760, 3500
    ctx.move_to(2700, GROUND)
    ctx.curve_to(2760, GROUND, 2780, 1180, 2900, 1200)
    ctx.line_to(3360, 1200)
    ctx.curve_to(3480, 1180, 3500, GROUND, 3560, GROUND)
    ctx.close_path()
    ctx.set_source(lgrad(0, GROUND, 0, 1200, [(0, C('#8fd6f5')), (1, C('#3f9fd8'))]))
    ctx.fill_preserve()
    fs(ctx, None, 3.5)
    for k in range(6):
        xx = 2800 + k * 110 + 30 * math.sin(t * 2 + k)
        ctx.move_to(xx, GROUND + 30 + (k % 2) * 40)
        ctx.curve_to(xx + 20, GROUND + 20 + (k % 2) * 40, xx + 40, GROUND + 40 + (k % 2) * 40, xx + 60, GROUND + 30 + (k % 2) * 40)
        setc(ctx, C('#ffffff', 0.8))
        ctx.set_line_width(Pen.L(4))
        ctx.stroke()
    # chorro de agua limpia
    pour = prog(t, 59.6, 60.2)
    if pour > 0:
        ctx.move_to(2700, 1060)
        ctx.curve_to(2760, 1060, 2790, 1060, 2800, 1060 + 0 * pour)
        ctx.curve_to(2810, 1040, 2830, 1010 + (1 - pour) * 40, 2840, 1010)
        ctx.new_path()
        ctx.move_to(2700, 1050)
        ctx.curve_to(2770, 1040, 2810, 1060, 2830, 1020 + 40 * (1 - pour))
        ctx.line_to(2845, 1030 + 40 * (1 - pour))
        ctx.curve_to(2820, 1080, 2770, 1075, 2700, 1072)
        ctx.close_path()
        setc(ctx, PAL['water'], pour)
        ctx.fill()
        for k in range(5):
            sparkle(ctx, 2830 + k * 18, 1010 + 10 * math.sin(t * 9 + k), 14, pour)
    # pececito feliz
    fj = pulse(t, 60.2, 61.2)
    if fj > 0:
        fx = 3150
        fy = 1010 - 120 * fj
        ctx.save()
        ctx.translate(fx, fy)
        ctx.rotate(-0.6 + 1.2 * prog(t, 60.2, 61.2, lin))
        ctx.save()
        ctx.scale(1, 0.6)
        ctx.arc(0, 0, 34, 0, 2 * math.pi)
        ctx.restore()
        fs(ctx, C('#f5b35b'), 3)
        poly(ctx, [(-30, 0), (-58, -18), (-58, 18)])
        fs(ctx, C('#f5b35b'), 3)
        ctx.arc(14, -5, 5, 0, 2 * math.pi)
        setc(ctx, PAL['ink'])
        ctx.fill()
        ctx.restore()
    for i, x in enumerate((2620, 2680, 3600, 3690, 3800)):
        tree(ctx, x, GROUND + 4, 70, seed=i * 3 + 1)
