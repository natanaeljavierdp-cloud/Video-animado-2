import numpy as np, wave, sys
from scipy import signal

SR = 48000
rng = np.random.default_rng(1)

def env(n, a, d, curve=4):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-np.maximum(t - a, 0) * curve / max(d, 1e-4))
    return e

def lp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'low'); return signal.lfilter(b, a, x)

def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'high'); return signal.lfilter(b, a, x)

def bp(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], 'band'); return signal.lfilter(b, a, x)

def reverb(x, wet=0.3, length=1.2):
    n = int(SR * length)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 5.0)
    ir = lp(ir, 5000)
    y = signal.fftconvolve(x, ir)[:len(x) + n]
    y = y / (np.abs(y).max() + 1e-9) * np.abs(x).max()
    out = np.zeros(len(y)); out[:len(x)] += x * (1 - wet)
    return out + y * wet

def norm(x, peak=0.9):
    return x / (np.abs(x).max() + 1e-9) * peak

def whoosh(d=0.7):
    n = int(SR * d); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    # sweeping band via time-varying lowpass approximated in blocks
    out = np.zeros(n); blk = 512
    zi = None
    for i in range(0, n, blk):
        f = 300 + 5000 * np.sin(np.pi * min(i / n, 1)) ** 2
        b, a = signal.butter(2, [max(80, f * 0.3) / (SR / 2), min(f * 1.6, 20000) / (SR / 2)], 'band')
        seg = x[i:i + blk]
        if zi is None:
            zi = signal.lfilter_zi(b, a) * 0
        y, zi = signal.lfilter(b, a, seg, zi=zi)
        out[i:i + blk] = y
    e = np.sin(np.pi * t / d) ** 2.2
    return norm(out * e, 0.8)

def boom(d=2.2, f0=58, f1=32):
    n = int(SR * d); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 2.2)
    noise = lp(rng.standard_normal(n), 900) * np.exp(-t * 7) * 0.8
    click = hp(rng.standard_normal(n), 2000) * np.exp(-t * 60) * 0.5
    return norm(reverb(s + noise + click, 0.25, 1.5), 0.95)

def hit(d=0.6):
    n = int(SR * d); t = np.arange(n) / SR
    f = 70 + 110 * np.exp(-t * 25)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    sn = bp(rng.standard_normal(n), 800, 6000) * np.exp(-t * 35) * 0.6
    return norm(s + sn, 0.9)

def ping(freq=1400, d=1.6):
    n = int(SR * d); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2.01 * t)) * env(n, 0.003, 0.5, 3)
    return norm(reverb(s, 0.45, 1.4), 0.6)

def sonar(d=2.6):
    n = int(SR * d); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * 880 * t) * env(n, 0.01, 1.4, 3) * (1 + 0.15 * np.sin(2 * np.pi * 6 * t))
    out = s.copy()
    for k, g in [(0.45, 0.4), (0.9, 0.2), (1.35, 0.1)]:
        sh = int(k * SR); out[sh:] += s[:n - sh] * g
    return norm(reverb(out, 0.5, 2.0), 0.6)

def tick(d=0.05):
    n = int(SR * d); t = np.arange(n) / SR
    return norm(hp(rng.standard_normal(n), 3000) * np.exp(-t * 200) + np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 120), 0.5)

def pop(d=0.25):
    n = int(SR * d); t = np.arange(n) / SR
    f = 300 + 900 * np.exp(-t * 30)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18)
    return norm(s, 0.6)

def riser(d=1.6):
    n = int(SR * d); t = np.arange(n) / SR
    f = 200 * (8 ** (t / d))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3 + hp(rng.standard_normal(n), 2000) * 0.4 * (t / d)
    return norm(s * (t / d) ** 2, 0.55)

def crack(d=0.9):
    n = int(SR * d); t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(14):
        p = int(rng.uniform(0, 0.25) * SR)
        L = int(0.02 * SR)
        x[p:p + L] += hp(rng.standard_normal(L), 1500) * np.exp(-np.arange(L) / SR * 150) * rng.uniform(0.4, 1)
    x += lp(rng.standard_normal(n), 400) * np.exp(-t * 6) * 0.5
    return norm(reverb(x, 0.2, 0.8), 0.85)

def explosion(d=1.6):
    n = int(SR * d); t = np.arange(n) / SR
    x = lp(rng.standard_normal(n), 1800) * env(n, 0.005, 0.6, 3)
    sub = np.sin(2 * np.pi * np.cumsum(45 + 40 * np.exp(-t * 10)) / SR) * np.exp(-t * 3)
    return norm(reverb(x + sub, 0.3, 1.2), 0.85)

def buzz(d=2.4):
    n = int(SR * d); t = np.arange(n) / SR
    f = 155 + 6 * np.sin(2 * np.pi * 3 * t)
    s = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR) * 0.5 + signal.sawtooth(2 * np.pi * np.cumsum(f * 1.5) / SR) * 0.3
    s = lp(s, 1500)
    e = np.minimum(t / 0.4, 1) * np.minimum((d - t) / 0.6, 1)
    return norm(s * e, 0.4)

def stamp(d=0.8):
    return norm(hit(d) * 0.8 + boom(d, 90, 50)[:int(SR * d)] * 0.6, 0.95)

def cash(d=1.0):
    n = int(SR * d); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t) for f in (2637, 3136, 3951)) * np.exp(-t * 6)
    s[: int(0.04 * SR)] += hp(rng.standard_normal(int(0.04 * SR)), 3000) * 0.5
    return norm(reverb(s, 0.3, 0.8), 0.4)

def horn(d=1.6):
    n = int(SR * d); t = np.arange(n) / SR
    s = signal.sawtooth(2 * np.pi * 98 * t) + signal.sawtooth(2 * np.pi * 147 * t) * 0.6
    s = lp(s, 700) * np.minimum(t / 0.15, 1) * np.minimum((d - t) / 0.4, 1)
    return norm(reverb(s, 0.4, 2.0), 0.5)

GEN = dict(whoosh=whoosh, boom=boom, hit=hit, ping=ping, sonar=sonar, tick=tick, pop=pop, riser=riser, crack=crack,
           explosion=explosion, buzz=buzz, stamp=stamp, cash=cash, horn=horn)

EVENTS = [
    (0.0, 'boom', 0.55), (0.22, 'hit', 0.55), (0.80, 'hit', 0.6), (1.38, 'hit', 0.7), (2.05, 'boom', 0.75), (0.6, 'sonar', 0.25),
    (4.15, 'whoosh', 0.55), (5.1, 'riser', 0.35), (6.55, 'boom', 0.5), (6.6, 'ping', 0.35), (6.25, 'hit', 0.45),
    (8.0, 'whoosh', 0.55), (8.35, 'hit', 0.45), (10.16, 'pop', 0.4), (10.78, 'pop', 0.4), (11.66, 'hit', 0.55), (12.3, 'pop', 0.4),
    (13.5, 'explosion', 0.6), (13.75, 'explosion', 0.4), (14.15, 'explosion', 0.35), (14.4, 'explosion', 0.3), (14.0, 'hit', 0.4),
    (16.5, 'whoosh', 0.55), (16.85, 'pop', 0.4), (18.68, 'crack', 0.7), (18.95, 'stamp', 0.6), (19.75, 'whoosh', 0.4), (19.9, 'hit', 0.45),
    (20.6, 'sonar', 0.35), (21.0, 'pop', 0.3), (21.4, 'pop', 0.3), (21.8, 'pop', 0.3), (21.6, 'tick', 0.5), (22.0, 'tick', 0.5), (22.4, 'tick', 0.5), (22.2, 'hit', 0.5),
    (23.3, 'whoosh', 0.55), (23.6, 'ping', 0.3), (24.62, 'explosion', 0.55), (25.1, 'explosion', 0.4), (25.8, 'ping', 0.25),
    (26.85, 'whoosh', 0.45), (27.2, 'sonar', 0.35), (27.6, 'hit', 0.45), (28.3, 'hit', 0.45), (30.4, 'pop', 0.35),
    (31.2, 'whoosh', 0.55), (31.7, 'ping', 0.35), (32.8, 'buzz', 0.45), (32.9, 'hit', 0.35), (33.3, 'ping', 0.25),
    (34.2, 'explosion', 0.45), (34.45, 'boom', 0.5), (34.6, 'explosion', 0.35), (34.95, 'explosion', 0.35), (35.3, 'explosion', 0.3),
    (35.7, 'whoosh', 0.55), (36.2, 'sonar', 0.35), (37.2, 'hit', 0.45),
    (39.45, 'whoosh', 0.5), (40.1, 'boom', 0.6), (40.5, 'boom', 0.6), (40.9, 'hit', 0.5),
    (42.4, 'whoosh', 0.55), (43.3, 'riser', 0.4), (45.05, 'stamp', 0.75), (45.1, 'cash', 0.3),
    (46.85, 'whoosh', 0.55), (47.7, 'ping', 0.3), (48.4, 'horn', 0.35), (49.75, 'hit', 0.5), (50.6, 'hit', 0.4),
    (52.2, 'whoosh', 0.5), (52.75, 'pop', 0.4), (53.9, 'whoosh', 0.25), (54.3, 'pop', 0.4), (54.45, 'hit', 0.5), (55.25, 'whoosh', 0.25),
    (55.6, 'pop', 0.4), (55.96, 'cash', 0.35), (56.78, 'cash', 0.35),
    (57.35, 'whoosh', 0.55), (57.6, 'hit', 0.4), (60.1, 'hit', 0.55), (60.75, 'hit', 0.55),
    (61.6, 'whoosh', 0.5), (62.3, 'ping', 0.3), (62.7, 'ping', 0.25), (63.2, 'whoosh', 0.25), (63.95, 'boom', 0.7), (64.8, 'hit', 0.6),
    (65.75, 'whoosh', 0.55), (66.0, 'hit', 0.5), (66.9, 'pop', 0.45), (68.4, 'pop', 0.45), (69.85, 'pop', 0.4),
    (71.55, 'whoosh', 0.6), (71.75, 'sonar', 0.3),
]
# counter ticks
for k in range(14):
    EVENTS.append((43.3 + k * 0.12, 'tick', 0.25))
    EVENTS.append((62.4 + k * 0.11, 'tick', 0.25))

def build(total):
    out = np.zeros((int(total * SR) + SR * 3, 2))
    cache = {}
    for (t, kind, g) in EVENTS:
        if kind not in cache:
            cache[kind] = GEN[kind]()
        s = cache[kind]
        pan = rng.uniform(-0.25, 0.25)
        i = int(t * SR)
        L = min(len(s), len(out) - i)
        out[i:i + L, 0] += s[:L] * g * (1 - pan)
        out[i:i + L, 1] += s[:L] * g * (1 + pan)
    out = out[:int(total * SR)]
    out = np.tanh(out * 1.1) * 0.9
    return out

if __name__ == '__main__':
    total = float(sys.argv[2])
    a = build(total)
    with wave.open(sys.argv[1], 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    print('ok', a.shape)
