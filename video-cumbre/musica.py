# Genera una pista de suspenso original (sin derechos de terceros) sincronizada con el video.
# Uso: python3 musica.py  -> audio/musica-suspenso.wav
import numpy as np, wave, os

SR = 44100
DUR = 77.1
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)

def env(a, b, fade_in=1.0, fade_out=1.0):
    """Envolvente 0..1 activa entre a y b con fundidos."""
    e = np.clip((t - a) / max(fade_in, 1e-3), 0, 1) * np.clip((b - t) / max(fade_out, 1e-3), 0, 1)
    return e

def lowpass(x, cutoff):
    # paso bajo suave de 2.º orden aplicado en frecuencia (solo numpy)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (f / cutoff) ** 2), len(x))

def saw(f, detune=0.0):
    ph = (t * f * (1 + detune)) % 1.0
    return 2 * ph - 1

D, F, A, Bb, C = 73.42, 87.31, 110.0, 116.54, 130.81  # D2, F2, A2, Bb2, C3

L = np.zeros(N); R = np.zeros(N)

# 1) Dron grave en Re con LFO lento
drone = (np.sin(2*np.pi*36.71*t) * 0.6 + np.sin(2*np.pi*55.0*t) * 0.3) * (0.8 + 0.2*np.sin(2*np.pi*0.11*t))
drone *= env(0, DUR, 2.5, 2.0)
L += drone * 0.35; R += drone * 0.35

# 2) Colchón de cuerdas (sierras desafinadas filtradas): Rem -> Sib -> Rem -> (tensión) Sib/Do
def pad(freqs, a, b, gain):
    s = sum(saw(f, d) for f in freqs for d in (-0.004, 0.0, 0.005))
    s = lowpass(s, 900) / (len(freqs) * 3)
    e = env(a, b, 2.0, 2.0)
    return s * e * gain
p = pad([D, F, A], 0, 23.6, 0.22) + pad([Bb/2*2, D, F], 23.4, 36.5, 0.22) \
  + pad([D, F, A], 36.3, 50.5, 0.2) + pad([Bb, D*2, F], 50.4, 68.6, 0.18) \
  + pad([C, Bb, D*2, A], 68.4, DUR, 0.24) * np.clip((t - 68.4) / 8.0, 0.4, 1.0)
L += p; R += np.roll(p, int(0.012 * SR))  # leve ensanchamiento estéreo

# 3) Pulso de "latido" a 70 bpm (más intenso al final)
beat = 60 / 70
pulse = np.zeros(N)
klen = int(0.35 * SR); kt = np.arange(klen) / SR
kick = np.sin(2*np.pi*(55*kt + (90-55)*(1-np.exp(-kt*25))/25)) * np.exp(-kt * 9)
for bt in np.arange(1.0, DUR - 0.5, beat):
    for off, g in ((0, 1.0), (0.22, 0.55)):  # doble golpe tipo latido
        i = int((bt + off) * SR)
        if i + klen < N:
            pulse[i:i+klen] += kick * g
pulse *= (0.35 + 0.65 * np.clip((t - 50) / 25, 0, 1)) * env(0.5, DUR, 1.0, 1.5)
L += pulse * 0.45; R += pulse * 0.45

# 4) Tic-tac de reloj (escena de Shenzhen y cierre)
tick = np.zeros(N); tl = int(0.03 * SR); tt = np.arange(tl) / SR
tk = rng.standard_normal(tl) * np.exp(-tt * 300)
tk = np.diff(np.concatenate([[0], tk]))  # brillo
for k, bt in enumerate(np.arange(15.0, DUR - 0.6, 0.5)):
    if 23.4 < bt < 68.5:
        continue
    i = int(bt * SR); tick[i:i+tl] += tk * (1.0 if k % 2 == 0 else 0.7)
L += tick * 0.10; R += tick * 0.08

# 5) Impactos sincronizados con los sellos y momentos clave (con "subida" previa)
hits = [0.0, 7.54, 14.0, 23.45, 36.45, 38.6, 50.6, 62.5, 68.5, 76.4]
hl = int(2.5 * SR); ht = np.arange(hl) / SR
boom = (np.sin(2*np.pi*(40*ht + 60*(1-np.exp(-ht*12))/12)) * np.exp(-ht * 2.2)
        + lowpass(rng.standard_normal(hl), 400) * np.exp(-ht * 5) * 0.8)
rl = int(1.2 * SR); rt = np.arange(rl) / SR
riser = lowpass(rng.standard_normal(rl), 2500) * (rt / rt[-1]) ** 3
for h in hits:
    i = int(h * SR)
    if i + hl <= N:
        L[i:i+hl] += boom * 0.55; R[i:i+hl] += boom * 0.55
    j = i - rl
    if j >= 0:
        L[j:i] += riser * 0.12; R[j:i] += riser * 0.12

# 6) Nota aguda inquietante (tremolo) en las escenas de tensión
hi = np.sin(2*np.pi*587.33*t) * (0.5 + 0.5*np.sin(2*np.pi*6*t)) * (env(31.5, 44.5, 1.5, 1.5) + env(59.5, DUR, 2.0, 1.5))
L += hi * 0.035; R += hi * 0.045

# Fundido final y normalización
fade = np.clip((DUR - t) / 1.2, 0, 1)
L *= fade; R *= fade
m = max(np.abs(L).max(), np.abs(R).max())
L, R = L / m * 0.89, R / m * 0.89

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio', 'musica-suspenso.wav')
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.stack([L, R], 1) * 32767).astype('<i2').tobytes())
print('Listo:', out)
