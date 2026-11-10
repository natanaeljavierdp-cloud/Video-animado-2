"""Genera música de fondo de tensión/noticias + efectos de sonido (100 % sintetizados, sin derechos de autor).

Uso:  python3 musica.py salida/sfx.json salida/
Salida: salida/musica.wav (solo música), salida/efectos.wav (solo efectos), salida/musica_y_efectos.wav (mezcla)
Duración: 63.5 s (60 s de noticia + 3.5 s del cierre de Capital Curioso).
"""
import json
import sys
import wave

import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
DUR = 63.5
N = int(SR * DUR)
BPM = 100
BEAT = 60 / BPM
rng = np.random.default_rng(7)


def t_axis(d):
    return np.arange(int(SR * d)) / SR


def lp(x, f, order=2):
    return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)


def env(n, a, r, sus=None):
    """envolvente ataque/decaimiento exponencial"""
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / r)
    return e


def add(buf, sig, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    if i < 0:
        sig, i = sig[-i:], 0
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


def saw(f, d, detune=0.0):
    t = t_axis(d)
    out = np.zeros_like(t)
    for dt in (-detune, 0, detune):
        ph = (t * f * (1 + dt)) % 1
        out += 2 * ph - 1
    return out / 3


def reverb(x, secs=2.2, mix=0.25):
    ir_t = t_axis(secs)
    ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.2)
    ir = lp(ir, 6000)
    ir /= np.sqrt(np.sum(ir ** 2))
    wet = fftconvolve(x, ir)[: len(x)]
    return x * (1 - mix) + wet * mix


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


# ------------------------------------------------------------------ MÚSICA
music = np.zeros(N)
END = 60.0  # la noticia termina aquí; después entra el cierre de marca

# progresión en Re menor: Dm  Bb  Gm  A  (2 compases cada uno)
prog = [(50, [62, 65, 69]), (46, [62, 65, 70]), (43, [62, 67, 70]), (45, [61, 64, 69])]
bar = 4 * BEAT
chord_len = 2 * bar

# pad de cuerdas oscuro
t = 0.0
i = 0
while t < END:
    root, notes = prog[i % 4]
    d = chord_len + 0.6
    sig = sum(saw(midi(n), d, 0.004) for n in notes) / 3
    sig = lp(sig, 1400)
    e = np.minimum(1, t_axis(d) / 0.8) * np.minimum(1, (d - t_axis(d)) / 0.6)
    add(music, sig * e * 0.16, t)
    # drone grave
    dr = (np.sin(2 * np.pi * midi(root - 12) * t_axis(d)) + 0.4 * np.sin(2 * np.pi * midi(root) * t_axis(d)))
    add(music, dr * e * 0.20, t)
    t += chord_len
    i += 1

# bajo pulsante en corcheas (tensión), arranca tras el golpe inicial
t = 0.4
k = 0
while t < END - 0.3:
    root, _ = prog[int(t // chord_len) % 4]
    d = BEAT / 2
    s = saw(midi(root - 12), d, 0.003)
    s = lp(s, 380 + 250 * (k % 2 == 0))
    add(music, s * env(len(s), 0.004, 0.09) * (0.34 if k % 2 == 0 else 0.24), t)
    t += BEAT / 2
    k += 1

# reloj / tic-tac de noticiero en semicorcheas
t = 0.4
k = 0
while t < END - 0.3:
    n = int(SR * 0.03)
    tick = hp(rng.standard_normal(n), 6000) * env(n, 0.0005, 0.008)
    add(music, tick * (0.10 if k % 4 == 0 else 0.045), t)
    t += BEAT / 4
    k += 1

# bombo suave en negras + acento en cada compás
t = 0.4
k = 0
while t < END - 0.3:
    d = 0.35
    tt = t_axis(d)
    f = 50 + 70 * np.exp(-tt * 30)
    kick = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9)
    add(music, kick * (0.45 if k % 4 == 0 else 0.22), t)
    t += BEAT
    k += 1

# arpegio agudo tipo "sintetizador de noticias" (a partir de 8 s)
t = 8.0
k = 0
while t < 53.0:
    root, notes = prog[int(t // chord_len) % 4]
    n = notes[[0, 1, 2, 1][k % 4]] + 12
    d = BEAT / 2
    s = np.sign(np.sin(2 * np.pi * midi(n) * t_axis(d))) * 0.5 + np.sin(2 * np.pi * midi(n) * t_axis(d)) * 0.5
    s = lp(s, 2500)
    add(music, s * env(len(s), 0.003, 0.12) * 0.05, t)
    t += BEAT / 2
    k += 1

music = reverb(music, 2.0, 0.22)

# respiración: baja durante la "gran pregunta" y sube en la encuesta
gain = np.ones(N)
tt = np.arange(N) / SR
gain *= np.interp(tt, [0, 46.3, 46.8, 53.3, 53.8, 59.4, 60.0, DUR], [1, 1, .65, .65, 1, 1, 0, 0])
music *= gain

# cola del cierre: acorde final que sostiene el logo
d = DUR - 59.9
fin = sum(np.sin(2 * np.pi * midi(n) * t_axis(d)) for n in (50, 57, 62, 65)) / 4
fin = lp(fin + 0.3 * sum(saw(midi(n), d, 0.003) for n in (62, 69)) / 2, 1800)
fin *= np.minimum(1, t_axis(d) / 0.05) * np.exp(-t_axis(d) * 0.9)
fin_r = reverb(np.concatenate([fin, np.zeros(int(SR * 0.1))]), 2.5, 0.4)
add(music, fin_r * 0.35, 59.95)

# ------------------------------------------------------------------ EFECTOS
fx = np.zeros(N)


def boom(gainv=1.0, d=2.5):
    tt = t_axis(d)
    f = 38 + 90 * np.exp(-tt * 18)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.2)
    noise = lp(rng.standard_normal(len(tt)), 900) * np.exp(-tt * 10) * 0.6
    return reverb(s + noise, 2.2, 0.3) * gainv


def whoosh(d=0.55, up=False):
    tt = t_axis(d)
    nz = rng.standard_normal(len(tt))
    out = np.zeros_like(nz)
    # barrido de filtro por bloques
    blocks = 24
    L = len(nz) // blocks
    for b in range(blocks):
        p = b / blocks
        fc = 300 + 5000 * (p if up else np.sin(np.pi * p))
        seg = nz[b * L:(b + 1) * L]
        out[b * L:(b + 1) * L] = bp(seg, max(80, fc * .5), min(18000, fc * 1.6))
    e = np.sin(np.pi * np.clip(tt / d, 0, 1)) ** 2
    return out * e


def pop():
    tt = t_axis(0.15)
    f = 900 + 600 * np.exp(-tt * 40)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(tt), 0.002, 0.04)


def click():
    n = int(SR * 0.025)
    return bp(rng.standard_normal(n), 1500, 7000) * env(n, 0.0005, 0.006)


def sting():
    d = 2.6
    tt = t_axis(d)
    s = sum(saw(midi(n), d, 0.005) for n in (38, 50, 57, 62, 65)) / 5
    s = lp(s, 2600) * np.exp(-tt * 1.4) * np.minimum(1, tt / 0.01)
    return reverb(s, 2.4, 0.35)


for c in json.load(open(sys.argv[1])):
    t0, ty = c['t'], c['type']
    if ty == 'sting':
        add(fx, sting() * 0.55, t0)
    elif ty == 'impact':
        add(fx, boom(0.9), t0)
    elif ty == 'impact_small':
        add(fx, boom(0.45, 1.5), t0)
    elif ty == 'whoosh':
        add(fx, whoosh() * 0.30, t0 - 0.1)
    elif ty == 'swoosh_up':
        add(fx, whoosh(0.35, True) * 0.20, t0)
    elif ty == 'pop':
        add(fx, pop() * 0.30, t0)
    elif ty == 'stamp':
        add(fx, boom(0.75, 1.2), t0)
        n = int(SR * .08)
        add(fx, lp(rng.standard_normal(n), 2500) * env(n, .001, .02) * 0.6, t0)
    elif ty == 'counter':
        # tics que se van espaciando (como un contador que frena)
        d = c.get('dur', 3.0)
        x = 0.0
        while x < d:
            add(fx, click() * 0.25, t0 + x)
            x += 0.035 + 0.22 * (x / d) ** 2
        add(fx, pop() * 0.35, t0 + d)
    elif ty == 'typing':
        d = c.get('dur', 3.0)
        x = 0.0
        while x < d:
            add(fx, click() * (0.18 + 0.1 * rng.random()), t0 + x)
            x += 0.06 + 0.05 * rng.random()


def norm_peak(x, peak):
    m = np.max(np.abs(x))
    return x / m * peak if m > 0 else x


def soft(x):
    return np.tanh(x * 1.2) / np.tanh(1.2)


def write(path, x):
    st = np.stack([x, x], axis=1)
    pcm = (np.clip(st, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


outdir = sys.argv[2].rstrip('/')
music = norm_peak(music, 0.55)
fx = norm_peak(fx, 0.75)
write(f'{outdir}/musica.wav', soft(music))
write(f'{outdir}/efectos.wav', soft(fx))
write(f'{outdir}/musica_y_efectos.wav', soft(music * 0.8 + fx * 0.7))
print('ok')
