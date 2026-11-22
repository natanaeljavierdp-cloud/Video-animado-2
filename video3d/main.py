"""Build the whole toy-model scene and render frames (Workbench).
usage: python main.py START END [STEP] [--res 1.0] [--out DIR]
"""
import sys, os, time, math, json, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix, Quaternion, Euler
from bpy_extras.object_utils import world_to_camera_view
import numpy as np

bpy.ops.wm.read_factory_settings(use_empty=True)
from util import *
import car as carmod
import mech
import envs

FPS = 30
DUR = 84.43
NF = int(math.ceil(DUR * FPS))

# ------------------------------------------------------------------ setup
S = bpy.context.scene
S.render.engine = 'BLENDER_WORKBENCH'
S.render.resolution_x = 1080
S.render.resolution_y = 1920
S.render.film_transparent = True
S.view_settings.view_transform = 'Standard'
S.render.image_settings.file_format = 'PNG'
S.render.image_settings.color_mode = 'RGBA'
S.render.image_settings.compression = 15
S.display.render_aa = os.environ.get('AA','5')
sh = S.display.shading
sh.light = 'STUDIO'
sh.studio_light = 'paint.sl'
sh.color_type = 'MATERIAL'
sh.show_shadows = True
sh.shadow_intensity = 0.35
sh.show_cavity = True
sh.cavity_type = 'BOTH'
sh.cavity_ridge_factor = 1.0
sh.cavity_valley_factor = 1.0
sh.show_object_outline = True
sh.object_outline_color = (0, 0, 0)
sh.show_backface_culling = True
sh.show_specular_highlight = False
S.display.light_direction = (0.35, -0.45, 0.82)
S.display.shadow_shift = 0.05
S.display.shadow_focus = 0.6

HL = mat('HL', '#fff36b')
HL2 = mat('HL2', '#fffbe0')

car, P, CM = carmod.build_car()
E = mech.build_engine(car)
G = mech.build_gearbox(car)
CO = mech.build_callout(None)
B = {
    'curve': envs.board_curve(), 'track': envs.board_track(), 'city': envs.board_city(),
    'highway': envs.board_highway(), 'strada': envs.board_strada(), 'sport': envs.board_sport(),
    'corsa': envs.board_corsa(), 'barrio': envs.board_barrio(), 'open': envs.board_open(),
}
BAL = envs.build_balance()
GRIP = envs.build_grip_arrows()
AIRA = envs.build_air_arrows(10)
CAIR = envs.build_dashes(14, '#2f8cff', 'cair', 0.05, 0.22)
DROPS = envs.build_drops(12)
SPARK = envs.build_star('spark', '#fff200', 0.22, 0.07, 6)
FLASH = envs.build_star('flash', '#ff7a1a', 0.55, 0.30, 9, 0.05)
STREAM = envs.build_dashes(90, '#3d8bff', 'stream', 0.03, 0.42)
DOWN = envs.build_down_arrows(5)
RING = envs.build_ring(4.02, 0.16, 40)
SEL = envs.build_selector()

# power line object (rebuilt per frame)
PWR_M = mat('power', '#ffe14a')
pwr_obj = bpy.data.objects.new('power', bpy.data.meshes.new('power'))
link(pwr_obj)
pwr_obj.parent = car
pwr_obj.data.materials.append(PWR_M)

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
link(cam)
S.camera = cam
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 36.0
cam.data.clip_start = 0.05
cam.data.clip_end = 400

# ------------------------------------------------------------------ helpers
_children = {}


def descend(ob):
    if ob.name not in _children:
        out = [ob]
        for c in ob.children:
            out += descend(c)
        _children[ob.name] = out
    return _children[ob.name]


def show(ob, v):
    for o in descend(ob):
        o.hide_render = not v


def set_mat(ob, m):
    for s in ob.material_slots:
        s.material = m


def reset_mat(ob):
    for i, s in enumerate(ob.material_slots):
        s.material = bpy.data.materials[ob['basemats'][i]]


def hl(obs, m=None):
    for ob in obs:
        for o in descend(ob):
            if o.type == 'MESH':
                set_mat(o, m or HL)


ALL_MESH = [o for o in bpy.data.objects if o.type == 'MESH' and 'basemats' in o.keys()]


def window(t, a, b, fade=0.25):
    """1 inside [a,b] with smooth fades."""
    return smooth(ramp(t, a, a + fade)) * (1 - smooth(ramp(t, b - fade, b)))


# ------------------------------------------------------------------ timing (from word timestamps)
T = dict(
    explode=7.10, s2=8.52, behind=10.34, balance=13.34, curve=15.28, s3=17.66, cyl10=19.26, turbo=20.18,
    hp=21.36, air=23.82, mix=26.22, spark=27.76, boom=28.42, push=29.40, s4=31.50, crank=32.94,
    force=33.68, seven=35.52, dual=36.56, mientras=37.52, parpadeo=40.48, s5=42.34, result=45.28,
    s6=48.90, rear=51.30, city=53.30, hw=57.72, s7=61.76, strada=64.50, sport=67.36, corsa=69.26,
    s8=71.00, conductos=72.76, usa=74.34, s9=77.46, sueno=79.90, capotillo=80.86, s10=81.96, end=DUR)


# ------------------------------------------------------------------ integrated angles
def integrate(fn, t, dt=1 / 240):
    n = int(t / dt)
    acc = 0.0
    for i in range(n):
        acc += fn(i * dt) * dt
    return acc


def crank_rate(t):  # rad/s
    w = 0.0
    if t < T['s2'] + 0.5:
        w = 0.0
    elif t < T['s3']:
        w = 2 * math.pi * 1.2
    elif t < T['hp']:
        w = 2 * math.pi * 1.4
    elif t < T['hp'] + 1.6:
        w = 2 * math.pi * (1.4 + 2.2 * math.sin(math.pi * ramp(t, T['hp'], T['hp'] + 1.6)))
    elif t < T['s5'] + 3:
        w = 2 * math.pi * 1.5
    else:
        w = 2 * math.pi * 1.5
    return w


# speed of car (m/s) used for wheel spin
def run_sim_t(t):
    return max(0.0, min(3.2, (t - 45.40) / 2.60 * 3.2))


ACC = 27.78 / 3.2


def car_speed(t):
    if T['curve'] + 0.3 <= t < T['s3']:
        return 3.2
    if 45.40 <= t < 48.0:
        return ACC * run_sim_t(t)
    if 48.0 <= t < 49.4:
        return 27.78 * (1 - smooth(ramp(t, 48.0, 49.4)))
    if T['city'] <= t < T['hw'] - 0.2:
        return city_speed(t)
    if T['hw'] - 0.2 <= t < T['s7'] + 0.6:
        return 12.0
    if 62.8 <= t < T['s8']:
        return mode_speed(t)
    if T['s8'] <= t < 76.5:
        return 6.0
    return 0.0


def mode_speed(t):
    if t < T['sport']:
        return 5.0
    if t < T['corsa']:
        return lerp(5.0, 11.0, smooth(ramp(t, T['sport'], T['sport'] + 0.8)))
    return lerp(11.0, 20.0, smooth(ramp(t, T['corsa'], T['corsa'] + 0.8)))


# --- city turn geometry (board city placed at CITY_OFF) ---
CITY_OFF = Vector((6.0, 0.0, 0.0))
ICR_LOCAL = Vector((-0.40, 4.0))   # ICR in car frame during turn
R_TURN = ICR_LOCAL.length
D_STRAIGHT1 = 4.6
D_ARC = R_TURN * math.pi / 2
CITY_T0, CITY_T1 = T['city'] + 0.15, T['hw'] - 0.35


def city_speed(t):
    tt = ramp(t, CITY_T0, CITY_T1)
    # distance profile: smooth accelerate / decelerate
    total = D_STRAIGHT1 + D_ARC + 3.0
    return total / (CITY_T1 - CITY_T0) * 30 * tt * tt * (1 - tt) * (1 - tt) * 1.0 / 1.0 if False else total / (CITY_T1 - CITY_T0) * 6 * tt * (1 - tt) * 1.0


def city_dist(t):
    total = D_STRAIGHT1 + D_ARC + 3.0
    tt = ramp(t, CITY_T0, CITY_T1)
    return total * smooth(tt)


def city_pose(t):
    """Return (pos Vector world, yaw, steer_front, steer_rear)."""
    d = city_dist(t)
    start = CITY_OFF + Vector((-3.0, 0, 0))
    df = math.atan2(1.31 - ICR_LOCAL.x, ICR_LOCAL.y)
    dr = math.atan2(-1.31 - ICR_LOCAL.x, ICR_LOCAL.y)
    if d <= D_STRAIGHT1:
        pos = start + Vector((d, 0, 0))
        yaw = 0.0
        k = smooth(ramp(d, D_STRAIGHT1 - 1.4, D_STRAIGHT1))
        return pos, yaw, df * k, dr * k
    if d <= D_STRAIGHT1 + D_ARC:
        a = (d - D_STRAIGHT1) / R_TURN
        p0 = start + Vector((D_STRAIGHT1, 0, 0))
        icr = p0 + Vector((ICR_LOCAL.x, ICR_LOCAL.y, 0))
        rel = p0 - icr
        rot = Matrix.Rotation(a, 3, 'Z')
        pos = icr + rot @ rel
        k = 1 - smooth(ramp(d, D_STRAIGHT1 + D_ARC - 1.2, D_STRAIGHT1 + D_ARC))
        return pos, a, df * k, dr * k
    a = math.pi / 2
    p0 = start + Vector((D_STRAIGHT1, 0, 0))
    icr = p0 + Vector((ICR_LOCAL.x, ICR_LOCAL.y, 0))
    pend = icr + Matrix.Rotation(a, 3, 'Z') @ (p0 - icr)
    pos = pend + Vector((0, d - D_STRAIGHT1 - D_ARC, 0))
    return pos, a, 0.0, 0.0


CITY_ICR_W = CITY_OFF + Vector((-3.0 + D_STRAIGHT1 + ICR_LOCAL.x, ICR_LOCAL.y, 0))
CITY_END = city_pose(CITY_T1 + 1)[0]

# highway lane change (board oriented along +Y at CITY_END)
HW_T0, HW_T1 = T['hw'] + 0.9, T['hw'] + 3.4


def hw_lateral(t):
    return -3.5 * smooth(ramp(t, HW_T0, HW_T1))  # world -X (car's left)


def hw_beta(t):
    # velocity angle relative to heading (in-phase crab), car's left positive
    dt = 1 / 120
    vy = (hw_lateral(t + dt) - hw_lateral(t - dt)) / (2 * dt)
    return math.atan2(-vy, 12.0)


# --- selector / mode scene geometry ---
CAMB_TGT = Vector((0.0, 0.0, 0.8))
CAMB = dict(az=-35.0, el=12.0, dist=11.5, lens=30.0)


def cam_from(tgt, az, el, dist):
    d = Vector((math.cos(math.radians(el)) * math.cos(math.radians(az)),
                math.cos(math.radians(el)) * math.sin(math.radians(az)),
                math.sin(math.radians(el))))
    return tgt + d * dist


def look_quat(pos, tgt, roll_up=Vector((0, 0, 1))):
    fwd = (tgt - pos).normalized()
    return fwd.to_track_quat('-Z', 'Y')


_cb = cam_from(CAMB_TGT, CAMB['az'], CAMB['el'], CAMB['dist'])
_q = look_quat(_cb, CAMB_TGT)
_fwd = _q @ Vector((0, 0, -1))
_up = _q @ Vector((0, 1, 0))
_right = _q @ Vector((1, 0, 0))
SEL_SC = 0.6
SEL_POS = _cb + _fwd * 3.0 - _up * 0.85
SEL_MAT = Matrix((_fwd, -_right, _up)).transposed()  # local X=fwd, Y=left, Z=up
DIAL_W = SEL_POS + SEL_MAT @ (Vector((-0.16, 0.2, -0.25)) * SEL_SC)
SEL['group'].location = SEL_POS
SEL['group'].rotation_euler = SEL_MAT.to_euler()

# ------------------------------------------------------------------ camera keys
# (t, tx, ty, tz, az, el, dist, lens)
K = [
    (0.0, 0.0, 0.0, 0.55, 25, 14, 8.6, 34),
    (6.9, 0.0, 0.0, 0.55, 75, 16, 8.3, 34),
    (8.4, 0.0, 0.0, 1.1, 95, 20, 13.5, 34),
    (10.2, -0.3, 0.0, 0.5, 125, 46, 9.6, 34),
    (13.1, -0.3, 0.0, 0.5, 150, 44, 9.2, 34),
    (13.7, 0.0, 0.0, 0.95, 268, 10, 11.5, 34),
    (15.0, 0.0, 0.0, 0.95, 272, 12, 11.5, 34),
    (15.8, 0.0, 1.2, 0.4, 330, 38, 12.0, 34),
    (17.5, 0.0, 1.2, 0.4, 352, 40, 11.5, 34),
    (18.4, -0.6, 0.0, 0.62, 140, 36, 4.2, 34),
    (21.2, -0.6, 0.0, 0.62, 160, 32, 4.0, 34),
    (23.4, -0.6, 0.0, 0.62, 170, 30, 4.4, 34),
    (24.4, -0.6, 0.0, 0.55, 112, 18, 5.0, 34),
    (25.3, -0.6, 0.0, 0.55, 100, 18, 5.2, 34),
    (26.2, -0.6, 0.0, 3.40, 92, 6, 4.7, 34),
    (31.2, -0.6, 0.0, 3.40, 88, 6, 4.5, 34),
    (32.3, -0.6, 0.0, 0.55, 205, 36, 4.0, 34),
    (33.6, -0.7, 0.0, 0.50, 220, 33, 3.8, 34),
    (35.3, -1.45, 0.0, 0.42, 228, 26, 3.0, 34),
    (40.4, -1.45, 0.0, 0.42, 240, 24, 2.9, 34),
    (42.3, -1.45, 0.0, 0.42, 245, 26, 3.2, 34),
    (43.6, -0.5, 0.0, 0.40, 215, 50, 8.4, 34),
    (45.0, -0.5, 0.0, 0.40, 205, 48, 8.4, 34),
    (45.6, 1.2, 0.0, 0.75, 270, 7, 12.5, 32),
    (48.3, 1.8, 0.0, 0.75, 270, 7, 12.5, 32),
    (49.6, 6.0, 0.0, 0.0, 180, 89.5, 16.0, 30),
    (51.2, 6.0, 0.0, 0.0, 180, 89.5, 16.0, 30),
    (51.6, 3.0, 0.0, 0.0, 180, 89.5, 10.5, 30),
    (53.0, 3.0, 0.0, 0.0, 180, 89.5, 10.5, 30),
    (53.9, 7.0, 3.6, 0.0, 180, 89.5, 21.0, 30),
    (57.5, 7.0, 3.6, 0.0, 180, 89.5, 21.0, 30),
]


def cam_keys():
    k = list(K)
    hw_tgt = CITY_END
    k.append((58.5, hw_tgt.x, hw_tgt.y + 3, 0.0, 270, 89.5, 19.0, 30))
    k.append((61.4, hw_tgt.x - 3.5, hw_tgt.y + 3, 0.0, 270, 89.5, 19.0, 30))
    # close-up on dial: camera in front of dial looking along selector X
    dial = DIAL_W
    k.append((62.75, dial.x, dial.y, dial.z, None, None, 0.24, 30))  # special: along -fwd
    k.append((64.3, CAMB_TGT.x, CAMB_TGT.y, CAMB_TGT.z, CAMB['az'], CAMB['el'], CAMB['dist'], CAMB['lens']))
    k.append((70.7, CAMB_TGT.x, CAMB_TGT.y, CAMB_TGT.z, CAMB['az'], CAMB['el'], CAMB['dist'], CAMB['lens']))
    k += [
        (71.8, 0.0, 0.0, 0.9, 270, 5, 9.6, 32),
        (76.3, -0.1, 0.0, 0.9, 272, 6, 9.6, 32),
        (77.3, 0.0, 0.0, 0.9, 300, 14, 13.0, 32),
        (78.2, 0.0, 0.0, 0.6, 320, 16, 11.0, 32),
        (81.9, 0.0, 0.0, 0.6, 375, 18, 12.0, 32),
        (84.5, 0.0, 0.0, 0.6, 410, 28, 21.0, 32),
    ]
    return k


KEYS = cam_keys()
_dial_fwd = SEL_MAT @ Vector((1, 0, 0))
_az_d = math.degrees(math.atan2(-_dial_fwd.y, -_dial_fwd.x))
_el_d = math.degrees(math.asin(max(-1, min(1, -_dial_fwd.z))))
KEYS = [(k[0], k[1], k[2], k[3], _az_d if k[4] is None else k[4], _el_d if k[5] is None else k[5], k[6], k[7]) for k in KEYS]
_prev = None
_u = []
for k in KEYS:
    az = k[4]
    if _prev is not None:
        while az - _prev > 180:
            az -= 360
        while az - _prev < -180:
            az += 360
    _u.append((k[0], k[1], k[2], k[3], az, k[5], k[6], k[7]))
    _prev = az
KEYS = _u
KT = np.array([k[0] for k in KEYS])
KV = np.array([k[1:] for k in KEYS], dtype=float)


def pchip_slopes(x, y):
    h = np.diff(x)
    d = np.diff(y) / h
    m = np.zeros_like(y)
    for i in range(1, len(y) - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0
        else:
            w1 = 2 * h[i] + h[i - 1]
            w2 = h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0] = 0
    m[-1] = 0
    return m


SLOPES = np.stack([pchip_slopes(KT, KV[:, j]) for j in range(KV.shape[1])], 1)


def cam_params(t):
    if t <= KT[0]:
        return KV[0]
    if t >= KT[-1]:
        return KV[-1]
    i = int(np.searchsorted(KT, t) - 1)
    h = KT[i + 1] - KT[i]
    s = (t - KT[i]) / h
    h00 = 2 * s ** 3 - 3 * s ** 2 + 1
    h10 = s ** 3 - 2 * s ** 2 + s
    h01 = -2 * s ** 3 + 3 * s ** 2
    h11 = s ** 3 - s ** 2
    return h00 * KV[i] + h10 * h * SLOPES[i] + h01 * KV[i + 1] + h11 * h * SLOPES[i + 1]


def set_camera(t):
    tx, ty, tz, az, el, dist, lens = cam_params(t)
    tgt = Vector((tx, ty, tz))
    pos = cam_from(tgt, az, el, dist)
    cam.location = pos
    if el > 80:
        # top-down: screen-up = direction from camera azimuth toward target
        upv = Vector((-math.cos(math.radians(az)), -math.sin(math.radians(az)), 0))
        fwd = (tgt - pos).normalized()
        right = fwd.cross(upv).normalized()
        upv = right.cross(fwd).normalized()
        m = Matrix((right, upv, -fwd)).transposed()
        cam.rotation_euler = m.to_euler()
    else:
        cam.rotation_euler = look_quat(pos, tgt).to_euler()
    cam.data.lens = lens
    cam.data.shift_y = 0.0
    # gentle framing: subjects a bit lower than center (subtitle space on top)
    cam.data.shift_y = 0.045 if el < 80 else 0.03


# ------------------------------------------------------------------ explode
EXP = {
    'body': (Vector((0, 0, 1.5)), Vector((0.05, 0.10, 0))),
    'cabin': (Vector((0, 0, 2.5)), Vector((-0.08, 0.0, 0.1))),
    'wing': (Vector((-1.0, 0, 2.1)), Vector((0, 0.18, 0))),
    'interior': (Vector((0.35, 0, 0.95)), Vector((0.0, -0.1, 0.12))),
    'engine': (Vector((0.15, 0, 0.55)), Vector((0.1, 0.0, -0.05))),
    'gearbox': (Vector((-1.25, 0, 0.55)), Vector((0.0, -0.15, 0.0))),
}
GROUPS = {'body': P['body'], 'cabin': P['cabin'], 'wing': P['wing'], 'interior': P['interior'],
          'engine': E['group'], 'gearbox': G['group']}
WHEEL_BASE = {n: w['group'].location.copy() for n, w in P['wheels'].items()}


def explode_k(t):
    k = 0.0
    # scene 1 explode / scene 2 reassemble
    if T['explode'] <= t < T['s2'] + 1.0:
        k = back_out(ramp(t, T['explode'], T['explode'] + 0.75), 1.2) * (1 - smooth(ramp(t, T['s2'], T['s2'] + 0.9)))
    # scene 9: quick explode then pop together
    if 76.55 <= t < T['s9'] + 0.8:
        k = smooth(ramp(t, 76.55, 77.05)) * (1 - back_out(ramp(t, T['s9'], T['s9'] + 0.55), 2.2))
    return k


def apply_explode(t):
    k = explode_k(t)
    bob = math.sin(t * 2.3)
    for name, g in GROUPS.items():
        off, rot = EXP[name]
        g.location = off * k + Vector((0, 0, 0.06 * bob * k))
        g.rotation_euler = Euler(tuple(r * k for r in rot))
    for n, w in P['wheels'].items():
        side = 1 if n[1] == 'L' else -1
        fr = 1 if n[0] == 'F' else -1
        w['group'].location = WHEEL_BASE[n] + Vector((0.45 * fr, side * 1.15, 0.25)) * k
        w['group'].rotation_euler = (0, 0, side * 0.25 * k)
    return k


# ------------------------------------------------------------------ boards
BOARD_WIN = {
    'curve': (T['curve'] - 0.15, T['s3'] + 0.25),
    'track': (45.15, 49.0),
    'city': (48.95, T['hw'] + 0.55),
    'highway': (T['hw'] + 0.25, 62.75),
    'strada': (62.75, T['sport'] + 0.2),
    'sport': (T['sport'] + 0.05, T['corsa'] + 0.2),
    'corsa': (T['corsa'] + 0.05, T['s8'] + 0.35),
    'barrio': (78.55, T['capotillo'] + 1.2),
    'open': (T['capotillo'] + 0.35, 99),
}
_scroll_d = {}


def scroll_dist(t):
    # integrate car speed for scrolling boards (cached on grid)
    key = round(t * 120)
    if key in _scroll_d:
        return _scroll_d[key]
    acc = 0.0
    dt = 1 / 120
    for i in range(key):
        tt = i * dt
        acc += board_speed(tt) * dt
    _scroll_d[key] = acc
    return acc


def board_speed(t):
    if 45.40 <= t < 48.0:
        return ACC * run_sim_t(t)
    if 48.0 <= t < 49.4:
        return 27.78 * (1 - smooth(ramp(t, 48.0, 49.4)))
    if T['hw'] <= t < 62.8:
        return 12.0 * smooth(ramp(t, T['hw'], T['hw'] + 0.8))
    if 62.8 <= t < T['s8'] + 0.4:
        return mode_speed(t)
    return 0.0


def board_scale(t, name):
    a, b = BOARD_WIN[name]
    if t < a or t > b:
        return 0.0
    k_in = back_out(ramp(t, a, a + 0.45), 1.3)
    k_out = 1 - smooth(ramp(t, b - 0.35, b))
    return max(0.0, k_in * k_out)


def place_boards(t, carM):
    d = scroll_dist(t)
    for name, bd in B.items():
        g = bd['group']
        sc = board_scale(t, name)
        vis = sc > 0.001
        show(g, vis)
        if not vis:
            continue
        g.scale = (sc, sc, sc)
        if name == 'curve':
            g.location = (0, 0, 0)
            g.rotation_euler = (0, 0, 0)
            ang = curve_angle(t)
            bd['rot'].rotation_euler = (0, 0, -ang)
        elif name == 'track':
            g.location = (0, 0, 0)
        elif name == 'city':
            g.location = CITY_OFF
        elif name == 'highway':
            g.location = CITY_END
            g.rotation_euler = (0, 0, math.pi / 2)
        elif name in ('strada', 'sport', 'corsa'):
            g.location = (0, 0, 0)
        elif name == 'barrio':
            g.location = (0, 0, 0)
            k = 1 - smooth(ramp(t, T['capotillo'] + 0.1, T['capotillo'] + 0.9))
            for i, h in enumerate(bd['houses']):
                kk = back_out(ramp(t, 78.7 + i * 0.05, 79.2 + i * 0.05), 1.5) * k
                h.scale = (1, 1, max(0.001, kk))
        elif name == 'open':
            g.location = (0, 0, 0)
        if 'scroll' in bd:
            for (scn, Pp) in bd['scroll']:
                scn.location = (-(d % Pp), 0, 0)


def curve_angle(t):
    # car travels along the arc (R=9) at ~3.2 m/s -> board rotates under it
    return max(0.0, t - (T['curve'] + 0.3)) * 3.2 / 9.0 if t < T['s3'] + 0.3 else (T['s3'] - T['curve']) * 3.2 / 9.0


# ------------------------------------------------------------------ main pose
WHEEL_SPIN = {}


def wheel_angle(t):
    key = round(t * 120)
    if key in WHEEL_SPIN:
        return WHEEL_SPIN[key]
    # integrate incrementally from nearest cached key
    prev = max([k for k in WHEEL_SPIN.keys() if k <= key], default=0)
    acc = WHEEL_SPIN.get(prev, 0.0)
    dt = 1 / 120
    for i in range(prev, key):
        acc += car_speed(i * dt) / carmod.WHEEL_R * dt
    WHEEL_SPIN[key] = acc
    return acc


CRANK = {}


def crank_angle(t):
    key = round(t * 120)
    if key in CRANK:
        return CRANK[key]
    prev = max([k for k in CRANK.keys() if k <= key], default=0)
    acc = CRANK.get(prev, 0.0)
    dt = 1 / 120
    for i in range(prev, key):
        acc += crank_rate(i * dt) * dt
    CRANK[key] = acc
    return acc


BODY_MATS = ['yellow', 'black', 'headlight', 'taillight', 'exhaust']
CAB_MATS = ['glass']


def body_alpha(t):
    a = 1.0
    # scene 2: x-ray to show engine
    a = lerp(a, 0.13, smooth(ramp(t, T['s2'] + 0.3, T['s2'] + 1.3)))
    a = lerp(a, 1.0, smooth(ramp(t, T['curve'] - 0.2, T['curve'] + 0.3)))
    a = lerp(a, 0.11, smooth(ramp(t, T['s3'] - 0.1, T['s3'] + 0.6)))
    a = lerp(a, 1.0, smooth(ramp(t, 44.95, 45.45)))
    return a


def cabin_vis(t):
    return body_alpha(t) > 0.95


def pose(t):
    anchors = {}
    for ob in ALL_MESH:
        reset_mat(ob)
    for m in MATS.values():
        if 'base' in m.keys():
            m.diffuse_color = m['base']
    k = apply_explode(t)

    # ---------- car root
    carM = Matrix.Identity(4)
    lift = 0.0
    tilt = 0.0
    bal_sc = 0.0
    if T['balance'] - 0.1 <= t < T['curve'] + 0.2:
        bal_sc = back_out(ramp(t, T['balance'], T['balance'] + 0.45), 1.4) * (1 - smooth(ramp(t, T['curve'] - 0.35, T['curve'] + 0.05)))
        lift = 0.75 * smooth(ramp(t, T['balance'] + 0.2, T['balance'] + 0.6)) * (1 - smooth(ramp(t, T['curve'] - 0.45, T['curve'] - 0.1)))
        tt = t - (T['balance'] + 0.6)
        if tt > 0:
            tilt = 0.10 * math.exp(-2.6 * tt) * math.cos(8.0 * tt)
    BAL['group'].scale = (max(bal_sc, 1e-3),) * 3
    BAL['group'].location = (0, 0, 0.95)
    BAL['piv'].rotation_euler = (0, tilt, 0)
    show(BAL['group'], bal_sc > 0.002)
    steer_f = steer_r = 0.0
    steer = None
    if lift > 0:
        carM = Matrix.Translation((0, 0, lift)) @ Matrix.Rotation(tilt, 4, 'Y')
    if 45.40 <= t < 49.5:
        ts = run_sim_t(t)
        dd = 0.5 * ACC * ts * ts if t < 48.0 else 44.6
        cx = 3.0 * (1 - math.exp(-dd / 3.0))
        carM = Matrix.Translation((cx, 0, 0))
    if 48.0 <= t < 49.5:
        carM = Matrix.Translation((3.0, 0, 0))
    if 49.5 <= t < T['hw'] + 0.2:
        pos, yaw, sf, sr = city_pose(t)
        carM = Matrix.Translation(pos) @ Matrix.Rotation(yaw, 4, 'Z')
        steer_f, steer_r = sf, sr
        if T['rear'] - 0.1 <= t < T['city']:
            w = window(t, T['rear'] + 0.2, T['city'] - 0.1, 0.35)
            steer_r = math.radians(14) * math.sin((t - T['rear']) * 4.2) * w
    if T['hw'] + 0.2 <= t < 62.75:
        lat = hw_lateral(t)
        beta = hw_beta(t)
        yaw = math.pi / 2 + 0.25 * beta
        carM = Matrix.Translation(CITY_END + Vector((lat, 0, 0))) @ Matrix.Rotation(yaw, 4, 'Z')
        steer_f = steer_r = 0.75 * beta * 2.2
    if 46.0 > t >= 45.0:
        pass
    # curve scene: steer into curve (left)
    if T['curve'] <= t < T['s3']:
        steer_f = math.atan(2.62 / 9.0) * smooth(ramp(t, T['curve'], T['curve'] + 0.4))
    car.matrix_world = carM

    # ---------- wheels
    wa = wheel_angle(t)
    for n, w in P['wheels'].items():
        w['spin'].rotation_euler = (0, wa, 0)
        w['steer'].rotation_euler = (0, 0, steer_f if n[0] == 'F' else steer_r)

    # ---------- body transparency, cutaways
    a = body_alpha(t)
    for mn in BODY_MATS:
        set_alpha(MATS[mn], a)
    cab_on = a > 0.5 or k > 0.01
    show(P['cabin'], True)
    set_alpha(MATS['glass'], 1.0 if a > 0.95 else max(0.0, (a - 0.11) * 1.0))
    if a < 0.5 and k < 0.01:
        show(P['cabin'], False)
    else:
        show(P['cabin'], True)
    for mn in ('yellow',):
        pass
    # engine cutaway (scene 3-5)
    cut = T['s3'] - 0.1 <= t < 45.2
    for ob in E['banks'] + E['heads'] + [E['plenum']]:
        set_mat(ob, E['M']['engT'] if cut else E['M']['eng'] if ob in E['banks'] else (E['M']['head'] if ob in E['heads'] else E['M']['intake']))
    gcut = T['force'] + 0.3 <= t < 45.2
    set_mat(G['case'], G['M']['caseT'] if gcut else G['M']['case'])
    show(P['interior'], True)

    # ---------- engine + gearbox mechanics
    phi = crank_angle(t)
    mech.pose_engine(E, phi)
    mech.pose_gearbox(G, phi, wa)

    # highlights ------------------------------------------------
    pulse = 0.5 + 0.5 * math.sin(t * 9)
    HL.diffuse_color = hexcol('#fff36b')
    HL2.diffuse_color = hexcol('#fffbe0')
    if T['behind'] - 0.05 <= t < T['curve'] - 0.3:
        hl([E['group']])
    # cylinders light one by one in firing order
    if T['cyl10'] <= t < T['hp'] + 0.3:
        n_lit = int((t - T['cyl10']) / 0.085) + 1
        for i, num in enumerate(mech.FIRING[:min(10, n_lit)]):
            for c in E['cyl']:
                if c['info']['num'] == num:
                    set_mat(c['piston'], HL)
                    set_mat(c['liner'], mat('linerHL', '#fff36b', 0.55))
    if T['air'] <= t < T['air'] + 2.6:
        for ob in descend(P['body']):
            if ob.name.startswith('sideintake'):
                set_mat(ob, HL)
    if T['crank'] - 0.6 <= t < T['force'] + 0.6:
        set_mat(E['crank'], HL)
    # gearbox: gear sweep for "7 cambios", clutches for "doble embrague"
    if T['seven'] <= t < T['dual']:
        i = int((t - T['seven']) / 0.13)
        for gr in G['gears'][:min(7, i + 1)]:
            set_mat(gr['gi'], HL)
            set_mat(gr['go'], HL)
    if T['dual'] <= t < T['s5']:
        swapped = t >= T['parpadeo']
        act, ready = (0, 1) if not swapped else (1, 0)
        g_act, g_ready = (2, 3) if not swapped else (3, 4)
        set_mat(G['clutch'][act], HL)
        rm = mat('readyHL', '#d8ffe2')
        rm.diffuse_color = [lerp(a_, b_, pulse) for a_, b_ in zip(hexcol('#9ff0b6'), hexcol('#fffbe0'))]
        if t >= T['mientras'] - 0.3:
            set_mat(G['clutch'][ready], rm)
            set_mat(G['gears'][g_act]['gi'], HL)
            set_mat(G['gears'][g_act]['go'], HL)
            set_mat(G['gears'][g_ready]['gi'], rm)
            set_mat(G['gears'][g_ready]['go'], rm)
    if T['s5'] + 0.3 <= t < 45.1:
        for n in ('RL', 'RR'):
            w = P['wheels'][n]
            set_mat(w['tire'], HL)
            set_mat(w['rim'], mat('rimHL', '#ffe680'))
        for hs in G['halfshafts']:
            set_mat(hs, HL)
    if T['s8'] + 0.1 <= t < 76.5:
        hl([P['wing']])
    if T['conductos'] - 0.1 <= t < 76.5:
        for ob in descend(P['body']):
            if ob.name.startswith('sideintake') or ob.name.startswith('intakeY'):
                set_mat(ob, HL)
    # scene 9 paint shine
    if T['s9'] + 0.6 <= t < DUR:
        s = 0.5 + 0.5 * math.sin((t - T['s9']) * 2.2)
        base = MATS['yellow']['base']
        MATS['yellow'].diffuse_color = [min(1, c * (1 + 0.22 * s)) for c in base[:3]] + [MATS['yellow'].diffuse_color[3]]

    # ---------- power line
    pw = 0.0
    pts = []
    if T['force'] <= t < 45.1:
        path = mech.resample(mech.power_path(), 0.01)
        prog = smooth(ramp(t, T['force'], T['force'] + 1.6))
        n = max(2, int(len(path) * prog))
        pts = [path[:n]]
        if t >= T['s5']:
            pr2 = smooth(ramp(t, T['s5'], T['s5'] + 0.9))
            for wp in mech.wheel_paths():
                rp = mech.resample(wp, 0.01)
                nn = max(2, int(len(rp) * pr2))
                pts.append(rp[:nn])
    import bmesh as _bm
    bmw = _bm.new()
    for seg in pts:
        if len(seg) >= 2:
            tb = bm_tube_path(seg[::2] if len(seg) > 6 else seg, 0.022, 10)
            me = bpy.data.meshes.new('tmp')
            tb.to_mesh(me)
            tb.free()
            bmw.from_mesh(me)
            bpy.data.meshes.remove(me)
    old = pwr_obj.data
    newm = bpy.data.meshes.new('power')
    bmw.to_mesh(newm)
    bmw.free()
    newm.materials.append(PWR_M)
    pwr_obj.data = newm
    bpy.data.meshes.remove(old)
    pwr_obj.hide_render = len(pts) == 0
    PWR_M.diffuse_color = [lerp(a_, b_, pulse) for a_, b_ in zip(hexcol('#ffd21a'), hexcol('#fff7b0'))]

    # ---------- grip arrows (curve)
    gvis = T['curve'] + 0.5 <= t < T['s3'] - 0.1
    gk = back_out(ramp(t, T['curve'] + 0.5, T['curve'] + 0.9)) * (1 - smooth(ramp(t, T['s3'] - 0.4, T['s3'] - 0.1)))
    for i, (n, w) in enumerate(P['wheels'].items()):
        ob = GRIP[i]
        ob.hide_render = not gvis
        side = 1 if n[1] == 'L' else -1
        base = carM @ Vector((WHEEL_BASE[n].x, 1.08 if side > 0 else -2.42, 0.03))
        # arrow points toward curve centre (+Y, left)
        ob.location = base
        ob.rotation_euler = (0, 0, math.pi / 2)
        ob.scale = (max(gk, 1e-3),) * 3
        if n == 'FL':
            anchors['grip'] = base + Vector((0, 0.9, 0))

    # ---------- intake air arrows (scene 3)
    avis = T['air'] <= t < T['air'] + 2.5
    for i, ob in enumerate(AIRA):
        ob.hide_render = not avis
        if not avis:
            continue
        side = 1 if i % 2 == 0 else -1
        ph = ((t - T['air']) * 0.9 + (i // 2) * 0.2) % 1.0
        p0 = Vector((-0.62, side * 1.9, 0.52))
        p1 = Vector((-0.62, side * 0.95, 0.52))
        p2 = Vector((-0.62, side * 0.10, 0.78))
        if ph < 0.6:
            p = p0.lerp(p1, ph / 0.6)
            dvec = p1 - p0
        else:
            p = p1.lerp(p2, (ph - 0.6) / 0.4)
            dvec = p2 - p1
        ob.location = p
        ob.rotation_mode = 'QUATERNION'
        ob.rotation_quaternion = dvec.normalized().to_track_quat('X', 'Z')
        ob.scale = (1.0,) * 3

    # ---------- callout (single cylinder)
    c_sc = 0.0
    if T['air'] + 1.4 <= t < T['s4'] + 0.5:
        c_sc = back_out(ramp(t, T['air'] + 1.4, T['air'] + 1.9), 1.2) * (1 - smooth(ramp(t, T['s4'] - 0.1, T['s4'] + 0.4)))
    show(CO['group'], c_sc > 0.002)
    CO['group'].location = (-0.6, 0.0, 2.55)
    CO['group'].rotation_euler = (0, 0, math.pi)
    CO['group'].scale = (max(1e-3, c_sc * 0.78),) * 3
    bpy.context.view_layer.update()
    # stroke timeline
    t0 = T['air'] + 1.9  # 25.72
    t_int1 = T['mix'] + 0.7
    t_cmp1 = T['spark'] - 0.02
    t_pow0 = T['push']
    t_pow1 = T['s4'] - 0.1
    if t < t0:
        th = 0.0
    elif t < t_int1:
        th = math.pi * smooth(ramp(t, t0, t_int1))
    elif t < t_cmp1:
        th = math.pi + math.pi * smooth(ramp(t, t_int1, t_cmp1))
    elif t < t_pow0:
        th = 2 * math.pi
    else:
        th = 2 * math.pi + math.pi * smooth(ramp(t, t_pow0, t_pow1)) ** 0.85
    iv = math.sin(math.pi * ramp(t, t0 - 0.1, t_int1 + 0.1)) if t0 - 0.1 <= t < t_int1 + 0.1 else 0.0
    ev = 0.0
    s_p = mech.pose_callout(CO, th, iv, ev)
    cw = CO['group'].matrix_world if c_sc > 0.002 else None
    S.view_layers[0].update() if False else None
    # chamber region (local): crown z = s+0.36? piston body top at s+0.08+0.2
    crown = s_p + 0.08 + 0.2
    head_z = 1.84
    # blue charge dashes and fuel drops
    for i, ob in enumerate(CAIR):
        vis = c_sc > 0.05 and t0 - 0.2 <= t < T['boom'] + 0.1
        ob.hide_render = not vis
        if not vis:
            continue
        rr = random.Random(i)
        ph = rr.random()
        if t < t0 + 0.35 + ph * 0.5:
            # travelling down the intake port
            u = ((t - t0 + 0.2) * 1.1 + ph) % 1.0
            p = Vector((-1.2, 0, 2.33)).lerp(Vector((-0.22, 0, 1.92)), u)
            dv = Vector((1, 0, -0.4))
        else:
            ang = t * (3 + rr.random() * 2) + ph * 6.28
            rad = 0.12 + rr.random() * 0.2
            zz = lerp(crown + 0.04, head_z - 0.04, rr.random())
            p = Vector((rad * math.cos(ang), -0.05 - 0.15 * rr.random(), zz))
            dv = Vector((-math.sin(ang), 0, 0.2))
        ob.location = CO['group'].matrix_world @ p if c_sc > 0 else p
        ob.rotation_mode = 'QUATERNION'
        ob.rotation_quaternion = (CO['group'].matrix_world.to_3x3() @ dv).normalized().to_track_quat('X', 'Z')
        ob.scale = (c_sc * 0.78 * 1.6,) * 3
    for i, ob in enumerate(DROPS):
        vis = c_sc > 0.05 and T['mix'] <= t < T['boom'] + 0.1
        ob.hide_render = not vis
        if not vis:
            continue
        rr = random.Random(100 + i)
        ph = rr.random()
        tt = t - T['mix'] - ph * 0.5
        if tt < 0:
            ob.hide_render = True
            continue
        if tt < 0.45:
            p = Vector((-0.50, 0, 2.18)).lerp(Vector((-0.15, 0, 1.75)), tt / 0.45)
        else:
            ang = t * 3.2 + ph * 6.28
            rad = 0.08 + rr.random() * 0.24
            zz = lerp(crown + 0.05, head_z - 0.05, (rr.random() + 0.1 * math.sin(t * 5 + i)) % 1.0)
            p = Vector((rad * math.cos(ang), -0.1 - 0.12 * rr.random(), zz))
        ob.location = CO['group'].matrix_world @ p
        ob.scale = (c_sc * 0.78 * 1.4,) * 3
    # spark
    svis = c_sc > 0.05 and T['spark'] <= t < T['boom'] + 0.15
    SPARK.hide_render = not svis
    if svis:
        fl = 0.7 + 0.3 * math.sin(t * 60)
        SPARK.location = CO['group'].matrix_world @ Vector((0, -0.3, 1.80))
        SPARK.rotation_euler = (0, t * 4, 0)
        SPARK.scale = (c_sc * 0.78 * fl * 1.2,) * 3
    fvis = c_sc > 0.05 and T['boom'] <= t < t_pow1 + 0.05
    FLASH.hide_render = not fvis
    if fvis:
        g_ = smooth(ramp(t, T['boom'], T['boom'] + 0.35))
        fade = 1 - smooth(ramp(t, t_pow1 - 0.5, t_pow1))
        zc = (crown + head_z) / 2
        hgt = max(0.05, head_z - crown)
        FLASH.location = CO['group'].matrix_world @ Vector((0, -0.42, zc))
        sx = c_sc * 0.78 * (0.3 + 0.42 * g_) * (0.85 + 0.15 * math.sin(t * 40))
        FLASH.scale = (sx * 1.25 * fade + 1e-3, 1, max(1e-3, c_sc * 0.78 * min(hgt / 0.9, 1.0) * 1.0 * g_ * fade))
        FLASH.rotation_euler = (0, 0, 0)
    if c_sc > 0.05:
        anchors['piston_c'] = CO['group'].matrix_world @ Vector((0.0, -0.4, crown - 0.12))
        anchors['plug_c'] = CO['group'].matrix_world @ Vector((0.0, -0.1, 2.3))

    # ---------- aero streamlines (scene 8)
    s_vis = T['s8'] + 0.2 <= t < 76.6
    sk = smooth(ramp(t, T['s8'] + 0.2, T['s8'] + 0.6)) * (1 - smooth(ramp(t, 76.2, 76.6)))
    lines = aero_lines()
    per = len(STREAM) // len(lines)
    for li, (pl, hide_fn) in enumerate(lines):
        L = pl[-1][0]
        for j in range(per):
            ob = STREAM[li * per + j]
            if not s_vis:
                ob.hide_render = True
                continue
            s_ = ((t - T['s8']) * 4.5 + j * L / per) % L
            p, dv = sample_line(pl, s_)
            ob.hide_render = hide_fn(p)
            ob.location = p
            ob.rotation_mode = 'QUATERNION'
            ob.rotation_quaternion = dv.to_track_quat('X', 'Z')
            ob.scale = (max(sk, 1e-3),) * 3
    dvis = T['s8'] + 0.6 <= t < 76.6
    dk = back_out(ramp(t, T['s8'] + 0.6, T['s8'] + 1.0)) * (1 - smooth(ramp(t, 76.2, 76.6)))
    dpos = [(-2.10, -0.9, 1.55), (-2.10, -0.45, 1.55), (-2.10, 0.0, 1.55), (0.3, -1.0, 1.55), (1.6, -1.0, 1.35)]
    for i, ob in enumerate(DOWN):
        ob.hide_render = not dvis
        bob = 0.06 * math.sin(t * 6 + i)
        ob.location = Vector(dpos[i]) + Vector((0, 0, bob + (0.25 if i >= 3 else 0.0)))
        ob.rotation_euler = (0, math.pi / 2, 0)
        sc_ = dk * (1.0 if i < 3 else 0.8)
        ob.scale = (max(sc_, 1e-3),) * 3
    anchors['down'] = Vector((0.3, -1.0, 1.55 + 0.25 - 0.6))

    # ---------- turning ring (city)
    rk = back_out(ramp(t, T['city'] + 1.0, T['city'] + 1.5)) * (1 - smooth(ramp(t, T['hw'] - 0.1, T['hw'] + 0.3)))
    show(RING, rk > 0.002)
    RING.location = CITY_ICR_W + Vector((0, 0, 0.02))
    RING.scale = (max(rk, 1e-3),) * 3

    # ---------- selector
    sel_k = back_out(ramp(t, 61.6, 62.3), 1.2) * (1 - smooth(ramp(t, T['s8'] - 0.2, T['s8'] + 0.3)))
    show(SEL['group'], sel_k > 0.002)
    SEL['group'].scale = (max(sel_k * SEL_SC, 1e-3),) * 3
    knob_ang = 0.0
    for tt_, ang in ((T['strada'], 50), (T['sport'], 0), (T['corsa'], -50)):
        if t >= tt_ - 0.12:
            knob_ang = math.radians(ang) * 1.0
    # smooth snap
    prev = 0.0
    for tt_, ang in ((T['strada'], 50), (T['sport'], 0), (T['corsa'], -50)):
        kk = smooth(ramp(t, tt_ - 0.15, tt_))
        prev = lerp(prev, math.radians(ang), kk)
    SEL['knob'].rotation_euler = (prev, 0, 0)

    # ---------- environment boards
    place_boards(t, carM)

    # ---------- car hidden?  (always visible)
    show(car, True)
    # re-apply cabin & group visibility rules after show(car)
    if a < 0.5 and k < 0.01:
        show(P['cabin'], False)
    pwr_obj.hide_render = len(pts) == 0
    for ob in [o for o in descend(car) if o.name.startswith('cut')]:
        ob.hide_render = True

    # ---------- anchors (world)
    cw = car.matrix_world
    anchors.update({
        'engine': cw @ (E['group'].matrix_local @ Vector((-0.6, 0, 0.82))),
        'engine_side': cw @ (E['group'].matrix_local @ Vector((-0.75, 0.25, 0.62))),
        'balance': BAL['group'].matrix_world @ Vector((0.0, -0.5, -0.5)),
        'v10': cw @ Vector((-0.45, 0.28, 0.75)),
        'turbo': cw @ Vector((-0.95, -0.3, 0.75)),
        'intake_L': cw @ Vector((-0.55, 0.98, 0.52)),
        'crank': cw @ Vector((-0.35, -0.05, mech.CRANK_Z)),
        'gears': cw @ Vector((mech.GEAR_X[4], -0.05, 0.38)),
        'clutch': cw @ Vector((-1.16, 0.0, mech.IN_Z + 0.12)),
        'rear_wheel': cw @ Vector((-1.31, -0.84, 0.70)),
        'wing': cw @ Vector((-2.10, -0.5, 0.98)),
        'duct': cw @ Vector((-0.6, -0.98, 0.52)),
        'car_center': cw @ Vector((0, 0, 0.6)),
    })
    # studio floor shadow footprint (only when no board under the car)
    on_board = any(board_scale(t, n) > 0.2 for n in B)
    foot = [cw @ Vector((x, y, 0)) for x in (-2.3, 2.3) for y in (-1.0, 1.0)]
    return anchors, foot, (0.0 if on_board else 1.0), k


def sample_line(pl, s):
    for i in range(len(pl) - 1):
        if pl[i + 1][0] >= s:
            a, pa = pl[i]
            b, pb = pl[i + 1]
            u = (s - a) / max(1e-6, b - a)
            return pa.lerp(pb, u), (pb - pa).normalized()
    return pl[-1][1], Vector((1, 0, 0))


_AL = None


def aero_lines():
    global _AL
    if _AL is not None:
        return _AL

    def poly(pts):
        out = []
        acc = 0.0
        prev = None
        for p in pts:
            p = Vector(p)
            if prev is not None:
                acc += (p - prev).length
            out.append((acc, p))
            prev = p
        return out

    def body_top(x):
        # approximate roof/body top profile
        import car as C
        if -1.5 <= x <= 1.02:
            return float(np.interp(x, [-1.50, -1.2, -0.8, -0.3, 0.1, 0.45, 0.80, 1.02], [0.90, 0.99, 1.08, 1.145, 1.16, 1.12, 1.0, 0.87]))
        return float(np.interp(x, C.PX, C.PT))

    lines = []
    xs = np.linspace(4.5, -5.5, 70)
    # over the roof
    for off, y in ((0.16, -0.25), (0.42, -0.6)):
        pts = []
        for x in xs:
            z = body_top(min(2.3, max(-2.3, x))) + off if -2.4 < x < 2.4 else 0.55 + off + (0.45 if x < 0 else 0.0)
            if x > 2.3:
                z = lerp(0.62 + off * 0.5, body_top(2.3) + off, smooth((4.5 - x) / 2.2))
            if x < -2.0:
                # deflected upward by the wing
                z = body_top(-2.0) + off + 0.25 * smooth((-2.0 - x) / 1.2) + (0.35 if off < 0.3 else 0.12) * smooth((-2.1 - x) / 2.0)
            pts.append((x, y, z))
        lines.append((poly(pts), lambda p: False))
    # side duct: into side intake, through body, out the back
    pts = [(x, -1.05, 0.50) for x in np.linspace(4.5, -0.35, 30)]
    pts += [(x, -0.99, 0.50) for x in np.linspace(-0.4, -2.2, 18)]
    pts += [(x, -0.99, 0.48) for x in np.linspace(-2.25, -5.5, 25)]
    lines.append((poly(pts), lambda p: -2.2 < p.x < -0.45))
    # front Y-intake duct exiting over the hood
    pts = [(x, -0.62, 0.30) for x in np.linspace(4.5, 2.25, 20)]
    pts += [(2.0, -0.62, 0.45), (1.4, -0.62, 0.78)]
    pts += [(x, -0.62, float(np.interp(x, [-5.5, -2.4, 0.5, 1.2], [1.55, 1.45, 1.25, 0.95]))) for x in np.linspace(1.2, -5.5, 40)]
    lines.append((poly(pts), lambda p: 1.45 < p.x < 2.22))
    # underbody line
    pts = [(x, -0.3, 0.07) for x in np.linspace(4.5, -5.5, 60)]
    lines.append((poly(pts), lambda p: False))
    _AL = lines
    return lines


def project(p):
    co = world_to_camera_view(S, cam, p)
    return [co.x * 1080, (1 - co.y) * 1920, co.z]


# ------------------------------------------------------------------ main
if __name__ == '__main__':
    args = sys.argv[1:]
    f0 = int(args[0]) if args else 0
    f1 = int(args[1]) if len(args) > 1 else NF
    step = int(args[2]) if len(args) > 2 else 1
    outdir = os.environ.get('OUTDIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frames'))
    scale = float(os.environ.get('RES', '1.0'))
    S.render.resolution_percentage = int(scale * 100)
    os.makedirs(outdir, exist_ok=True)
    meta = {}
    times = []
    for f in range(f0, min(f1, NF), step):
        t = f / FPS
        t_a = time.time()
        anchors, foot, studio, k = pose(t)
        set_camera(t)
        bpy.context.view_layer.update()
        pa = {kk: project(v) for kk, v in anchors.items()}
        pf = [project(v) for v in foot]
        meta[f] = dict(a=pa, foot=pf, studio=studio)
        S.render.filepath = os.path.join(outdir, 'f_%05d.png' % f)
        t_r = time.time()
        bpy.ops.render.render(write_still=True)
        print('render', time.time() - t_r)
        times.append(time.time() - t_a)
        print('frame', f, 't=%.2f' % t, '%.2fs' % times[-1], flush=True)
    with open(os.path.join(outdir, 'meta_%05d_%05d.json' % (f0, f1)), 'w') as fh:
        json.dump(meta, fh)
    if times:
        print('avg', sum(times) / len(times))
