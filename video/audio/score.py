"""Banda sonora dramática original (15 s) sincronizada con el motion graphic.

Todo se sintetiza aquí (sin muestras externas): drones, cuerdas, "braams",
tambores graves, risers, whooshes y campanas, colocados en los cortes del video.
Uso:  python3 score.py <salida.wav>
"""
import sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
DUR = 15.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
L = np.zeros(N)
R = np.zeros(N)


def t_(d):
    return np.arange(int(d * SR)) / SR


def hz(note):  # 'D2', 'A#3' ...
    names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    n, o = note[:-1], int(note[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (o + 1) - 69) / 12)


def lp(x, f, order=2):
    return sosfilt(butter(order, min(f, SR / 2 - 100), 'low', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)


def saw(f, d, detune=0.0, vib=0.0):
    """Diente de sierra de banda limitada (aditiva)."""
    t = t_(d)
    ph = 2 * np.pi * f * (1 + detune) * t + vib * np.sin(2 * np.pi * 5.2 * t + rng.random() * 6)
    out = np.zeros_like(t)
    for k in range(1, int(9000 / f) + 1):
        out += np.sin(k * ph + rng.random() * 0.2) / k
    return out * 0.55


def env(d, a, r, curve=2.0):
    t = t_(d)
    e = np.minimum(1, t / max(a, 1e-4))
    rel = np.clip((d - t) / max(r, 1e-4), 0, 1) ** curve
    return e * rel


def put(x, at, pan=0.0, gain=1.0):
    i = int(at * SR)
    if i >= N:
        return
    x = x[: N - i] * gain
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L[i:i + len(x)] += x * gl * 1.41
    R[i:i + len(x)] += x * gr * 1.41


# ---------- instrumentos ----------
def strings(notes, at, d, gain=0.12, cutoff=2400, a=0.8, r=1.2):
    for j, n in enumerate(notes):
        for dt, pan in ((-0.004, -0.6), (0.0, 0.0), (0.005, 0.6)):
            x = lp(saw(hz(n), d, dt, vib=0.0035 * 2 * np.pi * hz(n) / 5.2 / 50), cutoff)
            put(x * env(d, a, r), at, pan, gain / len(notes))


def braam(at, root='D', gain=0.5, d=2.6):
    t = t_(d)
    x = np.zeros_like(t)
    for n, g in ((root + '1', 1.0), (root + '2', 0.8), ('A2' if root == 'D' else root + '3', 0.6)):
        for dt in (-0.006, 0.0, 0.007):
            x += saw(hz(n), d, dt) * g
    # filtro que se abre y se cierra (efecto metal)
    cut = 180 + 2600 * np.exp(-t * 2.2) * np.minimum(1, t / 0.05)
    y = np.zeros_like(x)
    blk = 512
    for s in range(0, len(x), blk):
        y[s:s + blk] = lp(x[s:s + blk + 256], cut[s], 2)[: len(x[s:s + blk])]
    y = np.tanh(y * 1.6) * env(d, 0.02, d * 0.85, 1.5)
    put(y, at, -0.15, gain)
    put(y, at + 0.012, 0.15, gain)


def boom(at, gain=0.9, f0=110, f1=38, d=2.2):
    t = t_(d)
    f = f1 + (f0 - f1) * np.exp(-t * 9)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.1)
    click = bp(rng.standard_normal(len(t)), 80, 900) * np.exp(-t * 45) * 0.6
    put(np.tanh((x + click) * 1.4), at, 0, gain)


def taiko(at, gain=0.55, pan=0.0):
    t = t_(1.2)
    f = 55 + 70 * np.exp(-t * 22)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5.5)
    skin = bp(rng.standard_normal(len(t)), 120, 1800) * np.exp(-t * 30) * 0.45
    put(x + skin, at, pan, gain)


def tick(at, gain=0.12, pan=0.0):
    t = t_(0.18)
    x = hp(rng.standard_normal(len(t)), 3000) * np.exp(-t * 60)
    x += np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 80) * 0.5
    put(x, at, pan, gain)


def riser(at, d, gain=0.25, f0=300, f1=6000):
    t = t_(d)
    k = (t / d) ** 2
    noise = rng.standard_normal(len(t))
    y = np.zeros_like(t)
    blk = 1024
    for s in range(0, len(t), blk):
        fc = f0 + (f1 - f0) * k[s]
        y[s:s + blk] = bp(noise[s:s + blk + 512], fc * 0.6, min(fc * 1.6, SR / 2 - 200))[: len(y[s:s + blk])]
    tone = np.sin(2 * np.pi * np.cumsum(110 + 330 * k) / SR) * 0.35
    out = (y + tone) * (t / d) ** 2.2
    put(out, at, -0.3, gain)
    put(np.roll(out, 300), at, 0.3, gain)


def whoosh(at, d=0.9, gain=0.3, pan_from=-0.8, pan_to=0.8):
    t = t_(d)
    e = np.sin(np.pi * t / d) ** 2
    noise = rng.standard_normal(len(t))
    y = np.zeros_like(t)
    blk = 1024
    for s in range(0, len(t), blk):
        fc = 400 + 3200 * np.sin(np.pi * s / len(t))
        y[s:s + blk] = bp(noise[s:s + blk + 512], fc * 0.5, fc * 1.5)[: len(y[s:s + blk])]
    steps = 8
    for k in range(steps):
        a, b = k * len(t) // steps, (k + 1) * len(t) // steps
        put(y[a:b] * e[a:b], at + a / SR, pan_from + (pan_to - pan_from) * k / (steps - 1), gain)


def bell(note, at, gain=0.12, pan=0.0, d=3.5):
    t = t_(d)
    f = hz(note)
    x = sum(np.sin(2 * np.pi * f * m * t) * a * np.exp(-t * dec) for m, a, dec in
            ((1, 1, 1.4), (2.0, 0.45, 2.2), (2.76, 0.3, 3.0), (5.4, 0.15, 5.0), (8.9, 0.07, 8)))
    put(x * np.minimum(1, t / 0.003), at, pan, gain)


def drone(at, d, gain=0.22):
    t = t_(d)
    x = np.zeros_like(t)
    for n, g in (('D1', 1.0), ('A1', 0.6), ('D2', 0.4)):
        for dt in (-0.003, 0.003):
            x += saw(hz(n), d, dt) * g
    cut = 140 + 500 * (t / d) ** 1.5
    y = lp(x, 900) * 0
    blk = 2048
    for s in range(0, len(x), blk):
        y[s:s + blk] = lp(x[s:s + blk + 512], cut[s])[: len(y[s:s + blk])]
    put(y * env(d, 1.2, 0.5), at, 0, gain)


def shimmer(at, d, gain=0.05):
    t = t_(d)
    x = sum(np.sin(2 * np.pi * hz(n) * t + 3 * np.sin(2 * np.pi * 0.3 * t + i)) for i, n in enumerate(('D6', 'A6', 'E7')))
    put(x * env(d, 1.5, 1.0) * (0.6 + 0.4 * np.sin(2 * np.pi * 3.1 * t)), at, -0.5, gain)
    put(x * env(d, 1.5, 1.0) * (0.6 + 0.4 * np.cos(2 * np.pi * 2.7 * t)), at, 0.5, gain)


# =============================================================
#  Partitura (en re menor) — tiempos en segundos, alineados al video
# =============================================================
# 1 · Origen (0–3.3): drone grave, brillo agudo, pulso de latido
drone(0.0, 3.6, 0.28)
shimmer(0.2, 3.3, 0.035)
for b in (0.9, 1.75, 2.5):
    taiko(b, 0.28)
    taiko(b + 0.22, 0.16)
riser(2.2, 1.12, 0.22)
whoosh(2.75, 0.75, 0.22)

# 2 · Historia (3.33 apertura del rombo): BRAAM + cuerdas
boom(3.33, 0.95)
braam(3.33, 'D', 0.42)
strings(['D3', 'F3', 'A3', 'D4'], 3.4, 1.5, 0.16, 2000, a=0.5, r=0.6)
strings(['A#2', 'F3', 'A#3', 'D4'], 4.85, 1.45, 0.16, 2200, a=0.4, r=0.5)
for k in range(12):  # pulso rítmico en corcheas (~106 bpm)
    tick(3.95 + k * 0.283, 0.09 + 0.03 * (k % 2 == 0), pan=(-0.4 if k % 2 else 0.4))
taiko(4.8, 0.3)

# 3 · Transición de barras (6.15–7.1) y valores (7.05 / 8.05 / 9.1)
riser(5.7, 0.95, 0.18, 400, 4000)
whoosh(6.2, 0.85, 0.32)
for i, (at, chord) in enumerate(((7.0, ['G2', 'D3', 'A#3', 'D4']),
                                 (8.05, ['A#2', 'F3', 'A#3', 'F4']),
                                 (9.1, ['A2', 'E3', 'A3', 'C#4']))):
    boom(at, 0.75 + 0.08 * i, f0=100, f1=42, d=1.4)
    taiko(at, 0.5)
    taiko(at + 0.14, 0.22, pan=0.3)
    strings(chord, at, 1.15, 0.15 + 0.02 * i, 2600 + 600 * i, a=0.15, r=0.5)
    bell(['D5', 'F5', 'A5'][i], at + 0.02, 0.07, pan=(-0.4, 0.0, 0.4)[i], d=2.0)
    for k in range(4):
        tick(at + 0.26 * k + 0.13, 0.08, pan=(-0.3 if k % 2 else 0.3))

# 4 · Portal (9.5–12.6): riser largo, golpe al cruzar el anillo, suspensión
riser(9.6, 1.25, 0.3, 250, 7000)
whoosh(10.55, 1.3, 0.38, -0.9, 0.9)
boom(10.85, 0.6, f0=80, f1=30, d=2.5)
strings(['D3', 'A3', 'E4', 'A4'], 10.85, 2.0, 0.13, 1800, a=0.3, r=0.9)  # Dsus2: suspensión
shimmer(10.9, 2.2, 0.04)
riser(11.95, 1.0, 0.2, 500, 8000)

# 5 · Logo (12.95): impacto final y resolución en re mayor
boom(12.95, 1.0, f0=120, f1=34, d=2.05)
braam(12.95, 'D', 0.32, d=2.05)
strings(['D3', 'F#3', 'A3', 'D4', 'F#4'], 12.95, 2.05, 0.2, 3000, a=0.12, r=1.4)
for i, n in enumerate(('D5', 'F#5', 'A5', 'D6')):
    bell(n, 13.1 + i * 0.16, 0.06, pan=(-0.5 + i * 0.33), d=1.9)
tick(13.95, 0.1)

# ---------- reverberación (IR sintética) y master ----------
ir_t = t_(2.4)
irL = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 2.6)
irR = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 2.6)
irL, irR = lp(irL, 6000), lp(irR, 6000)
irL /= np.sqrt(np.sum(irL ** 2)); irR /= np.sqrt(np.sum(irR ** 2))
wetL = fftconvolve(hp(L, 150), irL)[:N]
wetR = fftconvolve(hp(R, 150), irR)[:N]
outL, outR = L + wetL * 0.32, R + wetR * 0.32

# cola final: desvanecer los últimos 0.45 s junto con la imagen
fade = np.ones(N)
k = int(14.55 * SR)
fade[k:] = np.linspace(1, 0, N - k) ** 1.5
outL, outR = outL * fade, outR * fade

mix = np.stack([outL, outR], 1)
mix = np.tanh(mix / np.max(np.abs(mix)) * 1.2) / np.tanh(1.2) * 0.89  # limitador suave
from scipy.io import wavfile
wavfile.write(sys.argv[1] if len(sys.argv) > 1 else 'score.wav', SR, (mix * 32767).astype(np.int16))
print('ok')
