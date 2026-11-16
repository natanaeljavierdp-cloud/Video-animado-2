# Genera música de suspenso + efectos (síntesis propia, sin derechos) y mezcla con la narración.
import json, numpy as np, subprocess, sys
SR = 44100
cfg = json.load(open('build/cues.json')); DUR = cfg['dur']; N = int(DUR * SR)
rng = np.random.default_rng(7)
t_all = np.arange(N) / SR
def env(n, a, r):
    e = np.ones(n); a = max(1, int(a * SR)); r = max(1, int(r * SR))
    e[:a] = np.linspace(0, 1, a); e[-r:] *= np.linspace(1, 0, r) ** 2; return e
def lp(x, k):  # filtro paso bajo de un polo, k en (0,1]
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc += k * (x[i] - acc); y[i] = acc
    return y
def lp_fast(x, cutoff):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= 1 / np.sqrt(1 + (f / cutoff) ** 4); return np.fft.irfft(X, len(x))
def bp_sweep(x, f0, f1):
    # barrido de paso banda por bloques
    out = np.zeros_like(x); B = 1024
    for s in range(0, len(x), B // 2):
        seg = x[s:s + B]; 
        if len(seg) < 8: break
        w = np.hanning(len(seg)); fc = f0 * (f1 / f0) ** (s / len(x))
        X = np.fft.rfft(seg * w); f = np.fft.rfftfreq(len(seg), 1 / SR)
        X *= np.exp(-((np.log2((f + 1) / fc)) ** 2) / 0.5); out[s:s + len(seg)] += np.fft.irfft(X, len(seg)) * .5
    return out
# ---------------- Música ----------------
mus = np.zeros(N)
def note(f, dur, a=.6, r=1.2, harm=((1, 1), (2, .3), (3, .1))):
    n = int(dur * SR); tt = np.arange(n) / SR
    s = sum(g * np.sin(2 * np.pi * f * h * tt + rng.random() * 6) for h, g in harm)
    return s * env(n, a, r)
# drone en Re menor
for f, g in [(36.71, .35), (73.42, .22), (110.0, .08), (55.0, .1)]:
    mus += g * np.sin(2 * np.pi * f * t_all + 0.3 * np.sin(2 * np.pi * .07 * t_all)) * (0.8 + 0.2 * np.sin(2 * np.pi * .05 * t_all + f))
# pad de acordes (Dm – Bb – Gm – A)
chords = [[146.83, 174.61, 220.0], [116.54, 146.83, 174.61], [98.0, 116.54, 146.83], [110.0, 138.59, 164.81]]
bar = 60 / 84 * 4  # 84 BPM
k = 0; tt0 = 0.0
while tt0 < DUR:
    ch = chords[k % 4]; seg = sum(note(f, bar * 2 + .5, a=1.2, r=1.5, harm=((1, 1), (2, .15))) for f in ch) * .05
    s = int(tt0 * SR); e = min(N, s + len(seg)); mus[s:e] += seg[:e - s]; tt0 += bar * 2; k += 1
# pulso tipo latido + hi-hat de reloj
beat = 60 / 84
for i in range(int(DUR / beat)):
    s = int(i * beat * SR)
    if i % 4 in (0, 2) or (i % 4 == 3 and i % 8 == 7):
        n = int(.35 * SR); tt = np.arange(n) / SR
        kick = np.sin(2 * np.pi * (55 * np.exp(-tt * 8) + 38) * tt) * np.exp(-tt * 9) * .55
        mus[s:s + n] += kick[:max(0, min(n, N - s))]
    n = int(.05 * SR); tick = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 120) * (.06 if i % 2 else .1)
    tick = np.diff(np.concatenate([[0], tick]))
    for off in (0, beat / 2):
        so = s + int(off * SR); mus[so:so + n] += tick[:max(0, min(n, N - so))]
# arpegio misterioso (piano-like) en la segunda mitad de cada ciclo
arp = [293.66, 349.23, 440.0, 587.33, 440.0, 349.23]
for i in range(int(DUR / (beat / 2))):
    if (i // 16) % 2 == 1 and i % 2 == 0:
        f = arp[(i // 2) % len(arp)]; seg = note(f, .9, a=.005, r=.85, harm=((1, 1), (2, .4), (3, .15), (4, .05))) * .045
        s = int(i * beat / 2 * SR); e = min(N, s + len(seg)); mus[s:e] += seg[:e - s]
mus = lp_fast(mus, 3500)
# entrada y salida
mus *= np.clip(t_all / 1.5, 0, 1) * np.clip((DUR - t_all) / 2.0, 0, 1)
# ---------------- Efectos ----------------
sfx = np.zeros(N)
def put(t, x, g):
    s = int(t * SR); e = min(N, s + len(x)); 
    if s < N: sfx[max(0, s):e] += g * x[max(0, -s):e - s]
def whoosh(d=.55, f0=300, f1=4000):
    n = int(d * SR); x = rng.standard_normal(n); y = bp_sweep(x, f0, f1)
    e = np.sin(np.linspace(0, np.pi, n)) ** 2; return y * e / (np.abs(y).max() + 1e-9)
def click():
    n = int(.03 * SR); tt = np.arange(n) / SR; return np.sin(2 * np.pi * 2200 * tt) * np.exp(-tt * 260) + .4 * rng.standard_normal(n) * np.exp(-tt * 600)
def pop():
    n = int(.12 * SR); tt = np.arange(n) / SR; return np.sin(2 * np.pi * (900 * np.exp(-tt * 30) + 300) * tt) * np.exp(-tt * 35)
def blip():
    n = int(.09 * SR); tt = np.arange(n) / SR; return np.sin(2 * np.pi * 1320 * tt) * np.exp(-tt * 45) * .8
def ding():
    n = int(1.2 * SR); tt = np.arange(n) / SR; return sum(g * np.sin(2 * np.pi * f * tt) for f, g in [(1760, 1), (2637, .5), (3520, .25)]) * np.exp(-tt * 4) * .6
def impact():
    n = int(1.4 * SR); tt = np.arange(n) / SR
    b = np.sin(2 * np.pi * (80 * np.exp(-tt * 4) + 32) * tt) * np.exp(-tt * 3.2)
    nz = lp_fast(rng.standard_normal(n), 900) * np.exp(-tt * 10) * .8
    return np.tanh((b + nz) * 1.5)
def hit():
    n = int(.6 * SR); tt = np.arange(n) / SR
    return np.tanh((np.sin(2 * np.pi * (120 * np.exp(-tt * 12) + 45) * tt) * np.exp(-tt * 7) + lp_fast(rng.standard_normal(n), 2500) * np.exp(-tt * 25) * .7) * 1.6)
def stamp():
    n = int(.4 * SR); tt = np.arange(n) / SR
    return np.tanh((lp_fast(rng.standard_normal(n), 1500) * np.exp(-tt * 30) * 1.4 + np.sin(2 * np.pi * 90 * tt) * np.exp(-tt * 18)) * 2)
def shimmer():
    n = int(1.3 * SR); tt = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * tt + f) for f in (2093, 2637, 3136, 4186)) * np.exp(-tt * 3) * np.clip(tt / .03, 0, 1) * .25
def riser(d=1.4, up=True):
    n = int(d * SR); x = rng.standard_normal(n); y = bp_sweep(x, 200, 5000) if up else bp_sweep(x, 5000, 200)
    e = np.linspace(0, 1, n) ** 2 if up else np.linspace(1, 0, n) ** 1.5
    return y / (np.abs(y).max() + 1e-9) * e
def alarm():
    n = int(1.1 * SR); tt = np.arange(n) / SR; f = np.where((tt * 4).astype(int) % 2 == 0, 880, 660)
    return np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * .25 * lp_fast(np.ones(n), 1) * np.exp(-tt * 1.5)
def ticker(d):
    n = int(d * SR); x = np.zeros(n); c = click() * .5; tt = 0.0; step = .035
    while tt < d:
        s = int(tt * SR); e = min(n, s + len(c)); x[s:e] += c[:e - s]; tt += step * (1 + 1.5 * (tt / d) ** 3)
    return x
for t, kind, g in cfg['cues']:
    if kind.startswith('ticker:'): put(t, ticker(float(kind.split(':')[1])), g * .7); continue
    x = {'whoosh': lambda: whoosh(), 'whoosh_s': lambda: whoosh(.35, 800, 6000) * .7, 'click': click, 'pop': pop, 'blip': blip, 'ding': ding,
         'impact': impact, 'hit': hit, 'stamp': stamp, 'shimmer': shimmer, 'riser': lambda: riser(), 'riser_down': lambda: riser(1.6, False), 'alarm': alarm}[kind]()
    put(t - (len(x) / SR * .55 if kind == 'whoosh' else 0), x, g)
def norm(x, peak): return x / (np.abs(x).max() + 1e-9) * peak
mus = norm(mus, 1.0); sfx = norm(sfx, 1.0)
def wav(x, p):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '-', p], input=pcm, check=True)
wav(mus, 'build/musica.wav'); wav(sfx, 'build/sfx.wav')
print('ok', DUR)
