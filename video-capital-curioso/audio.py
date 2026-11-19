"""Mix: narration + background music (ducked) + synthesized SFX (whoosh, ding, tick, impact).
Usage: python3 audio.py <narration.mp3> <music.mp3> <out.wav> <total_s>"""
import sys, subprocess, numpy as np
SR = 44100
def load(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).copy()
nar, mus = load(sys.argv[1]), load(sys.argv[2])
T = float(sys.argv[4]); N = int(T * SR)
out = np.zeros((N, 2), np.float32)
out[:len(nar)] += nar[:N] * 1.0
rng = np.random.default_rng(7)

def whoosh(d=0.55):
    n = int(d * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    # sweeping band-pass via FFT-free one-pole filters with moving cutoff
    y = np.zeros(n); lp = 0; hp_prev = 0; x_prev = 0
    for i in range(n):
        f = 300 + 4500 * np.sin(np.pi * i / n) ** 2
        a = 1 - np.exp(-2 * np.pi * f / SR)
        lp += a * (noise[i] - lp)
        y[i] = lp
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.5
    y = y * env; y /= np.abs(y).max()
    pan = np.linspace(-0.7, 0.7, n)
    return np.stack([y * (1 - pan) / 2 * 1.4, y * (1 + pan) / 2 * 1.4], 1) * 0.5

def ding():
    d = 1.4; t = np.arange(int(d * SR)) / SR
    y = 0
    for f, a, k in [(1568, 1, 3.5), (2093, .7, 4), (3136, .35, 6), (4186, .2, 8)]:
        y = y + a * np.sin(2 * np.pi * f * t) * np.exp(-k * t)
    y2 = np.zeros_like(y); off = int(0.09 * SR)
    y2[off:] = y[:-off] * 0.8   # cash-register double ding
    y = (y + y2) * (1 - np.exp(-t * 400))
    y /= np.abs(y).max()
    return np.stack([y, y], 1) * 0.32

def tick():
    t = np.arange(int(0.03 * SR)) / SR
    y = (np.sin(2 * np.pi * 2600 * t) + .5 * rng.standard_normal(len(t))) * np.exp(-t * 260)
    return np.stack([y, y], 1) * 0.14

def impact():
    d = 1.0; t = np.arange(int(d * SR)) / SR
    f = 90 * np.exp(-t * 2) + 40
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4)
    y += 0.3 * rng.standard_normal(len(t)) * np.exp(-t * 30)
    y /= np.abs(y).max()
    return np.stack([y, y], 1) * 0.45

def add(s, at):
    i = int(at * SR); j = min(N, i + len(s))
    if i < N: out[i:j] += s[:j - i]

W = whoosh()
for at in [0.05, 2.75, 5.5, 8.2, 12.8, 33.5, 41.95, 47.35, 50.65, 57.05, 63.35]:
    add(W, at)
D = ding()
for at in [7.0, 11.26, 51.7, 54.0]: add(D, at)
TK = tick()
def ticks(a, b, step=0.07):
    x = a
    while x < b: add(TK, x); x += step
ticks(9.1, 11.2, 0.1)
for ts in [15.10, 17.64, 19.56, 24.98, 26.40, 28.72]: ticks(ts, ts + 0.9)
ticks(50.95, 51.65, 0.05); ticks(53.2, 53.95, 0.09)
add(impact(), 29.6)
for at in [37.40, 38.20, 38.62, 39.75]: add(tick() * 2.5, at)

# music: duck under voice, swell at outro, fade out
m = mus[:N] if len(mus) >= N else np.pad(mus, ((0, N - len(mus)), (0, 0)))
env = np.full(N, 0.16, np.float32)
end_v = 63.55
i0 = int(end_v * SR)
env[i0:] = np.linspace(0.16, 0.38, min(int(.4 * SR), N - i0)).tolist() + [0.38] * max(0, N - i0 - int(.4 * SR))
fade = int(1.2 * SR); env[-fade:] *= np.linspace(1, 0, fade)
env[:int(.5 * SR)] *= np.linspace(0, 1, int(.5 * SR))
out += m * env[:, None]
peak = np.abs(out).max(); out *= 0.95 / max(peak, 0.95)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", sys.argv[3]], input=out.astype(np.float32).tobytes())
print("peak", peak)
