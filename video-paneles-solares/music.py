import numpy as np, wave, sys
sr=44100; dur=float(open(sys.argv[1]).read())+0.5; n=int(sr*dur); t=np.arange(n)/sr
bpm=100; beat=60/bpm; bar=4*beat
def f(m): return 440*2**((m-69)/12)
chords=[[60,64,67],[67,71,74],[69,72,76],[65,69,72]]  # C G Am F
bass=[48,43,45,41]
out=np.zeros(n)
# pads
for i in range(int(dur/bar)+1):
    c=chords[i%4]; s0=int(i*bar*sr); s1=min(n,int((i+1)*bar*sr)+int(0.3*sr))
    if s0>=n: break
    tt=np.arange(s1-s0)/sr; env=np.minimum(1,tt/0.6)*np.minimum(1,(bar+0.3-tt)/0.5).clip(0)
    for m in c:
        for d in (-0.08,0.08): out[s0:s1]+=0.05*np.sin(2*np.pi*f(m)*(1+d/100)*tt)*env
    out[s0:s1]+=0.10*np.sin(2*np.pi*f(bass[i%4])*tt)*env
    # arpeggio plucks (8ths)
    arp=[c[0]+12,c[1]+12,c[2]+12,c[1]+12]
    for k in range(8):
        a0=s0+int(k*beat/2*sr); a1=min(n,a0+int(0.6*sr))
        if a0>=n: break
        ta=np.arange(a1-a0)/sr; m=arp[k%4]
        out[a0:a1]+=0.06*(np.sin(2*np.pi*f(m)*ta)+0.3*np.sin(4*np.pi*f(m)*ta))*np.exp(-ta*6)
fade=np.minimum(1,t/1.5)*np.minimum(1,(dur-0.5-t)/2.5).clip(0)
out*=fade; out/=np.abs(out).max()
w=wave.open('music.wav','w'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
w.writeframes((out*0.9*32767).astype(np.int16).tobytes()); w.close()
