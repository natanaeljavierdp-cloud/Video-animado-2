import numpy as np, subprocess, wave, sys
SR=44100; NAR_DUR=86.752; TOT=NAR_DUR+3.5
N=int(TOT*SR); t=np.arange(N)/SR
rng=np.random.default_rng(7)
def seg(a,b): return slice(int(a*SR),int(b*SR))
def bandnoise(n,lo,hi):
    x=rng.standard_normal(n); X=np.fft.rfft(x); f=np.fft.rfftfreq(n,1/SR)
    X[(f<lo)|(f>hi)]=0; y=np.fft.irfft(X,n); return y/ (np.abs(y).max()+1e-9)
def add(buf,start,sig,g=1.0):
    i=int(start*SR); j=min(N,i+len(sig)); buf[i:j]+=sig[:j-i]*g
# ---------- music ----------
mus=np.zeros(N)
# intensity envelope
inten=np.interp(t,[0,10,24,45,65,79,86.7,TOT],[0.45,0.55,0.65,0.8,0.9,1.0,1.0,0.0])
# heartbeat
def thump(f0=55,dur=0.35):
    tt=np.arange(int(dur*SR))/SR; f=f0*(1+0.6*np.exp(-tt*30))
    ph=2*np.pi*np.cumsum(f)/SR; return np.sin(ph)*np.exp(-tt*14)+0.25*np.sin(2*ph)*np.exp(-tt*22)
hb=np.zeros(N); x=0.4
while x<TOT-1.0:
    bpm=np.interp(x,[0,40,80],[66,80,96])
    add(hb,x,thump(52),1.0); add(hb,x+0.21,thump(46),0.7)
    x+=60/bpm
mus+=hb*0.55
# tense strings (additive saw, detuned)
def saw(f,harm=10,det=0.0):
    y=np.zeros(N); vib=1+0.004*np.sin(2*np.pi*5.2*t+rng.uniform(0,6))
    ph=2*np.pi*np.cumsum(f*(1+det)*vib)/SR
    for k in range(1,harm+1): y+=np.sin(k*ph)/k*(0.92**k)
    return y
low=(saw(73.42)+saw(73.42,det=0.004)+saw(110.0)+saw(146.83,det=-0.003)+saw(174.61))/5
swell=0.6+0.4*np.sin(2*np.pi*t/9.0)**2
mus+=low*0.16*swell*np.interp(t,[0,3,TOT],[0,1,1])
tense=(saw(207.65,8)+saw(155.56,8,0.003))/2   # tritone + minor second tension
mus+=tense*0.10*np.interp(t,[0,20,30,TOT],[0,0,1,1])
trem=0.5+0.5*np.sign(np.sin(2*np.pi*7.5*t))*0.6
hi=(saw(587.33,6)+saw(622.25,6,0.002))/2
mus+=hi*0.05*trem*np.interp(t,[0,44,52,TOT],[0,0,1,1])
mus*=inten
# ---------- sfx ----------
sfx=np.zeros(N)
def boom(dur=2.2):
    tt=np.arange(int(dur*SR))/SR; f=34+110*np.exp(-tt*9); ph=2*np.pi*np.cumsum(f)/SR
    b=np.sin(ph)*np.exp(-tt*2.2); n=bandnoise(len(tt),30,900)*np.exp(-tt*16)*0.6
    return np.tanh((b+n)*1.6)
for bt in [3.78,8.82,22.92,34.18,38.4,47.2,53.48,59.5,70.52,77.58,86.80]: add(sfx,bt,boom(),0.95)
def rotor(dur,fade=1.2,rate=5.6):
    n=int(dur*SR); tt=np.arange(n)/SR; base=bandnoise(n,40,320)
    mod=(0.35+0.65*np.abs(np.sin(np.pi*rate*tt))**6); env=np.minimum(1,np.minimum(tt/fade,(dur-tt)/fade))
    return base*mod*env
add(sfx,0.0,rotor(8.4,1.5),0.55); add(sfx,35.3,rotor(9.6,1.0,6.0),0.75)
def radio(dur):
    n=int(dur*SR); tt=np.arange(n)/SR; st=bandnoise(n,500,3200)
    crack=(rng.random(n)<0.0015).astype(float); crack=np.convolve(crack,np.exp(-np.arange(200)/30),'same')
    beep=np.sin(2*np.pi*1250*tt)*((tt<0.12)|((tt>dur-0.15)&(tt<dur-0.05)))*0.5
    env=np.minimum(1,np.minimum(tt/0.05,(dur-tt)/0.1))
    return (st*0.35*(0.6+0.4*np.sin(2*np.pi*3*tt))+crack*0.8+beep)*env
for a,d in [(10.1,1.6),(24.0,1.0),(35.3,1.3),(57.3,1.0)]: add(sfx,a,radio(d),0.45)
def glitch(dur=0.22):
    n=int(dur*SR); y=np.zeros(n); i=0
    while i<n:
        L=int(rng.uniform(0.008,0.03)*SR); kind=rng.integers(3)
        if kind==0: y[i:i+L]=rng.uniform(-1,1)
        elif kind==1: y[i:i+L]=np.sign(np.sin(2*np.pi*rng.uniform(200,2500)*np.arange(len(y[i:i+L]))/SR))
        else: y[i:i+L]=rng.standard_normal(len(y[i:i+L]))*0.7
        i+=L
    return y*0.5
for gt in [3.76,8.40,10.10,23.95,35.30,44.85,51.55,57.30,61.85,64.84,65.75,79.30,86.75]: add(sfx,gt,glitch(),0.35)
def click():
    n=int(0.05*SR); tt=np.arange(n)/SR
    return (bandnoise(n,1500,7000)*np.exp(-tt*120)+0.4*np.sin(2*np.pi*2400*tt)*np.exp(-tt*200))
TW1=[(0.25+i*0.075) for i in range(len("CARACAS · 18 NOV 2026"))]
TW2=[(36.0+i*0.06) for i in range(len("3 ENE 2026 · 2:00 A. M."))]
for c in TW1+TW2: add(sfx,c,click(),0.5*rng.uniform(0.7,1))
# carriage bell after line
add(sfx,TW1[-1]+0.1,np.sin(2*np.pi*2100*np.arange(int(0.4*SR))/SR)*np.exp(-np.arange(int(0.4*SR))/SR*9),0.15)
# ---------- silences before key phrases ----------
gate=np.ones(N)
for k in [8.82,22.34,47.2,53.1,70.52,79.46]:
    a,b=k-0.5,k
    i,j=int(a*SR),int(b*SR); gate[i:j]=0
    r=int(0.04*SR); gate[i-r:i]=np.linspace(1,0,r)
    gate[j:j+r]=np.minimum(gate[j:j+r],np.linspace(0,1,r))
# booms at gate end should pass: they start at j => gate ramps 0->1 over 40ms, fine
bus=(mus*0.22+sfx*0.30)*gate
# narration
raw=subprocess.run(["ffmpeg","-v","error","-i",sys.argv[1],"-ac","1","-ar",str(SR),"-f","f32le","-"],capture_output=True).stdout
nar=np.frombuffer(raw,dtype=np.float32).astype(float)
outm=bus.copy(); outm[:len(nar)]+=nar[:N]*1.0
outm/=max(1.0,np.abs(outm).max()/0.95)
st=np.stack([outm,outm],1)
with wave.open("mix.wav","wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st*32767).astype(np.int16).tobytes())
print("done",TOT)
