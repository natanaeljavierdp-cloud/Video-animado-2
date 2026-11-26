# Musica y efectos sintetizados (originales, libres de derechos) + mezcla con la voz
# Uso: python3 audio.py voice.mp3 out.wav
import sys, subprocess, numpy as np, wave
SR = 44100
voice_path, out = sys.argv[1], sys.argv[2]
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', voice_path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
voice = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
N = len(voice)
T = N / SR
rng = np.random.default_rng(1)
t_all = np.arange(N) / SR

def env_adsr(n, a=0.005, d=0.2, s=0.0, r=0.05):
    e = np.ones(n)
    na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na)
    rest = np.arange(n - na) / SR
    e[na:] = s + (1 - s) * np.exp(-rest / d)
    nr = int(r * SR)
    if nr < n: e[-nr:] *= np.linspace(1, 0, nr)
    return e

def add(buf, sig, t0, gain=1.0):
    i = int(t0 * SR)
    if i >= len(buf): return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i] * gain

def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros_like(x); acc = 0.0
    # filtro de un polo (vectorizado por bloques via lfilter manual)
    from itertools import accumulate
    y = np.empty_like(x); prev = 0.0
    for k in range(len(x)):
        prev = (1 - a) * x[k] + a * prev
        y[k] = prev
    return y

def onepole(x, fc):
    # implementacion rapida con scipy si existe
    try:
        from scipy.signal import lfilter
        a = np.exp(-2 * np.pi * fc / SR)
        return lfilter([1 - a], [1, -a], x)
    except Exception:
        return lowpass(x, fc)

def bandnoise(n, lo, hi):
    x = rng.standard_normal(n)
    return onepole(x, hi) - onepole(x, lo)

# ---------------------------------------------------------------- musica
music = np.zeros(N)
bpm = 112; beat = 60 / bpm
def note(f, dur, kind='pluck'):
    n = int(dur * SR); tt = np.arange(n) / SR
    if kind == 'pluck':
        s = np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(6 * np.pi * f * tt)
        return s * env_adsr(n, 0.004, 0.22, 0.0, 0.03)
    if kind == 'bass':
        s = np.sin(2 * np.pi * f * tt) + 0.2 * np.sin(4 * np.pi * f * tt)
        return s * env_adsr(n, 0.01, 0.35, 0.3, 0.05)
    if kind == 'pad':
        s = np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 1.003 * tt)
        e = np.minimum(1, tt / 0.3) * np.minimum(1, (dur - tt) / 0.3)
        return s * e
def mid(m): return 440 * 2 ** ((m - 69) / 12)
prog = [(60, [60, 64, 67]), (67, [59, 62, 67]), (69, [60, 64, 69]), (65, [60, 65, 69])]  # C G Am F
arp = [0, 1, 2, 1, 0, 2, 1, 2]
bar = 4 * beat
nb = int(T / bar) + 2
for b in range(nb):
    root, ch = prog[b % 4]
    t0 = b * bar
    add(music, note(mid(root - 24), bar * 0.95, 'bass'), t0, 0.5)
    add(music, note(mid(root - 24), beat * 0.9, 'bass'), t0 + 2.5 * beat, 0.3)
    for k in range(8):
        m = ch[arp[k]] + (12 if k in (3, 7) else 0)
        add(music, note(mid(m + 12), beat * 0.6), t0 + k * beat / 2, 0.22)
    for m in ch:
        add(music, note(mid(m), bar, 'pad'), t0, 0.05)
    # percusion suave
    for k in range(8):
        hh = rng.standard_normal(int(0.04 * SR)) * env_adsr(int(0.04 * SR), 0.001, 0.012)
        add(music, np.diff(hh, prepend=0), t0 + k * beat / 2, 0.08 if k % 2 else 0.05)
    for k in (0, 2):
        n = int(0.12 * SR); tt = np.arange(n) / SR
        kick = np.sin(2 * np.pi * (50 + 60 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 18)
        add(music, kick, t0 + k * beat, 0.35)
music /= np.max(np.abs(music)) + 1e-9
fade = np.minimum(1, t_all / 1.0) * np.clip((T - t_all) / 1.2, 0, 1)
music *= fade

# ---------------------------------------------------------------- efectos
sfx = np.zeros(N)
def whoosh(dur=0.7, up=True):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    # barrido de filtro por bloques
    blk = 512; a_prev = 0.0; y = 0.0
    from math import exp, pi
    fcs = np.linspace(300, 3500, n) if up else np.linspace(3500, 300, n)
    for i in range(n):
        a = exp(-2 * pi * fcs[i] / SR)
        y = (1 - a) * x[i] + a * y
        out[i] = y
    e = np.sin(np.pi * tt / dur) ** 2
    return out * e * 3
def click():
    n = int(0.05 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2200 * tt) * np.exp(-tt * 160) + 0.6 * rng.standard_normal(n) * np.exp(-tt * 400))
def pop():
    n = int(0.18 * SR); tt = np.arange(n) / SR
    f = 300 + 600 * np.exp(-tt * 25)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 22)
def water(dur, t0, gain, lo=300, hi=2500):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = bandnoise(n, lo, hi)
    mod = 0.7 + 0.3 * np.sin(2 * np.pi * 5.3 * tt) * np.sin(2 * np.pi * 1.7 * tt)
    e = np.minimum(1, tt / 0.25) * np.minimum(1, (dur - tt) / 0.35)
    x = x / (np.std(x) + 1e-9)
    add(sfx, x * mod * e, t0, gain)
def gurgle(dur, t0, gain):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = bandnoise(n, 120, 900); x /= np.std(x) + 1e-9
    bub = np.zeros(n)
    for k in range(int(dur * 7)):
        st = rng.uniform(0, dur - 0.1); L = int(0.07 * SR); t2 = np.arange(L) / SR
        f = rng.uniform(250, 600)
        s = np.sin(2 * np.pi * f * (1 + 4 * t2) * t2) * np.exp(-t2 * 50)
        i = int(st * SR); bub[i:i + L] += s[:n - i]
    e = np.minimum(1, tt / 0.2) * np.minimum(1, (dur - tt) / 0.3)
    add(sfx, (0.6 * x + 0.8 * bub) * e, t0, gain)
def hum(t0, t1, f0, f1, gain, slow=None):
    n = int((t1 - t0) * SR); tt = np.arange(n) / SR
    ramp = np.clip(tt / 1.6, 0, 1)
    f = f0 + (f1 - f0) * ramp
    end = np.clip((t1 - t0 - tt) / 0.9, 0, 1)
    f = f * (0.4 + 0.6 * end)
    if slow:
        a, b = slow
        tw = t0 + tt
        sl = np.clip((tw - a) / 0.3, 0, 1) * np.clip((b - tw) / 0.3, 0, 1)
        f = f * (1 - 0.55 * sl)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)
    s += 0.25 * bandnoise(n, 200, 1500) / 1.0
    e = np.minimum(1, tt / 0.4) * end
    add(sfx, s * e, t0, gain)
def motor_swish(t0, dur, gain):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = bandnoise(n, 150, 1200); x /= np.std(x) + 1e-9
    e = np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 1.5
    add(sfx, x * e, t0, gain)

add(sfx, whoosh(0.9), 4.35, 0.17)
for tc in (13.85, 19.86, 40.1, 41.6):
    add(sfx, click(), tc, 0.55)
water(5.6, 14.3, 0.09)
water(3.0, 21.1, 0.05)
water(1.5, 40.3, 0.08)
for a, b in [(27.3, 29.25), (29.95, 31.0), (31.05, 32.9), (33.0, 34.75), (34.8, 36.45), (41.3, 42.35), (42.45, 43.55), (65.3, 67.3), (67.4, 69.9)]:
    motor_swish(a, b - a, 0.06)
gurgle(2.2, 37.9, 0.12)
gurgle(1.7, 43.6, 0.08)
hum(45.2, 65.2, 70, 210, 0.07, slow=(51.9, 54.3))
water(8.5, 46.6, 0.035, 800, 4000)
add(sfx, whoosh(0.5, up=False), 70.0, 0.14)
add(sfx, pop(), 70.48, 0.35)
add(sfx, pop(), 65.35, 0.2)

sfx *= 0.32
mix = voice * 1.0 + music * 0.095 + sfx
# atenuar musica un poco bajo la voz ya incluido (volumen bajo)
mix = np.tanh(mix * 1.1) / 1.1
pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
with wave.open(out, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok', T)
