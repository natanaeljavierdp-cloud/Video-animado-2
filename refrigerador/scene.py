# Escena 3D "maqueta" del refrigerador: construccion + animacion procedural por tiempo.
import bpy, bmesh, math
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

FPS = 30
DUR = 71.24
NFRAMES = int(DUR * FPS)
W, H = 1080, 1920
TH0 = -0.64  # giro de referencia del refrigerador

# ---------------------------------------------------------------- utilidades
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def sstep(a, b, t):
    if b == a: return 1.0 if t >= b else 0.0
    x = clamp((t - a) / (b - a)); return x * x * (3 - 2 * x)
def lerp(a, b, x): return a + (b - a) * x
def lerpv(a, b, x): return tuple(lerp(a[i], b[i], x) for i in range(len(a)))
def back_out(x, s=2.2):
    x = clamp(x); x -= 1; return 1 + x * x * ((s + 1) * x + s)
def pulse(t, a, b, fade=0.35):  # 0..1..0 ventana suave
    return sstep(a, a + fade, t) * (1 - sstep(b - fade, b, t))

MATS = {}
def mat(name, col=None, alpha=1.0):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name)
    m.diffuse_color = (col[0], col[1], col[2], alpha)
    m.roughness = 1.0; m.specular_intensity = 0.0; m.metallic = 0.0
    MATS[name] = m
    return m

ROOT = None
OBJS = {}
BASE = {}  # posicion local base

def new_obj(name, bm, material, parent='ROOT', bevel=0.0, seg=3, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if isinstance(material, (list, tuple)):
        for m_ in material: me.materials.append(m_)
    else:
        me.materials.append(material)
    if bevel > 0:
        md = ob.modifiers.new('bev', 'BEVEL'); md.width = bevel; md.segments = seg
        md.limit_method = 'ANGLE'; md.harden_normals = False
    if parent == 'ROOT': ob.parent = ROOT
    elif parent is not None: ob.parent = OBJS[parent]
    OBJS[name] = ob
    return ob

def bm_box(size):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    return bm

def box(name, x0, x1, y0, y1, z0, z1, m, bevel=0.025, parent='ROOT'):
    bm = bm_box((x1 - x0, y1 - y0, z1 - z0))
    ob = new_obj(name, bm, m, parent, bevel=bevel)
    ob.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    BASE[name] = ob.location.copy()
    return ob

def bm_cyl(r, h, n=32, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=n, radius1=r,
                          radius2=r if r2 is None else r2, depth=h)
    return bm

def cyl(name, r, h, loc, m, n=32, bevel=0.0, parent='ROOT', rot=(0, 0, 0), r2=None, smooth=True):
    ob = new_obj(name, bm_cyl(r, h, n, r2), m, parent, bevel=bevel, smooth=smooth)
    ob.location = loc; ob.rotation_euler = rot
    BASE[name] = ob.location.copy()
    return ob

def bm_sphere(r, seg=24, ring=16):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=r)
    return bm

def sphere(name, r, loc, m, scale=(1, 1, 1), parent='ROOT'):
    bm = bm_sphere(r)
    for v in bm.verts: v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
    ob = new_obj(name, bm, m, parent, smooth=True)
    ob.location = loc; BASE[name] = ob.location.copy()
    return ob

def bm_capsule(r, h, cut=None):
    bm = bm_sphere(r, 32, 20)
    for v in bm.verts:
        if v.co.z > 1e-5: v.co.z += h / 2
        elif v.co.z < -1e-5: v.co.z -= h / 2
    if cut is not None:  # quita la mitad x>0 (corte en seccion)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(1, 0, 0),
                               clear_outer=(cut == 'keepneg'), clear_inner=(cut == 'keeppos'))
    return bm

# ---------------------------------------------------------------- tubo con colores por segmento
def round_poly(pts, r=0.06, n=6):
    out = [Vector(pts[0])]
    P = [Vector(p) for p in pts]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        d1 = (b - a); d2 = (c - b)
        l1, l2 = d1.length, d2.length
        if l1 < 1e-6 or l2 < 1e-6: continue
        rr = min(r, l1 * 0.49, l2 * 0.49)
        p0 = b - d1.normalized() * rr; p2 = b + d2.normalized() * rr
        for k in range(n + 1):
            u = k / n
            out.append((1 - u) ** 2 * p0 + 2 * (1 - u) * u * b + u * u * p2)
    out.append(P[-1])
    # quitar duplicados
    res = [out[0]]
    for p in out[1:]:
        if (p - res[-1]).length > 1e-5: res.append(p)
    return res

def resample(pts, step):
    L = [0.0]
    for i in range(1, len(pts)): L.append(L[-1] + (pts[i] - pts[i - 1]).length)
    tot = L[-1]; n = max(2, int(tot / step) + 1)
    out = []
    j = 0
    for k in range(n + 1):
        s = tot * k / n
        while j < len(L) - 2 and L[j + 1] < s: j += 1
        seg = L[j + 1] - L[j]
        u = 0 if seg < 1e-9 else (s - L[j]) / seg
        out.append(pts[j].lerp(pts[j + 1], u))
    return out, tot

def sweep(bm, pts, radius_fn, sides=10, mat_fn=None):
    """Barrido de un circulo por la polilinea. radius_fn(i)->radio, mat_fn(i)->indice material del tramo i..i+1"""
    rings = []
    prev_n = None
    for i, p in enumerate(pts):
        if i == 0: t = (pts[1] - pts[0]).normalized()
        elif i == len(pts) - 1: t = (pts[-1] - pts[-2]).normalized()
        else: t = ((pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()).normalized()
        if prev_n is None:
            a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            nrm = t.cross(a).normalized()
        else:
            nrm = (prev_n - t * prev_n.dot(t)).normalized()
        prev_n = nrm
        b = t.cross(nrm)
        r = radius_fn(i)
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * k / sides
            ring.append(bm.verts.new(p + (nrm * math.cos(ang) + b * math.sin(ang)) * r))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(sides):
            f = bm.faces.new((rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]))
            f.smooth = True
            if mat_fn: f.material_index = mat_fn(i)
    f = bm.faces.new(list(reversed(rings[0]))); f.material_index = mat_fn(0) if mat_fn else 0
    f = bm.faces.new(rings[-1]); f.material_index = mat_fn(len(rings) - 2) if mat_fn else 0

# ---------------------------------------------------------------- colores
WHITE = (0.93, 0.94, 0.95)
COLD = (0.42, 0.80, 1.00)
COLD2 = (0.30, 0.62, 1.00)
HOT = (0.95, 0.08, 0.03)
WARM = (1.00, 0.62, 0.32)
YEL = (1.00, 0.82, 0.05)
ORANGE = (1.00, 0.36, 0.02)
DARK = (0.22, 0.25, 0.30)

# circuito
EVAP = [(-0.5, .47, 1.95), (0.5, .47, 1.95), (0.5, .47, 1.83), (-0.5, .47, 1.83), (-0.5, .47, 1.71),
        (0.5, .47, 1.71), (0.5, .47, 1.59), (-0.5, .47, 1.59), (-0.5, .47, 1.47), (0.5, .47, 1.47)]
SUCT = [(0.5, .47, 1.47), (0.6, .47, 1.47), (0.6, .68, 1.47), (0.6, .68, 0.47), (0.42, .68, 0.47), (0.42, .80, 0.47)]
DISC = [(0.35, 0.95, 0.66), (0.35, 0.95, 0.80), (0.68, 0.95, 0.80), (0.68, 0.84, 0.80), (0.68, 0.84, 2.6)]
CZ = [2.6 - i * (1.6 / 6) for i in range(7)]
COND = [(0.68, 0.84, 2.6)]
for i, z in enumerate(CZ):
    xs = (0.55, -0.55) if i % 2 == 0 else (-0.55, 0.55)
    COND += [(xs[0], 0.84, z), (xs[1], 0.84, z)]
CAP_A = [(-0.55, 0.84, 1.0), (-0.70, 0.84, 1.0), (-0.70, 0.84, 0.72)]

def helix():
    c = Vector((-0.70, 0.75)); r = 0.09; pts = []
    turns = 3; n = 90
    for k in range(n + 1):
        u = k / n; a = math.pi / 2 + u * turns * 2 * math.pi
        pts.append(Vector((c.x + r * math.cos(a), c.y + r * math.sin(a), 0.72 - u * 0.30)))
    return pts
CAP_B = [(-0.70, 0.84, 0.42), (-0.70, 0.66, 0.42), (-0.70, 0.66, 1.95), (-0.5, 0.66, 1.95), (-0.5, .47, 1.95)]

SEGS = []  # (tag, frac, s_mid)
TUBE_MATS = []

def build_circuit():
    parts = []
    def add(tag, pts, rounded=True, r=0.06):
        P = round_poly(pts, r) if rounded else [Vector(p) for p in pts]
        P, L = resample(P, 0.045)
        parts.append((tag, P, L))
    add('evap', EVAP, r=0.06)
    add('suct', SUCT, r=0.06)
    add('disc', DISC, r=0.07)
    add('cond', COND, r=0.11)
    add('capA', CAP_A, r=0.06)
    add('capH', helix(), rounded=False)
    add('capB', CAP_B, r=0.06)
    s0 = 0.0
    bm = bmesh.new()
    for tag, P, L in parts:
        n = len(P) - 1
        start = len(SEGS)
        for i in range(n):
            SEGS.append((tag, (i + 0.5) / n, s0 + L * (i + 0.5) / n))
            m = bpy.data.materials.new('tube%d' % len(TUBE_MATS)); m.diffuse_color = (*COLD, 1)
            m.roughness = 1; m.specular_intensity = 0
            TUBE_MATS.append(m)
        rad = 0.013 if tag.startswith('cap') and tag != 'capA' else (0.035 if tag == 'suct' else 0.03)
        if tag == 'capA': rad = 0.026
        sweep(bm, P, lambda i, rad=rad: rad, sides=10, mat_fn=lambda i, st=start, n=n: st + min(i, n - 1))
        s0 += L
    ob = new_obj('tubes', bm, TUBE_MATS, smooth=True)
    BASE['tubes'] = ob.location.copy()
    return s0

def seg_base_color(tag, f):
    if tag == 'evap': return lerpv(COLD, COLD2, f * 0.6)
    if tag == 'suct': return lerpv(lerpv(COLD, COLD2, 0.6), COLD2, f)
    if tag == 'disc': return HOT
    if tag == 'cond': return lerpv(HOT, WARM, sstep(0.0, 1.0, f))
    if tag == 'capA': return WARM
    if tag == 'capH': return WARM if f < 0.22 else COLD
    if tag == 'capB': return COLD
    return COLD

# ---------------------------------------------------------------- flechas de calor
ARROWS = []
def bm_arrow():
    bm = bmesh.new()
    n = 24; L = 0.62; w = 0.045; amp = 0.05
    top, bot = [], []
    for k in range(n + 1):
        x = L * k / n
        y = amp * math.sin(2 * math.pi * x / 0.31)
        dy = amp * 2 * math.pi / 0.31 * math.cos(2 * math.pi * x / 0.31)
        nx, ny = -dy, 1.0; ln = math.hypot(nx, ny); nx /= ln; ny /= ln
        top.append(bm.verts.new((x + nx * w - L, y + ny * w, 0)))
        bot.append(bm.verts.new((x - nx * w - L, y - ny * w, 0)))
    for k in range(n):
        bm.faces.new((bot[k], bot[k + 1], top[k + 1], top[k]))
    # punta
    yend = amp * math.sin(2 * math.pi * L / 0.31)
    a = bm.verts.new((0 - 0.01, yend + 0.12, 0)); b = bm.verts.new((0 - 0.01, yend - 0.12, 0))
    c = bm.verts.new((0.22, yend, 0))
    bm.faces.new((b, c, a))
    for v in bm.verts: v.co.x += 0.11  # centrar
    return bm

def make_arrows(n):
    m = mat('heat', ORANGE)
    for i in range(n):
        ob = new_obj('arrow%d' % i, bm_arrow(), m, parent=None)
        ob.hide_render = True
        ARROWS.append(ob)

# ---------------------------------------------------------------- construccion
def build():
    global ROOT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.exposure = 0.55
    sh = sc.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'
    sh.show_shadows = True; sh.shadow_intensity = 0.25
    sh.show_cavity = True; sh.cavity_type = 'WORLD'
    sh.cavity_ridge_factor = 0.6; sh.cavity_valley_factor = 0.8
    sh.show_specular_highlight = False
    sc.display.light_direction = (0.45, -0.35, 0.82)
    sc.display.render_aa = '8'
    # freestyle
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = 'ABSOLUTE'; sc.render.line_thickness = 1.0
    vl = sc.view_layers[0]
    fs = vl.freestyle_settings
    fs.crease_angle = math.radians(120)
    for ls in list(fs.linesets): fs.linesets.remove(ls)
    ls = fs.linesets.new('outline')
    ls.select_by_visibility = True; ls.visibility = 'VISIBLE'
    ls.select_by_edge_types = True
    ls.select_silhouette = True; ls.select_border = True; ls.select_crease = True
    ls.select_external_contour = True
    ls.linestyle.color = (0.03, 0.03, 0.05); ls.linestyle.thickness = 2.6
    ls.linestyle.chaining = 'PLAIN'

    ROOT = bpy.data.objects.new('ROOT', None); sc.collection.objects.link(ROOT)

    # camara
    cd = bpy.data.cameras.new('cam'); cd.lens = 40; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 36
    cd.clip_start = 0.05; cd.clip_end = 100
    cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
    OBJS['cam'] = cam

    w = mat('white', WHITE); inner = mat('inner', (0.86, 0.91, 0.96))
    grey = mat('grey', (0.72, 0.75, 0.80)); dark = mat('dark', (0.18, 0.19, 0.22))
    # carcasa
    box('wall_L', -0.70, -0.62, -0.60, 0.60, 0.10, 2.92, w)
    box('wall_R', 0.62, 0.70, -0.60, 0.60, 0.10, 2.92, w)
    box('top', -0.70, 0.70, -0.60, 0.60, 2.92, 3.00, w)
    box('back', -0.62, 0.62, 0.52, 0.60, 0.18, 2.92, w)
    box('bottom', -0.62, 0.62, -0.60, 0.52, 0.10, 0.18, inner, bevel=0.01)
    box('divider', -0.62, 0.62, -0.60, 0.52, 2.00, 2.08, inner, bevel=0.015)
    box('shelf', -0.60, 0.60, -0.55, 0.42, 0.82, 0.85, mat('shelf', (0.70, 0.84, 0.96)), bevel=0.01)
    box('drawer', -0.55, 0.55, -0.55, 0.35, 0.19, 0.44, mat('drawer', (0.62, 0.86, 0.80)), bevel=0.03)
    box('door_top', -0.70, 0.70, -0.70, -0.61, 2.065, 3.00, w, bevel=0.035)
    box('door_bot', -0.70, 0.70, -0.70, -0.61, 0.10, 2.035, w, bevel=0.035)
    box('h_top', -0.03, 0.03, -0.05, 0.0, -0.22, 0.22, grey, bevel=0.018, parent='door_top')
    OBJS['h_top'].location = (-0.55, -0.075, -0.05); BASE['h_top'] = OBJS['h_top'].location.copy()
    box('h_bot', -0.03, 0.03, -0.05, 0.0, -0.3, 0.3, grey, bevel=0.018, parent='door_bot')
    OBJS['h_bot'].location = (-0.55, -0.075, 0.55); BASE['h_bot'] = OBJS['h_bot'].location.copy()
    for i, (x, y) in enumerate([(-0.55, -0.5), (0.55, -0.5), (-0.55, 0.5), (0.55, 0.5)]):
        cyl('foot%d' % i, 0.05, 0.1, (x, y, 0.05), dark, n=16)
    # alimentos
    red = mat('apple', (0.92, 0.12, 0.10))
    sphere('apple', 0.12, (-0.32, -0.2, 0.85 + 0.11), red, scale=(1, 1, 0.92))
    cyl('stem', 0.012, 0.07, (-0.32, -0.2, 0.85 + 0.25), mat('stem', (0.45, 0.25, 0.1)), n=8)
    sphere('leaf', 0.05, (-0.28, -0.2, 0.85 + 0.255), mat('leaf', (0.2, 0.75, 0.25)), scale=(1.2, 0.5, 0.25))
    gb = mat('bottle', (0.22, 0.72, 0.52))
    cyl('bottle', 0.075, 0.26, (0.05, -0.1, 0.85 + 0.13), gb, bevel=0.02)
    cyl('bneck', 0.075, 0.12, (0.05, -0.1, 0.85 + 0.32), gb, r2=0.03)
    cyl('bcap', 0.033, 0.04, (0.05, -0.1, 0.85 + 0.395), mat('cap', (0.95, 0.75, 0.15)), bevel=0.008)
    box('milk', 0.25, 0.43, -0.28, -0.10, 0.85, 1.13, mat('milk', (0.97, 0.97, 0.97)), bevel=0.012)
    bm = bmesh.new()  # techo a dos aguas del carton
    vs = [bm.verts.new(v) for v in [(-0.09, -0.09, 0), (0.09, -0.09, 0), (0.09, 0.09, 0), (-0.09, 0.09, 0), (0, -0.09, 0.08), (0, 0.09, 0.08)]]
    bm.faces.new((vs[0], vs[1], vs[4])); bm.faces.new((vs[2], vs[3], vs[5]))
    bm.faces.new((vs[1], vs[2], vs[5], vs[4])); bm.faces.new((vs[3], vs[0], vs[4], vs[5]))
    bm.faces.new((vs[3], vs[2], vs[1], vs[0]))
    ob = new_obj('milktop', bm, mat('milktop', (0.35, 0.60, 0.95)))
    ob.location = (0.34, -0.19, 1.13); BASE['milktop'] = ob.location.copy()
    box('milkfin', 0.335, 0.345, -0.28, -0.10, 1.21, 1.25, mat('milktop'), bevel=0.004)

    # circuito
    global PATH_LEN
    PATH_LEN = build_circuit()
    box('evplate', -0.64, 0.64, 0.505, 0.52, 1.38, 2.03, mat('evplate', (0.80, 0.84, 0.90)), bevel=0.008)
    # rejilla del condensador (varillas negras)
    cw = mat('condwire', (0.08, 0.08, 0.09))
    for i in range(12):
        x = -0.55 + 1.1 * i / 11
        box('cwire%d' % i, x - 0.008, x + 0.008, 0.875, 0.89, 0.92, 2.68, cw, bevel=0.0)
    for zz in (0.92, 2.68):
        box('cbar%.2f' % zz, -0.62, 0.62, 0.87, 0.895, zz - 0.02, zz + 0.02, cw, bevel=0.005)

    # compresor
    cc = Vector((0.35, 0.95, 0.36))
    comp = mat('comp', DARK)
    ob = new_obj('shell_back', bm_capsule(0.2, 0.25, 'keepneg'), comp, smooth=True); ob.location = cc
    BASE['shell_back'] = ob.location.copy()
    ob = new_obj('shell_front', bm_capsule(0.2, 0.25, 'keeppos'), comp, smooth=True); ob.location = cc
    BASE['shell_front'] = ob.location.copy()
    box('cbase', cc.x - 0.17, cc.x + 0.17, cc.y - 0.17, cc.y + 0.17, 0.0, 0.05, dark, bevel=0.01)
    # cilindro interno (mitad) + piston + camara de gas + biela
    bm = bm_cyl(0.085, 0.30, 32)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(1, 0, 0), clear_outer=True)
    ob = new_obj('bore', bm, mat('bore', (0.62, 0.66, 0.72)), smooth=True); ob.location = (cc.x, cc.y, 0.40)
    BASE['bore'] = ob.location.copy()
    cyl('piston', 0.078, 0.07, (cc.x, cc.y, 0.30), mat('piston', (0.80, 0.82, 0.86)), bevel=0.01)
    cyl('gas', 0.079, 1.0, (cc.x, cc.y, 0.45), mat('gas', COLD), smooth=True)
    box('rod', -0.012, 0.012, -0.012, 0.012, -0.5, 0.5, mat('piston'), bevel=0.0)
    cyl('crank', 0.05, 0.03, (cc.x + 0.0, cc.y, 0.16), mat('bore'), rot=(0, math.pi / 2, 0))
    cyl('valve', 0.03, 0.05, (cc.x, cc.y, 0.575), mat('bore'))

    # termostato
    tc = Vector((0.50, -0.28, 1.72))
    box('tbody', tc.x - 0.03, tc.x + 0.03, tc.y - 0.17, tc.y + 0.17, tc.z - 0.17, tc.z + 0.17, w, bevel=0.03)
    bm = bm_cyl(0.135, 0.02, 40); ob = new_obj('tring', bm, mat('tring', (0.72, 0.75, 0.80)), smooth=True)
    ob.location = (tc.x + 0.035, tc.y, tc.z); ob.rotation_euler = (0, math.pi / 2, 0); BASE['tring'] = ob.location.copy()
    # arcos azul/rojo
    def arc(name, a0, a1, colm):
        bm = bmesh.new(); n = 16; r0, r1 = 0.075, 0.115
        vs = []
        for k in range(n + 1):
            a = math.radians(lerp(a0, a1, k / n))
            vs.append((bm.verts.new((0, r0 * math.cos(a), r0 * math.sin(a))), bm.verts.new((0, r1 * math.cos(a), r1 * math.sin(a)))))
        for k in range(n): bm.faces.new((vs[k][0], vs[k + 1][0], vs[k + 1][1], vs[k][1]))
        ob = new_obj(name, bm, colm); ob.location = (tc.x + 0.047, tc.y, tc.z); BASE[name] = ob.location.copy()
    arc('arc_cold', 180, 95, mat('arccold', COLD2))  # izquierda en pantalla (-y)
    arc('arc_hot', 85, 0, mat('archot', HOT))
    bm = bm_box((0.01, 0.022, 0.12))
    for v in bm.verts: v.co.z += 0.05
    ob = new_obj('needle', bm, mat('needle', (0.1, 0.1, 0.12))); ob.location = (tc.x + 0.055, tc.y, tc.z); BASE['needle'] = ob.location.copy()
    cyl('knob', 0.03, 0.03, (tc.x + 0.06, tc.y, tc.z), mat('grey'), rot=(0, math.pi / 2, 0))
    # cable termostato -> compresor
    bm = bmesh.new()
    P, _ = resample(round_poly([(0.5, -0.28, 1.55), (0.5, -0.28, 1.05), (0.5, 0.64, 1.05), (0.5, 0.64, 0.5), (0.5, 0.80, 0.5)], 0.06), 0.03)
    sweep(bm, P, lambda i: 0.008, sides=6)
    new_obj('wire', bm, mat('wire', (0.15, 0.16, 0.2)), smooth=True)

    # pared (escena 8): en marco con giro pero sin traslado
    bm = bm_box((2.6, 0.12, 3.6))
    ob = new_obj('wallbg', bm, mat('wallbg', (0.80, 0.80, 0.78)), parent=None, bevel=0.02)
    ob.hide_render = True
    # halo amarillo del tubo capilar
    make_arrows(36)
    return sc

# ---------------------------------------------------------------- tiempo / camara lenta
SLOW = [(22.3, 24.2), (31.3, 33.7), (47.2, 48.8)]
def speed(t):
    s = 1.0
    for a, b in SLOW: s -= 0.68 * pulse(t, a, b, 0.4)
    return s
def comp_on(t):  # termostato: apaga 58.2, enciende 60.4
    return 1 - sstep(58.1, 58.35, t) * (1 - sstep(60.35, 60.55, t))
CLK = []; FLOW = []; PIST = []
def precompute():
    dt = 1.0 / FPS / 4; c = f = p = 0.0; t = 0.0
    for fr in range(NFRAMES + 2):
        CLK.append(c); FLOW.append(f); PIST.append(p)
        for _ in range(4):
            s = speed(t); on = comp_on(t)
            c += s * dt; f += s * on * dt; p += s * on * dt; t += dt
def at(arr, t):
    x = t * FPS; i = int(x); u = x - i
    i = min(i, len(arr) - 2)
    return lerp(arr[i], arr[i + 1], u)

# ---------------------------------------------------------------- giro del refrigerador
def theta(t):
    if t < 6.7:
        u = clamp(t / 6.7); return TH0 + 1.25 * (1 - u) ** 2  # giro lento
    if t < 69.0: return TH0
    return TH0 - 2 * math.pi * sstep(69.0, 71.0, t)
def root_shift(t):  # escena 8: se separa de la pared
    return -0.95 * sstep(66.2, 67.4, t) * (1 - sstep(68.4, 69.0, t))

def Rz(a): return Matrix.Rotation(a, 4, 'Z')

# camara: llaves en coordenadas locales (pos, objetivo)
W1 = (Vector((0, -6.3, 2.05)), Vector((0, 0, 1.55)))
def local_from_world(v): return Rz(-TH0) @ v
CAMK = [
    (6.7, local_from_world(W1[0]), local_from_world(W1[1])),
    (9.6, Vector((4.3, -7.6, 4.2)), Vector((-0.15, 0.0, 2.7))),
    (12.6, Vector((3.6, -7.0, 3.5)), Vector((-0.1, 0.1, 2.3))),
    (14.3, Vector((2.6, -4.4, 2.3)), Vector((0.0, 0.3, 1.5))),
    (16.0, Vector((1.55, -2.55, 1.85)), Vector((0.0, 0.3, 1.45))),
    (19.2, Vector((1.25, -2.15, 1.55)), Vector((0.0, 0.3, 1.35))),
    (22.4, Vector((0.95, -1.85, 1.45)), Vector((0.05, 0.3, 1.32))),
    (24.3, Vector((0.9, -1.7, 1.4)), Vector((0.1, 0.35, 1.3))),
    (26.2, Vector((2.3, -0.5, 1.3)), Vector((0.5, 0.62, 0.95))),
    (28.0, Vector((2.3, 0.6, 0.85)), Vector((0.35, 0.92, 0.45))),
    (30.4, Vector((1.85, 1.0, 0.65)), Vector((0.32, 0.95, 0.38))),
    (33.6, Vector((1.45, 1.1, 0.55)), Vector((0.3, 0.95, 0.38))),
    (35.3, Vector((1.7, 1.9, 0.9)), Vector((0.2, 0.85, 0.7))),
    (37.2, Vector((1.6, 4.4, 1.8)), Vector((0.0, 0.84, 1.75))),
    (40.5, Vector((0.8, 4.5, 1.9)), Vector((0.0, 0.84, 1.75))),
    (44.8, Vector((-0.5, 3.9, 1.4)), Vector((-0.25, 0.84, 1.35))),
    (46.4, Vector((-1.5, 2.2, 0.85)), Vector((-0.68, 0.75, 0.62))),
    (48.7, Vector((-1.25, 1.75, 0.75)), Vector((-0.70, 0.75, 0.58))),
    (50.8, Vector((-2.6, 1.3, 1.7)), Vector((-0.5, 0.5, 1.4))),
    (53.0, Vector((-1.5, -2.0, 1.85)), Vector((-0.1, 0.4, 1.65))),
    (55.2, Vector((1.9, -0.95, 1.85)), Vector((0.5, -0.28, 1.72))),
    (57.4, Vector((2.2, -0.75, 1.75)), Vector((0.5, -0.20, 1.62))),
    (59.0, Vector((4.3, -0.1, 1.2)), Vector((0.45, 0.15, 1.05))),
    (63.2, Vector((4.4, 0.0, 1.2)), Vector((0.45, 0.2, 1.05))),
    (65.0, Vector((4.6, -1.4, 2.6)), Vector((0.0, 0.7, 1.55))),
    (67.6, Vector((4.6, -2.0, 2.6)), Vector((0.0, 0.2, 1.55))),
    (69.0, Vector((3.7, -5.3, 2.2)), Vector((0.0, -0.4, 1.5))),
]

def catmull(keys, t, idx):
    ts = [k[0] for k in keys]
    if t <= ts[0]: return keys[0][idx].copy()
    if t >= ts[-1]: return keys[-1][idx].copy()
    i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
    p0 = keys[max(i - 1, 0)][idx]; p1 = keys[i][idx]; p2 = keys[i + 1][idx]; p3 = keys[min(i + 2, len(keys) - 1)][idx]
    t0 = keys[max(i - 1, 0)][0]; t1 = ts[i]; t2 = ts[i + 1]; t3 = keys[min(i + 2, len(keys) - 1)][0]
    u = (t - t1) / (t2 - t1)
    # tangentes (cardinal con tiempos no uniformes)
    m1 = (p2 - p0) / max(t2 - t0, 1e-6) * (t2 - t1) if i > 0 else (p2 - p1) * 0.0
    m2 = (p3 - p1) / max(t3 - t1, 1e-6) * (t2 - t1) if i + 2 < len(keys) else (p2 - p1) * 0.0
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
    return p1 * h00 + m1 * h10 + p2 * h01 + m2 * h11

def camera_world(t):
    if t < 6.7:
        drift = Vector((0, 0.25 * (1 - t / 6.7), 0))
        return W1[0] + drift, W1[1]
    lp = catmull(CAMK, t, 1); lt = catmull(CAMK, t, 2)
    R = Rz(TH0)
    return (R @ lp), (R @ lt)

def look_at(ob, pos, tgt):
    d = (tgt - pos).normalized()
    ob.location = pos
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- despiece
EXPL = {  # desplazamiento local, giro z, retraso
    'door_top': (Vector((-0.95, -1.5, 0.75)), 0.55, 0.0),
    'door_bot': (Vector((-1.05, -1.65, -0.05)), 0.55, 0.1),
    'wall_L': (Vector((-0.9, 0, 0.0)), 0, 0.25),
    'wall_R': (Vector((0.95, 0, 0.0)), 0, 0.25),
    'top': (Vector((0, 0, 0.95)), 0, 0.4),
    'back': (Vector((0, 0.0, 3.35)), 0, 0.5),
}
FAR = {'door_top': Vector((-3, -2, 1)), 'door_bot': Vector((-3, -2.5, 0)), 'wall_L': Vector((-4, 0, 0)),
       'wall_R': Vector((4.5, 0, 0)), 'top': Vector((0, 0, 4)), 'back': Vector((0, 0, 5))}

def explode_state(name, t):
    off, rz, dl = EXPL[name]
    e = sstep(7.0 + dl, 8.6 + dl, t)
    far = sstep(14.2, 15.6, t)
    if name.startswith('door'):
        back_t = 68.78
    else:
        back_t = 63.85
    rec = back_out((t - back_t) / 0.55) if t >= back_t else 0.0
    o = off * e + FAR[name] * far
    r = rz * e
    if t >= back_t: o = off * (1 - rec); r = rz * (1 - rec)
    vis = not (far > 0.98 and t < back_t)
    return o, r, vis

# ---------------------------------------------------------------- flechas: corrientes
def food_pts():
    return {'apple': Vector((-0.32, -0.2, 1.05)), 'bottle': Vector((0.05, -0.1, 1.25)), 'milk': Vector((0.34, -0.19, 1.25))}

def stream_list():
    S = []
    # escena 1: salen de dentro hacia atras
    for k, (x, z) in enumerate([(-0.25, 1.0), (0.2, 1.6), (0.0, 2.3), (-0.1, 0.6)]):
        S.append(dict(t0=3.35 + 0.18 * k, t1=6.4, n=2, period=1.7, size=0.85, clock=False,
                      pts=[Vector((x * 0.5, 0.0, z)), Vector((0.6, 0.7, z + 0.1)), Vector((1.3, 1.6, z + 0.35)), Vector((1.6, 2.6, z + 0.6))]))
    # escena 3: de la comida al evaporador
    fp = food_pts()
    tg = {'apple': Vector((-0.3, 0.42, 1.6)), 'bottle': Vector((0.05, 0.42, 1.75)), 'milk': Vector((0.35, 0.42, 1.65))}
    for k, nm in enumerate(['apple', 'bottle', 'milk']):
        S.append(dict(t0=19.0 + 0.25 * k, t1=24.2, n=3, period=1.5, size=0.5, clock=True,
                      pts=[fp[nm], fp[nm] + Vector((0, 0.15, 0.25)), tg[nm]]))
    # escena 5: del condensador hacia el aire
    for k, (x, z) in enumerate([(-0.35, 2.3), (0.3, 2.0), (-0.1, 1.6), (0.35, 1.25), (-0.4, 1.15)]):
        S.append(dict(t0=39.1 + 0.2 * k, t1=45.2, n=2, period=1.7, size=0.62, clock=False,
                      pts=[Vector((x, 0.9, z)), Vector((x + 0.05, 1.5, z + 0.25)), Vector((x + 0.1, 2.3, z + 0.7))]))
    # escena 8a: atrapadas entre condensador y pared (rebote)
    for k, (x, z) in enumerate([(-0.3, 2.2), (0.25, 1.8), (-0.05, 1.3), (0.3, 2.5)]):
        S.append(dict(t0=64.2 + 0.15 * k, t1=66.4, n=1, period=0.9, size=0.42, clock=False, bounce=True,
                      pts=[Vector((x, 0.92, z)), Vector((x, 1.2, z + 0.05))]))
    # escena 8b: salen libres
    for k, (x, z) in enumerate([(-0.3, 2.2), (0.25, 1.8), (-0.05, 1.3), (0.3, 2.5)]):
        S.append(dict(t0=66.9 + 0.12 * k, t1=68.6, n=2, period=1.3, size=0.55, clock=False,
                      pts=[Vector((x, 0.92, z)), Vector((x, 1.6, z + 0.4)), Vector((x + 0.2, 1.9, z + 1.6))]))
    return S
STREAMS = None

def path_at(pts, u):
    L = [0.0]
    for i in range(1, len(pts)): L.append(L[-1] + (pts[i] - pts[i - 1]).length)
    s = u * L[-1]
    for i in range(len(pts) - 1):
        if s <= L[i + 1] or i == len(pts) - 2:
            seg = max(L[i + 1] - L[i], 1e-9); v = clamp((s - L[i]) / seg)
            return pts[i].lerp(pts[i + 1], v), (pts[i + 1] - pts[i]).normalized()

def pose_arrows(t, Mroot, campos, camfwd):
    global STREAMS
    if STREAMS is None: STREAMS = stream_list()
    used = 0
    clk = at(CLK, t)
    if t > 68.8: STREAMS_OFF = True
    else: STREAMS_OFF = False
    for st in (STREAMS if not STREAMS_OFF else []):
        tt = clk if st['clock'] else t
        t0 = at(CLK, st['t0']) if st['clock'] else st['t0']
        t1 = at(CLK, st['t1']) if st['clock'] else st['t1']
        if t < st['t0'] - 0.01 or tt > t1 + st['period']: continue
        for i in range(st['n']):
            raw = (tt - t0) / st['period'] - i / st['n']
            if raw < 0: continue
            cyc = math.floor(raw); u = raw - cyc
            cstart = t0 + (cyc + i / st['n']) * st['period']
            if cstart > t1: continue
            if st.get('bounce'):
                if tt > t1: continue
                uu = u * 2 if u < 0.5 else 2 - u * 2
                p, d = path_at(st['pts'], uu)
                if u >= 0.5: d = -d
                env = min(1.0, (tt - t0) / 0.3, (t1 - tt) / 0.3 + 0.0)
            else:
                p, d = path_at(st['pts'], u)
                env = min(1.0, u / 0.15, (1 - u) / 0.18)
            env = clamp(env)
            if env < 0.02 or used >= len(ARROWS): continue
            ob = ARROWS[used]; used += 1
            pw = Mroot @ p
            dw = (Mroot.to_3x3() @ d).normalized()
            z = (campos - pw).normalized()
            x = dw - z * dw.dot(z)
            if x.length < 1e-4: x = Vector((0, 0, 1)) - z * z.z
            x.normalize(); y = z.cross(x)
            s = st['size'] * (0.4 + 0.6 * env)
            M = Matrix((x * s, y * s, z * s)).transposed().to_4x4()
            M.translation = pw
            ob.matrix_world = M
            ob.hide_render = False
    for ob in ARROWS[used:]: ob.hide_render = True

# ---------------------------------------------------------------- pose por tiempo
def set_col(name, col):
    m = MATS[name]; m.diffuse_color = (col[0], col[1], col[2], m.diffuse_color[3])

def pose(t):
    sc = bpy.context.scene
    th = theta(t)
    ROOT.rotation_euler = (0, 0, th)
    ROOT.location = Rz(th) @ Vector((0, root_shift(t), 0))
    # despiece
    for nm in EXPL:
        o, r, vis = explode_state(nm, t)
        ob = OBJS[nm]
        ob.location = BASE[nm] + o
        ob.rotation_euler = (0, 0, r)
        ob.hide_render = not vis
        for ch in ob.children: ch.hide_render = not vis
    # carcasa del compresor: corte en seccion 30.4 -> 63.85
    cut = sstep(30.3, 31.0, t) * (1 - sstep(63.85, 64.3, t))
    sf = OBJS['shell_front']
    sf.location = BASE['shell_front'] + Vector((0.9 * cut, 0.0, 0.25 * cut))
    sf.hide_render = cut > 0.97
    # vibracion del compresor
    on = comp_on(t)
    vib = (0.004 + 0.006 * pulse(t, 60.4, 63.6, 0.3)) * on
    vx = vib * math.sin(t * 2 * math.pi * 23.0); vy = vib * math.sin(t * 2 * math.pi * 17.0 + 1)
    for nm in ('shell_back', 'shell_front'):
        OBJS[nm].location = (OBJS[nm].location if nm == 'shell_front' else BASE[nm]) + Vector((vx, vy, 0)) * (1 if nm == 'shell_back' else 1)
    # piston
    ang = 2 * math.pi * 1.6 * at(PIST, t)
    cc = BASE['bore']
    zp = 0.33 + 0.065 * math.cos(ang)  # centro del piston
    OBJS['piston'].location = (cc.x, cc.y, zp)
    top = 0.545
    gh = top - (zp + 0.035)
    OBJS['gas'].location = (cc.x, cc.y, zp + 0.035 + gh / 2)
    OBJS['gas'].scale = (1, 1, max(gh, 0.005))
    comp = (math.cos(ang) + 1) / 2  # 1 = arriba (gas apretado)
    hotness = sstep(30.4, 31.0, t) * comp ** 0.7 if t < 64 else comp
    set_col('gas', lerpv(COLD, HOT, max(hotness, 0.15 * comp)))
    crank_y = 0.05 * math.sin(ang); crank_z = 0.16 + 0.05 * math.cos(ang)
    a = Vector((cc.x, cc.y + crank_y, crank_z)); b = Vector((cc.x, cc.y, zp - 0.02))
    rod = OBJS['rod']; rod.location = (a + b) / 2
    d = b - a; rod.scale = (1, 1, d.length)
    rod.rotation_euler = (math.atan2(-d.y, d.z), 0, 0)
    OBJS['crank'].rotation_euler = (ang, math.pi / 2, 0)
    # resaltes amarillos
    set_col('comp', lerpv(DARK, YEL, pulse(t, 27.2, 29.6, 0.3)))
    set_col('evplate', lerpv((0.80, 0.84, 0.90), YEL, pulse(t, 17.9, 19.9, 0.3)))
    set_col('condwire', lerpv((0.08, 0.08, 0.09), YEL, pulse(t, 38.0, 40.0, 0.3)))
    set_col('tring', lerpv((0.72, 0.75, 0.80), YEL, pulse(t, 54.2, 56.4, 0.3)))
    # termostato visible solo en escena 7
    tv = sstep(53.6, 54.2, t) * (1 - sstep(63.6, 63.9, t))
    for nm in ('tbody', 'tring', 'arc_cold', 'arc_hot', 'needle', 'knob', 'wire'):
        ob = OBJS[nm]; ob.hide_render = tv < 0.01
        ob.scale = (max(tv, 0.01),) * 3 if nm != 'wire' else (1, 1, 1)
        if nm != 'wire':
            c = Vector((0.50, -0.28, 1.72))
            ob.location = c + (BASE[nm] - c) * max(tv, 0.01)
    # termostato: aguja
    temp = 0.5
    temp = lerp(0.65, 0.15, sstep(56.1, 57.9, t))
    temp = lerp(temp, 0.75, sstep(59.1, 60.4, t))
    temp = lerp(temp, 0.5, sstep(61.0, 63.0, t))
    OBJS['needle'].rotation_euler = (lerp(1.25, -1.25, temp), 0, 0)
    # colores del refrigerante con pulsos que avanzan
    ph = at(FLOW, t) * 0.55
    lam = 0.32
    for i, (tag, f, s) in enumerate(SEGS):
        base = seg_base_color(tag, f)
        if tag == 'capH' and f >= 0.22:
            # destello del cambio brusco
            base = base
        b = 0.5 + 0.5 * math.cos(2 * math.pi * (s - ph) / lam)
        b = b ** 6
        light = tuple(min(1.0, c + 0.45) for c in base)
        c = lerpv(base, light, 0.75 * b)
        TUBE_MATS[i].diffuse_color = (c[0], c[1], c[2], 1)
    # pared escena 8
    wb = OBJS['wallbg']
    wv = sstep(63.7, 64.3, t) * (1 - sstep(68.3, 68.8, t))
    wb.hide_render = wv < 0.01
    Mw = Rz(th) @ Matrix.Translation((0, 1.32, 1.8 * wv)) @ Matrix.Diagonal((1, 1, max(wv, 0.01), 1))
    wb.matrix_world = Mw
    # camara
    cp, ct = camera_world(t)
    look_at(OBJS['cam'], cp, ct)
    bpy.context.view_layer.update()
    Mroot = ROOT.matrix_world.copy()
    pose_arrows(t, Mroot, cp, (ct - cp).normalized())
    bpy.context.view_layer.update()

# ---------------------------------------------------------------- anclas de etiquetas (locales)
ANCHORS = {
    'refrig': Vector((0.68, 0.84, 1.9)),
    'evap': Vector((-0.2, 0.47, 1.83)),
    'comp': Vector((0.30, 0.86, 0.55)),
    'cond': Vector((0.0, 0.84, 2.07)),
    'cap': Vector((-0.70, 0.75, 0.55)),
    'termo': Vector((0.55, -0.28, 1.84)),
}

def project(t):
    sc = bpy.context.scene; cam = OBJS['cam']
    M = ROOT.matrix_world
    out = {}
    for k, v in ANCHORS.items():
        p = world_to_camera_view(sc, cam, M @ v)
        out[k] = (p.x * W, (1 - p.y) * H, p.z)
    # elipse de sombra en el piso
    Ms = Rz(theta(t)) @ Matrix.Translation((0, root_shift(t), 0))
    sh = []
    for k in range(24):
        a = 2 * math.pi * k / 24
        p = world_to_camera_view(sc, cam, Ms @ Vector((0.95 * math.cos(a), 0.15 + 1.0 * math.sin(a), 0)))
        sh.append((p.x * W, (1 - p.y) * H, p.z))
    out['shadow'] = sh
    return out
