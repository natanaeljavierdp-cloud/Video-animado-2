import numpy as np, subprocess, os
from scipy import signal
SR = 44100
DUR = 66.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")

def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()

def tt(n): return np.arange(n) / SR

def place(buf, x, t0, g=1.0):
    i = int(t0 * SR)
    if i < 0: x = x[-i:]; i = 0
    n = min(len(x), len(buf) - i)
    if n > 0: buf[i:i + n] += x[:n] * g

def env_adsr(n, a, r):
    e = np.ones(n); na = max(1, int(a * SR)); nr = max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr); return e

def reverb(x, secs=1.8, mix=0.3):
    n = int(secs * SR); ir = rng.normal(0, 1, n) * np.exp(-tt(n) * 5 / secs)
    ir = signal.lfilter([1], [1, -0.6], ir); ir /= np.abs(ir).sum() ** 0.5 * 4
    wet = signal.fftconvolve(x, ir)[:len(x)]
    return x * (1 - mix) + wet * mix * 3

def lp(x, f, order=2): b, a = signal.butter(order, f / (SR / 2)); return signal.lfilter(b, a, x)
def hp(x, f, order=2): b, a = signal.butter(order, f / (SR / 2), 'high'); return signal.lfilter(b, a, x)
def bp(x, f1, f2): b, a = signal.butter(2, [f1 / (SR / 2), f2 / (SR / 2)], 'band'); return signal.lfilter(b, a, x)

def saw(f, n, harm=14, detune=(0, -0.11, 0.09)):
    t = tt(n); out = np.zeros(n)
    for d in detune:
        ff = f * 2 ** (d / 12); ph = rng.uniform(0, 6.28)
        for k in range(1, harm + 1):
            if ff * k > 9000: break
            out += np.sin(2 * np.pi * ff * k * t + ph * k) / k
    return out / len(detune)

def note(m): return 440 * 2 ** ((m - 69) / 12)

# ---------------- MUSIC ----------------
mus = np.zeros(N)
EPIC = 38.9
# Suspense drone 0 - EPIC
n = int((EPIC + 1.0) * SR); t = tt(n)
drone = saw(note(38), n, 8) * 0.5 + saw(note(45), n, 8) * 0.3 + np.sin(2 * np.pi * note(26) * t) * 0.6
drone = lp(drone, 700) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.13 * t))
cres = np.clip(t / 3, 0, 1) * (0.55 + 0.45 * np.clip(t / EPIC, 0, 1)) * (1 - np.clip((t - EPIC) / 0.6, 0, 1))
place(mus, drone * cres * 0.5, 0)
# high eerie tremolo strings
hi = (saw(note(74), n, 6) + saw(note(77), n, 6) * .6) * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * t))
hi = bp(hi, 500, 4000) * np.clip((t - 8) / 6, 0, 1) * (1 - np.clip((t - EPIC) / 0.5, 0, 1))
place(mus, hi * 0.07, 0)
# pulse / heartbeat at 100bpm
beat = 60 / 100
def kick(f0=90, f1=40, d=0.5, g=1.0):
    k = int(d * SR); tk = tt(k); f = f1 + (f0 - f1) * np.exp(-tk * 25)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tk * 7) * g
def tick():
    k = int(0.03 * SR); return hp(rng.normal(0, 1, k), 3000) * np.exp(-tt(k) * 200)
x = 0.0
while x < EPIC - 0.3:
    g = 0.35 + 0.65 * x / EPIC
    place(mus, kick() * 0.55 * g, x); place(mus, kick() * 0.3 * g, x + 0.22)
    place(mus, tick() * 0.12 * g, x + beat / 2)
    x += beat * 2
# riser into epic
rn = int(2.2 * SR); rt = tt(rn)
riser = bp(rng.normal(0, 1, rn), 300, 6000) * (rt / rt[-1]) ** 2
sweep = np.sin(2 * np.pi * np.cumsum(200 + 900 * (rt / rt[-1]) ** 2) / SR) * (rt / rt[-1]) ** 2 * 0.3
place(mus, (riser * 0.35 + sweep) * 0.8, EPIC - 2.2)
# Epic section
bpm = 96; b = 60 / bpm; bar = 4 * b
prog = [[50, 53, 57, 62], [46, 50, 53, 58], [41, 45, 48, 53], [48, 52, 55, 60]]  # Dm Bb F C
end = 63.0
k = 0; x = EPIC
while x < end:
    ch = prog[k % 4]; nn = int(bar * 2 * SR) + int(0.6 * SR)
    pad = sum(saw(note(m), nn, 12) for m in ch) / 4
    pad += saw(note(ch[0] - 12), nn, 10) * 0.7
    intensity = 0.6 + 0.4 * min(1, (x - EPIC) / 14)
    pad = lp(pad, 1200 + 2500 * min(1, (x - EPIC) / 15)) * env_adsr(nn, 0.25, 0.6) * intensity
    if x + bar * 2 > end: pad[int((end - x) * SR):] *= 0
    place(mus, pad * 0.55, x)
    # brass stab at chord change
    sn = int(0.9 * SR); st = tt(sn)
    stab = lp(sum(saw(note(m + 12), sn, 10) for m in ch[:3]), 2200) * np.exp(-st * 3) * env_adsr(sn, 0.02, 0.2)
    place(mus, stab * 0.22 * intensity, x)
    # taiko pattern over 2 bars
    for bb in range(8):
        tb = x + bb * b
        if tb >= end: break
        place(mus, kick(120, 45, 0.6) * 0.75 * intensity, tb if bb % 2 == 0 else tb)
        if bb % 4 == 3: place(mus, kick(150, 60, 0.35) * 0.45 * intensity, tb + b / 2)
        place(mus, tick() * 0.2 * intensity, tb + b / 2)
        # ostinato strings eighths
        for e in range(2):
            on = int(b / 2 * SR); o = saw(note(ch[0] + 12 + (7 if (bb + e) % 3 == 2 else 0)), on, 8) * np.exp(-tt(on) * 9)
            place(mus, lp(o, 3000) * 0.12 * intensity, tb + e * b / 2)
    x += bar * 2; k += 1
# Final hit + tail
fn = int(3.0 * SR); ft = tt(fn)
final = (sum(saw(note(m), fn, 12) for m in [38, 50, 53, 57, 62]) / 4) * np.exp(-ft * 1.1)
final = lp(final, 2500)
place(mus, final * 0.6, 63.0); place(mus, kick(100, 35, 1.5) * 1.0, 63.0)
mus = reverb(mus, 2.0, 0.25)
mus = hp(mus, 30)

# ---------------- SFX ----------------
sfx = np.zeros(N)
def whoosh(d=0.6, f0=300, f1=4000, rev=False):
    n = int(d * SR); tw = tt(n); x = rng.normal(0, 1, n); out = np.zeros(n)
    # time-varying bandpass via block processing
    blk = 512; zi = None
    for i in range(0, n, blk):
        p = i / n; p = 1 - p if rev else p
        fc = f0 * (f1 / f0) ** p
        bb, aa = signal.butter(2, [fc * 0.6 / (SR / 2), min(fc * 1.6, 20000) / (SR / 2)], 'band')
        if zi is None: zi = signal.lfilter_zi(bb, aa) * 0
        out[i:i + blk], zi = signal.lfilter(bb, aa, x[i:i + blk], zi=zi)
    e = np.sin(np.pi * np.clip(tw / d, 0, 1)) ** 2
    return out * e * 2.2
def boom(g=1.0):
    n = int(1.6 * SR); tb = tt(n)
    f = 35 + 70 * np.exp(-tb * 9)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tb * 2.6)
    s += lp(rng.normal(0, 1, n), 1500) * np.exp(-tb * 18) * 0.6
    return s * g
def pop(f=900):
    n = int(0.12 * SR); tp = tt(n)
    return np.sin(2 * np.pi * np.cumsum(f * (1 + 1.2 * np.exp(-tp * 40))) / SR) * np.exp(-tp * 35)
def clickt():
    n = int(0.025 * SR); return np.sin(2 * np.pi * 2200 * tt(n)) * np.exp(-tt(n) * 220)
def beep(f=880, d=0.18):
    n = int(d * SR); return np.sin(2 * np.pi * f * tt(n)) * env_adsr(n, 0.005, 0.08)

CUTS = [8.1, 20.55, 26.85, 38.9, 50.0, 54.5, 63.0]
for c in CUTS: place(sfx, whoosh(0.65), c - 0.42, 0.55)
# title stamps / impacts
for tm, g in [(0.05, .9), (0.35, .7), (13.94, .8), (27.0, .7), (35.9, .9), (39.05, .6), (54.5, .6), (63.0, 1.0)]:
    place(sfx, boom(g), tm)
place(sfx, whoosh(0.5, 4000, 400), 5.45, 0.4)          # US flag in
for tm in (6.5, 6.75): place(sfx, whoosh(0.25, 1500, 6000), tm, 0.5)  # strike X
place(sfx, whoosh(0.5, 300, 3000), 7.1, 0.45)           # DR flag in
place(sfx, boom(0.5), 7.3)
place(sfx, whoosh(0.45, 600, 3000), 8.25, 0.3)          # map
place(sfx, beep(1320, 0.12) * 0.5, 11.65); place(sfx, beep(1320, 0.12) * 0.5, 11.85)  # Qatar lights
place(sfx, whoosh(0.45, 500, 3500), 15.1, 0.35)
for tm, f in [(16.0, 660), (17.1, 880), (17.42, 1100)]: place(sfx, beep(f) * 0.45, tm)
place(sfx, whoosh(0.5, 5000, 500), 20.85, 0.35)         # lower third
place(sfx, pop(700) * 0.6, 21.0)
for i in range(8): place(sfx, clickt() * 0.6, 23.45 + i * 0.1)  # countdown
place(sfx, pop(500) * 0.6, 25.55)
place(sfx, whoosh(0.4, 600, 3500), 29.95, 0.35)
place(sfx, pop(900) * 0.7, 31.4); place(sfx, pop(900) * 0.7, 31.75)
for tm in (33.4, 33.6): place(sfx, whoosh(0.3, 800, 5000), tm, 0.3)
for i in range(18): place(sfx, clickt() * 0.35, 34.5 + i * 0.07)
place(sfx, pop(1100) * 0.6, 37.38)
place(sfx, whoosh(1.2, 200, 3000), 40.2, 0.35)           # plane
for i in range(24): place(sfx, clickt() * 0.4, 41.04 + i * 0.036)
for g in [42.82, 45.44, 46.32, 46.92]: place(sfx, whoosh(0.3, 800, 5000), g - 0.1, 0.3); place(sfx, pop(800) * 0.4, g)
place(sfx, pop(600) * 0.6, 48.72)
place(sfx, whoosh(0.5, 5000, 500), 50.15, 0.35)
place(sfx, pop(700) * 0.5, 50.9)
for tm in (59.74, 61.68): place(sfx, pop(1000) * 0.7, tm)
place(sfx, whoosh(0.5, 400, 3000), 59.4, 0.4)
# whistle (CC0) on "empató"
wh = load("dl/whistle.wav"); wh = wh / (np.abs(wh).max() + 1e-9)
i0 = np.argmax(np.abs(wh) > 0.1); wh = wh[i0:i0 + int(1.3 * SR)] * env_adsr(min(len(wh) - i0, int(1.3 * SR)), 0.005, 0.4)
place(sfx, wh * 0.35, 30.76)
place(sfx, wh[:int(0.5 * SR)] * env_adsr(int(0.5 * SR), .005, .2) * 0.25, 27.0 - 0.6)
# crowd (CC BY-SA) loops
cr = load("dl/crowd.wav"); cr = cr / (np.abs(cr).max() + 1e-9)
def crowd(t0, t1, g, fi=0.8, fo=1.2):
    n = int((t1 - t0) * SR); reps = np.tile(cr, n // len(cr) + 2)[:n]
    e = np.minimum(np.clip(tt(n) / fi, 0, 1), np.clip((t1 - t0 - tt(n)) / fo, 0, 1))
    place(sfx, reps * e * g, t0)
crowd(0.0, 3.5, 0.18, 0.05, 2.0)
crowd(7.1, 9.0, 0.16, 0.2, 1.2)
crowd(31.3, 34.0, 0.16, 0.3, 1.5)
crowd(36.5, 40.5, 0.1, 1.0, 1.5)
crowd(54.3, 63.6, 0.2, 1.5, 1.0)

# ---------------- VOICE + MIX ----------------
voice = load("voice.mp3")
vb = np.zeros(N); place(vb, voice, 0.0)
# ducking envelope from voice
env = np.abs(vb); env = signal.lfilter([1], [1, -0.9995], env) * 0.0005
env = np.convolve(env, np.ones(2205) / 2205, mode='same')
duck = 1 - 0.45 * np.clip(env / (np.percentile(env[env > 0], 60) + 1e-9), 0, 1)
def norm(x, peak): return x / (np.abs(x).max() + 1e-9) * peak
mus = norm(mus, 1.0)
musg = np.where(tt(N) < EPIC, 0.19, 0.24) * np.ones(N)
musg[int(63.0 * SR):] = 1.0  # outro: music up
mix = norm(vb, 0.9) + mus * musg * duck + norm(sfx, 1.0) * 0.32 * (0.6 + 0.4 * duck)
mix = mix / max(1, np.abs(mix).max() / 0.97)
# fade out end
fo = int(0.8 * SR); mix[-fo:] *= np.linspace(1, 0, fo)
mix.astype(np.float32).tofile("build/mix.f32")
print("ok", np.abs(mix).max())
