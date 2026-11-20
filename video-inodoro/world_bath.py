"""Mundo B: corte de la casa con el baño y el inodoro en vista de corte (cutaway)."""
import math
import random
import cairo
from common import *

FLOOR = 1500
YF, YE = 790.0, 1060.0          # nivel lleno / vacío del tanque
BOWL_N = 1290.0                  # nivel normal de la taza (sello)
BOWL_LOW = 1348.0

TRAP = PL((596, 1342),
          ((594, 1392), (562, 1426), (522, 1424)),
          ((482, 1422), (464, 1384), (462, 1334)),
          ((461, 1288), (442, 1262), (418, 1262)),
          ((396, 1262), (392, 1286), (392, 1322)),
          ((392, 1500),))
# arclength del punto más alto del sifón (cresta)
CREST_S = min(range(int(TRAP.len)), key=lambda s: TRAP.at(s)[1] if 150 < s < 330 else 1e9)
DRAIN = PL((392, 1480), ((392, 1700),), ((392, 1764), (436, 1780), (500, 1781)), ((3200, 1860),))
PASSAGE = PL((270, 1066), ((270, 1104),), ((270, 1124), (282, 1134), (310, 1136)), ((470, 1136),))
SUPPLY = PL((30, 2400), ((30, 1400),), ((150, 1400),), ((150, 805),))
VALVE = (150, 787)
PIVOT_F = (176, 782)
ARM_L = 196
LEVER_P = (424, 760)
FLAP_H = (240, 1060)

rnd = random.Random(7)
SPARK = [(rnd.uniform(130, 400), rnd.uniform(0, 1), rnd.uniform(0, 6.28)) for _ in range(9)]
TILE_VAR = {}


# ====================================================================== estado temporal
def state(t):
    s = {}
    # cutaway (abrir 4.4-5.5, cerrar 70.6-71.9)
    s['cut'] = prog(t, 4.4, 5.6) * (1 - prog(t, 70.6, 71.9))
    # palanca
    s['lever'] = prog(t, 12.55, 12.95) * (1 - prog(t, 13.9, 14.3))
    s['hand_in'] = prog(t, 11.7, 12.5) * (1 - prog(t, 14.0, 14.8))
    # tapón
    flap = prog(t, 13.1, 13.6, eio)
    flap *= 1 - prog(t, 32.7, 33.1, eio)
    s['flap'] = flap
    # nivel del tanque
    drain_fast = prog(t, 13.7, 18.0, lambda u: 1 - (1 - clamp(u)) ** 2) * 0.58
    drain_slow = prog(t, 18.0, 32.8, ss) * 0.42
    fill = prog(t, 35.6, 42.5, ss)
    emptiness = clamp(drain_fast + drain_slow) * (1 - fill)
    s['tank'] = lerp(YF, YE, emptiness)
    s['tank_moving'] = max(window(t, 13.7, 33.0, .4, .4), window(t, 35.6, 42.5, .3, .3))
    s['inflow'] = window(t, 35.2, 42.75, 0.5, 0.15)
    s['valve_open_fx'] = pulse(t, 34.45, 35.2)
    s['valve_close_fx'] = pulse(t, 42.55, 43.25)
    s['level_mark'] = window(t, 40.9, 45.0, 0.4, 0.5)
    s['level_ok'] = prog(t, 41.7, 42.1)
    s['check'] = back(prog(t, 43.75, 44.15, lin)) * (1 - prog(t, 44.9, 45.3))
    # cascada al interior de la taza
    s['cascade'] = window(t, 13.75, 26.5, 0.5, 1.2)
    s['cascade_arrows'] = window(t, 14.6, 19.0, 0.4, 0.6)
    # taza
    rise = prog(t, 14.0, 17.4) * 70
    siph = prog(t, 25.0, 27.6, eio)
    refill = prog(t, 38.0, 43.5)
    lvl = BOWL_N - rise
    lvl = lerp(lvl, BOWL_LOW, siph)
    lvl = lerp(lvl, BOWL_N, refill)
    if t > 50:
        lvl = BOWL_N
    s['bowl'] = lvl
    s['bowl_used'] = prog(t, 13.8, 16.5) * (1 - prog(t, 38.0, 43.0)) if t < 50 else 0.0
    # sifón
    s['trap_front'] = prog(t, 18.7, 25.0, lambda u: clamp(u) ** 1.2) * TRAP.len
    s['siphon_full'] = window(t, 24.9, 27.7, 0.1, 0.25)
    s['trap_glow'] = window(t, 20.3, 29.6, 0.5, 0.8)
    s['swirl'] = window(t, 25.3, 28.2, 0.3, 0.6)
    s['suction'] = window(t, 25.5, 28.0, 0.3, 0.5)
    s['drain_flow'] = max(window(t, 25.3, 30.5, 0.4, 1.0), window(t, 45.0, 49.5, 0.6, 0.6))
    s['sound'] = window(t, 28.0, 29.9, 0.15, 0.4)
    s['gurgle'] = window(t, 27.4, 29.8, 0.2, 0.5)
    # sello y olores
    s['seal_glow'] = window(t, 63.6, 70.4, 0.6, 0.6)
    s['odor_t'] = t - 67.4
    s['shield'] = back(prog(t, 68.3, 68.7, lin)) * (1 - prog(t, 70.2, 70.6))
    # resaltes en escena 2
    s['hl_float'] = pulse(t, 9.1, 10.3)
    s['hl_valve'] = pulse(t, 9.7, 10.9)
    s['hl_flap'] = pulse(t, 10.3, 11.6)
    s['hl_tank'] = pulse(t, 6.6, 7.9)
    s['t'] = t
    return s


# ====================================================================== fondo (corte de la casa)
def draw_background(ctx, t):
    # cielo
    ctx.rectangle(-4000, -4500, 9000, 6100)
    ctx.set_source(lgrad(0, -2600, 0, 1500, [(0, PAL['sky1']), (1, PAL['sky2'])]))
    ctx.fill()
    for i, (x, y, s) in enumerate([(-900, -1500, 160), (2500, -1700, 190), (-600, 200, 120), (2600, 300, 140), (300, -2100, 150), (1600, -2300, 130)]):
        cloud(ctx, x + 30 * math.sin(t * 0.2 + i), y, s)
    # pasto exterior
    ctx.rectangle(-4000, 1470, 9000, 80)
    fs(ctx, PAL['grass'], 3)
    for gx in range(-3000, 5000, 70):
        if -80 < gx < 1880:
            continue
        ctx.move_to(gx, 1472)
        ctx.line_to(gx + 12, 1446)
        ctx.line_to(gx + 22, 1472)
    setc(ctx, PAL['grass2'])
    ctx.fill()
    # subsuelo
    ctx.rectangle(-4000, 1540, 9000, 2400)
    ctx.set_source(lgrad(0, 1540, 0, 2700, [(0, PAL['soil']), (1, PAL['soil3'])]))
    ctx.fill()
    r = random.Random(3)
    for _ in range(170):
        x = r.uniform(-1800, 3600)
        y = r.uniform(1620, 2600)
        rr = r.uniform(6, 16)
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(1, 0.7)
        ctx.arc(0, 0, rr, 0, 2 * math.pi)
        ctx.restore()
        setc(ctx, PAL['soil2'])
        ctx.fill_preserve()
        setc(ctx, C('#9a7b55', 0.6))
        ctx.set_line_width(Pen.L(1.6))
        ctx.stroke()

    # ---- casa en corte
    # pared del fondo: pintura arriba, azulejos abajo
    ctx.rectangle(90, -360, 1610, 1860)
    ctx.set_source(lgrad(0, -360, 0, 480, [(0, C('#efe0c8')), (1, C('#f6e9d4'))]))
    ctx.fill()
    tile = 100
    for j, y in enumerate(range(480, 1500, tile)):
        for i, x in enumerate(range(90, 1700, tile)):
            v = ((i * 7 + j * 13) % 5) / 5.0
            ctx.rectangle(x, y, tile, tile)
            setc(ctx, mix(PAL['tile'], PAL['tile2'], v * 0.8))
            ctx.fill()
    setc(ctx, PAL['grout'])
    ctx.set_line_width(Pen.L(2.2))
    for y in range(480, 1501, tile):
        ctx.move_to(90, y)
        ctx.line_to(1700, y)
    for x in range(90, 1701, tile):
        ctx.move_to(x, 480)
        ctx.line_to(x, 1500)
    ctx.stroke()
    # brillo suave sobre azulejos
    ctx.rectangle(90, 480, 1610, 1020)
    ctx.set_source(lgrad(90, 480, 1700, 1500, [(0, C('#ffffff', 0.18)), (0.5, C('#ffffff', 0.0)), (1, C('#5c8fa3', 0.12))]))
    ctx.fill()
    # moldura
    ctx.rectangle(90, 462, 1610, 26)
    fs(ctx, C('#9fd0df'), 2.5)
    # ventana
    rrect(ctx, 1170, 40, 1490, 360, 14)
    fs(ctx, PAL['white'], 3.5)
    ctx.rectangle(1192, 62, 276, 276)
    ctx.set_source(lgrad(0, 62, 0, 338, [(0, PAL['sky1']), (1, PAL['sky2'])]))
    ctx.fill_preserve()
    fs(ctx, None, 3)
    ctx.save()
    ctx.rectangle(1192, 62, 276, 276)
    ctx.clip()
    cloud(ctx, 1290 + 20 * math.sin(t * 0.4), 170, 55)
    ctx.restore()
    ctx.move_to(1330, 62)
    ctx.line_to(1330, 338)
    ctx.move_to(1192, 200)
    ctx.line_to(1468, 200)
    setc(ctx, PAL['white'])
    ctx.set_line_width(12)
    ctx.stroke()
    # toallero y toalla
    rrect(ctx, 1000, 640, 1290, 656, 8)
    fs(ctx, PAL['chrome'], 2.5)
    ctx.move_to(1030, 648)
    ctx.line_to(1260, 648)
    ctx.line_to(1250, 940)
    ctx.curve_to(1180, 960, 1110, 930, 1040, 950)
    ctx.close_path()
    fs(ctx, C('#f4b6a6'), 3)
    for yy in (880, 905):
        ctx.move_to(1044, yy)
        ctx.line_to(1252, yy - 6)
    setc(ctx, C('#ffffff', 0.7))
    ctx.set_line_width(8)
    ctx.stroke()
    # planta en maceta
    ctx.move_to(1460, 1500)
    ctx.line_to(1440, 1380)
    ctx.line_to(1600, 1380)
    ctx.line_to(1580, 1500)
    ctx.close_path()
    fs(ctx, C('#e7a77f'), 3)
    for ang, ln in ((-1.9, 170), (-1.4, 210), (-1.1, 160), (-2.3, 140), (-0.8, 120)):
        ctx.save()
        ctx.translate(1520, 1385)
        ctx.rotate(ang + math.pi / 2 + 0.05 * math.sin(t + ang))
        ctx.move_to(0, 0)
        ctx.curve_to(-38, -ln * .4, -20, -ln * .85, 0, -ln)
        ctx.curve_to(20, -ln * .85, 38, -ln * .4, 0, 0)
        ctx.restore()
        fs(ctx, C('#86c062'), 2.5)
    # lámpara
    ctx.move_to(900, -350)
    ctx.line_to(900, -260)
    setc(ctx, PAL['ink'])
    ctx.set_line_width(Pen.L(3))
    ctx.stroke()
    ctx.move_to(840, -200)
    ctx.curve_to(840, -270, 960, -270, 960, -200)
    ctx.close_path()
    fs(ctx, C('#fbe6a2'), 3)
    ctx.arc(900, -190, 120, 0, 2 * math.pi)
    ctx.set_source(rgrad(900, -190, 10, 220, [(0, C('#fff6c8', 0.45)), (1, C('#fff6c8', 0))]))
    ctx.fill()

    # paredes en corte
    for x0, x1 in ((-70, 90), (1700, 1860)):
        ctx.rectangle(x0, -430, x1 - x0, 1970)
        fs(ctx, PAL['wall_pink'], 3.5)
        setc(ctx, PAL['wall_pink2'])
        rr = random.Random(x0)
        for _ in range(60):
            ctx.arc(rr.uniform(x0 + 8, x1 - 8), rr.uniform(-420, 1530), rr.uniform(2, 5), 0, 2 * math.pi)
            ctx.fill()
    # techo / losa
    ctx.rectangle(-110, -440, 2010, 80)
    fs(ctx, PAL['concrete'], 3.5)
    # tejado
    ctx.move_to(-260, -430)
    ctx.line_to(900, -1180)
    ctx.line_to(2060, -430)
    ctx.close_path()
    fs(ctx, C('#ead8bd'), 3.5)
    ctx.move_to(-300, -405)
    ctx.line_to(900, -1215)
    ctx.line_to(2100, -405)
    ctx.line_to(2060, -360)
    ctx.line_to(900, -1110)
    ctx.line_to(-260, -360)
    ctx.close_path()
    ctx.set_source(lgrad(0, -1200, 0, -360, [(0, PAL['roof']), (1, PAL['roof2'])]))
    ctx.fill_preserve()
    fs(ctx, None, 3.5)
    # vigas
    for x in (420, 900, 1380):
        ctx.move_to(x, -440)
        ctx.line_to(900 + (x - 900) * 0.1, -1100 + abs(x - 900) * 0.0)
    setc(ctx, C('#c9ab84'))
    ctx.set_line_width(26)
    ctx.stroke()
    # piso: borde superior en perspectiva + losa
    ctx.move_to(90, 1500)
    ctx.line_to(1700, 1500)
    ctx.line_to(1700, 1540)
    ctx.line_to(90, 1540)
    ctx.close_path()
    fs(ctx, C('#dbe8ec'), 3)
    for x in range(90, 1700, 100):
        ctx.move_to(x, 1500)
        ctx.line_to(x + 18, 1540)
    setc(ctx, PAL['grout'])
    ctx.set_line_width(Pen.L(2))
    ctx.stroke()
    ctx.rectangle(-70, 1540, 1930, 70)
    fs(ctx, PAL['concrete'], 3.5)
    # cimientos laterales
    for x0 in (-70, 1700):
        ctx.rectangle(x0, 1610, 160, 260)
        fs(ctx, PAL['concrete2'], 3.5)


# ====================================================================== piezas del inodoro
def bowl_body(ctx):
    ctx.move_to(330, 1095)
    ctx.line_to(880, 1095)
    ctx.curve_to(902, 1180, 862, 1300, 742, 1350)
    ctx.curve_to(702, 1370, 690, 1400, 702, 1440)
    ctx.line_to(734, 1500)
    ctx.line_to(348, 1500)
    ctx.line_to(366, 1440)
    ctx.curve_to(372, 1392, 352, 1362, 330, 1334)
    ctx.curve_to(304, 1300, 300, 1160, 330, 1095)
    ctx.close_path()


def bowl_cavity(ctx):
    ctx.move_to(470, 1112)
    ctx.curve_to(480, 1240, 540, 1322, 600, 1346)
    ctx.curve_to(700, 1346, 846, 1262, 862, 1112)
    ctx.close_path()


def tank_body(ctx):
    rrect(ctx, 100, 690, 430, 1095, 26)


def tank_cavity(ctx):
    rrect(ctx, 122, 712, 408, 1072, 16)


def lid(ctx):
    rrect(ctx, 86, 660, 444, 702, 14)


def seat(ctx):
    rrect(ctx, 446, 1076, 900, 1098, 11)


def seat_lid(ctx):
    rrect(ctx, 434, 800, 458, 1080, 11)


def handle_pts(ang):
    px, py = LEVER_P
    outer = (px + 52 * math.cos(ang), py + 52 * math.sin(ang))
    inner = (px - 142 * math.cos(ang), py - 142 * math.sin(ang))
    return outer, inner


def draw_handle(ctx, ang):
    outer, _ = handle_pts(ang)
    ctx.arc(LEVER_P[0] + 8, LEVER_P[1], 13, 0, 2 * math.pi)
    fs(ctx, PAL['chrome'], 3)
    ctx.move_to(LEVER_P[0] + 8, LEVER_P[1])
    ctx.line_to(*outer)
    setc(ctx, PAL['ink'])
    ctx.set_line_width(16 + Pen.L(3) * 2)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.move_to(LEVER_P[0] + 8, LEVER_P[1])
    ctx.line_to(*outer)
    setc(ctx, PAL['chrome'])
    ctx.set_line_width(16)
    ctx.stroke()


def float_pos(level):
    # la boya flota sobre el agua; si el agua baja demasiado, cuelga del brazo
    yb = level - 6
    sa = clamp((yb - PIVOT_F[1]) / ARM_L, -0.25, 0.86)
    a = math.asin(sa)
    return (PIVOT_F[0] + ARM_L * math.cos(a), PIVOT_F[1] + ARM_L * math.sin(a)), a


def water_fill(ctx, level, top_col, bot_col, x0, x1, y1):
    ctx.rectangle(x0, level, x1 - x0, y1 - level)
    ctx.set_source(lgrad(0, level, 0, y1, [(0, top_col), (1, bot_col)]))
    ctx.fill()


def water_surface(ctx, x0, x1, level, t, amp, col):
    ctx.move_to(x0, level)
    n = 24
    for i in range(n + 1):
        x = lerp(x0, x1, i / n)
        ctx.line_to(x, level + amp * math.sin(x * 0.045 + t * 7))
    setc(ctx, col)
    ctx.set_line_width(Pen.L(4))
    ctx.stroke()


def hand(ctx, x, y, a):
    """Mano de caricatura con el índice apuntando hacia abajo; la yema en (x, y)."""
    if a <= 0:
        return
    ctx.push_group()
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(-0.25)
    # manga
    rrect(ctx, -20, -250, 92, -150, 20)
    fs(ctx, PAL['sleeve'], 3.5)
    ctx.move_to(-14, -170)
    ctx.line_to(86, -170)
    setc(ctx, C('#ffffff', 0.5))
    ctx.set_line_width(6)
    ctx.stroke()
    # palma
    rrect(ctx, -26, -160, 86, -62, 34)
    ctx.set_source(lgrad(-26, -160, 86, -62, [(0, PAL['skin']), (1, PAL['skin2'])]))
    ctx.fill_preserve()
    fs(ctx, None, 3.5)
    # nudillos
    for kx in (14, 40, 66):
        ctx.arc(kx, -64, 15, 0, math.pi)
        fs(ctx, PAL['skin'], 3)
    # índice
    rrect(ctx, -16, -100, 14, 4, 15)
    ctx.set_source(lgrad(-16, 0, 14, 0, [(0, PAL['skin']), (1, PAL['skin2'])]))
    ctx.fill_preserve()
    fs(ctx, None, 3.5)
    rrect(ctx, -8, -16, 6, -4, 5)
    setc(ctx, C('#ffffff', 0.55))
    ctx.fill()
    # pulgar
    ctx.move_to(-24, -120)
    ctx.curve_to(-62, -110, -60, -76, -30, -76)
    fs(ctx, PAL['skin'], 3.5)
    ctx.restore()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)


# ====================================================================== dibujo principal del mundo B
def draw(ctx, t):
    s = state(t)
    draw_background(ctx, t)
    cut = s['cut']
    lever_ang = 0.32 * s['lever']

    # sombra en el piso
    ctx.save()
    ctx.translate(560, 1502)
    ctx.scale(1, 0.12)
    ctx.arc(0, 0, 330, 0, 2 * math.pi)
    ctx.restore()
    setc(ctx, C('#000000', 0.13))
    ctx.fill()

    # ---- tubería de desagüe bajo el piso (siempre visible en el corte del subsuelo)
    DRAIN.stroke(ctx, PAL['ink'], 84)
    DRAIN.stroke(ctx, PAL['pipe'], 78)
    DRAIN.stroke(ctx, PAL['pipe_in'], 56)
    df = s['drain_flow']
    if df > 0:
        ctx.save()
        ctx.push_group()
        DRAIN.stroke(ctx, PAL['used'], 44)
        if DRAIN.path(ctx):
            setc(ctx, C('#c4d4df'))
            ctx.set_line_width(10)
            ctx.set_dash([60, 90], -t * 700)
            ctx.stroke()
            ctx.set_dash([])
        for k in range(14):
            sp = (k * 260 + t * 650) % DRAIN.len
            px, py = DRAIN.at(sp)
            ctx.arc(px, py - 6 + 8 * math.sin(k * 3.1), 6 + (k % 3) * 2, 0, 2 * math.pi)
            setc(ctx, C('#e6f2f8', 0.9))
            ctx.fill()
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(df)
        ctx.restore()
    # brillo del tubo
    DRAIN.stroke(ctx, C('#ffffff', 0.5), 4, 30, DRAIN.len)
    # brida
    rrect(ctx, 352, 1488, 432, 1512, 6)
    fs(ctx, PAL['chrome'], 3)

    # ---- suministro de agua desde la tubería de la casa
    SUPPLY.stroke(ctx, PAL['ink'], 24)
    SUPPLY.stroke(ctx, PAL['chrome'], 19)
    if s['inflow'] > 0:
        ctx.save()
        ctx.push_group()
        SUPPLY.stroke(ctx, PAL['water'], 12)
        if SUPPLY.path(ctx):
            setc(ctx, PAL['water_hi'])
            ctx.set_line_width(5)
            ctx.set_dash([26, 34], -t * 520)
            ctx.stroke()
            ctx.set_dash([])
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(s['inflow'])
        ctx.restore()
    else:
        SUPPLY.stroke(ctx, C('#ffffff', 0.55), 4, 0, SUPPLY.len)
    # llave de paso
    ctx.save()
    ctx.translate(96, 1400)
    rrect(ctx, -10, -18, 22, 18, 7)
    fs(ctx, PAL['chrome2'], 3)
    ctx.save()
    ctx.scale(1, 1.6)
    ctx.arc(6, -20, 11, 0, 2 * math.pi)
    ctx.restore()
    fs(ctx, C('#f1f4f6'), 3)
    ctx.restore()

    # ---- inodoro: volumen trasero (profundidad 3D)
    ctx.save()
    ctx.translate(30, -20)
    bowl_body(ctx)
    fs(ctx, PAL['porc_sh2'], 3)
    tank_body(ctx)
    fs(ctx, PAL['porc_sh2'], 3)
    lid(ctx)
    fs(ctx, PAL['porc_sh2'], 3)
    ctx.restore()

    # ------------------------------------------------ INTERIOR (vista en corte)
    if cut > 0:
        ctx.save()
        # región revelada: por encima de la línea de corte que barre de arriba a abajo
        sweep = lerp(640, 1520, cut)
        if cut < 1:
            ctx.rectangle(-200, 0, 1400, sweep)
            ctx.clip()
        draw_interior(ctx, s, lever_ang)
        ctx.restore()

    # ------------------------------------------------ EXTERIOR (se retira con el corte)
    if cut < 1:
        ctx.save()
        sweep = lerp(640, 1520, cut)
        ctx.rectangle(-200, sweep, 1400, 2000)
        ctx.clip()
        draw_exterior(ctx, s, lever_ang)
        ctx.restore()
    if 0 < cut < 1:
        sweep = lerp(640, 1520, cut)
        ctx.move_to(40, sweep)
        ctx.line_to(960, sweep)
        setc(ctx, C('#ffffff', 0.9))
        ctx.set_line_width(Pen.L(7))
        ctx.stroke()
        ctx.move_to(40, sweep)
        ctx.line_to(960, sweep)
        setc(ctx, PAL['red'])
        ctx.set_line_width(Pen.L(3))
        ctx.set_dash([Pen.L(14), Pen.L(10)])
        ctx.stroke()
        ctx.set_dash([])
        for k in range(5):
            sparkle(ctx, 120 + k * 200 + 30 * math.sin(t * 9 + k), sweep - 4, 22, 0.95)

    # tapa levantada y asiento (siempre exteriores, por delante)
    seat_lid(ctx)
    ctx.set_source(lgrad(434, 0, 458, 0, [(0, PAL['porcelain']), (1, PAL['porc_sh'])]))
    ctx.fill_preserve()
    fs(ctx, None, 3)
    seat(ctx)
    ctx.set_source(lgrad(0, 1076, 0, 1098, [(0, PAL['porcelain']), (1, PAL['porc_sh'])]))
    ctx.fill_preserve()
    fs(ctx, None, 3)
    # palanca (exterior)
    draw_handle(ctx, lever_ang)

    # mano
    if s['hand_in'] > 0:
        outer, _ = handle_pts(lever_ang)
        hi = s['hand_in']
        hx = lerp(outer[0] + 260, outer[0] + 8, ss(hi))
        hy = lerp(outer[1] - 380, outer[1] - 9, ss(hi))
        hand(ctx, hx, hy, min(1, hi * 3))
        if s['lever'] > 0.05:
            burst(ctx, outer[0] + 4, outer[1] + 4, 46, pulse(t, 12.6, 13.3), n=8, lw=3.5)

    # ondas de sonido de cómic
    so = s['sound']
    if so > 0:
        for side in (-1, 1):
            for k in range(3):
                ph = ((t * 1.8 + k / 3) % 1)
                r = 120 + ph * 260
                ctx.arc(640, 1150, r, -math.pi / 2 + side * 0.55 - 0.32, -math.pi / 2 + side * 0.55 + 0.32)
                setc(ctx, PAL['ink'], so * (1 - ph))
                ctx.set_line_width(Pen.L(7))
                ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.stroke()
        burst(ctx, 660, 1050, 150 + 20 * math.sin(t * 20), so * 0.8, n=12, lw=5)

    # check verde
    if s['check'] > 0:
        check_badge(ctx, 482, 610, 46, s['check'])


def draw_exterior(ctx, s, lever_ang):
    bowl_body(ctx)
    ctx.set_source(lgrad(300, 1095, 900, 1500, [(0, PAL['porcelain']), (0.55, C('#eef2f4')), (1, PAL['porc_sh'])]))
    ctx.fill_preserve()
    fs(ctx, None, 3.5)
    # sombreado suave del vientre
    ctx.save()
    bowl_body(ctx)
    ctx.clip()
    ctx.arc(780, 1260, 140, 0, 2 * math.pi)
    ctx.set_source(rgrad(800, 1300, 20, 200, [(0, C('#b8c6d0', 0.0)), (1, C('#b8c6d0', 0.35))]))
    ctx.fill()
    ctx.move_to(360, 1130)
    ctx.curve_to(360, 1230, 420, 1300, 520, 1320)
    setc(ctx, C('#ffffff', 0.8))
    ctx.set_line_width(10)
    ctx.stroke()
    ctx.restore()
    tank_body(ctx)
    ctx.set_source(lgrad(100, 690, 430, 1095, [(0, PAL['porcelain']), (1, PAL['porc_sh'])]))
    ctx.fill_preserve()
    fs(ctx, None, 3.5)
    rrect(ctx, 128, 720, 150, 1060, 10)
    setc(ctx, C('#ffffff', 0.85))
    ctx.fill()
    lid(ctx)
    ctx.set_source(lgrad(0, 660, 0, 702, [(0, PAL['porcelain']), (1, PAL['porc_sh'])]))
    ctx.fill_preserve()
    fs(ctx, None, 3.5)


def draw_interior(ctx, s, lever_ang):
    t = s['t']
    # superficie de corte de la cerámica
    bowl_body(ctx)
    fs(ctx, PAL['porcelain'], 3.5)
    tank_body(ctx)
    fs(ctx, PAL['porcelain'], 3.5)
    lid(ctx)
    fs(ctx, PAL['porcelain'], 3.5)
    # tramado suave del corte
    ctx.save()
    bowl_body(ctx)
    tank_body(ctx)
    ctx.clip()
    setc(ctx, C('#cdd7de', 0.55))
    ctx.set_line_width(Pen.L(1.5))
    for k in range(-40, 80):
        ctx.move_to(k * 28, 640)
        ctx.line_to(k * 28 - 900, 1540)
    ctx.stroke()
    ctx.restore()

    # cavidad del tanque
    tank_cavity(ctx)
    ctx.set_source(lgrad(0, 712, 0, 1072, [(0, PAL['inner']), (1, PAL['inner2'])]))
    ctx.fill_preserve()
    fs(ctx, None, 3)
    # pasaje del tanque al borde de la taza
    PASSAGE.stroke(ctx, PAL['ink'], 34)
    PASSAGE.stroke(ctx, PAL['inner'], 27)

    # glow rojo suave del sifón
    if s['trap_glow'] > 0:
        g = s['trap_glow'] * (0.75 + 0.25 * math.sin(t * 6))
        TRAP.stroke(ctx, C('#ec7b78', 0.45 * g), 104, 0, TRAP.len - 40)
        TRAP.stroke(ctx, C('#e2504a', 0.55 * g), 76, 0, TRAP.len - 40)

    # sifón (contorno), cavidad de la taza, luego interior del sifón
    TRAP.stroke(ctx, PAL['ink'], 58)
    bowl_cavity(ctx)
    ctx.set_source(lgrad(0, 1112, 0, 1346, [(0, PAL['inner']), (1, PAL['inner2'])]))
    ctx.fill()
    ctx.save()
    ctx.rectangle(-100, 0, 1200, 2000)
    ctx.arc_negative(598, 1342, 30, 2 * math.pi, 0)
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.clip()
    bowl_cavity(ctx)
    fs(ctx, None, 3)
    ctx.restore()
    TRAP.stroke(ctx, PAL['inner2'], 50)
    # canal del borde (rim)
    for rx in (478, 852):
        ctx.arc(rx, 1124, 13, 0, 2 * math.pi)
        fs(ctx, PAL['inner'], 2.5)

    # ---------------- agua de la taza y del sifón
    lvl = s['bowl']
    used = s['bowl_used']
    wc_top = mix(PAL['water'], PAL['used'], used)
    wc_bot = mix(PAL['water2'], PAL['used2'], used)
    seal_clean = t > 50
    if seal_clean:
        wc_top, wc_bot = PAL['water'], PAL['water2']
    ctx.save()
    bowl_cavity(ctx)
    ctx.clip()
    water_fill(ctx, lvl, wc_top, wc_bot, 440, 880, 1360)
    water_surface(ctx, 440, 880, lvl, t, 3 + 5 * s['swirl'] + 3 * s['cascade'], C('#e9f7ff', 0.9))
    ctx.restore()
    # agua estática en el sifón (lado de la taza hasta la cresta)
    crest_y = 1262 + 25
    trap_lvl = max(lvl, crest_y)
    if t > 27.6 and t < 43.5:
        trap_lvl = max(lvl, lerp(1386, crest_y, prog(t, 38.0, 43.5)))
    ctx.save()
    ctx.rectangle(-100, trap_lvl, 1200, 800)
    ctx.clip()
    TRAP.stroke(ctx, wc_bot, 50, 0, CREST_S + 8)
    ctx.restore()
    # frente de agua avanzando por el sifón
    front = s['trap_front']
    if 0 < front < TRAP.len and s['siphon_full'] < 0.99 and t < 26:
        TRAP.stroke(ctx, wc_bot, 50, 0, front)
        TRAP.stroke(ctx, C('#ffffff', 0.5), 8, max(0, front - 120), front)
    sf = s['siphon_full']
    if sf > 0:
        ctx.save()
        ctx.push_group()
        TRAP.stroke(ctx, wc_bot, 50)
        if TRAP.path(ctx):
            setc(ctx, C('#d6e4ec'))
            ctx.set_line_width(8)
            ctx.set_dash([40, 50], -t * 600)
            ctx.stroke()
            ctx.set_dash([])
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(sf)
        ctx.restore()
    # flujo por el pasaje y cascada desde el borde
    ca = s['cascade']
    if ca > 0:
        ctx.save()
        ctx.push_group()
        PASSAGE.stroke(ctx, PAL['water'], 20)
        if PASSAGE.path(ctx):
            setc(ctx, PAL['water_hi'])
            ctx.set_line_width(5)
            ctx.set_dash([22, 26], -t * 500)
            ctx.stroke()
            ctx.set_dash([])
        ctx.save()
        bowl_cavity(ctx)
        ctx.clip()
        for k, x in enumerate((486, 540, 610, 690, 770, 842)):
            ctx.move_to(x, 1124)
            for yy in range(1124, int(lvl) + 6, 12):
                ctx.line_to(x + (x - 660) * -0.12 * (yy - 1124) / 200 + 4 * math.sin(yy * 0.08 + t * 20 + k), yy)
            setc(ctx, PAL['water'])
            ctx.set_line_width(12)
            ctx.stroke()
        for k in range(10):
            x = 500 + k * 36
            ph = (t * 3 + k * 0.37) % 1
            ctx.arc(x, lvl - 4 - 16 * math.sin(ph * math.pi), 6 * (1 - ph) + 2, 0, 2 * math.pi)
            setc(ctx, PAL['water_hi'])
            ctx.fill()
        ctx.restore()
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(ca)
        ctx.restore()
    if s['cascade_arrows'] > 0:
        a = s['cascade_arrows']
        ph = (t * 1.2) % 1
        for x in (560, 760):
            pl = PL((x, 1150), ((x + (660 - x) * 0.2, 1240),))
            arrow(ctx, pl, 0, pl.len * (0.4 + 0.6 * ph), w=12, a=a * (1 - ph * 0.6), col=PAL['water_hi'])
        pl = PL((300, 1100), ((330, 1135), (380, 1140), (440, 1140)))
        arrow(ctx, pl, 0, pl.len, w=10, a=a, col=PAL['water_hi'])
    # remolino y succión
    sw = s['swirl']
    if sw > 0:
        for k in range(3):
            ctx.save()
            ctx.translate(660, lerp(1240, 1320, prog(t, 25.3, 27.6)) + k * 8)
            ctx.scale(1, 0.28)
            a0 = t * 9 + k * 2.1
            ctx.arc(0, 0, 150 - k * 40, a0, a0 + 3.6)
            ctx.restore()
            setc(ctx, PAL['white'], sw)
            ctx.set_line_width(Pen.L(6))
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()
    su = s['suction']
    if su > 0:
        for k in range(4):
            ph = ((t * 1.6) + k / 4) % 1
            s0 = ph * (TRAP.len - 80)
            arrow(ctx, TRAP, s0, s0 + 70, w=10, a=su * math.sin(ph * math.pi), col=PAL['white'])
        for k in range(5):
            ph = ((t * 2.2) + k / 5) % 1
            x = 600 + (k - 2) * 70
            ctx.move_to(x * (1 - ph) + 596 * ph, 1170 + ph * 150)
            ctx.line_to(x * (1 - ph * 0.6) + 596 * ph * 0.6, 1210 + ph * 150)
            setc(ctx, PAL['ink'], su * 0.6 * math.sin(ph * math.pi))
            ctx.set_line_width(Pen.L(4))
            ctx.stroke()
    if s['gurgle'] > 0:
        for k in range(9):
            ph = (t * 1.5 + k * 0.29) % 1
            px, py = TRAP.at(TRAP.len * ((k * 0.13 + ph * 0.3) % 1))
            ctx.arc(px + 6 * math.sin(k), py - ph * 30, 5 + 5 * (k % 3), 0, 2 * math.pi)
            setc(ctx, PAL['white'], s['gurgle'] * (1 - ph))
            ctx.set_line_width(Pen.L(2.5))
            ctx.stroke()

    # brillo del sello de agua (escena 9)
    sg = s['seal_glow']
    if sg > 0:
        g = 0.5 + 0.5 * math.sin(t * 5)
        ctx.save()
        ctx.rectangle(-100, trap_lvl - 30, 1200, 800)
        ctx.clip()
        TRAP.stroke(ctx, C('#fff3a0', 0.8 * sg * g), 72, 0, CREST_S)
        ctx.restore()
        ctx.save()
        ctx.rectangle(-100, trap_lvl, 1200, 800)
        ctx.clip()
        TRAP.stroke(ctx, PAL['water2'], 50, 0, CREST_S + 8)
        TRAP.stroke(ctx, C('#ffffff', 0.3 * g * sg), 50, 0, CREST_S + 8)
        ctx.restore()
        for k in range(6):
            sp = (k + 0.5) / 6 * CREST_S
            px, py = TRAP.at(sp)
            if py > trap_lvl + 4:
                sparkle(ctx, px + 8 * math.sin(k * 2), py, 14 * (0.6 + 0.4 * math.sin(t * 6 + k)), sg)

    # olores que suben desde el desagüe y no pueden pasar
    ot = s['odor_t']
    if -0.5 < ot < 3.6:
        for k in range(4):
            lt = ot - k * 0.35
            if lt < 0:
                continue
            # ruta: desde el desagüe sube por el lado de salida hasta la cresta, rebota
            up = clamp(lt / 1.2)
            bounce = clamp((lt - 1.2) / 1.2)
            y = lerp(1720, 1335 + k * 6, ss(up)) + 70 * ss(bounce)
            x = 392 + 14 * math.sin(lt * 5 + k) + (k - 1.5) * 6
            if lt < 0.4:
                x = lerp(560 + k * 60, x, ss(lt / 0.4))
                y = lerp(1775, y, ss(lt / 0.4))
            a = clamp(lt * 3) * (1 - clamp((lt - 2.1) / 0.6))
            odor_cloud(ctx, x, y, 22, a, lt)
            if 1.1 < lt < 1.5:
                burst(ctx, 400, 1312, 34, pulse(lt, 1.1, 1.5), n=7, col=PAL['red'], lw=4)
        if 1.0 < ot:
            x_mark(ctx, 396, 1305, 16, back(prog(ot, 1.1, 1.4, lin)) * (1 - prog(ot, 3.0, 3.4)))
    if s['shield'] > 0:
        shield(ctx, 462, 1236, 30, s['shield'])

    # ---------------- agua del tanque
    lv = s['tank']
    ctx.save()
    tank_cavity(ctx)
    ctx.clip()
    water_fill(ctx, lv, PAL['water'], PAL['water2'], 110, 420, 1075)
    mv = s['tank_moving']
    water_surface(ctx, 110, 420, lv, t, 1.5 + 4 * mv, C('#e9f7ff', 0.95))
    for (x, u, ph) in SPARK:
        y = lerp(lv + 20, 1060, u)
        if y > lv + 10:
            sparkle(ctx, x, y, 11 * (0.5 + 0.5 * math.sin(t * 3 + ph)), 0.85)
    # chorro de llenado
    if s['inflow'] > 0:
        ctx.move_to(132, 800)
        for yy in range(800, int(lv) + 6, 10):
            ctx.line_to(128 + 3 * math.sin(yy * 0.1 + t * 25), yy)
        setc(ctx, PAL['water'], s['inflow'])
        ctx.set_line_width(14)
        ctx.stroke()
        for k in range(6):
            ph = (t * 2.5 + k / 6) % 1
            ctx.arc(128 + (k - 3) * 9, lv - 2 - 18 * math.sin(ph * math.pi), 5 * (1 - ph) + 2, 0, 2 * math.pi)
            setc(ctx, PAL['water_hi'], s['inflow'])
            ctx.fill()
    ctx.restore()

    # marca del nivel correcto
    lm = s['level_mark']
    if lm > 0:
        col = mix(PAL['red'], PAL['green'], s['level_ok'])
        ctx.move_to(126, YF)
        ctx.line_to(404, YF)
        setc(ctx, col, lm)
        ctx.set_line_width(Pen.L(4))
        ctx.set_dash([Pen.L(12), Pen.L(9)])
        ctx.stroke()
        ctx.set_dash([])
        for x, d in ((126, 1), (404, -1)):
            poly(ctx, [(x, YF - 12), (x, YF + 12), (x + d * 18, YF)])
            setc(ctx, col, lm)
            ctx.fill()

    # ---------------- mecanismos
    # tubo de rebose
    rrect(ctx, 214, 768, 236, 1066, 6)
    fs(ctx, C('#ece7da'), 3)
    # válvula de llenado
    ctx.rectangle(140, 800, 20, 268)
    fs(ctx, C('#b7c6d0'), 3)
    rrect(ctx, 124, 768, 180, 806, 9)
    fs(ctx, C('#8fa4b3'), 3)
    if s['valve_open_fx'] > 0:
        sparkle(ctx, VALVE[0] - 6, VALVE[1] - 30, 40 * s['valve_open_fx'], s['valve_open_fx'])
        burst(ctx, VALVE[0], VALVE[1], 70, s['valve_open_fx'] * 0.9, n=10, col=PAL['white'], lw=5)
    if s['valve_close_fx'] > 0:
        vc = s['valve_close_fx']
        ctx.arc(VALVE[0], VALVE[1], 30 + 50 * (1 - vc), 0, 2 * math.pi)
        setc(ctx, PAL['white'], vc)
        ctx.set_line_width(Pen.L(6))
        ctx.stroke()
        burst(ctx, VALVE[0], VALVE[1], 64, vc, n=8, lw=4.5)
    # brazo y boya
    (bx, by), _ = float_pos(lv)
    ctx.move_to(*PIVOT_F)
    ctx.line_to(bx, by)
    setc(ctx, PAL['ink'])
    ctx.set_line_width(9 + Pen.L(3) * 2)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.move_to(*PIVOT_F)
    ctx.line_to(bx, by)
    setc(ctx, C('#a9b9c4'))
    ctx.set_line_width(9)
    ctx.stroke()
    ctx.arc(*PIVOT_F, 8, 0, 2 * math.pi)
    fs(ctx, C('#6f8594'), 2.5)
    ctx.arc(bx, by, 34, 0, 2 * math.pi)
    ctx.set_source(rgrad(bx - 12, by - 12, 3, 40, [(0, C('#ffd29a')), (1, C('#e48a3c'))]))
    ctx.fill_preserve()
    fs(ctx, None, 3.2)
    ctx.arc(bx - 11, by - 12, 8, 0, 2 * math.pi)
    setc(ctx, C('#ffffff', 0.7))
    ctx.fill()
    # asiento de descarga + tapón de goma
    rrect(ctx, 236, 1056, 306, 1072, 5)
    fs(ctx, C('#9fb0bc'), 3)
    phi = s['flap'] * 1.15
    ctx.save()
    ctx.translate(*FLAP_H)
    ctx.rotate(-phi)
    ctx.save()
    ctx.scale(1, 0.45)
    ctx.arc(34, -10, 36, math.pi, 2 * math.pi)
    ctx.restore()
    ctx.line_to(70, 2)
    ctx.line_to(-2, 2)
    ctx.close_path()
    ctx.set_source(lgrad(0, -26, 0, 4, [(0, C('#e27a6e')), (1, PAL['rubber'])]))
    ctx.fill_preserve()
    fs(ctx, None, 3)
    ctx.arc(64, -10, 6, 0, 2 * math.pi)
    fs(ctx, C('#9b3f38'), 2)
    ear = ctx.user_to_device(64, -10)
    ctx.restore()
    ear = ctx.device_to_user(*ear)
    ctx.arc(FLAP_H[0], FLAP_H[1], 6, 0, 2 * math.pi)
    fs(ctx, C('#9b3f38'), 2)
    # brazo interior de la palanca + cadenita
    _, inner = handle_pts(lever_ang)
    ctx.move_to(LEVER_P[0], LEVER_P[1])
    ctx.line_to(*inner)
    setc(ctx, PAL['ink'])
    ctx.set_line_width(10 + Pen.L(3) * 2)
    ctx.stroke()
    ctx.move_to(LEVER_P[0], LEVER_P[1])
    ctx.line_to(*inner)
    setc(ctx, PAL['chrome2'])
    ctx.set_line_width(10)
    ctx.stroke()
    d = math.dist(inner, ear)
    chain_len = 300
    sag = max(0, chain_len - d) * 0.6
    mx, my = (inner[0] + ear[0]) / 2 + sag * 0.5, (inner[1] + ear[1]) / 2
    n = 22
    for i in range(n + 1):
        u = i / n
        x = (1 - u) ** 2 * inner[0] + 2 * (1 - u) * u * mx + u * u * ear[0]
        y = (1 - u) ** 2 * inner[1] + 2 * (1 - u) * u * my + u * u * ear[1]
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(0.7 if i % 2 else 1, 1 if i % 2 else 0.7)
        ctx.arc(0, 0, 6, 0, 2 * math.pi)
        ctx.restore()
        setc(ctx, C('#7d8f9c'))
        ctx.set_line_width(Pen.L(3))
        ctx.stroke()
    # resaltes de escena 2
    for key, (x, y, r) in (('hl_float', (bx, by, 50)), ('hl_valve', (VALVE[0], VALVE[1] + 40, 58)), ('hl_flap', (272, 1052, 52))):
        a = s[key]
        if a > 0:
            ctx.arc(x, y, r + 8 * math.sin(t * 8), 0, 2 * math.pi)
            setc(ctx, C('#fff3a0', 0.95 * a))
            ctx.set_line_width(Pen.L(7))
            ctx.stroke()
            sparkle(ctx, x + r * 0.8, y - r * 0.8, 20, a)
    if s['hl_tank'] > 0:
        a = s['hl_tank']
        for k in range(5):
            sparkle(ctx, 150 + k * 60, YF + 40 + 50 * ((k * 7) % 3), 26 * a, a)
