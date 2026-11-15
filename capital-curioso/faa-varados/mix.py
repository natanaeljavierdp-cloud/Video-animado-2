# -*- coding: utf-8 -*-
"""Mezcla de audio: narracion + musica (con ducking) + efectos sintetizados.
Uso: python3 mix.py <voz.mp3> <musica.mp3> <salida.wav>
"""
import subprocess, sys, wave
import numpy as np

SR = 48000
VOFF, TOTAL, OUTRO = 0.5, 76.0, 70.95
WIPES = [6.3, 17.0, 23.3, 31.25, 43.0, 54.2, 61.5, OUTRO]
rng = np.random.default_rng(7)

def decode(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()

N = int(TOTAL * SR)
def place(buf, snd, t, gain=1.0):
    i = int(t * SR)
    if snd.ndim == 1: snd = np.stack([snd, snd], 1)
    j = min(N, i + len(snd))
    if j > i >= 0: buf[i:j] += snd[:j - i] * gain

def onepole_lp(x, cut):
    """filtro paso bajo de un polo con frecuencia de corte variable (array)."""
    a = np.exp(-2 * np.pi * cut / SR)
    y = np.zeros_like(x); s = 0.0
    for n in range(len(x)):
        s = (1 - a[n]) * x[n] + a[n] * s
        y[n] = s
    return y

def whoosh(d=0.75):
    n = int(d * SR); t = np.arange(n) / n
    noise = rng.standard_normal(n)
    cut = 300 + 5000 * np.sin(np.pi * t) ** 2
    lp = onepole_lp(noise, cut)
    lp2 = onepole_lp(noise, cut * 0.35)
    band = lp - lp2
    env = np.sin(np.pi * t ** 0.8) ** 2
    s = band * env
    pan = np.linspace(-0.7, 0.7, n)
    st = np.stack([s * (1 - pan) / 2, s * (1 + pan) / 2], 1)
    return st / np.abs(st).max()

def bell(f, d=1.8):
    n = int(d * SR); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2) + 0.35 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 3.5)
         + 0.12 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 6))
    s *= np.minimum(1, t / 0.004)
    return s

def ding():
    out = np.zeros(int(2.6 * SR))
    for k, f in enumerate((659.25, 523.25, 783.99)):
        b = bell(f); i = int(k * 0.32 * SR); out[i:i + len(b)] += b
    return out / np.abs(out).max()

def tic():
    n = int(0.03 * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 260) + 0.4 * rng.standard_normal(n) * np.exp(-t * 600)
    return s / np.abs(s).max()

def thud():
    n = int(0.35 * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * (90 * np.exp(-t * 6) + 45) * t) * np.exp(-t * 14) + 0.3 * rng.standard_normal(n) * np.exp(-t * 80)
    return s / np.abs(s).max()

def movavg(x, w):
    c = np.cumsum(np.concatenate([np.zeros(w // 2 + 1), x, np.zeros(w)]))
    return (c[w:w + len(x)] - c[:len(x)]) / w

def main():
    vpath, mpath, out = sys.argv[1:4]
    voice = decode(vpath); music = decode(mpath)
    V = np.zeros((N, 2), np.float32); place(V, voice, VOFF)
    M = np.zeros((N, 2), np.float32); M[:min(N, len(music))] = music[:N]
    M /= np.abs(M).max()
    FX = np.zeros((N, 2), np.float32)

    # ---- efectos
    place(FX, ding(), 0.03, 0.55)
    wh = whoosh()
    for T in WIPES:
        place(FX, wh, T + VOFF - 0.42, 0.42)
    tk = tic()
    for k in range(1, 20):                        # contador 0 -> 19
        place(FX, tk, VOFF + 19.2 + 0.96 * (k - 0.5) / 19, 0.30)
    for val, t0 in ((12, 21.5), (7, 22.74)):      # barras salidas / llegadas (ease-out)
        for k in range(1, val + 1):
            x = 1 - (1 - (k - 0.5) / val) ** (1 / 3)
            place(FX, tk, VOFF + t0 + 0.7 * x, 0.22)
    place(FX, tk, VOFF + 49.42, 0.3)                # "2 dias"
    th = thud()
    for ts in (41.0, 41.54):                      # sello de migracion
        place(FX, th, VOFF + ts, 0.5)

    # ---- ducking de la musica segun la voz
    env = np.abs(V).mean(1)
    win = int(0.05 * SR)
    env = movavg(env, win)
    act = (env > 0.01).astype(np.float32)
    rel = int(0.4 * SR)
    act = movavg(act, rel); act = np.clip(act * 1.5, 0, 1)
    t = np.arange(N) / SR
    g = 0.20 - 0.09 * act                             # ~ -14 dB / -21 dB debajo de la voz
    g *= np.clip(t / 1.2, 0, 1)                        # entrada suave
    outro = np.clip((t - (OUTRO + VOFF)) / 0.8, 0, 1)
    g = g * (1 - outro) + 0.42 * outro                 # sube en el cierre
    g *= np.clip((TOTAL - t) / 1.6, 0, 1)              # fade out final
    mix = V * 1.0 + M * g[:, None] + FX
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)            # limitador suave
    mix *= 0.93 / np.abs(mix).max()
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(out, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

if __name__ == '__main__':
    main()
