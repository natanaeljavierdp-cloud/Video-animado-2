"""Timeline: maps time -> list of (state, weight) shots. Synced to voice word timings."""
import math
import chaingeom as cg

FPS = 30
DUR = 60.30
NFRAMES = int(round(DUR * FPS))  # 1809
P = cg.P
CAS = [11, 13, 15, 17, 19, 21, 24, 28, 34]
COG_Y = {n: -0.0512 + i * 0.0039 for i, n in enumerate(CAS)}
RING_Y = {34: -0.0400, 50: -0.0455}


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ss(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def sss(x):  # smootherstep
    x = clamp(x)
    return x * x * x * (x * (x * 6 - 15) + 10)


def ramp(t, t0, t1):
    return ss((t - t0) / (t1 - t0)) if t1 > t0 else float(t >= t0)


def lerp(a, b, f):
    return a + (b - a) * f


def vlerp(a, b, f):
    return tuple(lerp(x, y, f) for x, y in zip(a, b))


def env(t, pts):
    """piecewise smooth envelope through (t, value) points"""
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1:
            return lerp(v0, v1, ss((t - t0) / (t1 - t0)))
    return pts[-1][1]


# ------------------------------------------------------------------ chain travel s(t)
# speed keys (t, v m/s); turn segments defined separately with exact distance
SPEED_KEYS = [(0, 0.22), (6.0, 0.22), (7.0, 0.12), (11.6, 0.12), (12.4, 0.22), (17.4, 0.22),
              (18.0, 0.10), (18.3, 0.05), (21.0, 0.05), (21.6, 0.004), (25.6, 0.004), (26.3, 0.10),
              (28.3, 0.10), (28.6, 0.06), (30.8, 0.06), (31.4, 0.18), (33.4, 0.18), (33.6, 0.12),
              (35.6, 0.12), (36.2, 0.10), (39.3, 0.0)]
TURN1 = (39.45, 42.35, 50 * P)   # exactly one crank revolution on 50T
ROAD1 = (42.35, 44.75, 1.25 * 50 * P)  # cadence 1.25 rev/s
TURN2 = (46.75, 49.15, 34 * P)   # one revolution on 34T
HILL = (49.15, 52.30, 1.0 * 34 * P)


def speed(t):
    if t < 39.3:
        return env(t, SPEED_KEYS) if False else _plin(t, SPEED_KEYS)
    for (a, b, dist) in (TURN1, TURN2):
        if a <= t < b:
            u = (t - a) / (b - a)
            return dist / (b - a) * (1 - math.cos(2 * math.pi * u))
    if ROAD1[0] <= t < ROAD1[1]:
        a, b, v = ROAD1
        return v * ss((t - a) / 0.25)
    if 44.75 <= t < 46.75:
        return 0.08 * ss((t - 44.75) / 0.2) * (1 - ss((t - 46.4) / 0.35))
    if HILL[0] <= t < HILL[1]:
        a, b, v = HILL
        return v * ss((t - a) / 0.25)
    if t >= 52.3:
        return 0.16
    return 0.0


def _plin(t, keys):
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            return lerp(v0, v1, (t - t0) / (t1 - t0))
    return keys[-1][1]


S_TABLE = []


def build_s_table():
    global S_TABLE
    sub = 20
    dt = 1.0 / (FPS * sub)
    s = 0.0
    tab = [0.0]
    t = 0.0
    for f in range(NFRAMES + 2):
        for k in range(sub):
            s += speed(t + dt / 2) * dt
            t += dt
        tab.append(s)
    S_TABLE = tab


def s_at(t):
    if not S_TABLE:
        build_s_table()
    x = t * FPS
    i = int(math.floor(x))
    i = max(0, min(i, len(S_TABLE) - 2))
    f = x - i
    return lerp(S_TABLE[i], S_TABLE[i + 1], f)


# ------------------------------------------------------------------ gear configuration

def rear_shift(u, na, nb):
    """returns y_der, r_chain, y_chain, w (engagement), r_geom"""
    ra, rb = cg.pitch_r(na), cg.pitch_r(nb)
    ya, yb = COG_Y[na], COG_Y[nb]
    lift = max(ra, rb) + 0.0090
    y_der = lerp(ya, yb, ss(u / 0.45))
    r = ra
    if u < 0.35:
        r = lerp(ra, lift, ss((u - 0.08) / 0.27))
    elif u < 0.62:
        r = lift
    else:
        r = lerp(lift, rb, ss((u - 0.62) / 0.30))
    y_chain = lerp(ya, yb, ss((u - 0.36) / 0.24))
    w = ss((u - 0.75) / 0.2) if u > 0.05 else 1.0
    if u <= 0.0:
        w = 1.0
    r_geom = lerp(ra, rb, ss(u / 0.45))
    return y_der, r, y_chain, w, r_geom


def drive_main(t):
    s = s_at(t)
    # rear: 11 -> 13 (18.35..21.0) ; 13 -> 11 (28.6..30.8)
    n_cog, y_der, r_cog, y_cogc, w_cog, r_geom = 11, COG_Y[11], cg.pitch_r(11), COG_Y[11], 1.0, cg.pitch_r(11)
    if 18.35 <= t < 21.0:
        u = (t - 18.35) / (21.0 - 18.35)
        y_der, r_cog, y_cogc, w_cog, r_geom = rear_shift(u, 11, 13)
        n_cog = 13 if u > 0.5 else 11
    elif 21.0 <= t < 28.6:
        n_cog, y_der, r_cog, y_cogc, r_geom = 13, COG_Y[13], cg.pitch_r(13), COG_Y[13], cg.pitch_r(13)
    elif 28.6 <= t < 30.8:
        u = (t - 28.6) / (30.8 - 28.6)
        y_der, r_cog, y_cogc, w_cog, r_geom = rear_shift(u, 13, 11)
        n_cog = 11 if u > 0.5 else 13
    # front: 34 -> 50 (33.6..35.6)
    n_ring, r_ring, y_ring, y_fd, w_ring = 34, cg.pitch_r(34), RING_Y[34], RING_Y[34], 1.0
    if t >= 33.6:
        u = clamp((t - 33.6) / 2.0)
        ra, rb = cg.pitch_r(34), cg.pitch_r(50)
        y_fd = lerp(RING_Y[34], RING_Y[50] - 0.001, ss(u / 0.4))
        lift = rb + 0.0095
        if u < 0.4:
            r_ring = lerp(ra, lift, ss((u - 0.1) / 0.3))
        elif u < 0.62:
            r_ring = lift
        else:
            r_ring = lerp(lift, rb, ss((u - 0.62) / 0.3))
        y_ring = lerp(RING_Y[34], RING_Y[50], ss((u - 0.4) / 0.22))
        w_ring = ss((u - 0.8) / 0.18)
        n_ring = 50 if u > 0.5 else 34
        if u >= 1.0:
            w_ring = 1.0
    return dict(s=s, r_ring=r_ring, r_cog=r_cog, y_ring=y_ring, y_cogc=y_cogc, y_der=y_der, y_fd=y_fd,
                n_ring=n_ring, n_cog=n_cog, w_ring=w_ring, w_cog=w_cog, r_cog_geom=r_geom)


def drive_fixed(t, nr, nc):
    return dict(s=s_at(t), r_ring=cg.pitch_r(nr), r_cog=cg.pitch_r(nc), y_ring=RING_Y[nr], y_cogc=COG_Y[nc],
                y_der=COG_Y[nc], y_fd=RING_Y[nr], n_ring=nr, n_cog=nc, w_ring=1, w_cog=1, r_cog_geom=cg.pitch_r(nc))


# ------------------------------------------------------------------ camera
def hermite_path(keys, t):
    """keys: list of (t, dict(pos, tgt, lens, fstop)). Catmull-Rom (non-uniform) for vectors, smooth for scalars"""
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]
    for i in range(len(keys) - 1):
        if keys[i][0] <= t <= keys[i + 1][0]:
            break
    t0, k0 = keys[i]
    t1, k1 = keys[i + 1]
    tp, kp = keys[i - 1] if i > 0 else (t0 - (t1 - t0), k0)
    tn, kn = keys[i + 2] if i + 2 < len(keys) else (t1 + (t1 - t0), k1)
    h = t1 - t0
    u = (t - t0) / h
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1
    h10 = u ** 3 - 2 * u ** 2 + u
    h01 = -2 * u ** 3 + 3 * u ** 2
    h11 = u ** 3 - u ** 2
    out = {}
    for key in k0:
        a, b = k0[key], k1[key]
        pa, nb = kp.get(key, a), kn.get(key, b)
        if isinstance(a, tuple):
            m0 = tuple(((b[j] - pa[j]) / (t1 - tp)) * h for j in range(3))
            m1 = tuple(((nb[j] - a[j]) / (tn - t0)) * h for j in range(3))
            if i == 0:
                m0 = (0, 0, 0)
            if i + 2 >= len(keys):
                m1 = (0, 0, 0)
            out[key] = tuple(h00 * a[j] + h10 * m0[j] + h01 * b[j] + h11 * m1[j] for j in range(3))
        else:
            out[key] = lerp(a, b, ss(u))
    return out


def K(t, pos, tgt, lens=40, fstop=4.0):
    return (t, dict(pos=pos, tgt=tgt, lens=lens, fstop=fstop))


CAM_STUDIO_A = [
    K(0.0, (1.75, -2.95, 1.05), (0.06, 0.0, 0.52), 35, 8),
    K(2.6, (1.62, -2.70, 1.02), (0.06, 0.0, 0.54), 35, 8),
    K(4.3, (1.85, -2.85, 1.12), (0.12, 0.0, 0.64), 30, 8),
    K(5.5, (1.20, -1.10, 1.08), (0.62, -0.02, 0.98), 30, 5.6),
    K(6.4, (1.18, -0.72, 1.07), (0.72, -0.14, 0.95), 36, 5.6),
    K(7.3, (1.06, -0.43, 0.97), (0.685, -0.21, 0.86), 46, 4.5),
    K(8.3, (1.01, -0.41, 0.94), (0.685, -0.21, 0.855), 52, 4.5),
    K(9.1, (0.96, -0.39, 0.92), (0.685, -0.215, 0.86), 60, 5.0),
    K(10.3, (0.91, -0.42, 0.93), (0.665, -0.205, 0.87), 55, 5.0),
    K(11.4, (0.86, -0.52, 1.00), (0.585, -0.11, 0.85), 44, 5.0),
    K(12.3, (0.86, -0.78, 0.96), (0.52, -0.02, 0.72), 38, 5.6),
    K(13.5, (0.20, -0.60, 0.98), (0.30, -0.01, 0.50), 38, 5.6),
    K(14.7, (0.02, -0.72, 0.62), (0.0, -0.02, 0.30), 38, 5.6),
    K(15.9, (-0.17, -0.62, 0.41), (-0.25, -0.05, 0.31), 42, 5.0),
    K(17.0, (-0.24, -0.44, 0.37), (-0.40, -0.06, 0.29), 46, 4.5),
    K(18.0, (-0.52, -0.36, 0.49), (-0.42, -0.05, 0.32), 46, 8),
    K(19.6, (-0.51, -0.31, 0.50), (-0.42, -0.045, 0.335), 50, 8),
    K(21.0, (-0.52, -0.27, 0.50), (-0.42, -0.045, 0.345), 54, 8),
    K(22.4, (-0.54, -0.17, 0.47), (-0.42, -0.046, 0.355), 64, 11),
    K(25.4, (-0.55, -0.18, 0.465), (-0.42, -0.047, 0.352), 62, 11),
    K(26.6, (-0.56, -0.31, 0.28), (-0.43, -0.066, 0.29), 52, 8),
    K(28.4, (-0.52, -0.30, 0.24), (-0.43, -0.065, 0.29), 55, 8),
    K(30.6, (-0.50, -0.32, 0.25), (-0.43, -0.065, 0.29), 55, 8),
    K(31.7, (-0.50, -0.40, 0.36), (-0.32, -0.05, 0.33), 45, 6),
    K(32.7, (-0.34, -0.37, 0.47), (-0.18, -0.045, 0.35), 45, 6),
    K(33.6, (-0.22, -0.33, 0.55), (-0.02, -0.04, 0.36), 45, 8),
    K(35.6, (-0.18, -0.36, 0.56), (0.0, -0.04, 0.35), 45, 8),
    K(36.6, (-0.26, -2.05, 0.52), (-0.21, 0.0, 0.40), 40, 8),
]
CAM_GEARS = (-0.26, -2.05, 0.52), (-0.21, 0.0, 0.40), 40
CAM_ROAD = [K(42.2, (1.75, -2.60, 0.55), (0.05, 0.0, 0.50), 30, 6), K(44.9, (1.25, -2.30, 0.48), (-0.10, 0.0, 0.48), 30, 6)]
CAM_HILL = [K(49.0, (0.45, -2.75, 0.50), (0.10, 0.0, 0.62), 30, 6), K(52.5, (0.15, -2.65, 0.48), (0.05, 0.0, 0.62), 30, 6)]
CAM_FINAL = [K(52.0, (2.35, -3.75, 1.25), (0.08, 0.0, 0.62), 30, 8), K(57.3, (2.25, -3.55, 1.18), (0.08, 0.0, 0.56), 30, 8),
             K(60.4, (3.20, -4.90, 1.45), (0.08, 0.0, 0.55), 30, 8)]

# ------------------------------------------------------------------ explode
EXPLODE_ORDER = ["frame", "fork", "rear_wheel", "front_wheel", "bar", "saddle", "crank", "pedal-1", "pedal1",
                 "chain", "cassette", "rd", "fd", "cables", "bolt0", "bolt1", "bolt2", "bolt3", "bolt4"]
REASSEMBLE_ORDER = ["frame", "fork", "rear_wheel", "front_wheel", "crank", "cassette", "chain", "rd", "fd",
                    "bar", "cables", "saddle", "pedal-1", "pedal1", "bolt0", "bolt1", "bolt2", "bolt3", "bolt4"]
BAR_ZONE = ["bar", "cables"]


def explode_main(t):
    ex = {}
    for i, n in enumerate(EXPLODE_ORDER):
        t0 = 2.75 + 0.06 * i
        e = sss((t - t0) / 1.25)
        if n in BAR_ZONE:
            e *= 1 - sss((t - 6.25) / 1.0)
        else:
            e *= 1 - sss((t - (8.0 + 0.12 * i)) / 1.6)
        ex[n] = e
    return ex


LANDINGS = {}


def explode_final(t):
    ex = {}
    for i, n in enumerate(REASSEMBLE_ORDER):
        t0 = 52.7 + 0.21 * i
        u = (t - t0) / 0.75
        ex[n] = 1 - sss(u)
        LANDINGS[n] = t0 + 0.75
    return ex


# ------------------------------------------------------------------ shots
LIGHTS = dict(key=125, rim1=260, rim2=200, top=50, backwash=110, kick=25)
ROAD_LIGHTS = dict(key=70, rim1=300, rim2=240, top=15, backwash=0, kick=10)
def base(t):
    return dict(t=t, explode={"*": 0.0}, lights=dict(LIGHTS), road=0, pitch=0.0, road_dist=0.0, spin_t=t,
                drive_id="main", drive=drive_main(t), hand_vis=0.0, marker_glow=0.0)


def shot_studio(t):
    st = base(t)
    st["explode"] = explode_main(t)
    c = hermite_path(CAM_STUDIO_A, t)
    st.update(cam_pos=c["pos"], cam_tgt=c["tgt"], lens=c["lens"], fstop=c["fstop"])
    # bike slowly turning at the start
    st["bike_rot"] = 0.55 * (1 - sss(t / 6.0))
    # hand & lever (S2)
    st["hand_vis"] = 1.0 if 6.5 <= t <= 12.4 else 0.0
    st["hand_app"] = ss((t - 6.6) / 1.0) * (1 - ss((t - 11.4) / 0.9))
    lev = ramp(t, 8.55, 8.85) * (1 - ramp(t, 9.65, 9.95))
    st["lever"] = lev
    st["hand_press"] = lev
    st["ratchet"] = -(2 * math.pi / 12) * ramp(t, 8.78, 8.92)
    st["pawl"] = 0.32 * ramp(t, 8.62, 8.82) * (1 - ramp(t, 8.88, 8.93))
    st["xray_hood"] = env(t, [(8.75, 0), (9.05, 1.0), (11.0, 1.0), (11.6, 0.0)])
    st["xray_frame"] = env(t, [(11.7, 0), (12.5, 1.0), (16.3, 1.0), (17.4, 0.0)])
    st["xray_rd"] = env(t, [(26.3, 0), (27.1, 1.0), (30.9, 1.0), (31.6, 0.0)])
    st["pulse_amp"] = env(t, [(9.3, 0), (9.5, 14.0), (16.8, 14.0), (17.6, 0.0)])
    st["pulse"] = env(t, [(9.42, -0.02), (11.7, 0.17), (16.65, 0.985)]) if t < 16.65 else 0.985
    if t < 9.42:
        st["pulse"] = -0.1
    st["pulse_line"] = env(t, [(11.6, 0.0), (12.4, 0.10), (16.6, 0.10), (17.5, 0.0)])
    st["ramp_glow"] = env(t, [(21.9, 0), (22.8, 6.0), (25.7, 6.0), (26.3, 0)])
    return st


def gear_cam(st, t, t0):
    p, tg, lens = CAM_GEARS
    d = 0.08 * (t - t0) / 6.0
    st.update(cam_pos=(p[0] - d * 0.4, p[1] + d, p[2]), cam_tgt=tg, lens=lens, fstop=8)


def shot_gears1(t):  # S7 display 50x11
    st = shot_studio(t)
    gear_cam(st, t, 36.6)
    st["marker_glow"] = 2.0 * ramp(t, 38.8, 39.3)
    if t < 36.6:
        c = hermite_path(CAM_STUDIO_A, t)
        st.update(cam_pos=c["pos"], cam_tgt=c["tgt"], lens=c["lens"], fstop=c["fstop"])
    return st


def shot_road(t):
    st = base(t)
    st["drive"] = drive_main(t)
    st["road"] = 1
    c = hermite_path(CAM_ROAD, t)
    st.update(cam_pos=c["pos"], cam_tgt=c["tgt"], lens=c["lens"], fstop=c["fstop"])
    st["world"] = (0.010, 0.012, 0.018, 1)
    st["lights"] = dict(ROAD_LIGHTS)
    return st


def shot_gears2(t):  # S8 display 34x34
    st = base(t)
    st["drive_id"] = "B"
    st["drive"] = drive_fixed(t, 34, 34)
    gear_cam(st, t, 44.6)
    st["marker_glow"] = 2.0
    return st


def shot_hill(t):
    st = base(t)
    st["drive_id"] = "B"
    st["drive"] = drive_fixed(t, 34, 34)
    st["road"] = 1
    st["pitch"] = 0.20
    c = hermite_path(CAM_HILL, t)
    st.update(cam_pos=c["pos"], cam_tgt=c["tgt"], lens=c["lens"], fstop=c["fstop"])
    st["world"] = (0.010, 0.012, 0.018, 1)
    st["lights"] = dict(ROAD_LIGHTS)
    return st


def shot_final(t):
    st = base(t)
    st["drive_id"] = "C"
    st["drive"] = drive_fixed(t, 50, 15)
    st["explode"] = explode_final(t)
    st["spin_t"] = t
    c = hermite_path(CAM_FINAL, t)
    st.update(cam_pos=c["pos"], cam_tgt=c["tgt"], lens=c["lens"], fstop=c["fstop"])
    st["bike_rot"] = 0.45 - 0.10 * (t - 52.0)
    return st


SHOTS = [  # (name, fn, t_in, t_out)  crossfade where ranges overlap
    ("studio", shot_studio, 0.0, 36.6),
    ("gears1", shot_gears1, 36.6, 42.55),
    ("road", shot_road, 42.40, 44.85),
    ("gears2", shot_gears2, 44.70, 49.40),
    ("hill", shot_hill, 49.25, 52.30),
    ("final", shot_final, 52.15, DUR + 0.2),
]


def shots_at(t):
    out = []
    for name, fn, a, b in SHOTS:
        if a <= t < b:
            out.append((name, fn, a, b))
    if len(out) == 1:
        return [(out[0][0], out[0][1], 1.0)]
    # crossfade: weight of the later shot rises across overlap
    (n1, f1, a1, b1), (n2, f2, a2, b2) = out[0], out[1]
    w2 = ss((t - a2) / (b1 - a2))
    return [(n1, f1, 1 - w2), (n2, f2, w2)]
