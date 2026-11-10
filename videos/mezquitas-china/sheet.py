import sys
from PIL import Image
fs=sys.argv[2:]; ims=[Image.open(f).resize((360,640)) for f in fs]
s=Image.new('RGB',(360*len(ims)+8*(len(ims)-1),640),(255,0,255))
for i,im in enumerate(ims): s.paste(im,(i*368,0))
s.save(sys.argv[1])
