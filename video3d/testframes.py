import sys, os, json
sys.argv=[sys.argv[0]]
import main as M
from bpy_extras.object_utils import world_to_camera_view
import bpy
out=os.environ['OUTDIR']; os.makedirs(out,exist_ok=True)
meta={}
for f in [int(x) for x in os.environ['FR'].split(',')]:
    t=f/30
    a,foot,studio,k=M.pose(t); M.set_camera(t); bpy.context.view_layer.update()
    meta[f]=dict(a={kk:M.project(v) for kk,v in a.items()},foot=[M.project(v) for v in foot],studio=studio)
    M.S.render.filepath=os.path.join(out,'f_%05d.png'%f); bpy.ops.render.render(write_still=True)
json.dump(meta,open(os.path.join(out,'meta_test.json'),'w'))
