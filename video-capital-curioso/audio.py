# Synthesized suspense score + SFX, ducked under the narration. Writes build/mezcla.wav
import os, subprocess, wave
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; DUR = 76.0; N = int(SR * DUR)
rng = np.random.default_rng(1)
tt = np.arange(N) / SR

def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, a, b, o=2): return sosfilt(butter(o, [a, b], 'band', fs=SR, output='sos'), x)
def env(n, a, r):
    e = np.ones(n); ia = int(a * SR); ir = int(r * SR)
    if ia: e[:ia] = np.linspace(0, 1, ia)
    if ir: e[-ir:] *= np.linspace(1, 0, ir)
    return e
def add(buf, t0, sig, g=1.0):
    i = int(t0 * SR); j = min(len(buf), i + len(sig))
    if i < len(buf): buf[i:j] += sig[:j - i] * g

def note(f): return 440 * 2 ** ((f - 69) / 12)

# ------------------------------------------------------------ music
music = np.zeros(N)
SECT = [(0, 8.3, [45, 52, 60]), (8.0, 15.3, [45, 52, 60, 64]), (15.0, 22.8, [41, 48, 57, 60]), (22.5, 31.5, [38, 45, 53, 57]),
        (31.2, 37.8, [45, 52, 60, 63]), (37.5, 45.2, [41, 48, 56, 60]), (45.0, 53.5, [40, 47, 56, 59]), (53.2, 60.3, [38, 45, 50, 53]),
        (60.0, 65.8, [41, 48, 53, 57]), (65.5, 72.3, [40, 47, 52, 56, 59]), (72.0, 76.0, [45, 52, 57, 64])]
for a, b, notes in SECT:
    n = int((b - a) * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for k, m in enumerate(notes):
        f = note(m); det = 1 + 0.003 * (k + 1)
        trem = 0.75 + 0.25 * np.sin(2 * np.pi * (0.13 + 0.05 * k) * t + k)
        w = sum(np.sin(2 * np.pi * f * det * h * t + k) / h ** 1.6 for h in (1, 2, 3, 4)) + np.sin(2 * np.pi * f / det * t)
        s += w * trem * (1.0 if k == 0 else 0.45) / len(notes)
    s = lp(s, 1400)
    add(music, a, s * env(n, .7, .7), 0.55)
# sub drone + wind
sub = np.sin(2 * np.pi * 36.7 * tt) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * tt)) * 0.25
wind = bp(rng.standard_normal(N), 300, 1800) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * tt + 1)) * 0.05
eerie = np.sin(2 * np.pi * (1760 + 6 * np.sin(2 * np.pi * 5 * tt)) * tt) * 0.012 * (0.5 + 0.5 * np.sin(2 * np.pi * .09 * tt))
music += sub + wind + eerie

def thump(f0=55, d=.45):
    n = int(d * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (f0 + 60 * np.exp(-t * 30)) * t) * np.exp(-t * 9)
def hat(d=.05):
    n = int(d * SR); return hp(rng.standard_normal(n), 7000) * np.exp(-np.arange(n) / SR * 80)
# heartbeat in the hook
for b in np.arange(0.2, 8.0, 60 / 66): add(music, b, thump(), .55); add(music, b + .22, thump(50), .35)
# driving pulse in data sections
for a, b, bpm in ((8.0, 31.2, 104), (33.2, 53.2, 104), (65.5, 72.0, 116)):
    beat = 60 / bpm
    for k, x in enumerate(np.arange(a, b, beat / 2)):
        add(music, x, hat(), .18 if k % 2 else .10)
        if k % 4 == 0: add(music, x, thump(48, .35), .4)
fo = np.ones(N); fo[int(74.5 * SR):] = np.linspace(1, 0, N - int(74.5 * SR)); music *= fo

# ------------------------------------------------------------ sfx
sfx = np.zeros(N)
def boom(d=2.2):
    n = int(d * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * (34 + 120 * np.exp(-t * 7)) * t) * np.exp(-t * 2.2)
    s += lp(rng.standard_normal(n), 400) * np.exp(-t * 9) * 1.5
    return s
def whoosh(d=.7, rev=False):
    n = int(d * SR); t = np.arange(n) / SR; x = rng.standard_normal(n)
    lo, hi = bp(x, 200, 900), bp(x, 1500, 6000); k = t / d
    s = lo * (1 - k) + hi * k
    e = np.sin(np.pi * k) ** 2
    s = s * e
    return s[::-1] if rev else s
def tick():
    n = int(.03 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2600 * t) * .6 + hp(rng.standard_normal(n), 3000)) * np.exp(-t * 260)
def blip(f=1300, d=.05):
    n = int(d * SR); t = np.arange(n) / SR; return np.sin(2 * np.pi * f * t) * np.exp(-t * 60)
def pop():
    n = int(.12 * SR); t = np.arange(n) / SR; return np.sin(2 * np.pi * (500 + 2500 * t) * t) * np.exp(-t * 35)
def ping(f=1450):
    n = int(1.4 * SR); t = np.arange(n) / SR; s = np.sin(2 * np.pi * f * t) * np.exp(-t * 4)
    s[int(.28 * SR):] += s[:n - int(.28 * SR)] * .4; return s
def glitch(d=.3):
    n = int(d * SR); t = np.arange(n) / SR; s = np.zeros(n); i = 0
    while i < n:
        m = int(rng.uniform(.01, .04) * SR); f = rng.uniform(80, 900)
        seg = np.sign(np.sin(2 * np.pi * f * t[:min(m, n - i)])) * rng.uniform(.3, 1)
        if rng.random() < .4: seg = rng.standard_normal(len(seg)) * .6
        s[i:i + len(seg)] = seg; i += m
    return lp(s, 6000) * .5
def powerdown():
    n = int(.11 * SR); t = np.arange(n) / SR; return np.sin(2 * np.pi * (900 - 5000 * t) * t) * np.exp(-t * 18)
def riser(d=1.4):
    n = int(d * SR); t = np.arange(n) / SR; k = t / d
    return (bp(rng.standard_normal(n), 800, 5000) * k ** 2 * .8 + np.sin(2 * np.pi * (200 + 900 * k ** 2) * t) * k ** 2 * .3)
def ding():
    n = int(2.5 * SR); t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * 880 * r * t) * np.exp(-t * (2 + 2 * i)) / (i + 1) for i, r in enumerate((1, 2.76, 5.4, 8.9)))

for s in (0, 1, 2, 3): add(sfx, s, tick(), .5)
add(sfx, 3.2, whoosh(.5), .35); add(sfx, 3.38, boom(1.2), .45)
add(sfx, 4.9, boom(), .85); add(sfx, 5.5, boom(1.4), .55)
add(sfx, 7.7, whoosh(.6), .4)
for x in np.arange(8.1, 9.9, .07): add(sfx, x, blip(1500), .07)
for x in np.arange(11.4, 12.4, .09): add(sfx, x, blip(1100), .06)
add(sfx, 11.38, pop(), .3)
add(sfx, 14.8, whoosh(.6), .35)
add(sfx, 16.2, boom(1.0), .35)
for x in (18.45, 20.62): add(sfx, x, ping(1250), .18)
add(sfx, 21.45, boom(1.6), .45); add(sfx, 21.45, ping(1700), .18)
add(sfx, 22.2, whoosh(.6), .35)
add(sfx, 25.78, boom(1.6), .6)
for i in range(22): add(sfx, 26.4 + i * .085, powerdown(), .12)
add(sfx, 28.3, whoosh(.55), .35)
add(sfx, 30.95, riser(.4), .25)
add(sfx, 31.2, glitch(.45), .4); add(sfx, 31.6, boom(), .7)
add(sfx, 33.1, whoosh(.5), .35); add(sfx, 33.3, glitch(.15), .3); add(sfx, 34.35, glitch(.25), .35)
for x in np.arange(35.0, 36.4, .06): add(sfx, x, blip(1600), .06)
add(sfx, 37.3, whoosh(.5), .35)
add(sfx, 41.2, riser(1.2), .15); add(sfx, 43.25, pop(), .3)
add(sfx, 44.8, whoosh(.5), .35)
add(sfx, 47.84, whoosh(.35, True), .25)
add(sfx, 50.5, riser(1.3), .2); add(sfx, 51.84, boom(), .75)
add(sfx, 53.0, whoosh(.6), .35)
for x in np.arange(53.4, 55.0, .09): add(sfx, x, tick(), .12)
add(sfx, 55.72, boom(1.8), .9); add(sfx, 55.72, lp(rng.standard_normal(int(.15 * SR)), 900) * np.exp(-np.arange(int(.15 * SR)) / SR * 30), .6)
add(sfx, 57.48, pop(), .2)
add(sfx, 59.8, whoosh(.6), .35)
for x in (62.78, 63.72, 64.44): add(sfx, x, ping(1450), .22)
add(sfx, 65.3, whoosh(.6), .35)
for x in (65.7, 66.96, 68.92): add(sfx, x, pop(), .35)
add(sfx, 70.6, riser(1.4), .3); add(sfx, 72.0, whoosh(.6), .35); add(sfx, 72.0, boom(2.5), .6)
add(sfx, 72.8, ding(), .3)

ir_n = int(1.1 * SR); ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR * 5); ir = lp(ir, 5000)
sfx = sfx + fftconvolve(sfx, ir)[:N] * .025

# ------------------------------------------------------------ voice + ducking
raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', os.path.join(HERE, 'audio/narracion.mp3'), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                     capture_output=True, check=True).stdout
voice = np.frombuffer(raw, np.float32).astype(np.float64)
v = np.zeros(N); v[:min(N, len(voice))] = voice[:N]
e = lp(np.abs(v), 6)
e = e / (np.percentile(e, 95) + 1e-9)
duck = 1 - 0.5 * np.clip(e * 1.5, 0, 1)
duck = lp(duck, 3)

music *= 0.20 / (np.abs(music).max() + 1e-9) * 1.8
sfx *= 0.55 / (np.abs(sfx).max() + 1e-9)
vg = 0.9 / (np.abs(v).max() + 1e-9)
mix = v * vg + music * duck + sfx
L = mix + np.roll(music * duck, 240) * .08  # slight width
R = mix - np.roll(music * duck, 240) * .08
st = np.stack([L, R], 1); st /= max(1.0, np.abs(st).max() / .97)
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
with wave.open(os.path.join(HERE, 'build/mezcla.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print('ok')
