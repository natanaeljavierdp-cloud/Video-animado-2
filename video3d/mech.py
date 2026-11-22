"""V10 engine, dual-clutch 7-speed gearbox, driveline, single-cylinder callout."""
import bpy, bmesh, math
from mathutils import Vector, Matrix, Quaternion
from util import *

CRANK_Z = 0.40
CR = 0.045       # crank radius
ROD = 0.15       # rod length
BANK = math.radians(45)  # each bank 45 deg from vertical -> 90 deg V
CYL_X = [-0.24 - i * 0.18 for i in range(5)]
BANK_OFF = 0.026
# crank throw angles (5 throws, 72 deg apart, firing-friendly order)
THROW = [0, 144, 288, 72, 216]
# Firing order (cyl 1-5 right bank, 6-10 left bank)
FIRING = [1, 6, 5, 10, 2, 7, 3, 8, 4, 9]
GEAR_X = [-1.42 - k * 0.078 for k in range(7)]
IN_Z, OUT_Z = 0.47, 0.29
GB_X0, GB_X1 = -1.02, -2.0


def bank_dir(side):
    # side +1 = left bank (+Y), -1 = right bank (-Y)
    return Vector((0, side * math.sin(BANK), math.cos(BANK)))


def cyl_info():
    """List of dicts for the 10 cylinders: num, side, x, throw index."""
    out = []
    for i, x in enumerate(CYL_X):
        out.append(dict(num=i + 1, side=-1, x=x - BANK_OFF, throw=i))      # right bank 1..5
        out.append(dict(num=i + 6, side=1, x=x + BANK_OFF, throw=i))       # left bank 6..10
    return out


def piston_s(phi, throw_deg, side):
    """Distance from crank axis to piston pin along bank axis (slider-crank)."""
    a = phi + math.radians(throw_deg)
    pin = Vector((0, -CR * math.sin(a), CR * math.cos(a)))
    d = bank_dir(side)
    ca = pin.dot(d) / CR
    sa2 = 1 - ca * ca
    s = CR * ca + math.sqrt(ROD * ROD - CR * CR * sa2)
    return s, pin


def build_engine(parent):
    M = {
        'eng': mat('engine', '#4b5058'),
        'engT': mat('engine_t', '#4b5058', 0.22),
        'head': mat('head', '#3a3e45'),
        'piston': mat('piston', '#d3d7de'),
        'rod': mat('rod', '#a2a8b2'),
        'crank': mat('crank', '#2f6fe8'),
        'liner': mat('liner', '#8d939c', 0.35),
        'intake': mat('intake', '#5d636c'),
    }
    E = {}
    g = empty('G_engine', parent)
    E['group'] = g
    # crankcase
    E['case'] = mesh_obj('crankcase', bm_box(1.02, 0.40, 0.26, (-0.62, 0, CRANK_Z - 0.06)), M['eng'], g, bevel=0.03)
    E['pan'] = mesh_obj('oilpan', bm_box(0.9, 0.30, 0.08, (-0.62, 0, CRANK_Z - 0.21)), M['head'], g, bevel=0.02)
    # bank blocks + heads (oriented along bank axis)
    E['banks'] = []
    E['heads'] = []
    for side in (1, -1):
        d = bank_dir(side)
        rot = Matrix.Rotation(side * -BANK, 4, 'X')  # rotate Z axis toward d
        xc = -0.60 + side * BANK_OFF
        blk = bm_box(0.98, 0.17, 0.20, (0, 0, 0))
        bm_transform(blk, rot)
        c = Vector((xc, 0, CRANK_Z)) + d * 0.17
        ob = mesh_obj('bank', blk, M['eng'], g, loc=c, bevel=0.02)
        E['banks'].append(ob)
        hd = bm_box(1.0, 0.19, 0.07, (0, 0, 0))
        bm_transform(hd, rot)
        c2 = Vector((xc, 0, CRANK_Z)) + d * 0.305
        ob2 = mesh_obj('head', hd, M['head'], g, loc=c2, bevel=0.02)
        E['heads'].append(ob2)
    # intake plenum between banks + runners
    E['plenum'] = mesh_obj('plenum', bm_box(0.86, 0.16, 0.08, (-0.60, 0, CRANK_Z + 0.36)), M['intake'], g, bevel=0.03)
    # crankshaft (one object rotating around X)
    parts = [bm_cyl(0.022, 1.02, 16, 'X', (-0.60 - (-0.60), 0, 0))]
    cx0 = -0.60
    for i, x in enumerate(CYL_X):
        a = math.radians(THROW[i])
        pin = Vector((x - cx0, -CR * math.sin(a), CR * math.cos(a)))
        parts.append(bm_cyl(0.017, 0.09, 12, 'X', tuple(pin)))
        for dx in (-0.055, 0.055):
            web = bm_box(0.022, 0.05, CR + 0.05, (0, 0, (CR) / 2 - 0.0))
            bm_transform(web, Matrix.Rotation(a, 4, 'X'))
            bmesh.ops.translate(web, vec=(x - cx0 + dx, 0, 0), verts=web.verts)
            parts.append(web)
    # flywheel at rear end
    parts.append(bm_cyl(0.12, 0.03, 32, 'X', (-1.06 - cx0, 0, 0)))
    # pulley at front
    parts.append(bm_cyl(0.06, 0.03, 24, 'X', (-0.10 - cx0, 0, 0)))
    crank = mesh_obj('crankshaft', bm_merge(*parts), M['crank'], g, loc=(cx0, 0, CRANK_Z))
    E['crank'] = crank
    # pistons, rods, liners
    E['cyl'] = []
    for ci in cyl_info():
        d = bank_dir(ci['side'])
        q = d.to_track_quat('Z', 'X')
        base = Vector((ci['x'], 0, CRANK_Z))
        liner = bm_cyl(0.066, 0.17, 24, 'Z', (0, 0, 0))
        lob = mesh_obj('liner%d' % ci['num'], liner, M['liner'], g, smooth=True)
        lob.rotation_mode = 'QUATERNION'
        lob.rotation_quaternion = q
        lob.location = base + d * 0.215
        pis = bm_merge(bm_cyl(0.062, 0.06, 24, 'Z', (0, 0, 0.012)), bm_cyl(0.016, 0.07, 10, 'X', (0, 0, 0)))
        pob = mesh_obj('piston%d' % ci['num'], pis, M['piston'], g, smooth=True)
        pob.rotation_mode = 'QUATERNION'
        pob.rotation_quaternion = q
        rod = bm_box(0.022, 0.024, 1.0, (0, 0, 0.5))
        rob = mesh_obj('rod%d' % ci['num'], rod, M['rod'], g)
        rob.rotation_mode = 'QUATERNION'
        # spark marker for firing highlight (crown cap)
        E['cyl'].append(dict(info=ci, liner=lob, piston=pob, rod=rob, base=base, d=d))
    E['M'] = M
    return E


def pose_engine(E, phi):
    E['crank'].rotation_euler = (phi, 0, 0)
    for c in E['cyl']:
        ci = c['info']
        s, pin = piston_s(phi, THROW[ci['throw']], ci['side'])
        ppos = c['base'] + c['d'] * s
        c['piston'].location = ppos
        pinw = Vector((ci['x'], pin.y, CRANK_Z + pin.z))
        v = ppos - pinw
        c['rod'].location = pinw
        c['rod'].rotation_quaternion = v.normalized().to_track_quat('Z', 'X')
        c['rod'].scale = (1, 1, v.length)


def build_gearbox(parent):
    M = {
        'case': mat('gbcase', '#21a352'),
        'caseT': mat('gbcase_t', '#21a352', 0.25),
        'gear': mat('gear', '#7fe39a'),
        'shaft': mat('gbshaft', '#2a7a45'),
        'clutch1': mat('clutch1', '#3ccf6e'),
        'clutch2': mat('clutch2', '#3ccf6e'),
        'diff': mat('diff', '#5fbf7a'),
        'halfshaft': mat('halfshaft', '#5a5f68'),
    }
    G = {}
    g = empty('G_gearbox', parent)
    G['group'] = g
    # housing: rounded box
    G['case'] = mesh_obj('gbhousing', bm_box(0.98, 0.42, 0.38, ((GB_X0 + GB_X1) / 2, 0, 0.39)), M['case'], g, bevel=0.05, bevel_seg=3)
    # clutches (two packs side by side along x), rotate around X
    G['clutch'] = []
    for k, (x0, rr) in enumerate(((-1.10, 0.14), (-1.22, 0.125))):
        parts = []
        for j in range(3):
            parts.append(bm_cyl(rr, 0.014, 32, 'X', (x0 - j * 0.022, 0, 0)))
        parts.append(bm_cyl(rr * 0.35, 0.08, 16, 'X', (x0 - 0.022, 0, 0)))
        # radial slots to see rotation
        for j in range(6):
            a = j * math.pi / 3
            sl = bm_box(0.075, 0.018, rr * 0.9, (0, 0, rr * 0.45))
            bm_transform(sl, Matrix.Rotation(a, 4, 'X'))
            bmesh.ops.translate(sl, vec=(x0 - 0.022, 0, 0), verts=sl.verts)
            parts.append(sl)
        ob = mesh_obj('clutch%d' % (k + 1), bm_merge(*parts), M['clutch%d' % (k + 1)], g, loc=(0, 0, IN_Z))
        G['clutch'].append(ob)
    # shafts
    G['inshaft'] = mesh_obj('inshaft', bm_cyl(0.022, 0.95, 16, 'X', (-1.48, 0, 0)), M['shaft'], g, loc=(0, 0, IN_Z))
    G['outshaft'] = mesh_obj('outshaft', bm_cyl(0.022, 0.72, 16, 'X', (-1.62, 0, 0)), M['shaft'], g, loc=(0, 0, OUT_Z))
    # 7 gear pairs
    G['gears'] = []
    for k in range(7):
        gear_no = k + 1
        r_in = 0.050 + k * 0.0095
        r_out = (IN_Z - OUT_Z) - r_in
        t_in = max(10, int(round(r_in / 0.0045)))
        t_out = max(10, int(round(t_in * r_out / r_in)))
        x = GEAR_X[k]
        gi = mesh_obj('gin%d' % gear_no, bm_gear(r_in, t_in, 0.045, 'X'), M['gear'], g, loc=(x, 0, IN_Z))
        go = mesh_obj('gout%d' % gear_no, bm_gear(r_out, t_out, 0.045, 'X'), M['gear'], g, loc=(x, 0, OUT_Z))
        G['gears'].append(dict(n=gear_no, gi=gi, go=go, r_in=r_in, r_out=r_out, t_in=t_in, t_out=t_out))
    # differential ring gear (axis Y) at rear axle line
    G['diff'] = mesh_obj('diffring', bm_gear(0.11, 30, 0.04, 'Y'), M['diff'], g, loc=(-1.31, 0.12, 0.35))
    # halfshafts to rear wheels
    G['halfshafts'] = []
    for sy in (1, -1):
        hs = mesh_obj('halfshaft', bm_cyl(0.028, 0.62, 16, 'Y', (0, 0, 0)), M['halfshaft'], g, loc=(-1.31, sy * 0.50, 0.35))
        G['halfshafts'].append(hs)
    G['M'] = M
    return G


def pose_gearbox(G, phi_in, wheel_angle):
    for c in G['clutch']:
        c.rotation_euler = (phi_in, 0, 0)
    G['inshaft'].rotation_euler = (phi_in, 0, 0)
    for gr in G['gears']:
        gr['gi'].rotation_euler = (phi_in, 0, 0)
        gr['go'].rotation_euler = (-phi_in * gr['r_in'] / gr['r_out'] + math.pi / gr['t_out'], 0, 0)
    G['outshaft'].rotation_euler = (-phi_in * 0.6, 0, 0)
    G['diff'].rotation_euler = (0, wheel_angle, 0)
    for hs in G['halfshafts']:
        hs.rotation_euler = (0, wheel_angle, 0)


# ---------- driveline path for the "power" light line (car frame) ----------
def power_path(to_rear=True):
    p = [Vector((-0.10, 0, CRANK_Z)), Vector((-1.06, 0, CRANK_Z)),
         Vector((-1.12, 0, IN_Z)), Vector((GEAR_X[2], 0, IN_Z)),
         Vector((GEAR_X[2], 0, OUT_Z)), Vector((-1.31, 0, OUT_Z)), Vector((-1.31, 0, 0.35))]
    return p


def wheel_paths():
    return [[Vector((-1.31, 0, 0.35)), Vector((-1.31, 0.84, 0.35))],
            [Vector((-1.31, 0, 0.35)), Vector((-1.31, -0.84, 0.35))]]


def resample(pts, step=0.01):
    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        L = (b - a).length
        n = max(1, int(L / step))
        for i in range(1, n + 1):
            out.append(a.lerp(b, i / n))
    return out


# ---------- single cylinder callout (big, detailed) ----------
def build_callout(parent):
    M = {
        'wall': mat('cyl_wall', '#7d838d'),
        'head': mat('cyl_head', '#4b5058'),
        'piston': mat('piston', '#d3d7de'),
        'rod': mat('rod', '#a2a8b2'),
        'crank': mat('crank', '#2f6fe8'),
        'valve': mat('valve', '#b9bec6'),
        'plug': mat('plug', '#f4f4f0'),
        'plugtip': mat('plugtip', '#8a8f98'),
        'injector': mat('injector', '#2b2e35'),
        'port': mat('port', '#5d636c'),
    }
    R = 0.40     # bore radius
    Cc = {}
    g = empty('G_callout', parent)
    Cc['group'] = g
    # back half of cylinder wall (cut-away): half tube open toward -Y
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=R + 0.08, radius2=R + 0.08, depth=1.5)
    kill = [v for v in bm.verts if v.co.y < -0.001]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    # thicken
    res = bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.08)
    bmesh.ops.translate(bm, vec=(0, 0, 0.75 + 0.35), verts=bm.verts)
    Cc['wall'] = mesh_obj('cyl_wall', bm, M['wall'], g, smooth=True)
    # head (half block) with ports
    hb = bm_box(1.25, 0.46, 0.28, (0, 0.23, 1.98))
    Cc['head'] = mesh_obj('cyl_head', hb, M['head'], g, bevel=0.03)
    # intake port tube (left) & exhaust port (right)
    ip = bm_tube_path([Vector((-1.25, 0, 2.35)), Vector((-0.6, 0, 2.15)), Vector((-0.22, 0, 1.92))], 0.11, 20)
    Cc['inport'] = mesh_obj('inport', ip, M['port'], g, smooth=True)
    ep = bm_tube_path([Vector((0.22, 0, 1.92)), Vector((0.6, 0, 2.15)), Vector((1.25, 0, 2.35))], 0.11, 20)
    Cc['export'] = mesh_obj('export', ep, M['port'], g, smooth=True)
    # valves (stem + head), move along their axis
    Cc['valves'] = []
    for sx in (-1, 1):
        axis = Vector((sx * 0.25, 0, 1)).normalized()
        v = bm_merge(bm_cyl(0.11, 0.025, 24, 'Z', (0, 0, 0)), bm_cyl(0.018, 0.5, 8, 'Z', (0, 0, 0.26)))
        ob = mesh_obj('valve', v, M['valve'], g, smooth=True)
        ob.rotation_mode = 'QUATERNION'
        ob.rotation_quaternion = axis.to_track_quat('Z', 'X')
        base = Vector((sx * 0.20, 0, 1.86))
        ob.location = base
        Cc['valves'].append(dict(ob=ob, base=base, axis=axis))
    # spark plug at top center
    plug = bm_merge(bm_cyl(0.05, 0.35, 16, 'Z', (0, 0, 2.20)), bm_cyl(0.07, 0.12, 6, 'Z', (0, 0, 2.42)))
    Cc['plug'] = mesh_obj('plug', plug, M['plug'], g, smooth=False)
    Cc['plugtip'] = mesh_obj('plugtip', bm_cyl(0.02, 0.08, 8, 'Z', (0, 0, 1.86)), M['plugtip'], g)
    # injector (pointing into intake port)
    inj = bm_cyl(0.035, 0.32, 12, 'Z', (0, 0, 0))
    io = mesh_obj('injector', inj, M['injector'], g, loc=(-0.55, 0, 2.35), smooth=True)
    io.rotation_euler = (0, math.radians(-30), 0)
    Cc['injector'] = io
    # piston, rod, crank
    pis = bm_merge(bm_cyl(R - 0.01, 0.40, 40, 'Z', (0, 0, 0)), bm_cyl(0.07, 0.5, 12, 'Y', (0, 0, -0.08)))
    for k in range(3):
        pis = bm_merge(pis, bm_cyl(R, 0.02, 40, 'Z', (0, 0, 0.13 - k * 0.07)))
    Cc['piston'] = mesh_obj('cpiston', pis, M['piston'], g, smooth=True)
    Cc['rod'] = mesh_obj('crod', bm_box(0.12, 0.08, 1.0, (0, 0, 0.5)), M['rod'], g)
    Cc['rod'].rotation_mode = 'QUATERNION'
    cparts = [bm_cyl(0.32, 0.08, 40, 'Y', (0, 0.18, 0)), bm_cyl(0.07, 0.5, 16, 'Y', (0, 0.32, 0)),
              bm_cyl(0.07, 0.25, 16, 'Y', (0.0, 0.05, 0.25))]
    Cc['crank'] = mesh_obj('ccrank', bm_merge(*cparts), M['crank'], g, loc=(0, 0, 0.0), smooth=True)
    Cc['R'] = R
    Cc['M'] = M
    return Cc


C_CR, C_ROD = 0.25, 1.05


def pose_callout(Cc, theta, intake_open, exhaust_open):
    """theta: crank angle, 0 = TDC. Crank rotates about Y."""
    Cc['crank'].rotation_euler = (0, theta, 0)
    pin = Vector((C_CR * math.sin(theta), 0.0, C_CR * math.cos(theta)))
    # crank pin is at z=0.25 in local (0.05 offset y) — consistent with C_CR
    s = C_CR * math.cos(theta) + math.sqrt(C_ROD ** 2 - (C_CR * math.sin(theta)) ** 2)
    ppos = Vector((0, 0, s))
    Cc['piston'].location = ppos + Vector((0, 0, 0.08))
    v = ppos - pin
    Cc['rod'].location = Vector((pin.x, -0.06, pin.z))
    Cc['rod'].rotation_quaternion = v.normalized().to_track_quat('Z', 'X')
    Cc['rod'].scale = (1, 1, v.length)
    for vv, op in zip(Cc['valves'], (intake_open, exhaust_open)):
        vv['ob'].location = vv['base'] - vv['axis'] * 0.12 * op
    return s
