#!/usr/bin/env python3
"""Genera toda la banda sonora del video y el archivo de tiempos.

Salidas:
  public/audio/mix.wav        Mezcla final (narración + música + ambiente + efectos)
  src/timings.json            Inicio/duración de cada escena y subtítulos

Requisitos: espeak-ng, mbrola + voz mbrola-mx2, sox, numpy, scipy.
Si existe public/audio/voz/escena{N}.wav (p. ej. una locución profesional grabada o
generada con ElevenLabs/Azure), se usa ese archivo en lugar de la voz sintética.
"""
import json
import os
import re
import subprocess
import tempfile

import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
FPS = 30
MIN_SCENE = 10.0       # segundos mínimos por escena
LEAD_IN = 0.6          # la narración empieza 0.6 s después del inicio de la escena
TAIL = 1.2             # respiro tras la narración
TRANSITION = 15        # frames de fundido cruzado entre escenas
END_CARD = 3.5         # segundos extra al final para el título
RNG = np.random.default_rng(7)

NARR = json.load(open(os.path.join(ROOT, "scripts", "narracion.json"), encoding="utf-8"))
VOICE_DIR = os.path.join(ROOT, "public", "audio", "voz")


# ---------------------------------------------------------------- narración
def tts(text: str, out: str):
    """espeak-ng (fonemas) -> mbrola mx2. Se corrigen fonemas que la voz no tiene."""
    pho = subprocess.run(
        ["espeak-ng", "-v", "mb-mx2", "-s", "158", "-p", "38", "-q", "--pho", text],
        capture_output=True, text=True, check=True).stdout
    fixed = []
    for line in pho.splitlines():
        parts = line.split("\t")
        if parts and parts[0]:
            parts[0] = {"e/": "e", "o/": "o", "l^": "j", "L": "j"}.get(parts[0], parts[0])
        fixed.append("\t".join(parts))
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "v.pho")
        raw = os.path.join(td, "raw.wav")
        open(p, "w").write("\n".join(fixed) + "\n")
        subprocess.run(["mbrola", "/usr/share/mbrola/mx2/mx2", p, raw],
                       check=True, capture_output=True)
        # Tratamiento de "locutor": EQ cálida, compresión, un toque de sala.
        subprocess.run([
            "sox", raw, "-r", str(SR), "-c", "1", out,
            "highpass", "70", "bass", "+4", "120", "treble", "+2", "6000",
            "compand", "0.02,0.2", "6:-60,-40,-30,-20,-10", "-6", "-90", "0.05",
            "reverb", "12", "50", "40", "100", "0", "0",
            "norm", "-1",
        ], check=True, capture_output=True)


def load(path):
    sr, x = wavfile.read(path)
    if x.dtype == np.int16:
        x = x.astype(np.float32) / 32768.0
    elif x.dtype == np.int32:
        x = x.astype(np.float32) / 2147483648.0
    else:
        x = x.astype(np.float32)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != SR:
        x = signal.resample_poly(x, SR, sr).astype(np.float32)
    return x


def chunk_subtitles(text, max_chars=84):
    """Divide el texto en bloques de subtítulos (máx. 2 líneas) en pausas naturales."""
    clauses = re.split(r"(?<=[\.,:;?])\s+", text)
    chunks, cur = [], ""
    for c in clauses:
        cand = (cur + " " + c).strip()
        if len(cand) <= max_chars:
            cur = cand
        else:
            if cur:
                chunks.append(cur)
            cur = c
    if cur:
        chunks.append(cur)
    out = []
    for c in chunks:
        if len(c) <= max_chars:
            out.append(c)
            continue
        words = c.split()
        half, acc = len(c) / 2, 0
        for k, w in enumerate(words):
            acc += len(w) + 1
            if acc >= half:
                out += [" ".join(words[: k + 1]), " ".join(words[k + 1:])]
                break
    merged = []
    for c in out:
        if merged and len(merged[-1]) < 20 and len(merged[-1]) + 1 + len(c) <= 90:
            merged[-1] += " " + c
        else:
            merged.append(c)
    return merged


voices, voice_lens = [], []
tmpdir = tempfile.mkdtemp()
for i, t in enumerate(NARR):
    custom = os.path.join(VOICE_DIR, f"escena{i + 1}.wav")
    if os.path.exists(custom):
        v = load(custom)
    else:
        path = os.path.join(tmpdir, f"n{i}.wav")
        tts(t, path)
        v = load(path)
    # recorta silencios de los extremos
    nz = np.where(np.abs(v) > 0.01)[0]
    v = v[max(0, nz[0] - 800): nz[-1] + 2400]
    voices.append(v)
    voice_lens.append(len(v) / SR)

# ---------------------------------------------------------------- tiempos
scenes, start = [], 0
for i, L in enumerate(voice_lens):
    dur_s = max(MIN_SCENE, LEAD_IN + L + TAIL)
    if i == len(voice_lens) - 1:
        dur_s += END_CARD
    dur = int(round(dur_s * FPS))
    narr_from = start + int(round(LEAD_IN * FPS))
    chunks = chunk_subtitles(NARR[i])
    total_chars = sum(len(c) for c in chunks)
    subs, t0 = [], narr_from
    for c in chunks:
        n = int(round(L * FPS * len(c) / total_chars))
        subs.append({"text": c, "from": t0, "duration": n})
        t0 += n
    scenes.append({"from": start, "duration": dur, "narrationFrom": narr_from,
                   "narrationDuration": int(round(L * FPS)), "subtitles": subs})
    start += dur - TRANSITION
total_frames = scenes[-1]["from"] + scenes[-1]["duration"]
N = int(total_frames / FPS * SR) + SR
T = total_frames / FPS
print("Duraciones de narración:", [round(x, 2) for x in voice_lens])
print("Escenas (s):", [round(s["duration"] / FPS, 2) for s in scenes], "Total:", round(T, 2), "s")


def at(sec):
    return int(sec * SR)


def place(buf, x, sec, gain=1.0):
    i = at(sec)
    if i >= len(buf):
        return
    x = x[: len(buf) - i]
    buf[i: i + len(x)] += x * gain


def env(n, a=0.01, r=0.1):
    e = np.ones(n, np.float32)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def bandpass(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x).astype(np.float32)


def lowpass(x, f, order=2):
    sos = signal.butter(order, f, btype="low", fs=SR, output="sos")
    return signal.sosfilt(sos, x).astype(np.float32)


# ---------------------------------------------------------------- voz
voice_track = np.zeros(N, np.float32)
for i, s in enumerate(scenes):
    place(voice_track, voices[i], s["narrationFrom"] / FPS, 0.95)

# ---------------------------------------------------------------- música
def note_freq(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pad_tone(freqs, dur):
    n = at(dur)
    t = np.arange(n) / SR
    y = np.zeros(n, np.float32)
    for f in freqs:
        for det in (-0.12, 0.0, 0.11):
            ff = f * 2 ** (det / 12)
            ph = RNG.uniform(0, 2 * np.pi)
            y += (np.sin(2 * np.pi * ff * t + ph) + 0.25 * np.sin(4 * np.pi * ff * t + ph)
                  + 0.08 * np.sin(6 * np.pi * ff * t)).astype(np.float32)
    y *= env(n, 0.8, 0.9)
    return y / (len(freqs) * 3)


def pluck(f, dur=1.2):
    n = at(dur)
    t = np.arange(n) / SR
    e = np.exp(-t * 4.0)
    y = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) * np.exp(-t * 6)
         + 0.2 * np.sin(6 * np.pi * f * t) * np.exp(-t * 9))
    return (y * e * env(n, 0.004, 0.2)).astype(np.float32)


def soft_kick():
    n = at(0.35)
    t = np.arange(n) / SR
    f = 50 + 70 * np.exp(-t * 30)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)).astype(np.float32)


music = np.zeros(N, np.float32)
BPM = 84
beat = 60 / BPM
bar = beat * 4
# Progresión en Do mayor: C - G - Am - F  (inspiradora, luminosa)
prog = [[48, 55, 60, 64], [43, 55, 59, 62], [45, 57, 60, 64], [41, 57, 60, 65]]
arp_pat = [0, 1, 2, 3, 2, 1, 2, 3]
n_bars = int(T / bar) + 2
for b in range(n_bars):
    ch = prog[b % 4]
    t0 = b * bar
    place(music, pad_tone([note_freq(m) for m in ch], bar + 0.9), t0, 0.55)
    place(music, pad_tone([note_freq(ch[0] - 12)], bar + 0.5), t0, 0.35)
    # arpegio de "piano/pluck"
    for k, idx in enumerate(arp_pat):
        m = ch[idx] + 12
        place(music, pluck(note_freq(m)), t0 + k * beat / 2, 0.22 * (0.9 + 0.2 * RNG.random()))
    # pulso suave a partir del segundo tercio (sensación de crecimiento)
    if t0 > T * 0.33:
        for k in range(4):
            place(music, soft_kick(), t0 + k * beat, 0.30 if k % 2 == 0 else 0.18)
    # melodía simple en las escenas finales
    if t0 > T * 0.62:
        mel = [ch[3] + 12, ch[2] + 12, ch[3] + 12, ch[1] + 24]
        for k, m in enumerate(mel):
            place(music, pluck(note_freq(m), 1.6), t0 + k * beat, 0.16)
music = lowpass(music, 7000)
# crescendo suave y fundidos
tt = np.arange(N) / SR
music *= np.clip(tt / 2.0, 0, 1) * (0.75 + 0.25 * np.clip(tt / T, 0, 1))
fade_out = np.clip((T - tt) / 2.5, 0, 1)
music *= fade_out

# ---------------------------------------------------------------- ambiente y efectos
amb = np.zeros(N, np.float32)
# viento suave constante
wind = lowpass(RNG.standard_normal(N).astype(np.float32), 400) * 0.5
wind *= (0.6 + 0.4 * np.sin(2 * np.pi * tt / 7.3)).astype(np.float32)
amb += wind * 0.08


def chirp_bird():
    n = at(0.09)
    t = np.arange(n) / SR
    f0 = RNG.uniform(2800, 4200)
    f = f0 + RNG.uniform(-1500, 1500) * t / t[-1]
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1])).astype(np.float32)


def bird_call(sec, g=0.12):
    for k in range(RNG.integers(2, 5)):
        place(amb, chirp_bird(), sec + k * RNG.uniform(0.09, 0.16), g)


def cluck(f=520):
    n = at(0.13)
    t = np.arange(n) / SR
    ff = f * (1.3 - 0.5 * t / t[-1])
    tone = signal.sawtooth(2 * np.pi * np.cumsum(ff) / SR).astype(np.float32)
    y = bandpass(tone, 600, 2600) + 0.3 * bandpass(RNG.standard_normal(n).astype(np.float32), 1000, 4000)
    return y * np.abs(np.sin(np.pi * t / t[-1])) ** 0.6


def bok(sec, g=0.18):
    f = RNG.uniform(420, 620)
    for k in range(RNG.integers(2, 5)):
        place(amb, cluck(f * RNG.uniform(0.95, 1.08)), sec + k * RNG.uniform(0.16, 0.24), g)


def grunt(f=95, dur=0.32):
    n = at(dur)
    t = np.arange(n) / SR
    ff = f * (1 + 0.15 * np.sin(2 * np.pi * 3 * t))
    buzz = signal.sawtooth(2 * np.pi * np.cumsum(ff) / SR).astype(np.float32)
    am = (0.6 + 0.4 * np.sin(2 * np.pi * 28 * t)).astype(np.float32)
    y = bandpass(buzz * am, 150, 900) + 0.6 * bandpass(buzz, 250, 500)
    return y * np.abs(np.sin(np.pi * t / t[-1])) ** 0.5


def squeal(dur=0.25):
    n = at(dur)
    t = np.arange(n) / SR
    ff = RNG.uniform(700, 1000) * (1 + 0.3 * np.sin(np.pi * t / t[-1]))
    y = signal.sawtooth(2 * np.pi * np.cumsum(ff) / SR).astype(np.float32)
    return bandpass(y, 800, 3500) * np.sin(np.pi * t / t[-1])


def truck(dur):
    n = at(dur)
    t = np.arange(n) / SR
    ff = 38 + 6 * np.clip(t / dur, 0, 1)
    y = signal.sawtooth(2 * np.pi * np.cumsum(ff) / SR).astype(np.float32)
    y = lowpass(y, 260) + 0.3 * lowpass(RNG.standard_normal(n).astype(np.float32), 500)
    return y * env(n, 0.6, 1.2)


def whoosh(dur=0.7):
    n = at(dur)
    t = np.arange(n) / SR
    noise = RNG.standard_normal(n).astype(np.float32)
    out = np.zeros(n, np.float32)
    seg = n // 8
    for k in range(8):
        lo = 300 + 2500 * np.sin(np.pi * (k + 0.5) / 8)
        out[k * seg:(k + 1) * seg] = bandpass(noise[k * seg:(k + 1) * seg], lo, lo * 1.8)
    return out * np.abs(np.sin(np.pi * t / t[-1])) ** 2


def chime():
    y = np.zeros(at(2.5), np.float32)
    for k, m in enumerate([72, 76, 79, 84]):
        p = pluck(note_freq(m), 2.0)
        y[at(k * 0.09): at(k * 0.09) + len(p)] += p[: len(y) - at(k * 0.09)]
    return y


def sec_of(i, off=0.0):
    return scenes[i]["from"] / FPS + off


# Escena 1: pájaros y viento
for s in np.arange(0.5, scenes[0]["duration"] / FPS, 1.6):
    bird_call(s + RNG.uniform(0, 0.8))
# Escena 2: gallinero + camión
d2 = scenes[1]["duration"] / FPS
for s in np.arange(0.3, d2 - 2.5, 0.75):
    bok(sec_of(1, s + RNG.uniform(0, 0.4)), 0.13)
place(amb, truck(3.4), sec_of(1, d2 - 3.6), 0.22)
# Escena 3: maternidad (gruñidos suaves y lechones)
d3 = scenes[2]["duration"] / FPS
for s in np.arange(0.4, d3, 1.1):
    place(amb, grunt(RNG.uniform(80, 110), RNG.uniform(0.25, 0.4)), sec_of(2, s + RNG.uniform(0, 0.5)), 0.14)
for s in np.arange(0.9, d3, 1.7):
    place(amb, squeal(), sec_of(2, s + RNG.uniform(0, 0.6)), 0.06)
# Escena 4: engorde
d4 = scenes[3]["duration"] / FPS
for s in np.arange(0.3, d4, 0.9):
    place(amb, grunt(RNG.uniform(70, 100), RNG.uniform(0.3, 0.45)), sec_of(3, s + RNG.uniform(0, 0.4)), 0.15)
# Escena 5: campanita en la cifra de inversión
place(amb, chime(), sec_of(4, 3.2), 0.18)
for s in np.arange(0.5, scenes[4]["duration"] / FPS, 2.5):
    bird_call(sec_of(4, s), 0.06)
# Escena 6: pájaros, ambiente vivo
for s in np.arange(0.5, scenes[5]["duration"] / FPS - 3, 1.4):
    bird_call(sec_of(5, s + RNG.uniform(0, 0.6)), 0.09)
    if RNG.random() < 0.5:
        bok(sec_of(5, s + 0.7), 0.05)
# transiciones
for i in range(1, len(scenes)):
    place(amb, whoosh(), scenes[i]["from"] / FPS - 0.2, 0.05)
place(amb, chime(), sec_of(5, scenes[5]["duration"] / FPS - END_CARD - 0.2), 0.14)

amb *= fade_out

# ---------------------------------------------------------------- mezcla con "ducking"
v_env = np.abs(voice_track)
v_env = lowpass(v_env, 4)
v_env = np.clip(v_env / (v_env.max() + 1e-9) * 3, 0, 1)
duck = 1.0 - 0.45 * v_env
mix = voice_track * 1.0 + music * 0.20 * duck + amb * 0.75 * (1.0 - 0.3 * v_env)
mix = mix[: at(T)]
peak = np.abs(mix).max()
mix = mix / peak * 0.89
out = os.path.join(ROOT, "public", "audio", "mix.wav")
os.makedirs(os.path.dirname(out), exist_ok=True)
wavfile.write(out, SR, (mix * 32767).astype(np.int16))

timing = {"fps": FPS, "transition": TRANSITION, "durationInFrames": total_frames,
          "endCardFrames": int(END_CARD * FPS), "scenes": scenes}
json.dump(timing, open(os.path.join(ROOT, "src", "timings.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("OK ->", out)
