"""Genera la música de suspenso (latido + cuerdas tensas que suben) y los efectos.

Uso: python3 audio.py <carpeta_salida>
Crea musica.wav y sfx.wav (44.1 kHz, estéreo) de la duración total del video.
"""
import sys, os
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import *

SR = 44100
N = int(TOTAL * SR) + SR
t = np.arange(N) / SR
rng = np.random.default_rng(7)
CLIMAX = 68.6


def lp(x, f, order=2):
    return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)


def env_ramp(times, vals):
    return np.interp(t, times, vals)


def reverb(x, secs=2.2, wet=0.35, seed=1):
    r = np.random.default_rng(seed)
    n = int(secs * SR)
    ir = r.standard_normal(n) * np.exp(-np.linspace(0, 7, n))
    ir = lp(ir, 5000)
    ir /= np.sqrt((ir ** 2).sum())
    y = fftconvolve(x, ir)[:len(x)]
    return x * (1 - wet) + y * wet * 3


# ---------------------------------------------------------------- MÚSICA
def heartbeat():
    out = np.zeros(N)
    # intervalo entre latidos: 60 bpm -> ~112 bpm en el clímax
    cur = 0.35
    beats = []
    while cur < CLIMAX - 0.05:
        beats.append(cur)
        p = cur / CLIMAX
        cur += 1.0 - 0.47 * p ** 1.3
    # durante la pregunta: latido lento y suspendido
    cur = CLIMAX + 0.9
    while cur < MAIN_END - 0.6:
        beats.append(cur); cur += 1.15

    def thump(amp, f0, f1, dur):
        n = int(dur * SR); tt = np.arange(n) / SR
        f = f1 + (f0 - f1) * np.exp(-tt * 28)
        ph = 2 * np.pi * np.cumsum(f) / SR
        s = np.sin(ph) * np.exp(-tt * 9) * amp
        click = lp(rng.standard_normal(n), 900) * np.exp(-tt * 120) * amp * 0.25
        return np.tanh((s + click) * 1.8)

    for b in beats:
        p = min(b / CLIMAX, 1.0)
        a = 0.55 + 0.45 * p
        for off, k in ((0.0, 1.0), (0.21 - 0.05 * p, 0.7)):
            s = thump(a * k, 120, 46, 0.45)
            i = int((b + off) * SR)
            out[i:i + len(s)] += s[:max(0, N - i)]
    return lp(out, 400)


def string_section():
    """Cluster de cuerdas: sierras desafinadas, trémolo, tono que sube."""
    # semitonos de transposición global en el tiempo: sube por escenas y glissa al final
    tp = env_ramp([0, 16, 21.7, 46.6, 50.7, 59.4, CLIMAX, CLIMAX + 0.01, TOTAL],
                  [0, 0, 1, 2, 3, 4, 9, 9, 9])
    # notas base (Re menor + tensión): D3 A3 F4 + G#4 (tritono) desde escena 4
    voices = [(146.83, 0.0, 1.0), (220.0, 0.0, 0.8), (349.23, 4.0, 0.6),
              (415.30, 21.7, 0.5), (73.42, 0.0, 0.9), (587.33, 46.6, 0.35),
              (622.25, 59.4, 0.3)]
    out = np.zeros(N)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t)
    for f, start, amp in voices:
        v = np.zeros(N)
        for d in (-0.09, -0.03, 0.03, 0.09):
            f_t = f * 2 ** ((tp + d * 0.5) / 12) * vib * (1 + d * 0.01)
            ph = np.cumsum(f_t) / SR + rng.random()
            v += 2 * (ph % 1) - 1
        fade = np.clip((t - start) / 3.0, 0, 1)
        out += v * amp * fade
    out = lp(out, 2600, 4)
    out = hp(out, 60)
    # trémolo que se acelera (7 Hz -> 14 Hz)
    trem_rate = env_ramp([0, CLIMAX, TOTAL], [7, 14, 14])
    trem = 0.6 + 0.4 * np.abs(np.sin(np.pi * np.cumsum(trem_rate) / SR))
    trem_mix = env_ramp([0, 20, 46, CLIMAX, TOTAL], [0.2, 0.4, 0.7, 1.0, 1.0])
    out *= (1 - trem_mix) + trem_mix * trem
    return out


def sub_drone():
    f = 36.71 * 2 ** (env_ramp([0, CLIMAX, TOTAL], [0, 3, 3]) / 12)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) + 0.3 * np.sin(2 * ph)


def high_harmonic():
    f = 1174.66 * 2 ** (env_ramp([0, 59.4, CLIMAX, TOTAL], [0, 0, 5, 5]) / 12)
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.006 * np.sin(2 * np.pi * 6 * t))) / SR
    return np.sin(ph) * (0.7 + 0.3 * np.sin(2 * np.pi * 11 * t))


def make_music():
    strings = string_section()
    # crescendo general hasta la pregunta, sostén suspendido, corte al cierre
    s_env = env_ramp([0, 3, 16, 46, 59.4, CLIMAX - 0.05, CLIMAX, CLIMAX + 0.6, MAIN_END - 0.4, MAIN_END + 0.6, TOTAL],
                     [0.10, 0.16, 0.22, 0.33, 0.45, 0.85, 0.0, 0.32, 0.32, 0.0, 0.0])
    h_env = env_ramp([0, 46.6, 50, CLIMAX - 0.05, CLIMAX, CLIMAX + 0.3, MAIN_END, MAIN_END + 0.4, TOTAL],
                     [0, 0, 0.05, 0.12, 0.0, 0.10, 0.10, 0, 0])
    d_env = env_ramp([0, 2, CLIMAX - 0.05, CLIMAX, CLIMAX + 0.5, MAIN_END, MAIN_END + 0.5, TOTAL],
                     [0.15, 0.25, 0.45, 0.6, 0.35, 0.35, 0.0, 0.0])
    hb_env = env_ramp([0, CLIMAX, MAIN_END, MAIN_END + 0.3, TOTAL], [0.7, 1.0, 0.8, 0, 0])
    mono = strings * s_env * 0.55 + high_harmonic() * h_env * 0.5 + sub_drone() * d_env * 0.5
    mono = reverb(mono, 2.8, 0.45)
    hb = heartbeat() * hb_env * 2.6
    # estéreo: cuerdas abiertas con pequeño retardo, latido al centro
    d = int(0.013 * SR)
    L = mono + hb
    R = np.concatenate([np.zeros(d), mono[:-d]]) + hb
    st = np.stack([L, R], 1)
    st = st / np.percentile(np.abs(st), 99.5)
    return np.tanh(st * 0.9) * 0.85


# ---------------------------------------------------------------- EFECTOS
def sfx_impact(soft=False):
    dur = 2.5; n = int(dur * SR); tt = np.arange(n) / SR
    f = 32 + 70 * np.exp(-tt * 9)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * (2.2 if not soft else 4))
    noise = lp(rng.standard_normal(n), 2500) * np.exp(-tt * 18)
    x = np.tanh((boom * 1.4 + noise * 0.5) * 1.5)
    x = reverb(np.concatenate([x, np.zeros(SR)]), 2.5, 0.4, 3)
    return x * (0.55 if soft else 1.0)


def sfx_stamp():
    n = int(0.9 * SR); tt = np.arange(n) / SR
    thud = np.sin(2 * np.pi * np.cumsum(90 + 120 * np.exp(-tt * 40)) / SR) * np.exp(-tt * 14)
    crack = hp(rng.standard_normal(n), 1500) * np.exp(-tt * 70)
    return reverb(np.tanh(thud * 1.6 + crack * 0.6), 0.8, 0.25, 4) * 0.9


def sfx_whoosh(dur=0.55, strong=False):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    # barrido de banda: segmentos con frecuencia central que sube y baja
    seg = 256
    centers = 400 + 3800 * np.sin(np.pi * np.linspace(0, 1, n // seg + 1)) ** 2
    zi_sig = bp(x, 300, 6000)
    for k in range(n // seg):
        c = centers[k]
        lo, hi = c * 0.6, min(c * 1.6, 15000)
        a, b = k * seg, (k + 1) * seg
        out[a:b] = zi_sig[a:b] * (c / 4200)
    out = lp(out, 7000)
    env = np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 2
    return out * env * (0.9 if strong else 0.5)


def sfx_pop():
    n = int(0.18 * SR); tt = np.arange(n) / SR
    f = 500 + 900 * (1 - np.exp(-tt * 60))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 30) * 0.35


def sfx_ping():
    n = int(1.4 * SR); tt = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 1318 * tt) + 0.4 * np.sin(2 * np.pi * 2637 * tt)) * np.exp(-tt * 5)
    return reverb(x, 1.2, 0.3, 5) * 0.28


def sfx_glitch():
    n = int(0.45 * SR)
    x = rng.standard_normal(n)
    x = np.round(x * 3) / 3                       # bit crush
    gate = np.repeat(rng.random(n // 400 + 1) > 0.35, 400)[:n]
    tone = np.sign(np.sin(2 * np.pi * 180 * np.arange(n) / SR)) * 0.4
    y = (bp(x, 800, 6000) + tone) * gate
    return y * np.linspace(1, 0.3, n) * 0.4


def sfx_counter():
    out = np.zeros(int(1.4 * SR))
    tick_n = int(0.02 * SR); tt = np.arange(tick_n) / SR
    tick = hp(rng.standard_normal(tick_n), 3000) * np.exp(-tt * 300)
    for k in range(22):
        i = int((k * 0.06) * SR)
        out[i:i + tick_n] += tick * 0.5
    return out


def sfx_riser(dur=1.0):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = 200 * 2 ** (tt / dur * 3)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3 + hp(rng.standard_normal(n), 2000) * 0.25
    return x * (tt / dur) ** 2 * 0.6


def make_sfx():
    out = np.zeros(N)

    def put(x, at):
        i = int(at * SR)
        if i < 0:
            x = x[-i:]; i = 0
        m = min(len(x), N - i)
        out[i:i + m] += x[:m]

    for c in SCENE_CUTS:
        w = sfx_whoosh(0.6, True); put(w, c - 0.38)
    for c in SHOT_CUTS:
        w = sfx_whoosh(0.4); put(w, c - 0.22)
    for at, kind in HITS:
        x = {"impact": lambda: sfx_impact(),
             "impact_soft": lambda: sfx_impact(True),
             "stamp": sfx_stamp, "pop": sfx_pop, "ping": sfx_ping,
             "glitch": sfx_glitch, "counter": sfx_counter,
             "riser_short": lambda: sfx_riser(0.9)}[kind]()
        put(x, at)
    # whoosh de entrada al cierre
    put(sfx_whoosh(0.7, True), MAIN_END - 0.4)
    st = np.stack([out, out], 1)
    return st / np.abs(st).max() * 0.9


if __name__ == "__main__":
    od = sys.argv[1]
    os.makedirs(od, exist_ok=True)
    wavfile.write(os.path.join(od, "musica.wav"), SR, (make_music() * 32767).astype(np.int16))
    wavfile.write(os.path.join(od, "sfx.wav"), SR, (make_sfx() * 32767).astype(np.int16))
    print("ok")
