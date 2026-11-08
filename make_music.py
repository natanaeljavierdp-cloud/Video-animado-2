#!/usr/bin/env python3
"""Compose the background music and the stamp hit, timed to video_spec.json.

  * Suspense (scenes 1-6): low D drone, dissonant string pad that swells,
    a slow heartbeat pulse and high shimmering tension; a boom on the stamp.
  * Calm (from the happy family, scene 7): warm D-major pad with a soft
    piano arpeggio, ending on a long fade.

Writes assets/musica.mp3 and assets/golpe.mp3.   Usage: python3 make_music.py
"""
import json
import os
import subprocess

import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SPEC = json.load(open(os.path.join(ROOT, "video_spec.json"), encoding="utf-8"))
SR = 44100
DUR = SPEC["format"]["durationSec"]
CALM_AT = next(s["start"] for s in SPEC["scenes"] if s["id"] == 7)
XFADE = 1.6
rng = np.random.default_rng(3)


def hz(note):
    """MIDI note number -> Hz."""
    return 440.0 * 2 ** ((note - 69) / 12)


def lowpass(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def highpass(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def t_axis(sec):
    return np.arange(int(sec * SR)) / SR


def saw(f, t, phase=0.0):
    return 2 * ((f * t + phase) % 1.0) - 1


def strings(notes, t, cutoff=900, detune=0.004):
    """Detuned-saw string pad, low-passed."""
    out = np.zeros_like(t)
    for n in notes:
        f = hz(n)
        for d in (-detune, 0, detune):
            out += saw(f * (1 + d), t, rng.random())
    vib = 1 + 0.002 * np.sin(2 * np.pi * 5.2 * t)
    return lowpass(out * vib, cutoff) / (3 * len(notes))


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


# ------------------------------------------------------------ suspense
def suspense(sec):
    t = t_axis(sec)
    n = len(t)
    out = np.zeros(n)
    # low drone on D with slow breathing
    drone = np.sin(2 * np.pi * hz(38) * t) + 0.5 * np.sin(2 * np.pi * hz(50) * t)
    drone += 0.35 * lowpass(saw(hz(38), t), 220)
    out += 0.35 * drone * (0.8 + 0.2 * np.sin(2 * np.pi * 0.11 * t))
    # dissonant pad: D minor with a b2 / b6 rub, swelling over time
    pad = strings([62, 65, 69], t, 700) + 0.6 * strings([63, 70], t, 900)
    swell = 0.35 + 0.65 * np.clip(t / sec, 0, 1) ** 1.3
    out += 0.45 * pad * swell * (0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t))
    # high shimmer (tension) - tremolo on a minor second
    sh = np.sin(2 * np.pi * hz(86) * t) + np.sin(2 * np.pi * hz(87) * t)
    out += 0.035 * sh * (0.5 + 0.5 * np.sin(2 * np.pi * 6.5 * t)) * swell
    # heartbeat: lub-dub every 1.1 s, slowly speeding up
    beat_t, period = 0.6, 1.15
    while beat_t < sec - 0.3:
        for off, amp in ((0.0, 1.0), (0.22, 0.6)):
            s = int((beat_t + off) * SR)
            k = t_axis(0.35)
            f = 48 + 40 * np.exp(-k * 25)
            hit = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-k * 11)
            e = min(n, s + len(k))
            out[s:e] += 0.55 * amp * hit[: e - s]
        beat_t += period
        period = max(0.82, period * 0.992)
    return out


# ------------------------------------------------------------ calm
def piano(f, sec):
    t = t_axis(sec)
    tone = sum(a * np.sin(2 * np.pi * f * h * t) for h, a in ((1, 1), (2, 0.45), (3, 0.18), (4, 0.08)))
    return tone * np.exp(-t * 2.2) * env_adsr(len(t), 0.004, 0.05)


def calm(sec):
    t = t_axis(sec)
    n = len(t)
    out = np.zeros(n)
    # D - A - Bm - G, two seconds each
    chords = [(50, [62, 66, 69]), (45, [61, 64, 69]), (47, [62, 66, 71]), (43, [62, 67, 71])]
    bar = 2.4
    i = 0
    while i * bar < sec:
        root, notes = chords[i % 4]
        s = int(i * bar * SR)
        seg = t_axis(bar + 0.6)
        pad = strings(notes, seg, 1400, 0.003) * env_adsr(len(seg), 0.5, 0.7)
        bass = np.sin(2 * np.pi * hz(root) * seg) * env_adsr(len(seg), 0.08, 0.7)
        chunk = 0.42 * pad + 0.3 * bass
        # soft arpeggio, eighth notes
        arp = [notes[0] + 12, notes[1] + 12, notes[2] + 12, notes[1] + 12]
        for j in range(8):
            p = piano(hz(arp[j % 4]), 1.6)
            a = int(j * bar / 8 * SR)
            e = min(len(chunk), a + len(p))
            chunk[a:e] += 0.12 * p[: e - a]
        e = min(n, s + len(chunk))
        out[s:e] += chunk[: e - s]
        i += 1
    return out


def boom(sec=1.6):
    """Stamp hit: low sub drop + noise crack."""
    t = t_axis(sec)
    f = 40 + 90 * np.exp(-t * 18)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    crack = highpass(rng.standard_normal(len(t)), 900) * np.exp(-t * 28)
    body = lowpass(rng.standard_normal(len(t)), 300) * np.exp(-t * 9)
    return 0.9 * sub + 0.35 * crack + 0.5 * body


def save_mp3(x, path):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.89
    stereo = np.stack([x, x], axis=1)
    tmp = path[:-4] + ".wav"
    wavfile.write(tmp, SR, (stereo * 32767).astype(np.int16))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-b:a", "192k", path],
                   check=True)
    os.remove(tmp)


def main():
    total = int(DUR * SR)
    a = suspense(CALM_AT + XFADE)
    b = calm(DUR - CALM_AT + 0.5)
    mix = np.zeros(total)
    # suspense, fading out across the cut to the happy family
    na = min(len(a), total)
    fa = np.ones(na)
    x0 = int((CALM_AT - 0.4) * SR)
    fa[x0:] = np.linspace(1, 0, na - x0) ** 1.5
    mix[:na] += a[:na] * fa
    # calm, fading in
    s = int((CALM_AT - 0.4) * SR)
    nb = min(len(b), total - s)
    fb = np.ones(nb)
    fb[: int(XFADE * SR)] = np.linspace(0, 1, int(XFADE * SR))
    mix[s:s + nb] += 0.7 * b[:nb] * fb
    # final fade-out
    fo = int(2.5 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)
    # gentle overall low-pass to keep it under the voice
    mix = lowpass(mix, 5000)
    save_mp3(mix, os.path.join(ROOT, "assets/musica.mp3"))
    save_mp3(boom(), os.path.join(ROOT, "assets/golpe.mp3"))
    print(f"musica.mp3: {DUR}s (suspenso hasta {CALM_AT}s, luego tranquila) · golpe.mp3")


if __name__ == "__main__":
    main()
