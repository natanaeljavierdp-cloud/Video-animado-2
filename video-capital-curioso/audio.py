"""Música de tensión + efectos de sonido sintetizados (sin licencias de terceros),
y mezcla final con la voz.  Uso: python3 audio.py  -> out/musica.wav, out/sfx.wav, out/mezcla.wav
"""
import os, subprocess
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile
from timeline import *

SR = 44100
N = int(DURATION * SR) + SR
rng = np.random.default_rng(7)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)

def tt(n): return np.arange(n) / SR
def lp(x, f, o=2): return sosfilt(butter(o, f, "low", fs=SR, output="sos"), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, "high", fs=SR, output="sos"), x)
def bp(x, a, b, o=2): return sosfilt(butter(o, [a, b], "band", fs=SR, output="sos"), x)
def env_ad(n, att, dec):
    t = tt(n); e = np.minimum(t / max(att, 1e-4), 1.0) * np.exp(-np.maximum(t - att, 0) / dec); return e
def add(buf, x, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR); j = min(len(buf), i + len(x))
    if j <= i: return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:j, 0] += x[: j - i] * gain * l * 1.414; buf[i:j, 1] += x[: j - i] * gain * r * 1.414
def saw(f, n, harm=10, det=0.0):
    t = tt(n); y = np.zeros(n)
    for k in range(1, harm + 1):
        y += np.sin(2 * np.pi * f * (1 + det) * k * t + k) / k
    return y
def reverb(x, secs=2.2, wet=0.3):
    n = int(secs * SR); irs = []
    for _ in range(2):  # un impulso distinto por canal = reverb estéreo
        ir = lp(rng.standard_normal(n) * np.exp(-tt(n) / (secs / 5)), 5000)
        irs.append(ir / np.sqrt(np.sum(ir ** 2)))
    out = np.stack([fftconvolve(x[:, c], irs[c], mode="full")[: len(x)] for c in range(2)], 1)
    return x * (1 - wet) + out * wet

def hz(note):  # 'D3'
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
    n, o = note[:-1], int(note[-1]); return 440 * 2 ** ((names[n] + 12 * (o + 1) - 69) / 12)

# ============================ MÚSICA ============================
def music():
    m = np.zeros((N, 2))
    bpm = 96; beat = 60 / bpm; bar = 4 * beat
    def intensity(t):          # curva de energía según la narración
        pts = [(0, .55), (7, .75), (21, .85), (34.4, .6), (35.6, .8), (43, .85), (54.9, .9), (62.4, .5), (67.5, .75), (VOICE_END, 1.0), (DURATION, .9)]
        for (a, va), (b, vb) in zip(pts, pts[1:]):
            if a <= t <= b: return va + (vb - va) * (t - a) / (b - a)
        return .8
    # 1) drone grave (D) que respira
    n = N; t = tt(n)
    dr = sum(saw(hz("D2"), n, 8, d) for d in (-0.003, 0.0, 0.004)) + 0.6 * saw(hz("A2"), n, 6, 0.002)
    dr = lp(dr, 380, 4) * (0.75 + 0.25 * np.sin(2 * np.pi * t / 7.5))
    m += np.stack([dr, dr], 1) * 0.10
    # 2) colchón de cuerdas: Dm - Bb - Gm - A (cada 2 compases)
    chords = [["D3", "F3", "A3", "D4"], ["A#2", "D3", "F3", "A#3"], ["G2", "A#2", "D3", "G3"], ["A2", "C#3", "E3", "A3"]]
    seg = 2 * bar; k = 0; t0 = 0.0
    while t0 < DURATION:
        n = int((seg + 1.2) * SR)
        pad = np.zeros(n)
        for nt in chords[k % 4]:
            for d in (-0.004, 0.004):
                pad += saw(hz(nt), n, 7, d)
        e = np.minimum(tt(n) / 0.9, 1) * np.minimum(1, np.maximum(0, (seg + 1.2 - tt(n)) / 1.2))
        pad = lp(pad, 1400, 2) * e * (1 + 0.15 * np.sin(2 * np.pi * 5.5 * tt(n)))
        add(m, pad, t0, 0.028 * (0.6 + 0.5 * intensity(t0)), -0.3 if k % 2 else 0.3)
        t0 += seg; k += 1
    # 3) pulso tipo latido (sub) y 4) tic-tac de reloj
    bt = 0.0; i = 0
    while bt < DURATION + 1:
        quiet = S7[0] <= bt < 67.6
        if i % 2 == 0:
            for off, g in ((0, 1.0), (0.2, 0.6)):
                n = int(0.45 * SR); tt_ = tt(n)
                f = 38 + 30 * np.exp(-tt_ * 25)
                kick = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt_ * 7)
                add(m, kick, bt + off, 0.42 * g * intensity(bt) * (0.5 if quiet else 1))
        for h in range(2):          # corcheas de reloj
            n = int(0.03 * SR)
            tk = hp(rng.standard_normal(n), 5000) * np.exp(-tt(n) * 220)
            add(m, tk, bt + h * beat / 2, (0.10 if h == 0 else 0.055) * intensity(bt), 0.35 if h else -0.35)
        bt += beat; i += 1
    # 5) ostinato staccato (cello) desde la escena 2, se calla en la pregunta
    pattern = ["D3", "D3", "A2", "D3", "F3", "D3", "A2", "C3"]
    roots = {0: 0, 1: -4, 2: -7, 3: -5}
    st = S2[0]; i = 0
    while st < DURATION:
        if not (S7[0] - 0.3 <= st < 67.6) and st < VOICE_END:
            ch = int(st // seg) % 4
            f = hz(pattern[i % 8]) * 2 ** (roots[ch] / 12)
            n = int(0.22 * SR)
            note = lp(saw(f, n, 9), 900 + 900 * intensity(st)) * env_ad(n, 0.005, 0.07)
            add(m, note, st, 0.11 * intensity(st), 0.2 if i % 2 else -0.2)
        st += beat / 2; i += 1
    # 6) cuerda aguda disonante (tensión) en tramos clave
    for a, b, nt in ((21.1, 34.3, "A5"), (43.1, 54.8, "A#5"), (54.9, 62.3, "A5"), (62.5, 70.5, "D6")):
        n = int((b - a) * SR); t_ = tt(n)
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5 * t_)
        s = np.sin(2 * np.pi * hz(nt) * np.cumsum(vib) / SR) + 0.3 * np.sin(4 * np.pi * hz(nt) * np.cumsum(vib) / SR)
        e = np.minimum(t_ / 2.5, 1) * np.minimum(1, (b - a - t_) / 1.0)
        add(m, s * e, a, 0.016)
    # 7) golpe final + cola en el cierre
    n = int(3.2 * SR); t_ = tt(n)
    boom = np.sin(2 * np.pi * (32 + 40 * np.exp(-t_ * 6)) * t_) * np.exp(-t_ * 1.4)
    add(m, boom, OUTRO[0] + 0.25, 0.6)
    chord = sum(saw(hz(x), n, 8, d) for x in ("D2", "A2", "D3", "F3") for d in (-0.003, 0.003))
    add(m, lp(chord, 1200) * np.exp(-t_ * 1.0), OUTRO[0] + 0.25, 0.045)
    m = reverb(m, 2.5, 0.22)
    # fundido de salida
    fe = np.ones(N); e0 = int((DURATION - 0.9) * SR); fe[e0:] = np.linspace(1, 0, N - e0) ** 2
    m *= fe[:, None]
    return m / (np.max(np.abs(m)) + 1e-9) * 0.9

# ============================ EFECTOS ============================
def sfx():
    s = np.zeros((N, 2))
    for cue in CUES:
        kind, t0 = cue[0], cue[1]
        if kind in ("whoosh", "swoosh_long"):
            d = 0.55 if kind == "whoosh" else 1.4
            n = int(d * SR); x = rng.standard_normal(n); t_ = tt(n)
            # barrido de filtro por bloques
            y = np.zeros(n); blk = 512
            for b0 in range(0, n, blk):
                u = b0 / n; fc = 300 + 5000 * np.sin(np.pi * u) ** 2
                y[b0:b0 + blk] = bp(x[b0:b0 + blk + 0], max(80, fc * 0.5), min(16000, fc * 1.6))[: len(y[b0:b0 + blk])]
            y = lp(y, 7000) * np.sin(np.pi * t_ / d) ** 2
            st = t0 - d * 0.45
            half = n // 2
            add(s, y[:half], st, 0.55, -0.6); add(s, y[half:], st + half / SR, 0.55, 0.6)
        elif kind in ("hit", "boom"):
            n = int(1.6 * SR); t_ = tt(n)
            sub = np.sin(2 * np.pi * (40 + 70 * np.exp(-t_ * 18)) * t_) * np.exp(-t_ * (3 if kind == "hit" else 1.8))
            crack = lp(rng.standard_normal(n), 2500) * np.exp(-t_ * 30)
            add(s, sub + (0.5 * crack if kind == "hit" else 0.2 * crack), t0, 0.75 if kind == "hit" else 0.6)
        elif kind == "type":
            d = cue[2]; tc = t0
            while tc < t0 + d:
                n = int(0.02 * SR); c = bp(rng.standard_normal(n), 1800, 6000) * np.exp(-tt(n) * 300)
                add(s, c, tc, 0.22 * rng.uniform(0.6, 1), rng.uniform(-0.3, 0.3))
                tc += rng.uniform(0.055, 0.1)
        elif kind == "tick":
            d = cue[2]; tc = t0; i = 0
            while tc < t0 + d:
                n = int(0.03 * SR); c = np.sin(2 * np.pi * (2200 + 40 * i) * tt(n)) * np.exp(-tt(n) * 160)
                add(s, c, tc, 0.18); tc += 0.06; i += 1
        elif kind == "pop":
            n = int(0.12 * SR); t_ = tt(n)
            c = np.sin(2 * np.pi * (900 - 500 * t_ / 0.12) * t_) * np.exp(-t_ * 40)
            add(s, c, t0, 0.32)
        elif kind == "ding":
            n = int(1.0 * SR); t_ = tt(n)
            c = (np.sin(2 * np.pi * 1320 * t_) + 0.5 * np.sin(2 * np.pi * 1980 * t_)) * np.exp(-t_ * 5)
            add(s, c, t0, 0.22)
        elif kind == "riser":
            d = cue[2]; n = int(d * SR); t_ = tt(n)
            y = hp(rng.standard_normal(n), 1500) * (t_ / d) ** 2
            tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * (t_ / d) ** 2) / SR) * (t_ / d) ** 2
            add(s, y * 0.5 + tone * 0.25, t0, 0.35)
        elif kind == "sting":
            n = int(2.5 * SR); t_ = tt(n)
            c = sum(np.sin(2 * np.pi * hz(x) * t_) for x in ("D4", "A4", "D5", "F5")) * np.exp(-t_ * 1.6)
            add(s, c, t0, 0.12)
            sub = np.sin(2 * np.pi * (35 + 60 * np.exp(-t_ * 10)) * t_) * np.exp(-t_ * 2)
            add(s, sub, t0, 0.7)
    s = reverb(s, 1.4, 0.18)
    return s / (np.max(np.abs(s)) + 1e-9) * 0.9

def w(path, x):
    wavfile.write(path, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))

if __name__ == "__main__":
    w(os.path.join(OUT, "musica.wav"), music())
    w(os.path.join(OUT, "sfx.wav"), sfx())
    voz = os.path.join(HERE, "assets", "voz.mp3")
    # voz al frente, música baja con "ducking" bajo la voz, efectos moderados
    fc = ("[0:a]aresample=44100,aformat=channel_layouts=stereo,highpass=f=70,"
          "acompressor=threshold=-18dB:ratio=3:attack=5:release=80,loudnorm=I=-15:TP=-1.5:LRA=9,asplit=2[v][vsc];"
          "[1:a]volume=0.30[mu];"
          "[mu][vsc]sidechaincompress=threshold=0.04:ratio=5:attack=20:release=400[mud];"
          "[2:a]volume=0.55[fx];"
          "[v][mud][fx]amix=inputs=3:normalize=0:duration=longest,alimiter=limit=0.95[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", voz, "-i", os.path.join(OUT, "musica.wav"),
                    "-i", os.path.join(OUT, "sfx.wav"), "-filter_complex", fc, "-map", "[out]",
                    "-t", str(DURATION), "-ar", "44100", os.path.join(OUT, "mezcla.wav")], check=True)
    print("audio listo")
