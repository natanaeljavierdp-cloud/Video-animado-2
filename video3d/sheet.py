import sys, glob
from PIL import Image, ImageDraw
files=sorted(glob.glob(sys.argv[1]+'/f_*.png'))
a=int(sys.argv[2]); b=int(sys.argv[3]); out=sys.argv[4]
sel=[f for f in files if a<=int(f[-9:-4])<b]
n=len(sel); cols=6; rows=(n+cols-1)//cols
w,h=Image.open(sel[0]).size
th=(w//1*1, h)
W=Image.new('RGB',(cols*w,rows*h),(160,175,192))
d=ImageDraw.Draw(W)
for i,f in enumerate(sel):
    im=Image.open(f).convert('RGBA')
    W.paste(im,((i%cols)*w,(i//cols)*h),im)
    d.text(((i%cols)*w+5,(i//cols)*h+5),'%.1f'%(int(f[-9:-4])/30),fill=(0,0,0))
W.save(out)
