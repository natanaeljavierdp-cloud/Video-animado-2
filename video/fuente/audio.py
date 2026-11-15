import numpy as np, soundfile as sf, sys
from scipy import signal
SR = 48000; DUR = 66.0; N = int(SR * DUR)
rng = np.random.default_rng(7)
out = sys.argv[1]

def t_(d): return np.arange(int(SR * d)) / SR
def add(buf, x, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if x.ndim == 1:
        l, r = x * np.sqrt((1 - pan) / 2) * 1.414, x * np.sqrt((1 + pan) / 2) * 1.414
        x = np.stack([l, r], 1)
    j = min(N, i + len(x)); buf[i:j] += x[: j - i] * gain
def lp(x, f, o=2): return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, f1, f2, o=2): return signal.sosfilt(signal.butter(o, [f1, f2], 'band', fs=SR, output='sos'), x)
def reverb(x, dec=1.8, mix=0.3, seed=1):
    r = np.random.default_rng(seed); L = int(SR * dec)
    ir = r.standard_normal((L, 2)) * np.exp(-np.arange(L) / (SR * dec / 6.9))[:, None]
    ir[:, 0] = lp(ir[:, 0], 6000); ir[:, 1] = lp(ir[:, 1], 6000)
    if x.ndim == 1: x = np.stack([x, x], 1)
    wet = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    wet /= (np.abs(wet).max() + 1e-9) / (np.abs(x).max() + 1e-9)
    return x * (1 - mix) + wet * mix
def mtof(m): return 440 * 2 ** ((m - 69) / 12)

# ================= MUSIC =================
mus = np.zeros((N, 2))
tt = np.arange(N) / SR
# drone D1/D2/A2 with slow movement
dr = 0.5 * np.sin(2 * np.pi * 36.71 * tt) + 0.35 * np.sin(2 * np.pi * 73.42 * tt + 0.3) + 0.18 * np.sin(2 * np.pi * 110 * tt)
dr *= 0.6 + 0.4 * np.sin(2 * np.pi * tt / 9.0) ** 2
mus += np.stack([dr, dr], 1) * 0.22
# pad chords
bar = 60 / 72 * 4
prog = [[50, 57, 62, 65], [46, 53, 58, 62], [43, 50, 55, 58], [45, 52, 57, 61]]  # Dm Bb Gm A
pad = np.zeros(N)
seg = bar * 2
k = 0; t0 = 0.0
while t0 < 58.45:
    ch = prog[k % 4]; d = seg + 1.5
    x = t_(d); s = np.zeros_like(x)
    for m in ch:
        for det in (-0.08, 0.0, 0.07):
            f = mtof(m + det); s += signal.sawtooth(2 * np.pi * f * x + rng.random() * 6) * 0.25
    s = lp(s, 900 + 500 * (k % 2))
    env = np.minimum(1, x / 1.2) * np.minimum(1, (d - x) / 1.5)
    i = int(t0 * SR); j = min(N, i + len(s)); pad[i:j] += (s * env)[: j - i]
    t0 += seg; k += 1
pad /= np.abs(pad).max()
mus += np.stack([pad, np.roll(pad, 600)], 1) * 0.26
# heartbeat pulse (from 5.75 to 58.4), double thump per bar
def thump(f=55, d=0.35):
    x = t_(d); return np.sin(2 * np.pi * (f + 30 * np.exp(-x * 30)) * x) * np.exp(-x * 11)
b = 5.75
while b < 58.2:
    g = 0.5 if b < 30.5 else 0.65
    add(mus, thump(), b, g); add(mus, thump(50), b + 0.28, g * 0.6)
    b += bar / 2
# clock ticks (suspense) eighth notes, soft
def tick():
    x = t_(0.03); return hp(rng.standard_normal(len(x)), 3000) * np.exp(-x * 300)
b = 5.75; i = 0
while b < 58.2:
    add(mus, tick(), b, 0.06 if i % 2 == 0 else 0.035, pan=0.3 if i % 2 else -0.3)
    b += 60 / 72 / 2; i += 1
# piano-ish motif
def pluck(m, d=2.2):
    x = t_(d); f = mtof(m)
    s = sum(a * np.sin(2 * np.pi * f * h * x) for h, a in [(1, 1), (2, .5), (3, .25), (4, .12), (5.02, .06)])
    return s * np.exp(-x * 2.4) * np.minimum(1, x / 0.004)
mot = [74, 77, 81, 76, 74, 77, 82, 81, 72, 77, 79, 74, 73, 76, 81, 79]
b = 13.6; i = 0
pno = np.zeros((N, 2))
while b < 57.5:
    add(pno, pluck(mot[i % 16]), b, 0.16, pan=np.sin(i) * 0.4)
    b += 60 / 72 * 1.5; i += 1
mus += reverb(pno, 2.5, 0.45)
# intro hit
def boom(d=2.5, f=42):
    x = t_(d); s = np.sin(2 * np.pi * (f + 40 * np.exp(-x * 8)) * x) * np.exp(-x * 2.2)
    n = lp(rng.standard_normal(len(x)), 400) * np.exp(-x * 5) * 0.4
    return s + n
add(mus, boom(), 0.0, 0.5)
# global music envelope: duck slightly during speech, fade
env = np.ones(N)
env *= np.clip(tt / 0.4, 0, 1)
mus *= env[:, None]
# ending: resolve to D major shimmer pad
x = t_(8.0); s = np.zeros_like(x)
for m in [50, 57, 62, 66, 69, 74]:
    for det in (-0.06, 0.06): s += signal.sawtooth(2 * np.pi * mtof(m + det) * x) * 0.2
s = lp(s, 1600) * np.minimum(1, x / 0.6) * np.clip((8.0 - x) / 4.5, 0, 1)
add(mus, reverb(s / np.abs(s).max(), 3, 0.5), 58.45, 0.35)
mus = reverb(mus, 1.6, 0.15, seed=3)
mus *= np.clip((66.0 - tt) / 3.0, 0, 1)[:, None]
mus /= np.abs(mus).max()

# ================= SFX =================
fx = np.zeros((N, 2))
def svf_sweep(x, f0, f1, q=2.0):
    n = len(x); fs = np.geomspace(f0, f1, n); y = np.zeros(n); lo = bd = 0.0
    for i in range(n):
        f = 2 * np.sin(np.pi * fs[i] / SR); hi = x[i] - lo - bd / q; bd += f * hi; lo += f * bd; y[i] = bd
    return y
def whoosh(d=0.7, f0=300, f1=4000, peak=0.6):
    x = t_(d); n = rng.standard_normal(len(x))
    env = np.where(x < d * peak, (x / (d * peak)) ** 2, np.exp(-(x - d * peak) * 9))
    y = svf_sweep(n * env, f0, f1, 1.5) + 0.5 * svf_sweep(n * env, f0 * 0.5, f1 * 0.4, 1.2)
    y /= np.abs(y).max()
    pan = np.linspace(-0.8, 0.8, len(x))
    return np.stack([y * np.sqrt((1 - pan) / 2), y * np.sqrt((1 + pan) / 2)], 1) * 1.4
for c in [5.75, 13.6, 30.55, 34.5, 46.45, 55.0]:
    add(fx, whoosh(0.75), c - 0.45, 0.55)
for c in [17.12, 25.58, 32.25, 37.55, 40.85]:
    add(fx, whoosh(0.5, 500, 3000, 0.5), c - 0.2, 0.28)
def gavel():
    x = t_(1.2)
    knock = sum(a * np.sin(2 * np.pi * f * x) * np.exp(-x * dcy) for f, a, dcy in [(190, 1, 28), (410, .7, 35), (980, .45, 55), (1720, .25, 80)])
    click = bp(rng.standard_normal(len(x)), 1200, 5000) * np.exp(-x * 400) * 1.5
    low = np.sin(2 * np.pi * (70 + 60 * np.exp(-x * 25)) * x) * np.exp(-x * 9) * 1.2
    s = (knock + click + low); s /= np.abs(s).max()
    return reverb(s, 1.4, 0.35, seed=5)
add(fx, gavel(), 30.93, 0.95)
add(fx, gavel() * 0.5, 31.12, 0.5)
def stamp():
    x = t_(0.5)
    th = np.sin(2 * np.pi * (110 + 80 * np.exp(-x * 40)) * x) * np.exp(-x * 22)
    cl = hp(rng.standard_normal(len(x)), 2500) * np.exp(-x * 250) * 0.9
    k = bp(rng.standard_normal(len(x)), 300, 1500) * np.exp(-x * 60) * 0.6
    s = th + cl + k; s /= np.abs(s).max(); return reverb(s, 0.8, 0.2, seed=8)
for c in [35.8, 39.77, 47.93]: add(fx, stamp(), c, 0.85)
def glitch(d=0.4, seed=0):
    r = np.random.default_rng(seed); x = t_(d); y = np.zeros(len(x)); i = 0
    while i < len(x):
        L = int(r.integers(400, 2400)); f = r.choice([180, 440, 880, 1320, 2600, 60])
        seg = signal.square(2 * np.pi * f * x[: L]) * (r.random() > 0.3) * r.uniform(.3, 1)
        if r.random() > 0.6: seg = r.standard_normal(L) * 0.7
        y[i:i + L] = seg[: len(y[i:i + L])]; i += L
    y = np.round(y * 4) / 4; return lp(y, 7000) * np.exp(-x * 4)
add(fx, glitch(0.45, 1), 0.04, 0.22); add(fx, glitch(0.4, 2), 4.84, 0.2)
def blip(f=880, d=0.18):
    x = t_(d); return np.sin(2 * np.pi * f * x * (1 + 0.3 * np.exp(-x * 40))) * np.exp(-x * 30)
for i, c in enumerate([9.3, 9.55, 9.8, 10.05]): add(fx, blip(660 + 110 * i), c, 0.3)
add(fx, stamp(), 10.12, 0.4)
for c in [6.35, 6.85, 7.5]: add(fx, blip(1200, 0.08), c, 0.15)
for c in [13.78, 17.22, 25.68]: add(fx, blip(520, 0.25), c + 0.1, 0.3)
for i, c in enumerate([19.96, 21.02, 21.82, 22.86, 24.36]): add(fx, blip(1000 + 90 * i, 0.1), c, 0.16)
add(fx, blip(900, 0.15), 29.1, 0.2)
for c in [49.4, 50.8, 55.3, 57.8]: add(fx, blip(740, 0.2), c + 0.05, 0.25)
# poll tap
add(fx, hp(rng.standard_normal(int(SR * .02)), 2000) * np.exp(-t_(.02) * 300), 56.25, 0.5)
add(fx, blip(1300, 0.12), 56.26, 0.25)
# eraser scrub
x = t_(0.55); er = bp(rng.standard_normal(len(x)), 1500, 6000) * (0.5 + 0.5 * np.sin(2 * np.pi * 14 * x) ** 2) * np.sin(np.pi * x / 0.55)
add(fx, er, 39.18, 0.25)
# strike-through pen scratch
x = t_(0.8); sc = bp(rng.standard_normal(len(x)), 2500, 8000) * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 4 * x))) * np.sin(np.pi * x / 0.8)
add(fx, sc, 38.35, 0.15)
# riser -> logo boom -> shimmer
x = t_(1.3); rs = svf_sweep(rng.standard_normal(len(x)) * (x / 1.3) ** 2, 200, 9000, 2) + 0.3 * np.sin(2 * np.pi * (200 + 600 * (x / 1.3) ** 2) * x) * (x / 1.3) ** 2
add(fx, rs / np.abs(rs).max(), 57.15, 0.35)
add(fx, reverb(boom(3.0, 38), 2.5, 0.3), 58.45, 0.8)
x = t_(2.5); sh = sum(np.sin(2 * np.pi * f * x) * np.exp(-x * (2 + i)) * np.minimum(1, x / 0.01) for i, f in enumerate([2349, 2960, 3520, 4699]))
add(fx, reverb(sh / 4, 2.0, 0.5), 60.65, 0.25)
add(fx, whoosh(0.9, 300, 6000, 0.5), 60.4, 0.25)
fx /= max(1.0, np.abs(fx).max() / 0.95)

sf.write(out + '/music.wav', mus.astype(np.float32), SR)
sf.write(out + '/sfx.wav', fx.astype(np.float32), SR)
print('done')
