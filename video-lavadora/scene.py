# Escena 3D procedural de la lavadora (Blender 4.0, motor Workbench)
# Uso: blender -b --factory-startup -P scene.py -- START END OUTDIR
import bpy, bmesh, math, json, os, sys, random, time
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
DUR = 72.672653
NFR = int(math.ceil(DUR * FPS))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
F0 = int(argv[0]) if len(argv) > 0 else 0
F1 = int(argv[1]) if len(argv) > 1 else NFR
OUT = argv[2] if len(argv) > 2 else '/tmp/frames'
LIST = [int(x) for x in argv[3].split(',')] if len(argv) > 3 else None
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- utilidades
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def sstep(a, b, x):
    u = clamp((x - a) / (b - a)) if b != a else (1.0 if x >= b else 0.0)
    return u * u * (3 - 2 * u)
def lerp(a, b, u): return a + (b - a) * u
def lerpv(a, b, u): return tuple(lerp(x, y, u) for x, y in zip(a, b))
def win(t, a, b, f=0.2):  # ventana suave 0..1..0
    return sstep(a - f, a, t) * (1 - sstep(b, b + f, t))

for o in list(bpy.data.objects): bpy.data.objects.remove(o)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.render.resolution_percentage = 100
sc.render.film_transparent = True
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'
sc.render.image_settings.compression = 10
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'MATERIAL'
sh.show_shadows = True
sh.shadow_intensity = 0.35
sh.show_cavity = True
sh.cavity_type = 'BOTH'
sh.show_specular_highlight = False
sc.display.render_aa = 'FXAA'
sc.view_settings.view_transform = 'Standard'
sc.view_settings.exposure = 0.55
sc.eevee.taa_render_samples = 8
sc.render.use_freestyle = True
sc.render.line_thickness_mode = 'ABSOLUTE'
sc.render.line_thickness = 2.2
fs = sc.view_layers[0].freestyle_settings
fs.crease_angle = math.radians(130)
fs.use_culling = True
noline = bpy.data.collections.new('NOLINE'); sc.collection.children.link(noline)
ls = fs.linesets[0]
ls.select_by_visibility = True
ls.select_by_edge_types = True
ls.select_silhouette = True; ls.select_border = True; ls.select_crease = True
ls.select_external_contour = True
ls.select_by_collection = True; ls.collection = noline; ls.collection_negation = 'EXCLUSIVE'
ls.linestyle.color = (0.02, 0.02, 0.03)
ls.linestyle.thickness = 2.2

MATS = {}
def mat_for(obj, rgb, alpha=1.0):
    m = bpy.data.materials.new(obj.name + '_m')
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], alpha)
    if alpha < 1: m.blend_method = 'BLEND'
    obj.data.materials.clear(); obj.data.materials.append(m)
    MATS[obj.name] = (m, tuple(rgb), alpha)
    return m

def set_rgb(name, rgb, alpha=None):
    m, base, a0 = MATS[name]
    a = a0 if alpha is None else alpha
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], a)

def mesh_obj(name, verts, faces, rgb, parent=None, alpha=1.0, smooth=False, nl=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(name, me)
    (noline if nl else sc.collection).objects.link(ob)
    if parent: ob.parent = parent
    if smooth:
        for p in me.polygons: p.use_smooth = True
        me.use_auto_smooth = True; me.auto_smooth_angle = math.radians(45)
    mat_for(ob, rgb, alpha)
    return ob

def bm_obj(name, bm, rgb, parent=None, alpha=1.0, smooth=False, nl=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    (noline if nl else sc.collection).objects.link(ob)
    if parent: ob.parent = parent
    if smooth:
        for p in me.polygons: p.use_smooth = True
        me.use_auto_smooth = True; me.auto_smooth_angle = math.radians(45)
    mat_for(ob, rgb, alpha)
    return ob

def empty(name, parent=None, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); sc.collection.objects.link(e)
    e.parent = parent; e.location = loc
    return e

def rbox(name, size, loc, rgb, parent=None, bev=0.015, seg=3, alpha=1.0, nl=False):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    if bev > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bev, segments=seg, affect='EDGES', profile=0.5)
    ob = bm_obj(name, bm, rgb, parent, alpha, smooth=True, nl=nl)
    ob.location = loc
    return ob

def cyl_y(name, r, y0, y1, rgb, parent=None, n=48, loc=(0, 0, 0), bev=0.0, nl=False, alpha=1.0):
    """cilindro con eje Y"""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=n, radius1=r, radius2=r, depth=abs(y1 - y0))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, (y0 + y1) / 2, 0))
    if bev > 0:
        sel = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > 0.8]
        bmesh.ops.bevel(bm, geom=sel, offset=bev, segments=2, affect='EDGES', profile=0.5)
    ob = bm_obj(name, bm, rgb, parent, alpha, smooth=True, nl=nl)
    ob.location = loc
    return ob

def cyl_z(name, r, h, loc, rgb, parent=None, n=32, r2=None, nl=False):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=n, radius1=r, radius2=(r if r2 is None else r2), depth=h)
    ob = bm_obj(name, bm, rgb, parent, smooth=True, nl=nl)
    ob.location = loc
    return ob

def cyl_x(name, r, h, loc, rgb, parent=None, n=32):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=n, radius1=r, radius2=r, depth=h)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, 'Y'))
    ob = bm_obj(name, bm, rgb, parent, smooth=True)
    ob.location = loc
    return ob

def shell_y(name, r_in, r_out, y0, y1, rgb, parent=None, n=64, back=None, a0=0.0, a1=2 * math.pi):
    """tubo cilindrico con eje Y; back = radio de tapa trasera (o None)"""
    full = abs(a1 - a0 - 2 * math.pi) < 1e-6
    m = n if full else n + 1
    V = []; F = []
    for i in range(m):
        a = a0 + (a1 - a0) * i / n
        c, s = math.cos(a), math.sin(a)
        V += [(r_out * c, y0, r_out * s), (r_out * c, y1, r_out * s), (r_in * c, y1, r_in * s), (r_in * c, y0, r_in * s)]
    rng = range(n) if full else range(n)
    for i in rng:
        j = (i + 1) % m
        a, b = 4 * i, 4 * j
        F += [(a, b, b + 1, a + 1), (a + 1, b + 1, b + 2, a + 2), (a + 2, b + 2, b + 3, a + 3), (a + 3, b + 3, b, a)]
    if not full:
        F += [(0, 1, 2, 3), (4 * n + 3, 4 * n + 2, 4 * n + 1, 4 * n)]
    if back is not None:
        k = len(V)
        for i in range(n):
            a = a0 + (a1 - a0) * i / n
            V.append((r_out * math.cos(a), y1, r_out * math.sin(a)))
        F.append(tuple(range(k, k + n)))
    return mesh_obj(name, V, F, rgb, parent, smooth=True)

def poly_extrude(name, pts, th, rgb, parent=None, scale=1.0, nl=False):
    n = len(pts)
    V = [(x * scale, -th / 2, z * scale) for x, z in pts] + [(x * scale, th / 2, z * scale) for x, z in pts]
    F = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        F.append((i, j, n + j, n + i))
    return mesh_obj(name, V, F, rgb, parent, nl=nl)

def disc_y(name, r, y, rgb, parent=None, n=24, nl=False, alpha=1.0, th=0.0):
    V = [(r * math.cos(2 * math.pi * i / n), y, r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    F = [tuple(range(n))]
    if th > 0:
        V += [(x, y + th, z) for x, y_, z in V]
        F = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return mesh_obj(name, V, F, rgb, parent, nl=nl, alpha=alpha)

def curve_obj(name, pts, r, rgb, parent=None, nl=False):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts): p.co = (c[0], c[1], c[2], 1)
    cu.bevel_depth = r; cu.bevel_resolution = 3; cu.use_fill_caps = True
    ob = bpy.data.objects.new(name, cu)
    (noline if nl else sc.collection).objects.link(ob)
    if parent: ob.parent = parent
    m = bpy.data.materials.new(name + '_m'); m.diffuse_color = (*rgb, 1)
    cu.materials.append(m); MATS[name] = (m, tuple(rgb), 1.0)
    return ob

def smooth_path(ctrl, n=12):
    """Catmull-Rom sobre puntos de control"""
    P = [Vector(c) for c in ctrl]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            u = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    out.append(P[-2])
    return [tuple(v) for v in out]

# ---------------------------------------------------------------- colores
WHITE = (0.93, 0.94, 0.96)
PANEL = (0.95, 0.95, 0.97)
GRAYL = (0.78, 0.8, 0.84)
TUBC = (0.58, 0.64, 0.9)
DRUMC = (0.93, 0.94, 0.97)
DARK = (0.18, 0.2, 0.25)
YEL = (1.0, 0.8, 0.05)
WATER = (0.45, 0.75, 1.0)
DIRTY = (0.48, 0.4, 0.3)
BLUE_T = (0.25, 0.55, 0.95)

CZ = 0.45  # altura del eje del tambor
W2, D2, H = 0.33, 0.31, 0.88
R_TUB_IN, R_TUB_OUT = 0.29, 0.305
TY0, TY1 = -0.23, 0.245
R_DRUM = 0.22
DY0, DY1 = -0.19, 0.19

ROOT = empty('ROOT')
TUBG = empty('TUBG', ROOT, (0, 0, CZ))  # grupo suspendido (tina + tambor + motor)

# base
rbox('BASE', (0.66, 0.64, 0.03), (0, 0, 0.015), (0.45, 0.48, 0.55), ROOT, bev=0.008)
for sx in (-1, 1):
    for sy in (-1, 1):
        cyl_z('PATA%d%d' % (sx, sy), 0.025, 0.03, (sx * 0.28, sy * 0.26, -0.005), DARK, ROOT, n=16)

# tina (no gira) - abierta al frente (vista en corte)
TUB = shell_y('TUB', R_TUB_IN, R_TUB_OUT, TY0, TY1, TUBC, TUBG, n=64, back=True)
# tambor (gira)
DRUM = empty('DRUM', TUBG)
DRUMS = shell_y('DRUMSHELL', R_DRUM - 0.008, R_DRUM, DY0, DY1, DRUMC, DRUM, n=64, back=True)
DLIP = shell_y('DRUMLIP', R_DRUM - 0.025, R_DRUM + 0.002, DY0 - 0.012, DY0 + 0.004, (0.8, 0.83, 0.88), DRUM, n=64)
# costillas en el fondo del tambor (para ver el giro)
for k in range(3):
    a = k * 2 * math.pi / 3
    o = rbox('RIB%d' % k, (0.19, 0.012, 0.035), (0.095 * math.cos(a), DY1 - 0.012, 0.095 * math.sin(a)), (0.55, 0.62, 0.75), DRUM, bev=0.006, seg=2)
    o.rotation_euler = (0, -a, 0)
cyl_y('HUB', 0.04, DY1 - 0.02, DY1 - 0.004, (0.55, 0.62, 0.75), DRUM, n=24)
# paletas
PADDLES = []
for k in range(3):
    a = math.pi / 2 + k * 2 * math.pi / 3
    o = rbox('PADDLE%d' % k, (0.05, DY1 - DY0 - 0.03, 0.04), (0, 0, 0), (0.6, 0.68, 0.8), DRUM, bev=0.012)
    o.location = ((R_DRUM - 0.025) * math.cos(a), 0, (R_DRUM - 0.025) * math.sin(a))
    o.rotation_euler = (0, -(a - math.pi / 2), 0)
    PADDLES.append(o)
# agujeritos (puntos oscuros, sin contorno)
V = []; F = []
def add_dot(c, nrm, r=0.008, n=8):
    nrm = Vector(nrm).normalized()
    t1 = nrm.orthogonal().normalized(); t2 = nrm.cross(t1)
    k = len(V)
    for i in range(n):
        a = 2 * math.pi * i / n
        p = Vector(c) + (t1 * math.cos(a) + t2 * math.sin(a)) * r
        V.append(tuple(p))
    F.append(tuple(range(k, k + n)))
for row in range(5):
    y = DY0 + 0.05 + row * (DY1 - DY0 - 0.1) / 4
    for i in range(22):
        a = 2 * math.pi * (i + 0.5 * (row % 2)) / 22
        rr = R_DRUM - 0.0095
        add_dot((rr * math.cos(a), y, rr * math.sin(a)), (-math.cos(a), 0, -math.sin(a)))
for ring, cnt in ((0.13, 14), (0.18, 20)):
    for i in range(cnt):
        a = 2 * math.pi * (i + 0.5) / cnt
        add_dot((ring * math.cos(a), DY1 - 0.0085, ring * math.sin(a)), (0, -1, 0), r=0.007)
HOLES = mesh_obj('HOLES', V, F, (0.25, 0.28, 0.35), DRUM, nl=True)

# poleas y correa (atras) + motor
PULLEY = empty('PULLEY', TUBG)
cyl_y('PULLEYD', 0.24, TY1 + 0.015, TY1 + 0.035, (0.7, 0.72, 0.76), PULLEY, n=64)
for k in range(3):
    a = k * 2 * math.pi / 3
    o = rbox('SPOKE%d' % k, (0.2, 0.012, 0.04), (0.1 * math.cos(a), TY1 + 0.04, 0.1 * math.sin(a)), (0.4, 0.43, 0.5), PULLEY, bev=0.006, seg=2)
    o.rotation_euler = (0, -a, 0)
cyl_y('SHAFT', 0.03, TY1, TY1 + 0.05, DARK, PULLEY, n=20)
MZ = -CZ + 0.085
MOTOR = cyl_y('MOTOR', 0.06, 0.02, 0.22, (0.2, 0.4, 0.85), TUBG, n=32, loc=(0.0, 0, MZ), bev=0.01)
for k in range(5):
    cyl_y('MOTRING%d' % k, 0.062, 0.05 + k * 0.03, 0.06 + k * 0.03, (0.14, 0.3, 0.68), MOTOR, n=32)
MPUL = empty('MPUL', TUBG, (0.0, 0, MZ))
cyl_y('MPULD', 0.03, TY1 + 0.015, TY1 + 0.035, (0.7, 0.72, 0.76), MPUL, n=24)
rbox('MPULMARK', (0.04, 0.012, 0.01), (0.0, TY1 + 0.04, 0), (0.4, 0.43, 0.5), MPUL, bev=0.003, seg=1)
cyl_y('MSHAFT', 0.012, 0.2, TY1 + 0.03, DARK, MPUL, n=12)
rbox('MBRACKET', (0.05, 0.06, 0.06), (0.0, 0.13, -R_TUB_OUT + 0.01), (0.4, 0.43, 0.5), TUBG, bev=0.006, seg=2)

def belt_loop(r1, c1, r2, c2, n=160):
    pts = []
    for i in range(240):
        a = 2 * math.pi * i / 240
        pts.append((c1[0] + r1 * math.cos(a), c1[1] + r1 * math.sin(a)))
        pts.append((c2[0] + r2 * math.cos(a), c2[1] + r2 * math.sin(a)))
    pts = sorted(set(pts))
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo = []; up = []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    hull = lo[:-1] + up[:-1]
    # empezar en el punto mas alto
    k = max(range(len(hull)), key=lambda i: hull[i][1]); hull = hull[k:] + hull[:k]
    L = [0]
    for i in range(1, len(hull) + 1):
        a, b = hull[i - 1], hull[i % len(hull)]
        L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    res = []; j = 0
    for i in range(n):
        s = L[-1] * i / n
        while L[j + 1] < s: j += 1
        u = (s - L[j]) / (L[j + 1] - L[j] + 1e-12)
        a, b = hull[j], hull[(j + 1) % len(hull)]
        res.append((lerp(a[0], b[0], u), lerp(a[1], b[1], u)))
    return res
inner = belt_loop(0.24, (0, 0), 0.03, (0, MZ))
outer = belt_loop(0.254, (0, 0), 0.044, (0, MZ))
V = []; F = []; n = len(inner)
yb0, yb1 = TY1 + 0.018, TY1 + 0.032
for (xi, zi), (xo, zo) in zip(inner, outer):
    V += [(xi, yb0, zi), (xo, yb0, zo), (xo, yb1, zo), (xi, yb1, zi)]
for i in range(n):
    j = (i + 1) % n
    a, b = 4 * i, 4 * j
    F += [(a, b, b + 1, a + 1), (a + 1, b + 1, b + 2, a + 2), (a + 2, b + 2, b + 3, a + 3), (a + 3, b + 3, b, a)]
BELT = mesh_obj('BELT', V, F, (0.12, 0.12, 0.14), TUBG)

# bloque de concreto (contrapeso)
CONC = rbox('CONCRETE', (0.3, 0.09, 0.075), (0.05, -0.15, R_TUB_OUT - 0.005), (0.58, 0.58, 0.6), TUBG, bev=0.01)

# agua dentro de la tina (malla dinamica)
WAT = mesh_obj('WATER', [(0, 0, 0)] * 3, [(0, 1, 2)], WATER, TUBG, alpha=0.62)
def water_mesh(level, R=R_TUB_IN - 0.004, y0=-0.17, y1=TY1 - 0.01, n=40):
    me = WAT.data
    me.clear_geometry()
    if level <= -R + 0.003:
        WAT.hide_render = True; return
    WAT.hide_render = False
    h = min(level, R - 0.001)
    a0 = math.asin(h / R)
    pts = []
    for i in range(n + 1):
        a = (math.pi - a0) + (2 * math.pi + a0 - (math.pi - a0)) * i / n
        pts.append((R * math.cos(a), R * math.sin(a)))
    m = len(pts)
    Vv = [(x, y0, z) for x, z in pts] + [(x, y1, z) for x, z in pts]
    Ff = [tuple(range(m)), tuple(range(2 * m - 1, m - 1, -1))]
    for i in range(m):
        j = (i + 1) % m
        Ff.append((j, i, m + i, m + j))
    me.from_pydata(Vv, [], Ff); me.update()
    me.materials.append(MATS['WATER'][0])

# burbujas de jabon (planas, de caricatura)
random.seed(4)
BUBBLES = []
for i in range(14):
    r = random.uniform(0.012, 0.03)
    b = disc_y('BUB%d' % i, r, 0, (0.92, 0.97, 1.0), TUBG, n=20)
    hl = disc_y('BUBH%d' % i, r * 0.32, -0.001, (1, 1, 1), b, n=10, nl=True)
    hl.location = (-r * 0.35, 0, r * 0.35)
    BUBBLES.append((b, r, random.uniform(-0.24, 0.24), random.uniform(0, 1), random.uniform(0.6, 1.4)))

# ropa de caricatura
SHIRT = [(-0.18, 0.5), (-0.5, 0.38), (-0.66, 0.1), (-0.42, 0.0), (-0.34, 0.16), (-0.34, -0.5), (0.34, -0.5), (0.34, 0.16), (0.42, 0.0), (0.66, 0.1), (0.5, 0.38), (0.18, 0.5), (0.0, 0.38)]
SOCK = [(-0.2, 0.5), (0.2, 0.5), (0.2, -0.12), (0.5, -0.22), (0.58, -0.36), (0.5, -0.5), (-0.12, -0.5), (-0.2, -0.38)]
TOWEL = [(-0.5, 0.33), (0.5, 0.33), (0.5, -0.33), (-0.5, -0.33)]
CLOTHES = []
spec = [('SHIRT', (0.95, 0.2, 0.25), 0.13), ('SOCK', (0.6, 0.3, 0.9), 0.09), ('TOWEL', (0.1, 0.75, 0.7), 0.15),
        ('SHIRT', (0.2, 0.75, 0.3), 0.12), ('SOCK', (1.0, 0.45, 0.7), 0.09), ('SHIRT', (1.0, 0.55, 0.1), 0.12),
        ('SHIRT', (0.2, 0.45, 0.95), 0.11)]
random.seed(7)
for i, (kind, col, s) in enumerate(spec):
    pts = {'SHIRT': SHIRT, 'SOCK': SOCK, 'TOWEL': TOWEL}[kind]
    ob = poly_extrude('CL%d' % i, pts, 0.018, col, TUBG, scale=s)
    if kind == 'TOWEL':
        for k, zz in enumerate((-0.03, 0.03)):
            st = rbox('CLS%d_%d' % (i, k), (s * 0.98, 0.022, 0.012), (0, 0, zz), (1, 1, 1), ob, bev=0.0)
    if kind == 'SHIRT':
        st = rbox('CLS%d' % i, (s * 0.66, 0.022, 0.014), (0, 0, -s * 0.2), (1, 1, 1), ob, bev=0.0)
    CLOTHES.append(dict(ob=ob, s=s, rest=math.radians(-90 + (i - 3) * 13 + random.uniform(-4, 4)),
                        rr=0.14 + random.uniform(-0.03, 0.03), y=-0.1 + 0.03 * (i % 4) + random.uniform(0, 0.02),
                        off=random.uniform(0, 1), spin=random.uniform(-1, 1), rot0=random.uniform(-0.6, 0.6),
                        wall=random.uniform(0, 2 * math.pi)))
# ropa extra para la escena "demasiado lleno"
EXTRA = []
random.seed(11)
cols = [(0.95, 0.2, 0.25), (0.2, 0.75, 0.3), (0.6, 0.3, 0.9), (1.0, 0.55, 0.1), (0.1, 0.75, 0.7), (0.2, 0.45, 0.95), (1.0, 0.45, 0.7)]
k = 0
for ring, cnt in ((0.0, 1), (0.08, 6), (0.155, 10)):
    for j in range(cnt):
        a = 2 * math.pi * j / max(cnt, 1) + ring * 3
        kind = [SHIRT, SOCK, TOWEL][k % 3]
        ob = poly_extrude('EX%d' % k, kind, 0.018, cols[k % 7], TUBG, scale=0.11)
        EXTRA.append((ob, (ring * math.cos(a), -0.13 + 0.004 * (k % 5), ring * math.sin(a)), random.uniform(-1.5, 1.5)))
        k += 1

# manchas de suciedad
STAINS = []
random.seed(3)
for i in range(6):
    pts = []
    for j in range(9):
        a = 2 * math.pi * j / 9
        rr = 0.5 + 0.18 * math.sin(3 * a + i) + 0.1 * math.cos(5 * a)
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    ob = poly_extrude('STAIN%d' % i, pts, 0.004, (0.45, 0.3, 0.15), TUBG, scale=0.035)
    STAINS.append(dict(ob=ob, cl=i % 7, off=(random.uniform(-0.03, 0.03), random.uniform(-0.03, 0.03)),
                       v=(random.uniform(-0.05, 0.05), random.uniform(0.03, 0.08))))

# gotas del centrifugado
DROPS = []
random.seed(5)
for i in range(36):
    ob = disc_y('DROP%d' % i, 0.011, 0, (0.4, 0.7, 1.0), TUBG, n=12)
    DROPS.append(dict(ob=ob, a=random.uniform(0, 2 * math.pi), ph=random.uniform(0, 1), y=random.uniform(-0.17, -0.15)))

# flechas curvas planas (giro)
def arrow_mesh(name, R, w, a_from, a_to, y, rgb, parent, th=0.012, head=2.2):
    n = 24; Vv = []; Ff = []
    for i in range(n + 1):
        a = lerp(a_from, a_to, i / n)
        for rr in (R - w / 2, R + w / 2):
            Vv.append((rr * math.cos(a), y, rr * math.sin(a)))
    for i in range(n):
        Ff.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    # punta
    sgn = 1 if a_to > a_from else -1
    k = len(Vv)
    a = a_to
    Vv += [((R - w * head / 2) * math.cos(a), y, (R - w * head / 2) * math.sin(a)),
           ((R + w * head / 2) * math.cos(a), y, (R + w * head / 2) * math.sin(a)),
           (R * math.cos(a + sgn * 0.28), y, R * math.sin(a + sgn * 0.28))]
    Ff.append((k, k + 1, k + 2))
    # extruir
    m = len(Vv)
    Vv2 = Vv + [(x, y + th, z) for x, _, z in Vv]
    Ff2 = list(Ff) + [tuple(reversed([i + m for i in f])) for f in Ff]
    # bordes
    bound = {}
    for f in Ff:
        for i in range(len(f)):
            e = (f[i], f[(i + 1) % len(f)])
            key = tuple(sorted(e))
            bound[key] = None if key in bound else e
    for e in bound.values():
        if e: Ff2.append((e[1], e[0], e[0] + m, e[1] + m))
    return mesh_obj(name, Vv2, Ff2, rgb, parent)

ARROWS = empty('ARROWS', TUBG)
ARR_F = empty('ARR_F', ARROWS)
arrow_mesh('ARF1', 0.355, 0.035, math.radians(140), math.radians(40), -0.3, (1.0, 0.42, 0.08), ARR_F)
arrow_mesh('ARF2', 0.355, 0.035, math.radians(-40), math.radians(-140), -0.3, (1.0, 0.42, 0.08), ARR_F)
ARR_B = empty('ARR_B', ARROWS)
arrow_mesh('ARB1', 0.3, 0.032, math.radians(140), math.radians(40), TY1 + 0.08, (1.0, 0.42, 0.08), ARR_B)
arrow_mesh('ARB2', 0.3, 0.032, math.radians(-40), math.radians(-140), TY1 + 0.08, (1.0, 0.42, 0.08), ARR_B)
# lineas de velocidad
SPEED = empty('SPEED', TUBG)
for k in range(6):
    a = k * 2 * math.pi / 6
    R = 0.34 + 0.025 * (k % 2)
    arrow_mesh('SPL%d' % k, R, 0.014, a, a - math.radians(50), -0.31, (0.98, 0.98, 1.0), SPEED, head=1.0)

# gabinete (piezas que se desarman)
def panel_with_hole(name, w, h, th, hole_r, hole_z, rgb):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * w, v.co.y * th, v.co.z * h))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.01, segments=2, affect='EDGES', profile=0.5)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    cut = bpy.data.meshes.new(name + 'cut')
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=hole_r, radius2=hole_r, depth=0.2)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, hole_z)); bm.to_mesh(cut); bm.free()
    co = bpy.data.objects.new(name + 'cut', cut); sc.collection.objects.link(co)
    md = ob.modifiers.new('b', 'BOOLEAN'); md.object = co; md.operation = 'DIFFERENCE'
    bpy.context.view_layer.objects.active = ob
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear(); ob.data = me2
    bpy.data.objects.remove(co)
    for p in me2.polygons: p.use_smooth = True
    me2.use_auto_smooth = True; me2.auto_smooth_angle = math.radians(40)
    mat_for(ob, rgb)
    return ob

PARTS = []  # (obj, base_loc, dir)
fp = panel_with_hole('FRONT', 2 * W2, H - 0.04, 0.02, 0.215, CZ - (H / 2 + 0.02), PANEL)
fp.parent = ROOT; fp.location = (0, -D2, H / 2 + 0.02)
PARTS.append((fp, Vector(fp.location), Vector((0, -1, 0.15))))
DOOR = empty('DOOR', ROOT, (0, -D2 - 0.03, CZ))
bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=0.235, radius2=0.235, depth=0.035)
bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
bmesh.ops.bevel(bm, geom=[e for e in bm.edges if e.calc_face_angle(0) > 0.8], offset=0.012, segments=2, affect='EDGES', profile=0.5)
dr = bm_obj('DOORRING', bm, (0.85, 0.87, 0.9), DOOR, smooth=True)
dw = disc_y('DOORWIN', 0.17, -0.019, (0.55, 0.72, 0.9), DOOR, n=48)
dw2 = disc_y('DOORWIN2', 0.12, -0.0195, (0.65, 0.8, 0.95), DOOR, n=48, nl=True)
rbox('HANDLE', (0.04, 0.03, 0.1), (0.2, -0.03, 0), (0.7, 0.72, 0.76), DOOR, bev=0.01)
PARTS.append((DOOR, Vector(DOOR.location), Vector((0.25, -1.2, 0.0))))
top = rbox('TOP', (2 * W2 + 0.01, 2 * D2 + 0.01, 0.03), (0, 0, H + 0.015), PANEL, ROOT, bev=0.012)
PARTS.append((top, Vector(top.location), Vector((0, 0, 1))))
for sx, nm in ((-1, 'LEFT'), (1, 'RIGHT')):
    o = rbox(nm, (0.02, 2 * D2, H - 0.04), (sx * (W2 - 0.01), 0, H / 2 + 0.01), WHITE, ROOT, bev=0.008)
    PARTS.append((o, Vector(o.location), Vector((sx, 0, 0.05))))
bk = rbox('BACK', (2 * W2, 0.02, H - 0.04), (0, D2 - 0.01, H / 2 + 0.01), WHITE, ROOT, bev=0.008)
PARTS.append((bk, Vector(bk.location), Vector((0, 1, 0.1))))
# panel de control (sin marca: solo perilla y botones lisos)
knob = cyl_y('KNOB', 0.035, -D2 - 0.035, -D2 - 0.005, (0.75, 0.77, 0.82), fp, n=32, loc=(0.18, D2, H - 0.1 - (H / 2 + 0.02)))
for i in range(2):
    rbox('BTN%d' % i, (0.035, 0.014, 0.022), (0.04 + i * 0.05, -0.012, H - 0.1 - (H / 2 + 0.02)), (0.6, 0.85, 0.75) if i == 0 else (0.9, 0.6, 0.55), fp, bev=0.005, seg=2)

# dosificador (cajon del detergente) - se queda
DISP = rbox('DISPENSER', (0.18, 0.2, 0.06), (-0.18, -0.2, H - 0.1), (0.85, 0.87, 0.9), ROOT, bev=0.008)
DRAWER = empty('DRAWERG', ROOT, (-0.18, -D2 - 0.01, H - 0.1))
# cajon abierto arriba (5 caras) para ver adentro
dw_, dd_, dh_ = 0.17, 0.12, 0.055
V = [(-dw_ / 2, 0, -dh_ / 2), (dw_ / 2, 0, -dh_ / 2), (dw_ / 2, dd_, -dh_ / 2), (-dw_ / 2, dd_, -dh_ / 2),
     (-dw_ / 2, 0, dh_ / 2), (dw_ / 2, 0, dh_ / 2), (dw_ / 2, dd_, dh_ / 2), (-dw_ / 2, dd_, dh_ / 2)]
F = [(0, 3, 2, 1), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
DRW = mesh_obj('DRAWER', V, F, (0.88, 0.9, 0.93), DRAWER)
rbox('DRAWERFRONT', (0.185, 0.016, 0.065), (0, -0.006, 0), (0.92, 0.93, 0.95), DRAWER, bev=0.006, seg=2)
rbox('DRAWERGRIP', (0.07, 0.008, 0.014), (0, -0.016, -0.012), (0.7, 0.72, 0.76), DRAWER, bev=0.003, seg=1)
DET = rbox('DETERG', (0.09, 0.07, 0.03), (0.0, 0.065, -0.012), (0.6, 0.35, 0.95), DRAWER, bev=0.012)
DRWAT = rbox('DRWATER', (0.155, 0.105, 0.03), (0.0, 0.062, -0.012), WATER, DRAWER, bev=0.004, seg=1)

# valvula de entrada (arriba atras)
VALVE = rbox('VALVE', (0.07, 0.06, 0.06), (0.18, 0.24, H - 0.08), (1.0, 0.5, 0.15), ROOT, bev=0.012)
VKNOB = empty('VKNOBG', VALVE, (0, 0, 0.03))
vk = rbox('VKNOB', (0.07, 0.016, 0.016), (0.0, 0, 0.018), (0.85, 0.25, 0.2), VKNOB, bev=0.006, seg=2)
cyl_z('VSTEM', 0.008, 0.02, (0, 0, 0.008), DARK, VKNOB, n=12)
INLET_P = [(0.18, 0.27, H - 0.08), (0.18, 0.4, H - 0.08), (0.18, 0.55, H - 0.14), (0.18, 0.7, H - 0.3)]
TUBE_A_P = smooth_path([(0.18, 0.21, H - 0.08), (0.1, 0.05, H - 0.075), (-0.12, -0.05, H - 0.075), (-0.18, -0.09, H - 0.09)], 10)
TUBE_B_P = smooth_path([(-0.18, -0.2, H - 0.135), (-0.18, -0.15, H - 0.16), (-0.17, -0.1, 0.71)], 8)
for nm, P in (('INLET', INLET_P), ('TUBEA', TUBE_A_P), ('TUBEB', TUBE_B_P)):
    curve_obj(nm, P, 0.014, (0.86, 0.88, 0.92), ROOT)
WCORES = {}
for nm, P in (('WINLET', INLET_P), ('WTUBEA', TUBE_A_P), ('WTUBEB', TUBE_B_P)):
    c = curve_obj(nm, P, 0.017, BLUE_T, ROOT)
    c.data.bevel_factor_mapping_end = 'SPLINE'
    WCORES[nm] = c

# sensor de nivel (cajita + tubo fino)
SX, SY = 0.285, 0.31
SENS = rbox('SENSOR', (0.06, 0.05, 0.05), (SX, SY, H - 0.13), (0.62, 0.35, 0.9), ROOT, bev=0.01)
STUBE = cyl_z('STUBE', 0.013, (H - 0.155) - 0.13, (SX, SY, 0.13 + ((H - 0.155) - 0.13) / 2), (0.92, 0.94, 0.98), ROOT, n=20)
mat_for(STUBE, (0.92, 0.94, 0.98), 0.4)
SCOL = cyl_z('SCOL', 0.009, 1.0, (SX, SY, 0), WATER, ROOT, n=16)
curve_obj('SHOSE', smooth_path([(0.05, 0.18, 0.15), (0.2, 0.3, 0.12), (SX, SY, 0.13)], 8), 0.01, (0.86, 0.88, 0.92), ROOT)
LEVEL_Z = CZ - 0.105  # nivel justo de lavado (mundo)
MARK = cyl_z('MARK', 0.017, 0.006, (SX, SY, LEVEL_Z), (0.95, 0.1, 0.1), ROOT, n=20)

# bomba de desague + manguera
PUMP = empty('PUMPG', ROOT, (-0.17, -0.16, 0.085))
pb = cyl_y('PUMP', 0.055, -0.04, 0.05, (0.15, 0.72, 0.4), PUMP, n=32, bev=0.01)
cyl_y('PUMPCAP', 0.035, -0.06, -0.035, (0.1, 0.5, 0.3), PUMP, n=24)
curve_obj('PHOSE_IN', smooth_path([(-0.05, -0.1, 0.15), (-0.12, -0.12, 0.15), (-0.17, -0.15, 0.14)], 8), 0.016, (0.3, 0.32, 0.36), ROOT)
DRAIN_P = smooth_path([(-0.2, -0.14, 0.08), (-0.34, -0.1, 0.1), (-0.37, -0.02, 0.4), (-0.4, 0.0, 0.62), (-0.52, 0.0, 0.66), (-0.6, 0.0, 0.55)], 10)
curve_obj('DHOSE', DRAIN_P, 0.017, (0.3, 0.32, 0.36), ROOT)
WDRAIN = curve_obj('WDRAIN', DRAIN_P, 0.02, DIRTY, ROOT); WDRAIN.data.bevel_factor_mapping_end = 'SPLINE'
WCORES['WDRAIN'] = WDRAIN
WPIN = curve_obj('WPIN', smooth_path([(-0.05, -0.1, 0.15), (-0.12, -0.12, 0.15), (-0.17, -0.15, 0.14)], 8), 0.019, DIRTY, ROOT)
WPIN.data.bevel_factor_mapping_end = 'SPLINE'
OUTDROPS = []
for i in range(7):
    OUTDROPS.append(disc_y('ODROP%d' % i, 0.014, 0, DIRTY, ROOT, n=12, th=0.01))
INDROPS = []
for i in range(5):
    INDROPS.append(disc_y('IDROP%d' % i, 0.012, 0, WATER, ROOT, n=12, th=0.01))

# resortes, amortiguadores y barra superior
TOPBAR = rbox('TOPBAR', (2 * W2 - 0.04, 0.05, 0.03), (0, 0.05, H - 0.02), (0.55, 0.58, 0.65), ROOT, bev=0.008)
SPRINGS = []
for sx in (-1, 1):
    pts = []
    turns = 7
    for i in range(turns * 16 + 1):
        a = 2 * math.pi * i / 16
        pts.append((0.022 * math.cos(a), 0.022 * math.sin(a), -i / (turns * 16)))
    sp = curve_obj('SPRING%d' % (sx > 0), pts, 0.0045, (0.75, 0.78, 0.85), ROOT)
    sp.location = (sx * 0.17, 0.05, H - 0.035)
    SPRINGS.append(sp)
DAMPERS = []
for sx in (-1, 1):
    body = cyl_z('DAMPB%d' % (sx > 0), 0.022, 0.1, (sx * 0.17, 0.02, 0.08), (0.15, 0.55, 0.95), ROOT, n=20)
    rod = cyl_z('DAMPR%d' % (sx > 0), 0.009, 1.0, (sx * 0.17, 0.02, 0.13), (0.8, 0.82, 0.86), ROOT, n=12)
    DAMPERS.append((body, rod, sx))

# camara
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('CAM', cam_d)
sc.collection.objects.link(cam); sc.camera = cam
cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 36; cam_d.clip_start = 0.05; cam_d.clip_end = 50

# ---------------------------------------------------------------- linea de tiempo
SLOWMO = [(34.85, 36.5), (51.9, 54.3)]
def rate(t):
    r = 1.0
    for a, b in SLOWMO:
        r = min(r, 1 - 0.75 * win(t, a, b, 0.3))
    return r

WASH_W = 3.2
def omega(t):
    """velocidad angular del tambor (rad/s), signo = sentido"""
    w = 0.0
    segs = [(27.3, 29.25, 1), (29.95, 31.0, -1), (31.05, 32.9, 1), (33.0, 34.75, -1), (34.8, 36.45, 1),
            (41.3, 42.35, 1), (42.45, 43.55, -1),
            (65.3, 66.3, 1), (66.3, 67.3, -1), (67.4, 68.6, 1), (68.65, 69.9, -1)]
    for a, b, s in segs:
        w += s * WASH_W * sstep(a, a + 0.25, t) * (1 - sstep(b - 0.25, b, t))
    # centrifugado
    w += 16.0 * sstep(45.2, 46.9, t) * (1 - sstep(64.3, 65.2, t))
    return w

def spinf(t):  # 0..1 ropa pegada a la pared
    return sstep(45.4, 46.6, t) * (1 - sstep(64.4, 65.2, t))

ANG = [0.0] * (NFR + 1); TAU = [0.0] * (NFR + 1)
for f in range(1, NFR + 1):
    t = (f - 0.5) / FPS
    ANG[f] = ANG[f - 1] + omega(t) * rate(t) / FPS
    TAU[f] = TAU[f - 1] + rate(t) / FPS

def water_level(t):
    """nivel relativo al eje del tambor"""
    empty_l = -R_TUB_IN
    wl = LEVEL_Z - CZ
    L = empty_l
    L = lerp(L, wl, sstep(15.1, 18.85, t))
    L = lerp(L, empty_l, sstep(37.9, 39.9, t))
    L = lerp(L, wl, sstep(40.5, 41.7, t))
    L = lerp(L, empty_l, sstep(43.6, 45.3, t))
    return L

def water_color(t):
    c = WATER
    c = lerpv(c, DIRTY, sstep(36.6, 37.6, t) * (1 - sstep(40.3, 40.5, t)))
    return c

def soapy(t):
    return sstep(21.6, 23.2, t) * (1 - sstep(36.6, 37.4, t))

# explosion del gabinete
def explode(t):
    a = sstep(4.45, 5.4, t) * (1 - sstep(70.05, 70.5, t))
    b = sstep(5.6, 6.5, t) * (1 - sstep(70.05, 70.5, t))  # se alejan y desaparecen
    return a, b

HL = {  # resaltado amarillo: objeto -> [(t0,t1)]
    'TUB': [(6.9, 9.4)], 'DRUMSHELL': [(9.8, 12.9)], 'DRUMLIP': [(9.8, 12.9)],
    'VALVE': [(14.2, 15.7), (19.85, 20.4)], 'SENSOR': [(16.0, 19.0)],
    'DRAWER': [(22.6, 24.4)], 'DRAWERFRONT': [(22.6, 24.4)],
    'MOTOR': [(26.9, 28.6)], 'BELT': [(27.9, 28.9)],
    'PUMP': [(37.7, 39.6)],
    'SPRING0': [(59.1, 60.2)], 'SPRING1': [(59.1, 60.2)],
    'DAMPB0': [(60.1, 61.4)], 'DAMPB1': [(60.1, 61.4)],
    'CONCRETE': [(62.55, 65.0)],
}

# camara: llaves (t, pos, objetivo, lente)
CK = [
    (0.0, (1.0, -2.05, 1.0), (0, 0, 0.47), 40),
    (4.2, (0.88, -1.85, 0.95), (0, 0, 0.46), 40),
    (6.5, (0.95, -2.0, 1.05), (0, 0, 0.45), 40),
    (9.6, (0.55, -1.75, 0.85), (0, 0, 0.42), 40),
    (12.6, (0.4, -1.55, 0.95), (0, 0, 0.45), 40),
    (14.4, (0.9, 1.25, 1.55), (0.05, 0.05, 0.7), 40),
    (16.4, (1.55, -0.4, 1.05), (0.1, 0.05, 0.52), 40),
    (19.6, (1.45, -0.7, 1.1), (0.08, 0.0, 0.52), 40),
    (21.4, (-0.5, -1.15, 1.3), (-0.13, -0.15, 0.66), 40),
    (24.2, (-0.3, -1.2, 1.2), (-0.08, -0.1, 0.6), 40),
    (26.6, (-1.45, 1.35, 0.62), (0, 0.15, 0.36), 40),
    (29.6, (-1.2, 1.6, 0.52), (0, 0.15, 0.36), 40),
    (31.6, (0.2, -1.45, 0.62), (0, 0, 0.43), 40),
    (34.6, (0.05, -1.2, 0.55), (0, 0, 0.42), 40),
    (36.4, (0.0, -1.0, 0.5), (0, 0, 0.42), 40),
    (38.2, (-0.85, -1.35, 0.55), (-0.12, 0, 0.36), 40),
    (40.2, (-0.95, -1.25, 0.65), (-0.15, 0, 0.4), 40),
    (42.6, (0.25, -1.55, 0.7), (0, 0, 0.44), 40),
    (45.6, (0.0, -1.35, 0.55), (0, 0, 0.45), 40),
    (49.6, (0.0, -1.25, 0.5), (0, 0, 0.45), 40),
    (52.2, (0.12, -0.75, 0.55), (0.08, 0, 0.5), 40),
    (54.6, (0.05, -1.05, 0.52), (0.03, 0, 0.47), 40),
    (57.2, (0.6, -1.5, 0.85), (0, 0, 0.47), 40),
    (60.5, (0.85, -1.4, 0.62), (0, 0, 0.42), 40),
    (64.5, (0.5, -1.3, 0.95), (0, 0, 0.55), 40),
    (66.0, (0.0, -1.3, 0.52), (0, 0, 0.45), 40),
    (69.6, (0.05, -1.3, 0.55), (0, 0, 0.45), 40),
    (71.5, (1.3, -2.7, 1.2), (0, 0, 0.46), 40),
    (72.7, (1.35, -2.8, 1.25), (0, 0, 0.46), 40),
]
def cam_at(t):
    ts = [k[0] for k in CK]
    i = 0
    while i < len(CK) - 2 and t > ts[i + 1]: i += 1
    t0, t1 = ts[i], ts[i + 1]
    u = clamp((t - t0) / (t1 - t0))
    def tang(j, idx):
        a = CK[max(j - 1, 0)]; b = CK[min(j + 1, len(CK) - 1)]
        dt = (b[0] - a[0]) or 1
        return (Vector(b[idx]) - Vector(a[idx])) / dt if idx < 3 else (b[3] - a[3]) / dt
    def herm(idx):
        p0 = Vector(CK[i][idx]); p1 = Vector(CK[i + 1][idx])
        m0 = tang(i, idx) * (t1 - t0) * 0.8; m1 = tang(i + 1, idx) * (t1 - t0) * 0.8
        h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
        return p0 * h00 + m0 * h10 + p1 * h01 + m1 * h11
    return herm(1), herm(2), lerp(CK[i][3], CK[i + 1][3], u)

def place_cam(t):
    pos, tgt, lens = cam_at(t)
    # leve deriva constante
    d = Vector((0.03 * math.sin(t * 0.5), 0.0, 0.02 * math.sin(t * 0.37)))
    pos = pos + d
    cam.location = pos
    direc = (tgt - pos)
    cam.rotation_euler = direc.to_track_quat('-Z', 'Y').to_euler()
    cam_d.lens = lens

# ---------------------------------------------------------------- actualizar fotograma
def tumble_pos(c, t, tau, f):
    w = omega(t)
    amp = clamp(abs(w) / WASH_W)
    dirp = -1 if w >= 0 else 1  # sentido del angulo polar
    rest_a = c['rest']; rr = c['rr']
    rx, rz = rr * math.cos(rest_a), rr * math.sin(rest_a)
    p = (tau * 0.62 + c['off']) % 1.0
    lift = math.radians(135)
    if p < 0.55:
        u = p / 0.55
        a = rest_a + dirp * lift * u
        r = lerp(rr, 0.185, sstep(0, 0.3, u))
        x, z = r * math.cos(a), r * math.sin(a)
        rot = c['rot0'] + dirp * u * 2.2
    else:
        u = (p - 0.55) / 0.45
        a = rest_a + dirp * lift
        x0, z0 = 0.185 * math.cos(a), 0.185 * math.sin(a)
        x = lerp(x0, rx, u) - dirp * 0.04 * math.sin(math.pi * u)
        z = z0 + (rz - z0) * (u * u * 0.7 + 0.3 * u) + 0.03 * math.sin(math.pi * u)
        rot = c['rot0'] + dirp * (2.2 + c['spin'] * u * 2.5)
    x = lerp(rx, x, amp); z = lerp(rz, z, amp); rot = lerp(c['rot0'], rot, amp)
    # centrifugado: pegada a la pared, gira con el tambor
    s = spinf(t)
    if s > 0:
        aw = c['wall'] - ANG[f]
        rw = 0.186
        x = lerp(x, rw * math.cos(aw), s); z = lerp(z, rw * math.sin(aw), s)
        rot = lerp(rot, aw + math.pi / 2 + c['rot0'] * 0.3, s)
    return x, z, rot

def overfill(t):
    return sstep(65.3, 65.7, t) * (1 - sstep(67.3, 67.7, t))

def frame_update(f):
    t = f / FPS
    tau = TAU[min(f, NFR)]
    ang = ANG[min(f, NFR)]
    # gira la maquina completa al inicio y al final
    rz = lerp(math.radians(-25), math.radians(15), sstep(0, 4.6, t))
    rz += math.radians(360) * sstep(70.3, 72.3, t)
    ROOT.rotation_euler = (0, 0, rz)
    # vibracion de la tina (centrifugado / estabilidad)
    sh = 0.0045 * sstep(46.5, 47.5, t) * (1 - sstep(64.3, 65.2, t)) + 0.006 * win(t, 57.5, 64.3, 0.5)
    TUBG.location = (sh * math.sin(t * 47), 0, CZ + sh * math.sin(t * 59 + 1.3))
    # explosion
    a, b = explode(t)
    for ob, base, d in PARTS:
        ob.location = base + d.normalized() * (0.28 * a + 1.6 * b * b)
        s = 1 - sstep(0.35, 1.0, b)
        ob.scale = (s, s, s)
        ob.hide_render = s < 0.02
        for ch in ob.children_recursive:
            ch.hide_render = s < 0.02
    # tambor y poleas
    DRUM.rotation_euler = (0, ang, 0)
    PULLEY.rotation_euler = (0, ang, 0)
    MPUL.rotation_euler = (0, ang * 8.0, 0)
    # flechas
    w = omega(t)
    show_ar = clamp(abs(w) / WASH_W) * (1 - spinf(t))
    for e in (ARR_F, ARR_B):
        sgn = 1 if w >= 0 else -1
        e.scale = (sgn * show_ar, 1, show_ar)
        e.rotation_euler = (0, ang * 0.15, 0)
        for ch in e.children: ch.hide_render = show_ar < 0.05
    ARR_B.scale = (0, 0, 0) if True else ARR_B.scale
    sp_s = spinf(t) * (1 - sstep(56.6, 57.3, t))
    SPEED.rotation_euler = (0, ang * 0.5, 0)
    SPEED.scale = (sp_s, 1, sp_s)
    for ch in SPEED.children: ch.hide_render = sp_s < 0.05
    # flechas traseras solo en la vista de atras (motor)
    sb = win(t, 27.2, 31.2, 0.3)
    sgn = 1 if w >= 0 else -1
    ARR_B.scale = (sgn * sb * clamp(abs(w) / WASH_W), 1, sb * clamp(abs(w) / WASH_W))
    for ch in ARR_B.children: ch.hide_render = sb < 0.05 or abs(w) < 0.2
    for ch in ARR_F.children: ch.hide_render = show_ar < 0.05 or sb > 0.5
    # agua
    lvl = water_level(t)
    water_mesh(lvl)
    wc = water_color(t)
    set_rgb('WATER', wc)
    # burbujas
    so = soapy(t) * (lvl > -0.2)
    for i, (bo, r, x0, ph, sp) in enumerate(BUBBLES):
        R = R_TUB_IN - 0.02
        x = x0 + 0.01 * math.sin(t * sp * 2 + ph * 6)
        zmax = lvl - r - 0.005
        zmin = -math.sqrt(max(R * R - x * x, 0)) + r
        if zmax < zmin: bo.hide_render = True; continue
        z = lerp(zmin, zmax, (ph + 0.08 * math.sin(t * sp + i)) % 1.0)
        pop = sstep(21.6 + ph * 1.2, 22.1 + ph * 1.2, t) * (1 - sstep(36.6 + ph * 0.6, 37.0 + ph * 0.6, t))
        s = pop
        bo.scale = (s, s, s); bo.hide_render = s < 0.05
        for ch in bo.children: ch.hide_render = bo.hide_render
        bo.location = (x, -0.178 - 0.001 * i, z)
    # ropa
    of = overfill(t)
    for i, c in enumerate(CLOTHES):
        x, z, rot = tumble_pos(c, t, tau, f)
        if of > 0:
            ex = EXTRA[i % len(EXTRA)][1]
            x = lerp(x, ex[0] * 0.9 + 0.02 * i - 0.06, of); z = lerp(z, ex[2] * 0.9 - 0.08, of)
        c['ob'].location = (x, c['y'], z)
        c['ob'].rotation_euler = (0, -rot, 0)
        c['ob'].hide_render = False
        for ch in c['ob'].children: ch.hide_render = False
    for i, (ob, p, r0) in enumerate(EXTRA):
        s = sstep(65.3 + 0.03 * i, 65.6 + 0.03 * i, t) * (1 - sstep(67.3, 67.65, t))
        # la ropa no se mueve: atascada (solo un leve temblor con el tambor)
        jig = 0.004 * math.sin(t * 9 + i)
        ob.location = (p[0] + jig, p[1], p[2])
        ob.rotation_euler = (0, r0, 0)
        ob.scale = (s, s, s); ob.hide_render = s < 0.03
    # manchas
    for k, st in enumerate(STAINS):
        c = CLOTHES[st['cl']]; ob = st['ob']
        vis = sstep(24.5, 25.5, t) * (1 - sstep(37.0, 37.8, t))
        cx, cz, crot = tumble_pos(c, t, tau, f)
        ca, sa = math.cos(crot), math.sin(crot)
        ox, oz = st['off']
        px = cx + ox * ca - oz * sa; pz = cz + ox * sa + oz * ca
        td = 35.0 + 0.12 * k
        if t > td:
            dt = (tau - TAU[int(td * FPS)])
            px += st['v'][0] * dt * 1.6; pz += st['v'][1] * dt * 1.6 + 0.02 * math.sin(dt * 3)
            sc_ = 1 - sstep(td + 1.2, 37.6, t) * 0.5
        else:
            sc_ = 1
        ob.location = (px, c['y'] - 0.012, pz)
        ob.scale = (vis * sc_,) * 3
        ob.hide_render = vis < 0.05
    # gotas del centrifugado
    dr_on = sstep(46.3, 47.0, t) * (1 - sstep(55.6, 56.6, t))
    for i, d in enumerate(DROPS):
        p = (tau * 1.4 + d['ph']) % 1.0
        a0 = d['a'] - ANG[f] * 0.0 + i * 0.7 + math.floor(tau * 1.4 + d['ph']) * 2.1
        r = lerp(R_DRUM - 0.005, R_TUB_IN - 0.01, p)
        a = a0 - 0.5 * p
        d['ob'].location = (r * math.cos(a), d['y'], r * math.sin(a))
        s = dr_on * (1 - sstep(0.8, 1.0, p)) * sstep(0.0, 0.08, p)
        d['ob'].scale = (s * 1.0, 1, s * 0.75)
        d['ob'].rotation_euler = (0, -a, 0)
        d['ob'].hide_render = s < 0.05
    # valvula y flujo de agua
    vopen = (sstep(13.85, 14.05, t) * (1 - sstep(19.86, 20.0, t))) + (sstep(40.1, 40.25, t) * (1 - sstep(41.6, 41.75, t)))
    VKNOB.rotation_euler = (0, 0, math.radians(90) * vopen)
    def core(nm, a0, a1, b0, b1):
        o = WCORES[nm] if nm in WCORES else nm
        st = sstep(a0, a1, t); en = sstep(b0, b1, t)
        o.data.bevel_factor_end = max(st, 0.001)
        o.data.bevel_factor_start = min(en, 0.999)
        o.hide_render = st < 0.01 or en > 0.99
    # primera carga
    def multi(nm, phases):
        o = WCORES[nm]
        best = None
        for a0, a1, b0, b1 in phases:
            if t >= a0 - 0.01 and t <= b1 + 0.01:
                best = (a0, a1, b0, b1)
        if best is None:
            o.hide_render = True; return
        core(nm, *best)
    multi('WINLET', [(13.9, 14.3, 19.86, 20.2), (40.1, 40.3, 41.6, 41.9)])
    multi('WTUBEA', [(14.2, 14.8, 20.0, 20.5), (40.2, 40.5, 41.7, 42.0)])
    multi('WTUBEB', [(14.8, 15.1, 20.4, 20.8), (21.0, 21.3, 24.0, 24.4), (40.45, 40.6, 41.9, 42.2)])
    drw_w = win(t, 14.75, 20.6, 0.2) + win(t, 20.9, 24.1, 0.2) + win(t, 40.4, 41.9, 0.15)
    DRWAT.hide_render = drw_w < 0.05
    DRWAT.scale = (1, 1, max(drw_w, 0.05))
    set_rgb('DRWATER', lerpv(WATER, (0.7, 0.6, 1.0), sstep(21.0, 22.0, t) * (1 - sstep(24.2, 24.5, t))))
    det = 1 - 0.75 * sstep(21.2, 24.0, t)
    DET.scale = (det, det, det)
    DET.hide_render = t > 24.3 and t < 70.5
    # gotas que entran a la tina
    inflow = win(t, 15.0, 20.5, 0.2) + win(t, 21.1, 24.0, 0.2) + win(t, 40.5, 41.9, 0.15)
    for i, d in enumerate(INDROPS):
        p = (t * 2.2 + i / len(INDROPS)) % 1.0
        d.location = (-0.17, -0.1, lerp(0.7, 0.58, p))
        d.hide_render = inflow < 0.5
        d.rotation_euler = ROOT.rotation_euler
    # desague
    multi('WDRAIN', [(37.9, 38.3, 39.9, 40.2), (43.6, 43.9, 45.3, 45.6), (46.4, 46.8, 55.8, 56.3)])
    WPINc = WPIN
    pin_on = win(t, 37.8, 39.9, 0.1) + win(t, 43.55, 45.3, 0.1) + win(t, 46.3, 55.8, 0.2)
    WPINc.hide_render = pin_on < 0.3
    out_on = win(t, 38.3, 40.1, 0.1) + win(t, 43.9, 45.5, 0.1) + win(t, 46.8, 56.2, 0.2)
    for i, d in enumerate(OUTDROPS):
        p = (t * 2.0 + i / len(OUTDROPS)) % 1.0
        d.location = (-0.6 - 0.04 * p, 0.0, 0.55 - 0.5 * p * p)
        d.hide_render = out_on < 0.5
        s = 1 - 0.4 * p
        d.scale = (s, s, s)
    wc_out = DIRTY if t < 46 else lerpv(DIRTY, WATER, 0.5)
    set_rgb('WDRAIN', wc_out)
    for d in OUTDROPS: set_rgb(d.name, wc_out)
    # sensor: columna sube con el nivel (vasos comunicantes)
    lw = CZ + lvl
    h = max(lw - 0.13, 0.0005)
    SCOL.scale = (1, 1, h)
    SCOL.location = (SX, SY, 0.13 + h / 2)
    SCOL.hide_render = h < 0.002
    set_rgb('SCOL', wc)
    # resortes y amortiguadores (siguen a la tina)
    for sp in SPRINGS:
        top_z = H - 0.035
        bot = CZ + TUBG.location.z - CZ + math.sqrt(max(R_TUB_OUT ** 2 - 0.17 ** 2, 0)) - 0.005
        sp.scale = (1, 1, (top_z - bot))
    for body, rod, sx in DAMPERS:
        tz = TUBG.location.z - math.sqrt(max(R_TUB_OUT ** 2 - 0.17 ** 2, 0)) + 0.005
        rod.location = (sx * 0.17, 0.02, (0.11 + tz) / 2)
        rod.scale = (1, 1, max(tz - 0.11, 0.01))
    # resaltados
    for nm, wins in HL.items():
        m, base, a0 = MATS[nm]
        hv = 0
        for a, b in wins: hv = max(hv, win(t, a, b, 0.15))
        set_rgb(nm, lerpv(base, YEL, hv))
    # visibilidad: barra superior / resortes visibles siempre que el gabinete este abierto
    place_cam(t)

# anclas para etiquetas (en coordenadas locales de un objeto)
ANCH = {
    'tina': ('TUBG', (0.22, -0.2, 0.2)),
    'tambor': ('TUBG', (-0.14, -0.19, 0.12)),
    'valvula': ('VALVE', (0, 0, 0.03)),
    'sensor': ('SENSOR', (0, 0, 0.0)),
    'detergente': ('DRAWERG', (0, 0.06, 0.0)),
    'motor': ('MOTOR', (0.0, 0.1, 0.0)),
    'bomba': ('PUMPG', (0, -0.03, 0.03)),
    'resortes': ('SPRING1', (0, 0, -0.5)),
    'amortiguadores': ('DAMPB1', (0, 0, 0.0)),
    'concreto': ('CONCRETE', (0.0, 0, 0.0)),
    'drum_c': ('TUBG', (0, -0.19, 0)),
}

def meta(f):
    dg = bpy.context.evaluated_depsgraph_get()
    W, Hh = sc.render.resolution_x, sc.render.resolution_y
    out = {}
    for k, (on, p) in ANCH.items():
        ob = bpy.data.objects[on]
        wp = ob.matrix_world @ Vector(p)
        v = world_to_camera_view(sc, cam, wp)
        out[k] = (v.x * W, (1 - v.y) * Hh, v.z)
    # sombra: proyeccion del rectangulo de la base
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            wp = ROOT.matrix_world @ Vector((sx * 0.36, sy * 0.34, 0))
            v = world_to_camera_view(sc, cam, wp)
            pts.append((v.x * W, (1 - v.y) * Hh))
    out['shadow'] = pts
    return out

if __name__ == '__main__':
    frames = LIST if LIST else list(range(F0, min(F1, NFR)))
    allmeta = {}
    for f in frames:
        t0 = time.time()
        frame_update(f)
        bpy.context.view_layer.update()
        sc.render.filepath = os.path.join(OUT, 'f%05d.png' % f)
        bpy.ops.render.render(write_still=True)
        allmeta[f] = meta(f)
        print('FRAME', f, 'time %.2f' % (time.time() - t0), flush=True)
        with open(os.path.join(OUT, 'm%05d.json' % f), 'w') as fh:
            json.dump(allmeta[f], fh)
