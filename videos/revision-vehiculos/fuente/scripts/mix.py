import numpy as np, wave
SR=48000; DUR=67.2; L=int(DUR*SR)
def ld(f): a=np.fromfile(f,dtype='<f4').reshape(-1,2); z=np.zeros((L,2),dtype=np.float32); n=min(L,len(a)); z[:n]=a[:n]; return z
nar=ld('narr.f32'); mus=ld('music.f32')
with wave.open('sfx_track.wav') as w: sfx=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,2).astype(np.float32)/32767
s=np.zeros((L,2),np.float32); s[:min(L,len(sfx))]=sfx[:L]
t=np.arange(L)/SR
def smoothstep(a,b,x): u=np.clip((x-a)/(b-a),0,1); return u*u*(3-2*u)
# music gain envelope (linear)
g=np.full(L,0.27)
g+=0.16*(smoothstep(-.1,.3,t)-smoothstep(2.4,3.4,t))   # hook lift
g+=0.10*(smoothstep(5.6,6.6,t)-smoothstep(7.3,8.2,t))  # prision lift
g+=0.14*(smoothstep(25.0,25.4,t)-smoothstep(26.5,27.6,t)) # pena lift
g+=0.08*(smoothstep(37.4,37.8,t)-smoothstep(38.6,39.6,t))
g*=1-smoothstep(65.4,67.2,t)
g*=smoothstep(0,0.25,t)
# ducking from narration envelope
env=np.abs(nar[:,0]); k=int(.05*SR); env=np.convolve(env,np.ones(k)/k,'same')
duck=1-0.35*smoothstep(0.01,0.06,env)
# smooth duck (attack/release)
dk=int(.15*SR); duck=np.convolve(duck,np.ones(dk)/dk,'same')
mix=nar*1.0 + mus*(g*duck)[:,None] + s*0.8
np.save('mix.npy',mix)
with wave.open('mix.wav','wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix,-1,1)*32767).astype('<i2').tobytes())
print('peak',np.abs(mix).max())
