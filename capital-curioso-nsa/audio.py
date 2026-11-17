import numpy as np, json, sys
from scipy import signal
from scipy.io import wavfile
from timeline import *
SR = 48000
N = int(DUR * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)

def lp(x, f, o=4): return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, a, b, o=2): return signal.sosfilt(signal.butter(o, [a, b], 'band', fs=SR, output='sos'), x)
def env_curve(points):
    xs, ys = zip(*points); return np.interp(t, xs, ys)

def reverb(x, rt=2.0, mix=0.35, seed=1):
    r = np.random.default_rng(seed); L = int(rt * SR); tt = np.arange(L) / SR
    out = []
    for ch in range(2):
        ir = r.standard_normal(L) * np.exp(-6.9 * tt / rt); ir = lp(ir, 5000); ir /= np.sqrt((ir**2).sum())
        out.append(signal.fftconvolve(x, ir)[:len(x)])
    wet = np.stack(out, 1)
    return np.stack([x, x], 1) * (1 - mix) + wet * mix

def place(buf, snd, at, gain=1.0):
    i = int(at * SR); j = min(len(buf), i + len(snd))
    if j > i: buf[i:j] += snd[:j - i] * gain

# ---------------- MÚSICA ----------------
# curva de intensidad
I = env_curve([(0, 0), (2.5, 0.05), (8, 0.22), (16, 0.35), (29, 0.5), (41, 0.62), (46, 0.55),
               (58, 0.72), (66.5, 0.95), (69, 0.8), (79.5, 1.0), (82, 0.45), (85, 0.15), (88.3, 0.05), (90, 0)])

def saw_voice(freq, detunes=(-0.12, -0.05, 0, 0.06, 0.13), vib=0.004, seed=0):
    r = np.random.default_rng(seed); s = np.zeros(N)
    for d in detunes:
        f = freq * 2 ** (d / 12) * (1 + vib * np.sin(2 * np.pi * (5 + r.random()) * t + r.random() * 6))
        ph = np.cumsum(f) / SR + r.random()
        s += 2 * (ph % 1) - 1
    return s / len(detunes)

# cuerdas graves sostenidas
low = (saw_voice(73.42, seed=1) + 0.8 * saw_voice(110.0, seed=2) + 0.6 * saw_voice(146.83, seed=3))
low = lp(low, 900) * env_curve([(0, 0), (6.6, 0), (9, 1), (90, 1)])
# disonancia (Eb3) entra más tarde
dis = lp(saw_voice(155.56, seed=4), 1100) * env_curve([(0, 0), (29, 0), (33, 0.7), (58, 0.8), (66, 1), (90, 1)])
# cuerdas agudas tensas en trémolo (D5 + Eb5)
trem = np.abs(np.sin(2 * np.pi * 5.5 * t)) ** 0.6
hi = (saw_voice(587.33, seed=5) + 0.8 * saw_voice(622.25, seed=6))
hi = bp(hi, 400, 4000) * trem * env_curve([(0, 0), (16, 0), (22, 0.35), (41, 0.6), (46, 0.5), (66, 1), (80, 1), (84, 0)])
# glissando ascendente de tensión (58–67 s)
gl_f = np.interp(t, [58, 67], [440, 880]); gl_ph = np.cumsum(gl_f) / SR
gl = (2 * (gl_ph % 1) - 1 + 2 * ((gl_ph * 1.006) % 1) - 1) * 0.5
gl = bp(gl, 300, 3500) * env_curve([(0, 0), (58, 0), (62, 0.5), (66.4, 0.9), (66.6, 0), (90, 0)])
# segundo ascenso 69–80
gl2_f = np.interp(t, [69, 80], [330, 740]); gl2_ph = np.cumsum(gl2_f) / SR
gl2 = bp(2 * (gl2_ph % 1) - 1, 300, 3500) * env_curve([(0, 0), (69, 0), (74, 0.4), (79.8, 0.85), (80.2, 0), (90, 0)])
# sub drone
sub = np.sin(2 * np.pi * 36.71 * t) * env_curve([(0, 0), (3, 0.3), (8, 0.6), (90, 0.6)])

strings = 0.32 * low + 0.22 * dis + 0.16 * hi + 0.14 * gl + 0.12 * gl2
music = strings * (0.25 + 0.75 * I) + 0.35 * sub * (0.4 + 0.6 * I)

# latido (lub-dub) que acelera
beat = np.zeros(N)
def thump(f0, dur=0.32, amp=1.0):
    tt = np.arange(int(dur * SR)) / SR
    f = f0 * (1 + 1.2 * np.exp(-tt / 0.02)); ph = 2 * np.pi * np.cumsum(f) / SR
    return amp * np.sin(ph) * np.exp(-tt / 0.09) * (1 - np.exp(-tt / 0.003))
bt = 3.0
while bt < 88.0:
    bpm = np.interp(bt, [3, 41, 46, 80, 85, 88], [56, 72, 66, 98, 70, 60])
    a = 0.55 + 0.45 * np.interp(bt, t[::SR // 10], I[::SR // 10])
    place(beat, thump(52), bt, a); place(beat, thump(46, amp=0.7), bt + 0.27, a)
    bt += 60 / bpm
beat = lp(beat, 180)

# ---------------- EFECTOS ----------------
sfx = np.zeros(N)
def boom(amp=1.0):
    L = int(3.2 * SR); tt = np.arange(L) / SR
    f = 30 + 70 * np.exp(-tt / 0.25); ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-tt / 0.9)
    nz = lp(rng.standard_normal(L), 300) * np.exp(-tt / 0.18) * 0.8
    click = hp(rng.standard_normal(L), 1500) * np.exp(-tt / 0.008) * 0.25
    return amp * (body + nz + click)
for at, a in BOOMS: place(sfx, boom(a), at - 0.02, 1.0)

def glitch_snd(d, amp):
    L = int(d * SR); s = np.zeros(L); i = 0
    while i < L:
        seg = int(rng.uniform(0.012, 0.05) * SR); tt = np.arange(seg) / SR
        k = rng.integers(4)
        if k == 0: x = np.sign(np.sin(2 * np.pi * rng.uniform(200, 2500) * tt))
        elif k == 1: x = np.repeat(rng.uniform(-1, 1, seg // 20 + 1), 20)[:seg]
        elif k == 2: x = rng.standard_normal(seg)
        else: x = np.zeros(seg)
        s[i:i + seg] = x[:len(s[i:i + seg])]; i += seg
    s = np.round(s * 4) / 4
    return amp * 0.5 * s * np.minimum(1, np.linspace(0, 40, L)) * np.minimum(1, np.linspace(40, 0, L))
for at, d, a in GLITCHES: place(sfx, glitch_snd(d, a), at, 0.55)

def err_snd():
    out = []
    for f in (880, 587):
        tt = np.arange(int(0.11 * SR)) / SR
        out.append(signal.square(2 * np.pi * f * tt, 0.3) * np.exp(-tt / 0.09))
    return lp(np.concatenate(out), 3500)
for at in ERRORS: place(sfx, err_snd(), at, 0.22)

def stamp_snd():
    L = int(0.5 * SR); tt = np.arange(L) / SR
    return lp(rng.standard_normal(L), 500) * np.exp(-tt / 0.05) + np.sin(2 * np.pi * 70 * tt) * np.exp(-tt / 0.12)
for at in STAMPS: place(sfx, stamp_snd(), at, 0.8)

# máquina de escribir: "17 NOV 2026" = 11 caracteres
a, b = TYPE_T
for k in range(11):
    L = int(0.06 * SR); tt = np.arange(L) / SR
    click = hp(rng.standard_normal(L), 2500) * np.exp(-tt / 0.006) + 0.5 * lp(rng.standard_normal(L), 300) * np.exp(-tt / 0.02)
    if k not in (2, 6): place(sfx, click, a + (b - a) * k / 10, 0.35)
place(sfx, (lambda tt: np.sin(2*np.pi*2200*tt)*np.exp(-tt/0.25))(np.arange(int(0.6*SR))/SR), b + 0.12, 0.12)  # campanita

# estática
for s0, s1, a in STATIC:
    L = int((s1 - s0) * SR); x = bp(rng.standard_normal(L), 900, 7000)
    crack = (rng.random(L) > 0.9993) * rng.standard_normal(L) * 6
    e = np.minimum(1, np.minimum(np.arange(L), L - np.arange(L)) / (0.08 * SR))
    place(sfx, (x * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * np.arange(L) / SR)) + crack) * e, s0, 0.09 * a)

# alarma lejana (filtrada y con mucha reverberación)
alarm = np.zeros(N)
for s0, s1 in ALARMS:
    L = int((s1 - s0) * SR); tt = np.arange(L) / SR
    f = 640 + 180 * np.sin(2 * np.pi * 0.42 * tt); ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.3 * np.sin(2 * ph)
    e = np.minimum(1, np.minimum(tt, (s1 - s0) - tt) / 1.5)
    place(alarm, lp(x, 1200) * e, s0, 1.0)

# golpe y cola para el cierre
place(sfx, boom(0.5), CIERRE_T, 0.6)

# ---------------- MEZCLA ----------------
gate = np.ones(N)
for s0, s1 in SILENCES:
    gate *= 1 - np.clip(np.minimum((t - s0) / 0.03, (s1 - t) / 0.02), 0, 1)
m_off = 1 - np.clip(np.minimum((t - MUSIC_OFF[0]) / 0.05, (MUSIC_OFF[1] - t) / 0.05), 0, 1)

music_st = reverb(music * 0.5, 2.6, 0.45, 1)
alarm_st = reverb(alarm * 0.05, 3.0, 0.85, 2)
sfx_st = reverb(sfx, 1.6, 0.25, 3)
beat_st = np.stack([beat, beat], 1)
beat_gain = np.where(m_off < 0.5, 0.5, 1.0)[:, None]

bed = (music_st * m_off[:, None] * 0.4 + alarm_st * m_off[:, None] + beat_st * 0.55 * beat_gain + sfx_st * 0.7)
bed *= gate[:, None]
sr_n, narr = wavfile.read(sys.argv[1]); narr = narr.astype(np.float64) / 32768
narr = np.pad(narr, ((0, max(0, N - len(narr))), (0, 0)))[:N]
narr /= np.abs(narr).max()
mix = narr * 0.9 + bed * 0.5
mix /= max(1.0, np.abs(mix).max() / 0.98)
wavfile.write(sys.argv[2], SR, (mix * 32767).astype(np.int16))
wavfile.write(sys.argv[3], SR, (np.clip(bed * 0.5, -1, 1) * 32767).astype(np.int16))
print('ok', np.abs(bed).max())
