import sys
from PIL import Image
fs=sys.argv[2:]; out=sys.argv[1]
ims=[Image.open(f).resize((360,640)) for f in fs]
s=Image.new('RGB',(360*len(ims)+10*(len(ims)-1),640),'white')
for i,im in enumerate(ims): s.paste(im,(i*370,0))
s.save(out,quality=85)
