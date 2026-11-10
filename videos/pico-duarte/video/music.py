"""Música original de ambiente caribeño (marimba, clave, bajo, shaker y pad),
generada 100 % con código. Baja sola cuando habla la voz (ducking) usando los
tiempos reales de cada palabra (words.json).

Uso: python3 music.py <duracion_total_seg> <offset_voz_seg> <inicio_cierre_seg> <salida.wav>
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
TOTAL = float(sys.argv[1])
VOICE_OFF = float(sys.argv[2])
CIERRE = float(sys.argv[3])
OUT = sys.argv[4]

BPM = 98
BEAT = 60 / BPM
S16 = BEAT / 4
BAR = BEAT * 4
N = int(TOTAL * SR) + SR
rng = np.random.default_rng(7)

def note(n):  # MIDI -> Hz
    return 440 * 2 ** ((n - 69) / 12)

def add(buf, start, sig):
    i = int(start * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]

def marimba(freq, dur=0.9, vel=1.0):
    t = np.arange(int(dur * SR)) / SR
    env = np.exp(-t * 6.5) * (1 - np.exp(-t * 900))
    s = (np.sin(2 * np.pi * freq * t)
         + 0.28 * np.sin(2 * np.pi * freq * 3.93 * t) * np.exp(-t * 18)
         + 0.08 * np.sin(2 * np.pi * freq * 9.2 * t) * np.exp(-t * 40))
    return vel * env * s

def clave(vel=1.0):
    t = np.arange(int(0.09 * SR)) / SR
    env = np.exp(-t * 70)
    s = np.sin(2 * np.pi * 2450 * t) + 0.4 * np.sin(2 * np.pi * 1650 * t)
    return vel * env * s

def bass(freq, dur, vel=1.0):
    t = np.arange(int(dur * SR)) / SR
    env = (1 - np.exp(-t * 120)) * np.exp(-t * 2.2)
    s = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * 2 * freq * t)
    return vel * env * s

def shaker(vel=1.0):
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = np.diff(np.concatenate([[0], noise]))  # high-pass simple
    env = np.sin(np.pi * np.clip(t / 0.06, 0, 1)) ** 2
    return vel * env * noise

def pad(freqs, dur):
    t = np.arange(int(dur * SR)) / SR
    env = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.6).clip(0)
    s = sum(np.sin(2 * np.pi * f * t + i) + 0.3 * np.sin(2 * np.pi * f * 2.003 * t)
            for i, f in enumerate(freqs))
    return env * s / len(freqs)

# Progresión C - F - G - F (alegre, caribeña)
CHORDS = [
    (48, [60, 64, 67, 72]),  # C
    (53, [60, 65, 69, 72]),  # F
    (55, [59, 62, 67, 71]),  # G
    (53, [60, 65, 69, 72]),  # F
]
# patrón de marimba (posiciones en semicorcheas, índice de nota del acorde)
MARIMBA_PAT = [(0, 0), (3, 2), (6, 1), (8, 3), (10, 2), (12, 1), (14, 2)]
CLAVE_32 = [0, 6, 12, 20, 24]  # son clave 3-2 en dos compases

mar = np.zeros(N); clv = np.zeros(N); bas = np.zeros(N); shk = np.zeros(N); pd = np.zeros(N)
nbars = int(TOTAL / BAR) + 2
for b in range(nbars):
    t0 = b * BAR
    root, ch = CHORDS[b % 4]
    for pos, idx in MARIMBA_PAT:
        n = ch[idx] + (12 if (b % 2 and pos in (8, 14)) else 0)
        add(mar, t0 + pos * S16, marimba(note(n), vel=0.9 if pos % 4 == 0 else 0.65))
    # bajo tumbao: tiempo 1, "y" del 2, tiempo 4
    add(bas, t0, bass(note(root - 12), BEAT * 1.4, 1.0))
    add(bas, t0 + 6 * S16, bass(note(root - 12 + 7), BEAT * 1.4, 0.8))
    add(bas, t0 + 12 * S16, bass(note(root - 12), BEAT * 1.0, 0.85))
    for k in range(8):
        add(shk, t0 + k * 2 * S16, shaker(1.0 if k % 2 else 0.55))
    add(pd, t0, pad([note(n - 12) for n in ch[:3]], BAR + 0.3))
for b in range(0, nbars, 2):
    for pos in CLAVE_32:
        add(clv, b * BAR + pos * S16, clave())

def norm(x):
    return x / (np.max(np.abs(x)) + 1e-9)

mix = (0.55 * norm(mar) + 0.22 * norm(clv) + 0.55 * norm(bas)
       + 0.06 * norm(shk) + 0.18 * norm(pd))
# intro: arranque con un golpe de marimba más brillante
mix = norm(mix)[: int(TOTAL * SR)]

# ---------- ducking con los tiempos reales de la voz ----------
words = json.loads(Path(__file__).with_name("words.json").read_text(encoding="utf-8"))
talk = []
for w in words:
    s, e = w["start"] + VOICE_OFF, w["end"] + VOICE_OFF
    if talk and s - talk[-1][1] < 0.28:
        talk[-1][1] = e
    else:
        talk.append([s, e])
voice_end = words[-1]["end"] + VOICE_OFF

frames = np.arange(int(TOTAL * 100)) / 100  # control a 100 Hz
target = np.full(len(frames), 0.30)  # pausas: sube un poco
for s, e in talk:
    target[(frames >= s - 0.08) & (frames <= e + 0.05)] = 0.11  # bajo la voz
target[frames < VOICE_OFF] = 0.35
target[frames > voice_end + 0.15] = 0.42   # cierre: sube
# suavizado ataque/relajación
g = np.zeros_like(target); g[0] = target[0]
for i in range(1, len(g)):
    k = 0.25 if target[i] < g[i - 1] else 0.045
    g[i] = g[i - 1] + (target[i] - g[i - 1]) * k
gain = np.interp(np.arange(len(mix)) / SR, frames, g)
# fade in breve y fade out final
t = np.arange(len(mix)) / SR
gain *= np.clip(t / 0.15, 0, 1) * np.clip((TOTAL - t) / 1.6, 0, 1)
out = mix * gain

pcm = (np.clip(out, -1, 1) * 32767).astype(np.int16)
with wave.open(OUT, "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes(pcm.tobytes())
print("música", OUT, len(pcm) / SR, "s; tramos de voz:", len(talk))
