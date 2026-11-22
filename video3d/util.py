import bpy, bmesh, math
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree


def srgb2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexcol(h, a=1.0):
    h = h.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return (srgb2lin(r), srgb2lin(g), srgb2lin(b), a)


MATS = {}


def mat(name, hexc=None, a=1.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.diffuse_color = hexcol(hexc, a)
    m.roughness = 0.6
    m.metallic = 0.0
    MATS[name] = m
    m['base'] = list(m.diffuse_color)
    return m


def set_alpha(m, a):
    c = list(m['base'])
    c[3] = a
    m.diffuse_color = c


COLL = None


def link(ob):
    bpy.context.scene.collection.objects.link(ob)


def empty(name, parent=None, loc=(0, 0, 0)):
    ob = bpy.data.objects.new(name, None)
    link(ob)
    ob.parent = parent
    ob.location = loc
    return ob


def mesh_obj(name, bm, material, parent=None, loc=(0, 0, 0), smooth=False,
             bevel=0.0, bevel_seg=2, harden=True, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    link(ob)
    if isinstance(material, (list, tuple)):
        for m in material:
            me.materials.append(m)
    else:
        me.materials.append(material)
    if bevel > 0:
        md = ob.modifiers.new('bev', 'BEVEL')
        md.width = bevel
        md.segments = bevel_seg
        md.limit_method = 'ANGLE'
        md.angle_limit = math.radians(35)
        md.harden_normals = harden
        bake(ob)
        smooth = True
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
    ob.parent = parent
    ob.location = loc
    ob.rotation_euler = rot
    me = ob.data
    # object-linked materials for per-object highlight
    for i, s in enumerate(ob.material_slots):
        s.link = 'OBJECT'
        s.material = me.materials[i]
    ob['basemats'] = [m.name for m in me.materials]
    return ob


def bake(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    me.materials.clear()
    for m in old.materials:
        me.materials.append(m)


def bm_box(sx, sy, sz, center=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    return bm


def bm_cyl(r, depth, seg=32, axis='Z', center=(0, 0, 0), r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=r if r2 is None else r2, depth=depth)
    if axis == 'X':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'Y'))
    elif axis == 'Y':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'X'))
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    return bm


def bm_sphere(r, center=(0, 0, 0), seg=24, rings=12):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    return bm


def bm_merge(*bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new('tmp')
        b.to_mesh(me)
        b.free()
        out.from_mesh(me)
        bpy.data.meshes.remove(me)
    return out


def bm_transform(bm, M):
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return bm


def bm_prism(poly2d, depth, plane='XZ', offset=0.0):
    """Extrude a 2D polygon. plane XZ: poly (x,z), extruded along Y centered at offset."""
    bm = bmesh.new()
    vs = []
    for (a, b) in poly2d:
        if plane == 'XZ':
            vs.append(bm.verts.new((a, offset - depth / 2, b)))
        elif plane == 'YZ':
            vs.append(bm.verts.new((offset - depth / 2, a, b)))
        else:  # XY
            vs.append(bm.verts.new((a, b, offset - depth / 2)))
    f = bm.faces.new(vs)
    vec = {'XZ': (0, depth, 0), 'YZ': (depth, 0, 0), 'XY': (0, 0, depth)}[plane]
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    nv = [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=vec, verts=nv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_tube_path(pts, r, seg=12, closed=False):
    """Tube along a list of Vector points."""
    bm = bmesh.new()
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        if i == 0:
            t = (pts[1] - pts[0])
        elif i == n - 1:
            t = (pts[-1] - pts[-2])
        else:
            t = (pts[i + 1] - pts[i - 1])
        t = t.normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(up).normalized()
        v = t.cross(u).normalized()
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            ring.append(bm.verts.new(p + (u * math.cos(a) + v * math.sin(a)) * r))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(seg):
            a, b = rings[i][k], rings[i][(k + 1) % seg]
            c, d = rings[i + 1][(k + 1) % seg], rings[i + 1][k]
            bm.faces.new((a, b, c, d))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_gear(r, teeth, thick, axis='X', center=(0, 0, 0), tooth_h=None, bore=None):
    th = tooth_h if tooth_h else min(0.012, r * 0.18)
    bm = bmesh.new()
    pts = []
    n = teeth * 4
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r + th / 2 if (i % 4) in (1, 2) else r - th / 2
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    vs = [bm.verts.new((x, y, -thick / 2)) for x, y in pts]
    f = bm.faces.new(vs)
    res = bmesh.ops.extrude_face_region(bm, geom=[f])
    nv = [e for e in res['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, thick), verts=nv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if axis == 'X':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'Y'))
    elif axis == 'Y':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'X'))
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    return bm


def bm_arrow(length, r=0.03, head=0.09, head_r=0.07, seg=16):
    """Arrow along +X starting at origin."""
    shaft = bm_cyl(r, length - head, seg, 'X', ((length - head) / 2, 0, 0))
    tip = bm_cyl(head_r, head, seg, 'X', (length - head / 2, 0, 0), r2=0.0)
    return bm_merge(shaft, tip)


def bm_flat_arrow(length, w=0.12, head=0.3, head_w=0.32, h=0.03):
    poly = [(0, -w / 2), (length - head, -w / 2), (length - head, -head_w / 2), (length, 0),
            (length - head, head_w / 2), (length - head, w / 2), (0, w / 2)]
    return bm_prism(poly, h, 'XY', h / 2)


def look_rot(direction, up=Vector((0, 0, 1))):
    return direction.to_track_quat('X', 'Z')


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def smoother(x):
    x = max(0.0, min(1.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)


def ramp(t, t0, t1):
    if t1 == t0:
        return 1.0 if t >= t1 else 0.0
    return max(0.0, min(1.0, (t - t0) / (t1 - t0)))


def back_out(x, s=1.70158):
    x = max(0.0, min(1.0, x))
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def lerp(a, b, k):
    return a + (b - a) * k
