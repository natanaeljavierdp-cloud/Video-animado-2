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
    t = np.arange(N) / SR
    out = np.zeros((N, 2))
    A1 = 55.0
    # Dron grave (La) con LFO lento
    drone = (np.sin(2 * np.pi * A1 * t) * .5 + np.sin(2 * np.pi * A1 * 1.5 * t + .3) * .25 + np.sin(2 * np.pi * A1 * 2 * t) * .18)
    drone *= .7 + .3 * np.sin(2 * np.pi * .07 * t)
    out += st(drone * .55)
    # Aire / textura
    air = bp(rng.standard_normal((N, 2)), 300, 1600) * (.5 + .5 * np.sin(2 * np.pi * .05 * t))[:, None]
    out += air * .06
    # Pads por acordes (La m – Fa – Re m – Mi), 8 s cada uno
    chords = [[220, 261.63, 329.63], [174.61, 220, 261.63], [146.83, 174.61, 220], [164.81, 207.65, 246.94]]
    pad = np.zeros(N)
    seg = 8.0
    for i in range(int(DUR / seg) + 1):
        ch = chords[i % 4]
        s0, s1 = int(i * seg * SR), min(N, int((i + 1) * seg * SR + SR))
        if s0 >= N: break
        tt = np.arange(s1 - s0) / SR
        e = np.clip(tt / 2.5, 0, 1) * np.clip((seg + 1 - tt) / 1.5, 0, 1)
        sig = np.zeros(len(tt))
        for f in ch:
            for det in (-.6, .6):
                ph = 2 * np.pi * (f + det) * tt
                sig += sum(np.sin(ph * h) / h for h in range(1, 6))
        pad[s0:s1] += sig * e
    pad = lp(pad, 1400)
    out += reverb(norm(pad, .25), .5)
    # Pulso tipo latido (90 bpm)
    beat = 60 / 90
    k = np.zeros(N)
    thump = impact(.5, 80, 45, click=False)[:, 0]
    for b in np.arange(0, DUR, beat * 2):
        for off, g in ((0, 1.0), (beat * .45, .6)):
            i = int((b + off) * SR)
            j = min(N, i + len(thump)); k[i:j] += thump[:j - i] * g
    out += st(lp(k, 300) * .35)
    # Ostinato agudo (corcheas)
    arp = np.zeros(N)
    notes = [440, 523.25, 659.25, 523.25]
    for n_i, b in enumerate(np.arange(0, DUR, beat / 2)):
        f = notes[n_i % 4] * (1 if (n_i // 16) % 2 == 0 else 349.23 / 440 * (440 / 440))
        tt = tvec(.35); y = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 12) + np.sin(2 * np.pi * f * 2 * tt) * np.exp(-tt * 20) * .3
        i = int(b * SR); j = min(N, i + len(y)); arp[i:j] += y[:j - i]
    out += reverb(st(arp * .06, .2), .45)
    # Reloj (tic) hasta la pregunta
    for b in np.arange(0, 55, beat):
        place(out, tick(3200, .03) * .18, b)

    # Automatización: caída en los apagones, más energía en la pregunta y el cierre
    g = np.ones(N)
    def ramp(a, b, v0, v1):
        i, j = int(a * SR), int(b * SR); g[i:j] = np.linspace(v0, v1, j - i)
    ramp(2.78, 2.80, 1, .05); ramp(2.80, 3.6, .05, .05); ramp(3.6, 4.4, .05, 1)
    ramp(9.26, 9.28, 1, .1); ramp(9.28, 9.8, .1, .1); ramp(9.8, 10.5, .1, 1)
    ramp(54.9, 62.8, 1.0, 1.25)
    g[int(62.8 * SR):] = 1.25
    ramp(65.6, 67.0, 1.25, 0)
    out *= g[:, None]
    out[:int(.5 * SR)] *= np.linspace(0, 1, int(.5 * SR))[:, None]
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
        "[1:a]volume=-16dB[m];"
        "[m][vsc]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=500[md];"
        "[2:a]volume=-9dB[s];"
        "[v][md][s]amix=inputs=3:normalize=0:duration=longest,"
        "loudnorm=I=-14:TP=-1.0:LRA=11,aresample=44100[out]"
    )
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', 'assets/narracion.mp3', '-i', f'{OUT}/music.wav', '-i', f'{OUT}/sfx.wav',
                    '-filter_complex', fc, '-map', '[out]', '-t', str(DUR), '-ar', '44100', f'{OUT}/mix.wav'], check=True)
    print('ok')
