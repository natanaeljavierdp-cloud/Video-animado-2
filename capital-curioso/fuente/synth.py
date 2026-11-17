import numpy as np, wave
SR=44100; T=69.1; N=int(SR*T); rng=np.random.default_rng(7)
def wr(name,x):
    x=np.clip(x,-1,1); s=(x*32767).astype(np.int16)
    if s.ndim==1: s=np.stack([s,s],1)
    w=wave.open(name,'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(s.tobytes()); w.close()
def lp(x,a): # one-pole lowpass, a in (0,1)
    from scipy.signal import lfilter
    return lfilter([a],[1,a-1],x)
def bp(x,lo,hi):
    from scipy.signal import butter,sosfilt
    return sosfilt(butter(2,[lo,hi],'band',fs=SR,output='sos'),x)
def env(n,a,d): t=np.arange(n)/SR; return np.minimum(1,t/max(a,1e-4))*np.exp(-t/d)
t=np.arange(N)/SR
# ---------- MUSIC ----------
mus=np.zeros((N,2))
bpm=96; beat=60/bpm
# drone pad: A1 + E2 + A2 + C3 detuned, slow filter
freqs=[55,82.41,110,130.81,164.81]
pad=np.zeros(N)
for i,f in enumerate(freqs):
    for d in (-0.15,0.15):
        pad+=np.sign(np.sin(2*np.pi*(f+d)*t))*0.5+np.sin(2*np.pi*(f+d)*t)
from scipy.signal import butter,sosfilt
lfo=600+400*np.sin(2*np.pi*t/9)
# approximate moving filter by blending two filtered versions
p1=sosfilt(butter(2,250,'low',fs=SR,output='sos'),pad); p2=sosfilt(butter(2,1100,'low',fs=SR,output='sos'),pad)
k=(lfo-200)/800; pad=p1*(1-k)+p2*k
pad*=0.035
# chord shift every 8 beats: alternate Am / F (shift by multiplying? simpler: add second pad layer on F)
# sub pulse
sub=np.zeros(N)
for b in np.arange(0,T,beat):
    i=int(b*SR); n=int(0.5*SR)
    if i+n>N: break
    tt=np.arange(n)/SR; f=55*np.exp(-tt*3)+40
    sub[i:i+n]+=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-tt*7)*0.5
# ticks 8ths (clock), accent
tick=np.zeros(N); hn=int(0.03*SR)
for j,b in enumerate(np.arange(0,T,beat/2)):
    i=int(b*SR)
    if i+hn>N: break
    tick[i:i+hn]+=bp(rng.standard_normal(hn),5000,12000)*np.exp(-np.arange(hn)/SR/0.006)*(0.5 if j%2 else 0.25)
# arp pluck (tech) quiet: A minor pentatonic pattern on 16ths, starting at 12s
arp=np.zeros(N); notes=[220,261.63,329.63,392,440,392,329.63,261.63]; an=int(0.18*SR)
for j,b in enumerate(np.arange(12.3,T-3.5,beat/2)):
    i=int(b*SR); f=notes[j%8]*(0.5 if (j//16)%2 else 1)
    tt=np.arange(an)/SR; arp[i:i+an]+=np.sin(2*np.pi*f*tt)*np.sin(2*np.pi*2*f*tt)*np.exp(-tt/0.05)*0.12
music=pad+sub*0.35+tick*0.25+arp
# intensity curve: softer in hook, swell, drop at end
fade=np.clip(t/0.5,0,1)*np.clip((T-t)/3.0,0,1)
music*=fade
mus[:,0]=music; mus[:,1]=np.roll(music,int(0.012*SR))
mus/=np.max(np.abs(mus)); wr('music.wav',mus*0.9)
# ---------- SFX ----------
fx=np.zeros((N,2))
def add(x,at,g=1.0,pan=0):
    i=int(at*SR); x=x[:max(0,N-i)]
    fx[i:i+len(x),0]+=x*g*(1-max(0,pan)); fx[i:i+len(x),1]+=x*g*(1+min(0,pan))
def glitch(d=0.28,seed=0):
    r=np.random.default_rng(seed); n=int(d*SR); x=np.zeros(n); i=0
    while i<n:
        L=int(r.uniform(0.008,0.05)*SR); kind=r.integers(3); tt=np.arange(L)/SR
        if kind==0: s=np.sign(np.sin(2*np.pi*r.uniform(80,1600)*tt))
        elif kind==1: s=r.standard_normal(L)
        else: s=np.round(np.sin(2*np.pi*r.uniform(200,900)*tt)*3)/3
        s*=r.uniform(.3,1)*(r.random()>.2); x[i:i+L]=s[:n-i]; i+=L
    x=np.round(x*8)/8
    return x*np.linspace(1,.3,n)*0.5
def powerdown(d=1.1):
    n=int(d*SR); tt=np.arange(n)/SR; f=180*np.exp(-tt*3)+25
    hum=np.sin(2*np.pi*np.cumsum(f)/SR)+0.5*np.sign(np.sin(2*np.pi*np.cumsum(f*2)/SR))
    thump=np.sin(2*np.pi*np.cumsum(70*np.exp(-tt*20)+30)/SR)*np.exp(-tt*9)
    zap=bp(rng.standard_normal(n),2000,8000)*np.exp(-tt*25)
    return (hum*0.35*np.exp(-tt*2.2)+thump*0.9+zap*0.6)*0.6
def whoosh(d=0.6):
    n=int(d*SR); tt=np.arange(n)/SR; e=np.sin(np.pi*tt/d)**2
    x=rng.standard_normal(n); lo=bp(x,300,1500); hi=bp(x,1500,6000)
    k=tt/d; return (lo*(1-k)+hi*k)*e*0.8
def impact(d=1.8):
    n=int(d*SR); tt=np.arange(n)/SR
    b=np.sin(2*np.pi*np.cumsum(90*np.exp(-tt*6)+35)/SR)*np.exp(-tt*2.5)
    nz=lp(rng.standard_normal(n),0.05)*np.exp(-tt*4)
    return (b*0.9+nz*1.5)*0.8
def typing(d,seed=1):
    r=np.random.default_rng(seed); n=int(d*SR); x=np.zeros(n); tm=0
    while tm<d-0.05:
        i=int(tm*SR); L=int(0.025*SR); c=bp(r.standard_normal(L),1500,7000)*np.exp(-np.arange(L)/SR/0.004)
        c+=np.sin(2*np.pi*r.uniform(300,500)*np.arange(L)/SR)*np.exp(-np.arange(L)/SR/0.006)*0.4
        x[i:i+L]+=c*r.uniform(.5,1); tm+=r.uniform(0.06,0.13)
    return x*0.7
def alert(f1=880,f2=660):
    out=[]
    for f in (f1,f2):
        n=int(0.16*SR); tt=np.arange(n)/SR; out.append((np.sin(2*np.pi*f*tt)+0.3*np.sin(2*np.pi*2*f*tt))*np.minimum(1,tt/0.005)*np.exp(-tt*8)); out.append(np.zeros(int(0.03*SR)))
    return np.concatenate(out)*0.45
def flap():
    L=int(0.12*SR); x=np.zeros(L)
    for k in range(4):
        i=int(k*0.025*SR); m=int(0.012*SR); x[i:i+m]+=bp(rng.standard_normal(m),1000,5000)*np.exp(-np.arange(m)/SR/0.003)
    return x*0.6
def chime():
    n=int(1.2*SR); tt=np.arange(n)/SR
    return sum(np.sin(2*np.pi*f*tt)*np.exp(-tt*a) for f,a in ((880,3),(1318.5,4),(1760,5)))*0.18
def click():
    n=int(0.08*SR); tt=np.arange(n)/SR; return (bp(rng.standard_normal(n),800,4000)*np.exp(-tt*120)+np.sin(2*np.pi*150*tt)*np.exp(-tt*60))*0.7
for a in (1.02,3.48,7.12): add(powerdown(),a,0.9); add(glitch(0.35,int(a*10)),a,0.7)
for i,c in enumerate((12.3,22.6,27.0,30.2,34.4,40.05,42.0,46.0,54.0,57.6,62.1)): add(glitch(0.3,100+i),c-0.15,0.55)
for i,c in enumerate((36.68,37.36,38.42,39.22)): add(glitch(0.18,200+i),c-0.08,0.35)
add(glitch(0.25,300),16.1,0.5); add(glitch(0.25,301),16.35,0.5); add(glitch(0.35,302),56.2,0.6)
for a in (10.0,30.36,56.55): add(impact(),a,0.9)
for a in (12.2,22.5,26.9,30.05,32.0,34.3,45.9,51.0,53.9,57.5,62.0): add(whoosh(),a,0.55)
add(typing(1.6,1),19.3,0.5); add(typing(2.0,2),47.6,0.35)
for a in (34.8,40.5,41.3): add(alert(),a,0.6)
add(alert(520,390),26.35,0.5)
for i in range(8): add(flap(),27.35+i*0.26,0.6)
add(click(),52.45,0.9); add(chime(),52.5,0.7)
wr('sfx.wav',fx/ max(1,np.max(np.abs(fx)))*0.95)
print('ok',np.max(np.abs(fx)))
