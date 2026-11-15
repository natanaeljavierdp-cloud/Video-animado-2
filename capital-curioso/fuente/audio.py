import numpy as np, wave
SR=44100; T=90.6; N=int(SR*T); rng=np.random.default_rng(7)
t=np.arange(N)/SR
def env(n,a,d): x=np.arange(n)/SR; return np.minimum(1,x/a)*np.exp(-x/d)
def lp(x,k=0.05):
    y=np.zeros_like(x); acc=0
    from scipy.signal import lfilter
    return lfilter([k],[1,k-1],x)
# ---- música de suspenso ----
m=np.zeros(N)
for f,a in [(55,.5),(82.4,.28),(110,.18),(58.3,.12)]:  # dron con disonancia leve
    m+=a*np.sin(2*np.pi*f*t+0.3*np.sin(2*np.pi*.07*t))
m*=0.6+0.4*np.sin(2*np.pi*.05*t)**2
pad=sum(np.sin(2*np.pi*f*t) for f in (440,466.2,659.3))*(0.5+0.5*np.sin(2*np.pi*.11*t))*.05
m+=pad
# latido grave cada 0.92 s
bt=np.arange(0.4,T,0.92)
for b in bt:
    for off,amp in ((0,1),(0.22,.6)):
        i=int((b+off)*SR); n=int(.35*SR); 
        if i+n<N: x=np.arange(n)/SR; m[i:i+n]+=amp*.7*np.sin(2*np.pi*(48+30*np.exp(-x*25))*x)*np.exp(-x*12)
# tic de reloj
tk=lp(rng.standard_normal(int(.03*SR)),.5)*env(int(.03*SR),.001,.006)
for b in np.arange(0.4,T,0.46):
    i=int(b*SR); m[i:i+len(tk)]+=.25*tk
fade=np.minimum(1,t/1.0)*np.minimum(1,(T-t)/1.5)
m*=fade; m=m/np.abs(m).max()
# ---- efectos ----
fx=np.zeros(N)
def add(at,s,g=1):
    i=int(at*SR); n=min(len(s),N-i); fx[i:i+n]+=g*s[:n]
def stamp():
    n=int(.5*SR); x=np.arange(n)/SR
    return .9*np.sin(2*np.pi*(70+90*np.exp(-x*30))*x)*np.exp(-x*14)+.6*lp(rng.standard_normal(n),.3)*np.exp(-x*40)
def metal():
    n=int(2.2*SR); x=np.arange(n)/SR; s=np.zeros(n)
    for r,a,d in ((1,1,1.2),(2.76,.6,.8),(5.4,.4,.5),(8.93,.3,.3),(13.3,.2,.2)): s+=a*np.sin(2*np.pi*190*r*x+rng.random()*6)*np.exp(-x/d)
    return .5*s+.8*rng.standard_normal(n)*np.exp(-x*60)+.8*np.sin(2*np.pi*60*x)*np.exp(-x*8)
def notif():
    s=np.zeros(int(.6*SR))
    for at,f in ((0,988),(.12,1319)):
        n=int(.45*SR); x=np.arange(n)/SR; i=int(at*SR); s[i:i+n]+=(np.sin(2*np.pi*f*x)+.3*np.sin(2*np.pi*2*f*x))*np.minimum(1,x/.004)*np.exp(-x*9)
    return .5*s
def whoosh():
    n=int(.5*SR); x=np.arange(n)/SR; e=np.sin(np.pi*x/.5)**2
    return .35*lp(rng.standard_normal(n),.15)*e
def tick(): n=int(.08*SR); x=np.arange(n)/SR; return .5*np.sin(2*np.pi*1800*x)*np.exp(-x*80)
def riser(d=1.2):
    n=int(d*SR); x=np.arange(n)/SR; s=rng.standard_normal(n); return .25*(.4*lp(s,.08)+.6*lp(s,.4)*(x/d))*(x/d)**2
for b in [5.56,12.6,17.95,28.9,32.3,42.4,57.0,70.4,77.3,86.0]: add(b-.25,whoosh())
add(3.62,metal(),1.0); add(3.62,stamp(),.6)
add(17.04,stamp(),1.1)
for at in (20.84,22.78,24.4,26.1): add(at,stamp(),.45)
add(36.34,notif()); add(45.24,notif(),.7)
add(42.44,metal(),.9)
for k in range(24): add(60.82+.9*(1-(1-k/24)**(1/3))*1,tick(),.5)
add(61.72,stamp(),.9)
add(76.1,metal(),.5); add(76.1,stamp(),.6)
add(83.94,notif(),.8); add(85.04,notif(),.8)
add(84.8,riser(1.2)); add(86.95,stamp(),.6); add(87.6,notif(),.6)
fx=fx/np.abs(fx).max()
def w(name,x):
    x=np.clip(x,-1,1); f=wave.open(name,'wb'); f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes((x*32000).astype(np.int16).tobytes()); f.close()
w('music.wav',m); w('sfx.wav',fx)
