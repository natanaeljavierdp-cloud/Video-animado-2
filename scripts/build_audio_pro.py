#!/usr/bin/env python3
"""Banda sonora profesional para el video ya renderizado (no cambia las animaciones).

- Lee src/timings.json tal como está (mismos tiempos de escenas y subtítulos).
- Narración neural Kokoro (voz masculina "em_alex", español), ajustada en velocidad
  para que cada frase ocupe la misma ventana que los subtítulos.
- Música instrumental estéreo con reverberación, con "ducking" bajo la voz.
- Ambiente de granja suave (viento, aves, gallinas, cerdos, camión) también atenuado bajo la voz.
- Normalización de sonoridad a -16 LUFS integrados y pico real <= -1.5 dBTP.

Salida: public/audio/mix_pro.wav (48 kHz, estéreo, 24 bits)

Requisitos: pip install kokoro-onnx soundfile scipy numpy ; sox y ffmpeg instalados.
Modelos (gratuitos, Apache-2.0):
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
Indique la carpeta con KOKORO_DIR=/ruta (por defecto ./models).
Si existe public/audio/voz/escena{N}.wav (locución grabada o de otro servicio), se usa esa.
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
FPS = 30
VOICE = os.environ.get("VOICE", "em_alex")
KOKORO_DIR = os.environ.get("KOKORO_DIR", os.path.join(ROOT, "models"))
RNG = np.random.default_rng(11)

TEXT = json.load(open(os.path.join(ROOT, "scripts", "narracion.json"), encoding="utf-8"))
TM = json.load(open(os.path.join(ROOT, "src", "timings.json"), encoding="utf-8"))
SCENES = TM["scenes"]
TOTAL = TM["durationInFrames"] / FPS
N = int(TOTAL * SR)
TMP = tempfile.mkdtemp()


def sox(inp, out, *effects):
    subprocess.run(["sox", inp, out, *effects], check=True, capture_output=True)


def to48(x, sr):
    if sr == SR:
        return x.astype(np.float32)
    g = np.gcd(SR, sr)
    return signal.resample_poly(x, SR // g, sr // g).astype(np.float32)


def trim(x, thr=0.004, pad=0.03):
    nz = np.where(np.abs(x) > thr)[0]
    p = int(pad * SR)
    return x[max(0, nz[0] - p): nz[-1] + p]


def lp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, "low", fs=SR, output="sos"), x, axis=0).astype(np.float32)


def bp(x, lo, hi, o=2):
    return signal.sosfilt(signal.butter(o, [lo, hi], "band", fs=SR, output="sos"), x, axis=0).astype(np.float32)


def hp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, "high", fs=SR, output="sos"), x, axis=0).astype(np.float32)


# ------------------------------------------------------------------ NARRACIÓN
def kokoro():
    from kokoro_onnx import Kokoro
    return Kokoro(os.path.join(KOKORO_DIR, "kokoro-v1.0.onnx"), os.path.join(KOKORO_DIR, "voices-v1.0.bin"))


def process_voice(x):
    """Cadena de locutor: filtro de graves, EQ de presencia, compresión suave, de-esser."""
    a = os.path.join(TMP, "v_in.wav")
    b = os.path.join(TMP, "v_out.wav")
    sf.write(a, x, SR, subtype="FLOAT")
    sox(a, b,
        "highpass", "75",
        "equalizer", "180", "1.2q", "+1.5",     # cuerpo
        "equalizer", "350", "1.0q", "-1.5",     # menos "caja"
        "equalizer", "3200", "1.0q", "+2.5",    # presencia / inteligibilidad
        "equalizer", "7000", "2.0q", "-2",      # de-esser estático
        "compand", "0.008,0.15", "6:-50,-50,-30,-24,-20,-16,0,-10", "0", "-90", "0.01",
        "norm", "-3")
    y, _ = sf.read(b, dtype="float32")
    # nivelación: misma energía (RMS de los tramos con voz) en todas las escenas
    w = int(0.05 * SR)
    fr = np.array([np.sqrt(np.mean(y[i:i + w] ** 2)) for i in range(0, len(y) - w, w)])
    active = fr[fr > fr.max() * 0.1]
    target = 10 ** (-17 / 20)
    return y * (target / (np.sqrt(np.mean(active ** 2)) + 1e-9))


def tempo(x, ratio):
    """Cambia la duración sin alterar el tono (sox tempo, WSOLA)."""
    if abs(ratio - 1) < 0.005:
        return x
    a = os.path.join(TMP, "t_in.wav")
    b = os.path.join(TMP, "t_out.wav")
    sf.write(a, x, SR, subtype="FLOAT")
    sox(a, b, "tempo", "-s", f"{ratio:.4f}")
    y, _ = sf.read(b, dtype="float32")
    return y


def pauses(x, min_len=0.09):
    """Intervalos de silencio (centro en segundos) dentro de la locución."""
    w = int(0.01 * SR)
    fr = np.array([np.sqrt(np.mean(x[i:i + w] ** 2)) for i in range(0, len(x) - w, w)])
    quiet = fr < fr.max() * 0.04
    out, start = [], None
    for k, q in enumerate(np.append(quiet, False)):
        if q and start is None:
            start = k
        elif not q and start is not None:
            if (k - start) * 0.01 >= min_len:
                out.append(((start + k) / 2 * 0.01, (k - start) * 0.01))
            start = None
    return out


def align_to_subtitles(x, scene, tts, speed):
    """Corta la frase en las pausas que corresponden a cada bloque de subtítulo y
    coloca cada tramo en el instante en que aparece su texto. Devuelve [(seg, audio)]."""
    subs = scene["subtitles"]
    if len(subs) == 1 or tts is None:
        return [(scene["narrationFrom"] / FPS, x)]
    # posición esperada de cada corte: duración de los bloques sintetizados por separado
    lens = []
    for c in subs:
        a, sr = tts.create(c["text"], voice=VOICE, speed=speed, lang="es")
        lens.append(len(trim(to48(a, sr))) / SR)
    scale = (len(x) / SR) / sum(lens)
    expected = np.cumsum(lens)[:-1] * scale
    cand = pauses(x)
    cuts = []
    for e in expected:
        best = min(cand, key=lambda p: abs(p[0] - e), default=None)
        cuts.append(best[0] if best and abs(best[0] - e) < 0.9 else None)
    out, pos, cur_start = [], 0, scene["narrationFrom"] / FPS
    bounds = [c for c in cuts]
    seg_idx = 0
    for k in range(len(subs)):
        if k < len(bounds) and bounds[k] is None:
            continue  # sin pausa natural: el tramo sigue hasta el próximo corte
        end = int(bounds[k] * SR) if k < len(bounds) else len(x)
        seg = x[pos:end]
        nxt = subs[k + 1]["from"] / FPS if k + 1 < len(subs) else (scene["narrationFrom"] + scene["narrationDuration"]) / FPS + 0.35
        start = cur_start
        room = nxt - start - 0.06
        if len(seg) / SR > room:
            seg = tempo(seg, min(1.15, (len(seg) / SR) / room))
        out.append((start, seg))
        print(f"      tramo {seg_idx + 1}: inicio {start:6.2f}s  dur {len(seg) / SR:5.2f}s  (espacio {room:5.2f}s)")
        seg_idx += 1
        pos = end
        cur_start = max(nxt, start + len(seg) / SR + 0.06)
    return out


def make_voice():
    """Devuelve, por escena, una lista de tramos [(inicio_seg, audio)]."""
    tts = None
    voices = []
    for i, s in enumerate(SCENES):
        target = s["narrationDuration"] / FPS
        custom = os.path.join(ROOT, "public", "audio", "voz", f"escena{i + 1}.wav")
        if os.path.exists(custom):
            x, sr = sf.read(custom, dtype="float32")
            x = to48(x if x.ndim == 1 else x.mean(1), sr)
            voices.append([(s["narrationFrom"] / FPS, trim(process_voice(x)))])
            continue
        tts = tts or kokoro()
        speed = 1.0
        for _ in range(3):  # ajuste iterativo de velocidad para encajar en la ventana
            a, sr = tts.create(TEXT[i], voice=VOICE, speed=speed, lang="es")
            x = trim(to48(a, sr))
            d = len(x) / SR
            if abs(d - target) / target < 0.025:
                break
            speed = float(np.clip(speed * d / target, 0.9, 1.12))
        print(f"  escena {i + 1}: voz {d:5.2f}s  ventana {target:5.2f}s  velocidad {speed:.3f}")
        voices.append(align_to_subtitles(process_voice(x), s, tts, speed))
    return voices


# ------------------------------------------------------------------ MÚSICA (estéreo)
def nf(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, a, r):
    e = np.ones(n, np.float32)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    e[:na] = np.linspace(0, 1, na) ** 2
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e


def place(buf, x, sec, g=1.0, pan=0.0):
    i = int(sec * SR)
    if i >= len(buf) or i < 0:
        return
    x = x[: len(buf) - i]
    if x.ndim == 2:
        buf[i: i + len(x)] += x * g
    elif buf.ndim == 2:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        buf[i: i + len(x), 0] += x * g * l * 1.414
        buf[i: i + len(x), 1] += x * g * r * 1.414
    else:
        buf[i: i + len(x)] += x * g


def pad(freqs, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros((n, 2), np.float32)
    for f in freqs:
        for ch, det in ((0, -0.07), (1, 0.07)):
            ff = f * 2 ** (det / 12)
            vib = 1 + 0.002 * np.sin(2 * np.pi * 4.5 * t + ch)
            ph = 2 * np.pi * np.cumsum(ff * vib) / SR
            y[:, ch] += (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)).astype(np.float32)
    y *= env(n, 0.9, 1.0)[:, None]
    return y / (len(freqs) * 1.5)


def piano(f, dur=2.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for k, (a, d) in enumerate([(1, 3.2), (0.45, 4.5), (0.22, 6), (0.1, 8), (0.05, 10)], 1):
        y += a * np.sin(2 * np.pi * f * k * t * (1 + 0.0004 * k * k)) * np.exp(-t * d * (1 + f / 2000))
    y *= env(n, 0.003, 0.3)
    return lp(y.astype(np.float32), 5000)


def make_music():
    m = np.zeros((N + SR * 3, 2), np.float32)
    bpm = 84
    beat = 60 / bpm
    bar = 4 * beat
    prog = [[48, 55, 60, 64], [43, 55, 59, 62], [45, 57, 60, 64], [41, 57, 60, 65]]
    arp = [0, 1, 2, 3, 2, 1, 2, 3]
    for b in range(int(TOTAL / bar) + 2):
        ch = prog[b % 4]
        t0 = b * bar
        place(m, pad([nf(x) for x in ch[1:]], bar + 1.2), t0, 0.32)
        place(m, pad([nf(ch[0] - 12)], bar + 0.8), t0, 0.30)
        for k, idx in enumerate(arp):
            place(m, piano(nf(ch[idx] + 12)), t0 + k * beat / 2, 0.16 * (0.85 + 0.3 * RNG.random()),
                  pan=-0.35 + 0.7 * (idx / 3))
        if t0 > TOTAL * 0.55:
            mel = [ch[3] + 12, ch[2] + 12, ch[3] + 12, ch[1] + 24]
            for k, x in enumerate(mel):
                place(m, piano(nf(x), 2.8), t0 + k * beat, 0.11, pan=0.15)
    a = os.path.join(TMP, "m_in.wav")
    b = os.path.join(TMP, "m_out.wav")
    sf.write(a, m / (np.abs(m).max() + 1e-9) * 0.7, SR, subtype="FLOAT")
    sox(a, b, "reverb", "45", "50", "90", "100", "15", "0", "highpass", "60", "lowpass", "9000")
    y, _ = sf.read(b, dtype="float32")
    y = y[:N]
    t = np.arange(N) / SR
    # crescendo muy suave hacia el final y fundidos
    shape = np.clip(t / 2.5, 0, 1) * (0.8 + 0.2 * np.clip(t / TOTAL, 0, 1)) * np.clip((TOTAL - t) / 3.0, 0, 1)
    return y * shape[:, None]


# ------------------------------------------------------------------ AMBIENTE (estéreo)
def make_ambience():
    a = np.zeros((N + SR * 3, 2), np.float32)
    t = np.arange(len(a)) / SR
    # aire/viento muy suave y continuo (evita silencios digitales)
    w = lp(RNG.standard_normal((len(a), 2)).astype(np.float32), 350)
    w *= (0.7 + 0.3 * np.sin(2 * np.pi * t / 9.0))[:, None]
    a += w * 0.05

    def bird(sec, g, pan):
        for k in range(RNG.integers(2, 5)):
            n = int(RNG.uniform(0.06, 0.12) * SR)
            tt = np.arange(n) / SR
            f0 = RNG.uniform(2600, 4200)
            f = f0 * (1 + RNG.uniform(-0.25, 0.25) * tt / tt[-1])
            x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / tt[-1]) ** 2
            place(a, x.astype(np.float32), sec + k * RNG.uniform(0.1, 0.18), g, pan)

    def cluck(sec, g, pan):
        f = RNG.uniform(500, 700)
        for k in range(RNG.integers(2, 4)):
            n = int(0.09 * SR)
            tt = np.arange(n) / SR
            ff = f * (1.25 - 0.4 * tt / tt[-1])
            src = signal.sawtooth(2 * np.pi * np.cumsum(ff) / SR, 0.3).astype(np.float32)
            x = bp(src, 700, 1900) * 0.8 + bp(src, 2400, 3200) * 0.25
            x *= np.sin(np.pi * tt / tt[-1]) ** 1.5
            place(a, x, sec + k * RNG.uniform(0.17, 0.25), g, pan)

    def grunt(sec, g, pan, f=90):
        n = int(RNG.uniform(0.25, 0.4) * SR)
        tt = np.arange(n) / SR
        ff = f * (1 + 0.1 * np.sin(2 * np.pi * 3 * tt))
        src = signal.sawtooth(2 * np.pi * np.cumsum(ff) / SR).astype(np.float32)
        src *= (0.65 + 0.35 * np.sin(2 * np.pi * 24 * tt)).astype(np.float32)
        x = lp(bp(src, 120, 700), 600) * np.abs(np.sin(np.pi * tt / tt[-1])) ** 0.8
        place(a, x, sec, g, pan)

    def squeal(sec, g, pan):
        n = int(0.2 * SR)
        tt = np.arange(n) / SR
        ff = RNG.uniform(800, 1100) * (1 + 0.25 * np.sin(np.pi * tt / tt[-1]))
        x = bp(signal.sawtooth(2 * np.pi * np.cumsum(ff) / SR).astype(np.float32), 900, 2600)
        place(a, x * np.sin(np.pi * tt / tt[-1]) ** 2, sec, g, pan)

    def truck(sec, dur, g):
        n = int(dur * SR)
        tt = np.arange(n) / SR
        src = signal.sawtooth(2 * np.pi * np.cumsum(36 + 8 * tt / dur) / SR).astype(np.float32)
        x = lp(src, 220, 4) + 0.25 * lp(RNG.standard_normal(n).astype(np.float32), 400)
        x *= env(n, 0.8, 1.6)
        for i in range(0, n, SR // 10):  # paneo de izquierda a derecha
            place(a, x[i: i + SR // 10], sec + i / SR, g, -0.6 + 1.2 * i / n)

    def s(i, off=0.0):
        return SCENES[i]["from"] / FPS + off

    def d(i):
        return SCENES[i]["duration"] / FPS

    for x in np.arange(0.4, d(0), 1.7):
        bird(s(0, x + RNG.uniform(0, 0.8)), 0.05, RNG.uniform(-0.8, 0.8))
    for x in np.arange(0.3, d(1) - 3, 0.8):
        cluck(s(1, x + RNG.uniform(0, 0.4)), 0.07, RNG.uniform(-0.7, 0.7))
    truck(s(1, d(1) - 3.7), 3.6, 0.16)
    for x in np.arange(0.4, d(2), 1.2):
        grunt(s(2, x + RNG.uniform(0, 0.5)), 0.10, RNG.uniform(-0.6, 0.6))
    for x in np.arange(0.9, d(2), 1.8):
        squeal(s(2, x + RNG.uniform(0, 0.6)), 0.025, RNG.uniform(-0.6, 0.6))
    for x in np.arange(0.3, d(3), 1.0):
        grunt(s(3, x + RNG.uniform(0, 0.4)), 0.11, RNG.uniform(-0.7, 0.7), RNG.uniform(70, 95))
    for x in np.arange(0.5, d(4), 2.2):
        bird(s(4, x), 0.03, RNG.uniform(-0.8, 0.8))
    for x in np.arange(0.5, d(5) - 3, 1.5):
        bird(s(5, x + RNG.uniform(0, 0.6)), 0.045, RNG.uniform(-0.8, 0.8))
        if RNG.random() < 0.4:
            cluck(s(5, x + 0.7), 0.03, RNG.uniform(-0.8, 0.8))
    p = os.path.join(TMP, "a_in.wav")
    q = os.path.join(TMP, "a_out.wav")
    sf.write(p, a, SR, subtype="FLOAT")
    sox(p, q, "reverb", "30", "50", "70", "100", "10", "0")
    y, _ = sf.read(q, dtype="float32")
    y = y[:N]
    t = np.arange(N) / SR
    return y * (np.clip(t / 1.5, 0, 1) * np.clip((TOTAL - t) / 3.0, 0, 1))[:, None]


def chime():
    y = np.zeros((int(2.6 * SR), 2), np.float32)
    for k, m in enumerate([72, 76, 79, 84]):
        place(y, piano(nf(m), 2.4), k * 0.09, 0.5, -0.3 + 0.2 * k)
    return y


# ------------------------------------------------------------------ MEZCLA
def follower(x, attack=0.04, release=0.45):
    """Envolvente con ataque/relajación (para el ducking)."""
    e = np.abs(x)
    e = lp(e, 30)
    out = np.empty_like(e)
    a = np.exp(-1 / (attack * SR / 64))
    r = np.exp(-1 / (release * SR / 64))
    v = 0.0
    dec = e[::64]
    res = np.empty_like(dec)
    for i, s in enumerate(dec):
        v = a * v + (1 - a) * s if s > v else r * v + (1 - r) * s
        res[i] = v
    out = np.interp(np.arange(len(e)), np.arange(len(dec)) * 64, res)
    return out.astype(np.float32)


def main():
    print("Generando narración...")
    voices = make_voice()
    voice = np.zeros(N, np.float32)
    for segs in voices:
        for start, seg in segs:
            fade = np.ones(len(seg), np.float32)
            nf_ = min(len(seg) // 4, int(0.012 * SR))
            fade[:nf_] = np.linspace(0, 1, nf_)
            fade[-nf_:] = np.linspace(1, 0, nf_)
            place(voice, seg * fade, start, 1.0)
    print("Generando música y ambiente...")
    music = make_music()
    amb = make_ambience()
    for i, off in ((4, 3.2), (5, SCENES[5]["duration"] / FPS - TM["endCardFrames"] / FPS - 0.2)):
        place(amb, chime() * 0.35, SCENES[i]["from"] / FPS + off, 1.0)

    # ducking: -11 dB a la música y -6 dB al ambiente mientras habla el narrador
    e = follower(voice)
    k = np.clip(e / (np.percentile(e[e > 1e-4], 60) + 1e-9), 0, 1)
    duck_m = 10 ** (-11 * k / 20)
    duck_a = 10 ** (-6 * k / 20)

    v_st = np.stack([voice, voice], 1)
    mix = v_st * 1.0 + music * 0.40 * duck_m[:, None] + amb * 0.65 * duck_a[:, None]

    raw = os.path.join(TMP, "mix_raw.wav")
    sf.write(raw, mix / (np.abs(mix).max() + 1e-9) * 0.5, SR, subtype="FLOAT")
    out = os.path.join(ROOT, "public", "audio", "mix_pro.wav")
    # normalización de sonoridad en dos pasadas (EBU R128): -16 LUFS, TP -1.5 dBTP
    m = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af",
                        "loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    js = json.loads(m[m.rindex("{"): m.rindex("}") + 1])
    flt = (f"loudnorm=I=-16:TP=-1.5:LRA=7:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
           f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true,"
           f"aresample=48000")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", raw, "-af", flt,
                    "-c:a", "pcm_s24le", out], check=True)
    # pistas separadas para verificación
    stems = os.path.join(ROOT, "out", "stems")
    os.makedirs(stems, exist_ok=True)
    sf.write(os.path.join(stems, "voz.wav"), voice, SR, subtype="PCM_24")
    print("OK ->", out)


if __name__ == "__main__":
    sys.exit(main())
