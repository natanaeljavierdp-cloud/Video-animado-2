# Synthesizes suspense music + SFX and mixes them under narration.mp3 -> build/mix.wav
import numpy as np, soundfile as sf, subprocess, os
SR=44100; DUR=69.6; N=int(SR*DUR)
rng=np.random.default_rng(7)
os.makedirs('build',exist_ok=True)
subprocess.run(['ffmpeg','-v','error','-y','-i','narration.mp3','-ar',str(SR),'-ac','1','build/narr.wav'],check=True)
narr,_=sf.read('build/narr.wav'); voice=np.zeros(N); voice[:min(N,len(narr))]=narr[:N]
t=np.arange(N)/SR
def lp(x,a):  # one-pole lowpass
    from scipy.signal import lfilter
    return lfilter([1-a],[1,-a],x)
def env(n,att,dec):
    e=np.ones(n); a=int(att*SR); 
    if a>0: e[:a]=np.linspace(0,1,a)
    return e*np.exp(-np.arange(n)/SR/dec)
# ---------------- music ----------------
mus=np.zeros(N)
# drone D minor: D1, A1, D2 with detune & slow swell
for f,amp in [(36.71,0.5),(55.0,0.32),(73.42,0.22),(110.0,0.08)]:
    for d in (-0.15,0.15):
        mus+=amp*np.sin(2*np.pi*(f+d)*t+rng.uniform(0,6))
mus*=0.55+0.45*np.sin(2*np.pi*t/9.0)**2
# eerie high pad (minor 2nd cluster) with tremolo
pad=sum(np.sin(2*np.pi*f*t) for f in (587.3,622.3,880.0))*0.05*(0.5+0.5*np.sin(2*np.pi*0.23*t))
mus+=lp(pad,0.6)
# heartbeat pulse every 0.95s ("lub-dub")
beat=np.zeros(N)
def kick(n,f0=55):
    tt=np.arange(n)/SR; f=f0*(1+1.5*np.exp(-tt*30)); return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-tt*9)
k=kick(int(0.35*SR))
for s in np.arange(0.5,DUR-2,0.95):
    for off,g in ((0,1.0),(0.22,0.6)):
        i=int((s+off)*SR); j=min(N,i+len(k)); beat[i:j]+=g*k[:j-i]
mus+=0.9*beat
# ticking clock (hi-hat-ish) in 8ths, quiet
tick=lp(rng.standard_normal(int(0.03*SR)),0.2)*np.exp(-np.arange(int(0.03*SR))/SR/0.006)
for s in np.arange(0.5,DUR-2,0.475):
    i=int(s*SR); mus[i:i+len(tick)]+=0.05*tick[:N-i]
mus/=np.max(np.abs(mus))
# fade in/out, stop dramatic bed under ending logo slightly
mus*=np.clip(t/2.0,0,1)*np.clip((DUR-t)/2.5,0,1)
# ducking under voice (envelope of narration)
ve=lp(np.abs(voice),0.9995); ve/=ve.max()
duck=1-0.45*np.clip(ve*4,0,1)
mus*=duck
# ---------------- sfx ----------------
sfx=np.zeros(N)
def add(sig,at,g=1.0):
    i=int(at*SR); j=min(N,i+len(sig)); 
    if i<N: sfx[i:j]+=g*sig[:j-i]
def whoosh(d=0.6):
    n=int(d*SR); x=rng.standard_normal(n); e=np.sin(np.pi*np.linspace(0,1,n))**2
    # sweep lowpass coefficient
    out=np.zeros(n); y=0
    for i in range(n):
        a=0.98-0.6*(i/n); y=a*y+(1-a)*x[i]; out[i]=y
    return out*e*3
def impact(d=1.6,f0=45):
    n=int(d*SR); tt=np.arange(n)/SR
    boom=np.sin(2*np.pi*np.cumsum(f0*(1+2*np.exp(-tt*20)))/SR)*np.exp(-tt*2.5)
    crack=rng.standard_normal(n)*np.exp(-tt*25)*0.6
    return boom+lp(crack,0.3)
def pop(f=880,d=0.18):
    n=int(d*SR); tt=np.arange(n)/SR; fr=f*(1+0.8*np.exp(-tt*40))
    return np.sin(2*np.pi*np.cumsum(fr)/SR)*np.exp(-tt*22)
def blip(f=1500,d=0.06):
    n=int(d*SR); tt=np.arange(n)/SR; return np.sin(2*np.pi*f*tt)*np.exp(-tt*60)
def thud(d=0.5):
    n=int(d*SR); tt=np.arange(n)/SR
    return np.sin(2*np.pi*70*tt)*np.exp(-tt*14)+lp(rng.standard_normal(n),0.5)*np.exp(-tt*40)*0.8
def riser(d=1.5):
    n=int(d*SR); tt=np.arange(n)/SR; f=200+800*(tt/d)**2
    return (np.sin(2*np.pi*np.cumsum(f)/SR)*0.3+lp(rng.standard_normal(n),0.9)*2)*(tt/d)**2
def chime():
    n=int(2.2*SR); tt=np.arange(n)/SR
    return sum(np.sin(2*np.pi*f*tt)*np.exp(-tt*k) for f,k in ((587.3,2),(880,2.5),(1174.7,3)))*0.4
W=whoosh()
cuts=[5.15,24.12,30.12,36.85,46.35,53.65,59.75,66.45]
for c in cuts: add(W,c-0.3,0.35)
add(whoosh(0.5),18.45,0.3)
add(impact(),16.85,0.9)                 # BUT HE'S NOT THE ONLY ONE
add(impact(1.0,60),0.35,0.45)           # hook title
add(thud(),1.95,0.5); add(thud(),2.25,0.5)  # red X
add(pop(600),3.25,0.4)                  # morph to base
add(pop(700),7.95,0.25); add(whoosh(0.5),9.6,0.25); add(pop(900),10.7,0.35)
add(whoosh(0.4),11.85,0.3)
add(thud(0.6),15.02,0.8)                # stamp
for at in (18.85,19.8,24.2,31.0,37.65,39.8,42.25): add(pop(520,0.15),at,0.25)  # cards
# map pins
for at in (21.5,28.0,32.56,35.35,43.7,53.8,54.0,54.2,54.8):
    add(pop(1100),at+0.4,0.45); add(thud(0.3),at+0.42,0.25)
add(whoosh(0.5),22.4,0.25)              # crossfade to plan
add(pop(800),23.35,0.25)                # Generals' Row
for i in range(14): add(blip(1800),22.2+i*0.085,0.12)  # rent counter
add(pop(700),22.1,0.3); add(pop(700),26.2,0.3)
for i in range(9): add(blip(1200+i*90),46.55+i*0.118,0.35)  # counter 0->8
add(impact(0.8,70),47.5,0.45)
for at in (50.0,50.9,52.25): add(thud(0.5),at,0.6); add(pop(650),at,0.25)
add(riser(1.2),54.9,0.35)
for at in (55.9,56.15,56.4): add(pop(1300,0.12),at,0.25)
add(impact(0.9,50),57.3,0.4)
add(pop(500),60.15,0.35); add(pop(500),61.9,0.35); add(impact(0.9,60),61.5,0.4)
add(chime(),66.6,0.6)
add(pop(900),67.9,0.3)
# ---------------- mix ----------------
def db(x): return 10**(x/20)
mix=voice*db(0)+mus*db(-23)+sfx*db(-14)
mix/=max(1.0,np.max(np.abs(mix))/0.97)
sf.write('build/mix.wav',mix.astype(np.float32),SR)
print('ok',np.max(np.abs(mix)))
