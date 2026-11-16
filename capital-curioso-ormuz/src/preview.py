import sys, skia, numpy as np
sys.path.insert(0, '.')
from scenes import frame, W, H
from PIL import Image
times=[float(x) for x in sys.argv[2].split(',')]
ims=[]
for t in times:
    s=skia.Surface(W,H); c=s.getCanvas(); frame(c,t)
    a=s.makeImageSnapshot().toarray()[:,:,[2,1,0]]
    ims.append(Image.fromarray(a).resize((360,640)))
cols=min(len(ims),5); rows=(len(ims)+cols-1)//cols
sheet=Image.new('RGB',(cols*360,rows*640))
for i,im in enumerate(ims): sheet.paste(im,((i%cols)*360,(i//cols)*640))
sheet.save(sys.argv[1])
