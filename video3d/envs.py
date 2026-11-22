"""Toy diorama boards and helper props."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
from util import *

random.seed(7)


def M():
    return {
        'asphalt': mat('asphalt', '#5b616c'),
        'asphalt2': mat('asphalt2', '#4f5560'),
        'line': mat('roadline', '#f6f6f2'),
        'yline': mat('roadyline', '#ffd23a'),
        'side': mat('sidewalk', '#cfd4db'),
        'grass': mat('grass', '#72c66e'),
        'grass2': mat('grass2', '#5fb35d'),
        'trunk': mat('trunk', '#9a6a3f'),
        'leaf': mat('leaf', '#3fae4f'),
        'palm': mat('palmleaf', '#2f9e45'),
        'kerbR': mat('kerbred', '#e2312f'),
        'kerbW': mat('kerbwhite', '#f7f7f7'),
        'cone': mat('cone', '#ff8a1c'),
        'flagB': mat('flagblack', '#15161a'),
        'flagW': mat('flagwhite', '#fafafa'),
        'pole': mat('pole', '#9aa0a8'),
        'mount': mat('mount', '#8fb6a0'),
        'mount2': mat('mount2', '#a7c7b5'),
        'stand': mat('stand', '#7e8794'),
        'water': mat('water', '#6fc3e8'),
    }


HOUSE_COLS = ['#ff6f91', '#4fc3f7', '#ffd54f', '#81c784', '#ba68c8', '#ff8a65', '#4db6ac', '#f06292', '#9575cd', '#aed581']


def slab(name, sx, sy, m, parent, center=(0, 0), top=0.0, h=0.25, bevel=0.04):
    return mesh_obj(name, bm_box(sx, sy, h, (center[0], center[1], top - h / 2)), m, parent, bevel=bevel)


def flat(name, sx, sy, m, parent, center=(0, 0), z=0.006, h=0.012, rot=0.0):
    b = bm_box(sx, sy, h, (0, 0, 0))
    ob = mesh_obj(name, b, m, parent, loc=(center[0], center[1], z))
    ob.rotation_euler = (0, 0, rot)
    return ob


def house(parent, x, y, w, d, h, col, rot=0.0):
    g = empty('house', parent, (x, y, 0))
    g.rotation_euler = (0, 0, rot)
    mb = mat('house_' + col, col)
    mesh_obj('hbody', bm_box(w, d, h, (0, 0, h / 2)), mb, g, bevel=0.05)
    roof = bm_prism([(-w / 2 - 0.12, 0), (w / 2 + 0.12, 0), (0, h * 0.45)], d + 0.2, 'XZ', 0)
    mesh_obj('hroof', roof, mat('roof', '#d9534f'), g, loc=(0, 0, h), bevel=0.03)
    mesh_obj('hdoor', bm_box(0.04, 0.5, 0.9, (0, 0, 0.45)), mat('door', '#6d4c41'), g, loc=(w / 2, 0, 0))
    for sy in (-1, 1):
        mesh_obj('hwin', bm_box(0.04, 0.45, 0.45, (0, 0, 0)), mat('win', '#e3f2fd'), g, loc=(w / 2, sy * d * 0.3, h * 0.6))
    return g


def tree(parent, x, y, s=1.0):
    g = empty('tree', parent, (x, y, 0))
    mm = M()
    mesh_obj('trunk', bm_cyl(0.12 * s, 1.0 * s, 10, 'Z', (0, 0, 0.5 * s)), mm['trunk'], g, smooth=True)
    mesh_obj('crown', bm_sphere(0.75 * s, (0, 0, 1.5 * s), 16, 10), mm['leaf'], g, smooth=True)
    return g


def palm(parent, x, y, s=1.0):
    g = empty('palm', parent, (x, y, 0))
    mm = M()
    mesh_obj('ptrunk', bm_cyl(0.11 * s, 3.0 * s, 10, 'Z', (0, 0, 1.5 * s), r2=0.08 * s), mm['trunk'], g, smooth=True)
    for k in range(6):
        a = 2 * math.pi * k / 6
        lf = bm_box(1.5 * s, 0.32 * s, 0.05 * s, (0.75 * s, 0, 0))
        bm_transform(lf, Matrix.Rotation(math.radians(-22), 4, 'Y'))
        bm_transform(lf, Matrix.Rotation(a, 4, 'Z'))
        bmesh.ops.translate(lf, vec=(0, 0, 3.0 * s), verts=lf.verts)
        mesh_obj('pleaf', lf, mm['palm'], g, bevel=0.02)
    return g


def cone(parent, x, y):
    mm = M()
    return mesh_obj('cone', bm_merge(bm_cyl(0.22, 0.6, 16, 'Z', (0, 0, 0.3), r2=0.03), bm_box(0.45, 0.45, 0.05, (0, 0, 0.025))), mm['cone'], parent, loc=(x, y, 0), smooth=True)


def mountain(parent, x, y, r, h, m):
    return mesh_obj('mount', bm_cyl(r, h, 7, 'Z', (0, 0, h / 2), r2=0.0), m, parent, loc=(x, y, 0))


# ---------------------------------------------------------------- boards
def road_markings(parent, length, period, lanes_y, edge_y, dash=2.0, mline=None, mm=None):
    for k in range(int(length / period) + 1):
        x = -length / 2 + k * period
        for ly in lanes_y:
            flat('dash', dash, 0.14, mm['line'] if mline is None else mline, parent, (x, ly))


def board_curve():
    """Curved road (studio scene 2). Arc centered at (0, R) local."""
    mm = M()
    g = empty('B_curve')
    R = 9.0
    rot = empty('curve_rot', g, (0, R, 0))  # rotates around curve center
    bm = bmesh.new()
    a0, a1 = math.radians(-120), math.radians(60)
    n = 60
    inner, outer = R - 2.4, R + 2.4
    vs = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        ca, sa = math.sin(a), -math.cos(a)
        vs.append((bm.verts.new((inner * ca, inner * sa, 0.0)), bm.verts.new((outer * ca, outer * sa, 0.0))))
    for i in range(n):
        bm.faces.new((vs[i][0], vs[i][1], vs[i + 1][1], vs[i + 1][0]))
    res = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    nv = [e for e in res['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, -0.18), verts=nv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh_obj('curveroad', bm, mm['asphalt'], rot)
    # dashed center line
    for i in range(0, 40):
        a = a0 + (a1 - a0) * (i + 0.25) / 40
        ob = flat('cdash', 0.9, 0.12, mm['line'], rot, (R * math.sin(a), -R * math.cos(a)), z=0.008)
        ob.rotation_euler = (0, 0, a)
    for rr in (inner + 0.2, outer - 0.2):
        for i in range(0, 80):
            a = a0 + (a1 - a0) * (i + 0.5) / 80
            ob = flat('cedge', (a1 - a0) / 80 * rr * 1.02, 0.1, mm['line'], rot, (rr * math.sin(a), -rr * math.cos(a)), z=0.008)
            ob.rotation_euler = (0, 0, a)
    return dict(group=g, rot=rot, R=R)


def board_track():
    """Straight race strip for the 0-100 run (scene 5). Scroll along X."""
    mm = M()
    g = empty('B_track')
    L = 140
    slab('grass', L, 30, mm['grass'], g, top=-0.02, h=0.3)
    slab('road', L, 9, mm['asphalt'], g, top=0.0, h=0.25, bevel=0.0)
    sc = empty('track_scroll', g)
    P = 6.0
    for k in range(int(L / P) + 2):
        x = -L / 2 + k * P
        flat('dash', 3.0, 0.2, mm['line'], sc, (x, 0))
        for sy in (1, -1):
            # kerbs alternate red / white
            flat('kerbR', P / 2, 0.6, mm['kerbR'], sc, (x - P / 4, sy * 4.8), z=0.03, h=0.06)
            flat('kerbW', P / 2, 0.6, mm['kerbW'], sc, (x + P / 4, sy * 4.8), z=0.03, h=0.06)
    # far-side props (trees) on a slower parallax? same speed for correctness
    sc2 = empty('track_scroll_props', g)
    P2 = 12.0
    for k in range(int(L / P2) + 2):
        x = -L / 2 + k * P2
        tree(sc2, x, 9.5, 1.2)
        tree(sc2, x + 6, 12.5, 1.5)
    # start line
    return dict(group=g, scroll=[(sc, P), (sc2, P2)])


def board_city():
    """Top-view intersection for counter-phase rear steering (scene 6)."""
    mm = M()
    g = empty('B_city')
    slab('base', 36, 36, mm['side'], g, center=(3.3, 1.9), top=-0.01, h=0.3)
    # road A along X (lanes y in [-1.9, 5.7]), road B along Y (x in [0.3, 7.9])
    slab('roadA', 36, 7.6, mm['asphalt'], g, center=(3.3, 1.9), top=0.0, h=0.05, bevel=0.0)
    slab('roadB1', 7.6, 14.2, mm['asphalt'], g, center=(3.3, 12.8), top=0.0, h=0.05, bevel=0.0)
    slab('roadB2', 7.6, 14.2, mm['asphalt'], g, center=(3.3, -9.0), top=0.0, h=0.05, bevel=0.0)
    for x in [-13, -10, -7, -4, 10, 13, 16, 19]:
        flat('dA', 1.6, 0.14, mm['line'], g, (x, 1.9))
    for y in [-14, -11, -8, -5, 9, 12, 15, 18]:
        flat('dB', 0.14, 1.6, mm['line'], g, (3.3, y))
    # zebra crossings
    for i in range(6):
        flat('zebra', 1.2, 0.45, mm['line'], g, (-1.4, -1.4 + i * 1.25))
    # blocks with buildings
    cols = HOUSE_COLS
    k = 0
    for bx, by in ((-7.7, -7.1), (-7.7, 10.9), (14.3, -7.1), (14.3, 10.9)):
        for i in range(2):
            for j in range(2):
                h = random.uniform(1.6, 3.4)
                c = cols[k % len(cols)]
                k += 1
                mesh_obj('bld', bm_box(3.2, 3.2, h, (bx + (i - 0.5) * 4.2, by + (j - 0.5) * 4.2, h / 2)), mat('house_' + c, c), g, bevel=0.08)
    for (x, y) in ((-2.3, -2.9), (-6.0, -2.9), (-2.3, 6.7), (8.9, -2.9), (8.9, 6.7), (12.0, 6.7)):
        tree(g, x, y, 0.8)
    return dict(group=g)


def board_highway():
    mm = M()
    g = empty('B_highway')
    L = 120
    slab('grass', L, 40, mm['grass'], g, top=-0.02, h=0.3)
    slab('road', L, 15.0, mm['asphalt'], g, center=(0, 1.75), top=0.0, h=0.2, bevel=0.0)
    sc = empty('hw_scroll', g)
    P = 8.0
    lanes = [-3.5 + 1.75 + 0.0, 0 + 1.75, 3.5 + 1.75]  # dividers between 4 lanes
    for k in range(int(L / P) + 2):
        x = -L / 2 + k * P
        for ly in (-1.75, 1.75, 5.25):
            flat('dash', 3.0, 0.15, mm['line'], sc, (x, ly))
    for sy in (-5.3, 8.8):
        flat('edge', L, 0.18, mm['line'], g, (0, sy))
    sc2 = empty('hw_props', g)
    P2 = 16.0
    for k in range(int(L / P2) + 2):
        x = -L / 2 + k * P2
        tree(sc2, x, -9, 1.1)
        tree(sc2, x + 8, 12.5, 1.1)
    return dict(group=g, scroll=[(sc, P), (sc2, P2)])


def board_strada():
    mm = M()
    g = empty('B_strada')
    L = 90
    slab('base', L, 26, mm['side'], g, top=-0.02, h=0.3)
    slab('road', L, 8, mm['asphalt'], g, top=0.0, h=0.2, bevel=0.0)
    sc = empty('st_scroll', g)
    P = 10.0
    for k in range(int(L / P) + 2):
        x = -L / 2 + k * P
        flat('dash', 2.5, 0.15, mm['line'], sc, (x, 0))
        palm(sc, x, 5.2, 0.9)
        palm(sc, x + 5, 7.0, 0.8)
        c1 = HOUSE_COLS[k % len(HOUSE_COLS)]
        c2 = HOUSE_COLS[(k + 4) % len(HOUSE_COLS)]
        mesh_obj('bld', bm_box(4.0, 3.5, 2.6 + (k % 3) * 0.8, (x + 2, 9.0, (2.6 + (k % 3) * 0.8) / 2)), mat('house_' + c1, c1), sc, bevel=0.08)
        mesh_obj('bld', bm_box(4.0, 3.5, 2.2 + (k % 2) * 1.0, (x + 6, 13.0, (2.2 + (k % 2) * 1.0) / 2)), mat('house_' + c2, c2), sc, bevel=0.08)
    return dict(group=g, scroll=[(sc, P)])


def board_sport():
    mm = M()
    g = empty('B_sport')
    L = 90
    slab('base', L, 30, mm['grass'], g, top=-0.02, h=0.3)
    slab('road', L, 8, mm['asphalt'], g, top=0.0, h=0.2, bevel=0.0)
    sc = empty('sp_scroll', g)
    P = 12.0
    for k in range(int(L / P) + 2):
        x = -L / 2 + k * P
        flat('dash', 3.0, 0.15, mm['yline'], sc, (x, 0))
        for sy in (4.4, -4.4):
            cone(sc, x + (3 if sy > 0 else 9), sy)
        mesh_obj('hill', bm_sphere(3.0, (x + 4, 11, -1.2), 20, 10), mm['grass2'], sc, smooth=True)
    # winding road in the background (static decor)
    pts = []
    for i in range(80):
        xx = -40 + i
        pts.append(Vector((xx, 16 + 3.0 * math.sin(xx * 0.18), 0.02)))
    mesh_obj('wind', bm_tube_path(pts, 0.9, 6), mm['asphalt'], g)
    for i in range(4):
        mountain(g, -30 + i * 18, 26, 7, 8 + (i % 2) * 3, mm['mount'])
    return dict(group=g, scroll=[(sc, P)])


def board_corsa():
    mm = M()
    g = empty('B_corsa')
    L = 90
    slab('base', L, 30, mm['grass'], g, top=-0.02, h=0.3)
    slab('road', L, 11, mm['asphalt'], g, top=0.0, h=0.2, bevel=0.0)
    sc = empty('co_scroll', g)
    P = 30.0
    for k in range(int(L / P) + 2):
        x = -L / 2 + k * P
        # kerbs
        for j in range(10):
            for sy in (5.8, -5.8):
                flat('kerb', 1.5, 0.7, mm['kerbR'] if j % 2 == 0 else mm['kerbW'], sc, (x + j * 3 + 0.75, sy), z=0.03, h=0.06)
                flat('kerb', 1.5, 0.7, mm['kerbW'] if j % 2 == 0 else mm['kerbR'], sc, (x + j * 3 + 2.25, sy), z=0.03, h=0.06)
        # checkered start line
        for i in range(2):
            for j in range(16):
                flat('chk', 0.6, 0.68, mm['flagB'] if (i + j) % 2 == 0 else mm['flagW'], sc, (x + 10 + i * 0.6, -5.1 + j * 0.68))
        # gantry with checkered flag
        mesh_obj('pole', bm_cyl(0.12, 6.0, 10, 'Z', (x + 10.3, 6.6, 3.0)), mm['pole'], sc, smooth=True)
        for i in range(6):
            for j in range(4):
                mesh_obj('flag', bm_box(0.05, 0.5, 0.45, (x + 10.3, 6.6 - 0.35 - i * 0.5, 5.7 - j * 0.45)), mm['flagB'] if (i + j) % 2 == 0 else mm['flagW'], sc)
        # grandstand
        mesh_obj('stand', bm_prism([(0, 0), (6, 0), (6, 3.5)], 20, 'YZ', 0), mm['stand'], sc, loc=(x + 20, 9.0, 0))
    return dict(group=g, scroll=[(sc, P)])


def board_barrio():
    mm = M()
    g = empty('B_barrio')
    slab('base', 30, 22, mm['side'], g, top=-0.02, h=0.3)
    slab('road', 30, 7, mm['asphalt'], g, top=0.0, h=0.1, bevel=0.0)
    houses = []
    for i in range(7):
        x = -12 + i * 4.0
        c1 = HOUSE_COLS[i % len(HOUSE_COLS)]
        c2 = HOUSE_COLS[(i + 5) % len(HOUSE_COLS)]
        houses.append(house(g, x, 6.0, 3.2, 3.0, 2.0 + (i % 3) * 0.6, c1, rot=-math.pi / 2))
        houses.append(house(g, x + 2, -6.0, 3.2, 3.0, 2.0 + ((i + 1) % 3) * 0.6, c2, rot=math.pi / 2))
    for x in (-13, -5, 3, 11):
        flat('dash', 1.8, 0.14, mm['line'], g, (x, 0))
    return dict(group=g, houses=houses)


def board_open():
    mm = M()
    g = empty('B_open')
    slab('base', 140, 60, mm['grass'], g, center=(30, 0), top=-0.03, h=0.3)
    slab('road', 140, 7, mm['asphalt'], g, center=(30, 0), top=0.0, h=0.12, bevel=0.0)
    for k in range(18):
        flat('dash', 2.5, 0.15, mm['yline'], g, (-35 + k * 7.5, 0))
    for i in range(7):
        mountain(g, 20 + i * 14, 26 + (i % 2) * 6, 9, 10 + (i % 3) * 4, mm['mount'] if i % 2 else mm['mount2'])
        mountain(g, 26 + i * 14, -26 - (i % 2) * 6, 9, 9 + (i % 3) * 4, mm['mount2'] if i % 2 else mm['mount'])
    for i in range(10):
        tree(g, -20 + i * 9, 6.5, 0.9)
        tree(g, -16 + i * 9, -6.5, 0.9)
    return dict(group=g)


# ---------------------------------------------------------------- props
def build_balance():
    g = empty('P_balance')
    mf = mat('fulcrum', '#7e57c2')
    mp = mat('plank', '#b0bec5')
    tri = bm_prism([(-0.55, 0), (0.55, 0), (0, 0.75)], 1.0, 'XZ', 0)
    mesh_obj('fulcrum', tri, mf, g, loc=(0, 0, -0.95), bevel=0.04)
    plank_piv = empty('plank_piv', g, (0, 0, -0.2))
    mesh_obj('plank', bm_box(5.0, 2.2, 0.12, (0, 0, -0.06)), mp, plank_piv, bevel=0.04)
    return dict(group=g, piv=plank_piv)


def build_grip_arrows():
    ma = mat('griparrow', '#ff3b30')
    out = []
    for i in range(4):
        b = bm_flat_arrow(1.1, 0.16, 0.35, 0.42, 0.05)
        out.append(mesh_obj('grip', b, ma, None))
    return out


def build_air_arrows(n=8):
    mb = mat('air', '#2f8cff')
    out = []
    for i in range(n):
        b = bm_arrow(0.34, 0.025, 0.12, 0.06)
        out.append(mesh_obj('airarrow', b, mb, None, smooth=True))
    return out


def build_dashes(n, color='#2f8cff', name='airdash', r=0.035, length=0.45):
    mb = mat(name, color)
    out = []
    for i in range(n):
        b = bm_cyl(r, length, 8, 'X', (0, 0, 0))
        out.append(mesh_obj(name, b, mb, None, smooth=True))
    return out


def build_drops(n):
    mo = mat('fuel', '#ff9a1f')
    out = []
    for i in range(n):
        b = bm_merge(bm_sphere(0.05, (0, 0, 0), 12, 8), bm_cyl(0.05, 0.07, 12, 'Z', (0, 0, 0.035), r2=0.0))
        out.append(mesh_obj('drop', b, mo, None, smooth=True))
    return out


def build_star(name, color, r1, r2, n=8, h=0.04):
    poly = []
    for i in range(2 * n):
        a = math.pi * i / n
        rr = r1 if i % 2 == 0 else r2
        poly.append((rr * math.cos(a), rr * math.sin(a)))
    b = bm_prism(poly, h, 'XZ', 0)
    return mesh_obj(name, b, mat(name, color), None)


def build_down_arrows(n=5):
    mr = mat('downarrow', '#ff2d2d')
    out = []
    for i in range(n):
        b = bm_arrow(0.6, 0.04, 0.18, 0.1)
        out.append(mesh_obj('downarrow', b, mr, None, smooth=True))
    return out


def build_ring(radius, width=0.15, dashes=36, color='#fff36b'):
    g = empty('P_ring')
    m = mat('ring', color)
    for i in range(dashes):
        a = 2 * math.pi * i / dashes
        L = 2 * math.pi * radius / dashes * 0.6
        ob = flat('ringdash', L, width, m, g, (radius * math.cos(a), radius * math.sin(a)), z=0.02, h=0.02, rot=a + math.pi / 2)
    return g


def build_selector():
    """Steering wheel with round mode selector (no logos)."""
    g = empty('P_selector')
    mbk = mat('swblack', '#202126')
    mgr = mat('swgrey', '#55595f')
    # rim (torus approximated by tube)
    pts = [Vector((0, 0.9 * math.cos(2 * math.pi * i / 64), 0.9 * math.sin(2 * math.pi * i / 64))) for i in range(65)]
    mesh_obj('swrim', bm_tube_path(pts, 0.11, 16), mbk, g, smooth=True)
    mesh_obj('swhub', bm_box(0.18, 0.9, 0.7, (0.0, 0, -0.15)), mgr, g, bevel=0.08)
    for a in (0, math.pi, -math.pi / 2):
        sp = bm_box(0.08, 0.82, 0.12, (0, 0.41, 0))
        bm_transform(sp, Matrix.Rotation(a, 4, 'X'))
        mesh_obj('swspoke', sp, mgr, g, bevel=0.03)
    # dial base and knob (rotates around X)
    mesh_obj('dialbase', bm_cyl(0.20, 0.06, 32, 'X', (-0.10, 0.2, -0.25)), mbk, g, smooth=True)
    knob = empty('dialknob', g, (-0.14, 0.2, -0.25))
    mesh_obj('knob', bm_cyl(0.16, 0.08, 32, 'X', (0, 0, 0)), mat('knob', '#d62828'), knob, smooth=True)
    mesh_obj('knobptr', bm_box(0.03, 0.05, 0.13, (-0.045, 0, 0.075)), mat('knobptr', '#ffffff'), knob)
    # three colored marks on the base
    marks = []
    for col, a in (('#2ecc71', 50), ('#ff9800', 0), ('#e53935', -50)):
        m = mesh_obj('mark', bm_box(0.03, 0.06, 0.07, (0, 0, 0)), mat('mark' + col, col), g,
                     loc=(-0.14, 0.2 + 0.17 * math.sin(math.radians(-a)), -0.25 + 0.17 * math.cos(math.radians(a))))
        marks.append(m)
    return dict(group=g, knob=knob)
