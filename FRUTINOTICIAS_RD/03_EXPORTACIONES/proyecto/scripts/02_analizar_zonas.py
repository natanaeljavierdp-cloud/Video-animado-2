"""Detecta por fotograma la caja de la cabeza de Dania (hojas + rostro de fresa + cabello)
en cada clip original (720x1280). Salida: build/zonas_cabeza.json  {clip: [[x0,y0,x1,y1] por frame]}
Método: máscara de color (hojas verdes / rojo fresa), apertura morfológica para eliminar
líneas finas del set, y selección del blob rojo grande más alto (rostro)."""
import cv2, numpy as np, json, glob, os, sys
from scipy import ndimage
SRC=sys.argv[1]; OUT=sys.argv[2]
res={}
for f in sorted(glob.glob(os.path.join(SRC,"*.mp4"))):
    cap=cv2.VideoCapture(f); boxes=[]
    while True:
        ok,fr=cap.read()
        if not ok: break
        hsv=cv2.cvtColor(fr,cv2.COLOR_BGR2HSV); h,s,v=[hsv[...,i].astype(int) for i in range(3)]
        red=(((h<=8)|(h>=172))&(s>120)&(v>90)).astype(np.uint8)
        red=cv2.morphologyEx(red,cv2.MORPH_OPEN,np.ones((21,21),np.uint8))
        lab,n=ndimage.label(red)
        best=None
        if n:
            objs=ndimage.find_objects(lab); sizes=ndimage.sum(red,lab,range(1,n+1))
            cands=[(o,sz) for o,sz in zip(objs,sizes) if sz>6000]
            # rostro = blob grande cuyo borde superior es el más alto y es aproximadamente redondeado
            cands.sort(key=lambda t:t[0][0].start)
            for o,sz in cands:
                hh=o[0].stop-o[0].start; ww=o[1].stop-o[1].start
                if 0.6<hh/ww<1.8: best=o; break
        if best is None: boxes.append(None); continue
        y0,y1=best[0].start,best[0].stop; x0,x1=best[1].start,best[1].stop
        fw=x1-x0
        # hojas verdes encima del rostro
        green=((h>=30)&(h<=85)&(s>80)&(v>60)).astype(np.uint8)
        gy0=max(0,y0-int(0.9*fw)); gx0=max(0,x0-fw//3); gx1=min(720,x1+fw//3)
        g=green[gy0:y0+fw//4,gx0:gx1]; rows=np.where(g.sum(1)>3)[0]
        top=gy0+rows[0] if len(rows) else y0-int(0.35*fw)
        # cabello: ampliación lateral
        boxes.append([int(max(0,x0-0.35*fw)),int(max(0,top)),int(min(720,x1+0.35*fw)),int(min(1280,y1+0.04*fw))])
    res[os.path.basename(f)]=boxes
    ok=[b for b in boxes if b]; print(os.path.basename(f),len(boxes),"none:",boxes.count(None),
        "first",boxes[0],"mid",boxes[len(boxes)//2],"last",boxes[-1])
json.dump(res,open(OUT,"w"))
