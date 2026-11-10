# Efectos de sonido sintetizados (100% originales, sin derechos de terceros).
import numpy as np, soundfile as sf, os
SR = 44100; out = "public/sfx"; os.makedirs(out, exist_ok=True)
rng = np.random.default_rng(7)
def env(n, a, d):  # attack/decay exponencial
    t = np.arange(n)/SR; e = np.minimum(t/a, 1) * np.exp(-np.maximum(t-a, 0)/d); return e
def lowpass(x, k):
    y = np.zeros_like(x); acc = 0.0
    for i, v in enumerate(x): acc += k*(v-acc); y[i] = acc
    return y
def save(name, x, g=0.9):
    x = x/np.max(np.abs(x))*g; sf.write(f"{out}/{name}.wav", np.stack([x, x], 1).astype(np.float32), SR)
# whoosh: ruido filtrado con barrido
n = int(SR*0.6); t = np.arange(n)/SR; noise = rng.standard_normal(n)
k = 0.02 + 0.25*np.sin(np.pi*t/0.6)**2; y = np.zeros(n); acc = 0
for i in range(n): acc += k[i]*(noise[i]-acc); y[i] = acc
save("whoosh", y*np.sin(np.pi*t/0.6)**1.5, 0.7)
# impacto (boom grave + click)
n = int(SR*1.2); t = np.arange(n)/SR
f = 38 + 90*np.exp(-t*18); boom = np.sin(2*np.pi*np.cumsum(f)/SR)*env(n, 0.003, 0.35)
click = lowpass(rng.standard_normal(n), 0.3)*env(n, 0.0005, 0.02)
save("impacto", boom + 0.5*click)
# clic de candado (dos clics metálicos)
def clk(n, f): t = np.arange(n)/SR; return (np.sin(2*np.pi*f*t)+0.6*np.sin(2*np.pi*f*2.7*t))*env(n, 0.0005, 0.012) + 0.4*rng.standard_normal(n)*env(n, 0.0002, 0.004)
n = int(SR*0.35); y = np.zeros(n); y[:2000] += clk(2000, 2400)*0.6; y[int(SR*0.07):int(SR*0.07)+4000] += clk(4000, 1800)
save("clic", y, 0.8)
# sello (golpe seco)
n = int(SR*0.6); t = np.arange(n)/SR
thud = np.sin(2*np.pi*(70+60*np.exp(-t*30))*t)*env(n, 0.002, 0.12) + 0.6*lowpass(rng.standard_normal(n), 0.15)*env(n, 0.001, 0.05)
save("sello", thud)
# moneda
n = int(SR*0.5); t = np.arange(n)/SR
coin = sum(a*np.sin(2*np.pi*f*t)*np.exp(-t*d) for f, a, d in [(2637, 1, 9), (3951, .6, 12), (5274, .35, 16), (1318, .3, 7)])
save("moneda", coin*env(n, 0.001, 1), 0.6)
# ding de confirmación
n = int(SR*0.7); t = np.arange(n)/SR
ding = np.sin(2*np.pi*1046*t)*np.exp(-t*6)*(t < .7) + np.where(t > .09, np.sin(2*np.pi*1568*(t-.09))*np.exp(-(t-.09)*6), 0)
save("ding", ding, 0.5)
# tic (contador)
n = int(SR*0.04); save("tic", np.sin(2*np.pi*3200*np.arange(n)/SR)*env(n, 0.0003, 0.006), 0.4)
# riser (tensión antes de la encuesta)
n = int(SR*1.5); t = np.arange(n)/SR
riser = sum(np.sin(2*np.pi*(f*(1+t))*t) for f in (220, 330, 440))*(t/1.5)**2 + 0.3*rng.standard_normal(n)*(t/1.5)**3
save("riser", riser, 0.5)
print(os.listdir(out))
