# Escena 3D maqueta: cerradura de pines. Render Workbench frame a frame.
import bpy, bmesh, math, json, sys, os, time, random
from mathutils import Vector, Matrix, Euler
from bpy_extras.object_utils import world_to_camera_view
import numpy as np
from scipy.interpolate import PchipInterpolator

FPS = 30
DUR = 59.40
NFR = int(round(DUR * FPS))

# ---------------------------------------------------------------- helpers
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ss(x):
    x = clamp(x); return x * x * (3 - 2 * x)
def sm(x):
    x = clamp(x); return x * x * x * (x * (x * 6 - 15) + 10)
def ramp(t, a, b): return sm((t - a) / (b - a))
def back_out(x, s=1.9):
    x = clamp(x); x -= 1; return 1 + x * x * ((s + 1) * x + s)
def lerp(a, b, k): return a + (b - a) * k

def K(t, ks):
    """keys [(t,v)] -> smootherstep entre claves (para estados)"""
    if t <= ks[0][0]: return ks[0][1]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t <= t1:
            k = sm((t - t0) / (t1 - t0))
            if isinstance(v0, (tuple, list)):
                return tuple(a + (b - a) * k for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * k
    return ks[-1][1]

class P:
    """interpolación pchip (movimiento continuo sin paradas)"""
    def __init__(self, ks):
        ts = [k[0] for k in ks]; vs = np.array([np.atleast_1d(k[1]) for k in ks], float)
        self.t0, self.t1 = ts[0], ts[-1]
        self.f = PchipInterpolator(ts, vs, axis=0)
        self.v0, self.v1 = vs[0], vs[-1]
    def __call__(self, t):
        if t <= self.t0: r = self.v0
        elif t >= self.t1: r = self.v1
        else: r = self.f(t)
        return r if len(r) > 1 else float(r[0])

def s2l(c):
    def f(u): return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), 1.0)

def hexc(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

MATS = {}
def mat(name, hx):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name)
    m.diffuse_color = s2l(hexc(hx)); m.roughness = 1.0; m.metallic = 0.0
    MATS[name] = m; return m

# ---------------------------------------------------------------- reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
coll = scene.collection

def new_obj(name, bm=None, material=None, parent=None, smooth=True, angle=40):
    if bm is not None:
        me = bpy.data.meshes.new(name)
        bm.normal_update()
        bm.to_mesh(me); bm.free()
        if smooth:
            for p in me.polygons: p.use_smooth = True
            try: me.set_sharp_from_angle(angle=math.radians(angle))
            except Exception: pass
        ob = bpy.data.objects.new(name, me)
        if material: me.materials.append(material)
    else:
        ob = bpy.data.objects.new(name, None)
        ob.empty_display_size = 0.3
    coll.objects.link(ob)
    if parent: ob.parent = parent
    return ob

def lathe(pts, segs=48, closed=False, mtx=None):
    bm = bmesh.new()
    rings = []
    for (r, z) in pts:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), z)) for i in range(segs)])
    pairs = list(zip(rings, rings[1:]))
    if closed: pairs.append((rings[-1], rings[0]))
    for a, b in pairs:
        if len(a) == 1 and len(b) == 1: continue
        if len(a) == 1:
            for i in range(segs): bm.faces.new((a[0], b[i], b[(i + 1) % segs]))
        elif len(b) == 1:
            for i in range(segs): bm.faces.new((a[i], b[0], a[(i + 1) % segs]))
        else:
            for i in range(segs): bm.faces.new((a[i], b[i], b[(i + 1) % segs], a[(i + 1) % segs]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if mtx: bmesh.ops.transform(bm, matrix=mtx, verts=bm.verts)
    return bm

def arc(cx, cz, rad, a0, a1, n=4):
    return [(cx + rad * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cz + rad * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]

def rcyl_pts(r, z0, z1, b, b2=None):
    b2 = b if b2 is None else b2
    return [(0, z0)] + arc(r - b, z0 + b, b, -90, 0) + arc(r - b2, z1 - b2, b2, 0, 90) + [(0, z1)]

def rcyl(r, z0, z1, b, segs=48, mtx=None, b2=None):
    return lathe(rcyl_pts(r, z0, z1, b, b2), segs, False, mtx)

def rbox(x0, x1, y0, y1, z0, z1, b=0.1, seg=3):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(x1 - x0, y1 - y0, z1 - z0), verts=bm.verts)
    bmesh.ops.translate(bm, vec=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), verts=bm.verts)
    if b > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=b, segments=seg, profile=0.5, affect='EDGES', clamp_overlap=True)
    return bm

def bm_join(*bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new('tmp'); b.to_mesh(me); b.free()
        out.from_mesh(me); bpy.data.meshes.remove(me)
    return out

ROT_Z2X = Matrix.Rotation(math.pi / 2, 4, 'Y')      # eje Z -> X
ROT_Z2Y = Matrix.Rotation(math.pi / 2, 4, 'X')      # eje Z -> -Y

def tmp_obj(bm, name='tmp'):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob); return ob

def bool_bake(bm_base, ops):
    """ops: lista de (op, bm). devuelve bmesh resultante"""
    base = tmp_obj(bm_base, 'base')
    cutters = []
    for i, (op, b) in enumerate(ops):
        c = tmp_obj(b, 'c%d' % i); cutters.append(c)
        m = base.modifiers.new('b%d' % i, 'BOOLEAN'); m.operation = op; m.object = c; m.solver = 'EXACT'
    dg = bpy.context.evaluated_depsgraph_get()
    ev = base.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    out = bmesh.new(); out.from_mesh(me)
    bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(out, verts=out.verts, dist=1e-4)
    bmesh.ops.holes_fill(out, edges=out.edges, sides=0)
    bmesh.ops.recalc_face_normals(out, faces=out.faces)
    for c in cutters: bpy.data.objects.remove(c)
    bpy.data.objects.remove(base)
    return out

# ---------------------------------------------------------------- materiales
M_BODY = mat('body', '#D9DDE3')
M_CAP = mat('cap', '#B9BEC6')
M_PLUG = mat('plug', '#E6A83A')
M_KEY = mat('key', '#F2B630')
M_KEYG = mat('keygray', '#8E949C')
M_RED = mat('red', '#E0262B')
M_BLUE = mat('blue', '#1E5BE0')
M_SPR = mat('spring', '#34373D')
M_DOOR = mat('door', '#F0CC98')
M_DOOR2 = mat('door2', '#CFA067')
M_HANDLE = mat('handle', '#8F949B')
M_HOLE = mat('hole', '#2A2C31')
M_YEL = mat('yellow', '#FFE81A')
M_CAM = mat('cam', '#9AA0A8')
M_LATCH = mat('latch', '#A9AEB6')

# ---------------------------------------------------------------- geometría cerradura (local)
PX = [-1.7 + 0.85 * i for i in range(5)]       # x de cada fila de pines
H_OK = [0.15, -0.20, 0.25, -0.10, 0.05]          # alturas de corte de la llave correcta
H_BAD = [0.15, 0.05, 0.25, -0.10, 0.05]          # llave equivocada: fila 2 distinta
RED_LEN = [1.0 - h for h in H_OK]                # unión exacta en z=1.0 (línea de corte)
REST = -0.35
SHEAR = 1.0
BLUE_LEN = 0.70
TOPZ = 3.6
LNAT = 2.75
PIN_R = 0.22
KX_IN = -2.68
KEY_TIP = 4.95

# cuerpo
b_cyl = rcyl(1.5, -2.5, 2.5, 0.14, 64, ROT_Z2X)
b_tow = rbox(-2.5, 2.5, -0.75, 0.75, 0.0, TOPZ, 0.14)
ops = [('UNION', b_tow), ('DIFFERENCE', lathe([(0, -2.8), (1.03, -2.8), (1.03, 2.8), (0, 2.8)], 64, False, ROT_Z2X))]
for x in PX:
    ops.append(('DIFFERENCE', lathe([(0, 0.6), (0.25, 0.6), (0.25, TOPZ + 0.5), (0, TOPZ + 0.5)], 32, False, Matrix.Translation((x, 0, 0)))))
body_bm = bool_bake(b_cyl, ops)

# tapa superior
cap_bm = rbox(-2.5, 2.5, -0.75, 0.75, TOPZ + 0.005, TOPZ + 0.26, 0.08)

# cilindro (plug)
p_main = rcyl(1.0, -2.5, 2.5, 0.06, 64, ROT_Z2X)
p_lip = rcyl(1.18, -2.68, -2.48, 0.06, 64, ROT_Z2X)
ops = [('UNION', p_lip), ('DIFFERENCE', rbox(-3.0, 2.32, -0.13, 0.13, -0.78, 0.36, 0.0))]
for x in PX:
    ops.append(('DIFFERENCE', lathe([(0, -0.7), (0.25, -0.7), (0.25, 1.3), (0, 1.3)], 32, False, Matrix.Translation((x, 0, 0)))))
plug_bm = bool_bake(p_main, ops)

# pieza trasera (leva) con brazo hacia abajo
cam_bm = bm_join(rcyl(0.62, 2.52, 2.8, 0.05, 48, ROT_Z2X), rbox(2.54, 2.8, -0.25, 0.25, -1.45, 0.0, 0.06))
# pestillo: barra hacia -y con lengüeta junto al brazo
latch_bm = bm_join(rbox(2.86, 3.3, -3.4, 0.5, -1.7, -1.05, 0.08),
                   rbox(2.5, 2.9, 0.27, 0.5, -1.7, -1.1, 0.04),
                   rbox(2.86, 3.3, -3.75, -3.3, -1.7, -1.05, 0.12))

def key_profile(H):
    U = [x - KX_IN for x in PX]
    pts = [(0.0, 0.12), (0.5, 0.12)]
    for i in range(5):
        pts += [(U[i] - 0.1, H[i]), (U[i] + 0.1, H[i])]
        if i < 4:
            m = (U[i] + U[i + 1]) / 2; pk = min(0.30, max(H[i], H[i + 1]) + 0.14)
            pts += [(m - 0.05, pk), (m + 0.05, pk)]
    pts += [(KEY_TIP - 0.12, -0.38), (KEY_TIP, -0.47)]
    # insertar rampa inicial antes del primer valle
    pts.insert(2, (0.62, 0.30))
    return pts

def prof_eval(pts, u):
    if u < 0 or u > KEY_TIP: return None
    for (u0, z0), (u1, z1) in zip(pts, pts[1:]):
        if u0 <= u <= u1:
            return z0 + (z1 - z0) * (u - u0) / max(1e-9, (u1 - u0))
    return None

def key_bm(H, bow_r=1.25, seed=None):
    top = key_profile(H)
    outline = [(0.0, -0.6), (KEY_TIP - 0.15, -0.6), (KEY_TIP, -0.47)] + list(reversed(top[:-1]))
    # outline: base -> punta -> perfil superior de vuelta al hombro
    outline = [(0.0, -0.6), (KEY_TIP - 0.15, -0.6)] + list(reversed(top))
    bm = bmesh.new()
    fr = [bm.verts.new((u, 0.1, z)) for u, z in outline]
    bk = [bm.verts.new((u, -0.1, z)) for u, z in outline]
    bm.faces.new(fr); bm.faces.new(list(reversed(bk)))
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((fr[i], bk[i], bk[j], fr[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    neck = rbox(-0.55, 0.02, -0.13, 0.13, -0.72, 0.38, 0.05)
    shoulder = rbox(-0.3, 0.02, -0.14, 0.14, -0.75, 0.5, 0.05)
    ring = [(0.32, -0.15)] + arc(bow_r - 0.12, -0.03, 0.12, -90, 0, 3) + arc(bow_r - 0.12, 0.03, 0.12, 0, 90, 3) + [(0.32, 0.15)]
    bow = lathe(ring, 48, True, Matrix.Translation((-0.4 - bow_r, 0, -0.12)) @ ROT_Z2Y)
    return bm_join(bm, neck, shoulder, bow)

def spring_bm(turns=7, R=0.17, wr=0.04, steps_per=20, rs=8):
    bm = bmesh.new()
    N = turns * steps_per
    cz, dz, verts = [], [], []
    rings = []
    for s in range(N + 1):
        a = 2 * math.pi * s / steps_per
        h = -s / N                          # centro en z unitario (0 arriba, -1 abajo)
        c = Vector((R * math.cos(a), R * math.sin(a), 0))
        tng = Vector((-math.sin(a), math.cos(a), 0)).normalized()
        nrm = Vector((math.cos(a), math.sin(a), 0))
        bin_ = tng.cross(nrm)
        ring = []
        for k in range(rs):
            ph = 2 * math.pi * k / rs
            off = nrm * (wr * math.cos(ph)) + bin_ * (wr * math.sin(ph))
            v = bm.verts.new((c.x + off.x, c.y + off.y, 0))
            cz.append(h); dz.append(off.z); ring.append(v)
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(rs):
            bm.faces.new((a[k], a[(k + 1) % rs], b[(k + 1) % rs], b[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, np.array(cz), np.array(dz)

# ---------------------------------------------------------------- objetos
LOCK = new_obj('LockRoot')
CUT = new_obj('Cutter', rbox(-0.5, 0.5, -0.5, 0.5, -0.5, 0.5, 0), None, LOCK, smooth=False)
CUT.hide_render = True; CUT.display_type = 'BOUNDS'

BODY = new_obj('Body', body_bm, M_BODY, LOCK, angle=35)
CAP = new_obj('Cap', cap_bm, M_CAP, LOCK)
PLUGP = new_obj('PlugPivot', None, None, LOCK)
PLUG = new_obj('Plug', plug_bm, M_PLUG, PLUGP, angle=35)
CAM = new_obj('Cam', cam_bm, M_CAM, PLUGP)
LATCH = new_obj('Latch', latch_bm, M_LATCH, LOCK)
SHEARO = new_obj('Shear', rbox(0, 5.0, 0.0, 0.03, -0.045, 0.045, 0.0), M_YEL, LOCK, smooth=False)

REDS, BLUES, SPRINGS = [], [], []
for i, x in enumerate(PX):
    REDS.append(new_obj('Red%d' % i, rcyl(PIN_R, 0.0, RED_LEN[i], 0.09, 32, None, 0.04), M_RED, PLUGP))
    BLUES.append(new_obj('Blue%d' % i, rcyl(PIN_R, 0.0, BLUE_LEN, 0.04, 32), M_BLUE, LOCK))
    sb, cz, dz = spring_bm()
    so = new_obj('Spring%d' % i, sb, M_SPR, LOCK, angle=80)
    so['cz'] = 0
    SPRINGS.append((so, cz, dz))

KEYG = new_obj('KeyGold', key_bm(H_OK), M_KEY, PLUGP, angle=35)
KEYB = new_obj('KeyGray', key_bm(H_BAD), M_KEYG, PLUGP, angle=35)
PROF_OK = key_profile(H_OK)
PROF_BAD = key_profile(H_BAD)

# llaves de colores (escena 9)
random.seed(7)
ROW_COLS = ['#E0262B', '#1E5BE0', '#2BB24C', '#8A3FD1', '#F07A1A']
ROWKEYS = []
for i, c in enumerate(ROW_COLS):
    H = [random.choice([-0.25, -0.15, -0.05, 0.05, 0.15, 0.25]) for _ in range(5)]
    ROWKEYS.append(new_obj('RowKey%d' % i, key_bm(H, 1.1), mat('rk%d' % i, c), None, angle=35))

# cortes en vivo
CUT_TARGETS = [BODY, CAP, PLUG, KEYG, KEYB]
for o in CUT_TARGETS:
    m = o.modifiers.new('cut', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = CUT
    m.solver = 'EXACT'; m.use_self = True; m.use_hole_tolerant = True

# puerta
DOORP = new_obj('DoorPivot')
DOOR_W0, DOOR_W1, DOOR_T, DOOR_H = -4.0, 4.0, 1.0, 18.0
door_bm = bm_join(rbox(DOOR_W0, DOOR_W1, -DOOR_T, DOOR_T, 0, DOOR_H, 0.25),
                  rbox(-3.2, 1.9, -DOOR_T - 0.12, -DOOR_T + 0.1, 10.6, 16.8, 0.1),
                  rbox(-3.2, 1.9, -DOOR_T - 0.12, -DOOR_T + 0.1, 1.2, 6.6, 0.1))
DOOR = new_obj('Door', door_bm, M_DOOR, DOORP, angle=35)
DOOR.location = (-DOOR_W0, 0, 0)      # pivote en la bisagra
LX, LZ = 3.0, 9.0
hole_bm = bm_join(lathe([(0, 0), (0.49, 0), (0.49, 0.01), (0, 0.01)], 48, False, Matrix.Translation((LX, -DOOR_T - 0.002, LZ)) @ ROT_Z2Y),
                  rbox(LX - 0.26, LX + 0.26, -DOOR_T - 0.012, -DOOR_T - 0.002, LZ, LZ + 1.18, 0.0))
HOLE = new_obj('Hole', hole_bm, M_HOLE, DOOR, smooth=False)
HOLE.location = (0, 0, 0)
handle_bm = bm_join(rcyl(0.55, 0, 0.25, 0.08, 48, Matrix.Translation((LX, -DOOR_T, 7.2)) @ Matrix.Rotation(math.pi / 2, 4, 'X')),
                    rcyl(0.18, 0, 0.55, 0.05, 32, Matrix.Translation((LX, -DOOR_T - 0.2, 7.2)) @ Matrix.Rotation(math.pi / 2, 4, 'X')),
                    rbox(1.7, LX + 0.15, -DOOR_T - 0.95, -DOOR_T - 0.6, 7.0, 7.4, 0.15))
HANDLE = new_obj('Handle', handle_bm, M_HANDLE, DOOR)
hinge_bm = bm_join(rcyl(0.16, 2.5, 4.0, 0.05, 24, Matrix.Translation((DOOR_W0, DOOR_T, 0))),
                   rcyl(0.16, 13.5, 15.0, 0.05, 24, Matrix.Translation((DOOR_W0, DOOR_T, 0))))
HINGE = new_obj('Hinge', hinge_bm, M_HANDLE, DOOR)

# cámara
camd = bpy.data.cameras.new('Cam'); camd.lens = 50; camd.sensor_width = 36; camd.sensor_fit = 'HORIZONTAL'
camd.clip_start = 0.1; camd.clip_end = 400
CAMO = bpy.data.objects.new('Camera', camd); coll.objects.link(CAMO); scene.camera = CAMO

# ---------------------------------------------------------------- render setup
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1080; scene.render.resolution_y = 1920
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.fps = FPS
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
sh = scene.display.shading
sh.light = 'STUDIO'
sh.color_type = 'MATERIAL'
sh.show_cavity = True
sh.cavity_type = 'BOTH'
sh.cavity_ridge_factor = 0.6; sh.cavity_valley_factor = 1.0
sh.curvature_ridge_factor = 0.4; sh.curvature_valley_factor = 0.6
sh.show_shadows = False
sh.shadow_intensity = 0.35
sh.show_object_outline = True
sh.object_outline_color = (0, 0, 0)
sh.show_specular_highlight = False
scene.display.light_direction = (0.35, -0.45, 0.82)
scene.display.shadow_shift = 0.1
scene.display.shadow_focus = 0.2
scene.view_settings.view_transform = 'Standard'
try: scene.display.render_aa = os.environ.get('AA', '8')
except Exception: pass

# ================================================================ TIMELINE
F = (0.0, -4.0, 9.0)            # posición flotante de la cerradura
DOOR_HIDE = -32.0

attach = lambda t: K(t, [(0, 1), (2.8, 1), (4.3, 0), (42.8, 0), (44.0, 1), (46.0, 1), (47.2, 0), (56.6, 0), (57.7, 1)])
door_z = lambda t: K(t, [(0, 0), (3.6, 0), (4.8, DOOR_HIDE), (42.3, DOOR_HIDE), (43.6, 0), (46.3, 0), (47.5, DOOR_HIDE), (56.2, DOOR_HIDE), (57.3, 0)])
door_open = lambda t: K(t, [(0, 0), (44.2, 0), (45.35, 72), (45.4, 72), (46.2, 0)])
lock_lift = lambda t: K(t, [(0, 0), (51.5, 0), (52.3, 22), (54.9, 22), (55.0, 0)])   # sube fuera de cuadro
turn_extra = lambda t: (K(t, [(0, 0), (4.4, 0), (5.0, 1), (6.1, 1), (7.0, 0)]) * 28 * math.sin((t - 4.4) * 0.9)) + K(t, [(0, 0), (4.4, 0), (7.1, 0)])

explode = lambda t: K(t, [(0, 0), (4.45, 0), (5.35, 1), (6.15, 1), (7.25, 0)])
pins_away = lambda t, d: K(t, [(0, 0), (5.35, 0), (6.15, 0), (7.25, 1), (12.65 + d, 1), (13.35 + d, 0)])
cut = lambda t: K(t, [(0, 0), (7.3, 0), (8.6, 1), (42.6, 1), (43.1, 0), (46.7, 0), (47.5, 1), (51.6, 1), (52.1, 0)])
shear_on = lambda t: K(t, [(0, 0), (20.25, 0), (20.95, 1), (38.8, 1), (39.2, 0), (47.4, 0), (47.9, 1), (51.5, 1), (51.7, 0)])

def plug_rot(t):
    r = K(t, [(0, 0), (9.0, 0), (9.9, 32), (10.2, 32), (11.1, 0), (40.5, 0), (42.5, 90), (45.3, 90), (45.8, 0)])
    for t0 in (24.95, 50.05):        # intento de giro bloqueado: choca y vibra
        if t0 <= t <= t0 + 1.0:
            x = t - t0
            r += 4.0 * ss(x / 0.12) * (1 - ss((x - 0.55) / 0.4)) + 1.6 * math.sin(x * 70) * math.exp(-x * 4) * ss(x / 0.1)
    return r

KEYG_X = P([(25.6, KX_IN - 13.0), (26.9, KX_IN - 5.15), (32.35, KX_IN - 0.06), (32.75, KX_IN)])
KEYG_OUT = P([(45.75, KX_IN), (46.35, KX_IN - 4.0)])
KEYB_X = P([(46.5, KX_IN - 13.0), (47.35, KX_IN - 5.15), (48.75, KX_IN - 0.06), (49.0, KX_IN)])
KEYB_OUT = P([(51.45, KX_IN), (52.1, KX_IN - 8.0)])

def keyg_state(t):
    if t < 25.6 or t > 46.35: return None
    if t <= 45.75: return float(KEYG_X(t))
    return float(KEYG_OUT(t))
def keyb_state(t):
    if t < 46.5 or t > 52.1: return None
    if t <= 51.45: return float(KEYB_X(t))
    return float(KEYB_OUT(t))

def pin_bump(t):        # resortes comprimen y empujan (escena 3)
    return K(t, [(0, 0), (18.55, 0), (18.95, 0.32), (19.15, 0.32), (19.45, -0.02), (19.6, 0.0)])

def row_pulse(t, i):
    c = 14.15 + 0.3 * i
    x = (t - c) / 0.28
    return math.exp(-x * x * 2.5) if -2 < x < 2 else 0.0

latch_ret = lambda t: 1.05 * ss((plug_rot(t) - 25) / 60) if t > 30 else 0.0

# rearmado (escena 9): piezas dispersas que vuelan a su sitio
def reassemble(t, d):
    return 1 - back_out((t - (54.95 + d)) / 0.5, 1.6) if t > 51.0 else 0.0
SCAT = {}
random.seed(3)
def scat_vec(name):
    if name not in SCAT:
        a = random.uniform(0, 2 * math.pi)
        SCAT[name] = Vector((math.cos(a) * 14, random.uniform(-2, 2), math.sin(a) * 10 + 4))
    return SCAT[name]

# offsets de explosión (marco local de la cerradura)
EX = {'body': Vector((0, 0, 0)), 'cap': Vector((0, 0, 6.7)), 'spring': Vector((0, 0, 6.3)), 'blue': Vector((0, 0, 5.2)),
      'red': Vector((0, 0, 4.4)), 'plug': Vector((0, 0, -3.7)), 'cam': Vector((0, 0, -1.6)), 'latch': Vector((0, 0.4, -7.0))}
AWAY = Vector((0, 0, 16.0))
SPIN = {'body': 14, 'cap': -20, 'plug': 22, 'cam': -30, 'latch': 18}

# llaves de colores
def rowkey_state(t, i):
    a = back_out((t - (51.95 + 0.28 * i)) / 0.45, 1.7)
    leave = ramp(t, 54.95 + 0.06 * i, 55.55 + 0.06 * i)
    return a, leave

# cámara: claves (t, objetivo, distancia, azimut, elevación)
CAMK = [
    (0.0, (0.0, 0.0, 9.6), 31.0, -34, 10),
    (1.6, (1.2, -0.5, 9.4), 22.0, -18, 9),
    (2.9, (2.4, -0.8, 9.6), 15.0, -6, 6),
    (4.2, (0.6, -3.6, 10.0), 14.5, 2, 8),
    (5.3, (0.0, -4.0, 10.6), 23.0, 12, 10),
    (6.2, (0.0, -4.0, 10.5), 23.5, 16, 12),
    (7.3, (0.0, -4.0, 9.9), 14.5, 10, 9),
    (8.6, (0.0, -4.0, 9.9), 12.2, 4, 6),
    (10.5, (0.0, -4.0, 9.8), 12.0, -6, 8),
    (12.5, (0.0, -4.0, 10.6), 13.5, -10, 10),
    (14.0, (0.0, -4.0, 10.6), 11.8, -4, 6),
    (16.2, (-0.2, -4.0, 10.6), 10.6, 3, 4),
    (18.4, (-0.2, -4.0, 10.7), 10.4, 8, 5),
    (20.3, (0.0, -4.0, 10.4), 10.0, 4, 4),
    (23.0, (0.0, -4.0, 10.3), 9.6, -3, 3),
    (25.6, (0.0, -4.0, 10.1), 10.0, -6, 4),
    (27.5, (1.6, -4.0, 9.8), 13.8, -14, 9),
    (30.0, (0.8, -4.0, 9.8), 12.6, -10, 7),
    (32.6, (0.2, -4.0, 10.0), 10.6, -4, 4),
    (35.5, (0.0, -4.0, 10.2), 8.6, 1, 2),
    (38.4, (0.0, -4.0, 10.2), 8.4, 5, 3),
    (40.6, (-1.0, -3.4, 9.2), 15.0, -115, 24),
    (42.5, (-1.2, -3.0, 9.2), 15.5, -138, 28),
    (44.0, (1.0, -1.5, 9.4), 27.0, -40, 14),
    (45.3, (0.8, -1.0, 9.4), 30.0, -18, 10),
    (46.4, (0.6, -3.0, 9.6), 16.0, -4, 8),
    (47.6, (0.0, -4.0, 10.0), 12.0, -10, 7),
    (49.0, (0.0, -4.0, 10.1), 10.2, -4, 4),
    (51.3, (0.0, -4.0, 10.1), 10.0, 4, 4),
    (52.4, (0.0, -4.0, 10.6), 17.0, 0, 4),
    (54.8, (0.0, -4.0, 10.6), 17.5, 6, 6),
    (56.4, (0.0, -4.0, 10.4), 15.0, -4, 8),
    (57.6, (1.5, -1.5, 9.6), 26.0, -12, 9),
    (59.4, (0.5, 0.0, 9.6), 34.0, -34, 12),
]
CAM_T = P([(k[0], k[1]) for k in CAMK])
CAM_D = P([(k[0], k[2]) for k in CAMK])
CAM_A = P([(k[0], k[3]) for k in CAMK])
CAM_E = P([(k[0], k[4]) for k in CAMK])

# ================================================================ estado por fotograma
def apply_state(t):
    out = {}
    # puerta
    dz = door_z(t); op = door_open(t)
    DOORP.location = (DOOR_W0, 0, dz)
    DOORP.rotation_euler = (0, 0, math.radians(op))
    # pose cerradura
    b = attach(t)
    piv = Vector((DOOR_W0, 0, dz))
    rel = Vector((LX - DOOR_W0, -0.27, LZ))
    R = Matrix.Rotation(math.radians(op), 3, 'Z')
    a_loc = piv + R @ rel; a_rot = 90 + op; a_s = 0.30
    f_loc = Vector(F) + Vector((0, 0, lock_lift(t))); f_rot = 180 + turn_extra(t); f_s = 1.0
    loc = a_loc.lerp(f_loc, 1 - b) + Vector((0, 0, math.sin(math.pi * b) * 1.2))
    LOCK.location = loc
    LOCK.rotation_euler = (0, 0, math.radians(lerp(f_rot, a_rot, b)))
    s = lerp(f_s, a_s, b); LOCK.scale = (s, s, s)

    e = explode(t)
    def off(name, d=0.0):
        v = EX[name] * e
        if name in ('red', 'blue', 'spring', 'cap'):
            v = v + AWAY * pins_away(t, {'red': 0.0, 'blue': 0.18, 'spring': 0.36, 'cap': 0.62}[name] + 0.07 * d)
        r = reassemble(t, {'body': 0, 'plug': 0.12, 'cam': 0.2, 'latch': 0.25, 'red': 0.38, 'blue': 0.5, 'spring': 0.62, 'cap': 0.8}[name] + d * 0.08)
        if r != 0:
            sv = scat_vec(name + str(d))
            if name in ('red', 'blue', 'spring', 'cap'):
                v = v + Vector((sv.x * r * abs(r), 0, abs(sv.z) * r + 6 * r))
            else:
                v = v + sv * r
        return v
    spin_t = e * (t - 4.4)
    def spin(name): return math.radians(SPIN[name] * spin_t * 0.35)

    BODY.location = off('body'); BODY.rotation_euler = (0, 0, spin('body'))
    CAP.location = off('cap'); CAP.rotation_euler = (0, 0, spin('cap'))
    po = off('plug')
    PLUGP.location = po
    th = plug_rot(t)
    PLUGP.rotation_euler = (math.radians(th), 0, 0)
    PLUG.rotation_euler = (0, 0, spin('plug'))
    CAM.location = off('cam')
    CAM.rotation_euler = (0, 0, spin('cam'))
    LATCH.location = off('latch') + Vector((0, latch_ret(t), 0)); LATCH.rotation_euler = (0, 0, spin('latch'))

    # llaves
    kg = keyg_state(t); kb = keyb_state(t)
    for ob, kx in ((KEYG, kg), (KEYB, kb)):
        if kx is None:
            ob.hide_render = True; ob.location = (0, 0, -50)
        else:
            ob.hide_render = False; ob.location = (kx, 0, 0)
    # desaparición de la llave dorada al salir (escena 8): encoge
    if kg is not None and t > 45.75:
        k = 1 - ramp(t, 46.0, 46.35); KEYG.scale = (k, k, k)
    else:
        KEYG.scale = (1, 1, 1)
    if kb is not None and t > 51.45:
        k = 1 - ramp(t, 51.8, 52.1); KEYB.scale = (k, k, k)
    else:
        KEYB.scale = (1, 1, 1)

    bump = pin_bump(t)
    pins = []
    for i, x in enumerate(PX):
        bot = REST
        for kx, prof in ((kg, PROF_OK), (kb, PROF_BAD)):
            if kx is not None:
                z = prof_eval(prof, x - kx)
                if z is not None: bot = max(bot, z)
        bot += bump
        rtop = bot + RED_LEN[i]
        pulse = 1 + 0.10 * row_pulse(t, i)
        ro = off('red', i)
        REDS[i].location = Vector((x, 0, bot)) + ro - po
        REDS[i].scale = (pulse, pulse, 1)
        bo = off('blue', i)
        BLUES[i].location = Vector((x, 0, rtop)) + bo
        BLUES[i].scale = (pulse, pulse, 1)
        so_, cz, dzz = SPRINGS[i]
        sp = off('spring', i)
        top = TOPZ + sp.z
        blue_top = rtop + BLUE_LEN + bo.z
        L = min(LNAT, top - blue_top)
        so_.location = Vector((x, 0, TOPZ)) + sp
        so_.scale = (pulse, pulse, 1)
        co = np.zeros(len(cz) * 3)
        so_.data.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3); co[:, 2] = cz * L + dzz
        so_.data.vertices.foreach_set('co', co.ravel()); so_.data.update()
        pins.append(dict(bot=bot, rtop=rtop, L=L))

    # corte
    c = cut(t)
    for o in CUT_TARGETS:
        o.modifiers['cut'].show_render = c > 0.001
        o.modifiers['cut'].show_viewport = c > 0.001
    x0 = -2.72; x1 = x0 + 6.3 * c
    CUT.location = ((x0 + x1) / 2, 6.0137, 1.0); CUT.scale = (max(0.001, x1 - x0), 12.0, 16.0)
    so = shear_on(t)
    SHEARO.hide_render = so < 0.01
    SHEARO.location = (-2.5, 0.0, SHEAR)
    SHEARO.scale = (max(0.001, so), 1, 1.0 + 0.0)

    # llaves de colores
    for i, ob in enumerate(ROWKEYS):
        a, lv = rowkey_state(t, i)
        if a <= 0.001 or lv >= 0.999:
            ob.hide_render = True; continue
        ob.hide_render = False
        side = 1 if i % 2 == 0 else -1
        y = 13.7 - i * 1.75
        ob.location = (-2.2 + side * lv * 16, -4.0, y)
        ob.rotation_euler = (0, math.radians(4 * math.sin(t * 1.3 + i)), math.radians(8 * math.sin(t * 0.9 + i * 1.7)))
        sc = max(0.001, a) * 0.85; ob.scale = (sc, sc, sc)

    # cámara
    T = Vector(CAM_T(t)); D = float(CAM_D(t)); A = math.radians(float(CAM_A(t)) + 1.5 * math.sin(t * 0.37)); E = math.radians(float(CAM_E(t)))
    pos = T + D * Vector((math.sin(A) * math.cos(E), -math.cos(A) * math.cos(E), math.sin(E)))
    CAMO.location = pos
    CAMO.rotation_euler = (T - pos).to_track_quat('-Z', 'Y').to_euler()
    return pins

def project(co):
    v = world_to_camera_view(scene, CAMO, co)
    return [round(v.x * 1080, 1), round((1 - v.y) * 1920, 1), round(v.z, 3)]

def anchors(t, pins):
    vl = bpy.context.view_layer; vl.update()
    A = {}
    W = lambda ob, p: ob.matrix_world @ Vector(p)
    A['plug'] = project(W(PLUGP, (-1.25, 0.0, -0.55)))
    A['plugface'] = project(W(PLUGP, (0.4, 0.0, -0.85)))
    A['body'] = project(W(LOCK, (-1.27, 0.0, 2.75)))
    A['bodyfront'] = project(W(LOCK, (1.25, 0.0, -1.2)))
    for i, x in enumerate(PX):
        A['red%d' % i] = project(W(REDS[i], (0, 0, RED_LEN[i] * 0.5)))
        A['redbot%d' % i] = project(W(REDS[i], (0, 0, 0)))
        A['junc%d' % i] = project(W(REDS[i], (0, 0, RED_LEN[i])))
        A['blue%d' % i] = project(W(BLUES[i], (0, 0, BLUE_LEN * 0.5)))
        A['bluetop%d' % i] = project(W(BLUES[i], (0, 0, BLUE_LEN)))
        A['bluebot%d' % i] = project(W(BLUES[i], (0, 0, 0)))
        A['spring%d' % i] = project(W(SPRINGS[i][0], (0, 0, -pins[i]['L'] * 0.5)))
        A['springtop%d' % i] = project(W(SPRINGS[i][0], (0, 0, 0)))
        A['pinr%d' % i] = project(W(BLUES[i], (PIN_R, 0, 0)))
        A['shear%d' % i] = project(W(LOCK, (x, 0, SHEAR)))
    A['shearL'] = project(W(LOCK, (-2.5, 0, SHEAR)))
    A['shearR'] = project(W(LOCK, (2.5, 0, SHEAR)))
    A['keyteeth'] = project(W(KEYG, (3.0 - 0.85 * 0, 0, 0.3)))
    A['latch'] = project(W(LATCH, (3.08, -3.55, -1.05)))
    A['cam'] = project(W(CAM, (2.8, 0.0, -0.9)))
    A['center'] = project(W(LOCK, (0, 0, 1.0)))
    A['lockbot'] = project(W(LOCK, (0, 0, -1.5)))
    A['lockbotL'] = project(W(LOCK, (-2.7, 0, -1.5)))
    A['lockbotR'] = project(W(LOCK, (2.7, 0, -1.5)))
    A['doorbotL'] = project(DOOR.matrix_world @ Vector((DOOR_W0, 0, 0)))
    A['doorbotR'] = project(DOOR.matrix_world @ Vector((DOOR_W1, 0, 0)))
    A['doorbotC'] = project(DOOR.matrix_world @ Vector((0, 0, 0)))
    A['x_lock'] = A['shear2']
    A['scale_px'] = round(math.dist(A['shearL'][:2], A['shearR'][:2]) / 5.0, 2)
    A['pins'] = [[round(p['bot'], 3), round(p['rtop'], 3)] for p in pins]
    A['door_z'] = door_z(t); A['attach'] = attach(t); A['cut'] = cut(t)
    return A

# ================================================================ main
if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    mode = argv[0] if argv else 'test'
    outdir = argv[1] if len(argv) > 1 else '/tmp/claude-0/w/frames'
    os.makedirs(outdir, exist_ok=True)
    if mode == 'frames':
        frames = [int(v) for v in argv[2].split(',')] if ',' in argv[2] else list(range(int(argv[2]), int(argv[3]), int(argv[4]) if len(argv) > 4 else 1))
        pct = int(os.environ.get('PCT', '100'))
        scene.render.resolution_percentage = pct
        render = os.environ.get('NORENDER') is None
        allA = {}
        for f in frames:
            t = f / FPS
            t0 = time.time()
            pins = apply_state(t)
            allA[f] = anchors(t, pins)
            if render:
                scene.render.filepath = os.path.join(outdir, 'f%05d.png' % f)
                bpy.ops.render.render(write_still=True)
            print('FRAME', f, round(time.time() - t0, 2), flush=True)
        with open(os.path.join(outdir, 'anch_%05d_%05d.json' % (frames[0], frames[-1])), 'w') as fh:
            json.dump(allA, fh)
