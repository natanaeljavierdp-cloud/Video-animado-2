"""Genera la banda sonora: música de suspenso/documental + efectos (whoosh,
impacto, tic-tac, etc.) sintetizados desde cero (100 % libres de derechos),
y la mezcla con la narración. Salida: build/mix.wav
Uso: python3 audio.py
"""
import os, subprocess, wave
import numpy as np
from scipy import signal
from timeline import *

SR = 48000
rng = np.random.default_rng(7)
BUILD = os.path.join(HERE, "build")
os.makedirs(BUILD, exist_ok=True)
N = int((TOTAL + 0.5) * SR)


def t_arr(d):
    return np.arange(int(d * SR)) / SR


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def reverb(x, secs=1.6, mix=0.25):
    ir = rng.standard_normal(int(secs * SR)) * np.exp(-np.linspace(0, 7, int(secs * SR)))
    ir = lp(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    wet = signal.fftconvolve(x, ir)[: len(x) + len(ir)]
    out = np.zeros(len(wet))
    out[: len(x)] += x * (1 - mix)
    return out + wet * mix


# ------------------------------------------------------------------ música
def saw(f, t):
    return 2 * ((f * t) % 1.0) - 1


def build_music():
    L = np.zeros(N); R = np.zeros(N)
    bpm = 84; beat = 60 / bpm
    # Dm - Bb - Gm - A  (re menor, tono documental)
    chords = [[50, 53, 57], [46, 50, 53], [43, 46, 50], [45, 49, 52]]
    bar_len = beat * 8  # 2 compases por acorde
    t = np.arange(N) / SR

    # sección/intensidad
    def env_section(tt):
        e = np.ones_like(tt)
        e = np.where(tt < S2[0], 0.55, e)
        e = np.where((tt >= S6[0]) & (tt < S7[0]), 0.45, e)
        e = np.where(tt >= CLOSE_START + 3.2, np.clip(1 - (tt - CLOSE_START - 3.2) / 1.7, 0, 1), e)
        return signal.sosfiltfilt(signal.butter(1, 1.5, "low", fs=SR, output="sos"), e)

    sec = env_section(t)

    # drone grave (re)
    drone = 0.5 * np.sin(2 * np.pi * midi(26) * t) + 0.25 * np.sin(2 * np.pi * midi(38) * t + 0.3)
    drone *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t) ** 2
    L += drone * 0.35; R += drone * 0.35

    # pad (sierras desafinadas filtradas)
    pad = np.zeros(N)
    nchord = int(np.ceil(TOTAL / bar_len)) + 1
    for i in range(nchord):
        c = chords[i % 4]
        s0 = int(i * bar_len * SR); s1 = min(N, int(((i + 1) * bar_len + 0.6) * SR))
        if s0 >= N: break
        tt = np.arange(s1 - s0) / SR
        v = np.zeros(s1 - s0)
        for n in c:
            for det in (-0.08, 0.08):
                v += saw(midi(n + 12) * 2 ** (det / 12), tt)
        a = np.clip(tt / 0.8, 0, 1) * np.clip((tt[-1] - tt) / 0.6, 0, 1)
        pad[s0:s1] += v * a
    pad = lp(pad, 900, 4) * 0.07
    L += pad * 1.0; R += np.roll(pad, int(0.012 * SR))

    # pulso de bajo en corcheas (desde la noticia)
    bass = np.zeros(N)
    e8 = beat / 2
    k = 0
    while k * e8 < TOTAL:
        st = k * e8
        c = chords[int(st // bar_len) % 4]
        root = c[0] - 24 + (12 if c[0] < 46 else 0)
        n = int(0.32 * SR); s0 = int(st * SR)
        if s0 + n < N:
            tt = np.arange(n) / SR
            v = np.tanh(1.8 * (np.sin(2 * np.pi * midi(root) * tt) + 0.3 * saw(midi(root), tt)))
            v *= np.exp(-tt * 9) * (1.0 if k % 2 == 0 else 0.65)
            bass[s0:s0 + n] += v
        k += 1
    bass = lp(bass, 400) * 0.22
    bass *= (t >= S2[0] - 0.05) * 1.0
    L += bass; R += bass

    # arpegio pluck (agudo, misterioso)
    arp = np.zeros(N)
    k = 0
    pattern = [0, 2, 1, 2, 0, 2, 1, 2]
    while k * e8 < TOTAL:
        st = k * e8
        c = chords[int(st // bar_len) % 4]
        note = c[pattern[k % 8]] + 24
        n = int(0.6 * SR); s0 = int(st * SR)
        if s0 + n < N:
            tt = np.arange(n) / SR
            f = midi(note)
            v = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.1 * np.sin(6 * np.pi * f * tt))
            v *= np.exp(-tt * 7)
            arp[s0:s0 + n] += v
        k += 1
    arp = reverb(arp, 2.0, 0.35)[:N] * 0.05
    arp *= ((t >= S2[0]) & ((t < S6[0]) | (t >= S7[0]))) * 1.0
    arp = signal.sosfiltfilt(signal.butter(1, 4, "low", fs=SR, output="sos"), arp)  # suaviza cortes
    L += arp; R += np.roll(arp, int(0.02 * SR))

    # golpe de "taiko" suave en cada cambio de escena
    for c in CUTS:
        n = int(1.2 * SR); s0 = int(c * SR)
        tt = np.arange(n) / SR
        v = np.sin(2 * np.pi * (60 * np.exp(-tt * 3) + 38) * tt) * np.exp(-tt * 4)
        L[s0:s0 + n] += v * 0.25; R[s0:s0 + n] += v * 0.25

    # acorde final (re mayor) en el cierre
    s0 = int((CLOSE_START + 0.2) * SR); n = N - s0
    tt = np.arange(n) / SR
    v = sum(np.sin(2 * np.pi * midi(m) * tt) for m in (50, 54, 57, 62, 66))
    v *= np.clip(tt / 0.3, 0, 1) * np.exp(-tt * 0.6) * 0.08
    L[s0:] += v; R[s0:] += v

    L *= sec; R *= sec
    return np.stack([L, R])


# ------------------------------------------------------------------ efectos
def whoosh(d=0.55, up=True):
    n = int(d * SR); tt = np.arange(n) / SR
    noise = rng.standard_normal(n)
    bands = np.geomspace(250, 7000, 12)
    out = np.zeros(n)
    for i in range(len(bands) - 1):
        b = bp(noise, bands[i], bands[i + 1])
        frac = i / (len(bands) - 2)
        center = (0.25 + 0.5 * frac if up else 0.75 - 0.5 * frac) * d
        out += b * np.exp(-((tt - center) / (0.18 * d)) ** 2)
    env = np.sin(np.pi * np.clip(tt / d, 0, 1)) ** 1.5
    out *= env
    out /= np.max(np.abs(out)) + 1e-9
    pan = np.linspace(-0.7, 0.7, n)
    return np.stack([out * (1 - pan) / 2 * 1.4, out * (1 + pan) / 2 * 1.4])


def impact():
    n = int(2.2 * SR); tt = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(30 + 70 * np.exp(-tt * 9)) / SR) * np.exp(-tt * 2.2)
    crack = lp(rng.standard_normal(n), 3500) * np.exp(-tt * 18)
    body = bp(rng.standard_normal(n), 80, 600) * np.exp(-tt * 6)
    x = np.tanh(1.5 * (sub * 1.0 + crack * 0.6 + body * 0.5))
    x = reverb(x, 2.0, 0.3)[:n]
    x /= np.max(np.abs(x))
    return np.stack([x, x])


def shatter():
    n = int(1.0 * SR); x = np.zeros(n)
    for _ in range(70):
        s = int(rng.uniform(0, 0.55) ** 1.6 * SR)
        m = int(0.08 * SR)
        if s + m >= n: continue
        tt = np.arange(m) / SR
        f = rng.uniform(2500, 7500)
        x[s:s + m] += (np.sin(2 * np.pi * f * tt) * 0.5 + rng.standard_normal(m) * 0.5) * np.exp(-tt * rng.uniform(40, 90)) * rng.uniform(0.2, 1)
    x = hp(x, 1800)
    x = reverb(x, 1.0, 0.25)[:n]
    x /= np.max(np.abs(x))
    return np.stack([np.roll(x, 200), x])


def riser(d=1.1):
    n = int(d * SR); tt = np.arange(n) / SR
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    bands = np.geomspace(300, 9000, 10)
    for i in range(len(bands) - 1):
        out += bp(noise, bands[i], bands[i + 1]) * np.clip((tt / d) * 1.4 - i / 12, 0, 1)
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * (tt / d) ** 2) / SR) * 0.25
    out = (out / (np.max(np.abs(out)) + 1e-9) + tone) * (tt / d) ** 2
    return np.stack([out, out])


def pop(f=700):
    n = int(0.12 * SR); tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.6 * tt / 0.12)) / SR) * np.exp(-tt * 40)
    return np.stack([x, x])


def tick(f=2600):
    n = int(0.06 * SR); tt = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * tt) * 0.6 + bp(rng.standard_normal(n), f * 0.8, f * 1.6) * 0.6) * np.exp(-tt * 120)
    x = reverb(x, 0.4, 0.2)[:n + int(0.1 * SR)]
    return np.stack([x, x])


def ding():
    n = int(1.4 * SR); tt = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * k) for f, a, k in
            ((1318.5, 1, 3), (1975.5, 0.5, 4), (2637, 0.3, 6), (3951, 0.12, 9)))
    x *= np.clip(tt / 0.004, 0, 1)
    return np.stack([x, x])


def thud():
    n = int(0.8 * SR); tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * np.cumsum(70 + 120 * np.exp(-tt * 25)) / SR) * np.exp(-tt * 9)
    x += lp(rng.standard_normal(n), 1500) * np.exp(-tt * 35) * 0.7
    x = np.tanh(2 * x)
    return np.stack([x, x])


def build_sfx():
    out = np.zeros((2, N))

    def add(clip, at, gain_db):
        s = int(at * SR)
        if s < 0:
            clip = clip[:, -s:]; s = 0
        e = min(N, s + clip.shape[1])
        out[:, s:e] += clip[:, : e - s] * 10 ** (gain_db / 20)

    # transiciones rápidas (whoosh)
    for c in CUTS:
        add(whoosh(0.55), c - 0.3, -10)
    add(whoosh(0.7, up=False), T["por_fin"] + 0.1, -13)      # cortina fábrica→familia
    # escena 1
    for i in range(14):                                      # contador 0→83
        add(tick(3200), 0.12 + i * 0.075, -24)
    add(thud(), 1.18, -12)
    for i in range(6):
        add(pop(620 + i * 40), 2.75 + i * 0.12, -18)
    add(pop(950), T["descansar"] + 0.05, -15)
    add(riser(1.0), T["acabo"] - 1.0, -16)
    add(impact(), T["acabo"], -3)
    add(shatter(), T["acabo"] + 0.02, -9)
    # escena 2
    add(whoosh(0.4), T["lula"] - 0.15, -16)
    add(whoosh(0.45), T["decreto"] - 0.2, -15)
    add(thud(), T["vigente"] + 0.25, -6)
    # escena 3
    add(thud(), T["que_cambia"] + 0.05, -14)
    for k in ("h44", "h42", "h40"):
        add(whoosh(0.4), T[k] - 0.35, -20)
        add(pop(820), T[k] + 0.1, -16)
    add(pop(700), T["dos_dias"], -16); add(pop(880), T["dos_dias"] + 0.25, -16)
    add(ding(), T["sin_bajar"] + 0.45, -12)
    # escena 4
    for i in range(18):
        add(tick(3000), T["m15"] + i * 0.07, -25)
    add(thud(), T["m15"] + 1.3, -12)
    for i in range(10):
        add(pop(500 + i * 35), T["m15"] + 1.0 + i * 0.2, -24)
    # escena 5
    for k in ("brasil", "colombia", "chile", "mexico", "eeuu"):
        add(pop(760), T[k], -15)
    add(pop(980), T["h40mx"], -17)
    add(whoosh(0.5), T["ranking"] - 0.2, -14)
    add(whoosh(0.35, up=False), T["ranking"] + 0.95, -18)
    # escena 6: tic-tac de reloj
    t = S6[0] + 0.2; i = 0
    while t < S6[1] - 0.15:
        add(tick(2500 if i % 2 == 0 else 1900), t, -13)
        t += 0.5; i += 1
    # escena 7
    for i in range(4):
        add(pop(650 + i * 60), T["cuantos"] + 0.2 + i * 0.22, -16)
    add(pop(900), T["te_leo"], -14); add(pop(1000), T["te_leo"] + 0.35, -18)
    # escena 8
    add(ding(), CLOSE_START + 0.9, -14)
    return out


def read_narr():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(HERE, "assets/narracion.mp3"),
                          "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).T.astype(np.float64)
    out = np.zeros((2, N)); out[:, : min(N, x.shape[1])] = x[:, :N]
    return out


def rms_active(x):
    m = x.mean(0)
    fr = m[: len(m) // 2400 * 2400].reshape(-1, 2400)
    r = np.sqrt((fr ** 2).mean(1))
    act = r[r > r.max() * 0.08]
    return np.sqrt((act ** 2).mean())


def main():
    narr = read_narr()
    music = build_music()
    sfx = build_sfx()
    vr = rms_active(narr)
    # música a -20 dB respecto a la voz (medido en RMS de las partes habladas)
    music *= (vr * 10 ** (-20 / 20)) / (np.sqrt((music[:, int(10 * SR):int(50 * SR)] ** 2).mean()) + 1e-12)
    sfx *= vr / 0.25  # efectos referenciados al nivel de la voz
    mix = narr + music + sfx
    mix = np.tanh(mix / 0.98) * 0.98 if np.max(np.abs(mix)) > 0.98 else mix
    path = os.path.join(BUILD, "mix_raw.wav")
    pcm = (np.clip(mix.T, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    # normalización a -14 LUFS (redes sociales) con limitador
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), os.path.join(BUILD, "mix.wav")], check=True)
    print("ok", os.path.join(BUILD, "mix.wav"))


if __name__ == "__main__":
    main()
