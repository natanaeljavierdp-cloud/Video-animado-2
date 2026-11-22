import sys, os, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
from util import *
import car as carmod
s=bpy.context.scene
s.render.engine='BLENDER_WORKBENCH'
s.render.resolution_x=540; s.render.resolution_y=960
s.render.film_transparent=True
s.view_settings.view_transform='Standard'
sh=s.display.shading
sh.light='STUDIO'; sh.color_type='MATERIAL'
sh.show_shadows=True; sh.show_cavity=True; sh.cavity_type='BOTH'
sh.show_object_outline=True; sh.object_outline_color=(0,0,0)
sh.show_backface_culling=True
sh.show_specular_highlight=False
sh.studio_light=os.environ.get('SL','Default')
t=time.time()
car, parts, M = carmod.build_car()
print("build", time.time()-t)
cam=bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); link(cam); s.camera=cam
cam.data.lens=40
def shot(name, az, el, dist, tgt=(0,0,0.5)):
    tg=Vector(tgt)
    p=tg+Vector((math.cos(math.radians(el))*math.cos(math.radians(az)), math.cos(math.radians(el))*math.sin(math.radians(az)), math.sin(math.radians(el))))*dist
    cam.location=p
    cam.rotation_euler=(tg-p).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=os.path.abspath(f'out/{name}_'+os.environ.get('SL','D')+'.png')
    t=time.time(); bpy.ops.render.render(write_still=True); print(name, time.time()-t)
os.makedirs('out',exist_ok=True)
shot('front34', 35, 15, 9)
shot('rear34', 215, 20, 9)
shot('front', 0, 8, 9)
shot('side', -90, 5, 10)
