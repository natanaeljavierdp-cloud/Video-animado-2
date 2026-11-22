# Música de fondo y efectos sintetizados (sin derechos de terceros)
import numpy as np, json, glob, soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000
DUR = 59.40
N = int(SR * DUR) + SR
rng = np.random.default_rng(1)

def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)

def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, f1, f2, o=2): return sosfilt(butter(o, [f1, f2], 'band', fs=SR, output='sos'), x)

def ks(freq, dur, damp=0.996):
    n = int(SR * dur); p = int(SR / freq)
    buf = rng.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = damp * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return out

# ---------------------------------------------------------------- música
def note(m): return 440 * 2 ** ((m - 69) / 12)
music = np.zeros((N, 2))
bpm = 104; beat = 60 / bpm
prog = [(60, [60, 64, 67]), (55, [55, 59, 62, 67]), (57, [57, 60, 64]), (53, [53, 57, 60, 65])]
pl_cache = {}
def pluck(m, dur=0.9):
    if m not in pl_cache:
        x = ks(note(m), dur, 0.995); x = lp(x, 3500); pl_cache[m] = x / (np.abs(x).max() + 1e-9)
    return pl_cache[m]
def add(buf, x, t, g, pan=0.0):
    i = int(t * SR); j = min(len(buf), i + len(x))
    if i >= len(buf) or j <= i: return
    buf[i:j, 0] += x[:j - i] * g * (1 - pan) ; buf[i:j, 1] += x[:j - i] * g * (1 + pan)

t = 0.0; bar = 0
pattern = [0, 2, 1, 2, 0, 2, 1, 2]
while t < DUR + 1:
    root, ch = prog[bar % 4]
    # bajo suave
    bt = np.arange(int(SR * beat * 1.8)) / SR
    bass = np.sin(2 * np.pi * note(root - 12) * bt) * env(len(bt), 0.01, 0.6)
    add(music, bass, t, 0.30); add(music, bass, t + beat * 2, 0.22)
    # arpegio pluck
    for k in range(8):
        m = ch[pattern[k] % len(ch)] + (12 if k in (3, 7) else 0)
        add(music, pluck(m), t + k * beat / 2, 0.16, -0.3 if k % 2 else 0.3)
    # melodía tipo marimba cada 2 compases
    if bar % 2 == 1:
        for k, d in enumerate([4, 7, 9, 7]):
            m = root + 12 + d if root < 58 else root + d
            mt = np.arange(int(SR * 0.5)) / SR
            mar = (np.sin(2 * np.pi * note(m + 12) * mt) + 0.3 * np.sin(2 * np.pi * note(m + 12) * 4 * mt)) * env(len(mt), 0.002, 0.18)
            add(music, mar, t + k * beat, 0.10)
    # shaker
    for k in range(8):
        sh = hp(rng.normal(0, 1, int(SR * 0.06)), 6000) * env(int(SR * 0.06), 0.003, 0.02)
        add(music, sh, t + k * beat / 2, 0.05 if k % 2 else 0.03)
    # kick suave
    for k in (0, 2):
        kt = np.arange(int(SR * 0.25)) / SR
        kick = np.sin(2 * np.pi * (50 + 60 * np.exp(-kt * 30)) * kt) * env(len(kt), 0.002, 0.08)
        add(music, kick, t + k * beat, 0.25)
    t += beat * 4; bar += 1
music = music[:int(SR * DUR)]
music /= np.abs(music).max() + 1e-9
fade = np.ones(len(music)); fo = int(SR * 1.2); fade[-fo:] = np.linspace(1, 0, fo); fade[:int(SR * 0.4)] = np.linspace(0, 1, int(SR * 0.4))
music *= fade[:, None]

# ---------------------------------------------------------------- efectos
sfx = np.zeros((N, 2))
def whoosh(d=0.6):
    n = int(SR * d); x = rng.normal(0, 1, n)
    tt = np.linspace(0, 1, n); f = 400 + 2200 * np.sin(np.pi * tt)
    y = np.zeros(n); seg = 2048
    for i in range(0, n, seg):
        fc = f[i]; y[i:i + seg] = bp(x[i:i + seg + 0], max(100, fc * 0.6), min(20000, fc * 1.6))[:len(y[i:i + seg])]
    return y * np.sin(np.pi * tt) ** 2
def click(f=3800, d=0.03):
    n = int(SR * d); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * tt) * 0.6 + hp(rng.normal(0, 1, n), 2500) * 0.7) * np.exp(-tt / 0.006)
def clac():
    n = int(SR * 0.25); tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * 180 * tt) * np.exp(-tt / 0.05) + 0.6 * np.sin(2 * np.pi * 520 * tt) * np.exp(-tt / 0.03)
    noise = bp(rng.normal(0, 1, n), 800, 5000) * np.exp(-tt / 0.015)
    return body * 0.8 + noise
def pop(f=600):
    n = int(SR * 0.12); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * (f + 900 * np.exp(-tt * 60)) * tt) * np.exp(-tt / 0.03)
def slide(d):
    n = int(SR * d); x = bp(rng.normal(0, 1, n), 1500, 6000)
    tt = np.linspace(0, 1, n); am = 0.6 + 0.4 * np.sin(2 * np.pi * 23 * tt * d)
    e = np.minimum(1, tt * 8) * np.minimum(1, (1 - tt) * 8)
    return x * am * e
def creak(d=1.1):
    n = int(SR * d); tt = np.arange(n) / SR
    f0 = 160 + 90 * np.sin(2 * np.pi * 0.8 * tt)
    ph = np.cumsum(f0) / SR
    pulses = (np.sin(2 * np.pi * ph) > 0.92).astype(float)
    y = bp(pulses + 0.02 * rng.normal(0, 1, n), 300, 3000)
    e = np.minimum(1, tt * 6) * np.minimum(1, (d - tt) * 4)
    return y * e
def thump():
    n = int(SR * 0.3); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * 90 * tt) * np.exp(-tt / 0.07) + 0.3 * bp(rng.normal(0, 1, n), 200, 1500) * np.exp(-tt / 0.03)
def ding(f=1320):
    n = int(SR * 0.4); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 2.01 * tt)) * np.exp(-tt / 0.12)
def buzz():
    n = int(SR * 0.35); tt = np.arange(n) / SR
    return np.sign(np.sin(2 * np.pi * 140 * tt)) * 0.5 * np.exp(-tt / 0.15)
def tick():
    n = int(SR * 0.015); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * 2500 * tt) * np.exp(-tt / 0.003)

def put(x, t, g, pan=0.0):
    x = np.asarray(x, float); x = x / (np.abs(x).max() + 1e-9)
    add(sfx, x, t, g, pan)

for t0 in (2.85, 51.5): put(whoosh(0.8), t0, 0.35)
put(whoosh(0.7), 4.5, 0.5)                 # desarmado
put(whoosh(0.6), 6.15, 0.35)
for k in range(4): put(pop(500 + 80 * k), 6.95 + k * 0.07, 0.25)
put(whoosh(0.9), 7.3, 0.22)                # corte
for k, d in enumerate([0, 0.2, 0.4, 0.6, 0.85]): put(click(3000 + 300 * k), 13.32 + d, 0.30)
for i in range(5): put(tick(), 14.15 + 0.3 * i, 0.15)
put(click(2600), 19.45, 0.25)
put(clac(), 25.02, 0.7); put(clac(), 50.12, 0.7)
put(slide(6.4), 26.2, 0.12); put(slide(2.4), 46.6, 0.12)
put(slide(0.6), 45.75, 0.10); put(slide(0.6), 51.45, 0.10)
# clics de pines al pasar los dientes: a partir de los datos de anclaje
A = {}
for f in glob.glob('/tmp/claude-0/w/AF/anch_*.json'):
    A.update({int(k): v for k, v in json.load(open(f)).items()})
if A:
    fr = sorted(A)
    for i in range(5):
        b = [A[f]['pins'][i][0] for f in fr]
        for j in range(1, len(fr) - 1):
            if b[j] > b[j - 1] + 1e-4 and b[j] >= b[j + 1] and (fr[j] / 30 > 26 and fr[j] / 30 < 33 or 46.5 < fr[j] / 30 < 49.2):
                put(click(3400 + 200 * i), fr[j] / 30, 0.22, 0.2)
put(click(2200), 32.72, 0.3); put(click(2200), 48.98, 0.3)
for i in range(5): put(ding(1320 + 110 * i), 36.0 + 0.35 * i, 0.16)
put(click(1800, 0.05), 40.5, 0.35); put(thump(), 42.3, 0.35)
put(creak(1.1), 44.2, 0.18); put(thump(), 46.15, 0.35)
put(whoosh(0.6), 46.1, 0.3)
put(buzz(), 48.95, 0.12)
for i in range(5): put(pop(600 + 70 * i), 51.95 + 0.28 * i + 0.2, 0.25)
for k in range(24): put(tick(), 54.5 + k * 0.046, 0.12)
put(whoosh(0.6), 54.95, 0.3)
for k, d in enumerate([0, 0.12, 0.2, 0.25, 0.38, 0.5, 0.62, 0.8]): put(pop(450 + 60 * k), 54.95 + d + 0.32, 0.28)
put(whoosh(1.0), 56.6, 0.25)
sfx = sfx[:int(SR * DUR)]

voice, vsr = sf.read('/tmp/claude-0/w/voz.wav')
import subprocess
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', '/tmp/claude-0/w/voz.mp3', '-ar', str(SR), '-ac', '2', '/tmp/claude-0/w/voz48.wav'])
voice, _ = sf.read('/tmp/claude-0/w/voz48.wav')
L = int(SR * DUR)
v = np.zeros((L, 2)); v[:min(L, len(voice))] = voice[:L]
mix = v * 1.0 + music * 0.075 + sfx * 0.55
mix /= max(1.0, np.abs(mix).max() / 0.97)
sf.write('/tmp/claude-0/w/mix.wav', mix, SR)
print('ok', mix.shape, np.abs(mix).max())
