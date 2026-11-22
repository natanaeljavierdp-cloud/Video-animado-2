"""Procedural CGI bicycle scene for Blender (bpy module). Build once, then apply per-frame state."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler, Quaternion
import chaingeom as cg

P = cg.P
H = {}  # handles
random.seed(7)

# -------------------------------------------------------------- utils

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def link(ob, coll=None):
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    link(e)
    if parent:
        e.parent = parent
    return e


def mesh_obj(name, verts, faces, mat=None, parent=None, smooth=False, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    for p in me.polygons:
        p.use_smooth = smooth
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    if mat:
        me.materials.append(mat)
    link(ob)
    if parent:
        ob.parent = parent
    return ob


def obj_from_mesh(name, me, parent=None, loc=(0, 0, 0)):
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    link(ob)
    if parent:
        ob.parent = parent
    return ob


def set_smooth_angle(ob, angle=35):
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a = e.link_faces[0].normal.angle(e.link_faces[1].normal, 0)
            e.smooth = a < math.radians(angle)
    bm.to_mesh(me)
    bm.free()


def cylinder_verts(r, length, seg=24, axis='Y', cap=True):
    """returns verts, faces of a cylinder centered at origin along axis"""
    vs, fs = [], []
    for k in (-0.5, 0.5):
        for i in range(seg):
            a = 2 * math.pi * i / seg
            c, s = r * math.cos(a), r * math.sin(a)
            if axis == 'Y':
                vs.append((c, k * length, s))
            elif axis == 'Z':
                vs.append((c, s, k * length))
            else:
                vs.append((k * length, c, s))
    for i in range(seg):
        j = (i + 1) % seg
        fs.append((i, j, seg + j, seg + i))
    if cap:
        fs.append(tuple(range(seg))[::-1])
        fs.append(tuple(range(seg, 2 * seg)))
    return vs, fs


def tube_between(name, p0, p1, r0, r1=None, mat=None, parent=None, seg=32, origin=(0, 0, 0)):
    r1 = r0 if r1 is None else r1
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    vs, fs = [], []
    for k, r in ((0, r0), (1, r1)):
        for i in range(seg):
            a = 2 * math.pi * i / seg
            vs.append((r * math.cos(a), r * math.sin(a), k * L))
    for i in range(seg):
        j = (i + 1) % seg
        fs.append((i, j, seg + j, seg + i))
    fs.append(tuple(range(seg))[::-1])
    fs.append(tuple(range(seg, 2 * seg)))
    rot = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    M = Matrix.Translation(p0 - Vector(origin)) @ rot
    vs = [M @ Vector(v) for v in vs]
    ob = mesh_obj(name, vs, fs, mat, parent)
    set_smooth_angle(ob, 50)
    return ob


def sphere_verts(r, seg=24, rings=12, scale=(1, 1, 1), center=(0, 0, 0)):
    vs, fs = [], []
    for j in range(1, rings):
        th = math.pi * j / rings
        for i in range(seg):
            ph = 2 * math.pi * i / seg
            vs.append((center[0] + r * scale[0] * math.sin(th) * math.cos(ph),
                       center[1] + r * scale[1] * math.sin(th) * math.sin(ph),
                       center[2] + r * scale[2] * math.cos(th)))
    top = len(vs); vs.append((center[0], center[1], center[2] + r * scale[2]))
    bot = len(vs); vs.append((center[0], center[1], center[2] - r * scale[2]))
    for j in range(rings - 2):
        for i in range(seg):
            a = j * seg + i; b = j * seg + (i + 1) % seg
            fs.append((a, b, b + seg, a + seg))
    for i in range(seg):
        fs.append((top, (i + 1) % seg, i))
        base = (rings - 2) * seg
        fs.append((bot, base + i, base + (i + 1) % seg))
    return vs, fs


def lathe(profile, seg=64, axis='Y'):
    """profile: list of (radius, axial) closed loop; revolve around axis"""
    vs, fs = [], []
    n = len(profile)
    for i in range(seg):
        a = 2 * math.pi * i / seg
        for (r, h) in profile:
            if axis == 'Y':
                vs.append((r * math.cos(a), h, r * math.sin(a)))
            else:
                vs.append((r * math.cos(a), r * math.sin(a), h))
    for i in range(seg):
        i2 = (i + 1) % seg
        for k in range(n):
            k2 = (k + 1) % n
            fs.append((i * n + k, i * n + k2, i2 * n + k2, i2 * n + k))
    return vs, fs


def extrude_outline(outline, thick, y0=0.0):
    """outline in XZ (list of (x,z)) closed CCW; extrude along Y centered at y0"""
    n = len(outline)
    vs = [(x, y0 - thick / 2, z) for x, z in outline] + [(x, y0 + thick / 2, z) for x, z in outline]
    fs = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        fs.append((i, j, n + j, n + i))
    return vs, fs


# -------------------------------------------------------------- materials
MATS = {}


def principled(name, base, metallic=0.0, rough=0.5, aniso=0.0, coat=0.0, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if aniso:
        b.inputs["Anisotropic"].default_value = aniso
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.15
    MATS[name] = m
    return m


def add_bump(m, scale=400.0, strength=0.15, detail=4.0, stretch=None):
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = detail
    src = tc.outputs["Object"]
    if stretch:
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = stretch
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        src = mp.outputs["Vector"]
    nt.links.new(src, noise.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])


def xray_mix(m, name, tint=(0.75, 0.9, 1.0), edge=2.0):
    """wrap material output in a mix with an x-ray (transparent + fresnel glow) shader.
    Returns the Value node controlling the mix (0 solid, 1 x-ray)."""
    nt = m.node_tree
    out = nt.nodes["Material Output"]
    b = nt.nodes["Principled BSDF"]
    val = nt.nodes.new("ShaderNodeValue"); val.name = "XRAY"; val.outputs[0].default_value = 0.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*tint, 1)
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 2.5
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    ml = nt.nodes.new("ShaderNodeMath"); ml.operation = 'MULTIPLY'; ml.inputs[1].default_value = edge
    nt.links.new(pw.outputs[0], ml.inputs[0])
    nt.links.new(ml.outputs[0], em.inputs["Strength"])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(tr.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    # slight tinted glass feel
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(val.outputs[0], mix.inputs["Fac"])
    nt.links.new(b.outputs[0], mix.inputs[1])
    nt.links.new(add.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    H.setdefault("xray_vals", {})[name] = val
    return val


def make_materials():
    red = principled("frame_red", (0.42, 0.012, 0.010), rough=0.42, coat=0.25)
    xray_mix(red, "frame", tint=(1.0, 0.30, 0.25), edge=3.5)
    principled("chrome", (0.85, 0.85, 0.87), metallic=1, rough=0.07)
    principled("brushed", (0.62, 0.62, 0.64), metallic=1, rough=0.26, aniso=0.6)
    principled("alu_dark", (0.20, 0.20, 0.22), metallic=1, rough=0.32, aniso=0.4)
    principled("chain_plate", (0.50, 0.50, 0.52), metallic=1, rough=0.22)
    principled("chain_roller", (0.42, 0.42, 0.44), metallic=1, rough=0.28)
    rub = principled("rubber", (0.018, 0.018, 0.02), rough=0.78)
    add_bump(rub, 2200, 0.25)
    principled("plastic_black", (0.02, 0.02, 0.022), rough=0.45, coat=0.1)
    hood = principled("hood", (0.025, 0.025, 0.027), rough=0.55)
    xray_mix(hood, "hood", tint=(0.55, 0.75, 1.0), edge=0.7)
    rdb = principled("rd_body", (0.10, 0.10, 0.11), metallic=1, rough=0.28, aniso=0.3)
    xray_mix(rdb, "rd", tint=(0.55, 0.75, 1.0), edge=0.7)
    tape = principled("tape", (0.008, 0.008, 0.009), rough=0.75)
    add_bump(tape, 900, 0.3, stretch=(1, 1, 6))
    principled("rim", (0.015, 0.015, 0.017), rough=0.3, coat=0.6)
    principled("saddle", (0.02, 0.02, 0.022), rough=0.55, coat=0.2)
    principled("housing", (0.02, 0.02, 0.022), rough=0.25, coat=0.5)
    sk = principled("skin", (0.58, 0.40, 0.31), rough=0.5)
    b = sk.node_tree.nodes["Principled BSDF"]
    b.inputs["Subsurface Weight"].default_value = 0.25
    b.inputs["Subsurface Radius"].default_value = (0.004, 0.0015, 0.001)
    b.inputs["Coat Weight"].default_value = 0.08
    # spring steel
    principled("spring", (0.85, 0.85, 0.88), metallic=1, rough=0.12)
    # cable with travelling glow
    cab = principled("cable", (0.85, 0.86, 0.88), metallic=1, rough=0.18)
    nt = cab.node_tree
    b = nt.nodes["Principled BSDF"]
    uv = nt.nodes.new("ShaderNodeUVMap")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs[0], sep.inputs[0])
    pos = nt.nodes.new("ShaderNodeValue"); pos.name = "PULSE"; pos.outputs[0].default_value = -1
    amp = nt.nodes.new("ShaderNodeValue"); amp.name = "AMP"; amp.outputs[0].default_value = 0
    sub = nt.nodes.new("ShaderNodeMath"); sub.operation = 'SUBTRACT'
    nt.links.new(sep.outputs[0], sub.inputs[0]); nt.links.new(pos.outputs[0], sub.inputs[1])
    # tail: bright head with trailing glow : exp(-(d/w)^2) for d>0, exp(d*k) for d<0
    sq = nt.nodes.new("ShaderNodeMath"); sq.operation = 'MULTIPLY'
    nt.links.new(sub.outputs[0], sq.inputs[0]); nt.links.new(sub.outputs[0], sq.inputs[1])
    sc = nt.nodes.new("ShaderNodeMath"); sc.operation = 'MULTIPLY'; sc.inputs[1].default_value = -900.0
    nt.links.new(sq.outputs[0], sc.inputs[0])
    ex = nt.nodes.new("ShaderNodeMath"); ex.operation = 'EXPONENT'
    nt.links.new(sc.outputs[0], ex.inputs[0])
    # global faint line glow
    base = nt.nodes.new("ShaderNodeValue"); base.name = "LINE"; base.outputs[0].default_value = 0.0
    ad = nt.nodes.new("ShaderNodeMath"); ad.operation = 'ADD'
    nt.links.new(ex.outputs[0], ad.inputs[0]); nt.links.new(base.outputs[0], ad.inputs[1])
    mu = nt.nodes.new("ShaderNodeMath"); mu.operation = 'MULTIPLY'
    nt.links.new(ad.outputs[0], mu.inputs[0]); nt.links.new(amp.outputs[0], mu.inputs[1])
    b.inputs["Emission Color"].default_value = (1, 1, 1, 1)
    nt.links.new(mu.outputs[0], b.inputs["Emission Strength"])
    H["cable_pulse"], H["cable_amp"], H["cable_line"] = pos, amp, base
    # ramp highlight
    rp = principled("ramp", (0.80, 0.80, 0.82), metallic=1, rough=0.22, aniso=0.7)
    nt = rp.node_tree; b = nt.nodes["Principled BSDF"]
    v = nt.nodes.new("ShaderNodeValue"); v.name = "RAMPGLOW"; v.outputs[0].default_value = 0
    b.inputs["Emission Color"].default_value = (1.0, 0.04, 0.02, 1)
    nt.links.new(v.outputs[0], b.inputs["Emission Strength"])
    mixc = nt.nodes.new("ShaderNodeMix"); mixc.data_type = 'RGBA'
    mixc.inputs[6].default_value = (0.80, 0.80, 0.82, 1)
    mixc.inputs[7].default_value = (0.9, 0.02, 0.01, 1)
    clampn = nt.nodes.new("ShaderNodeMath"); clampn.operation = 'MINIMUM'; clampn.inputs[1].default_value = 1.0
    nt.links.new(v.outputs[0], clampn.inputs[0])
    nt.links.new(clampn.outputs[0], mixc.inputs[0])
    nt.links.new(mixc.outputs[2], b.inputs["Base Color"])
    H["ramp_glow"] = v
    # marker on rear wheel
    mk = principled("marker", (0.9, 0.03, 0.02), rough=0.3)
    b = mk.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (1, 0.05, 0.02, 1)
    b.inputs["Emission Strength"].default_value = 0.0
    H["marker_bsdf"] = b
    # floor
    fl = principled("floor", (0.010, 0.010, 0.011), rough=0.32)
    # backdrop
    bd = principled("backdrop", (0.035, 0.035, 0.04), rough=0.9)
    # emissive card
    em = bpy.data.materials.new("card")
    em.use_nodes = True
    nt = em.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs["Strength"].default_value = 1.2
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    MATS["card"] = em
    # road
    road = principled("road", (0.03, 0.03, 0.032), rough=0.85)
    road.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.25
    nt = road.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.name = "ROADMAP"
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    H["road_map"] = mp
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(mp.outputs[0], sep.inputs[0])
    # dashed center line: |y|<0.06 and frac(x/3)<0.5
    ay = nt.nodes.new("ShaderNodeMath"); ay.operation = 'ABSOLUTE'; nt.links.new(sep.outputs[1], ay.inputs[0])
    ly = nt.nodes.new("ShaderNodeMath"); ly.operation = 'LESS_THAN'; ly.inputs[1].default_value = 0.06
    nt.links.new(ay.outputs[0], ly.inputs[0])
    dx = nt.nodes.new("ShaderNodeMath"); dx.operation = 'DIVIDE'; dx.inputs[1].default_value = 3.0
    nt.links.new(sep.outputs[0], dx.inputs[0])
    fr = nt.nodes.new("ShaderNodeMath"); fr.operation = 'FRACT'; nt.links.new(dx.outputs[0], fr.inputs[0])
    lx = nt.nodes.new("ShaderNodeMath"); lx.operation = 'LESS_THAN'; lx.inputs[1].default_value = 0.5
    nt.links.new(fr.outputs[0], lx.inputs[0])
    dash = nt.nodes.new("ShaderNodeMath"); dash.operation = 'MULTIPLY'
    nt.links.new(ly.outputs[0], dash.inputs[0]); nt.links.new(lx.outputs[0], dash.inputs[1])
    # edge lines at |y| in [2.3,2.42]
    e1 = nt.nodes.new("ShaderNodeMath"); e1.operation = 'COMPARE'; e1.inputs[1].default_value = 2.36; e1.inputs[2].default_value = 0.06
    nt.links.new(ay.outputs[0], e1.inputs[0])
    lines = nt.nodes.new("ShaderNodeMath"); lines.operation = 'ADD'
    nt.links.new(dash.outputs[0], lines.inputs[0]); nt.links.new(e1.outputs[0], lines.inputs[1])
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 30
    nt.links.new(mp.outputs[0], noise.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeMapRange")
    cr.inputs[3].default_value = 0.02; cr.inputs[4].default_value = 0.06
    nt.links.new(noise.outputs["Fac"], cr.inputs[0])
    mixr = nt.nodes.new("ShaderNodeMix"); mixr.data_type = 'RGBA'
    nt.links.new(lines.outputs[0], mixr.inputs[0])
    nt.links.new(cr.outputs[0], mixr.inputs[6])
    mixr.inputs[7].default_value = (0.75, 0.75, 0.72, 1)
    nt.links.new(mixr.outputs[2], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.4
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 400
    nt.links.new(mp.outputs[0], n2.inputs["Vector"])
    nt.links.new(n2.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    gr = principled("ground", (0.015, 0.018, 0.016), rough=0.9)
    add_bump(gr, 8, 0.3)


# -------------------------------------------------------------- gears

def gear_mesh(name, n, thick, r_in, tip_h=0.0036, K=14):
    R = cg.pitch_r(n)
    rs = 0.0040
    outer = []
    arc = 2 * math.pi * R / n
    for j in range(n):
        for k in range(K):
            f = k / K
            if f >= 0.5:
                f -= 1.0
            x = abs(f) * arc
            x0 = rs * 0.92
            if x < x0:
                rad = R - math.sqrt(max(rs * rs - x * x, 0))
            else:
                c = math.sqrt(rs * rs - x0 * x0)
                t = min((x - x0) / (0.5 * arc - x0), 1.0)
                rad = R - c + (tip_h + c) * math.sin(t * math.pi / 2) ** 0.6
            th = 2 * math.pi * (j + (k / K if k / K < 0.5 else k / K - 1)) / n
            outer.append((rad, th))
    outer.sort(key=lambda a: a[1] % (2 * math.pi))
    m = len(outer)
    vs = []
    for y in (-thick / 2, thick / 2):
        for rad, th in outer:
            vs.append((rad * math.cos(th), y, rad * math.sin(th)))
        for rad, th in outer:
            vs.append((r_in * math.cos(th), y, r_in * math.sin(th)))
    fs = []
    # vs index: side0 outer [0,m), side0 inner [m,2m), side1 outer [2m,3m), side1 inner [3m,4m)
    for i in range(m):
        j = (i + 1) % m
        fs.append((i, m + i, m + j, j))              # cap -y
        fs.append((2 * m + i, 2 * m + j, 3 * m + j, 3 * m + i))  # cap +y
        fs.append((i, j, 2 * m + j, 2 * m + i))      # outer wall
        fs.append((m + i, 3 * m + i, 3 * m + j, m + j))  # inner wall
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], fs)
    me.validate()
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = abs(f.normal.y) < 0.5
    for e in bm.edges:
        if len(e.link_faces) == 2:
            e.smooth = e.link_faces[0].normal.angle(e.link_faces[1].normal, 0) < math.radians(40)
    bm.to_mesh(me); bm.free()
    return me


# -------------------------------------------------------------- chain link meshes

def dogbone(rh, waist, pitch, seg=18):
    pts = []
    # right lobe (x=+p/2) from -90..90 deg, left lobe from 90..270
    for i in range(seg + 1):
        a = -math.pi / 2 + math.pi * i / seg
        a2 = a * 0.82
        pts.append((pitch / 2 + rh * math.cos(a), rh * math.sin(a)))
    # top waist
    for i in range(1, 6):
        x = pitch / 2 - pitch * i / 6
        z = waist + (rh - waist) * (2 * abs(x) / pitch) ** 2.2
        pts.append((x, z))
    for i in range(seg + 1):
        a = math.pi / 2 + math.pi * i / seg
        pts.append((-pitch / 2 + rh * math.cos(a), rh * math.sin(a)))
    for i in range(1, 6):
        x = -pitch / 2 + pitch * i / 6
        z = -(waist + (rh - waist) * (2 * abs(x) / pitch) ** 2.2)
        pts.append((x, z))
    return pts


def chain_meshes():
    inner = bmesh.new()
    outer = bmesh.new()

    def add(bm, vs, fs):
        base = len(bm.verts)
        vv = [bm.verts.new(v) for v in vs]
        for f in fs:
            try:
                bm.faces.new([vv[i] for i in f])
            except ValueError:
                pass
    ol_in = dogbone(0.0046, 0.0036, P)
    ol_out = dogbone(0.0043, 0.0034, P)
    for y in (-0.00168, 0.00168):
        vs, fs = extrude_outline(ol_in, 0.0008, y)
        add(inner, vs, fs)
    for x in (-P / 2, P / 2):
        vs, fs = cylinder_verts(0.0039, 0.0026, 20, 'Y')
        add(inner, [(v[0] + x, v[1], v[2]) for v in vs], fs)
    for y in (-0.00252, 0.00252):
        vs, fs = extrude_outline(ol_out, 0.0008, y)
        add(outer, vs, fs)
    for x in (-P / 2, P / 2):
        vs, fs = cylinder_verts(0.0018, 0.0068, 12, 'Y')
        add(outer, [(v[0] + x, v[1], v[2]) for v in vs], fs)
    mi = bpy.data.meshes.new("link_inner"); inner.to_mesh(mi); inner.free()
    mo = bpy.data.meshes.new("link_outer"); outer.to_mesh(mo); outer.free()
    for me in (mi, mo):
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for f in bm.faces:
            f.smooth = abs(f.normal.y) < 0.7
        for e in bm.edges:
            if len(e.link_faces) == 2:
                e.smooth = e.link_faces[0].normal.angle(e.link_faces[1].normal, 0) < math.radians(40)
        bm.to_mesh(me); bm.free()
    # material slots: plates & rollers same-ish ; use plate material
    mi.materials.append(MATS["chain_plate"])
    mo.materials.append(MATS["chain_plate"])
    return mi, mo


# -------------------------------------------------------------- bike build
REAR = cg.REAR
BB = cg.BB
FRONT = cg.FRONT
WR = cg.WHEEL_R
SEAT_TOP = (-0.17, 0.80)
HT_TOP = (0.50, 0.83)
HT_BOT = (0.545, 0.66)
COG_Y = {}
CASSETTE = [11, 13, 15, 17, 19, 21, 24, 28, 34]
for i, n in enumerate(CASSETTE):
    COG_Y[n] = -0.0512 + i * 0.0039
RING_Y = {34: -0.0400, 50: -0.0455}
PARTS = []
THREADS = 4


def part(name, pivot, off, spin=(0, 0, 0.3), tilt=(0, 0, 0)):
    e = empty("P_" + name, pivot)
    PARTS.append(dict(name=name, empty=e, pivot=Vector(pivot), off=Vector(off),
                      spin=Vector(spin), tilt=Vector(tilt), e=0.0))
    return e


def V(x, z, y=0.0):
    return (x, y, z)


def build_frame():
    pe = part("frame", (0.05, 0, 0.55), (0.0, 0.0, 0.18), spin=(0, 0, 0.12), tilt=(0.1, 0.05, 0.0))
    o = pe.location
    m = MATS["frame_red"]
    st = SEAT_TOP
    tubes = [
        ("toptube", V(*st), V(*HT_TOP), 0.0155, 0.0165),
        ("downtube", V(*BB), V(*HT_BOT), 0.024, 0.021),
        ("seattube", V(*BB), V(*st), 0.017, 0.0152),
        ("headtube", V(*HT_BOT), V(*HT_TOP), 0.020, 0.019),
    ]
    for side in (-1, 1):
        tubes.append(("chainstay%d" % side, V(BB[0] - 0.02, BB[1], side * 0.035), V(REAR[0] + 0.012, REAR[1], side * 0.064), 0.0115, 0.0075))
        tubes.append(("seatstay%d" % side, V(st[0] + 0.012, st[1] - 0.06, side * 0.012), V(REAR[0] + 0.012, REAR[1] + 0.006, side * 0.064), 0.0085, 0.0065))
    for nm, a, b, r0, r1 in tubes:
        ob = tube_between(nm, a, b, r0, r1, m, pe, origin=o)
        ob.location = (0, 0, 0)
    # joints
    for nm, c, r in (("bbshell", V(*BB), 0.024), ("j_seat", V(*st), 0.017), ("j_ht", V(*HT_TOP), 0.020)):
        if nm == "bbshell":
            vs, fs = cylinder_verts(0.022, 0.07, 32, 'Y')
            ob = mesh_obj(nm, [(v[0] + c[0] - o.x, v[1], v[2] + c[2] - o.z) for v in vs], fs, m, pe)
            set_smooth_angle(ob, 50)
        else:
            vs, fs = sphere_verts(r, 24, 12, center=(c[0] - o.x, c[1], c[2] - o.z))
            mesh_obj(nm, vs, fs, m, pe, smooth=True)
    # dropouts
    for side in (-1, 1):
        ol = [(0.018 * math.cos(a), 0.018 * math.sin(a)) for a in [i * 2 * math.pi / 24 for i in range(24)]]
        vs, fs = extrude_outline(ol, 0.006, side * 0.066)
        mesh_obj("dropout%d" % side, [(v[0] + REAR[0] - o.x, v[1], v[2] + REAR[1] - o.z) for v in vs], fs, MATS["alu_dark"], pe)
    # derailleur hanger (drive side)
    ol = [(0.0, 0.0), (0.012, -0.004), (0.010, -0.032), (-0.006, -0.036), (-0.012, -0.010)]
    vs, fs = extrude_outline(ol[::-1], 0.004, -0.071)
    mesh_obj("hanger", [(v[0] + REAR[0] - o.x, v[1], v[2] + REAR[1] - o.z) for v in vs], fs, MATS["alu_dark"], pe)
    # cable ports (internal routing)
    for nm, c in (("port_dt", V(HT_BOT[0] - 0.05, HT_BOT[1] - 0.02, -0.02)), ("port_cs", V(REAR[0] + 0.07, REAR[1] - 0.012, -0.055))):
        vs, fs = sphere_verts(0.006, 16, 8, scale=(1.6, 1, 1), center=(c[0] - o.x, c[1], c[2] - o.z))
        mesh_obj(nm, vs, fs, MATS["plastic_black"], pe, smooth=True)
    H["frame_empty"] = pe
    return pe


def build_fork():
    pe = part("fork", (HT_BOT[0] + 0.02, 0, 0.5), (0.25, 0.0, 0.05), spin=(0, 0, -0.2), tilt=(0, 0.2, 0.1))
    o = pe.location
    m = MATS["frame_red"]
    for side in (-1, 1):
        pts = []
        a = Vector(V(HT_BOT[0] + 0.004, HT_BOT[1] - 0.02, side * 0.026))
        b = Vector(V(FRONT[0], FRONT[1], side * 0.052))
        mid = (a + b) / 2 + Vector((0.035, 0, 0))
        prev = None
        for i in range(8):
            t = i / 7
            p = (1 - t) ** 2 * a + 2 * (1 - t) * t * mid + t * t * b
            if prev is not None:
                tube_between("forkblade%d_%d" % (side, i), prev, p, 0.014 - 0.006 * (i - 1) / 7, 0.014 - 0.006 * i / 7, m, pe, origin=o)
                vs, fs = sphere_verts(0.014 - 0.006 * i / 7, 16, 8, center=(p - o))
                mesh_obj("fkj", vs, fs, m, pe, smooth=True)
            prev = p
    vs, fs = sphere_verts(0.03, 24, 12, scale=(1.0, 1.4, 0.6), center=(Vector(V(HT_BOT[0] + 0.004, HT_BOT[1] - 0.015)) - o))
    mesh_obj("crown", vs, fs, m, pe, smooth=True)
    tube_between("steerer", V(HT_BOT[0], HT_BOT[1]), V(HT_TOP[0] - 0.008, HT_TOP[1] + 0.05), 0.0143, 0.0143, MATS["alu_dark"], pe, origin=o)
    return pe


def build_wheel(name, center, off, rear=False):
    pe = part(name, (center[0], 0, center[1]), off, spin=(0, 0.25 if rear else -0.25, 0.15), tilt=(0.3, 0, 0.2 if rear else -0.2))
    rot = empty(name + "_rot", (0, 0, 0), pe)
    # rim (deep section)
    prof = [(0.300, -0.0095), (0.318, -0.0125), (0.3335, -0.0110), (0.3335, 0.0110), (0.318, 0.0125), (0.300, 0.0095), (0.292, 0.0)]
    vs, fs = lathe(prof, 128, 'Y')
    ob = mesh_obj(name + "_rim", vs, fs, MATS["rim"], rot)
    set_smooth_angle(ob, 40)
    # braking/brand-free metal track
    prof2 = [(0.3300, -0.0112), (0.3345, -0.0112), (0.3345, 0.0112), (0.3300, 0.0112)]
    vs, fs = lathe(prof2, 128, 'Y')
    ob = mesh_obj(name + "_track", vs, fs, MATS["alu_dark"], rot)
    # tire
    tp = []
    for i in range(20):
        a = 2 * math.pi * i / 20
        tp.append((0.3445 + 0.0125 * math.cos(a), 0.0125 * math.sin(a)))
    vs, fs = lathe(tp, 160, 'Y')
    ob = mesh_obj(name + "_tire", vs, fs, MATS["rubber"], rot, smooth=True)
    # hub
    hp = [(0.012, -0.05), (0.02, -0.05), (0.02, -0.045), (0.028 if not rear else 0.026, -0.042), (0.028 if not rear else 0.026, -0.036),
          (0.016, -0.033), (0.016, 0.033), (0.028, 0.036), (0.028, 0.042), (0.02, 0.045), (0.02, 0.05), (0.012, 0.05)]
    if rear:
        hp = [(r, h) for r, h in hp]
    vs, fs = lathe(hp, 48, 'Y')
    ob = mesh_obj(name + "_hub", vs, fs, MATS["brushed"], rot)
    set_smooth_angle(ob, 40)
    # spokes 24
    bmS = bmesh.new()
    for i in range(24):
        side = 1 if i % 2 == 0 else -1
        a_h = 2 * math.pi * i / 24
        a_r = a_h + (0.25 if side > 0 else -0.25) * (1 if rear else 0.0)
        hy = 0.038 * side if not (rear and side < 0) else -0.030
        p0 = Vector((0.026 * math.cos(a_h), hy, 0.026 * math.sin(a_h)))
        p1 = Vector((0.296 * math.cos(a_r), side * 0.002, 0.296 * math.sin(a_r)))
        d = p1 - p0
        q = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        M = Matrix.Translation(p0) @ q
        vs, fs = [], []
        seg = 6
        for k in (0, 1):
            for j in range(seg):
                a = 2 * math.pi * j / seg
                vs.append(M @ Vector((0.0011 * math.cos(a), 0.0011 * math.sin(a), k * d.length)))
        vv = [bmS.verts.new(v) for v in vs]
        for j in range(seg):
            j2 = (j + 1) % seg
            bmS.faces.new((vv[j], vv[j2], vv[seg + j2], vv[seg + j]))
    me = bpy.data.meshes.new(name + "_spokes"); bmS.to_mesh(me); bmS.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(MATS["chrome"])
    obj_from_mesh(name + "_spokes", me, rot)
    # axle / QR
    vs, fs = cylinder_verts(0.005, 0.15 if rear else 0.13, 16, 'Y')
    mesh_obj(name + "_axle", vs, fs, MATS["chrome"], pe)
    if rear:
        # marker (red valve-like reflector on rim) for counting turns
        vs, fs = sphere_verts(0.010, 16, 8, scale=(1.4, 1.6, 1.4), center=(0, -0.0135, 0.312))
        mk = mesh_obj("wheel_marker", vs, fs, MATS["marker"], rot, smooth=True)
        H["wheel_marker"] = mk
    H[name + "_rot"] = rot
    return pe


def build_cassette():
    pe = part("cassette", (REAR[0], 0, REAR[1]), (-0.10, -0.32, 0.12), spin=(0, 0.6, 0.2), tilt=(0.4, 0, 0.6))
    rot = empty("cassette_rot", (0, 0, 0), pe)
    H["cogs"] = {}
    for n in CASSETTE:
        me = gear_mesh("cog%d" % n, n, 0.0018, 0.0175, tip_h=0.0032)
        mat = MATS["brushed"] if n not in (13,) else MATS["brushed"]
        me.materials.append(MATS["brushed"])
        ob = obj_from_mesh("cog%d" % n, me, rot, loc=(0, COG_Y[n], 0))
        H["cogs"][n] = ob
    # spacers
    vs, fs = cylinder_verts(0.019, 0.034, 32, 'Y')
    mesh_obj("cas_core", [(v[0], v[1] + (COG_Y[11] + COG_Y[34]) / 2, v[2]) for v in vs], fs, MATS["alu_dark"], rot)
    # lockring
    vs, fs = lathe([(0.012, -0.002), (0.018, -0.002), (0.018, 0.002), (0.012, 0.002)], 32, 'Y')
    mesh_obj("lockring", [(v[0], v[1] + COG_Y[11] - 0.003, v[2]) for v in vs], fs, MATS["chrome"], rot)
    # shift ramps on the inboard face of 13T (facing 11T => -y side of 13T)
    R13 = cg.pitch_r(13)
    rbm = bmesh.new()
    H["ramp_angles"] = []
    for g in range(3):
        ang = 2 * math.pi * (g * 13 // 3 + 0.5) / 13
        H["ramp_angles"].append(ang)
        # wedge: a sloped block across one tooth flank
        w = 0.0050
        c, s = math.cos(ang), math.sin(ang)
        t = Vector((-s, 0, c))
        rdir = Vector((c, 0, s))
        y0 = COG_Y[13] - 0.0009
        base = rdir * (R13 - 0.0030)
        pts = []
        for (a_t, a_r, a_y) in ((-w, 0, 0), (w, 0, 0), (w * 0.7, 0.0068, 0), (-w * 0.7, 0.0068, 0),
                                (-w, 0, -0.0013), (w, 0, -0.0013), (w * 0.5, 0.0045, -0.0005), (-w * 0.5, 0.0045, -0.0005)):
            p = base + t * a_t + rdir * a_r
            pts.append(Vector((p.x, y0 + a_y, p.z)))
        vv = [rbm.verts.new(p) for p in pts]
        for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            rbm.faces.new([vv[i] for i in f])
    bmesh.ops.recalc_face_normals(rbm, faces=rbm.faces)
    me = bpy.data.meshes.new("ramps"); rbm.to_mesh(me); rbm.free()
    me.materials.append(MATS["ramp"])
    H["ramps"] = obj_from_mesh("ramps", me, rot)
    H["cassette_rot"] = rot
    return pe


def build_crankset():
    pe = part("crank", (BB[0], 0, BB[1]), (0.12, -0.40, -0.05), spin=(0, 0.45, 0.1), tilt=(0.5, 0, -0.3))
    rot = empty("crank_rot", (0, 0, 0), pe)
    H["rings"] = {}
    for n, rin in ((50, 0.084), (34, 0.058)):
        me = gear_mesh("ring%d" % n, n, 0.0022, rin, tip_h=0.0038)
        me.materials.append(MATS["brushed"] if n == 34 else MATS["alu_dark"])
        ob = obj_from_mesh("ring%d" % n, me, rot, loc=(0, RING_Y[n], 0))
        H["rings"][n] = ob
    # spider: 4 arms (between rings) to bolt circle r=0.0555... (inside the 34 ring hole limit 0.058)
    bmS = bmesh.new()
    for i in range(4):
        a = 2 * math.pi * i / 4 + math.pi / 4
        c, s = math.cos(a), math.sin(a)
        t = (-s, c)
        pts = []
        for rr, w in ((0.02, 0.012), (0.090, 0.007)):
            pts.append((rr * c + t[0] * w, rr * s + t[1] * w))
        for rr, w in ((0.090, -0.007), (0.02, -0.012)):
            pts.append((rr * c + t[0] * w, rr * s + t[1] * w))
        vs, fs = extrude_outline(pts, 0.004, -0.0475)
        vv = [bmS.verts.new(v) for v in vs]
        for f in fs:
            bmS.faces.new([vv[k] for k in f])
    bmesh.ops.recalc_face_normals(bmS, faces=bmS.faces)
    me = bpy.data.meshes.new("spider"); bmS.to_mesh(me); bmS.free()
    me.materials.append(MATS["alu_dark"])
    obj_from_mesh("spider", me, rot)
    # chainring bolts (outboard of 50)
    H["bolts_ring"] = []
    for i in range(4):
        a = 2 * math.pi * i / 4 + math.pi / 4
        vs, fs = cylinder_verts(0.0045, 0.012, 6, 'Y')
        ob = mesh_obj("ringbolt%d" % i, [(v[0] + 0.086 * math.cos(a), v[1] - 0.046, v[2] + 0.086 * math.sin(a)) for v in vs], fs, MATS["chrome"], rot)
    # spindle
    vs, fs = cylinder_verts(0.012, 0.15, 32, 'Y')
    mesh_obj("spindle", vs, fs, MATS["chrome"], rot)
    # crank arms (170mm) : drive arm points along +angle 0 => we orient arm along -X*?; arm along local +X direction rotated
    H["arm_len"] = 0.1725
    for side, y in ((-1, -0.062), (1, 0.062)):
        L = 0.1725
        ang0 = 0.0 if side < 0 else math.pi
        c, s = math.cos(ang0), math.sin(ang0)
        pts = []
        N = 16
        for i in range(N + 1):
            a = -math.pi / 2 + math.pi * i / N
            pts.append((L + 0.012 * math.cos(a), 0.012 * math.sin(a)))
        for i in range(N + 1):
            a = math.pi / 2 + math.pi * i / N
            pts.append((0.020 * math.cos(a), 0.020 * math.sin(a)))
        pts = [(x * c - z * s, x * s + z * c) for x, z in pts]
        vs, fs = extrude_outline(pts, 0.012, y)
        ob = mesh_obj("crankarm%d" % side, vs, fs, MATS["alu_dark"], rot)
        set_smooth_angle(ob, 60)
        # crank bolt
        vs, fs = cylinder_verts(0.008, 0.006, 6, 'Y')
        mesh_obj("crankbolt%d" % side, [(v[0], v[1] + y + side * 0.007, v[2]) for v in vs], fs, MATS["chrome"], rot)
    H["crank_rot"] = rot
    return pe


def build_pedals():
    H["pedals"] = []
    for side, y in ((-1, -0.09), (1, 0.09)):
        pe = part("pedal%d" % side, (BB[0], y, BB[1]), (0.05 * side, 0.30 * side, -0.12), spin=(0.5, 0.3, 0.2), tilt=(0.6, 0.3, 0))
        body = empty("pedal_body%d" % side, (0, 0, 0), pe)
        vs, fs = sphere_verts(0.03, 24, 12, scale=(1.6, 1.0, 0.35))
        ob = mesh_obj("pedalb%d" % side, vs, fs, MATS["plastic_black"], body, smooth=True)
        vs, fs = cylinder_verts(0.006, 0.07, 16, 'Y')
        mesh_obj("pedal_axle%d" % side, [(v[0], v[1] - side * 0.02, v[2]) for v in vs], fs, MATS["chrome"], body)
        vs, fs = sphere_verts(0.01, 12, 6, scale=(2.0, 1.2, 0.5), center=(0, 0, 0.011))
        mesh_obj("cleat%d" % side, vs, fs, MATS["brushed"], body, smooth=True)
        H["pedals"].append((pe, body, side))


def build_seat():
    pe = part("saddle", (SEAT_TOP[0] - 0.03, 0, 0.98), (-0.12, 0.05, 0.22), spin=(0, 0, 0.35), tilt=(0.2, 0.1, 0.3))
    o = pe.location
    a = Vector(V(SEAT_TOP[0] + 0.01, SEAT_TOP[1] - 0.03))
    d = Vector((-math.cos(math.radians(73)), 0, math.sin(math.radians(73))))
    b = a + d * 0.21
    tube_between("seatpost", a, b, 0.0136, 0.0136, MATS["alu_dark"], pe, origin=o)
    # saddle shell
    top = b + Vector((0.0, 0, 0.035))
    vs, fs = [], []
    NU, NV = 28, 24
    for i in range(NU + 1):
        u = i / NU
        x = -0.11 + 0.27 * u
        w = 0.072 * (1 - u) ** 0.5 * (1 - 0.65 * u) + 0.016
        w = 0.074 if u < 0.25 else w
        if u < 0.25:
            w = 0.05 + 0.024 * math.sin(u / 0.25 * math.pi / 2)
        hgt = 0.022 - 0.006 * u
        for j in range(NV):
            v = 2 * math.pi * j / NV
            cy, cz = math.cos(v), math.sin(v)
            z = hgt * (abs(cz) ** 0.6) * (1 if cz >= 0 else -0.5) * math.copysign(1, cz)
            vs.append((top.x - o.x + x, w * math.copysign(abs(cy) ** 0.7, cy), top.z - o.z + z - 0.03 * (u - 0.6) ** 2))
    for i in range(NU):
        for j in range(NV):
            j2 = (j + 1) % NV
            fs.append((i * NV + j, i * NV + j2, (i + 1) * NV + j2, (i + 1) * NV + j))
    c0 = len(vs); vs.append((top.x - o.x - 0.11, 0, top.z - o.z - 0.004))
    c1 = len(vs); vs.append((top.x - o.x + 0.16, 0, top.z - o.z - 0.006))
    for j in range(NV):
        j2 = (j + 1) % NV
        fs.append((c0, j2, j))
        fs.append((c1, NU * NV + j, NU * NV + j2))
    mesh_obj("saddle", vs, fs, MATS["saddle"], pe, smooth=True)
    # rails
    for s in (-1, 1):
        tube_between("rail%d" % s, top + Vector((-0.07, s * 0.022, -0.012)), top + Vector((0.09, s * 0.012, -0.014)), 0.0035, 0.0035, MATS["chrome"], pe, origin=o)
    # seat clamp bolt
    vs, fs = cylinder_verts(0.004, 0.012, 6, 'X')
    return pe


BAR_C = (0.60, 0.885)  # bar centre (x,z)


def bar_curve_pts(side):
    bx, bz = BAR_C
    s = side
    return [(bx, s * 0.0, bz), (bx, s * 0.12, bz), (bx + 0.005, s * 0.185, bz), (bx + 0.055, s * 0.207, bz - 0.006),
            (bx + 0.085, s * 0.210, bz - 0.045), (bx + 0.070, s * 0.210, bz - 0.105), (bx + 0.020, s * 0.210, bz - 0.130),
            (bx - 0.045, s * 0.210, bz - 0.125)]


def catmull(pts, n=12):
    out = []
    P_ = [Vector(pts[0]) * 2 - Vector(pts[1])] + [Vector(p) for p in pts] + [Vector(pts[-1]) * 2 - Vector(pts[-2])]
    for i in range(1, len(P_) - 2):
        p0, p1, p2, p3 = P_[i - 1], P_[i], P_[i + 1], P_[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(Vector(pts[-1]))
    return out


def sweep_tube(name, pts, r, mat, parent=None, seg=16, origin=(0, 0, 0), uv=False):
    """tube along polyline pts; UV.x = normalized length"""
    pts = [Vector(p) - Vector(origin) for p in pts]
    n = len(pts)
    lens = [0.0]
    for i in range(1, n):
        lens.append(lens[-1] + (pts[i] - pts[i - 1]).length)
    Ltot = lens[-1]
    vs, fs = [], []
    prev_nrm = None
    for i in range(n):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        t.normalize()
        if prev_nrm is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            nrm = (ref - t * ref.dot(t)).normalized()
        else:
            nrm = (prev_nrm - t * prev_nrm.dot(t)).normalized()
        prev_nrm = nrm
        bn = t.cross(nrm)
        for j in range(seg):
            a = 2 * math.pi * j / seg
            vs.append(pts[i] + (nrm * math.cos(a) + bn * math.sin(a)) * r)
    for i in range(n - 1):
        for j in range(seg):
            j2 = (j + 1) % seg
            fs.append((i * seg + j, i * seg + j2, (i + 1) * seg + j2, (i + 1) * seg + j))
    fs.append(tuple(range(seg))[::-1])
    fs.append(tuple(range((n - 1) * seg, n * seg)))
    ob = mesh_obj(name, vs, fs, mat, parent, smooth=True)
    if uv:
        me = ob.data
        uvl = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                uvl.data[li].uv = (lens[vi // seg] / Ltot, (vi % seg) / seg)
    return ob, Ltot, lens


def build_bar():
    """stem + handlebar + hoods/levers. Right (drive side, -Y) hood carries the shifter internals."""
    bx, bz = BAR_C
    pe = part("bar", (bx, 0, bz), (0.30, 0.0, 0.30), spin=(0.1, 0, -0.25), tilt=(0.25, 0.15, 0.4))
    o = pe.location
    # stem
    st0 = Vector(V(HT_TOP[0] - 0.008, HT_TOP[1] + 0.03))
    tube_between("stem", st0, Vector(V(bx, bz)), 0.016, 0.0165, MATS["alu_dark"], pe, origin=o)
    vs, fs = cylinder_verts(0.019, 0.04, 32, 'Z')
    ob = mesh_obj("stemclamp", [(v[0] + st0.x - o.x, v[1], v[2] + st0.z - o.z) for v in vs], fs, MATS["alu_dark"], pe)
    set_smooth_angle(ob, 50)
    vs, fs = cylinder_verts(0.019, 0.045, 32, 'Y')
    ob = mesh_obj("faceplate", [(v[0] + 0.004, v[1], v[2]) for v in vs], fs, MATS["alu_dark"], pe)
    set_smooth_angle(ob, 50)
    H["stem_bolts"] = []
    for k, (dy, dz) in enumerate(((-0.015, 0.013), (0.015, 0.013), (-0.015, -0.013), (0.015, -0.013))):
        vs, fs = cylinder_verts(0.0035, 0.008, 6, 'X')
        mesh_obj("stembolt%d" % k, [(v[0] + 0.024, v[1] + dy, v[2] + dz) for v in vs], fs, MATS["chrome"], pe)
    # bar both sides
    for side in (-1, 1):
        pts = catmull(bar_curve_pts(side), 10)
        sweep_tube("bar%d" % side, pts, 0.0125, MATS["tape"], pe, 20, origin=o)
    vs, fs = cylinder_verts(0.0159, 0.08, 32, 'Y')
    ob = mesh_obj("barcenter", vs, fs, MATS["alu_dark"], pe)
    set_smooth_angle(ob, 50)
    # hoods
    for side in (-1, 1):
        hood = build_hood(side, pe, o)
    return pe


def rounded_box(sx, sy, sz, r=0.3, n=10):
    """superellipsoid-ish box via sphere mapping"""
    vs, fs = [], []
    rings, seg = n, n * 2
    for j in range(1, rings):
        th = math.pi * j / rings
        for i in range(seg):
            ph = 2 * math.pi * i / seg
            x, y, z = math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)
            e = 0.35
            f = lambda v: math.copysign(abs(v) ** e, v)
            vs.append((sx * f(x), sy * f(y), sz * f(z)))
    top = len(vs); vs.append((0, 0, sz))
    bot = len(vs); vs.append((0, 0, -sz))
    for j in range(rings - 2):
        for i in range(seg):
            a = j * seg + i; b = j * seg + (i + 1) % seg
            fs.append((a, b, b + seg, a + seg))
    for i in range(seg):
        fs.append((top, (i + 1) % seg, i))
        base = (rings - 2) * seg
        fs.append((bot, base + i, base + (i + 1) % seg))
    return vs, fs


def build_hood(side, pe, o):
    bx, bz = BAR_C
    # hood frame: origin on the bar's front curve top, x forward
    hp = Vector((bx + 0.083, side * 0.210, bz - 0.030))
    he = empty("hood%d" % side, hp - o, pe)
    he.rotation_euler = (0, math.radians(-28), 0)
    vs, fs = rounded_box(0.042, 0.016, 0.022, n=14)
    body = mesh_obj("hoodbody%d" % side, [(v[0] + 0.02, v[1], v[2] + 0.012) for v in vs], fs, MATS["hood"], he, smooth=True)
    # horn
    vs, fs = sphere_verts(0.012, 16, 8, scale=(1.0, 1.0, 1.3), center=(0.062, 0, 0.026))
    mesh_obj("hoodhorn%d" % side, vs, fs, MATS["hood"], he, smooth=True)
    # brake lever blade (pivot near front top), hangs down
    piv = empty("brakelever%d" % side, (0.05, 0, 0.0), he)
    blade = []
    for i in range(12):
        t = i / 11
        blade.append(Vector((0.012 - 0.06 * t + 0.04 * t * t, 0, -0.005 - 0.115 * t)))
    sweep_tube("brakeblade%d" % side, blade, 0.0055, MATS["alu_dark"], piv, 12)
    # shift lever blade (behind brake blade) – pivots about the hood x axis to swing inward
    sp = empty("shiftlever%d" % side, (0.036, side * 0.0, -0.010), he)
    blade2 = []
    for i in range(10):
        t = i / 9
        blade2.append(Vector((-0.004 - 0.045 * t + 0.03 * t * t, -side * 0.0 + 0.0, -0.006 - 0.085 * t)))
    sweep_tube("shiftblade%d" % side, blade2, 0.0042, MATS["plastic_black"], sp, 12)
    if side < 0:
        H["shift_lever"] = sp
        H["hood_empty"] = he
        build_shifter_internals(he)
        H["hood_body"] = body
    return he


def build_shifter_internals(he):
    """ratchet wheel + pawl + spool inside right hood. Axis along hood local X."""
    inner = empty("ratchet_root", (0.010, 0.0, 0.014), he)
    rot = empty("ratchet_rot", (0, 0, 0), inner)
    # ratchet wheel: asymmetric saw teeth, in local YZ plane (axis X)
    n = 12
    pts = []
    Ro, Ri = 0.0105, 0.0078
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 0.82) / n
        a2 = 2 * math.pi * (i + 1) / n
        pts.append((Ri * math.cos(a0), Ri * math.sin(a0)))
        for k in range(1, 6):
            a = a0 + (a1 - a0) * k / 5
            rr = Ri + (Ro - Ri) * (k / 5) ** 1.3
            pts.append((rr * math.cos(a), rr * math.sin(a)))
        pts.append((Ri + 0.0006, 0))
        pts[-1] = (Ro * math.cos(a1 + 0.02), Ro * math.sin(a1 + 0.02))
        pts.append(((Ri) * math.cos(a2 - 0.01), Ri * math.sin(a2 - 0.01)))
    vs, fs = extrude_outline(pts, 0.003, 0)
    # map extrude (x,y,z)->(y as axis): outline in XZ extruded along Y; rotate so axis = X
    vs = [(v[1], v[0], v[2]) for v in vs]
    fs = [f[::-1] for f in fs]
    ob = mesh_obj("ratchet", vs, fs, MATS["chrome"], rot)
    set_smooth_angle(ob, 30)
    # hub & spool (cable winds here)
    prof = [(0.002, -0.004), (0.006, -0.004), (0.006, -0.0025), (0.0045, -0.0015), (0.0045, 0.0015), (0.006, 0.0025), (0.006, 0.004), (0.002, 0.004)]
    vs, fs = lathe(prof, 32, 'Y')
    vs = [(v[1] - 0.0045, v[0], v[2]) for v in vs]
    ob = mesh_obj("spool", vs, fs, MATS["brushed"], rot)
    set_smooth_angle(ob, 40)
    # pawl: pivot above wheel, arm whose tip rests in a tooth
    pp = empty("pawl_piv", (0.0, 0.0, 0.0155), inner)
    arm = [(0.0, 0.0018), (0.0068, 0.0006), (0.0082, -0.0040), (0.0068, -0.0026), (0.0, -0.0018), (-0.0016, 0.0)]
    vs, fs = extrude_outline(arm, 0.0022, 0)
    vs = [(v[1], v[0], v[2]) for v in vs]
    fs = [f[::-1] for f in fs]
    ob = mesh_obj("pawl", vs, fs, MATS["brushed"], pp)
    vs, fs = cylinder_verts(0.0014, 0.004, 12, 'X')
    mesh_obj("pawl_pin", vs, fs, MATS["chrome"], pp)
    # pawl spring (small)
    H["ratchet_rot"], H["pawl"], H["ratchet_root"] = rot, pp, inner


RD_A = Vector((0.0, -0.0075, 0.0125))   # separation between upper/lower link pivots (in YZ plane)


def rd_geom(y_der, r_cog):
    """return key points of the rear derailleur for a lateral position and cog radius"""
    gx = REAR[0] + 0.006
    gz = REAR[1] - r_cog - cg.pitch_r(cg.JOCKEY_N) - 0.008
    G = Vector((gx, y_der, gz))
    Pk = G + Vector((-0.002, -0.0185, 0.020))
    return G, Pk


def build_derailleur():
    pe = part("rd", (REAR[0], -0.085, REAR[1] - 0.06), (-0.10, -0.25, -0.12), spin=(0.3, 0.5, 0.1), tilt=(0.3, 0.2, 0.5))
    o = pe.location
    m = MATS["rd_body"]
    root = empty("rd_root", (0, 0, 0), pe)
    # B pivot chosen equidistant from P-knuckle at 11T and 34T (constant link length)
    _, P11 = rd_geom(COG_Y[11], cg.pitch_r(11))
    _, P34 = rd_geom(COG_Y[34], cg.pitch_r(34))
    mid = (P11 + P34) / 2
    dd = (P34 - P11).normalized()
    bolt0 = Vector((REAR[0], -0.073, REAR[1] - 0.022))
    B = bolt0 - dd * (bolt0 - mid).dot(dd)
    B.x = REAR[0] - 0.040
    l1, l2 = P11 - B, P34 - B
    nrm = l1.cross(l2).normalized()
    H["rd_nrm"] = nrm
    lm = (l1.normalized() + l2.normalized()).normalized()
    H["rd_A"] = nrm.cross(lm).normalized() * 0.011
    H["rd_B"] = B
    bolt = Vector((REAR[0], -0.073, REAR[1] - 0.022))
    # B-knuckle body: from hanger bolt down to B pivot
    tube_between("bknuckle", bolt, B, 0.0085, 0.0105, m, root, seg=24, origin=o)
    vs, fs = sphere_verts(0.0105, 20, 10, center=(B - o))
    mesh_obj("bknuckle_end", vs, fs, m, root, smooth=True)
    vs, fs = sphere_verts(0.0085, 20, 10, center=(bolt - o))
    mesh_obj("bknuckle_top", vs, fs, m, root, smooth=True)
    vs, fs = cylinder_verts(0.0048, 0.014, 6, 'Y')
    mesh_obj("bbolt", [(v[0] + bolt.x - o.x, v[1] + bolt.y - 0.010 - o.y, v[2] + bolt.z - o.z) for v in vs], fs, MATS["chrome"], root)
    # barrel adjuster (cable stop) on top-rear of B-knuckle
    bar0 = bolt + Vector((-0.004, -0.004, -0.004))
    tube_between("barrel", bar0 + Vector((-0.016, 0, 0.004)), bar0, 0.0042, 0.0042, MATS["alu_dark"], root, seg=12, origin=o)
    H["rd_barrel"] = bar0 + Vector((-0.016, 0, 0.004))
    # dynamic: two link plates, P-knuckle, spring, pivots
    H["rd_links"] = []
    for k in range(2):
        vs, fs = rounded_box(0.5, 0.5, 0.5, n=8)
        ob = mesh_obj("rdlink%d" % k, vs, fs, m if k == 0 else MATS["brushed"], root, smooth=True)
        H["rd_links"].append(ob)
    vs, fs = rounded_box(0.012, 0.0085, 0.014, n=10)
    H["rd_pk"] = mesh_obj("pknuckle", vs, fs, m, root, smooth=True)
    H["rd_pins"] = []
    for k in range(4):
        vs, fs = cylinder_verts(0.0022, 0.026, 12, 'X')
        H["rd_pins"].append(mesh_obj("rdpin%d" % k, vs, fs, MATS["chrome"], root))
    me = bpy.data.meshes.new("rdspring")
    me.materials.append(MATS["spring"])
    H["rd_spring"] = obj_from_mesh("rdspring", me, root)
    # cage + pulleys
    cage = empty("rd_cage", (0, 0, 0), root)
    H["rd_cage"] = cage
    for k, y in enumerate((-0.0075, 0.0075)):
        pts = []
        for i in range(17):
            a = math.pi * i / 16
            pts.append((0.0165 * math.cos(a), 0.0165 * math.sin(a)))
        for i in range(17):
            a = math.pi + math.pi * i / 16
            pts.append((0.0165 * math.cos(a), -cg.CAGE_LEN + 0.0165 * math.sin(a)))
        vs, fs = extrude_outline(pts, 0.0018, y)
        ob = mesh_obj("cageplate%d" % k, vs, fs, m if k == 0 else MATS["alu_dark"], cage)
        set_smooth_angle(ob, 40)
    H["pulleys"] = []
    for k in range(2):
        pr = empty("pulley%d" % k, (0, 0, 0), root)
        me = gear_mesh("pulley%d" % k, 11, 0.0024, 0.006, tip_h=0.0030)
        me.materials.append(MATS["alu_dark"])
        obj_from_mesh("pulley%dgear" % k, me, pr)
        vs, fs = cylinder_verts(0.0042, 0.019, 16, 'Y')
        mesh_obj("pulleybolt%d" % k, vs, fs, MATS["chrome"], pr)
        H["pulleys"].append(pr)
    H["rd_root"] = root
    H["rd_empty"] = pe
    return pe


def build_fd():
    pe = part("fd", (0.0, -0.03, 0.42), (0.05, -0.30, 0.22), spin=(0.2, 0.4, 0.1), tilt=(0.4, 0, 0.3))
    o = pe.location
    m = MATS["rd_body"]
    # clamp band on seat tube
    st_dir = (Vector(V(*SEAT_TOP)) - Vector(V(*BB))).normalized()
    cpos = Vector(V(*BB)) + st_dir * 0.19
    vs, fs = cylinder_verts(0.0195, 0.016, 32, 'Z')
    q = st_dir.to_track_quat('Z', 'Y').to_matrix()
    ob = mesh_obj("fdclamp", [q @ Vector(v) + cpos - o for v in vs], fs, MATS["alu_dark"], pe)
    set_smooth_angle(ob, 40)
    H["fd_clamp_pos"] = cpos
    cage = empty("fd_cage", (0, 0, 0), pe)
    # cage plates follow the 50T arc above the top run, behind the top
    R = cg.pitch_r(50) + 0.010
    for k, dy in enumerate((-0.0085, 0.0085)):
        pts = []
        a0, a1 = math.radians(70), math.radians(128)
        for i in range(13):
            a = a0 + (a1 - a0) * i / 12
            pts.append((BB[0] + R * math.cos(a), BB[1] + R * math.sin(a)))
        for i in range(13):
            a = a1 - (a1 - a0) * i / 12
            pts.append((BB[0] + (R + 0.020 - 0.006 * (i / 12)) * math.cos(a), BB[1] + (R + 0.022) * math.sin(a)))
        vs, fs = extrude_outline(pts[::-1], 0.0016, 0)
        ob = mesh_obj("fdplate%d" % k, [(v[0] - o.x, v[1] + dy, v[2] - o.z) for v in vs], fs, MATS["chrome"] if k == 0 else MATS["alu_dark"], cage)
        set_smooth_angle(ob, 40)
    # arm linking clamp to cage
    H["fd_cage"] = cage
    me = bpy.data.meshes.new("fdarm"); me.materials.append(m)
    H["fd_arm"] = obj_from_mesh("fdarm", me, pe)
    H["fd_empty"] = pe
    return pe


def build_chain():
    pe = part("chain", (-0.2, -0.045, 0.29), (-0.05, -0.18, 0.02), spin=(0.05, 0.2, 0.05), tilt=(0.35, 0.0, 0.1))
    mi, mo = chain_meshes()
    H["links"] = []
    for i in range(102):
        ob = obj_from_mesh("link%03d" % i, mi if i % 2 == 0 else mo, pe)
        ob.rotation_mode = 'QUATERNION'
        H["links"].append(ob)
    H["chain_empty"] = pe


def build_cables():
    """shift cable from right hood -> down tube (internal) -> chainstay -> rear derailleur."""
    pe = part("cables", (0.25, 0, 0.6), (0.0, 0.25, 0.10), spin=(0, 0, 0.1), tilt=(0.1, 0.0, 0.2))
    o = pe.location
    bx, bz = BAR_C
    hp = Vector((bx + 0.083, -0.210, bz - 0.030))
    pts = [
        hp + Vector((0.0, 0.0, 0.012)),
        hp + Vector((-0.03, 0.0, 0.006)),
        Vector((bx + 0.03, -0.20, bz - 0.006)),
        Vector((bx + 0.005, -0.15, bz - 0.012)),
        Vector((bx - 0.005, -0.06, bz - 0.014)),
        Vector((bx - 0.04, -0.03, bz - 0.05)),
        Vector((HT_BOT[0] - 0.01, -0.03, HT_BOT[1] + 0.03)),
        Vector((HT_BOT[0] - 0.05, -0.02, HT_BOT[1] - 0.02)),
    ]
    # inside down tube to BB
    a = Vector(V(*HT_BOT)); b = Vector(V(*BB))
    for t in (0.18, 0.4, 0.6, 0.8, 0.92):
        p = a.lerp(b, t)
        pts.append(Vector((p.x, -0.006, p.z + 0.004)))
    pts.append(Vector((BB[0] - 0.01, -0.03, BB[1] - 0.012)))
    # inside drive-side chainstay
    a = Vector(V(BB[0] - 0.02, BB[1], -0.035)); b = Vector(V(REAR[0] + 0.012, REAR[1], -0.064))
    for t in (0.12, 0.35, 0.6, 0.82):
        p = a.lerp(b, t)
        pts.append(Vector((p.x, p.y, p.z - 0.001)))
    # exit port & loop down to RD barrel
    pts += [Vector((REAR[0] + 0.07, -0.058, REAR[1] - 0.012)), Vector((REAR[0] + 0.05, -0.075, REAR[1] - 0.005)),
            Vector((REAR[0] + 0.02, -0.088, REAR[1] + 0.0)), Vector((REAR[0] - 0.002, -0.087, REAR[1] - 0.006)),
            Vector((REAR[0] - 0.008, -0.083, REAR[1] - 0.012))]
    sm = catmull([tuple(p) for p in pts], 8)
    ob, L, lens = sweep_tube("shiftcable", sm, 0.0016, MATS["cable"], pe, 10, origin=o, uv=True)
    H["cable_obj"] = ob
    H["cable_pts"] = [Vector(p) for p in sm]
    H["cable_lens"] = [l / L for l in lens]
    # housing (black) outside frame portions: bar->port, port->RD
    k1 = 8 * 7 + 1
    sweep_tube("housing1", sm[16:k1], 0.0028, MATS["housing"], pe, 14, origin=o)
    sweep_tube("housing2", sm[-34:-3], 0.0028, MATS["housing"], pe, 14, origin=o)
    return pe


def cable_point(u):
    pts, lens = H["cable_pts"], H["cable_lens"]
    for i in range(1, len(lens)):
        if lens[i] >= u:
            f = (u - lens[i - 1]) / max(lens[i] - lens[i - 1], 1e-9)
            return pts[i - 1].lerp(pts[i], f)
    return pts[-1]


def build_bolts():
    """loose bolts that fly in exploded view (bottle cage bosses + seat clamp)"""
    H["bolt_parts"] = []
    spots = [(Vector(V(0.20, 0.47, 0.0)) + Vector((0, 0, 0)), (0.25, 0.18, 0.05)),
             (Vector(V(0.12, 0.43, 0.0)), (0.10, 0.22, -0.15)),
             (Vector(V(-0.155, 0.76, 0.0)), (-0.20, -0.15, 0.35)),
             (Vector(V(-0.08, 0.56, 0.0)), (-0.15, 0.26, 0.12)),
             (Vector(V(0.03, 0.30, -0.06)), (0.15, -0.28, -0.20))]
    for i, (c, off) in enumerate(spots):
        pe = part("bolt%d" % i, tuple(c), off, spin=(0.8, 0.6, 0.4), tilt=(0.7, 0.3, 0.9))
        # hex head + threaded shank
        vs, fs = cylinder_verts(0.0055, 0.005, 6, 'Y')
        mesh_obj("bolthead%d" % i, [(v[0], v[1] - 0.004, v[2]) for v in vs], fs, MATS["chrome"], pe)
        vs, fs = cylinder_verts(0.0025, 0.014, 12, 'Y')
        mesh_obj("boltshank%d" % i, [(v[0], v[1] + 0.006, v[2]) for v in vs], fs, MATS["brushed"], pe)
        pe.scale = (1, 1, 1)
        H["bolt_parts"].append(pe)


# -------------------------------------------------------------- hand (metaball)

def capsule_bm(bm, p0, p1, r0, r1=None, seg=20, rings=6):
    r1 = r0 if r1 is None else r1
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    q = d.to_track_quat('Z', 'Y').to_matrix()
    rows = []
    # bottom hemisphere
    for j in range(rings, 0, -1):
        th = (math.pi / 2) * j / rings
        rows.append((-r0 * math.sin(th), r0 * math.cos(th)))
    rows.append((0.0, r0))
    rows.append((L, r1))
    for j in range(1, rings + 1):
        th = (math.pi / 2) * j / rings
        rows.append((L + r1 * math.sin(th), r1 * math.cos(th)))
    vv = []
    for z, rr in rows:
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ring.append(bm.verts.new(q @ Vector((rr * math.cos(a), rr * math.sin(a), z)) + p0))
        vv.append(ring)
    for k in range(len(vv) - 1):
        for i in range(seg):
            i2 = (i + 1) % seg
            bm.faces.new((vv[k][i], vv[k][i2], vv[k + 1][i2], vv[k + 1][i]))
    bm.faces.new(vv[0][::-1])
    bm.faces.new(vv[-1])


def build_hand():
    ob = obj_from_mesh("hand", bpy.data.meshes.new("hand"))
    ob.data.materials.append(MATS["skin"])
    H["hand"] = ob
    return ob


def hand_segments(press):
    """capsules in hood-local coordinates (x fwd along hood, y: -outboard, z up)"""
    segs = []
    # palm: wide flat volume resting on the hood top/back
    for dy in (-0.012, -0.002, 0.008, 0.016):
        segs.append(((-0.050, dy, 0.050), (-0.004, dy * 0.9, 0.044), 0.0125))
    # wrist / forearm going back and up
    segs.append(((-0.055, 0.002, 0.052), (-0.135, 0.008, 0.088), 0.024, 0.028))
    # thumb along inner (+y) side of hood
    segs.append(((-0.040, 0.020, 0.040), (-0.012, 0.030, 0.028), 0.0105, 0.0095))
    segs.append(((-0.012, 0.030, 0.028), (0.014, 0.027, 0.022), 0.0095, 0.0085))
    # middle, ring, little fingers curl over the outer side (-y) of the hood
    for k, x0 in enumerate((-0.004, -0.016, -0.028)):
        r = 0.0088 - 0.0007 * k
        a = (x0 + 0.002, -0.006, 0.047 - 0.002 * k)
        b = (x0 + 0.010, -0.026, 0.034 - 0.002 * k)
        c = (x0 + 0.012, -0.030, 0.008 - 0.002 * k)
        d = (x0 + 0.008, -0.022, -0.010 - 0.002 * k)
        segs += [(a, b, r), (b, c, r * 0.94), (c, d, r * 0.86)]
    # index finger reaches forward-down onto the shift lever, pushing it inward (+y)
    py = 0.011 * press
    a = (0.006, -0.008, 0.050)
    b = (0.030, -0.025, 0.030)
    c = (0.030, -0.024 + 0.5 * py, 0.002)
    d = (0.022, -0.016 + py, -0.026)
    segs += [(a, b, 0.0092), (b, c, 0.0086), (c, d, 0.0078)]
    return segs


def update_hand(press, approach):
    bm = bmesh.new()
    off = Vector((-0.07, 0.0, 0.09)) * (1 - approach)
    for sgm in hand_segments(press):
        p0, p1, r0 = Vector(sgm[0]) + off, Vector(sgm[1]) + off, sgm[2]
        r1 = sgm[3] if len(sgm) > 3 else r0
        capsule_bm(bm, p0, p1, r0, r1)
    me = H["hand"].data
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True


# -------------------------------------------------------------- studio, road, lights, camera

def build_studio():
    # floor (large)
    vs = [(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)]
    fl = mesh_obj("floor", vs, [(0, 1, 2, 3)], MATS["floor"])
    fl.location = (0, 0, -0.0165)
    H["floor"] = fl
    # cyclorama backdrop behind (curved)
    vs, fs = [], []
    NX, NC = 40, 16
    prof = []
    for j in range(NC + 1):
        a = math.pi / 2 * j / NC
        prof.append((6 - 3 * math.cos(a) + 0.0, 3 - 3 * math.cos(a) if False else 3 * (1 - math.cos(a))))
    prof = [(3 + 3 * math.sin(math.pi / 2 * j / NC), 3 * (1 - math.cos(math.pi / 2 * j / NC))) for j in range(NC + 1)]
    prof += [(6.0, 6.0), (6.0, 14.0)]
    NP = len(prof)
    for i in range(NX + 1):
        x = -14 + 28 * i / NX
        for (y, z) in prof:
            vs.append((x, y, z))
    for i in range(NX):
        for j in range(NP - 1):
            fs.append((i * NP + j, (i + 1) * NP + j, (i + 1) * NP + j + 1, i * NP + j + 1))
    bd = mesh_obj("backdrop", vs, fs, MATS["backdrop"], smooth=True)
    bd.location = (0, 2.0, -0.0165)
    H["backdrop"] = bd
    # world
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.004, 0.004, 0.005, 1)
    bg.inputs["Strength"].default_value = 1.0
    H["world_bg"] = bg


def area_light(name, loc, target, size, energy, color=(1, 1, 1), shape='RECTANGLE', size_y=None, spread=None):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy
    ld.color = color
    ld.shape = shape
    ld.size = size
    if size_y:
        ld.size_y = size_y
    if spread:
        ld.spread = spread
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    link(ob)
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


def build_lights():
    H["lights"] = {}
    H["lights"]["key"] = area_light("key", (1.2, -2.4, 2.3), (0, 0, 0.5), 1.8, 125, (1.0, 0.96, 0.92))
    H["lights"]["rim1"] = area_light("rim1", (-1.8, 1.6, 1.4), (0, 0, 0.5), 0.25, 260, (0.85, 0.92, 1.0), 'RECTANGLE', 2.2)
    H["lights"]["rim2"] = area_light("rim2", (2.0, 1.4, 1.2), (0, 0, 0.5), 0.25, 200, (0.85, 0.92, 1.0), 'RECTANGLE', 2.2)
    H["lights"]["top"] = area_light("top", (0, 0, 3.2), (0, 0, 0), 1.6, 50, (1, 1, 1))
    H["lights"]["backwash"] = area_light("backwash", (0, 4.5, 3.0), (0, 7, 1), 4.0, 110, (0.6, 0.65, 0.75))
    H["lights"]["kick"] = area_light("kick", (-1.0, -1.6, 0.25), (0, 0, 0.35), 0.6, 25, (0.9, 0.95, 1.0))
    # reflection cards (invisible to camera)
    for nm, loc, tgt, sx, sy in (("card1", (0.0, -1.5, 1.9), (0, 0, 0.4), 2.0, 0.25), ("card2", (-1.4, -0.8, 1.0), (0, 0, 0.4), 0.15, 1.5)):
        vs = [(-sx / 2, -sy / 2, 0), (sx / 2, -sy / 2, 0), (sx / 2, sy / 2, 0), (-sx / 2, sy / 2, 0)]
        ob = mesh_obj(nm, vs, [(0, 1, 2, 3)], MATS["card"])
        ob.location = loc
        d = Vector(tgt) - Vector(loc)
        ob.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        ob.visible_camera = False
        ob.visible_shadow = False
        ob.visible_diffuse = False


def build_road():
    root = empty("road_root", (0, 0, 0))
    vs = [(-60, -2.6, 0.0), (60, -2.6, 0.0), (60, 2.6, 0.0), (-60, 2.6, 0.0)]
    r = mesh_obj("road", vs, [(0, 1, 2, 3)], MATS["road"], root)
    for s in (-1, 1):
        vs = [(-60, s * 2.6, 0.0), (60, s * 2.6, 0.0), (60, s * 40, -0.3), (-60, s * 40, -0.3)]
        f = (0, 1, 2, 3) if s < 0 else (3, 2, 1, 0)
        mesh_obj("ground%d" % s, vs, [f], MATS["ground"], root)
    # roadside posts with reflectors
    H["posts"] = []
    for i in range(30):
        x = -60 + i * 4.0
        vs, fs = cylinder_verts(0.04, 0.9, 8, 'Z')
        ob = mesh_obj("post%d" % i, [(v[0] + x, v[1] + 2.9, v[2] + 0.45) for v in vs], fs, MATS["plastic_black"], root)
        vs, fs = cylinder_verts(0.03, 0.12, 8, 'Z')
        mesh_obj("refl%d" % i, [(v[0] + x, v[1] + 2.86, v[2] + 0.8) for v in vs], fs, MATS["marker"], root)
    H["road_root"] = root
    root.hide_render = True
    for ch in root.children:
        ch.hide_render = True


def build_camera():
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    link(cam)
    bpy.context.scene.camera = cam
    cd.sensor_fit = 'VERTICAL'
    cd.sensor_height = 24.0
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = 2.8
    cd.clip_start = 0.005
    cd.clip_end = 200
    H["cam"] = cam


def setup_render(res=(720, 1280), samples=24):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.03
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 3
    sc.cycles.glossy_bounces = 2
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.diffuse_bounces = 1
    sc.cycles.transmission_bounces = 1
    sc.cycles.use_light_tree = False
    sc.cycles.denoising_quality = 'BALANCED'
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 1.0
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.fps = 30
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = THREADS


def build_all(res=(720, 1280), samples=24):
    clear()
    make_materials()
    build_studio()
    build_lights()
    build_road()
    build_camera()
    build_frame()
    build_fork()
    build_wheel("rear_wheel", REAR, (-0.30, 0.05, 0.12), rear=True)
    build_wheel("front_wheel", FRONT, (0.32, 0.05, 0.10), rear=False)
    build_cassette()
    build_crankset()
    build_pedals()
    build_seat()
    build_bar()
    build_derailleur()
    build_fd()
    build_chain()
    build_cables()
    build_bolts()
    build_hand()
    setup_render(res, samples)
    # bike root to allow global placement (for road scenes)
    root = empty("bike_root", (0, 0, 0))
    for p in PARTS:
        p["empty"].parent = root
    H["hand"].parent = H["hood_empty"]
    H["bike_root"] = root
    return H
