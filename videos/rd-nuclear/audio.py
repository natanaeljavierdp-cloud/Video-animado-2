"""Genera la música de suspenso y los efectos de sonido (sintetizados, sin licencias)
y mezcla todo con la narración.  Salida: build/mix.wav

Uso: python3 audio.py
"""
import os, subprocess
import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt

SR = 44100
DUR = 67.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
OUT = 'build'
os.makedirs(OUT, exist_ok=True)


def tvec(d): return np.arange(int(SR * d)) / SR
def db(x): return 10 ** (x / 20)
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x, axis=0)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x, axis=0)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x, axis=0)
def norm(x, peak=1.0): m = np.max(np.abs(x)); return x * (peak / m) if m > 0 else x


def sweep_filter(x, f0, f1, kind='band', q=.25, block=512):
    """Filtro que barre su frecuencia (whoosh). Procesa en bloques."""
    y = np.zeros_like(x); n = len(x); zi = None
    for i in range(0, n, block):
        k = i / max(1, n - 1)
        f = f0 * (f1 / f0) ** k
        if kind == 'band':
            sos = butter(2, [max(30, f * (1 - q)), min(SR / 2 - 100, f * (1 + q))], 'band', fs=SR, output='sos')
        else:
            sos = butter(2, min(SR / 2 - 100, f), kind, fs=SR, output='sos')
        if zi is None or zi.shape[0] != sos.shape[0]:
            zi = np.zeros((sos.shape[0], 2))
        y[i:i + block], zi = sosfilt(sos, x[i:i + block], zi=zi)
    return y


def make_ir(dur=2.2, decay=3.0):
    t = tvec(dur)
    ir = rng.standard_normal((len(t), 2)) * np.exp(-decay * t)[:, None]
    ir = lp(ir, 6000)
    ir[0] += 1.0
    return ir / np.sqrt(np.sum(ir ** 2))


IR = make_ir()
IR_SHORT = make_ir(1.0, 6.0)


def reverb(x, wet=.35, ir=IR):
    if x.ndim == 1: x = np.stack([x, x], 1)
    w = np.stack([fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], 1)
    return x * (1 - wet) + w * wet * 2.5


def st(x, pan=0.0):
    if x.ndim == 2: return x
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    return np.stack([x * l, x * r], 1) * 1.41


def place(bus, x, t0, gain_db=0.0):
    x = st(x) * db(gain_db)
    i = int(t0 * SR)
    if i >= len(bus): return
    j = min(len(bus), i + len(x))
    bus[i:j] += x[:j - i]


# ---------------------------------------------------------------- EFECTOS
def whoosh(d=.7, f0=300, f1=4000, rev=True):
    n = rng.standard_normal(int(SR * d))
    y = sweep_filter(n, f0, f1, 'band', .35)
    t = tvec(d); e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.6
    y = norm(y * e, .8)
    # paneo de izquierda a derecha
    pan = np.linspace(-.6, .6, len(y))
    s = np.stack([y * np.cos((pan + 1) * np.pi / 4), y * np.sin((pan + 1) * np.pi / 4)], 1) * 1.41
    return reverb(s, .25, IR_SHORT) if rev else s


def impact(d=2.2, f0=110, f1=38, click=True):
    t = tvec(d)
    f = f1 + (f0 - f1) * np.exp(-t * 9)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(ph) * np.exp(-t * 2.4)
    body = lp(rng.standard_normal(len(t)), 900) * np.exp(-t * 14) * .9
    y = sub + body
    if click: y[:200] += rng.standard_normal(200) * np.linspace(1, 0, 200) * .8
    y = np.tanh(y * 1.6)
    return reverb(norm(y, .95), .3)


def powerdown(d=1.6):
    t = tvec(d)
    f = 520 * np.exp(-t * 2.6) + 28
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = 2 * ((ph / (2 * np.pi)) % 1) - 1
    y = lp(saw, 2500) * np.exp(-t * 1.6) * .7
    hum = np.sign(np.sin(2 * np.pi * 60 * t)) * .25 * np.exp(-t * 4)
    crack = (rng.random(len(t)) > .9985) * rng.standard_normal(len(t)) * 2.5 * np.exp(-t * 3)
    y = y + lp(hum, 1500) + hp(crack, 1500)
    y[:int(.03 * SR)] += impact(1.0, 90, 40)[:int(.03 * SR), 0]
    return reverb(norm(y, .9), .3)


def buzz(d=.45):
    t = tvec(d)
    hum = np.sign(np.sin(2 * np.pi * 120 * t)) * .5 + np.sin(2 * np.pi * 240 * t) * .3
    gate = np.repeat((rng.random(int(d * 30) + 1) > .45).astype(float), int(SR / 30) + 1)[:len(t)]
    y = lp(hum, 3000) * gate + hp(rng.standard_normal(len(t)), 3000) * gate * .25
    return norm(y, .6)


def tick(f=2600, d=.04):
    t = tvec(d); return np.sin(2 * np.pi * f * t) * np.exp(-t * 160) * .7


def pop(d=.16, f0=380, f1=980):
    t = tvec(d); f = f0 + (f1 - f0) * np.clip(t / .06, 0, 1)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 28)
    return reverb(y * .8, .2, IR_SHORT)


def zip_line(d=1.2):
    t = tvec(d)
    f = 300 * (8 ** (t / d))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * .25
    n = sweep_filter(rng.standard_normal(len(t)), 500, 6000, 'band', .3)
    e = np.clip(t / d, 0, 1) ** 1.5 * np.exp(-np.clip(t - d * .9, 0, None) * 30)
    return reverb(norm((tone + norm(n, .6)) * e, .6), .3)


def scribble(d=1.4):
    t = tvec(d)
    n = bp(rng.standard_normal(len(t)), 1800, 6000)
    env = np.abs(np.sin(2 * np.pi * 7.5 * t + np.sin(2 * np.pi * 2.3 * t) * 2)) ** 2
    return norm(n * env * np.minimum(1, (d - t) * 8), .35)


def ding(d=1.6):
    t = tvec(d)
    y = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * k) for f, a, k in [(1318.5, .6, 3), (1975.5, .35, 4), (2637, .2, 6), (659.25, .25, 2.5)])
    return reverb(y * .7, .35)


def zap(d=.6):
    t = tvec(d)
    crack = (rng.random(len(t)) > .992) * rng.standard_normal(len(t)) * 3
    hum = np.sin(2 * np.pi * 180 * t + 3 * np.sin(2 * np.pi * 37 * t)) * .3
    y = hp(lp(crack, 9000), 800) + hum
    return reverb(norm(y * np.exp(-t * 5), .7), .25, IR_SHORT)


def riser(d=2.0):
    t = tvec(d)
    n = sweep_filter(rng.standard_normal(len(t)), 200, 9000, 'band', .4)
    tone = sum(np.sin(2 * np.pi * np.cumsum(f0 * (2 ** (t / d * 1.0))) / SR) for f0 in (220, 330.0, 440))
    e = (t / d) ** 2.2
    return reverb(norm(norm(n, .7) * e + tone * .12 * e, .7), .4)


def stamp():
    y = impact(1.8, 140, 45)
    t = tvec(.25)
    paper = bp(rng.standard_normal(len(t)), 800, 5000) * np.exp(-t * 25)
    y[:len(t)] += st(paper * .8)
    return y


def sting(d=3.5):
    t = tvec(d)
    freqs = [220, 277.18, 329.63, 440, 554.37, 659.25, 880, 1108.7]
    y = sum(np.sin(2 * np.pi * f * t + rng.random() * 6) * np.exp(-t * (1.2 + i * .15)) * (1 / (1 + i * .3)) for i, f in enumerate(freqs))
    shimmer = hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * 2.5) * .15
    return reverb(norm(y + shimmer, .7), .45)


# ---------------------------------------------------------------- MÚSICA
def music():
    """Banda sonora cinematográfica: cuerdas en staccato, taikos, 'braams' graves y trémolo agudo.
    90 bpm, La menor (Am – F – Dm – E, un acorde cada 2 compases)."""
    t = np.arange(N) / SR
    out = np.zeros((N, 2))
    beat = 60 / 90; bar = beat * 4; s16 = beat / 4
    prog = [(110.0, [0, 3, 7]), (87.31, [0, 4, 7]), (73.42, [0, 3, 7]), (82.41, [0, 4, 7])]  # Am F Dm E
    def chord_at(x): return prog[int(x // (bar * 2)) % 4]

    # Curva de intensidad por secciones (sigue la historia)
    pts = [(0, .45), (2.75, .5), (2.8, 0), (3.6, 0), (4.0, .6), (7.3, .7), (9.25, .75), (9.3, 0), (9.8, 0), (10.3, .7),
           (15.5, .8), (18.0, .8), (28.1, .85), (28.2, .9), (37.5, .95), (37.6, 1.0), (41.1, 1.0), (41.2, .35),
           (47.4, .4), (47.42, .9), (53.5, .95), (54.9, 1.0), (62.7, 1.0), (62.9, 0), (DUR, 0)]
    xs, ys = zip(*pts)
    I = np.interp(t, xs, ys)

    # 1) Sub-dron
    drone = np.sin(2 * np.pi * 55 * t) * .6 + np.sin(2 * np.pi * 82.41 * t) * .2
    out += st(drone * (.35 + .25 * np.sin(2 * np.pi * .05 * t) ** 2) * .5)

    # 2) Cuerdas staccato (semicorcheas)
    pat = [0, 0, 12, 0, 7, 0, 12, 0, 3, 0, 12, 0, 7, 0, 15, 12]
    acc = [1, .55, .7, .55, .85, .55, .7, .55, 1, .55, .7, .55, .85, .55, .75, .65]
    nl = int(.16 * SR); tt = np.arange(nl) / SR
    osti = np.zeros(N)
    for k, x in enumerate(np.arange(0, DUR, s16)):
        root, ch = chord_at(x)
        semis = pat[k % 16]
        if semis in (3, 15) and ch[1] == 4: semis += 1      # tercera mayor en F y E
        f = root * 2 ** (semis / 12)
        ph = 2 * np.pi * f * tt
        saw = sum(np.sin(ph * h) / h for h in range(1, 9))
        note = saw * np.exp(-tt * 22) * np.minimum(1, tt / .004)
        i = int(x * SR); j = min(N, i + nl)
        osti[i:j] += note[:j - i] * acc[k % 16] * I[i]
    osti = lp(osti, 2600)
    out += reverb(np.stack([osti * .9, np.roll(osti, 400) * .9], 1), .3) * .32

    # 3) Trémolo agudo de cuerdas (tensión)
    trem = np.zeros(N)
    for c in range(int(DUR / (bar * 2)) + 1):
        x0 = c * bar * 2; root, ch = prog[c % 4]
        i, j = int(x0 * SR), min(N, int((x0 + bar * 2 + .5) * SR))
        if i >= N: break
        tt2 = np.arange(j - i) / SR
        sig = sum(sum(np.sin(2 * np.pi * root * 4 * 2 ** (iv / 12) * (1 + d) * tt2 * h) / h for h in range(1, 5)) for iv in ch for d in (-.002, .002))
        e = np.clip(tt2 / 1.2, 0, 1) * np.clip((bar * 2 + .5 - tt2) / .5, 0, 1)
        trem[i:j] += sig * e
    trem *= .55 + .45 * np.sin(2 * np.pi * 12 * t)
    trem = lp(hp(trem, 400), 5000) * (.35 + .65 * I)
    out += reverb(norm(trem, .12), .55)

    # 4) Taikos
    def taiko(d=1.0, f0=95, f1=48):
        x = tvec(d); f = f1 + (f0 - f1) * np.exp(-x * 18)
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 5.5)
        y += lp(rng.standard_normal(len(x)), 1200) * np.exp(-x * 30) * .5
        return np.tanh(y * 1.4)
    tk = taiko(); tk2 = taiko(.6, 150, 80)
    drums = np.zeros((N, 2))
    for b0 in np.arange(0, DUR, bar):
        for e8, g, kind in ((0, 1, 0), (3, .7, 0), (6, .8, 0), (7, .45, 1)):
            x = b0 + e8 * beat / 2; i = int(x * SR)
            if i >= N or I[i] < .55: continue
            place(drums, (tk if kind == 0 else tk2) * g * I[i], x)
    # redoble hacia la pregunta y hacia el choque de potencias
    for a0, a1 in ((53.6, 54.9), (36.3, 37.6)):
        for k, x in enumerate(np.arange(a0, a1, s16)):
            place(drums, tk2 * (.3 + .7 * (x - a0) / (a1 - a0)), x)
    out += reverb(drums, .3) * .55

    # 5) "Braams" graves en los momentos clave
    def braam(d=3.2):
        x = tvec(d)
        sig = sum(sum(np.sin(2 * np.pi * f * (1 + dt) * x * h) / h for h in range(1, 12)) for f in (55, 110, 82.41, 65.41) for dt in (-.004, .004))
        y = np.zeros(len(x)); blk = 1024
        for i in range(0, len(x), blk):
            k = i / len(x); fc = 250 + 1700 * np.sin(np.pi * min(1, k * 1.6)) ** 2
            y[i:i + blk] = sig[i:i + blk]
        y = sweep_filter(y, 1600, 220, 'low')
        e = np.minimum(1, x / .06) * np.exp(-x * .9)
        return reverb(norm(np.tanh(y * e * .5), .9), .45)
    br = braam()
    for x, g in ((0.0, .8), (7.3, .7), (15.5, .75), (28.15, .9), (37.6, 1.0), (47.42, 1.0), (54.9, .9)):
        place(out, br * g * .55, x)

    # Fundidos
    out[:int(.3 * SR)] *= np.linspace(0, 1, int(.3 * SR))[:, None]
    fo0 = int(62.85 * SR); out[fo0:] *= np.exp(-np.arange(N - fo0) / SR * 1.2)[:, None]
    return out


def sfx():
    bus = np.zeros((N, 2))
    P = lambda x, t0, g=0: place(bus, x, t0, g)
    P(impact(), 0.0, -4)
    P(whoosh(.8), 0.05, -8)
    P(buzz(.5), 2.42, -10)
    P(powerdown(), 2.72, -2)
    for i in range(14):                       # contador 0 → 11,000,000
        P(tick(2200 + i * 40), 4.05 + i * (1.85 / 14) * (1 + i / 30), -10)
    P(impact(1.6, 120, 45), 5.92, -6)
    P(whoosh(.6), 7.0, -7)
    for i in range(10):
        P(tick(2600), 7.38 + i * .075, -12)
    P(impact(1.4, 120, 50), 8.12, -8)
    P(buzz(.4), 9.18, -10)
    P(powerdown(1.2), 9.24, -5)
    P(whoosh(.7, 200, 2500), 12.45, -8)
    P(scribble(1.4), 13.27, -9)
    P(pop(.2, 300, 700), 14.6, -6)
    P(impact(1.8, 100, 40), 15.5, -7)
    P(ding(), 15.55, -14)
    P(whoosh(.8), 17.7, -7)
    P(zip_line(1.15), 18.45, -9)
    P(pop(), 19.4, -9)
    P(impact(1.4, 110, 45), 19.5, -9)
    P(whoosh(.5, 600, 5000), 20.8, -13)
    P(whoosh(.6), 23.85, -8)
    P(pop(), 24.36, -6)
    P(whoosh(.5, 800, 5000, False), 26.3, -15)
    P(zap(), 27.0, -7)
    P(pop(.16, 500, 1200), 27.02, -8)
    P(whoosh(.9, 150, 1800), 27.85, -6)
    P(impact(2.0, 90, 35), 28.15, -6)
    P(whoosh(1.8, 150, 2500), 28.95, -10)
    P(impact(1.4, 110, 45), 29.8, -8)
    P(zip_line(2.6), 31.2, -10)
    P(pop(), 34.95, -9)
    P(whoosh(.5, 600, 5000), 35.7, -11)
    P(impact(1.4, 110, 45), 35.75, -10)
    P(whoosh(.7), 37.35, -6)
    P(impact(2.2, 120, 38), 37.6, -3)
    P(pop(.16, 300, 800), 37.9, -8)
    P(impact(1.4, 100, 40), 38.9, -9)
    P(whoosh(.7), 40.95, -7)
    P(pop(), 41.3, -7)
    P(whoosh(.6, 500, 4000), 43.15, -11)
    P(stamp(), 47.42, -1)
    P(whoosh(.6), 49.05, -9)
    P(whoosh(.5, 600, 5000), 49.55, -14)
    P(pop(), 51.0, -8)
    P(ding(), 51.56, -9)
    P(riser(2.0), 52.95, -11)
    P(impact(2.2, 100, 38), 54.92, -5)
    P(pop(), 56.05, -10)
    for i, tt in enumerate([57.3, 57.9, 58.5, 58.78]):
        P(pop(.12, 250 + i * 60, 600 + i * 80), tt, -12)
    P(pop(), 60.6, -9)
    P(pop(.2, 300, 900), 60.95, -5)
    P(pop(.2, 350, 1000), 61.95, -5)
    P(riser(1.3), 61.7, -13)
    P(whoosh(.8), 62.75, -6)
    P(impact(2.6, 100, 35), 62.95, -4)
    P(sting(), 63.75, -6)
    P(whoosh(.5, 800, 6000, False), 64.2, -16)
    return bus


def wav(path, x):
    x = np.clip(x, -1, 1)
    import wave
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    m = music(); wav(f'{OUT}/music.wav', norm(m, .9))
    s = sfx(); wav(f'{OUT}/sfx.wav', norm(s, .95))
    # Mezcla: voz al frente, música baja con ducking por la voz, efectos encima.
    fc = (
        "[0:a]aresample=44100,pan=stereo|c0=c0|c1=c0,highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,"
        "volume=1.0,asplit=2[v][vsc];"
        "[1:a]volume=-12dB[m];"
        "[m][vsc]sidechaincompress=threshold=0.04:ratio=4:attack=30:release=400[md];"
        "[2:a]volume=-9dB[s];"
        "[v][md][s]amix=inputs=3:normalize=0:duration=longest,"
        "loudnorm=I=-14:TP=-1.0:LRA=11,aresample=44100[out]"
    )
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', 'assets/narracion.mp3', '-i', f'{OUT}/music.wav', '-i', f'{OUT}/sfx.wav',
                    '-filter_complex', fc, '-map', '[out]', '-t', str(DUR), '-ar', '44100', f'{OUT}/mix.wav'], check=True)
    print('ok')
