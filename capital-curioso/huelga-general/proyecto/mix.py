import numpy as np,subprocess,sys
SR=48000;rng=np.random.default_rng(3)
def load(p,ss=0,t=None):
    cmd=['ffmpeg','-v','error','-ss',str(ss),'-i',p]+(['-t',str(t)] if t else [])+['-ac','2','-ar',str(SR),'-f','f32le','-']
    return np.frombuffer(subprocess.run(cmd,capture_output=True).stdout,np.float32).reshape(-1,2).copy()
TOTAL=69.7;N=int(TOTAL*SR)
voice=load(sys.argv[1]);music=load(sys.argv[2],0,TOTAL)
out=np.zeros((N,2),np.float32)
def place(sig,t,g=1.0):
    if sig.ndim==1:sig=np.stack([sig,sig],1)
    i=int(t*SR);j=min(N,i+len(sig));out[i:j]+=sig[:j-i]*g
def onepole(x,fc):
    fc=np.broadcast_to(fc,x.shape);a=np.exp(-2*np.pi*fc/SR);y=np.zeros_like(x);s=0.0
    for k in range(len(x)):s=(1-a[k])*x[k]+a[k]*s;y[k]=s
    return y
def env(n,att,dec):
    t=np.arange(n)/SR;return np.minimum(1,t/max(att,1e-4))*np.exp(-np.maximum(0,t-att)/dec)
def whoosh(d=.55,lo=250,hi=5000):
    n=int(d*SR);t=np.linspace(0,1,n);fc=lo+(hi-lo)*np.sin(np.pi*t)**2
    x=onepole(rng.standard_normal(n),fc)-onepole(rng.standard_normal(n)*0,fc)
    e=np.sin(np.pi*t)**2;y=x*e;return y/np.abs(y).max()*.6
def boom(d=1.8,f0=95,f1=38):
    n=int(d*SR);t=np.arange(n)/SR;f=f1+(f0-f1)*np.exp(-t*6);ph=2*np.pi*np.cumsum(f)/SR
    y=np.sin(ph)*np.exp(-t*2.2)+onepole(rng.standard_normal(n),900)*np.exp(-t*18)*2
    return y/np.abs(y).max()*.9
def tick(f=2200,d=.03):
    n=int(d*SR);t=np.arange(n)/SR;return np.sin(2*np.pi*f*t)*np.exp(-t*160)*.5
def pop(f0=500,f1=950,d=.09):
    n=int(d*SR);t=np.arange(n)/SR;f=f0+(f1-f0)*t/d;return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*35)*.6
def thud():
    n=int(.7*SR);t=np.arange(n)/SR;y=np.sin(2*np.pi*70*t)*np.exp(-t*9)+onepole(rng.standard_normal(n),1500)*np.exp(-t*30)*3
    return y/np.abs(y).max()*.9
def riser(d=1.0):
    n=int(d*SR);t=np.linspace(0,1,n);f=200+900*t**2;y=np.sin(2*np.pi*np.cumsum(f)/SR)*.25+onepole(rng.standard_normal(n),300+5000*t**2)*.8
    y*=t**1.5*(1-np.clip((t-.95)/.05,0,1));return y/np.abs(y).max()*.45
def ding():
    n=int(1.6*SR);t=np.arange(n)/SR;y=sum(a*np.sin(2*np.pi*f*t) for f,a in [(880,1),(1320,.5),(1760,.25),(2640,.12)])*np.exp(-t*3.2)*np.minimum(1,t/.004)
    return y/np.abs(y).max()*.5
def crackle(d):
    n=int(d*SR);x=np.zeros(n);idx=rng.integers(0,n,int(d*90));x[idx]=rng.standard_normal(len(idx))*rng.random(len(idx))
    y=onepole(x,4000)*6+onepole(rng.standard_normal(n),400)*.25;t=np.linspace(0,1,n);y*=np.minimum(1,t*6)*np.minimum(1,(1-t)*6);return y/np.abs(y).max()*.5
def shutter():
    n=int(.25*SR);t=np.arange(n)/SR;y=onepole(rng.standard_normal(n),3000)*(np.exp(-t*60)+.6*np.exp(-np.maximum(0,t-.07)*60)*(t>.07));return y/np.abs(y).max()*.6
W=whoosh
# ---- SFX timeline ----
place(boom(2.5,70,32),0.0,.5)
place(boom(),0.70,.95)
place(pop(),3.34,.35)
place(boom(2.4,110,30),7.46,1.0)
place(W(.4),8.6,.35)
place(W(.5),9.4,.4)
place(pop(),11.4,.4)
for k in range(14):place(tick(2400),11.5+k*0.07,.25)
place(thud(),15.08,.9)
place(W(.6),15.85,.55);place(crackle(3.4),16.05,.35)
place(W(.6),19.2,.55)
place(riser(2.4),20.95,.3);place(pop(),23.35,.45)
place(riser(1.8),24.5,.25);place(pop(600,1100),26.25,.45);place(tick(1800,.05),25.54,.4)
place(W(.6),27.0,.55)
for tt in (28.0,28.5,28.95,29.4):place(pop(450,900),tt,.4)
place(boom(1.5,120,45),30.88,.8)
place(W(.45),33.85,.45)
place(W(.45),35.72,.45)
for k in range(16):place(tick(2200),35.85+k*0.055,.22)
place(W(.45),38.1,.45);place(thud(),38.25,.45)
for k in range(10):place(tick(2200),38.25+k*0.07,.22)
place(W(.6),39.4,.55);place(boom(1.4,120,45),39.72,.75)
place(shutter(),41.0,.7)
place(W(.6),42.5,.55);place(pop(),42.95,.35)
place(riser(1.0),44.45,.35);place(pop(),45.4,.4)
place(pop(),47.98,.35);place(riser(.8),49.5,.3)
place(W(.6),50.0,.55)
place(riser(1.1),52.2,.3);place(riser(1.1),55.5,.35);place(pop(600,1200),56.15,.45)
place(W(.6),56.45,.55);place(pop(),57.25,.4)
for d in range(12,29):place(tick(1900),57.6+(d-12)/17*1.8,.28)
place(boom(1.4,120,45),59.66,.75)
place(W(.6),60.85,.55);place(pop(),61.94,.35);place(pop(),62.3,.35);place(tick(1500,.06),63.6,.5)
place(pop(700,1300),64.92,.45)
place(W(.7),66.0,.6);place(ding(),67.15,.55)
# ---- music bed with ducking and drop ----
t=np.arange(N)/SR
vr=np.sqrt(np.convolve(np.pad(voice[:,0]**2,(0,max(0,N-len(voice))))[:N],np.ones(4800)/4800,'same'))
act=np.clip(vr/0.03,0,1);act=onepole(act.astype(np.float64),3).astype(np.float32)
g=10**(-14/20)*(1-0.55*act)
g*=np.clip(t/0.6,0,1)
drop=(t>=7.48)&(t<8.75);g[drop]=0
g*=np.where(t>=8.75,np.clip((t-8.75)/1.2,0,1),1)*(t<8.75)+np.where(t>=8.75,np.clip((t-8.75)/1.2,0,1),0) if False else 1
rec=np.clip((t-8.75)/1.2,0,1);g=np.where(t>=8.75,g*rec,g)
g*=np.clip((69.6-t)/3.2,0,1)
m=np.zeros((N,2),np.float32);m[:len(music)]=music[:N];out+=m*g[:,None]
v=np.zeros((N,2),np.float32);v[:min(N,len(voice))]=voice[:N];out+=v
out/=max(1,np.abs(out).max()/0.95)
out.astype(np.float32).tofile('mix.f32')
