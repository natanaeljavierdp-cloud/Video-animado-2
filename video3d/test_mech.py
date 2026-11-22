import sys, os, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
from util import *
import car as carmod, mech
s=bpy.context.scene
s.render.engine='BLENDER_WORKBENCH'
s.render.resolution_x=540; s.render.resolution_y=960
s.render.film_transparent=True
s.view_settings.view_transform='Standard'
sh=s.display.shading
sh.light='STUDIO'; sh.color_type='MATERIAL'; sh.studio_light='paint.sl'
sh.show_shadows=True; sh.show_cavity=True; sh.cavity_type='BOTH'
sh.show_object_outline=True; sh.object_outline_color=(0,0,0)
sh.show_backface_culling=True; sh.show_specular_highlight=False
car, parts, M = carmod.build_car()
E=mech.build_engine(car); G=mech.build_gearbox(car)
co=mech.build_callout(None); co['group'].location=(0,0,5)
mech.pose_engine(E, 0.7); mech.pose_gearbox(G, 0.3, 0.2); mech.pose_callout(co, 0.5, 0.0, 0.0)
for m in ('yellow','black','glass','headlight','taillight'):
    set_alpha(MATS[m], 0.18)
cam=bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); s.camera=cam
cam.data.lens=40
def shot(name, az, el, dist, tgt=(0,0,0.5), lens=40):
    cam.data.lens=lens
    tg=Vector(tgt)
    p=tg+Vector((math.cos(math.radians(el))*math.cos(math.radians(az)), math.cos(math.radians(el))*math.sin(math.radians(az)), math.sin(math.radians(el))))*dist
    cam.location=p
    cam.rotation_euler=(tg-p).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=os.path.abspath(f'out/{name}.png')
    t=time.time(); bpy.ops.render.render(write_still=True); print(name, time.time()-t)
shot('m1', 30, 35, 8)
shot('m2', 200, 30, 3.2, (-1.0,0,0.45))
shot('m3', -90, 5, 5.5, (0,0,6.2), 35)
shot('m4', 150, 40, 3, (-0.6,0,0.5))
