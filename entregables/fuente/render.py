import numpy as np, math, json, sys, subprocess, os
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import shapefile
W,H=1080,1920; FPS=30; NAR=86.752; TOT=NAR
IMG=sys.argv[1] if len(sys.argv)>1 else '../in/video_venezuela_hegseth'
GEO='../geo/geopandas/datasets/naturalearth_lowres/naturalearth_lowres'
NAVY=(8,16,34); NAVY2=(14,28,58); RED=(214,24,40); WHITE=(245,245,245); BLUE=(40,110,220)
FD='/usr/share/fonts/opentype/inter/'
def F(w,s): return ImageFont.truetype({'black':FD+'Inter-Black.otf','xb':FD+'Inter-ExtraBold.otf','b':FD+'Inter-Bold.otf','sb':FD+'Inter-SemiBold.otf','m':FD+'Inter-Medium.otf',
  'mono':'/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf'}[w],s)
FONTC={}
def font(w,s):
    k=(w,s)
    if k not in FONTC: FONTC[k]=F(w,s)
    return FONTC[k]
def clamp(x,a=0,b=1): return max(a,min(b,x))
def ss(x): x=clamp(x); return x*x*(3-2*x)
def eo(x): x=clamp(x); return 1-(1-x)**3
def lin(t,a,b): return clamp((t-a)/(b-a)) if b>a else float(t>=a)
def back(x):
    x=clamp(x); c=1.70158; return 1+(c+1)*(x-1)**3+c*(x-1)**2

# ---------------- text sprites ----------------
@lru_cache(maxsize=4000)
def tsprite(text,w,s,fill=WHITE,shadow=True,stroke=0,track=0):
    f=font(w,s); bb=f.getbbox(text,stroke_width=stroke)
    tw=bb[2]-bb[0]+abs(track)*len(text); th=bb[3]-bb[1]; pad=int(s*0.35)+8
    im=Image.new('RGBA',(tw+2*pad,th+2*pad),(0,0,0,0)); d=ImageDraw.Draw(im)
    def draw(dd,col,sw):
        if track==0: dd.text((pad-bb[0],pad-bb[1]),text,font=f,fill=col,stroke_width=sw,stroke_fill=(0,0,0,255) if sw else None)
        else:
            x=pad-bb[0]
            for ch in text:
                dd.text((x,pad-bb[1]),ch,font=f,fill=col,stroke_width=sw,stroke_fill=(0,0,0,255) if sw else None); x+=f.getlength(ch)+track
    if shadow:
        sh=Image.new('RGBA',im.size,(0,0,0,0)); draw(ImageDraw.Draw(sh),(0,0,0,230),stroke+2)
        sh=sh.filter(ImageFilter.GaussianBlur(max(3,s//14)))
        sh2=Image.new('RGBA',im.size,(0,0,0,0)); sh2.paste(sh,(max(2,s//25),max(3,s//18)))
        im=Image.alpha_composite(im,sh2); d=ImageDraw.Draw(im)
    draw(d,tuple(fill)+(255,) if len(fill)==3 else fill,stroke)
    return im
def alpha(sp,a):
    if a>=0.999: return sp
    sp=sp.copy(); A=sp.getchannel('A').point(lambda v:int(v*a)); sp.putalpha(A); return sp
def put(cv,sp,cx,cy,a=1.0,sc=1.0,anchor='mm'):
    if a<=0.003: return
    if abs(sc-1)>0.003:
        sp=sp.resize((max(1,int(sp.width*sc)),max(1,int(sp.height*sc))),Image.BICUBIC)
    sp=alpha(sp,a)
    x=cx-sp.width//2 if anchor[0]=='m' else (cx if anchor[0]=='l' else cx-sp.width)
    y=cy-sp.height//2
    cv.alpha_composite(sp,(int(x),int(y))) if 0<=x and 0<=y and x+sp.width<=W and y+sp.height<=H else paste_clip(cv,sp,int(x),int(y))
def paste_clip(cv,sp,x,y):
    x0,y0=max(0,x),max(0,y); x1,y1=min(W,x+sp.width),min(H,y+sp.height)
    if x1<=x0 or y1<=y0: return
    cv.alpha_composite(sp.crop((x0-x,y0-y,x1-x,y1-y)),(x0,y0))
def text(cv,s,cx,cy,w='black',size=60,fill=WHITE,a=1,sc=1,anchor='mm',shadow=True,track=0):
    put(cv,tsprite(s,w,size,tuple(fill),shadow,0,track),cx,cy,a,sc,anchor)

# ---------------- images ----------------
def load(name): return Image.open(os.path.join(IMG,name)).convert('RGB')
def grade(im,mode):
    a=np.asarray(im).astype(np.float32)/255
    L=(a@np.array([0.299,0.587,0.114],np.float32))[...,None]
    if mode=='cine':
        a=L+(a-L)*0.65; a=np.clip((a-0.5)*1.12+0.47,0,1)
        a=a*np.array([0.88,0.95,1.10],np.float32)+np.array([0,0.01,0.04],np.float32)*(1-a)
    elif mode=='night':
        g=np.clip((L-0.1)*1.45,0,1)**1.5; a=g*np.array([0.30,0.85,0.40],np.float32)*0.72+np.array([0.0,0.02,0.01],np.float32)
    elif mode=='bw':
        a=np.repeat(np.clip((L-0.5)*1.35+0.5,0,1),3,2)
    elif mode=='mel':
        a=L+(a-L)*0.35; a=a*np.array([0.82,0.9,1.08],np.float32)*0.85
    elif mode=='dark':
        a=L+(a-L)*0.55; a=a*np.array([0.8,0.88,1.05],np.float32)*0.8
    return Image.fromarray((np.clip(a,0,1)*255).astype(np.uint8))
def darksky(im,frac=0.5,strength=0.65):
    a=np.asarray(im).astype(np.float32); h=a.shape[0]
    g=np.clip(1-np.arange(h)/(h*frac),0,1)[:,None,None]*strength
    a=a*(1-g)+np.array([4,10,28],np.float32)*g; return Image.fromarray(a.astype(np.uint8))
def prep(im,w,h,extra=1.25):
    s=max(w/im.width,h/im.height)*extra
    if s<1: im=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS)
    return im
class KB:
    def __init__(s,im,w,h,z0=1.0,z1=1.15,c0=(0.5,0.5),c1=(0.5,0.5)):
        s.im=prep(im,w,h,z1*1.05); s.w,s.h=w,h; s.z0,s.z1,s.c0,s.c1=z0,z1,c0,c1
    def params(s,p):
        p=ss(p)*0.85+p*0.15
        sw,sh=s.im.size; base=max(s.w/sw,s.h/sh); z=s.z0+(s.z1-s.z0)*p; k=base*z
        vw,vh=s.w/k,s.h/k
        cx=(s.c0[0]+(s.c1[0]-s.c0[0])*p)*sw; cy=(s.c0[1]+(s.c1[1]-s.c0[1])*p)*sh
        l=clamp(cx-vw/2,0,sw-vw); tp=clamp(cy-vh/2,0,sh-vh); return l,tp,k
    def frame(s,p):
        l,tp,k=s.params(p)
        return s.im.transform((s.w,s.h),Image.AFFINE,(1/k,0,l,0,1/k,tp),Image.BILINEAR)
    def pt(s,p,x,y):  # src fraction -> output px
        l,tp,k=s.params(p); sw,sh=s.im.size; return ((x*sw-l)*k,(y*sh-tp)*k)
def blurbg(im):
    b=ImageOps.fit(im,(W//4,H//4)).filter(ImageFilter.GaussianBlur(6))
    b=ImageEnhance.Brightness(b).enhance(0.35); return b.resize((W,H),Image.BILINEAR)
def rrect_mask(w,h,r):
    m=Image.new('L',(w*2,h*2),0); ImageDraw.Draw(m).rounded_rectangle((0,0,w*2-1,h*2-1),r*2,fill=255); return m.resize((w,h),Image.LANCZOS)

# ---------------- icons (supersampled) ----------------
SSF=3
def icon_canvas(sz): im=Image.new('RGBA',(sz*SSF,sz*SSF),(0,0,0,0)); return im,ImageDraw.Draw(im),sz*SSF
def fin(im,sz): return im.resize((sz,sz),Image.LANCZOS)
@lru_cache(None)
def ic_target(sz=200,col=RED):
    im,d,S=icon_canvas(sz); c=S/2
    for r,cl in [(0.46,col),(0.36,WHITE),(0.26,col),(0.15,WHITE),(0.07,col)]:
        d.ellipse((c-r*S,c-r*S,c+r*S,c+r*S),fill=cl)
    w=int(S*0.025)
    for a in [(c,0.0*S,c,0.2*S),(c,0.8*S,c,S),(0,c,0.2*S,c),(0.8*S,c,S,c)]: d.line(a,fill=WHITE,width=w)
    return fin(im,sz)
@lru_cache(None)
def ic_shield(sz=200,col=BLUE):
    im,d,S=icon_canvas(sz)
    pts=[(0.5,0.05),(0.88,0.18),(0.85,0.55),(0.5,0.95),(0.15,0.55),(0.12,0.18)]
    d.polygon([(x*S,y*S) for x,y in pts],fill=WHITE)
    pts2=[(0.5,0.12),(0.80,0.23),(0.78,0.53),(0.5,0.86),(0.22,0.53),(0.20,0.23)]
    d.polygon([(x*S,y*S) for x,y in pts2],fill=col)
    d.line([(0.33*S,0.48*S),(0.46*S,0.62*S),(0.70*S,0.36*S)],fill=WHITE,width=int(S*0.07),joint='curve')
    return fin(im,sz)
@lru_cache(None)
def ic_eye(sz=200,col=RED):
    im,d,S=icon_canvas(sz)
    up=[(x*S,(0.5-0.32*math.sin(math.pi*x))*S) for x in np.linspace(0.04,0.96,40)]
    lo=[(x*S,(0.5+0.32*math.sin(math.pi*x))*S) for x in np.linspace(0.96,0.04,40)]
    d.polygon(up+lo,fill=WHITE); c=S/2
    d.ellipse((c-0.2*S,c-0.2*S,c+0.2*S,c+0.2*S),fill=col); d.ellipse((c-0.09*S,c-0.09*S,c+0.09*S,c+0.09*S),fill=(10,10,15))
    d.ellipse((c-0.12*S,c-0.14*S,c-0.05*S,c-0.07*S),fill=WHITE)
    return fin(im,sz)
@lru_cache(None)
def ic_pump(sz=220):
    im,d,S=icon_canvas(sz)
    d.rounded_rectangle((0.18*S,0.12*S,0.6*S,0.9*S),int(0.05*S),fill=WHITE)
    d.rectangle((0.12*S,0.86*S,0.66*S,0.94*S),fill=WHITE)
    d.rounded_rectangle((0.25*S,0.2*S,0.53*S,0.42*S),int(0.02*S),fill=NAVY)
    d.line([(0.6*S,0.3*S),(0.75*S,0.36*S),(0.78*S,0.7*S),(0.85*S,0.72*S),(0.86*S,0.3*S),(0.8*S,0.22*S)],fill=WHITE,width=int(0.05*S),joint='curve')
    return fin(im,sz)
@lru_cache(None)
def ic_barrel(sz=220):
    im,d,S=icon_canvas(sz)
    d.rounded_rectangle((0.2*S,0.08*S,0.8*S,0.92*S),int(0.08*S),fill=(30,30,36),outline=WHITE,width=int(0.03*S))
    for y in [0.3,0.7]: d.line([(0.2*S,y*S),(0.8*S,y*S)],fill=WHITE,width=int(0.03*S))
    d.ellipse((0.42*S,0.42*S,0.58*S,0.6*S),fill=RED); d.polygon([(0.5*S,0.36*S),(0.43*S,0.5*S),(0.57*S,0.5*S)],fill=RED)
    return fin(im,sz)
@lru_cache(None)
def ic_ballot(sz=220):
    im,d,S=icon_canvas(sz)
    d.rectangle((0.32*S,0.06*S,0.68*S,0.5*S),fill=WHITE,outline=(150,150,160),width=int(0.01*S))
    d.line([(0.40*S,0.28*S),(0.48*S,0.37*S),(0.61*S,0.17*S)],fill=BLUE,width=int(0.04*S),joint='curve')
    d.rounded_rectangle((0.12*S,0.42*S,0.88*S,0.94*S),int(0.04*S),fill=BLUE,outline=WHITE,width=int(0.03*S))
    d.rectangle((0.3*S,0.42*S,0.7*S,0.47*S),fill=(10,20,40))
    return fin(im,sz)
@lru_cache(None)
def ic_letter(L,sz=120,col=RED):
    im,d,S=icon_canvas(sz)
    d.rounded_rectangle((0,0,S-1,S-1),int(0.2*S),fill=col)
    f=font('black',int(S*0.62)); d.text((S/2,S/2),L,font=f,fill=WHITE,anchor='mm')
    return fin(im,sz)
@lru_cache(None)
def stamp(txt='CLASIFICADO',size=70,rot=-14):
    f=font('black',size); tw=int(f.getlength(txt)); pad=30
    im=Image.new('RGBA',(tw+2*pad,size+2*pad),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.rectangle((6,6,im.width-7,im.height-7),outline=RED+(255,),width=8)
    d.text((im.width/2,im.height/2),txt,font=f,fill=RED+(255,),anchor='mm')
    # distress
    a=np.array(im); m=np.random.default_rng(3).random(a.shape[:2])<0.10; a[m,3]=a[m,3]//4
    return Image.fromarray(a).rotate(rot,expand=True,resample=Image.BICUBIC)

# ---------------- map ----------------
def merc(lon,lat): return math.radians(lon), math.log(math.tan(math.pi/4+math.radians(clamp(lat,-80,80))/2))
class MapR:
    def __init__(s,lon0,lon1,lat0,lat1,wpx):
        s.x0,s.y1=merc(lon0,lat1); s.x1,s.y0=merc(lon1,lat0)
        s.k=wpx/(s.x1-s.x0); s.w=wpx; s.h=int((s.y1-s.y0)*s.k)
    def px(s,lon,lat):
        x,y=merc(lon,lat); return ((x-s.x0)*s.k,(s.y1-y)*s.k)
def build_map(lon0,lon1,lat0,lat1,wpx,hl):
    M=MapR(lon0,lon1,lat0,lat1,wpx); sf=shapefile.Reader(GEO,encoding='latin1')
    f=SSF-1; im=Image.new('RGBA',(M.w*f,M.h*f),(5,10,22,255)); d=ImageDraw.Draw(im)
    for lo in range(-180,181,10):
        a=M.px(lo,lat0); b=M.px(lo,lat1); d.line([(a[0]*f,0),(b[0]*f,M.h*f)],fill=(14,26,48,255),width=2)
    for la in range(-60,81,10):
        a=M.px(lon0,la); d.line([(0,a[1]*f),(M.w*f,a[1]*f)],fill=(14,26,48,255),width=2)
    fields=[x[0] for x in sf.fields[1:]]; ni=fields.index('name')
    for sr in sf.iterShapeRecords():
        nm=sr.record[ni]; pts=sr.shape.points; parts=list(sr.shape.parts)+[len(pts)]
        fill,ol=(18,32,60,255),(48,76,120,255)
        if nm in hl: fill,ol=hl[nm]
        for i in range(len(parts)-1):
            poly=[(M.px(*p)[0]*f,M.px(*p)[1]*f) for p in pts[parts[i]:parts[i+1]]]
            if len(poly)>2: d.polygon(poly,fill=fill,outline=ol,width=3)
    im=im.resize((M.w,M.h),Image.LANCZOS)
    # glow for highlighted
    return M,im
def bez(p0,p1,p2,u): return ((1-u)**2*p0[0]+2*(1-u)*u*p1[0]+u*u*p2[0],(1-u)**2*p0[1]+2*(1-u)*u*p1[1]+u*u*p2[1])

# ---------------- assets ----------------
A={}
def init():
    if A: return
    A['mira']=grade(darksky(load('02_miraflores.jpg'),0.45,0.75),'cine')
    A['mira_kb']=KB(A['mira'],W,int(W*439/784)+40,1.0,1.18,(0.5,0.55),(0.52,0.5))
    A['mira_bg']=blurbg(A['mira'])
    A['mad']=grade(load('05_maduro.jpg'),'bw'); A['mad_kb']=KB(A['mad'],W,760,1.05,1.2,(0.5,0.4),(0.5,0.38))
    A['heg']=KB(grade(load('01_hegseth.jpg'),'cine'),500,640,1.0,1.12,(0.5,0.38),(0.5,0.33))
    A['del']=KB(grade(load('03_delcy.jpg'),'cine'),500,640,1.0,1.12,(0.45,0.36),(0.45,0.31))
    A['heli']=KB(grade(load('06_helicopteros.jpg'),'night'),W,H,1.0,1.12,(0.42,0.5),(0.62,0.48))
    A['heli2']=KB(grade(load('06b_helicoptero.jpg'),'night'),W,H,1.05,1.2,(0.6,0.5),(0.68,0.5))
    A['oil']=KB(grade(load('07_petroleo.jpg'),'cine'),W,H,1.0,1.15,(0.35,0.5),(0.5,0.45))
    A['oil2']=KB(grade(load('07b_petroleo_torre.jpg'),'cine'),W,H,1.0,1.14,(0.5,0.55),(0.5,0.4))
    orm=grade(load('08_ormuz.jpg'),'cine'); A['orm_kb']=KB(orm,W,860,1.0,1.12,(0.55,0.32),(0.55,0.28)); A['orm_bg']=blurbg(orm)
    A['ven']=KB(grade(load('09_venezolanos.jpg'),'mel'),W,H,1.0,1.14,(0.55,0.45),(0.6,0.4))
    A['flag']=KB(grade(load('09b_bandera.jpg'),'mel'),W,H,1.0,1.12,(0.4,0.5),(0.35,0.45))
    hl={'United States of America':((28,70,150,255),(110,170,255,255)),'Venezuela':((170,20,36,255),(255,90,100,255))}
    M,mim=build_map(-128,-40,-12,52,1200,hl); A['M']=M
    A['map_kb']=KB(mim,W,1240,1.0,1.10,(0.55,0.55),(0.6,0.62)); A['map_kb'].im=mim  # keep exact size mapping
    # grain & vignette
    r=np.random.default_rng(1); A['grain']=[(r.standard_normal((H//2,W//2))*7).astype(np.float32) for _ in range(6)]
    yy,xx=np.mgrid[0:H,0:W].astype(np.float32); d=np.sqrt(((xx-W/2)/(W*0.62))**2+((yy-H/2)/(H*0.6))**2)
    A['vig']=(1-np.clip(d-0.45,0,1)**1.6*0.85)[...,None].astype(np.float32)
    A['words']=json.load(open('words.json')); build_subs()
    doc=Image.new('RGB',(900,1200),(222,218,206)); dd=ImageDraw.Draw(doc); rr=np.random.default_rng(5)
    dd.text((70,60),'CONFIDENCIAL',font=font('black',54),fill=(150,20,30))
    dd.text((70,140),'EXPEDIENTE N.º 2026-11-18',font=font('mono',30),fill=(40,40,40))
    dd.line([(70,195),(830,195)],fill=(40,40,40),width=3)
    y=240; A['bars']=[]
    while y<1130:
        ln=rr.integers(380,760); dd.rectangle((70,y,70+ln,y+18),fill=(110,110,110))
        if rr.random()<0.55: A['bars'].append((70-6,y-8,70+min(ln,rr.integers(250,760))+6,y+26))
        y+=46
    A['doc']=doc.filter(ImageFilter.GaussianBlur(2.2))

# ---------------- subtitles ----------------
FIX={'hexit':'Hegseth','hexit,':'Hegseth,','delsi':'Delcy'}
KEY={'maduro','pentágono','sorpresa','nadie','hegseth','pacto','militar','inteligencia','impensable','amenaza','agresiva','socio',
     '150','aeronaves','48','minutos','acuerdo','petróleo','ormuz','irán','gasolina','elecciones','democracia','washington','nueva','otra','comentarios','miraflores','delcy'}
def build_subs():
    ws=[]
    for w in A['words']:
        tx=w['w']; low=tx.lower()
        if low in FIX: tx=FIX[low]
        elif low.rstrip(',.') in FIX: tx=FIX[low.rstrip(',.')]+low[len(low.rstrip(',.')):]
        ws.append(dict(t=tx,s=w['s'],e=w['e']))
    chunks=[]; cur=[]
    for i,w in enumerate(ws):
        cur.append(w); nxt=ws[i+1] if i+1<len(ws) else None
        if w['t'][-1] in ',.?' or len(cur)>=3 or nxt is None or nxt['s']-w['e']>0.35 or len(''.join(x['t'] for x in cur))>16:
            chunks.append(cur); cur=[]
    for k,c in enumerate(chunks):
        nx=chunks[k+1][0]['s'] if k+1<len(chunks) else NAR
        c[0]['cs']=c[0]['s']; c[0]['ce']=min(nx,c[-1]['e']+0.6)
    A['chunks']=chunks
def subtitles(cv,t):
    for c in A['chunks']:
        if c[0]['cs']-0.02<=t<c[0]['ce']: break
    else: return
    size=78; sps=[]
    for w in c:
        disp=w['t'].upper().strip(',.')
        if disp.endswith('?') and False: pass
        bare=w['t'].lower().strip(',.¿?')
        col=RED if bare in KEY else WHITE
        sps.append((tsprite(disp,'black',size,col,True,2),w))
    sp_w=24; pad=int(size*0.35)+8
    widths=[s.width-2*pad for s,_ in sps]
    lines=[[]]; lw=0
    for i,wd in enumerate(widths):
        if lines[-1] and lw+sp_w+wd>980: lines.append([]); lw=0
        lines[-1].append(i); lw+=wd+(sp_w if lw else 0)
    y0=300-(len(lines)-1)*48
    for li,ln in enumerate(lines):
        tw=sum(widths[i] for i in ln)+sp_w*(len(ln)-1); x=(W-tw)/2
        for i in ln:
            sp,w=sps[i]
            if t>=w['s']-0.03:
                p=lin(t,w['s']-0.03,w['s']+0.1); sc=1.25-0.25*eo(p)
                put(cv,sp,x+widths[i]/2,y0+li*96,min(1,p*2.5),sc)
            x+=widths[i]+sp_w

# ---------------- UI pieces ----------------
def lower_third(cv,x,y,w,name,role,p):
    if p<=0: return
    e=eo(p); bw=int(w*e); h=118
    ov=Image.new('RGBA',(w,h),(0,0,0,0)); d=ImageDraw.Draw(ov)
    d.rectangle((0,0,bw,h),fill=NAVY2+(240,)); d.rectangle((0,0,min(bw,8),h),fill=RED+(255,)); d.rectangle((0,h-6,bw,h),fill=RED+(255,))
    cv.alpha_composite(ov,(x,y))
    a=lin(p,0.35,0.8)
    text(cv,name,x+26,y+38,'xb',36,WHITE,a,anchor='lm',shadow=False)
    rf=26 if len(role)<30 else 23
    text(cv,role,x+26,y+82,'sb',rf,(190,200,220),a,anchor='lm',shadow=False)
def card(cv,x,y,w,h,a=1,fill=NAVY2,line=True):
    ov=Image.new('RGBA',(w,h),(0,0,0,0)); d=ImageDraw.Draw(ov)
    d.rounded_rectangle((0,0,w-1,h-1),18,fill=fill+(int(235*a),))
    if line: d.rectangle((0,0,10,h),fill=RED+(int(255*a),))
    cv.alpha_composite(ov,(x,y))
def quote_card(cv,t,t0,lines,src,y=1300,hl_t=None):
    p=lin(t,t0,t0+0.5)
    if p<=0: return
    yy=y+int(60*(1-eo(p))); h=110+len(lines)*72+70
    card(cv,60,yy,960,h,p)
    text(cv,'“',140,yy+40,'black',200,RED,p,shadow=False)
    for i,l in enumerate(lines):
        col=WHITE
        if hl_t is not None and i==len(lines)-1 and t>=hl_t: col=(255,80,90)
        text(cv,l,110,yy+125+i*72,'xb',50,col,lin(t,t0+0.25+i*0.2,t0+0.6+i*0.2),anchor='lm',shadow=False)
    text(cv,src,110,yy+h-48,'sb',28,(170,180,200),lin(t,t0+0.6,t0+1.0),anchor='lm',shadow=False)
def stopwatch(cv,cx,cy,r,frac):
    s=int(r*2+40); im,d,S=icon_canvas(s); c=S/2; R=r*SSF
    d.ellipse((c-R,c-R,c+R,c+R),fill=(10,20,14,220),outline=WHITE,width=int(R*0.08))
    d.rectangle((c-R*0.12,c-R*1.3,c+R*0.12,c-R*1.05),fill=WHITE)
    for k in range(12):
        a=k/12*2*math.pi; d.line([(c+math.sin(a)*R*0.78,c-math.cos(a)*R*0.78),(c+math.sin(a)*R*0.9,c-math.cos(a)*R*0.9)],fill=WHITE,width=int(R*0.04))
    a=frac*2*math.pi; d.pieslice((c-R*0.7,c-R*0.7,c+R*0.7,c+R*0.7),-90,-90+math.degrees(a)+0.01,fill=RED+(140,))
    d.line([(c,c),(c+math.sin(a)*R*0.75,c-math.cos(a)*R*0.75)],fill=RED,width=int(R*0.06))
    put(cv,fin(im,s),cx,cy)

# ---------------- scenes ----------------
def bg_fill(cv,col): cv.paste(col+(255,),(0,0,W,H))
def card_photo(cv,kb,p,cy,bg=None,a=1.0):
    if bg is not None: cv.paste(bg,(0,0))
    fr=kb.frame(p).convert('RGBA')
    if a<1: fr.putalpha(int(255*a))
    cv.alpha_composite(fr,(0,int(cy-kb.h/2)))
    d=ImageDraw.Draw(cv); y0=int(cy-kb.h/2)
    d.rectangle((0,y0,W,y0+3),fill=RED+(255,)); d.rectangle((0,y0+kb.h-3,W,y0+kb.h),fill=RED+(255,))
def full(cv,kb,p): cv.paste(kb.frame(p),(0,0))
def dim(cv,a,col=(0,0,0)):
    if a>0: cv.alpha_composite(Image.new('RGBA',(W,H),col+(int(255*clamp(a)),)))

def s1(cv,t):
    bg_fill(cv,(0,0,0))
    ph=lin(t,1.7,2.6)
    if ph>0:
        card_photo(cv,A['mira_kb'],(t-1.7)/6.7,1080,A['mira_bg'])
        dim(cv,1-ph)
    s='CARACAS · 18 NOV 2026'; n=int(clamp((t-0.25)/0.075,0,len(s)))
    if n>0 or t<1.7:
        typed=s[:n]+('▌' if (t*2.5)%1<0.6 else ' ')
        cy=960 if t<1.7 else 960-int(330*eo(lin(t,1.7,2.5)))
        text(cv,s[:n],W//2-int(font('mono',58).getlength(s)/2),cy,'mono',58,WHITE,anchor='lm')
        if n<len(s) or (t*2.5)%1<0.6:
            cx=W//2-int(font('mono',58).getlength(s)/2)+int(font('mono',58).getlength(s[:n]))+18
            ImageDraw.Draw(cv).rectangle((cx,cy-32,cx+26,cy+30),fill=RED+(255,))
    if t>=2.8 and t<8.4:
        text(cv,'PALACIO DE MIRAFLORES',W//2,1450,'xb',40,(220,225,235),lin(t,2.8,3.3)*(1-lin(t,7.9,8.4)),track=4)
    # Maduro flash
    if 3.78<=t<4.55:
        k=t-3.78
        if k<0.1: dim(cv,0.85-k*4,(200,10,25))
        if 0.06<=k<0.7:
            card_photo(cv,A['mad_kb'],k/0.7,1080,None)
            if k<0.16: dim(cv,0.6,(255,255,255))
            text(cv,'NICOLÁS MADURO',W//2,1530,'black',54,WHITE,1)
            dim(cv,0.18,(150,0,10))
def s2(cv,t):
    bg_fill(cv,(0,0,0))
    if t<8.82:
        card_photo(cv,A['mira_kb'],(t-1.7)/6.7,1080,A['mira_bg']); dim(cv,lin(t,8.4,8.75))
    else:
        p=lin(t,8.82,9.0); j=(np.random.default_rng(int(t*30)).integers(-14,14) if t<9.1 else 0)
        put(cv,stamp('VISITA SORPRESA',96,0),W//2+j,1000,p,1.4-0.4*eo(lin(t,8.82,9.05)))
        d=ImageDraw.Draw(cv); w=int(700*eo(lin(t,8.9,9.4)))
        d.rectangle((W//2-w//2,1130,W//2+w//2,1136),fill=RED+(255,))
def s3(cv,t):
    bg_fill(cv,NAVY); d=ImageDraw.Draw(cv)
    for x in range(0,W,60): d.line([(x,0),(x,H)],fill=(14,24,46,255))
    for y in range(0,H,60): d.line([(0,y),(W,y)],fill=(14,24,46,255))
    text(cv,'EXPEDIENTE · REUNIÓN EN MIRAFLORES',W//2,470,'mono',30,(150,165,195),lin(t,10.1,10.6))
    P=[(30,520,A['heg'],10.1),(550,520,A['del'],10.6)]
    for x,y,kb,t0 in P:
        p=eo(lin(t,t0,t0+0.6))
        if p<=0: continue
        fr=kb.frame((t-10.1)/13.8).convert('RGBA'); fr.putalpha(int(255*p))
        cv.alpha_composite(fr,(x,y+int(40*(1-p))))
        d.rectangle((x-3,y-3+int(40*(1-p)),x+kb.w+2,y+kb.h+2+int(40*(1-p))),outline=RED+(int(255*p),),width=3)
    # red link
    lp=eo(lin(t,11.0,12.0))
    if lp>0:
        y=840; d.line([(530-int(0*lp),y),(530+int(20*lp),y)],fill=RED,width=6)
        d.line([(280,1160),(280,1180),(800,1180),(800,1160)],fill=RED,width=0)
        xa,xb=280,800; xm=xa+(xb-xa)*lp
        d.line([(xa,1180),(xm,1180)],fill=RED,width=6); d.ellipse((xa-10,1170,xa+10,1190),fill=RED)
        if lp>=1: d.ellipse((xb-10,1170,xb+10,1190),fill=RED)
    lower_third(cv,30,1195,500,'Pete Hegseth','Jefe del Pentágono',lin(t,10.24,10.9))
    lower_third(cv,550,1195,500,'Delcy Rodríguez','Presidenta encargada de Venezuela',lin(t,11.82,12.5))
    items=[(17.4,ic_target(170),'ENTRENAMIENTO','CONJUNTO'),(18.8,ic_shield(170),'EQUIPOS DE','DEFENSA'),(22.34,ic_eye(170),'INTELIGENCIA','COMPARTIDA')]
    for i,(t0,ic,l1,l2) in enumerate(items):
        p=lin(t,t0,t0+0.35)
        if p<=0: continue
        cx=180+i*360; cy=1460
        a=1.0
        if i==2 and t>22.9: a=0.35+0.65*(1 if (t*5)%1<0.55 else 0)
        if i==2 and t>22.9:
            o=Image.new('RGBA',(320,330),(0,0,0,0)); ImageDraw.Draw(o).rounded_rectangle((0,0,319,329),20,fill=RED+(int(120*a),)); cv.alpha_composite(o,(cx-160,1350))
        put(cv,ic,cx,cy,p,0.6+0.4*back(p))
        text(cv,l1,cx,1590,'xb',30,WHITE,p); text(cv,l2,cx,1630,'xb',30,WHITE,p)
    if t>=22.92:
        p=lin(t,22.92,23.08); put(cv,stamp('CLASIFICADO',56,-12),900,1480,p,2.0-1.0*eo(p))
def s4(cv,t):
    bg_fill(cv,(5,10,22)); M=A['M']; kb=A['map_kb']; p=(t-23.95)/11.35
    fr=kb.frame(p); cv.paste(fr,(0,400))
    g=Image.new('RGBA',(W,140),(0,0,0,0)); gd=ImageDraw.Draw(g)
    for i in range(140): gd.line([(0,i),(W,i)],fill=(5,10,22,int(255*(1-i/140))))
    cv.alpha_composite(g,(0,400)); cv.alpha_composite(g.transpose(Image.FLIP_TOP_BOTTOM),(0,400+1240-140))
    def P(lon,lat):
        x,y=M.px(lon,lat); x,y=x/M.w,y/M.h; X,Y=kb.pt(p,x,y); return X,Y+400
    d=ImageDraw.Draw(cv)
    wa=P(-77.04,38.9); ca=P(-66.9,10.5)
    for (pt,nm,col,dx) in [(wa,'WASHINGTON',(150,200,255),-1),(ca,'CARACAS',(255,130,140),1)]:
        a=lin(t,24.1,24.6); pul=8+4*math.sin(t*6)
        d.ellipse((pt[0]-pul,pt[1]-pul,pt[0]+pul,pt[1]+pul),fill=col+(int(255*a),))
        text(cv,nm,pt[0]+dx*20,pt[1]+38,'xb',32,col,a,anchor='lm' if dx>0 else 'rm')
    text(cv,'EE. UU.',P(-100,41)[0],P(-100,41)[1],'black',46,WHITE,lin(t,24.0,24.5))
    text(cv,'VENEZUELA',P(-66,5.5)[0]+30,P(-66,5.5)[1]+40,'black',40,WHITE,lin(t,24.3,24.8))
    ap=ss(lin(t,24.7,26.9))
    if ap>0:
        c=( (wa[0]+ca[0])/2+260,(wa[1]+ca[1])/2-60)
        pts=[bez(wa,c,ca,u*ap) for u in np.linspace(0,1,60)]
        ov=Image.new('RGBA',(W,H),(0,0,0,0)); od=ImageDraw.Draw(ov)
        od.line(pts,fill=RED+(90,),width=22,joint='curve'); od.line(pts,fill=RED+(255,),width=9,joint='curve')
        e=pts[-1]; q=pts[-3]; ang=math.atan2(e[1]-q[1],e[0]-q[0])
        hd=[(e[0]+math.cos(ang)*26,e[1]+math.sin(ang)*26),(e[0]+math.cos(ang+2.5)*28,e[1]+math.sin(ang+2.5)*28),(e[0]+math.cos(ang-2.5)*28,e[1]+math.sin(ang-2.5)*28)]
        od.polygon(hd,fill=RED+(255,)); cv.alpha_composite(ov)
    if t>26.8:
        k=lin(t,26.8,27.6); r=20+80*k; d.ellipse((ca[0]-r,ca[1]-r,ca[0]+r,ca[1]+r),outline=RED+(int(255*(1-k)),),width=5)
    quote_card(cv,t,28.4,['De amenaza regional','más agresiva…','a socio de seguridad'],'Fuente: Pete Hegseth, 18 nov 2026',1290,34.0)
def s5(cv,t):
    if t<41.0: full(cv,A['heli'],(t-35.3)/6.2)
    else:
        full(cv,A['heli2'],(t-41)/3.9)
        if t<41.4: 
            o=A['heli'].frame(1).convert('RGBA'); o.putalpha(int(255*(1-lin(t,41,41.4)))); cv.alpha_composite(o)
    # scanlines
    sl=A.setdefault('scan',None)
    if sl is None:
        o=Image.new('RGBA',(W,H),(0,0,0,0)); od=ImageDraw.Draw(o)
        for y in range(0,H,4): od.line([(0,y),(W,y)],fill=(0,0,0,70))
        A['scan']=sl=o
    cv.alpha_composite(sl)
    d=ImageDraw.Draw(cv)
    if (t*2)%1<0.6: d.ellipse((70,470,96,496),fill=RED)
    text(cv,'REC',110,483,'mono',30,WHITE,anchor='lm',shadow=False)
    s='3 ENE 2026 · 2:00 A. M.'; n=int(clamp((t-36.0)/0.06,0,len(s)))
    if n: text(cv,s[:n],W//2,600,'mono',54,(170,255,180),anchor='mm')
    if t>=38.1:
        p=lin(t,38.1,39.5); v=int(150*eo(p)); sc=1.0 if t<41.0 else 1-0.35*eo(lin(t,41,41.5))
        cy=1080 if t<41 else 1080-int(260*eo(lin(t,41,41.5)))
        num=f'{v}+' if p>=1 else f'{v}'
        text(cv,num,W//2,cy,'black',int(230*sc) if sc<1 else 230,WHITE,1)
        text(cv,'AERONAVES',W//2,cy+int(150*sc),'black',int(64*sc),RED,lin(t,38.6,39.1))
    if t>=41.1:
        p=lin(t,41.3,43.9); sec=int(48*60*ss(p)); a=lin(t,41.1,41.4)
        stopwatch(cv,W//2,1300,110,ss(p)) if a>0 else None
        text(cv,f'{sec//60:02d}:{sec%60:02d} MIN',W//2,1510,'mono',84,WHITE if p<1 else (255,80,90),a)
        text(cv,'según Hegseth',W//2,1590,'sb',32,(200,215,200),lin(t,42.0,42.4))
def s6(cv,t):
    bg_fill(cv,(4,7,16)); p=(t-44.85)/6.7
    sc=1.0+0.08*p; doc=A['doc']; dw,dh=int(doc.width*sc*0.95),int(doc.height*sc*0.95)
    im=doc.resize((dw,dh),Image.BILINEAR).rotate(-3+2*p,resample=Image.BILINEAR,expand=True,fillcolor=(4,7,16))
    put(cv,im.convert('RGBA'),W//2,1060)
    # redaction bars, drawn progressively in doc space (approx mapping)
    d=ImageDraw.Draw(cv); bars=A['bars']; k=0.95*sc
    ox=W//2-900*k/2; oy=1060-1200*k/2
    for i,(x0,y0,x1,y1) in enumerate(bars):
        q=lin(t,45.0+i*0.12,45.25+i*0.12)
        if q>0: d.rectangle((ox+x0*k,oy+y0*k,ox+(x0+(x1-x0)*q)*k,oy+y1*k),fill=(5,5,5,255))
    dim(cv,0.25+0.35*lin(t,47.0,47.4))
    if t>=47.2:
        q=lin(t,47.2,47.45); put(cv,tsprite('?','black',520,RED,True),W//2,1000,q,1.5-0.5*eo(q))
        text(cv,'¿QUÉ DICE EL ACUERDO?',W//2,1420,'black',64,WHITE,lin(t,47.4,47.8))
    if t>=49.34:
        q=lin(t,49.34,49.7); w=int(760*eo(q)); d.rectangle((W//2-w//2,1490,W//2+w//2,1580),fill=RED)
        text(cv,'SIN DETALLES OFICIALES',W//2,1535,'black',50,WHITE,lin(t,49.5,49.8),shadow=False)
def s7(cv,t):
    if t<54.6: full(cv,A['oil'],(t-51.55)/3.1)
    elif t<57.3:
        full(cv,A['oil2'],(t-54.6)/2.7)
        if t<55.0: o=A['oil'].frame(1).convert('RGBA'); o.putalpha(int(255*(1-lin(t,54.6,55.0)))); cv.alpha_composite(o)
    if t<57.3:
        if t>=53.48:
            q=lin(t,53.48,53.7); text(cv,'PETRÓLEO',W//2,1450,'black',110,RED,q,1.3-0.3*eo(q),track=6)
            text(cv,'acuerdo petrolero con Venezuela',W//2,1560,'sb',38,WHITE,lin(t,55.5,56.0))
        return
    if t<61.85:
        kb=A['orm_kb']; p=(t-57.3)/4.55; card_photo(cv,kb,p,1000,A['orm_bg'])
        text(cv,'ESTRECHO DE ORMUZ',W//2,1500,'black',56,WHITE,lin(t,57.4,57.9),track=3)
        route=[(0.0,0.42),(0.2,0.33),(0.42,0.2),(0.56,0.12),(0.66,0.2),(0.8,0.38),(1.0,0.6)]
        pts=[kb.pt(p,x,y) for x,y in route]; pts=[(x,y+1000-kb.h/2) for x,y in pts]
        # densify
        dense=[]
        for i in range(len(pts)-1):
            for u in np.linspace(0,1,12,endpoint=False): dense.append((pts[i][0]+(pts[i+1][0]-pts[i][0])*u,pts[i][1]+(pts[i+1][1]-pts[i][1])*u))
        dense.append(pts[-1])
        red=lin(t,58.9,59.5); col=tuple(int(a+(b-a)*red) for a,b in zip((80,170,255),RED))
        ov=Image.new('RGBA',(W,H),(0,0,0,0)); od=ImageDraw.Draw(ov)
        cut=t>=59.5; mid=len(dense)*45//100
        segs=[dense] if not cut else [dense[:mid-4],dense[mid+4:]]
        for sg in segs:
            if len(sg)>1: od.line(sg,fill=col+(90,),width=20,joint='curve'); od.line(sg,fill=col+(255,),width=8,joint='curve')
        if not cut:
            for k in range(3):
                u=((t*0.25+k/3)%1); i=int(u*(len(dense)-1)); x,y=dense[i]; od.ellipse((x-9,y-9,x+9,y+9),fill=WHITE+(255,))
        else:
            x,y=dense[mid]; s=30
            od.line([(x-s,y-s),(x+s,y+s)],fill=RED+(255,),width=12); od.line([(x-s,y+s),(x+s,y-s)],fill=RED+(255,),width=12)
        cv.alpha_composite(ov)
        if t>=60.96:
            q=lin(t,60.96,61.25); cx=W//2; cy=1680
            put(cv,ic_pump(170),cx-70,cy,q,0.6+0.4*back(q))
            ar=Image.new('RGBA',(100,170),(0,0,0,0)); ad=ImageDraw.Draw(ar)
            ad.polygon([(50,0),(100,60),(68,60),(68,170),(32,170),(32,60),(0,60)],fill=RED+(255,))
            put(cv,ar,cx+80,cy-int(25*math.sin(lin(t,61.0,61.85)*math.pi*2)),q)
        return
    # map with new route
    bg_fill(cv,(5,10,22)); M=A['M']; kb=A['map_kb']; p=0.3+(t-61.85)/3.9*0.7
    cv.paste(kb.frame(p),(0,400))
    g=Image.new('RGBA',(W,140),(0,0,0,0)); gd=ImageDraw.Draw(g)
    for i in range(140): gd.line([(0,i),(W,i)],fill=(5,10,22,int(255*(1-i/140))))
    cv.alpha_composite(g,(0,400)); cv.alpha_composite(g.transpose(Image.FLIP_TOP_BOTTOM),(0,400+1240-140))
    def P(lon,lat):
        x,y=M.px(lon,lat); X,Y=kb.pt(p,x/M.w,y/M.h); return X,Y+400
    a=P(-64.7,10.6); b=P(-95.0,29.0); c=((a[0]+b[0])/2+40,(a[1]+b[1])/2+120)
    ap=ss(lin(t,62.0,63.6)); pts=[bez(a,c,b,u*ap) for u in np.linspace(0,1,60)]
    ov=Image.new('RGBA',(W,H),(0,0,0,0)); od=ImageDraw.Draw(ov)
    if ap>0:
        od.line(pts,fill=BLUE+(100,),width=24,joint='curve'); od.line(pts,fill=(90,170,255,255),width=9,joint='curve')
        if ap>=1:
            for k in range(4):
                u=((t*0.35+k/4)%1); x,y=bez(a,c,b,u); od.ellipse((x-10,y-10,x+10,y+10),fill=WHITE+(255,))
    cv.alpha_composite(ov)
    text(cv,'VENEZUELA',a[0]+10,a[1]+50,'black',36,WHITE,lin(t,61.9,62.3))
    text(cv,'EE. UU.',b[0]-20,b[1]-60,'black',40,WHITE,lin(t,61.9,62.3))
    quote_card(cv,t,62.6,['Ormuz, “un factor','irrelevante” para','el hemisferio'],'Fuente: Pete Hegseth',1300)
def calendar(cv,cx,cy,a,t):
    w,h=720,620; o=Image.new('RGBA',(w,h),(0,0,0,0)); d=ImageDraw.Draw(o)
    d.rounded_rectangle((0,0,w-1,h-1),24,fill=(235,235,240,255)); d.rounded_rectangle((0,0,w-1,120),24,fill=RED+(255,)); d.rectangle((0,90,w,120),fill=RED+(255,))
    d.text((w/2,62),'ELECCIONES PRESIDENCIALES',font=font('black',40),fill=WHITE,anchor='mm')
    for r in range(4):
        for c in range(7):
            x=40+c*92; y=150+r*82; d.rounded_rectangle((x,y,x+78,y+68),8,outline=(170,170,180),width=3)
    d.text((w/2,560),'FECHA: —',font=font('black',54),fill=NAVY,anchor='mm')
    for r in range(4):
        for c in range(7):
            x=40+c*92; y=150+r*82
            if (r*7+c)%5==2:
                pass
    # blinking empty slot
    if (t*2)%1<0.6: d.rounded_rectangle((40+3*92-4,150+82-4,40+3*92+82,150+82+72),10,outline=RED,width=6)
    put(cv,o,cx,cy,a)
def balance(cv,cx,cy,t,a):
    tilt=14*ss(lin(t,77.58,78.6))+0  # degrees; negative -> left (petroleum) down
    wob=2.5*math.sin(t*2.1)*(1-lin(t,77.58,78.0))
    ang=math.radians(tilt+wob)
    o=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(o); al=int(255*a)
    d.polygon([(cx-90,cy+330),(cx+90,cy+330),(cx,cy+270)],fill=WHITE+(al,)); d.rectangle((cx-10,cy,cx+10,cy+300),fill=WHITE+(al,))
    L=330; dx,dy=math.cos(ang)*L,-math.sin(ang)*L
    l=(cx-dx,cy-dy); r=(cx+dx,cy+dy)
    d.line([l,r],fill=WHITE+(al,),width=14); d.ellipse((cx-22,cy-22,cx+22,cy+22),fill=RED+(al,))
    for (px,py) in [l,r]:
        d.line([(px,py),(px-90,py+170)],fill=WHITE+(al,),width=4); d.line([(px,py),(px+90,py+170)],fill=WHITE+(al,),width=4)
        d.chord((px-120,py+120,px+120,py+220),0,180,fill=WHITE+(al,))
    cv.alpha_composite(o)
    put(cv,ic_barrel(170),int(l[0]),int(l[1]+90),a); put(cv,ic_ballot(170),int(r[0]),int(r[1]+90),a)
    text(cv,'PETRÓLEO',int(l[0]),int(l[1]+250),'black',40,RED if t>77.58 else WHITE,a)
    text(cv,'DEMOCRACIA',int(r[0]),int(r[1]+250),'black',40,WHITE,a)
def s8(cv,t):
    if t<73.2: full(cv,A['ven'],(t-65.75)/7.45)
    else:
        full(cv,A['flag'],(t-73.2)/6.1)
        if t<73.6: o=A['ven'].frame(1).convert('RGBA'); o.putalpha(int(255*(1-lin(t,73.2,73.6)))); cv.alpha_composite(o)
    dim(cv,0.25)
    if 70.52<=t<73.5:
        p=lin(t,70.52,70.85); calendar(cv,W//2,1060+int(60*(1-eo(p))),p*(1-lin(t,73.1,73.5)),t)
    if t>=73.3:
        dim(cv,0.35*lin(t,73.3,73.7)); balance(cv,W//2,820,t,lin(t,73.4,73.9))
def s9(cv,t):
    bg_fill(cv,NAVY); d=ImageDraw.Draw(cv)
    for i in range(14):
        y=(i*150+t*40)%H; d.line([(0,y),(W,y)],fill=(16,30,62,255),width=2)
    p=lin(t,79.4,79.9)
    text(cv,'ENCUESTA',W//2,560,'mono',40,RED,p,track=8)
    text(cv,'¿Qué crees que significa',W//2,660,'black',60,WHITE,p)
    text(cv,'este pacto?',W//2,740,'black',60,WHITE,p)
    for i,(t0,L,lab,col) in enumerate([(82.14,'A','Una nueva Venezuela',RED),(84.02,'B','Otra cosa',BLUE)]):
        q=eo(lin(t,t0,t0+0.45))
        if q<=0: continue
        y=930+i*200; x=60+int(-300*(1-q))
        o=Image.new('RGBA',(960,160),(0,0,0,0)); od=ImageDraw.Draw(o)
        od.rounded_rectangle((0,0,959,159),26,fill=(22,40,80,int(240*q)),outline=col+(int(255*q),),width=4)
        cv.alpha_composite(o,(x,y)); put(cv,ic_letter(L,110,col),x+90,y+80,q)
        text(cv,lab,x+180,y+80,'xb',52,WHITE,q,anchor='lm',shadow=False)
    if t>=85.26:
        q=lin(t,85.26,85.6); text(cv,'Te leo en los comentarios',W//2,1420,'black',54,WHITE,q)
        b=int(18*abs(math.sin(t*5)))
        ar=Image.new('RGBA',(90,120),(0,0,0,0)); ImageDraw.Draw(ar).polygon([(25,0),(65,0),(65,60),(90,60),(45,120),(0,60),(25,60)],fill=RED+(255,))
        put(cv,ar,W//2,1540+b,q)

SCENES=[(0,8.4,s1),(8.4,10.1,s2),(10.1,23.95,s3),(23.95,35.3,s4),(35.3,44.85,s5),(44.85,51.55,s6),(51.55,65.75,s7),(65.75,79.3,s8),(79.3,NAR+0.1,s9)]
CUTS=[3.78,8.82,10.1,23.95,35.3,44.85,51.55,57.3,61.85,64.84,65.75,79.3]
def glitch(arr,t,seed):
    r=np.random.default_rng(seed); out=arr.copy()
    sh=r.integers(8,26); out[...,0]=np.roll(arr[...,0],sh,1); out[...,2]=np.roll(arr[...,2],-sh,1)
    for _ in range(7):
        y=r.integers(0,H-80); h=r.integers(10,80); out[y:y+h]=np.roll(out[y:y+h],r.integers(-90,90),1)
    return out
def frame(i):
    init(); t=i/FPS
    cv=Image.new('RGBA',(W,H),(0,0,0,255))
    for a,b,f in SCENES:
        if a<=t<b: f(cv,t); break
    subtitles(cv,t)
    arr=np.asarray(cv.convert('RGB')).astype(np.float32)
    for c in CUTS:
        if c<=t<c+0.13: arr=glitch(arr,t,i); break
    g=A['grain'][i%6]; g=np.repeat(np.repeat(g,2,0),2,1)[...,None]
    arr=arr*A['vig']+g
    # subtle flicker
    arr*=1+0.015*math.sin(i*1.7)
    return np.clip(arr,0,255).astype(np.uint8).tobytes()
if __name__=='__main__':
    import multiprocessing as mp
    mode=sys.argv[2]
    if mode=='stills':
        init()
        for ts in sys.argv[3].split(','):
            fi=int(float(ts)*FPS); Image.frombytes('RGB',(W,H),frame(fi)).save(f'st_{float(ts):05.1f}.jpg',quality=85)
    else:
        n=int(TOT*FPS)
        p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
            '-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','main.mp4'],stdin=subprocess.PIPE)
        with mp.Pool(4) as pool:
            for k,b in enumerate(pool.imap(frame,range(n),chunksize=6)):
                p.stdin.write(b)
                if k%300==0: print(k,'/',n,flush=True)
        p.stdin.close(); p.wait(); print('ok')
