import numpy as np, wave, sys
SR=48000; rng=np.random.default_rng(7)
def lp(x,fc):  # one-pole lowpass, fc array or scalar
    fc=np.broadcast_to(fc,x.shape); a=np.exp(-2*np.pi*fc/SR); y=np.zeros_like(x); s=0.0
    for i in range(len(x)): s=(1-a[i])*x[i]+a[i]*s; y[i]=s
    return y
def reverb(x,dur=.6,mix=.25):
    n=int(dur*SR); ir=rng.standard_normal(n)*np.exp(-np.linspace(0,7,n)); ir=lp(ir,4000); ir/=np.abs(ir).sum()**.5*8
    w=np.convolve(x,ir)[:len(x)+n]; d=np.concatenate([x,np.zeros(len(w)-len(x))]); return d*(1-mix)+w*mix*3
def whoosh(dur=.75,peak=.45):
    n=int(dur*SR); t=np.linspace(0,1,n); x=rng.standard_normal(n)
    fc=300+2600*np.sin(np.pi*t)**2; y=lp(x,fc)-lp(x,fc*.25)
    env=np.sin(np.pi*t**.8)**2; y*=env; y/=np.abs(y).max(); return y*peak, t
def gavel(peak=.9):
    n=int(.5*SR); t=np.arange(n)/SR; y=np.zeros(n)
    for f,a,d in [(95,1.0,18),(210,.7,30),(480,.45,45),(910,.3,70),(1720,.2,90),(2600,.12,120)]:
        y+=a*np.sin(2*np.pi*f*t)*np.exp(-d*t)
    cl=rng.standard_normal(n)*np.exp(-t*400); y+=lp(cl,6000)*1.2
    y=reverb(y,.7,.3); y/=np.abs(y).max(); return y*peak
def thud(peak=.7):
    n=int(.35*SR); t=np.arange(n)/SR; y=np.sin(2*np.pi*(70+80*np.exp(-t*30))*t)*np.exp(-t*14)
    sl=lp(rng.standard_normal(n),2500)*np.exp(-t*60)*2.5; y=y+sl; y=reverb(y,.35,.15); y/=np.abs(y).max(); return y*peak
def click(peak=.28, f=2400):
    n=int(.09*SR); t=np.arange(n)/SR; y=np.sin(2*np.pi*f*t)*np.exp(-t*90)*.6 + np.sin(2*np.pi*f*1.5*t)*np.exp(-t*140)*.3
    y+=rng.standard_normal(n)*np.exp(-t*900)*.5; y/=np.abs(y).max(); return y*peak
def tick(peak=.12): return click(peak,3200)
def riser(dur=1.0,peak=.18):
    n=int(dur*SR); t=np.linspace(0,1,n); x=rng.standard_normal(n); y=lp(x,200+5000*t**2)*t**2; y/=np.abs(y).max(); return y*peak
L=int(68*SR); out=np.zeros((L,2))
def put(sig,at,pan=0.0,width=0.0):
    i=int(at*SR); s=sig[:max(0,L-i)]
    gl=np.sqrt(.5*(1-pan)); gr=np.sqrt(.5*(1+pan)); out[i:i+len(s),0]+=s*gl*1.4; out[i:i+len(s),1]+=s*gr*1.4
def put_whoosh(at,peak=.4,dur=.75):
    y,t=whoosh(dur,peak); i=int((at-dur*.55)*SR); pan=np.linspace(-.6,.6,len(y))
    if i<0: y=y[-i:]; pan=pan[-i:]; i=0
    out[i:i+len(y),0]+=y*np.sqrt(.5*(1-pan))*1.4; out[i:i+len(y),1]+=y*np.sqrt(.5*(1+pan))*1.4
for T,p in [(0.25,.25),(3.6,.18),(7.55,.42),(25.3,.42),(32.5,.3),(42.2,.42),(49.75,.4),(53.55,.25),(59.5,.4),(63.25,.45)]: put_whoosh(T,p)
put(riser(1.0,.16),5.7)
put(gavel(.95),6.74); put(gavel(.55),37.76)
put(thud(.6),21.26,-.2); put(thud(.6),23.56,.2); put(thud(.45),42.38)
for T in [7.7,10.3,12.46,17.32,18.22,19.02,25.4,26.6,27.88,29.22,29.72,33.0,34.48,35.6,36.52,38.0,38.4,40.2,40.6,45.9,46.75,48.3,49.98,51.08,52.12,54.5,57.84,59.6,60.45,60.75,62.06]:
    put(click(.16),T)
for k in range(10): put(tick(.10),26.74+k*.055)
out=np.clip(out,-1,1)
with wave.open(sys.argv[1],'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out*32767).astype('<i2').tobytes())
# also export single sfx files for the user list
for name,sig in [('whoosh',whoosh(.75,.6)[0]),('mazo',gavel(.9)),('sello',thud(.8)),('clic',click(.6))]:
    with wave.open(sys.argv[1].replace('sfx_track.wav',f'sfx_{name}.wav'),'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(sig,-1,1)*32767).astype('<i2').tobytes())
print('ok')
