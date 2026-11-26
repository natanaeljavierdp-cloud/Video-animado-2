# Musica y efectos sintetizados aqui mismo (libres de derechos) + mezcla con la voz.
import numpy as np, subprocess, wave
SR = 44100; DUR = 71.24; N = int(SR * DUR)
rng = np.random.default_rng(7)
def tone(f, d, dec=3.0, harm=(1, .35, .12)):
    t = np.arange(int(SR * d)) / SR
    y = sum(a * np.sin(2 * np.pi * f * (k + 1) * t) for k, a in enumerate(harm))
    env = np.exp(-dec * t) * np.minimum(1, t / 0.005)
    return y * env
def add(buf, x, at, g=1.0):
    i = int(at * SR); j = min(N, i + len(x))
    if j > i: buf[i:j] += g * x[:j - i]
def midi(n): return 440 * 2 ** ((n - 69) / 12)
def lp(x, a):  # filtro paso bajo simple de un polo
    y = np.empty_like(x); acc = 0.0
    import scipy.signal as ss
    return ss.lfilter([a], [1, a - 1], x)

# ---- musica: I-V-vi-IV en Do, 104 bpm
mus = np.zeros(N); beat = 60 / 104
chords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
patt = [0, 2, 1, 2, 0, 2, 1, 2]
t = 0.0; bar = 0
while t < DUR:
    ch = chords[bar % 4]
    add(mus, tone(midi(ch[0] - 24), beat * 4, dec=1.2, harm=(1, .2)), t, 0.35)  # bajo
    for k in range(8):
        n = ch[patt[k]] + 12
        add(mus, tone(midi(n), 0.6, dec=6, harm=(1, .25, .05)), t + k * beat / 2, 0.16)
    if bar % 2 == 1:  # melodia sencilla
        mel = [ch[2] + 12, ch[1] + 12, ch[0] + 24, ch[2] + 12]
        for k, n in enumerate(mel):
            add(mus, tone(midi(n), 0.9, dec=3.5, harm=(1, .1)), t + k * beat, 0.10)
    for k in range(8):  # shaker
        sh = rng.standard_normal(int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / SR * 90)
        add(mus, sh, t + k * beat / 2 + beat / 4, 0.025)
    t += beat * 4; bar += 1
fade = np.minimum(1, np.arange(N) / SR / 1.5) * np.minimum(1, (DUR - np.arange(N) / SR) / 2.0)
mus *= fade

# ---- efectos
fx = np.zeros(N)
import scipy.signal as ss
def whoosh(at, d=1.3, g=0.5):
    n = int(SR * d); x = rng.standard_normal(n)
    tt = np.arange(n) / n
    out = np.zeros(n)
    for k in range(0, n, 2048):  # banda que sube y baja
        f = 300 + 2500 * np.sin(np.pi * tt[k])
        b, a = ss.butter(2, [f * 0.7 / (SR / 2), min(0.99, f * 1.4 / (SR / 2))], 'band')
        seg = x[max(0, k - 512):k + 2048]
        y = ss.lfilter(b, a, seg)[-min(2048, n - k):]
        out[k:k + len(y)] = y
    env = np.sin(np.pi * tt) ** 2
    add(fx, out * env / (np.abs(out).max() + 1e-9), at, g)
whoosh(6.95, 1.5, 0.45); whoosh(14.15, 1.2, 0.22); whoosh(30.35, 0.8, 0.18)
def click(at, g=0.5):
    n = int(0.03 * SR); tt = np.arange(n) / SR
    y = (rng.standard_normal(n) * 0.5 + np.sin(2 * np.pi * 2400 * tt)) * np.exp(-tt * 250)
    add(fx, y, at, g); add(fx, y * 0.5, at + 0.04, g)
click(58.2); click(60.4)
def pop(at, g=0.55):
    n = int(0.18 * SR); tt = np.arange(n) / SR
    f = 900 * np.exp(-tt * 18) + 180
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 22)
    add(fx, y, at, g)
pop(63.85); pop(68.78)
# zumbido del compresor
tt = np.arange(N) / SR
hum = (np.sin(2 * np.pi * 100 * tt) + 0.5 * np.sin(2 * np.pi * 200 * tt + 1) + 0.25 * np.sin(2 * np.pi * 300 * tt)) * (1 + 0.15 * np.sin(2 * np.pi * 6 * tt))
def ramp(a, b, w=0.3):
    return np.clip((tt - a) / w, 0, 1) * np.clip((b - tt) / w, 0, 1)
lvl = (0.10 * ramp(24.4, 30.4) + 0.22 * ramp(30.2, 35.4) + 0.06 * ramp(35.2, 54.2) + 0.12 * ramp(54.0, 58.25, 0.08)
       + 0.22 * ramp(60.4, 63.8, 0.08))
fx += hum * lvl * 0.5

# ---- voz y mezcla
raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', 'voz.mp3', '-ar', str(SR), '-ac', '1', '-f', 'f32le', '-'], capture_output=True).stdout
voz = np.frombuffer(raw, np.float32).astype(np.float64)[:N]
voz = np.pad(voz, (0, N - len(voz)))
voz /= np.abs(voz).max() + 1e-9
mix = 0.9 * voz + 0.16 * mus / (np.abs(mus).max() + 1e-9) + 0.5 * fx
mix /= max(1.0, np.abs(mix).max() / 0.98)
pcm = (mix * 32767).astype(np.int16)
with wave.open('mezcla.wav', 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok', len(pcm) / SR)
