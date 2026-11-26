import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, scene as S, outline
from PIL import Image
args = sys.argv[1:]
mode, out = args[0], args[1]
os.makedirs(out, exist_ok=True)
sc = S.build(); S.precompute()
sc.render.use_freestyle = False; sc.render.dither_intensity = 0
sh = sc.display.shading
if mode == 'times':
    frames = [int(round(float(x) * S.FPS)) for x in args[2:]]
else:
    a, b = int(args[2]), int(args[3]); frames = list(range(a, b))
tag = '%s_%d' % (mode, frames[0])
tmpb = os.path.join(out, '_b_%s.png' % tag); tmpi = os.path.join(out, '_i_%s.png' % tag)
meta = {}
for f in frames:
    t = f / S.FPS
    S.pose(t)
    meta[f] = S.project(t)
    fn = os.path.join(out, 'f%05d.png' % f)
    if mode == 'meta' or (mode == 'range' and os.path.exists(fn)): continue
    t0 = time.time()
    sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_shadows = True; sh.show_cavity = True
    sc.display.render_aa = '8'
    sc.render.filepath = tmpb; bpy.ops.render.render(write_still=True)
    sh.light = 'FLAT'; sh.color_type = 'RANDOM'; sh.show_shadows = False; sh.show_cavity = False
    sc.display.render_aa = 'OFF'
    sc.render.filepath = tmpi; bpy.ops.render.render(write_still=True)
    Image.fromarray(outline.outline(tmpb, tmpi)).save(fn, compress_level=1)
    print('FRAME', f, round(time.time() - t0, 2), flush=True)
json.dump(meta, open(os.path.join(out, 'meta_%s.json' % tag), 'w'))
