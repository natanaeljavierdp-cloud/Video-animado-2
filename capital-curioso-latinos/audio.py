"""Banda sonora sintetizada (libre de derechos): música de suspenso suave + efectos.
Genera build/musica.wav y build/sfx.wav (48 kHz, estéreo) sincronizados con scene.html.
Uso: python3 audio.py
"""
import numpy as np, json, subprocess, os
from scipy.signal import butter, sosfilt, sosfiltfilt

SR = 48000
DUR = 63.0          # 58.5 s de escenas + 3.5 s de cierre + 1 s de pausa
CIERRE = 58.5
ROOT = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(ROOT, 'build')
rng = np.random.default_rng(3)
N = int(DUR * SR)
tt = np.arange(N) / SR

def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, a, b, o=2): return sosfilt(butter(o, [a, b], 'band', fs=SR, output='sos'), x)
def nfreq(n): return 440 * 2 ** ((n - 69) / 12)
def place(buf, sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= buf.shape[1]: return
    sig = sig[: buf.shape[1] - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[0, i:i + len(sig)] += sig * gain * l * 1.414
    buf[1, i:i + len(sig)] += sig * gain * r * 1.414

# ------------------------------ MÚSICA ------------------------------
mus = np.zeros((2, N))
# progresión de suspenso (Re menor): (inicio, notas MIDI)
prog = [(0, [38, 50, 53, 57]), (5.0, [34, 46, 53, 58]), (9.45, [41, 48, 53, 57]), (13.0, [33, 45, 52, 57]),
        (16.25, [38, 50, 53, 57]), (21.6, [34, 46, 50, 58]), (27.05, [41, 48, 53, 60]), (32.3, [36, 48, 52, 55]),
        (37.2, [31, 43, 50, 55]), (42.2, [33, 45, 49, 52]), (47.25, [38, 50, 53, 57]), (50.15, [34, 46, 53, 58]),
        (54.2, [33, 45, 52, 57]), (CIERRE, [38, 50, 54, 57])]
pad = np.zeros((2, N))
for k, (a, notes) in enumerate(prog):
    b = prog[k + 1][0] if k + 1 < len(prog) else DUR
    i0, i1 = int(a * SR), int(min(DUR, b + 0.8) * SR)
    seg = tt[i0:i1] - a
    env = np.minimum(1, seg / 0.9) * np.minimum(1, np.maximum(0, (b + 0.8 - a - seg) / 0.8))
    for ch in range(2):
        s = np.zeros(len(seg))
        for j, n in enumerate(notes):
            f = nfreq(n) * (1 + (0.0025 if ch else -0.0025) * (j + 1))
            ph = 2 * np.pi * f * seg + rng.uniform(0, 6)
            saw = sum(np.sin(ph * h) / h for h in range(1, 7))
            s += saw * (1.3 if j == 0 else 0.55)
        pad[ch, i0:i1] += s * env
for ch in range(2):
    pad[ch] = lp(pad[ch], 900, 4)
lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.18 * tt)
mus += pad * lfo * 0.05

# latido grave (90 BPM) desde 5 s; mitad de tiempo en la parte oscura
def kick(f0=58, d=0.45):
    s = np.arange(int(d * SR)) / SR
    f = f0 + 60 * np.exp(-s * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-s * 7)
beat = 60 / 90
t = 5.0
while t < CIERRE - 0.3:
    dark = 37.2 <= t < 47.25
    g = 0.22 if not dark else 0.28
    if not dark or round((t - 5.0) / beat) % 2 == 0:
        place(mus, kick(), t, g)
    t += beat

# ostinato pulsado (corcheas) con eco
ost = np.zeros((2, N))
def pluck(f, d=0.35):
    s = np.arange(int(d * SR)) / SR
    return (np.sin(2 * np.pi * f * s) + 0.3 * np.sin(4 * np.pi * f * s)) * np.exp(-s * 11) * np.minimum(1, s / 0.004)
step = beat / 2
t, k = 9.45, 0
while t < CIERRE - 0.2:
    if not (37.2 <= t < 42.2):
        notes = [n for a, n in prog if a <= t][-1]
        pat = [notes[1] + 12, notes[2] + 12, notes[3] + 12, notes[2] + 12]
        place(ost, pluck(nfreq(pat[k % 4])), t, 0.07 * (1.15 if k % 4 == 0 else 1), pan=0.35 * np.sin(k * 0.7))
    t += step; k += 1
dly = int(beat * 0.75 * SR)
ost[0, dly:] += ost[1, :-dly] * 0.35
ost[1, dly:] += ost[0, :-dly] * 0.35
mus += ost

# textura de cuerdas agudas en tensión (37–47 s)
i0, i1 = int(37.2 * SR), int(47.6 * SR)
seg = tt[i0:i1] - 37.2
tr = np.sin(2 * np.pi * nfreq(74) * seg) * (0.6 + 0.4 * np.sin(2 * np.pi * 6 * seg))
tr *= np.minimum(1, seg / 3) * np.minimum(1, (10.4 - seg) / 0.6).clip(0) * 0.018
mus[:, i0:i1] += tr

# suaviza el final de la música dentro del cierre
fade = np.ones(N); fi = int((CIERRE + 2.0) * SR); fade[fi:] = np.linspace(1, 0, N - fi)
mus *= fade
mus = hp(mus, 35)

# ducking bajo la voz
voz = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(ROOT, 'assets/audio/narracion.mp3'), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True).stdout
voz = np.frombuffer(voz, np.float32)
env = np.zeros(N); env[:len(voz)] = np.abs(voz[:N])
env = sosfiltfilt(butter(1, 3, 'low', fs=SR, output='sos'), env)
env = env / (env.max() + 1e-9)
duck = 1 - 0.45 * np.clip(env * 4, 0, 1)
mus *= duck

# ------------------------------ EFECTOS ------------------------------
sfx = np.zeros((2, N))
def whoosh(d=0.7, f0=300, f1=5000):
    # ruido filtrado con filtro de estado variable cuyo corte sube y baja
    n = int(d * SR); u = np.arange(n) / n
    x = rng.standard_normal(n)
    fc = f0 + (f1 - f0) * np.sin(np.pi * u) ** 2
    F = 2 * np.sin(np.pi * fc / SR); q = 0.6
    out = np.zeros(n); low = band = 0.0
    for i in range(n):
        low += F[i] * band; high = x[i] - low - q * band; band += F[i] * high
        out[i] = band
    return out / (np.abs(out).max() + 1e-9) * np.sin(np.pi * u) ** 2.2
def boom(d=1.6):
    s = np.arange(int(d * SR)) / SR
    f = 42 + 70 * np.exp(-s * 14)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-s * 2.6)
    hit = lp(rng.standard_normal(len(s)), 1800) * np.exp(-s * 35) * 0.6
    return np.tanh((body + hit) * 1.6)
def tick():
    s = np.arange(int(0.03 * SR)) / SR
    return (np.sin(2 * np.pi * 2600 * s) * 0.6 + hp(rng.standard_normal(len(s)), 3000) * 0.5) * np.exp(-s * 260)
def pop(f=520):
    s = np.arange(int(0.18 * SR)) / SR
    f = f * (1 + 1.2 * np.exp(-s * 40))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-s * 22)
def chime():
    s = np.arange(int(3.0 * SR)) / SR
    out = np.zeros(len(s))
    for n, g in [(74, 1), (78, .7), (81, .6), (86, .45)]:
        for h, hg in [(1, 1), (2.76, .35), (5.4, .12)]:
            out += np.sin(2 * np.pi * nfreq(n) * h * s) * g * hg * np.exp(-s * (1.6 + h))
    return out * np.minimum(1, s / 0.004) * 0.35

eOut = lambda k: 1 - (1 - k) ** 3
def ticks(a, b, target, every=1):
    last, lt = -1, -1
    for i in range(int((b - a) * 300) + 1):
        tm = a + i / 300; v = int(round(target * eOut(min(1, (tm - a) / (b - a)))))
        if v // every != last and tm - lt > 0.045:
            place(sfx, tick(), tm, 0.35, pan=0.15); last, lt = v // every, tm

# whoosh en cada transición
for a in [5.0, 9.45, 16.25, 27.05, 37.2, 47.25, 50.15]:
    place(sfx, whoosh(), a - 0.32, 0.55, pan=0)
place(sfx, whoosh(0.9, 200, 3500), CIERRE - 0.45, 0.6)
# golpes graves en las cifras grandes
for t, g in [(0.8, 0.9), (7.45, 0.7), (23.0, 0.7), (33.0, 0.85), (37.4, 0.55), (43.5, 0.8)]:
    place(sfx, boom(), t, g)
# tics de contadores
ticks(6.45, 7.45, 20)
ticks(21.95, 23.0, 50, 2)
ticks(32.3, 33.0, 50, 2)
ticks(42.2, 43.5, 65, 2)
# pops de aparición
for i in range(5): place(sfx, pop(420 + i * 30), 0.05 + i * 0.13, 0.18, pan=(i - 2) * 0.3)
for t, f, g in [(10.3, 600, .3), (17.9, 600, .3), (51.8, 520, .35), (52.55, 440, .35), (55.15, 700, .3), (56.5, 620, .25)]:
    place(sfx, pop(f), t, g)
place(sfx, whoosh(0.45, 600, 6000), 29.3, 0.3, pan=-0.4)   # rótulo
place(sfx, whoosh(0.45, 600, 6000), 47.3, 0.25, pan=-0.5)  # pantalla dividida
place(sfx, whoosh(0.45, 600, 6000), 48.85, 0.25, pan=0.5)
# cierre de marca
place(sfx, chime(), CIERRE + 0.75, 0.9)
place(sfx, boom(1.2), CIERRE + 0.75, 0.35)

def wr(name, x):
    x = x / max(1e-9, np.abs(x).max()) * 0.9
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', os.path.join(B, name)],
                   input=x.T.astype(np.float32).tobytes())
os.makedirs(B, exist_ok=True)
wr('musica.wav', mus); wr('sfx.wav', sfx)
print('ok')
