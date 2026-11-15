#!/usr/bin/env python3
"""Audio de "El costo de congelar los combustibles".

1. Música original sintetizada por código (sin muestras de terceros): tema documental
   en re menor, pulso contenido y resolución final en fa mayor.
2. Efectos sonoros sintetizados (barridos y golpes suaves) en cambios de escena y cifras.
3. Narración con limpieza leve, mezcla con ducking (la voz siempre por encima) y
   normalización a -14 LUFS / -1.5 dBTP.

Uso: python3 audio.py <directorio_salida>
Genera: musica_original.wav, narracion.wav, mezcla_final.wav
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from marca import ASSETS  # noqa: E402
from tiempos import CIERRE_INICIO, DURACION_VIDEO, ESCENAS, OFFSET  # noqa: E402

SR = 48000
N = int(DURACION_VIDEO * SR)
rng = np.random.default_rng(7)


def write_wav(path, x):
    x = np.atleast_2d(x)
    if x.shape[0] < x.shape[1]:
        x = x.T
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(pcm.shape[1])
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def lowpass(x, fc, order=2.0):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (f / fc) ** (2 * order))
    return np.fft.irfft(X, len(x))


def bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (f / hi) ** 4) * (1 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 4))
    return np.fft.irfft(X, len(x))


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def saw(freq, n, phase=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, 14):
        if freq * k > 9000:
            break
        out += np.sin(2 * np.pi * freq * k * t + phase * k) / k
    return out * 0.55


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    e[-nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return e


def add(buf, sig, t0):
    i = int(t0 * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


def reverb(x, secs=2.4, mix=0.28):
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 7, n))
    ir = lowpass(ir, 5000)
    ir /= np.sqrt((ir ** 2).sum())
    L = len(x) + n
    nfft = 1 << (L - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[: len(x)]
    return x * (1 - mix) + wet * mix * 1.4


# ------------------------------------------------------------------- música
# Acordes (notas MIDI). Tiempos en segundos de VÍDEO.
Dm = [50, 57, 62, 65, 69]
Bb = [46, 53, 58, 62, 65]
F = [41, 48, 57, 60, 65]
C = [48, 55, 60, 64, 67]
Gm = [43, 50, 58, 62, 67]
Fmaj_fin = [41, 48, 53, 57, 60, 65, 69]
END_RES = CIERRE_INICIO + OFFSET          # resolución con el logo

PROG = [(0, Dm), (6, Bb), (12, F), (18, C), (24, Dm), (30, Bb), (36, Gm), (42, C), (48, Dm),
        (54, Bb), (END_RES - 2.4, C), (END_RES, Fmaj_fin)]
BEAT = 60 / 80


def musica():
    pad = np.zeros(N)
    bass = np.zeros(N)
    for i, (t0, notes) in enumerate(PROG):
        t1 = PROG[i + 1][0] if i + 1 < len(PROG) else DURACION_VIDEO
        last = i == len(PROG) - 1
        dur = t1 - t0 + (0 if last else 1.6)
        n = int(dur * SR)
        e = env_adsr(n, 1.4 if not last else 0.25, 1.8 if not last else 2.6)
        chord = np.zeros(n)
        for m in notes:
            for det in (-0.07, 0.0, 0.08):
                chord += saw(midi(m + det), n, rng.uniform(0, 6.28))
        add(pad, chord * e / len(notes), t0)
        root = notes[0] if notes[0] < 48 else notes[0] - 12
        add(bass, np.sin(2 * np.pi * midi(root - 12) * np.arange(n) / SR) * e * 0.9, t0)
    pad = lowpass(pad, 1100, 2)
    # intensidad: arranque suave, sube con las cifras, respiro en "¿Qué significa esto?"
    t = np.arange(N) / SR
    inten = np.interp(t, [0, 8, 21, 28.9, 29.3, 30.6, 47, 56.8, END_RES - 0.5, END_RES, DURACION_VIDEO],
                      [0.55, 0.7, 0.85, 0.85, 0.45, 0.8, 0.9, 0.95, 1.0, 1.0, 0.9])

    # pulso grave en cada pulso (late como un reloj) desde la escena 2
    pulse = np.zeros(N)
    k = np.arange(int(0.6 * SR)) / SR
    thump = np.sin(2 * np.pi * 55 * k * (1 - 0.3 * k)) * np.exp(-k * 9)
    tick_n = rng.standard_normal(int(0.05 * SR)) * np.exp(-np.linspace(0, 12, int(0.05 * SR)))
    tick = bandpass(np.pad(tick_n, (0, 2000)), 2500, 7000)
    b = 10.7
    while b < END_RES - 0.6:
        if not (29.0 < b < 30.6):
            bar_pos = round((b - 10.7) / BEAT) % 4
            add(pulse, thump * (0.9 if bar_pos == 0 else 0.45), b)
            add(pulse, tick * (0.25 if bar_pos % 2 else 0.4), b)
        b += BEAT

    # piano/campana sintética: arpegios escasos desde las cifras
    keys = np.zeros(N)

    def pluck(freq, dur=2.2):
        n = int(dur * SR)
        tt = np.arange(n) / SR
        s = sum(np.sin(2 * np.pi * freq * h * tt) * (0.6 ** (h - 1)) * np.exp(-tt * (2.2 + h))
                for h in (1, 2, 3, 4))
        return s * np.minimum(1, tt / 0.004)

    for i, (t0, notes) in enumerate(PROG[:-1]):
        if t0 < 20:
            continue
        t1 = PROG[i + 1][0]
        tt, j = t0, 0
        pattern = [2, 3, 4, 3]
        while tt < t1 - 0.1:
            if not (28.6 < tt < 30.6):
                m = notes[pattern[j % 4] % len(notes)] + 12
                add(keys, pluck(midi(m)) * 0.35, tt)
            tt += BEAT * 2
            j += 1
    # acorde final resuelto
    for m in Fmaj_fin[2:]:
        add(keys, pluck(midi(m + 12), 5.0) * 0.4, END_RES)
    # ascenso suave antes del cierre
    rn = int(1.6 * SR)
    riser = lowpass(rng.standard_normal(rn), 3000) * np.linspace(0, 1, rn) ** 2 * 0.25
    add(keys, riser, END_RES - 1.6)

    mix = pad * 0.55 * inten + bass * 0.32 * inten + pulse * 0.30 + keys * 0.30
    mix = reverb(mix)
    fade = np.clip((DURACION_VIDEO - t) / 1.2, 0, 1) * np.clip(t / 1.0, 0, 1)
    mix *= fade
    left = mix + reverb(keys * 0.06, 1.2, 1.0) * 0.0
    stereo = np.vstack([left, np.roll(mix, int(0.011 * SR))])   # ensanchado sutil
    return stereo / np.max(np.abs(stereo)) * 0.5


# ------------------------------------------------------------------- efectos

def whoosh(dur=0.7):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    # barrido de un filtro paso banda por bloques
    blk = 1024
    for i in range(0, n, blk):
        p = i / n
        fc = 300 + 2600 * np.sin(np.pi * p)
        seg = x[i:i + blk]
        out[i:i + blk] = bandpass(np.pad(seg, (0, 0)), fc * 0.6, fc * 1.6)[: len(seg)]
    e = np.sin(np.linspace(0, np.pi, n)) ** 2
    return out * e


def pop(freq=880):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * freq * t) * np.exp(-t * 18) * 0.6
         + np.sin(2 * np.pi * 110 * t) * np.exp(-t * 22) * 0.8)
    return s * np.minimum(1, t / 0.002)


def impact():
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * 48 * t * (1 - 0.25 * t)) * np.exp(-t * 3.2)
    s += lowpass(rng.standard_normal(n), 400) * np.exp(-t * 5) * 0.4
    return s


def efectos():
    fx = np.zeros(N)
    for name, a, _ in ESCENAS[1:]:
        if name == "sq":
            continue
        add(fx, whoosh() * 0.20, a + OFFSET - 0.35)
    for tn in (7.55, 13.75, 16.6, 21.3, 25.05, 33.4, 43.7, 47.85, 50.55, 53.3):
        add(fx, pop(660) * 0.16, tn + OFFSET)
    for tn in (14.25, 18.45, 26.6):        # cifras clave
        add(fx, pop(990) * 0.22, tn + OFFSET)
    add(fx, impact() * 0.33, 28.42 + OFFSET)
    # campanita del logo
    n = int(2.5 * SR)
    t = np.arange(n) / SR
    chime = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * 2.5) for f in (1046.5, 1568, 2093)) / 3
    add(fx, chime * 0.14, CIERRE_INICIO + OFFSET + 1.0)
    return reverb(fx, 1.4, 0.2)


# ------------------------------------------------------------------- mezcla

def narracion(outdir):
    src = ASSETS / "audio" / "narracion_combustibles.mp3"
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(src), "-af",
         "highpass=f=70,lowpass=f=15000,acompressor=threshold=-22dB:ratio=2:attack=10:release=150:makeup=1.5",
         "-ar", str(SR), "-ac", "1", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.float32).astype(np.float64)
    write_wav(Path(outdir) / "narracion.wav", v / np.max(np.abs(v)) * 0.89)
    voice = np.zeros(N)
    add(voice, v, OFFSET)
    return voice


def envelope(x, win=0.05, att=0.04, rel=0.45):
    hop = int(win * SR / 4)
    rms = np.sqrt(np.convolve(x ** 2, np.ones(int(win * SR)) / int(win * SR), "same")[::hop])
    e = np.zeros_like(rms)
    a, r = np.exp(-hop / (att * SR)), np.exp(-hop / (rel * SR))
    for i in range(1, len(rms)):
        c = a if rms[i] > e[i - 1] else r
        e[i] = c * e[i - 1] + (1 - c) * rms[i]
    return np.interp(np.arange(len(x)), np.arange(len(e)) * hop, e)


def main(outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    music = musica()
    write_wav(ASSETS / "musica" / "combustibles_tema_original.wav", music)
    fx = efectos()
    voice = narracion(out)
    voice = voice / np.max(np.abs(voice)) * 0.6
    env = envelope(voice)
    env = np.clip(env / np.percentile(env[env > 1e-4], 70), 0, 1)
    duck = 1 - 0.62 * env                         # ~ -8.4 dB bajo la voz
    music_lvl = 0.40
    mix = np.vstack([voice, voice]) + music * duck * music_lvl / 0.5 * 0.5 + np.vstack([fx, fx]) * 0.5
    peak = np.max(np.abs(mix))
    mix = mix / peak * 0.7
    tmp = out / "_premezcla.wav"
    write_wav(tmp, mix)
    # normalización de sonoridad en dos pasadas (EBU R128)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(tmp), "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = json.loads(r[r.rindex("{"):r.rindex("}") + 1])
    flt = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
           f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
           f"offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af", flt, "-ar", str(SR),
                    "-c:a", "pcm_s16le", str(out / "mezcla_final.wav")], check=True)
    tmp.unlink()
    print("mezcla lista", m)


if __name__ == "__main__":
    main(sys.argv[1])
