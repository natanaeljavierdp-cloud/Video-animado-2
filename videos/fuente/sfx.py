import numpy as np, os, subprocess, json
S = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = 79.5
rng = np.random.default_rng(7)
out = np.zeros((int(SR * DUR) + SR, 2), np.float32)

def env(n, a, d):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
    return e

def lp(x, fc):
    # one-pole low-pass
    a = np.exp(-2 * np.pi * fc / SR); y = np.zeros_like(x); s = 0.0
    for i in range(len(x)):
        s = (1 - a) * x[i] + a * s; y[i] = s
    return y

def bp_fft(x, f1, f2):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < f1) | (f > f2)] = 0
    return np.fft.irfft(X, len(x))

def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR); n = min(len(sig), len(out) - i)
    if sig.ndim == 1:
        l = np.sqrt((1 - pan) / 2); r = np.sqrt((1 + pan) / 2)
        out[i:i + n, 0] += sig[:n] * gain * l * 1.414; out[i:i + n, 1] += sig[:n] * gain * r * 1.414
    else:
        out[i:i + n] += sig[:n] * gain

def norm(x): return x / (np.max(np.abs(x)) + 1e-9)

def key_click():
    n = int(0.035 * SR)
    x = rng.standard_normal(n) * env(n, 0.0005, 0.006)
    x = bp_fft(x, 1800, 9000)
    t = np.arange(n) / SR
    x += 0.4 * np.sin(2 * np.pi * rng.uniform(250, 400) * t) * env(n, 0.0005, 0.008)
    return norm(x)

def impact(big=True):
    n = int((2.2 if big else 1.0) * SR); t = np.arange(n) / SR
    f = 45 + 70 * np.exp(-t * 18)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.55 if big else 0.25)
    nz = bp_fft(rng.standard_normal(n), 60, 3000) * env(n, 0.001, 0.08 if big else 0.04)
    body = bp_fft(rng.standard_normal(n), 100, 900) * env(n, 0.003, 0.35 if big else 0.15)
    x = sub * 1.0 + norm(nz) * 0.5 + norm(body) * 0.35
    return norm(np.tanh(norm(x) * 1.6))

def whoosh(d=0.7, up=True):
    n = int(d * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    # sweep via chunked band-pass
    y = np.zeros(n); seg = 1024
    for k in range(0, n, seg):
        p = k / n; fc = (300 + 4000 * p) if up else (4300 - 4000 * p)
        y[k:k + seg] = bp_fft(x[k:k + seg] if k + seg <= n else x[k:], fc * 0.5, fc * 1.6)[:len(y[k:k + seg])]
    e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return norm(lp(y * e, 6000))

def gavel():
    n = int(0.9 * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for f, a, d in ((620, 1, .05), (1240, .5, .03), (1870, .3, .02), (180, .8, .08)):
        x += a * np.sin(2 * np.pi * f * t) * env(n, 0.0005, d)
    x += 0.6 * bp_fft(rng.standard_normal(n), 800, 6000) * env(n, 0.0002, 0.01)
    x += 0.5 * np.sin(2 * np.pi * 70 * t) * env(n, 0.001, 0.12)
    # room
    rv = np.zeros(n);
    for dl, g in ((0.031, .35), (0.047, .25), (0.073, .18), (0.11, .12)):
        k = int(dl * SR); rv[k:] += x[:-k] * g
    return norm(x + rv)

def ding():
    n = int(1.2 * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for st, f in ((0, 1318.5), (0.11, 1760)):
        k = int(st * SR); tt = t[:n - k]
        x[k:] += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)) * env(n - k, 0.002, 0.25)
    return norm(x)

def pop():
    n = int(0.12 * SR); t = np.arange(n) / SR
    f = 900 * np.exp(-t * 25) + 300
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.03))

def glitch_sfx():
    n = int(0.65 * SR); x = np.zeros(n)
    k = 0
    while k < n:
        L = int(rng.uniform(0.015, 0.06) * SR)
        kind = rng.integers(0, 3)
        tt = np.arange(min(L, n - k)) / SR
        if kind == 0: s = np.sign(np.sin(2 * np.pi * rng.uniform(80, 1200) * tt))
        elif kind == 1: s = rng.standard_normal(len(tt))
        else: s = np.zeros(len(tt))
        x[k:k + len(tt)] = s * rng.uniform(.3, 1)
        k += L
    return norm(x) * 0.8

def riser(d=1.0):
    n = int(d * SR); t = np.arange(n) / SR
    x = bp_fft(rng.standard_normal(n), 2000, 12000) * (t / d) ** 2.5
    tone = np.sin(2 * np.pi * np.cumsum(200 + 600 * (t / d) ** 2) / SR) * (t / d) ** 2 * 0.3
    return norm(x + tone)

def shimmer():
    n = int(2.5 * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for f in (1046.5, 1318.5, 1568, 2093):
        x += np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * env(n, 0.05, 0.9)
    return norm(x)

# --- placement
t = 0.42
while t < 3.25:
    add(key_click(), t, 0.22, rng.uniform(-.3, .3)); t += rng.uniform(0.06, 0.13)
add(glitch_sfx(), 3.55, 0.35)
add(impact(True), 4.33, 0.75)
for tt in (6.0, 13.6, 33.1, 44.5, 60.45, 64.6, 69.3):
    add(whoosh(0.7), tt - 0.35, 0.35)
for tt in (7.6,):
    add(whoosh(0.6, False), tt - 0.1, 0.25)
for tt in (25.56, 26.34, 27.3, 28.12):
    add(pop(), tt, 0.3)
for tt in (29.96, 30.42, 40.2, 41.28, 54.76, 55.32):
    add(impact(False), tt, 0.4)
add(impact(False), 44.56, 0.45)
add(riser(0.9), 58.45, 0.3)
add(impact(True), 59.36, 0.8)
add(gavel(), 60.62, 0.6)
add(gavel(), 68.64, 0.5); add(gavel(), 68.9, 0.35)
add(ding(), 73.12, 0.35)
add(pop(), 74.3, 0.35)
add(riser(1.0), 74.85, 0.25)
add(impact(True), 75.85, 0.45)
add(shimmer(), 76.25, 0.18)
add(shimmer(), 77.3, 0.12)

out = out[:int(SR * DUR)]
out = np.clip(out, -1, 1)
(out * 32767).astype(np.int16).tofile(f"{S}/work/sfx.raw")
print("sfx peak", np.max(np.abs(out)))
