import math, json, os
import numpy as np, skia
from lib import *
from globe import Globe

# ======================= timing (from real audio) =======================
T2, T3, T4, T5, T5b, T6, T6b, T7, T7b, T8, T9, T9b, T10, T10b, T11, TEND = \
    4.30, 8.15, 16.65, 23.45, 27.0, 31.35, 34.45, 35.85, 39.6, 42.55, 47.0, 52.35, 57.5, 61.75, 65.9, 71.7

# ======================= subtitles =======================
FIX = {'Ali': 'Alí', 'Hamenei.': 'Jamenei.', 'Hormuz,': 'Ormuz,', 'Bahrain,': 'Bahréin,', 'resultado?': 'resultado?',
       '2500': '2,500', 'El': 'El'}

def load_words():
    W_ = json.load(open(os.path.join(BASE, 'work/words.json')))
    out = []
    i = 0
    while i < len(W_):
        w = dict(W_[i])
        s = w['w']
        if s == 'Bab' and i + 2 < len(W_) and W_[i + 1]['w'] == 'el':
            out.append({'w': 'Bab', 's': w['s'], 'e': w['e']})
            out.append({'w': 'el-Mandeb.', 's': W_[i + 1]['s'], 'e': W_[i + 2]['e']})
            i += 3; continue
        if s == 'El' and i + 1 < len(W_) and W_[i + 1]['w'].startswith('resultado'):
            s = '¿El'
        s = FIX.get(s, s)
        w['w'] = s
        out.append(w)
        i += 1
    return out

WORDS = load_words()
SUB_SIZE = 64

def build_chunks():
    chunks, cur = [], []
    for k, w in enumerate(WORDS):
        cur.append(k)
        disp = ' '.join(clean(WORDS[j]['w']) for j in cur)
        nxt = WORDS[k + 1] if k + 1 < len(WORDS) else None
        brk = (len(cur) >= 3 or w['w'][-1] in '.,?' or nxt is None or nxt['s'] - w['e'] > 0.35)
        if nxt is not None and not brk:
            disp2 = disp + ' ' + clean(nxt['w'])
            if tw(disp2, 'mont', SUB_SIZE) > 900:
                brk = True
        if brk:
            chunks.append(cur); cur = []
    res = []
    for i, ch in enumerate(chunks):
        s = WORDS[ch[0]]['s'] - 0.05
        e_last = WORDS[ch[-1]]['e']
        nxt_s = WORDS[chunks[i + 1][0]]['s'] - 0.05 if i + 1 < len(chunks) else e_last + 1.0
        e = min(nxt_s, e_last + 0.7)
        res.append((s, e, ch))
    return res

def clean(s):
    return s.strip(',.').upper()

CHUNKS = build_chunks()

def subtitles(c, t):
    for (s, e, ch) in CHUNKS:
        if s <= t < e:
            break
    else:
        return
    words = [clean(WORDS[k]['w']) for k in ch]
    gap = 30
    widths = [tw(w, 'mont', SUB_SIZE) for w in words]
    total = sum(widths) + gap * (len(words) - 1)
    pin = eback(prog(t, s, s + 0.16))
    a = prog(t, s, s + 0.08) * (1 - prog(t, e - 0.06, e))
    y = 300
    c.save()
    c.translate(W / 2, y); sc = lerp(0.85, 1, pin); c.scale(sc, sc); c.translate(-W / 2, -y)
    x = W / 2 - total / 2
    for j, k in enumerate(ch):
        w = WORDS[k]
        nxt_s = WORDS[k + 1]['s'] if k + 1 < len(WORDS) else 1e9
        active = w['s'] <= t < max(nxt_s, w['e'])
        spoken = t >= w['s']
        cxw = x + widths[j] / 2
        if active:
            pp = eback(prog(t, w['s'], w['s'] + 0.14))
            c.save(); c.translate(cxw, y); ss = lerp(0.8, 1.08, pp); c.scale(ss, ss)
            rrect(c, -widths[j] / 2 - 12, -SUB_SIZE * 0.62, widths[j] + 24, SUB_SIZE * 1.24, 12, RED, a * 0.35, blur=14)
            rrect(c, -widths[j] / 2 - 12, -SUB_SIZE * 0.62, widths[j] + 24, SUB_SIZE * 1.24, 12, RED, a)
            text(c, words[j], 0, 0, 'mont', SUB_SIZE, WHITE, a)
            c.restore()
        else:
            text(c, words[j], cxw, y, 'mont', SUB_SIZE, WHITE, a * (1.0 if spoken else 0.78), shadow=1.2, stroke=7, stroke_color='#020814')
            text(c, words[j], cxw, y, 'mont', SUB_SIZE, WHITE, a * (1.0 if spoken else 0.78))
        x += widths[j] + gap
    c.restore()

def handle(c, t):
    a = 0.85 * prog(t, 0.3, 1.0) * (1 - prog(t, TEND - 0.3, TEND))
    if a <= 0:
        return
    x, y = 58, 1722
    circle(c, x, y - 2, 13, WHITE, a, stroke=4)
    c.drawLine(x + 9, y + 7, x + 19, y + 17, P(rgba(RED, a), stroke=6))
    text(c, '@capitalcuriosoo', x + 30, y, 'mont', 26, WHITE, a, align='left', shadow=1)

# ======================= helpers =======================
_maps = {}
def M(key, *args, **kw):
    if key not in _maps:
        _maps[key] = RegionMap(*args, **kw)
    return _maps[key]

def appear(c, t, t0, x, y, dur=0.35, s0=0.6):
    """push a transform for a pop-in; returns alpha"""
    p = prog(t, t0, t0 + dur)
    c.save(); c.translate(x, y); s = lerp(s0, 1, eback(p)); c.scale(s, s)
    return eo(p)

# ======================= scenes =======================
def s1(c, t):
    photo(c, 'img1_portaaviones', prog(t, 0, T2 + 0.3), 1.04, 1.22, (500, 380), (470, 350))
    # counter
    nums = [(0.22, '1'), (0.80, '2'), (1.38, '3')]
    settle = 2.0
    cur = None
    for k, (tt, s) in enumerate(nums):
        if t >= tt:
            cur = k
    if cur is not None:
        tt, s = nums[cur]
        p = prog(t, tt, tt + 0.22)
        sm = prog(t, settle, settle + 0.45)
        y = lerp(860, 720, eo(sm))
        size = lerp(470, 330, eo(sm))
        scl = lerp(1.7, 1.0, eo(p))
        c.save(); c.translate(W / 2, y); c.scale(scl, scl)
        a = eo(p)
        circle(c, 0, 0, 230, RED, 0.25 * a, blur=90)
        text(c, s, 0, 0, 'anton', size, RED, a, stroke=10, stroke_color=WHITE)
        text(c, s, 0, 0, 'anton', size, RED, a)
        c.restore()
        # previous number flying out
        if cur > 0 and t < tt + 0.25:
            q = prog(t, tt, tt + 0.25)
            c.save(); c.translate(W / 2, 860); c.scale(1 - 0.5 * q, 1 - 0.5 * q)
            text(c, nums[cur - 1][1], 0, 0, 'anton', 470, WHITE, 1 - q)
            c.restore()
        if cur == 2:
            pa = prog(t, settle + 0.1, settle + 0.5)
            if pa > 0:
                c.save(); c.translate(W / 2, 960); s_ = lerp(1.4, 1, eo(pa)); c.scale(s_, s_)
                text(c, 'PORTAAVIONES', 0, 0, 'anton', 128, WHITE, eo(pa), shadow=1.5)
                c.restore()
                bw = 640 * eo(prog(t, settle + 0.3, settle + 0.7))
                c.drawRect(skia.Rect.MakeXYWH(W / 2 - bw / 2, 1052, bw, 10), P(rgba(RED, eo(pa))))
                text(c, 'DE EE. UU. EN MEDIO ORIENTE', W / 2, 1105, 'mont', 36, SKY, prog(t, settle + 0.5, settle + 0.9), shadow=1, track=2)
    # mini map
    m = M('s1', 28, 66, 8, 36, (560, 1240, 470, 360))
    a = eo(prog(t, 0.3, 0.8))
    if a > 0:
        panel(c, 550, 1200, 490, 410, a, r=22, accent=None)
        text(c, 'MEDIO ORIENTE', 795, 1222, 'mont', 22, SKY, a, track=3)
        m.draw(c, a, hl={'Iran': (RED, 0.35 + 0.15 * math.sin(t * 5))}, rr=16)
        for k, (lon, lat, tt) in enumerate([(62.5, 17.5, 0.22), (58.8, 23.6, 0.80), (37.6, 21.0, 1.38)]):
            q = prog(t, tt, tt + 0.3)
            if q > 0:
                x, y = m.xy(lon, lat)
                pulse(c, x, y, t - tt, RED, 40, 1.0, 2, 1, 3)
                circle(c, x, y, 26, NAVY_D, 0.85 * eo(q))
                circle(c, x, y, 26, RED, eo(q), stroke=3)
                carrier(c, x, y + 4, 38 * eback(q), WHITE, eo(q))
                text(c, str(k + 1), x + 26, y - 26, 'anton', 26, WHITE, eo(q), shadow=1)

_globe = None
def s2(c, t):
    global _globe
    if _globe is None:
        _globe = Globe()
    navy_bg(c, t, grid=False)
    # stars
    rng = np.random.RandomState(7)
    for i in range(90):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        tw_ = 0.4 + 0.4 * math.sin(t * 3 + i)
        circle(c, x, y, rng.uniform(0.8, 2.2), WHITE, 0.5 * tw_)
    lt = t - T2
    r = eio(prog(lt, 0.0, 1.1))
    lon0 = lerp(52, -8, r) - 2 * lt
    lat0 = lerp(26, 24, r)
    cx, cy, R = 540, 960, 470
    scl = lerp(0.92, 1.0, eo(prog(lt, 0, 0.6)))
    R = R * scl
    dr_on = prog(t, 6.55, 6.9)
    hl = {'Iran': (RED, 0.55), 'Dominican Rep.': (RED, dr_on * (0.75 + 0.25 * math.sin(t * 8)))}
    B = _globe.draw(c, cx, cy, R, lon0, lat0, hl)
    me, do = (52.5, 28.0), (-70.3, 18.9)
    pts = _globe.arc_pts(me, do, cx, cy, R, B, 90, 0.2)
    pa = eio(prog(t, 5.15, 6.6))
    res = line(c, pts, RED, 7, 1.0, pa, glow=True)
    if res and pa < 1:
        (ex, ey), ang = res
        arrowhead(c, ex, ey, ang, 28, WHITE)
        circle(c, ex, ey, 22, RED, 0.6, blur=14)
    if pa >= 1:
        e, ang = pts[-1], math.atan2(pts[-1][1] - pts[-2][1], pts[-1][0] - pts[-2][0])
    # markers
    (mx, my), d1 = _globe.proj_pt(*me, cx, cy, R, B)
    if d1 > 0:
        marker(c, mx, my, 'MEDIO ORIENTE', t, 4.5, RED, 'up', 90, 28)
    (dx_, dy_), d2 = _globe.proj_pt(*do, cx, cy, R, B)
    if d2 > 0 and t > 6.5:
        flash(c, dx_, dy_, 6.55, t, 70)
        marker(c, dx_, dy_, 'REPÚBLICA DOMINICANA', t, 6.6, RED, 'dr', 80, 28)
    # question
    q = prog(t, 6.2, 6.6)
    if q > 0:
        c.save(); c.translate(W / 2, 1560); s = lerp(1.5, 1, eo(q)); c.scale(s, s)
        w1 = tw('¿Y A TI ', 'anton', 104); w2 = tw('QUÉ TE TOCA?', 'anton', 104)
        x0 = -(w1 + w2) / 2
        text(c, '¿Y A TI ', x0, 0, 'anton', 104, WHITE, eo(q), align='left', shadow=1.5)
        rrect(c, x0 + w1 - 8, -66, w2 + 20, 132, 10, RED, eo(q))
        text(c, 'QUÉ TE TOCA?', x0 + w1 + 2, 0, 'anton', 104, WHITE, eo(q), align='left')
        c.restore()

TL_Y = 500
TL_NODES = [(170, '28 FEB 2026', 'COMIENZA LA GUERRA', 8.35), (540, 'JUNIO', 'ACUERDO', 16.8), (910, 'JULIO', 'BLOQUEO NAVAL DE EE. UU.', 19.9)]

def timeline(c, t):
    a = prog(t, T3, T3 + 0.3)
    c.drawLine(70, TL_Y, 1010, TL_Y, P(rgba(SKY, 0.3 * a), stroke=4))
    # progress
    xend = 70
    if t >= 8.2:
        xend = lerp(70, 170, eo(prog(t, 8.2, 8.5)))
    if t >= 16.75:
        xend = lerp(170, 540, eo(prog(t, 16.75, 17.2)))
    if t >= 19.7:
        xend = lerp(540, 910, eo(prog(t, 19.7, 20.1)))
    c.drawLine(70, TL_Y, xend, TL_Y, P(rgba(RED, 0.5 * a), stroke=12, blur=8))
    c.drawLine(70, TL_Y, xend, TL_Y, P(rgba(RED, a), stroke=6))
    if 18.68 <= t:
        cr = prog(t, 18.68, 18.95)
        crack(c, 330, TL_Y - 30, 740, TL_Y + 30, cr, seed=11, alpha=a * (1 - prog(t, 19.7, 20.0)))
    for k, (x, date, desc, tt) in enumerate(TL_NODES):
        on = prog(t, tt, tt + 0.35)
        latest = (k == 2 and t >= tt) or (k < 2 and t >= tt and t < TL_NODES[k + 1][3])
        if on <= 0:
            circle(c, x, TL_Y, 13, NAVY_D, a)
            circle(c, x, TL_Y, 13, SKY, 0.5 * a, stroke=3)
            continue
        if latest:
            pulse(c, x, TL_Y, t - tt, RED, 50, 1.1, 2, a, 3)
        circle(c, x, TL_Y, 18 * eback(on), RED, a)
        circle(c, x, TL_Y, 7, WHITE, a)
        dim = 1.0 if latest else 0.55
        text(c, date, x, TL_Y - 55, 'anton', 50 if latest else 40, WHITE, a * eo(on) * dim, shadow=1)
        lines = wrap(desc, 'mont', 24, 290)
        for j, ln in enumerate(lines):
            text(c, ln, x, TL_Y + 50 + j * 32, 'mont', 24, RED if (latest and k != 1) else SKY, a * eo(prog(t, tt + 0.15, tt + 0.5)) * dim, shadow=1)

def s3(c, t):
    photo(c, 'img1b_portaaviones_atardecer', prog(t, T3, T4), 1.0, 1.1, (960, 1300), (1000, 1250), dark=0.5)
    timeline(c, t)
    # flags
    fy = 730
    for (kind, x, tt, name) in [('us', 190, 10.16, 'EE. UU.'), ('il', 380, 10.78, 'ISRAEL'), ('ir', 860, 12.3, 'IRÁN')]:
        p = prog(t, tt, tt + 0.35)
        if p > 0:
            c.save(); c.translate(x, fy); s = eback(p); c.scale(s, s)
            flag(c, kind, 0, 0, 160, eo(p))
            c.restore()
            text(c, name, x, fy + 78, 'mont', 24, WHITE, eo(p), shadow=1, track=2)
    pv = prog(t, 11.66, 12.0)
    if pv > 0:
        c.save(); c.translate(620, fy); s = lerp(2, 1, eo(pv)); c.scale(s, s)
        circle(c, 0, 0, 62, RED, 0.4 * eo(pv), blur=30)
        text(c, 'VS', 0, 0, 'anton', 92, RED, eo(pv), stroke=6, stroke_color=WHITE)
        text(c, 'VS', 0, 0, 'anton', 92, RED, eo(pv))
        c.restore()
        text(c, 'EN GUERRA', 620, fy + 78, 'mont', 22, RED, eo(pv), shadow=1, track=2)
    # Iran map
    m = M('iran3', 43.5, 63.8, 24.6, 39.9, (70, 880, 940, 520))
    a = eo(prog(t, 12.3, 12.8))
    if a > 0:
        panel(c, 70, 880, 940, 520, a, accent=None)
        m.draw(c, a, hl={'Iran': (RED, 0.45 + 0.1 * math.sin(t * 6))})
        ix, iy = m.xy(55.5, 31.5)
        text(c, 'IRÁN', ix, iy, 'anton', 72, WHITE, a * 0.9, shadow=1.5, track=6)
        c.save(); m.clip(c)
        for (lon, lat, tt) in [(51.39, 35.69, 13.5), (51.67, 32.65, 13.75), (46.29, 38.08, 13.95), (52.53, 29.59, 14.15), (56.27, 27.18, 14.4), (48.68, 31.32, 14.6), (59.6, 36.3, 14.8)]:
            x, y = m.xy(lon, lat)
            flash(c, x, y, tt, t, 55)
            if t > tt:
                circle(c, x, y, 7, RED, prog(t, tt, tt + 0.2))
                pulse(c, x, y, t - tt, RED, 30, 1.2, 1, 0.8, 2)
        c.restore()
        if t > 13.5:
            x, y = m.xy(51.39, 35.69)
            marker(c, x, y, 'TEHERÁN', t, 13.55, RED, 'ul', 70, 26)
    # card
    pc = prog(t, 13.95, 14.4)
    if pc > 0:
        y0 = lerp(1500, 1440, eo(pc))
        panel(c, 70, y0, 940, 196, eo(pc))
        label_box(c, 110, y0 + 4, 'PRIMER ATAQUE', eo(pc), 24, WHITE, RED, None, align='left')
        text(c, 'Muere el líder supremo', 105, y0 + 82, 'mont', 44, WHITE, eo(prog(t, 14.1, 14.5)), align='left')
        text(c, 'ALÍ JAMENEI', 105, y0 + 145, 'anton', 64, RED, eo(prog(t, 14.4, 14.9)), align='left', track=2)
    source(c, 'AP / Wikipedia', t, 14.0, T4 + 0.1)

def s4(c, t):
    photo(c, 'img4_barco_ormuz', prog(t, T4, T5), 1.0, 1.14, (470, 300), (500, 290), dark=0.45)
    timeline(c, t)
    # handshake card
    ha = prog(t, 16.85, 17.2) * (1 - prog(t, 19.75, 20.05))
    if ha > 0:
        sh = 0
        if 18.68 < t < 19.1:
            sh = 14 * math.sin(t * 90) * (1 - prog(t, 18.68, 19.1))
        drop = 140 * eio(prog(t, 19.75, 20.05))
        c.save(); c.translate(540 + sh, 880 + drop); s = eback(prog(t, 16.85, 17.2)); c.scale(s, s); c.rotate(8 * prog(t, 19.75, 20.05))
        panel(c, -250, -230, 500, 460, ha, accent=None)
        broke = prog(t, 18.68, 18.9)
        emoji(c, '🤝', 0, -40, 230, ha)
        if broke > 0:
            c.drawRect(skia.Rect.MakeXYWH(-250, -230, 500, 460), P(rgba(RED_D, 0.25 * broke * ha)))
            crack(c, -190, -200, 170, 130, prog(t, 18.68, 18.92), seed=5, alpha=ha, width=8)
            crack(c, 160, -190, -120, 160, prog(t, 18.78, 19.0), seed=9, alpha=ha, width=6)
        text(c, 'ACUERDO', 0, 150, 'anton', 74, WHITE, ha * (1 - 0.5 * broke), shadow=1)
        if broke > 0:
            c.save(); c.rotate(-10); sc = lerp(2.2, 1, eo(prog(t, 18.95, 19.2))); c.scale(sc, sc)
            q = eo(prog(t, 18.95, 19.2)) * ha
            rrect(c, -190, -55, 380, 110, 12, RED, q, stroke=8)
            text(c, 'NO DURÓ', 0, 0, 'anton', 82, RED, q)
            c.restore()
        c.restore()
    # blockade map
    ma = eo(prog(t, 19.95, 20.4))
    if ma > 0:
        m = M('block', 48.3, 62.6, 23.4, 31.2, (50, 700, 980, 680))
        panel(c, 50, 700, 980, 680, ma, accent=None)
        m.draw(c, ma, hl={'Iran': (RED, 0.25)})
        ix, iy = m.xy(55.8, 29.4)
        text(c, 'IRÁN', ix, iy, 'anton', 64, WHITE, ma * 0.9, shadow=1, track=6)
        route = [(49.6, 29.3), (50.6, 28.5), (51.6, 27.65), (53.0, 26.9), (54.5, 26.6), (55.6, 26.5), (56.3, 26.45), (56.9, 25.85), (57.4, 25.25), (58.6, 25.15), (60.2, 25.0), (61.9, 24.95)]
        pts = smooth([m.xy(*q) for q in route], 10)
        pb = eio(prog(t, 20.6, 22.1))
        res = line(c, pts, RED, 9, ma, pb, dash=[26, 14], glow=True)
        for k, (f, tt) in enumerate([(0.18, 21.0), (0.48, 21.4), (0.8, 21.8)]):
            q = prog(t, tt, tt + 0.3)
            if q > 0 and pb > f:
                (x, y), ang = point_at(pts, f)
                warship(c, x, y + 30, 64 * eback(q), WHITE, eo(q) * ma)
        for (lon, lat, nm, tt, sd) in [(50.84, 28.97, 'BUSHEHR', 21.6, 'ur'), (56.27, 27.18, 'BANDAR ABBAS', 22.0, 'up'), (60.64, 25.29, 'CHABAHAR', 22.4, 'ul')]:
            x, y = m.xy(lon, lat)
            if t > tt:
                xmark(c, x, y, 34, prog(t, tt, tt + 0.25), RED, 9, ma)
                marker(c, x, y - 4, nm, t, tt + 0.1, RED, sd, 70, 24)
        pt = prog(t, 22.2, 22.6)
        if pt > 0:
            c.save(); c.translate(540, 1470); s = lerp(1.4, 1, eo(pt)); c.scale(s, s)
            rrect(c, -400, -52, 800, 104, 12, RED, eo(pt))
            text(c, 'PUERTOS IRANÍES BLOQUEADOS', 0, 0, 'anton', 62, WHITE, eo(pt))
            c.restore()

# --- Ormuz overlays shared by img2 / img3 ---
def hormuz_overlay(c, t, tr, sc, strait, routes, labels, t0):
    sx, sy = tr(*strait)
    # radar rings
    for k in range(3):
        ph = ((t - t0) / 2.2 + k / 3) % 1
        circle(c, sx, sy, 60 + 420 * ph, '#7FE3FF', 0.5 * (1 - ph), stroke=3)
    # strait highlight
    a = eo(prog(t, t0 + 0.1, t0 + 0.6))
    pul = 0.75 + 0.25 * math.sin(t * 6)
    c.save(); c.translate(sx, sy); c.rotate(-30)
    c.drawOval(skia.Rect.MakeXYWH(-150, -80, 300, 160), P(rgba(RED, 0.45 * a * pul), blur=30))
    c.drawOval(skia.Rect.MakeXYWH(-130, -64, 260, 128), P(rgba(RED, 0.95 * a), stroke=6))
    c.restore()
    # routes
    for ri, rt in enumerate(routes):
        pts = smooth([tr(*q) for q in rt], 10)
        pr = eio(prog(t, t0 + 0.2 + 0.2 * ri, t0 + 1.6 + 0.2 * ri))
        line(c, pts, WHITE, 4, 0.75 * a, pr, dash=[18, 12])
        for k in range(3):
            f = ((t - t0) * 0.09 + k / 3 + ri * 0.15) % 1
            if f < pr:
                (x, y), ang = point_at(pts, f)
                circle(c, x, y, 20, '#7FE3FF', 0.35 * a, blur=10)
                ship_top(c, x, y, ang, 36, WHITE, a)
    for (pt, txt, tt, side, dist) in labels:
        x, y = tr(*pt)
        marker(c, x, y, txt, t, tt, RED, side, dist, 30)

R2 = [[(0, 455), (200, 440), (380, 400), (500, 345), (590, 330), (640, 390), (680, 520), (760, 660), (900, 800)],
      [(0, 395), (220, 380), (420, 330), (540, 300), (620, 300), (680, 360), (720, 480), (820, 640), (960, 760)]]
R3 = [[(80, 340), (280, 320), (460, 300), (600, 255), (665, 240), (700, 300), (730, 400), (790, 520), (900, 700)],
      [(80, 300), (300, 285), (470, 260), (590, 215), (660, 195), (730, 240), (770, 360), (830, 500), (950, 660)]]

def s5(c, t):
    tr, sc = photo(c, 'img2_mapa_ormuz', prog(t, T5, T5b + 0.3), 1.08, 1.2, (560, 345), (575, 330), dark=0.3, tint=0.25)
    hormuz_overlay(c, t, tr, sc, (565, 360), R2,
                   [((650, 170), 'IRÁN', 23.7, 'down', 60), ((490, 480), 'OMÁN', 24.0, 'down', 80), ((565, 360), 'ESTRECHO DE ORMUZ', 24.3, 'dl', 130)], T5)
    # attacks on ships
    for (pt, tt) in [((640, 395), 24.62), ((690, 530), 25.1)]:
        x, y = tr(*pt)
        flash(c, x, y, tt, t, 80)
        if t > tt:
            circle(c, x, y, 12, '#FF7A00', 0.8 * (0.6 + 0.4 * math.sin(t * 20)), blur=6)
    pie(c, t)

def s5b(c, t):
    tr, sc = photo(c, 'img3_ormuz_satelite', prog(t, T5b, T6), 1.12, 1.26, (640, 300), (655, 285), dark=0.25, tint=0.2)
    hormuz_overlay(c, t, tr, sc, (650, 235), R3,
                   [((770, 200), 'IRÁN', 27.3, 'up', 60), ((580, 410), 'OMÁN', 27.5, 'left', 90), ((650, 235), 'ESTRECHO DE ORMUZ', 27.15, 'ul', 120)], T5b - 0.4)
    pie(c, t)

def pie(c, t):
    a = eo(prog(t, 27.55, 27.95))
    if a <= 0:
        return
    y0 = lerp(1430, 1370, a)
    panel(c, 50, y0, 980, 280, a)
    p = eo(prog(t, 27.8, 28.9)) * 0.25
    cx, cy = 210, y0 + 140
    donut(c, cx, cy, 92, p, a, 36)
    text(c, f'{int(round(p * 100))}%', cx, cy, 'anton', 58, WHITE, a)
    q = prog(t, 28.3, 28.7)
    text(c, '1/4', 350, y0 + 90, 'anton', 120, RED, eo(q) * a, align='left', shadow=1)
    text(c, 'DEL PETRÓLEO', 545, y0 + 72, 'mont', 34, WHITE, eo(prog(t, 28.5, 28.9)) * a, align='left')
    text(c, 'MARÍTIMO', 545, y0 + 116, 'mont', 34, WHITE, eo(prog(t, 28.6, 29.0)) * a, align='left')
    text(c, 'DEL MUNDO', 350, y0 + 200, 'anton', 64, WHITE, eo(prog(t, 30.4, 30.8)) * a, align='left', track=3)
    # tanker icon
    tanker(c, 870, y0 + 195, 150, WHITE, eo(prog(t, 30.4, 30.8)) * a)

DR_START = [(51.2, 29.2), (51.7, 28.7), (52.3, 28.15), (52.9, 27.75), (50.95, 29.55), (53.5, 27.55)]
def gulf_overlay(c, t):
    m = M('gulf', 47.4, 58.6, 23.7, 30.9, (50, 560, 980, 720))
    a = eo(prog(t, 31.45, 31.9))
    if a <= 0:
        return
    panel(c, 50, 560, 980, 720, a, accent=None)
    m.draw(c, a, hl={'Bahrain': (RED, 0.7 + 0.3 * math.sin(t * 8)), 'Iran': ('#3B5FA8', 0.3)})
    ix, iy = m.xy(54.5, 29.6)
    text(c, 'IRÁN', ix, iy, 'anton', 64, WHITE, 0.9 * a, shadow=1, track=6)
    bx, by = m.xy(50.55, 26.05)
    c.save(); m.clip(c)
    radar(c, bx, by, 95, t, a * eo(prog(t, 31.7, 32.2)))
    for k, (lon, lat) in enumerate(DR_START):
        t0 = 32.8 + k * 0.16
        dur = 1.6
        pk = prog(t, t0, t0 + dur)
        if pk <= 0:
            continue
        sx, sy = m.xy(lon, lat)
        tx, ty = bx + (k - 2.5) * 10, by + 6
        stop = 0.86 if k % 2 == 0 else 0.93
        f = min(eio(pk) if pk < 1 else 1, stop)
        x, y = lerp(sx, tx, f), lerp(sy, ty, f)
        ang = math.atan2(ty - sy, tx - sx)
        hit = t0 + dur * (stop if stop < 1 else 1) * 0.9
        alive = t < hit
        line(c, [(sx, sy), (x, y)], RED, 3, 0.6 * a, 1, dash=[10, 8])
        if alive:
            circle(c, x, y, 18, RED, 0.4, blur=10)
            drone(c, x, y, ang, 44, WHITE, a)
        flash(c, x, y, hit, t, 46)
    c.restore()
    marker(c, bx, by, 'BAHRÉIN', t, 31.8, RED, 'dl', 120, 30, sub='RADAR DE EE. UU.')
    # lower third
    pl = prog(t, 32.9, 33.3)
    if pl > 0:
        y0 = lerp(1420, 1340, eo(pl))
        panel(c, 50, y0, 980, 210, eo(pl))
        label_box(c, 90, y0 + 4, '14 NOV', eo(pl), 30, WHITE, RED, None, align='left', name='anton')
        text(c, 'Drones iraníes contra un radar', 90, y0 + 92, 'mont', 42, WHITE, eo(prog(t, 33.05, 33.4)), align='left')
        text(c, 'de EE. UU. en Bahréin', 90, y0 + 150, 'mont', 42, WHITE, eo(prog(t, 33.15, 33.5)), align='left')
        drone(c, 930, y0 + 120, -0.5, 80, RED, eo(pl))
    source(c, 'ABC News / Fox News', t, 33.0, T7 + 0.1)

def s6(c, t):
    photo(c, 'img6_base_bahrein', prog(t, T6, T6b + 0.3), 1.0, 1.15, (500, 360), (540, 340))
    gulf_overlay(c, t)

def s6b(c, t):
    photo(c, 'img6b_explosion_bahrein', prog(t, T6b, T7), 1.05, 1.2, (300, 230), (290, 210), dark=0.35)
    gulf_overlay(c, t)

def s7(c, t):
    tr, sc = photo(c, 'img7_mapa_bab_el_mandeb', prog(t, T7, T7b + 0.3), 1.0, 1.14, (390, 410), (395, 425), dark=0.25, tint=0.3)
    sx, sy = tr(375, 435)
    for k in range(3):
        ph = ((t - T7) / 2.0 + k / 3) % 1
        circle(c, sx, sy, 60 + 380 * ph, '#7FE3FF', 0.45 * (1 - ph), stroke=3)
    a = eo(prog(t, 36.0, 36.5))
    pul = 0.75 + 0.25 * math.sin(t * 6)
    c.save(); c.translate(sx, sy); c.rotate(-55)
    c.drawOval(skia.Rect.MakeXYWH(-230, -110, 460, 220), P(rgba(RED, 0.5 * a * pul), blur=34))
    c.drawOval(skia.Rect.MakeXYWH(-200, -90, 400, 180), P(rgba(RED, a), stroke=7))
    c.restore()
    rt = smooth([tr(*q) for q in [(420, 0), (400, 150), (385, 300), (390, 430), (430, 500), (560, 520), (700, 560), (984, 600)]], 10)
    pr = eio(prog(t, 36.1, 37.4))
    line(c, rt, WHITE, 4, 0.8 * a, pr, dash=[18, 12])
    for k in range(2):
        f = ((t - T7) * 0.08 + k / 2) % 1
        if f < pr:
            (x, y), ang = point_at(rt, f)
            ship_top(c, x, y, ang, 40, WHITE, a)
    marker(c, sx, sy, 'BAB EL-MANDEB', t, 36.3, RED, 'ur', 120, 32, sub='MAR ROJO')
    pc = prog(t, 37.2, 37.6)
    if pc > 0:
        y0 = lerp(1460, 1380, eo(pc))
        panel(c, 50, y0, 980, 230, eo(pc))
        label_box(c, 90, y0 + 4, 'HUTÍES (ALIADOS DE IRÁN)', eo(pc), 28, WHITE, RED, None, align='left')
        text(c, 'TOMAN BAB EL-MANDEB', 90, y0 + 130, 'anton', 80, WHITE, eo(prog(t, 39.3, 39.7)) if t > 39.0 else eo(prog(t, 37.4, 37.8)), align='left', track=1)

def s7b(c, t):
    navy_bg(c, t)
    m = M('dual', 31.0, 62.0, 9.0, 31.5, (30, 470, 1020, 900))
    a = eo(prog(t, T7b, T7b + 0.4))
    panel(c, 30, 470, 1020, 900, a, accent=None)
    m.draw(c, a, hl={'Iran': ('#3B5FA8', 0.35), 'Yemen': ('#3B5FA8', 0.35)})
    red_route = [(32.6, 29.9), (33.8, 27.9), (36.0, 25.0), (38.6, 20.6), (41.0, 16.3), (42.6, 13.8), (43.4, 12.6), (45.5, 12.0), (50.5, 12.6), (56.5, 14.3), (61.5, 16.0)]
    gulf_route = [(48.9, 29.3), (50.6, 27.6), (52.8, 26.6), (55.0, 26.3), (56.4, 26.5), (57.2, 25.5), (58.6, 24.0), (60.0, 22.6), (61.5, 21.0)]
    for rt, tt in [(red_route, 39.75), (gulf_route, 39.65)]:
        pts = smooth([m.xy(*q) for q in rt], 10)
        pr = eio(prog(t, tt, tt + 0.9))
        blocked = t > 40.5
        line(c, pts, RED if blocked else WHITE, 6, a, pr, dash=[20, 12], glow=blocked)
        if pr > 0.05 and not blocked:
            (x, y), ang = point_at(pts, pr)
            ship_top(c, x, y, ang, 40, WHITE, a)
    for (lon, lat, tt, nm, side) in [(56.4, 26.5, 40.1, 'ORMUZ', 'up'), (43.4, 12.6, 40.5, 'BAB EL-MANDEB', 'dl')]:
        x, y = m.xy(lon, lat)
        if t > tt:
            flash(c, x, y, tt, t, 70)
            xmark(c, x, y, 70, prog(t, tt, tt + 0.25), RED, 16)
            marker(c, x, y, nm, t, tt + 0.15, RED, side, 90, 30)
    for (lon, lat, nm) in [(38.4, 21.4, 'MAR ROJO'), (51.6, 27.2, 'GOLFO PÉRSICO'), (64.0, 18.0, '')]:
        if nm:
            x, y = m.xy(lon, lat)
            text(c, nm, x, y, 'mont', 22, SKY, a * 0.9, shadow=1, track=3)
    pt = prog(t, 40.9, 41.3)
    if pt > 0:
        c.save(); c.translate(540, 1500); s = lerp(1.5, 1, eo(pt)); c.scale(s, s)
        w1 = tw('2 ', 'anton', 110); w2 = tw('RUTAS CLAVE', 'anton', 110)
        x0 = -(w1 + w2) / 2
        text(c, '2', x0, 0, 'anton', 110, RED, eo(pt), align='left', shadow=1)
        text(c, 'RUTAS CLAVE', x0 + w1, 0, 'anton', 110, WHITE, eo(pt), align='left', shadow=1)
        rrect(c, -260, 70, 520, 86, 10, RED, eo(pt))
        text(c, 'BLOQUEADAS', 0, 113, 'anton', 66, WHITE, eo(pt), track=6)
        c.restore()

def vy(v):
    return 1236 - (v - 1000) * 0.112

def s8(c, t):
    photo(c, 'img8_barco_contenedores', prog(t, T8, T9), 1.0, 1.15, (480, 400), (520, 380))
    a = eo(prog(t, 42.7, 43.1))
    if a <= 0:
        return
    panel(c, 50, 560, 980, 820, a)
    container_icon(c, 165, 650, 150, 72, RED, a)
    text(c, 'COSTO DE ENVIAR', 270, 625, 'mont', 30, SKY, a, align='left', track=2)
    text(c, 'UN CONTENEDOR', 270, 675, 'anton', 56, WHITE, a, align='left')
    # axes
    x0, x1 = 150, 930
    c.drawLine(110, 1290, 980, 1290, P(rgba(SKY, 0.5 * a), stroke=2))
    for v in (2000, 3000, 4000):
        y = vy(v)
        c.drawLine(110, y, 980, y, P(rgba(SKY, 0.12 * a), stroke=1.5))
    # 2x line
    yd = vy(3798)
    pd = prog(t, 43.0, 43.5)
    l = skia.Paint(AntiAlias=True, Color=rgba(GOLD, 0.8 * a * pd)); l.setStyle(skia.Paint.kStroke_Style); l.setStrokeWidth(3)
    l.setPathEffect(skia.DashPathEffect.Make([14, 10], 0))
    c.drawLine(110, yd, 980, yd, l)
    text(c, 'EL DOBLE: $3,798', 125, yd - 24, 'mont', 22, GOLD, a * pd, align='left')
    # curve
    N = 60
    pts = []
    for i in range(N + 1):
        f = i / N
        v = 1899 + (4389 - 1899) * (f ** 2.1 * 0.55 + (1 - math.cos(math.pi * f)) / 2 * 0.45)
        pts.append((lerp(x0, x1, f), vy(v)))
    pc = eio(prog(t, 43.3, 45.0))
    if pc > 0:
        n = max(2, int(pc * N) + 1)
        sub = pts[:n]
        area = skia.Path(); area.moveTo(sub[0][0], 1290)
        for q in sub: area.lineTo(*q)
        area.lineTo(sub[-1][0], 1290); area.close()
        sh = skia.GradientShader.MakeLinear([(0, 870), (0, 1290)], [rgba(RED, 0.55 * a), rgba(RED, 0.0)])
        c.drawPath(area, skia.Paint(AntiAlias=True, Shader=sh))
        res = line(c, pts, RED, 8, a, pc, glow=True)
        (ex, ey), _ = res
        glow_dot(c, ex, ey, 12, RED, a)
        v = 1899 + (4389 - 1899) * pc
        val = f'${int(round(v)):,}'
        c.save(); c.translate(min(ex, 820), ey - 70)
        text(c, val, 0, 0, 'anton', 72 if pc < 1 else 80, WHITE, a, shadow=1.5)
        c.restore()
    # start label
    glow_dot(c, pts[0][0], pts[0][1], 10, WHITE, a)
    text(c, '$1,899', pts[0][0] - 10, pts[0][1] - 52, 'anton', 50, WHITE, a, align='left', shadow=1)
    text(c, 'FEB', x0, 1325, 'mont', 26, SKY, a)
    text(c, 'NOV', x1, 1325, 'mont', 26, SKY, a * prog(t, 44.5, 44.9))
    # stamp
    ps = prog(t, 45.05, 45.3)
    if ps > 0:
        c.save(); c.translate(600, 1150); c.rotate(-9); s = lerp(2.4, 1, eo(ps)); c.scale(s, s)
        q = eo(ps)
        rrect(c, -300, -82, 600, 164, 16, NAVY_D, 0.55 * q)
        rrect(c, -300, -82, 600, 164, 16, RED, q, stroke=10)
        rrect(c, -284, -66, 568, 132, 10, RED, q * 0.6, stroke=3)
        text(c, 'MÁS DEL DOBLE', 0, 0, 'anton', 96, RED, q, track=2)
        c.restore()
    source(c, 'ISW / CTP', t, 43.0, T9 + 0.1)

def s9(c, t):
    photo(c, 'img10b_puerto_sans_souci_crucero', prog(t, T9, T9b + 0.3), 1.0, 1.1, (420, 300), (640, 290), dark=0.4)
    a = eo(prog(t, 47.2, 47.6))
    if a <= 0:
        return
    # header
    c.save(); c.translate(0, 0)
    flag(c, 'do', 115, 555, 110, a)
    text(c, 'REPÚBLICA DOMINICANA', 195, 555, 'anton', 64, WHITE, a, align='left', shadow=1.5)
    c.restore()
    m = M('rd', -74.6, -67.6, 17.0, 20.4, (50, 640, 980, 640))
    panel(c, 50, 640, 980, 640, a, accent=None)
    m.draw(c, a, hl={'Dominican Rep.': (RED, 0.55 + 0.25 * math.sin(t * 5))})
    hx, hy = m.xy(-73.2, 19.3)
    text(c, 'HAITÍ', hx + 40, hy - 20, 'mont', 24, SKY, 0.8 * a, track=3)
    sx_, sy_ = m.xy(-69.88, 18.46)
    marker(c, sx_, sy_, 'SANTO DOMINGO', t, 47.7, RED, 'up', 80, 28)
    rt = smooth([m.xy(*q) for q in [(-67.2, 17.1), (-68.2, 17.45), (-69.1, 17.9), (-69.6, 18.25), (-69.86, 18.43)]], 12)
    pk = eio(prog(t, 48.3, 51.0))
    if pk > 0:
        line(c, rt, WHITE, 4, 0.7 * a, pk, dash=[14, 10])
        (x, y), ang = point_at(rt, pk)
        c.save(); m.clip(c)
        for k in range(5):
            circle(c, x + 30 + k * 18, y + 12 + k * 3, 6 + k * 2, WHITE, 0.25 * (1 - k / 5) * a)
        tanker(c, x, y - 4, 130, WHITE, a, flip=True)
        c.restore()
        label_box(c, x + 10, y - 70, '🛢 PETRÓLEO IMPORTADO'.replace('🛢 ', ''), a * eo(prog(t, 48.6, 49.0)), 22)
    pb = prog(t, 49.75, 50.15)
    if pb > 0:
        y0 = 1340
        c.save(); c.translate(540, y0 + 90); s = lerp(1.3, 1, eo(pb)); c.scale(s, s)
        panel(c, -490, -90, 980, 180, eo(pb))
        text(c, 'RD IMPORTA', -440, -32, 'anton', 64, WHITE, eo(pb), align='left')
        text(c, 'TODO SU PETRÓLEO', -440, 42, 'anton', 64, RED, eo(pb), align='left')
        text(c, '100%', 330, 0, 'anton', 120, WHITE, eo(prog(t, 50.6, 51.0)), shadow=1)
        c.restore()

def s9b(c, t):
    photo(c, 'img9b_gasolinera_precios', prog(t, T9b, T10), 1.0, 1.2, (620, 420), (690, 480), dark=0.48)
    ph = prog(t, 52.45, 52.85)
    if ph > 0:
        text(c, 'CUANDO EL BARCO PAGA MÁS…', W / 2, 590, 'anton', 66, WHITE, eo(ph), shadow=1.5)
    items = [(190, '🛢', 'PETRÓLEO', 52.75, None), (540, '⛽', 'GASOLINA', 54.3, 55.96), (890, '🛒', 'COLMADO', 55.6, 56.78)]
    for k, (x, em, lab, tt, hit) in enumerate(items):
        p = prog(t, tt, tt + 0.4)
        if p <= 0:
            continue
        y = 880
        hot = hit is not None and t >= hit
        c.save(); c.translate(x, y); s = eback(p) * (1 + (0.12 * (1 - prog(t, hit, hit + 0.4)) if hot else 0)); c.scale(s, s)
        circle(c, 0, 0, 140, RED, 0.35 * eo(p) * (1.5 if hot else 1), blur=40)
        circle(c, 0, 0, 132, NAVY_D, 0.88 * eo(p))
        circle(c, 0, 0, 132, RED, eo(p), stroke=6)
        emoji(c, em, 0, 0, 150, eo(p))
        c.restore()
        text(c, lab, x, y + 180, 'anton', 50, WHITE, eo(p), shadow=1.5, track=2)
        # rising $ and arrows
        rng = np.random.RandomState(k + 3)
        for j in range(5):
            ph_ = ((t - tt) * 0.7 + j / 5) % 1
            if t - tt < j * 0.12:
                continue
            ox = rng.uniform(-120, 120)
            yy = y - 120 - 200 * ph_
            al = eo(p) * math.sin(math.pi * ph_)
            if j % 2 == 0:
                text(c, '$', x + ox, yy, 'anton', 46, '#4CFF9A' if False else GOLD, al, shadow=1)
            else:
                arrowhead(c, x + ox, yy, -math.pi / 2, 22, RED, al)
                c.drawLine(x + ox, yy, x + ox, yy + 34, P(rgba(RED, al), stroke=8))
    for (x0, x1, t0) in [(330, 400, 53.9), (680, 750, 55.25)]:
        p = eo(prog(t, t0, t0 + 0.35))
        if p > 0:
            c.drawLine(x0, 880, lerp(x0, x1, p), 880, P(rgba(RED, 1), stroke=10))
            arrowhead(c, lerp(x0, x1, p) + 6, 880, 0, 28, RED)
    pt = prog(t, 54.45, 54.85)
    if pt > 0:
        c.save(); c.translate(540, 1300); s = lerp(1.5, 1, eo(pt)); c.scale(s, s)
        w1 = tw('…LO PAGAS ', 'anton', 120); w2 = tw('TÚ', 'anton', 120)
        x0 = -(w1 + w2 + 30) / 2
        text(c, '…LO PAGAS ', x0, 0, 'anton', 120, WHITE, eo(pt), align='left', shadow=1.5)
        rrect(c, x0 + w1 - 6, -78, w2 + 36, 156, 12, RED, eo(pt))
        text(c, 'TÚ', x0 + w1 + 12, 0, 'anton', 120, WHITE, eo(pt), align='left')
        c.restore()

def s10(c, t):
    photo(c, 'img5_misiles_lanzador', prog(t, T10, T10b + 0.3), 1.0, 1.15, (540, 330), (620, 330))
    a = eo(prog(t, 57.6, 58.0))
    if a <= 0:
        return
    flag(c, 'us', 112, 700, 100, a)
    text(c, 'WASHINGTON', 185, 700, 'anton', 60, WHITE, a, align='left', shadow=1.5, track=2)
    pc = prog(t, 57.8, 58.2)
    if pc > 0:
        y0 = lerp(830, 790, eo(pc))
        panel(c, 50, y0, 980, 470, eo(pc))
        text(c, '“', 120, y0 + 95, 'anton', 220, RED, eo(pc))
        text(c, 'EE. UU. avisó de una', 200, y0 + 95, 'mont', 50, WHITE, eo(prog(t, 58.1, 58.5)), align='left')
        text(c, 'posible ofensiva', 200, y0 + 165, 'mont', 50, WHITE, eo(prog(t, 59.4, 59.8)), align='left')
        for (word, x, tt) in [('CORTA', 200, 60.1), ('E INTENSA', 200 + tw('CORTA ', 'anton', 104), 60.75)]:
            q = prog(t, tt, tt + 0.25)
            if q > 0:
                c.save(); c.translate(x, y0 + 300); s = lerp(1.5, 1, eo(q)); c.scale(s, s)
                text(c, word, 0, 0, 'anton', 104, RED, eo(q), align='left', shadow=1.5)
                c.restore()
        text(c, '”', 975, y0 + 420, 'anton', 180, RED, eo(prog(t, 61.0, 61.3)))
    source(c, 'reportes de prensa', t, 57.9, T10b + 0.1)

def s10b(c, t):
    photo(c, 'img5b_misil_exhibicion', prog(t, T10b, T11), 1.0, 1.15, (420, 420), (380, 440), dark=0.48)
    text(c, 'IRÁN TODAVÍA TIENE HASTA', W / 2, 545, 'mont', 38, SKY, eo(prog(t, 62.0, 62.4)), shadow=1, track=2)
    pc = prog(t, 62.4, 63.95)
    if pc > 0:
        v = int(round(2500 * eo(pc)))
        done = t >= 63.95
        sc = 1 + 0.12 * (1 - prog(t, 63.95, 64.3)) if done else 1
        c.save(); c.translate(W / 2, 730); c.scale(sc, sc)
        circle(c, 0, 0, 230, RED, 0.3, blur=90)
        text(c, f'{v:,}', 0, 0, 'anton', 250, RED, 1, stroke=8, stroke_color=WHITE)
        text(c, f'{v:,}', 0, 0, 'anton', 250, RED, 1)
        c.restore()
    pm = prog(t, 64.8, 65.1)
    if pm > 0:
        c.save(); c.translate(W / 2, 930); s = lerp(1.6, 1, eo(pm)); c.scale(s, s)
        text(c, 'MISILES', 0, 0, 'anton', 120, WHITE, eo(pm), shadow=1.5, track=10)
        c.restore()
    # map with ranges
    a = eo(prog(t, 62.0, 62.5))
    if a > 0:
        m = M('range', 27.0, 76.0, 9.0, 44.0, (50, 1040, 980, 580))
        panel(c, 50, 1040, 980, 580, a, accent=None)
        m.draw(c, a, hl={'Iran': (RED, 0.6), 'Israel': ('#3D6FD1', 0.9)})
        ox, oy = m.xy(53.7, 32.4)
        c.save(); m.clip(c)
        kpd = m.k / 111.0
        for j, (km, tt) in enumerate([(1000, 62.3), (2000, 62.7)]):
            pr = eo(prog(t, tt, tt + 1.0))
            r = km * kpd * pr
            circle(c, ox, oy, r, RED, 0.1 * a, )
            circle(c, ox, oy, r, RED, 0.9 * a, stroke=4)
            if pr > 0.95:
                text(c, f'{km:,} KM', ox + r * 0.7, oy - r * 0.72, 'mont', 22, WHITE, a, shadow=1)
        for k in range(3):
            ph = ((t - 62.0) / 1.6 + k / 3) % 1
            circle(c, ox, oy, 30 + 60 * ph, RED, 0.6 * (1 - ph), stroke=3)
        for (lon, lat, tt) in [(35.0, 31.6, 63.2), (50.55, 26.05, 63.45), (45.0, 15.0, 63.7)]:
            tx, ty = m.xy(lon, lat)
            mx_, my_ = (ox + tx) / 2, min(oy, ty) - 110
            pts = [(ox + (tx - ox) * f + 0, (1 - f) ** 2 * oy + 2 * (1 - f) * f * my_ + f * f * ty) for f in np.linspace(0, 1, 30)]
            pts = [((1 - f) ** 2 * ox + 2 * (1 - f) * f * mx_ + f * f * tx, (1 - f) ** 2 * oy + 2 * (1 - f) * f * my_ + f * f * ty) for f in np.linspace(0, 1, 30)]
            pr = eio(prog(t, tt, tt + 0.8))
            res = line(c, pts, GOLD, 4, a, pr, dash=[12, 8])
            if res and pr < 1:
                (x, y), ang = res
                missile(c, x, y, 34, WHITE, a, rot=ang + math.pi / 2)
            if pr >= 1:
                flash(c, tx, ty, tt + 0.8, t, 40)
        c.restore()
        text(c, 'IRÁN', ox, oy + 60, 'anton', 44, WHITE, a, shadow=1, track=4)
        ix, iy = m.xy(35.0, 31.6)
        text(c, 'ISRAEL', ix - 10, iy - 34, 'mont', 22, WHITE, a * prog(t, 63.6, 64.0), shadow=1)
    source(c, 'Wall Street Journal', t, 62.2, T11 + 0.1)

def s11(c, t):
    navy_bg(c, t)
    # decorative rings
    for k in range(3):
        ph = ((t - T11) / 3 + k / 3) % 1
        circle(c, W / 2, 1000, 100 + 700 * ph, BLUE, 0.25 * (1 - ph), stroke=2)
    pt = prog(t, 66.0, 66.4)
    if pt > 0:
        c.save(); c.translate(W / 2, 610); s = lerp(1.5, 1, eo(pt)); c.scale(s, s)
        text(c, '¿ESTA GUERRA…?', 0, 0, 'anton', 132, WHITE, eo(pt), shadow=1.5)
        c.restore()
        bw = 520 * eo(prog(t, 66.2, 66.6))
        c.drawRect(skia.Rect.MakeXYWH(W / 2 - bw / 2, 700, bw, 10), P(rgba(RED, 1)))
    for (y, em, lab, tt, fill, dirn) in [(850, '🕊', 'TERMINA PRONTO', 66.9, NAVY_L, -1), (1060, '🔥', 'APENAS EMPIEZA', 68.4, RED_D, 1)]:
        p = prog(t, tt, tt + 0.45)
        if p <= 0:
            continue
        x = W / 2 + dirn * 900 * (1 - eback(p))
        pul = 0.5 + 0.5 * math.sin((t - tt) * 4)
        c.save(); c.translate(x, y)
        rrect(c, -440, -82, 880, 164, 30, fill if fill != RED_D else RED, 0.25 * pul, blur=30)
        rrect(c, -430, -78, 860, 156, 30, fill, 0.95)
        rrect(c, -430, -78, 860, 156, 30, WHITE, 0.8, stroke=4)
        circle(c, -330, 0, 56, WHITE, 0.95)
        emoji(c, em, -330, 0, 78)
        text(c, lab, -250, 0, 'anton', 76, WHITE, 1, align='left', track=2)
        c.restore()
    pc = prog(t, 69.85, 70.2)
    if pc > 0:
        c.save(); c.translate(W / 2, 1290); s = lerp(1.3, 1, eo(pc)); c.scale(s, s)
        text(c, 'TE LEO EN LOS COMENTARIOS', 0, 0, 'mont', 50, WHITE, eo(pc), shadow=1)
        c.restore()
        bounce = abs(math.sin((t - 69.85) * 5)) * 30
        emoji(c, '👇', W / 2, 1430 + bounce, 120, eo(pc))

SCENES = [(0.0, s1), (T2, s2), (T3, s3), (T4, s4), (T5, s5), (T5b, s5b), (T6, s6), (T6b, s6b), (T7, s7), (T7b, s7b),
          (T8, s8), (T9, s9), (T9b, s9b), (T10, s10), (T10b, s10b), (T11, s11)]
XF = 0.22

def frame(c, t):
    idx = 0
    for i, (st, fn) in enumerate(SCENES):
        if t >= st:
            idx = i
    st, fn = SCENES[idx]
    c.clear(rgba(NAVY_D))
    if idx > 0 and t - st < XF:
        SCENES[idx - 1][1](c, t)
        p = (t - st) / XF
        c.saveLayerAlpha(None, int(255 * eo(p)))
        c.save(); s = lerp(1.06, 1.0, eo(p)); c.translate(W / 2, H / 2); c.scale(s, s); c.translate(-W / 2, -H / 2)
        fn(c, t)
        c.restore(); c.restore()
        c.drawRect(skia.Rect.MakeWH(W, H), P(rgba(WHITE, 0.18 * (1 - p))))
    else:
        fn(c, t)
    subtitles(c, t)
    handle(c, t)
