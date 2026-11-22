"""Per-frame application of a state dict onto the built scene."""
import bpy, bmesh, math
from mathutils import Vector, Matrix, Quaternion, Euler
import chaingeom as cg
import scene as S

P = cg.P
NLINKS = 102
H = S.H
TWO_PI = 2 * math.pi


def n_eff(r):
    return math.pi / math.asin(P / (2 * r))


def build_path(r_ring, r_cog, phi, rg=None):
    rg = r_cog if rg is None else rg
    gx = cg.REAR[0] + 0.006
    gz = cg.REAR[1] - rg - cg.pitch_r(cg.JOCKEY_N) - 0.008
    tx, tz = gx + cg.CAGE_LEN * math.sin(phi), gz - cg.CAGE_LEN * math.cos(phi)
    ring = cg.Circle(cg.BB[0], cg.BB[1], 34, +1, "ring"); ring.r = r_ring; ring.n = n_eff(r_ring)
    T = cg.Circle(tx, tz, cg.JOCKEY_N, +1, "T")
    G = cg.Circle(gx, gz, cg.JOCKEY_N, -1, "G")
    cog = cg.Circle(cg.REAR[0], cg.REAR[1], 11, +1, "cog"); cog.r = r_cog; cog.n = n_eff(r_cog)
    return cg.Path([ring, T, G, cog])


def solve(r_ring, r_cog, rg=None):
    target = NLINKS * P
    lo, hi = -0.9, 1.7
    flo = build_path(r_ring, r_cog, lo, rg).length - target
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        fm = build_path(r_ring, r_cog, mid, rg).length - target
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    phi = 0.5 * (lo + hi)
    return phi, build_path(r_ring, r_cog, phi, rg)


class Drive:
    """keeps integrated sprocket angles between frames"""

    def __init__(self):
        self.beta = {"ring": 0.0, "cog": 0.0, "G": 0.0, "T": 0.0}
        self.s_prev = None
        self.first = True


DRIVES = {}


def wrap_pm(a, period):
    return (a + period / 2) % period - period / 2


def compute_drive(d, did):
    """d: dict with s, r_ring, r_cog, y_ring, y_cogc, y_der, n_ring, n_cog, w_ring, w_cog
    returns geometry dict"""
    st = DRIVES.setdefault(did, Drive())
    phi, path = solve(d["r_ring"], d["r_cog"], d.get("r_cog_geom"))
    rollers = []
    names = {c.name: c for c in path.circles}
    yof = {"ring": d["y_ring"], "cog": d["y_cogc"], "T": d["y_der"], "G": d["y_der"]}
    s0 = d["s"]
    arc_roller = {}
    for i in range(NLINKS):
        x, z, owner, f, ang = path.point(s0 + i * P)
        if ">" in owner:
            a, b = owner.split(">")
            y = yof[a] + (yof[b] - yof[a]) * f
        else:
            y = yof[owner]
            if owner not in arc_roller:
                arc_roller[owner] = ang
        rollers.append(Vector((x, y, z)))
    # sprocket angles
    ds = 0.0 if st.s_prev is None else (s0 - st.s_prev)
    st.s_prev = s0
    nteeth = {"ring": d["n_ring"], "cog": d["n_cog"], "G": cg.JOCKEY_N, "T": cg.JOCKEY_N}
    neng = {"ring": names["ring"].n, "cog": names["cog"].n, "G": cg.JOCKEY_N, "T": cg.JOCKEY_N}
    wts = {"ring": d.get("w_ring", 1.0), "cog": d.get("w_cog", 1.0), "G": 1.0, "T": 1.0}
    out = {}
    for k in ("ring", "cog", "G", "T"):
        sign = -1 if k == "G" else 1
        pred = st.beta[k] + sign * ds * TWO_PI / (neng[k] * P)
        if k in arc_roller:
            per = TWO_PI / nteeth[k]
            target = -arc_roller[k]
            delta = wrap_pm(target - pred, per)
            w = 1.0 if st.first else wts[k]
            pred = pred + w * delta
        st.beta[k] = pred
        out[k] = pred
    st.first = False
    G = names["G"]; T = names["T"]
    return dict(phi=phi, rollers=rollers, beta=out, G=(G.cx, G.cz), T=(T.cx, T.cz))


def place_chain(rollers, chain_pivot):
    links = H["links"]
    up = Vector((0, 1, 0))
    for i, ob in enumerate(links):
        a = rollers[i]
        b = rollers[(i + 1) % NLINKS]
        c = (a + b) / 2
        xd = (b - a).normalized()
        zd = xd.cross(up).normalized()
        yd = zd.cross(xd)
        M = Matrix((xd, yd, zd)).transposed()
        ob.location = c - chain_pivot
        ob.rotation_quaternion = M.to_quaternion()


def helix_mesh(me, p0, p1, radius=0.0034, wire=0.0007, coils=9, seg=10, steps_per=16):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    q = d.to_track_quat('Z', 'Y').to_matrix()
    nst = coils * steps_per
    vs, fs = [], []
    for i in range(nst + 1):
        t = i / nst
        a = TWO_PI * coils * t
        c = Vector((radius * math.cos(a), radius * math.sin(a), L * t))
        tg = Vector((-radius * math.sin(a) * TWO_PI * coils, radius * math.cos(a) * TWO_PI * coils, L)).normalized()
        nr = Vector((math.cos(a), math.sin(a), 0))
        bn = tg.cross(nr)
        for j in range(seg):
            b = TWO_PI * j / seg
            v = c + (nr * math.cos(b) + bn * math.sin(b)) * wire
            vs.append(q @ v + p0)
    for i in range(nst):
        for j in range(seg):
            j2 = (j + 1) % seg
            fs.append((i * seg + j, i * seg + j2, (i + 1) * seg + j2, (i + 1) * seg + j))
    me.clear_geometry()
    me.from_pydata([tuple(v) for v in vs], [], fs)
    for p in me.polygons:
        p.use_smooth = True


def box_between(ob, p0, p1, w, h, upref=Vector((0, 0, 1))):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    xd = d.normalized()
    zd = (upref - xd * upref.dot(xd)).normalized()
    yd = zd.cross(xd)
    M = Matrix((xd, yd, zd)).transposed().to_4x4()
    ob.matrix_basis = Matrix.Translation((p0 + p1) / 2) @ M @ Matrix.Diagonal((d.length + w, w, h, 1))


def plate_between(ob, p0, p1, width_x, thick, wax):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    xd = d.normalized()
    zd = (wax - xd * xd.dot(wax)).normalized()
    yd = zd.cross(xd)
    M = Matrix((xd, yd, zd)).transposed().to_4x4()
    ob.matrix_basis = Matrix.Translation((p0 + p1) / 2) @ M @ Matrix.Diagonal((d.length + 0.010, thick, width_x, 1))


def part_by_name(n):
    for p in S.PARTS:
        if p["name"] == n:
            return p


def apply(st):
    t = st["t"]
    # ---------------- drivetrain
    d = st["drive"]
    g = compute_drive(d, st.get("drive_id", "main"))
    beta = g["beta"]
    H["crank_rot"].rotation_euler = (0, beta["ring"], 0)
    H["cassette_rot"].rotation_euler = (0, beta["cog"], 0)
    H["rear_wheel_rot"].rotation_euler = (0, beta["cog"], 0)
    H["front_wheel_rot"].rotation_euler = (0, beta["cog"] if st.get("road", 0) else 0.0, 0)
    # pedals follow crank ends
    L = H["arm_len"]
    b = beta["ring"]
    for pe, body, side in H["pedals"]:
        p = part_by_name("pedal%d" % side)
        if side < 0:
            p["pivot"] = Vector((cg.BB[0] + L * math.cos(b), -0.098, cg.BB[1] - L * math.sin(b)))
        else:
            p["pivot"] = Vector((cg.BB[0] - L * math.cos(b), 0.098, cg.BB[1] + L * math.sin(b)))
    # chain
    cp = part_by_name("chain")
    place_chain(g["rollers"], cp["pivot"])
    # rear derailleur
    rdp = part_by_name("rd")
    o = rdp["pivot"]
    ydr = d["y_der"]
    Gx, Gz = g["G"]; Tx, Tz = g["T"]
    H["pulleys"][0].location = Vector((Gx, ydr, Gz)) - o
    H["pulleys"][0].rotation_euler = (0, beta["G"], 0)
    H["pulleys"][1].location = Vector((Tx, ydr, Tz)) - o
    H["pulleys"][1].rotation_euler = (0, beta["T"], 0)
    H["rd_cage"].location = Vector((Gx, ydr, Gz)) - o
    H["rd_cage"].rotation_euler = (0, -g["phi"], 0)
    _, pk = S.rd_geom(ydr, d["r_cog_geom"])
    H["rd_pk"].location = pk - o
    B = H["rd_B"]
    A = H["rd_A"]
    ends = [(B + A / 2, pk + A / 2), (B - A / 2, pk - A / 2)]
    for k, (a, b) in enumerate(ends):
        plate_between(H["rd_links"][k], a - o, b - o, 0.022 if k == 0 else 0.016, 0.0028, H["rd_nrm"])
        qn = H["rd_nrm"].to_track_quat('X', 'Z')
        for pin, pp in ((H["rd_pins"][2 * k], a), (H["rd_pins"][2 * k + 1], b)):
            pin.location = pp - o
            pin.rotation_mode = 'QUATERNION'
            pin.rotation_quaternion = qn
    sp0, sp1 = ends[0][0] - o + Vector((0.0, 0, 0)), ends[1][1] - o
    helix_mesh(H["rd_spring"].data, sp0, sp1)
    H["spring_local"] = (sp0 + sp1) / 2
    # front derailleur
    fdp = part_by_name("fd")
    H["fd_cage"].location = (0, d["y_fd"] - fdp["pivot"].y, 0)
    # ---------------- explode
    for p in S.PARTS:
        e = st["explode"].get(p["name"], st["explode"].get("*", 0.0))
        p["e"] = e
        tt = st.get("spin_t", t)
        bob = Vector((0, 0, 0.012 * math.sin(tt * 0.9 + hash(p["name"]) % 7)))
        p["empty"].location = p["pivot"] + p["off"] * e + bob * e
        r = (p["tilt"] + p["spin"] * tt) * e
        p["empty"].rotation_euler = Euler((r.x, r.y, r.z), 'XYZ')
    # ---------------- materials / fx
    xv = H["xray_vals"]
    xv["frame"].outputs[0].default_value = st.get("xray_frame", 0.0)
    xv["hood"].outputs[0].default_value = st.get("xray_hood", 0.0)
    xv["rd"].outputs[0].default_value = st.get("xray_rd", 0.0)
    H["cable_pulse"].outputs[0].default_value = st.get("pulse", -1.0)
    H["cable_amp"].outputs[0].default_value = st.get("pulse_amp", 0.0)
    H["cable_line"].outputs[0].default_value = st.get("pulse_line", 0.0)
    H["ramp_glow"].outputs[0].default_value = st.get("ramp_glow", 0.0)
    H["marker_bsdf"].inputs["Emission Strength"].default_value = st.get("marker_glow", 0.0)
    # shifter
    side = -1
    H["shift_lever"].rotation_euler = (st.get("lever", 0.0) * math.radians(22), 0, 0)
    H["ratchet_rot"].rotation_euler = (st.get("ratchet", 0.0), 0, 0)
    H["pawl"].rotation_euler = (st.get("pawl", 0.0), 0, 0)
    # hand
    hv = st.get("hand_vis", 0.0)
    H["hand"].hide_render = hv < 0.01
    if hv >= 0.01:
        S.update_hand(st.get("hand_press", 0.0), st.get("hand_app", 1.0))
    # ---------------- environment
    road = st.get("road", 0)
    H["floor"].hide_render = road > 0
    H["backdrop"].hide_render = road > 0
    rr = H["road_root"]
    rr.hide_render = road == 0
    for ch in rr.children:
        ch.hide_render = road == 0
    pitch = st.get("pitch", 0.0)
    H["bike_root"].rotation_euler = (0, -pitch, st.get("bike_rot", 0.0))
    rr.rotation_euler = (0, -pitch, 0)
    dist = beta["cog"] * 0.357 if road else 0.0
    H["road_map"].inputs["Location"].default_value = (dist, 0, 0)
    rr.location = (0, 0, -0.0165)
    for i, ob in enumerate([c for c in rr.children if c.name.startswith("post") or c.name.startswith("refl")]):
        pass
    posts = [c for c in rr.children if c.name.startswith(("post", "refl"))]
    # move posts with road (wrap every 4m) — they are built at x=-60+4i; shift via delta location
    sh = -(dist % 4.0)
    for ob in posts:
        ob.location = (sh, 0, 0)
    H["world_bg"].inputs["Color"].default_value = st.get("world", (0.004, 0.004, 0.005, 1))
    for k, v in st.get("lights", {}).items():
        H["lights"][k].data.energy = v
    # ---------------- camera
    cam = H["cam"]
    pos, tgt = Vector(st["cam_pos"]), Vector(st["cam_tgt"])
    cam.location = pos
    q = (tgt - pos).to_track_quat('-Z', 'Y')
    roll = st.get("cam_roll", 0.0)
    if roll:
        q = q @ Quaternion((0, 0, 1), roll)
    cam.rotation_euler = q.to_euler()
    cam.data.lens = st.get("lens", 50)
    cam.data.dof.aperture_fstop = st.get("fstop", 4.0)
    cam.data.dof.focus_distance = st.get("focus", (tgt - pos).length)
    return g


def project(pts_world):
    """project world points to normalized image coords (x right, y down) using the scene camera"""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    cam = H["cam"]
    bpy.context.view_layer.update()
    out = []
    for p in pts_world:
        co = world_to_camera_view(sc, cam, Vector(p))
        out.append((co.x, 1 - co.y, co.z))
    return out


def world_of(ob, local=(0, 0, 0)):
    bpy.context.view_layer.update()
    return ob.matrix_world @ Vector(local)
