"""Música de fondo y efectos de sonido sintetizados (100% propios, libres de derechos) + mezcla con la voz."""
import os
import subprocess
import sys
import numpy as np
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
SR = 48000
rng = np.random.default_rng(3)


def load_voice(path):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-ar', str(SR), '-ac', '1', '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def filt(x, kind, f):
    sos = butter(2, f, btype=kind, fs=SR, output='sos')
    return sosfilt(sos, x)


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def add(buf, t0, sig, gain=1.0):
    i = int(t0 * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i] * gain


def tone(freq, dur, decay=4.0, harm=((1, 1.0),)):
    t = np.arange(int(dur * SR)) / SR
    s = sum(a * np.sin(2 * np.pi * freq * h * t) for h, a in harm)
    return s * np.exp(-t * decay) * env_adsr(len(t), 0.004, 0.02)


def noise(dur):
    return rng.standard_normal(int(dur * SR))


# ------------------------------------------------------------------ música
def music(n):
    out = np.zeros(n)
    bpm = 96
    beat = 60 / bpm
    # progresión suave: Cmaj7 - Am7 - Fmaj7 - G6
    chords = [[48, 55, 59, 64, 67], [45, 52, 57, 60, 64], [41, 48, 53, 57, 64], [43, 50, 55, 59, 64]]
    mtof = lambda m: 440 * 2 ** ((m - 69) / 12)
    bar = 4 * beat
    total = n / SR
    k = 0
    tb = 0.0
    while tb < total:
        ch = chords[k % 4]
        dur = 2 * bar
        # pad
        tt = np.arange(int((dur + 1.5) * SR)) / SR
        pad = np.zeros_like(tt)
        for m in ch[1:]:
            f = mtof(m)
            pad += np.sin(2 * np.pi * f * tt) + 0.6 * np.sin(2 * np.pi * f * 1.003 * tt + 1) + 0.15 * np.sin(2 * np.pi * 2 * f * tt)
        pad *= env_adsr(len(tt), 1.2, 1.6) * 0.035
        add(out, tb, pad)
        # bajo suave
        for b in range(0, 8, 2):
            add(out, tb + b * beat, tone(mtof(ch[0] - 12 + 12), beat * 1.8, 2.5, ((1, 1), (2, .25))), 0.10)
        # arpegio tipo marimba
        pat = [0, 2, 1, 3, 2, 4, 3, 1]
        for st in range(16):
            m = ch[1 + pat[st % 8] % 4] + 12
            add(out, tb + st * beat / 2, tone(mtof(m), 0.6, 9, ((1, 1), (4, .18), (10, .04))), 0.05 * (0.8 + 0.2 * (st % 2 == 0)))
        tb += dur
        k += 1
    out = filt(out, 'lowpass', 5000)
    return out


# ------------------------------------------------------------------ efectos
def click(gain=1.0):
    s = tone(2400, 0.05, 90, ((1, 1), (1.7, .5))) + 0.5 * noise(0.05) * np.exp(-np.arange(int(.05 * SR)) / SR * 140)
    return s * gain


def whoosh(dur, f0=300, f1=2500, gain=1.0):
    x = noise(dur)
    n = len(x)
    # filtro pasabanda barrido aproximado por bloques
    out = np.zeros(n)
    blocks = 24
    for b in range(blocks):
        a, z = b * n // blocks, (b + 1) * n // blocks
        f = f0 + (f1 - f0) * (b / blocks)
        seg = filt(filt(x[max(0, a - 2000):z], 'lowpass', f * 1.5), 'highpass', f * 0.5)
        out[a:z] = seg[-(z - a):]
    e = np.sin(np.linspace(0, np.pi, n)) ** 2
    return out * e * gain


def flush(dur, gain=1.0):
    x = noise(dur)
    lo = filt(x, 'lowpass', 900)
    hi = filt(filt(x, 'highpass', 1500), 'lowpass', 5000) * 0.35
    n = len(x)
    t = np.arange(n) / SR
    e = np.minimum(1, t / 0.35) * np.exp(-np.maximum(0, t - 0.8) * 0.9)
    mod = 1 + 0.25 * np.sin(2 * np.pi * 3.3 * t) * np.sin(2 * np.pi * 0.7 * t)
    return (lo + hi) * e * mod * gain


def bubble(f=500, gain=1.0):
    d = 0.12
    t = np.arange(int(d * SR)) / SR
    fr = f * (1 + 1.5 * t / d)
    ph = 2 * np.pi * np.cumsum(fr) / SR
    return np.sin(ph) * np.exp(-t * 30) * env_adsr(len(t), 0.003, 0.01) * gain


def chime(freqs, gain=1.0, gap=0.09):
    out = np.zeros(int((1.3 + gap * len(freqs)) * SR))
    for i, f in enumerate(freqs):
        s = tone(f, 1.2, 4.5, ((1, 1), (2, .3), (3, .08)))
        out[int(i * gap * SR):int(i * gap * SR) + len(s)] += s
    return out * gain


def pop(gain=1.0):
    return bubble(rng.uniform(600, 900), gain)


def build_fx(n):
    fx = np.zeros(n)
    # transiciones de cámara
    for t0 in (2.1, 47.7, 53.7, 60.6, 72.2):
        add(fx, t0, whoosh(1.2), 0.10)
    add(fx, 0.0, whoosh(2.6, 200, 900), 0.07)          # dron/viento inicial
    add(fx, 4.45, whoosh(1.1, 1500, 5000), 0.05)       # corte del inodoro
    add(fx, 4.6, chime([1568, 2093], 1.0), 0.035)
    add(fx, 70.6, whoosh(1.2, 4000, 1200), 0.05)
    # palanca y descarga
    add(fx, 12.72, click(), 0.22)
    add(fx, 13.25, tone(180, 0.15, 25, ((1, 1), (2, .4))), 0.15)   # tapón se levanta
    add(fx, 13.7, flush(5.5), 0.16)
    for k in range(18):
        add(fx, 15.0 + k * 0.17 + rng.uniform(0, .08), bubble(rng.uniform(350, 700)), 0.06)
    # sifón: gorgoteo y succión
    add(fx, 24.9, flush(3.6), 0.13)
    for k in range(40):
        add(fx, 25.2 + k * 0.11 + rng.uniform(0, .06), bubble(rng.uniform(180, 420)), 0.10)
    add(fx, 27.9, whoosh(0.9, 200, 700), 0.12)
    # tubería
    add(fx, 25.6, filt(noise(4.0), 'lowpass', 400) * np.sin(np.linspace(0, np.pi, int(4.0 * SR))), 0.06)
    add(fx, 45.5, filt(noise(3.5), 'lowpass', 450) * np.sin(np.linspace(0, np.pi, int(3.5 * SR))), 0.07)
    # tapón cierra
    add(fx, 32.9, tone(140, 0.2, 18, ((1, 1), (2.1, .3))), 0.16)
    # válvula abre + agua nueva
    add(fx, 34.55, chime([1760, 2349, 2637], 1.0, 0.06), 0.05)
    hiss = filt(filt(noise(7.2), 'highpass', 1800), 'lowpass', 6000)
    hiss *= env_adsr(len(hiss), 0.4, 0.15)
    add(fx, 35.4, hiss, 0.035)
    for k in range(20):
        add(fx, 35.6 + k * 0.33 + rng.uniform(0, .1), bubble(rng.uniform(500, 900)), 0.035)
    # clic de válvula y check
    add(fx, 42.68, click(), 0.24)
    add(fx, 43.78, chime([1318.5, 1975.5], 1.0, 0.11), 0.08)
    # planta: rejilla, bacterias, agua limpia
    for k in range(10):
        add(fx, 54.5 + k * 0.13, tone(rng.uniform(700, 900), 0.08, 50), 0.04)
    for k in range(16):
        add(fx, 56.25 + k * 0.12 + rng.uniform(0, .2), pop(), 0.09)
    add(fx, 59.0, chime([1046.5, 1318.5, 1568, 2093], 1.0, 0.07), 0.05)
    add(fx, 59.6, flush(1.5), 0.05)
    # olores bloqueados por el sello
    add(fx, 68.5, tone(220, 0.25, 14, ((1, 1), (1.5, .4))), 0.16)
    add(fx, 68.35, chime([1568, 2349], 1.0), 0.04)
    add(fx, 43.0, np.zeros(1))
    return fx


def main(voice_path):
    v = load_voice(voice_path)
    n = len(v)
    m = music(n)
    # música bajita y que "se agacha" con la voz (ducking suave)
    venv = np.abs(v)
    k = int(0.25 * SR)
    venv = np.convolve(venv, np.ones(k) / k, mode='same')
    duck = 1 - 0.45 * np.clip(venv / (venv.max() * 0.35), 0, 1)
    m *= duck
    fade = np.ones(n)
    fade[:int(1.0 * SR)] = np.linspace(0, 1, int(1.0 * SR))
    fade[-int(2.0 * SR):] = np.linspace(1, 0, int(2.0 * SR))
    m *= fade
    fx = build_fx(n)
    mix = v + m * 0.45 + fx
    peak = np.abs(mix).max()
    if peak > 0.97:
        mix *= 0.97 / peak
    pcm = (mix * 32767).astype('<i2')
    path = os.path.join(OUT, 'mezcla.wav')
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '-', path], input=pcm.tobytes(), check=True)
    rms = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
    print('voz', round(rms(v), 1), 'dB | música', round(rms(m * 0.45), 1), 'dB | fx', round(rms(fx), 1), 'dB | muestras', n)


if __name__ == '__main__':
    main(sys.argv[1])
