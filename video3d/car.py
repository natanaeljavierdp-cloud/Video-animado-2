"""Stylized toy-model supercar (no logos), built procedurally."""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from util import *

WB_F, WB_R = 1.31, -1.31
TRACK = 0.84
WHEEL_R = 0.35
CRANK_Z = 0.40


def table_interp(xs, tbl, xq):
    return float(np.interp(xq, xs, tbl))


# side profile tables (x from tail to nose)
PX = [-2.26, -2.2, -2.0, -1.6, -1.31, -0.8, -0.3, 0.3, 0.8, 1.31, 1.8, 2.1, 2.24]
PW = [0.86, 0.90, 0.94, 0.97, 0.98, 0.965, 0.95, 0.95, 0.96, 0.97, 0.93, 0.86, 0.80]
PB = [0.30, 0.26, 0.20, 0.15, 0.14, 0.13, 0.13, 0.13, 0.13, 0.14, 0.14, 0.15, 0.17]
PT = [0.86, 0.88, 0.90, 0.91, 0.905, 0.90, 0.90, 0.88, 0.84, 0.77, 0.66, 0.56, 0.47]


def superellipse(n_pts, a, b, e=3.2, tumble=0.0):
    pts = []
    for k in range(n_pts):
        t = 2 * math.pi * k / n_pts
        c, s = math.cos(t), math.sin(t)
        y = a * math.copysign(abs(c) ** (2 / e), c)
        z = b * math.copysign(abs(s) ** (2 / e), s)
        if tumble and z > 0:
            y *= 1 - tumble * (z / b)
        pts.append((y, z))
    return pts


def loft(stations, ring_n, cap_front_center=None, cap_back_center=None):
    """stations: list of (x, W, B, T, e, tumble). Returns bmesh."""
    bm = bmesh.new()
    rings = []
    for (x, W, B, T, e, tb) in stations:
        zc = (B + T) / 2
        hb = (T - B) / 2
        ring = [bm.verts.new((x, y, zc + z)) for (y, z) in superellipse(ring_n, W, hb, e, tb)]
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(ring_n):
            a, b = rings[i][k], rings[i][(k + 1) % ring_n]
            c, d = rings[i + 1][(k + 1) % ring_n], rings[i + 1][k]
            bm.faces.new((a, d, c, b))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def body_stations():
    st = []
    # tail rounding cap
    for k in range(5, 0, -1):
        f = k / 5.0
        s = math.sqrt(1 - (1 - f) ** 2) if False else (1 - (1 - f) ** 2) ** 0.5
        x = -2.26 - 0.06 * (1 - f) ** 0.8
        W, B, T = PW[0], PB[0], PT[0]
        zc = (B + T) / 2
        hb = (T - B) / 2 * (0.55 + 0.45 * s)
        st.append((x, W * (0.8 + 0.2 * s), zc - hb, zc + hb, 3.2, 0.12))
    xs = np.linspace(-2.26, 2.24, 70)
    for x in xs:
        st.append((float(x), table_interp(PX, PW, x), table_interp(PX, PB, x), table_interp(PX, PT, x), 3.2, 0.12))
    # nose rounding: shrink toward center
    for k in range(1, 9):
        f = k / 8.0
        s = (1 - f ** 2) ** 0.5
        x = 2.24 + 0.09 * math.sin(f * math.pi / 2)
        W, B, T = PW[-1], PB[-1], PT[-1]
        zc = (B + T) / 2 - 0.02 * f
        hb = (T - B) / 2
        st.append((x, max(0.02, W * (0.55 + 0.45 * s)) if f < 1 else 0.3, zc - hb * (0.5 + 0.5 * s), zc + hb * (0.4 + 0.6 * s), 3.2, 0.12))
    return st


def cabin_stations():
    CX = [-1.50, -1.2, -0.8, -0.3, 0.1, 0.45, 0.80, 1.02]
    CT = [0.90, 0.99, 1.08, 1.145, 1.16, 1.12, 1.0, 0.87]
    CW = [0.62, 0.68, 0.74, 0.77, 0.77, 0.75, 0.72, 0.66]
    st = []
    for x in np.linspace(-1.5, 1.02, 40):
        T = table_interp(CX, CT, x)
        st.append((float(x), table_interp(CX, CW, x), 0.72, T, 2.8, 0.38))
    return st


class Decaler:
    def __init__(self, obj):
        dg = bpy.context.evaluated_depsgraph_get()
        self.bvh = BVHTree.FromObject(obj, dg)

    def make(self, polys, plane, direction, offset=0.006, thick=0.012, subdiv=3):
        """polys: list of 2D polygons in plane coords. plane 'YZ' (project along x), 'XZ' (along y), 'XY' (along z).
        direction: ray direction Vector."""
        bm = bmesh.new()
        for poly in polys:
            vs = []
            for (a, b) in poly:
                if plane == 'YZ':
                    p = Vector((0, a, b))
                elif plane == 'XZ':
                    p = Vector((a, 0, b))
                else:
                    p = Vector((a, b, 0))
                vs.append(bm.verts.new(p))
            bm.faces.new(vs)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        for _ in range(subdiv):
            bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
        d = direction.normalized()
        bad = []
        for v in bm.verts:
            origin = v.co - d * 5.0
            if plane == 'YZ':
                origin = Vector((-d.x * 5, v.co.y, v.co.z))
            elif plane == 'XZ':
                origin = Vector((v.co.x, -d.y * 5, v.co.z))
            else:
                origin = Vector((v.co.x, v.co.y, -d.z * 5))
            hit, n, idx, dist = self.bvh.ray_cast(origin, d)
            if hit is None:
                bad.append(v)
                continue
            v.co = hit - d * offset
            v.normal = -d
        if bad:
            bmesh.ops.delete(bm, geom=bad, context='VERTS')
        # thicken along -d
        geom = bm.faces[:]
        res = bmesh.ops.extrude_face_region(bm, geom=geom)
        nv = [e for e in res['geom'] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=-d * thick, verts=nv)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return bm


def mirror_y(poly):
    return [(-a, b) for (a, b) in reversed(poly)]


def stroke(p0, p1, w):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


def build_car():
    M = {
        'yellow': mat('yellow', '#FFC20E'),
        'black': mat('black', '#1c1d22'),
        'glass': mat('glass', '#20252f'),
        'tire': mat('tire', '#3a3c42'),
        'rim': mat('rim', '#101013'),
        'caliper': mat('caliper', '#FFD21A'),
        'white': mat('headlight', '#eef3ff'),
        'red': mat('taillight', '#d0202c'),
        'seat': mat('seat', '#8c2f39'),
        'exhaust': mat('exhaust', '#6b6f78'),
    }
    car = empty('CAR')
    parts = {}

    # ---------------- body shell -----------------
    g_body = empty('G_body', car)
    parts['body'] = g_body
    bm = loft(body_stations(), 128)
    body = mesh_obj('body', bm, M['yellow'], g_body, smooth=True)
    # wheel arches (boolean cut outer portions only)
    cutters = []
    for xw in (WB_F, WB_R):
        for sy in (1, -1):
            cb = bm_cyl(0.43, 0.7, 48, 'Y', (xw, sy * 1.05, WHEEL_R + 0.02))
            cut = mesh_obj('cut', cb, M['black'])
            cutters.append(cut)
            md = body.modifiers.new('b', 'BOOLEAN')
            md.object = cut
            md.operation = 'DIFFERENCE'
            md.solver = 'EXACT'
    bake(body)
    for c in cutters:
        bpy.data.objects.remove(c)
    for p in body.data.polygons:
        p.use_smooth = True
    # inner arch liners (black) so the cut is not hollow-looking
    for xw in (WB_F, WB_R):
        for sy in (1, -1):
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=False, segments=40, radius1=0.425, radius2=0.425, depth=0.36)
            bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'X'))
            # keep only upper part
            kill = [v for v in bm.verts if v.co.z < -0.10]
            bmesh.ops.delete(bm, geom=kill, context='VERTS')
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
            bmesh.ops.translate(bm, vec=(xw, sy * 0.80, WHEEL_R + 0.02), verts=bm.verts)
            ob = mesh_obj('liner', bm, M['black'], g_body)

    dec = Decaler(body)
    decals = []
    # front Y intakes (front view plane YZ, rays along -X)
    Ys = []
    for sgn in (1, -1):
        def P(a, b):
            return (sgn * a, b)
        arms = [stroke(P(0.36, 0.44), P(0.62, 0.27), 0.075), stroke(P(0.86, 0.44), P(0.62, 0.27), 0.075),
                stroke(P(0.62, 0.30), P(0.62, 0.15), 0.085)]
        if sgn < 0:
            arms = [list(reversed(a)) for a in arms]
        Ys += arms
    decals.append(('intakeY', dec.make(Ys, 'YZ', Vector((-1, 0, 0))), M['black']))
    decals.append(('splitter', dec.make([[(-0.80, 0.15), (0.80, 0.15), (0.80, 0.19), (-0.80, 0.19)],
                                        [(-0.26, 0.19), (0.26, 0.19), (0.22, 0.30), (-0.22, 0.30)]],
                                       'YZ', Vector((-1, 0, 0))), M['black']))
    # headlights: slim slanted strips with a small Y
    HL = []
    for sgn in (1, -1):
        poly = [(0.50, 0.565), (0.80, 0.505), (0.82, 0.535), (0.52, 0.598)]
        if sgn < 0:
            poly = mirror_y(poly)
        HL.append(poly)
    decals.append(('headlights', dec.make(HL, 'YZ', Vector((-1, 0, 0))), M['white']))
    # hood black vent band (front of windscreen)
    #decals.append(('hoodvent', dec.make([[(0.80, -0.45), (0.80, 0.45), (1.02, 0.30), (1.02, -0.30)]], 'XY', Vector((0, 0, -1))), M['black']))
    # side intakes (triangular) both sides
    for sgn in (1, -1):
        tri = [(-0.20, 0.66), (-1.00, 0.66), (-0.62, 0.32), (-0.30, 0.48)]
        decals.append(('sideintake', dec.make([tri], 'XZ', Vector((0, -sgn, 0))), M['black']))
        # sill
        sill = [(-0.95, 0.15), (0.95, 0.15), (0.95, 0.20), (-0.95, 0.20)]
        decals.append(('sill', dec.make([sill], 'XZ', Vector((0, -sgn, 0))), M['black']))
    # rear fascia black + taillights
    decals.append(('rearblack', dec.make([[(-0.84, 0.32), (0.84, 0.32), (0.80, 0.68), (-0.80, 0.68)]], 'YZ', Vector((1, 0, 0))), M['black']))
    TL = [[(0.40, 0.74), (0.84, 0.72), (0.82, 0.78), (0.42, 0.79)], mirror_y([(0.40, 0.74), (0.84, 0.72), (0.82, 0.78), (0.42, 0.79)])]
    decals.append(('taillights', dec.make(TL, 'YZ', Vector((1, 0, 0))), M['red']))
    # engine cover louvres (top, rear)
    lv = []
    for i in range(5):
        x0 = -1.62 - i * 0.11
        lv.append([(x0, -0.46), (x0, 0.46), (x0 - 0.06, 0.46), (x0 - 0.06, -0.46)])
    decals.append(('louvres', dec.make(lv, 'XY', Vector((0, 0, -1))), M['black']))
    for name, bmd, m in decals:
        mesh_obj(name, bmd, m, g_body, smooth=False)
    # exhausts
    for sy in (0.13, -0.13):
        mesh_obj('exhaust', bm_cyl(0.055, 0.14, 24, 'X', (-2.27, sy, 0.62)), M['exhaust'], g_body, smooth=True)
    # mirrors
    for sy in (1, -1):
        bm = bm_merge(bm_box(0.16, 0.10, 0.09, (0.0, 0.0, 0.0)), bm_box(0.05, 0.12, 0.03, (0.02, -sy * 0.08, -0.03)))
        mesh_obj('mirror', bm, M['yellow'], g_body, loc=(0.78, sy * 0.92, 0.93), bevel=0.02)

    # ---------------- cabin (glass + roof) -----------------
    g_cabin = empty('G_cabin', car)
    parts['cabin'] = g_cabin
    cab = mesh_obj('cabin', loft(cabin_stations(), 96), M['glass'], g_cabin, smooth=True)
    rst = []
    for (x, W, B, T, e, tb) in cabin_stations():
        if -1.02 <= x <= 0.40:
            rst.append((x, W * 0.64, T - 0.05, T + 0.012, 2.6, 0.0))
    mesh_obj('roof', loft(rst, 64), M['yellow'], g_cabin, smooth=True)

    # ---------------- rear wing -----------------
    g_wing = empty('G_wing', car)
    parts['wing'] = g_wing
    prof = [(-0.13, 0.0), (0.11, 0.012), (0.13, 0.026), (-0.12, 0.034)]
    wing = bm_prism([(x, z) for x, z in prof], 1.6, 'XZ', 0.0)
    wobj = mesh_obj('wing', wing, M['black'], g_wing, loc=(-2.10, 0, 0.965), bevel=0.008)
    wobj.rotation_euler = (0, math.radians(-6), 0)
    for sy in (0.32, -0.32):
        mesh_obj('strut', bm_box(0.08, 0.03, 0.12, (0, 0, 0)), M['black'], g_wing, loc=(-2.10, sy, 0.92), bevel=0.008)
    for sy in (0.80, -0.80):
        mesh_obj('endplate', bm_box(0.34, 0.02, 0.09, (0, 0, 0)), M['black'], g_wing, loc=(-2.10, sy, 0.965), bevel=0.006)
    parts['wing_main'] = wobj

    # ---------------- diffuser -----------------
    g_diff = empty('G_diffuser', g_body)
    for sy in (-0.6, -0.3, 0.0, 0.3, 0.6):
        mesh_obj('fin', bm_box(0.22, 0.025, 0.12, (0, 0, 0)), M['black'], g_diff, loc=(-2.12, sy, 0.24), bevel=0.006)
    mesh_obj('diffplate', bm_box(0.26, 1.4, 0.03, (0, 0, 0)), M['black'], g_diff, loc=(-2.10, 0, 0.19), bevel=0.01)

    # ---------------- seats & steering -----------------
    g_int = empty('G_interior', car)
    parts['interior'] = g_int
    for sy in (0.36, -0.36):
        mesh_obj('seat_base', bm_box(0.45, 0.42, 0.12, (0, 0, 0)), M['seat'], g_int, loc=(0.35, sy, 0.30), bevel=0.04)
        sb = mesh_obj('seat_back', bm_box(0.12, 0.42, 0.62, (0, 0, 0)), M['seat'], g_int, loc=(0.08, sy, 0.62), bevel=0.04)
        sb.rotation_euler = (0, math.radians(-18), 0)
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, segments=8, radius=0.01)
    sw = bm_merge(bm_cyl(0.17, 0.03, 32, 'X', (0, 0, 0)))
    swo = mesh_obj('steer', sw, M['black'], g_int, loc=(0.78, 0.36, 0.72), smooth=True)
    swo.rotation_euler = (0, math.radians(-25), 0)
    mesh_obj('dash', bm_box(0.25, 1.4, 0.18, (0, 0, 0)), M['black'], g_int, loc=(0.98, 0, 0.70), bevel=0.04)

    # ---------------- wheels -----------------
    wheels = {}
    for name, xw, sy in (('FL', WB_F, 1), ('FR', WB_F, -1), ('RL', WB_R, 1), ('RR', WB_R, -1)):
        width = 0.27 if name[0] == 'F' else 0.31
        g = empty('G_wheel_' + name, car, (xw, sy * TRACK, WHEEL_R))
        steer = empty('steer_' + name, g)
        spin = empty('spin_' + name, steer)
        tire = bm_cyl(WHEEL_R, width, 48, 'Y')
        tobj = mesh_obj('tire_' + name, tire, M['tire'], spin, bevel=0.06, bevel_seg=3)
        # rim: lip + hub + 6 Y-ish spokes
        outer = sy * (width / 2 - 0.02)
        rimparts = [bm_cyl(0.245, 0.02, 48, 'Y', (0, outer, 0)), bm_cyl(0.06, 0.05, 24, 'Y', (0, outer, 0))]
        for k in range(6):
            a = 2 * math.pi * k / 6
            sp = bm_box(0.2, 0.05, 0.06, (0.13, 0, 0))
            bm_transform(sp, Matrix.Rotation(a, 4, 'Y'))
            bmesh.ops.translate(sp, vec=(0, outer + sy * 0.012, 0), verts=sp.verts)
            rimparts.append(sp)
        # recessed dark disc behind spokes
        rimparts.append(bm_cyl(0.235, 0.01, 40, 'Y', (0, outer - sy * 0.09, 0)))
        robj = mesh_obj('rim_' + name, bm_merge(*rimparts), M['rim'], spin, smooth=False)
        cal = bm_box(0.16, 0.05, 0.08, (0, 0, 0))
        cobj = mesh_obj('caliper_' + name, cal, M['caliper'], steer, loc=(0.13 if name[0] == 'F' else -0.13, sy * (outer - sy * 0.09), 0.13), bevel=0.015)
        wheels[name] = dict(group=g, steer=steer, spin=spin, tire=tobj, rim=robj, caliper=cobj)
    parts['wheels'] = wheels
    return car, parts, M
