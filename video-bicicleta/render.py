"""Render driver.  usage: python3 render.py START END [--res W H] [--spp N] [--times t1,t2,..] [--out DIR]"""
import sys, os, json, math, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import scene as S
import rig as R
import timeline as T
import chaingeom as cg

ap = argparse.ArgumentParser()
ap.add_argument("start", type=int)
ap.add_argument("end", type=int)
ap.add_argument("--res", type=int, nargs=2, default=[720, 1280])
ap.add_argument("--spp", type=int, default=6)
ap.add_argument("--times", type=str, default="")
ap.add_argument("--out", type=str, default="/home/user/work/frames")
ap.add_argument("--step", type=int, default=1)
ap.add_argument("--threads", type=int, default=4)
args = ap.parse_args(sys.argv[1:])

S.THREADS = args.threads
S.build_all(res=tuple(args.res), samples=args.spp)
H = S.H
os.makedirs(args.out, exist_ok=True)
RAMP_PICK = {}


def wpos(ob, local=(0, 0, 0)):
    return ob.matrix_world @ Vector(local)


def anchors(st, g):
    bpy.context.view_layer.update()
    A = {}
    A["rd"] = wpos(H["rd_pk"], (0.0, -0.004, 0.006))
    cas = S.part_by_name if False else None
    cp = [p for p in S.PARTS if p["name"] == "cassette"][0]["empty"]
    A["cassette"] = wpos(cp, (0.0, T.COG_Y[17], 0.040))
    # ramps
    rot = H["cassette_rot"]
    R13 = cg.pitch_r(13)
    rp = []
    for a in H["ramp_angles"]:
        rp.append(wpos(rot, (R13 * math.cos(a), T.COG_Y[13] - 0.001, R13 * math.sin(a))))
    if "ramp" not in RAMP_PICK and st["t"] >= 21.8:
        # pick ramp that is highest & towards camera, and will stay visible (moves slowly)
        RAMP_PICK["ramp"] = max(range(len(rp)), key=lambda i: rp[i].z - 0.3 * rp[i].x)
    A["ramp"] = rp[RAMP_PICK.get("ramp", 0)]
    A["ramps_all"] = rp
    A["spring"] = H["rd_root"].matrix_world @ H.get("spring_local", Vector())
    crank = [p for p in S.PARTS if p["name"] == "crank"][0]["empty"]
    r50 = cg.pitch_r(50)
    a = math.radians(118)
    A["rings"] = wpos(crank, (r50 * math.cos(a) * 0.93, T.RING_Y[50], r50 * math.sin(a) * 0.93))
    A["ring_c"] = wpos(crank)
    nr = st["drive"]["n_ring"]
    rr = cg.pitch_r(nr)
    A["ring_top"] = wpos(crank, (rr * 0.70, T.RING_Y.get(nr, -0.04), rr * 0.75))
    rw = [p for p in S.PARTS if p["name"] == "rear_wheel"][0]["empty"]
    A["cog_c"] = wpos(rw)
    nc = st["drive"]["n_cog"]
    A["cog_top"] = wpos(rw, (-cg.pitch_r(nc) * 0.75, T.COG_Y.get(nc, -0.05), cg.pitch_r(nc) * 0.7))
    cab = [p for p in S.PARTS if p["name"] == "cables"][0]
    A["cable"] = cab["empty"].matrix_world @ (S.cable_point(0.15) - cab["pivot"])
    A["ratchet"] = wpos(H["ratchet_root"])
    A["marker"] = wpos(H["wheel_marker"])
    A["bike_c"] = wpos(H["bike_root"], (0.1, 0, 0.55))
    parts = {}
    for p in S.PARTS:
        parts[p["name"]] = [list(R.project([wpos(p["empty"])])[0]), p["e"]]
    names = [k for k in A if k != "ramps_all"]
    proj = R.project([A[k] for k in names])
    out = {k: list(v) for k, v in zip(names, proj)}
    out["ramps_all"] = [list(v) for v in R.project(A["ramps_all"])]
    out["parts"] = parts
    out["beta"] = g["beta"]
    return out


times = None
if args.times:
    times = [float(x) for x in args.times.split(",")]
    frames = [int(round(x * T.FPS)) for x in times]
else:
    frames = list(range(args.start, args.end, args.step))

# simulate drive state up to first frame (sprocket phase continuity)
first = frames[0]
t0 = time.time()
sim_from = 0 if times is None else max(0, first - 400)
for f in range(sim_from, first):
    t = f / T.FPS
    for name, fn, w in T.shots_at(t):
        st = fn(t)
        R.compute_drive(st["drive"], st.get("drive_id", "main"))
        if st["t"] >= 21.8 and "ramp" not in RAMP_PICK:
            pass
print("simulated", first - sim_from, "frames in", round(time.time() - t0, 1), "s", flush=True)

meta_path = os.path.join(args.out, "meta_%05d_%05d_%d.jsonl" % (frames[0], frames[-1], int(time.time())))
with open(meta_path, "a") as meta:
    for f in frames:
        t = f / T.FPS
        for name, fn, w in T.shots_at(t):
            out_png = os.path.join(args.out, name, "%05d.png" % f)
            os.makedirs(os.path.dirname(out_png), exist_ok=True)
            st = fn(t)
            g = R.apply(st)
            an = anchors(st, g)
            if os.path.exists(out_png) and times is None:
                meta.write(json.dumps(dict(f=f, shot=name, w=w, a=an)) + "\n")
                continue
            bpy.context.scene.render.filepath = out_png
            tt = time.time()
            bpy.ops.render.render(write_still=True)
            meta.write(json.dumps(dict(f=f, shot=name, w=w, a=an)) + "\n")
            meta.flush()
            print("frame", f, name, round(time.time() - tt, 2), flush=True)
