import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
U="/root/.claude/uploads/eeaa32a9-3bb8-5bc3-8e55-c80a01f77588/"
src={"fans":"ec1765c1","collage":"e8ee3e3c","yelena":"13e68d8c","team3":"78fd3a77","jump":"015b0225","stadium":"58ac4ccc","infantino":"fb69b3c4","crest":"0e48fea3","fdflogo":"ea5b69d9","usa":"66bb4e87"}
for k,v in src.items():
    im=Image.open(U+v+"-image.jpg").convert("RGB")
    print(k,im.size)
    if k in("crest","fdflogo"):
        im.save(f"build/img/{k}.png"); continue
    im=ImageEnhance.Color(im).enhance(0.78)
    im=ImageEnhance.Contrast(im).enhance(1.12)
    a=np.asarray(im).astype(np.float32)/255
    # filmic darken + navy shadows / warm highlights
    lum=a.mean(axis=2,keepdims=True)
    a=a*0.80
    shadow=(1-lum)**2
    a=a+shadow*np.array([-0.02,0.0,0.06])*1.0
    a=a*np.array([0.97,0.98,1.03])
    h,w=a.shape[:2]
    yy,xx=np.mgrid[0:h,0:w]
    d=np.sqrt(((xx-w/2)/(w/2))**2+((yy-h/2)/(h/2))**2)
    vig=1-0.38*np.clip(d-0.35,0,1)**1.4
    a=a*vig[...,None]
    a=np.clip(a,0,1)
    Image.fromarray((a*255).astype(np.uint8)).save(f"build/img/{k}.jpg",quality=93)
