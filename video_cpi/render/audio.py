"""Builds voice (with inserted silences), synthesized suspense score and SFX, and mixes them."""
import subprocess, numpy as np
from scipy.signal import fftconvolve, butter, sosfilt
from plan import *

SR = 44100
N = int(TOTAL * SR) + SR
rng = np.random.default_rng(7)
t_all = np.arange(N) / SR


def lp(x, f, o=2):
    return sosfilt(butter(o, f, "low", fs=SR, output="sos"), x, axis=0)


def hp(x, f, o=2):
    return sosfilt(butter(o, f, "high", fs=SR, output="sos"), x, axis=0)


def bp(x, lo, hi, o=2):
    return sosfilt(butter(o, [lo, hi], "band", fs=SR, output="sos"), x, axis=0)


def reverb(x, secs=2.4, decay=3.5, wet=0.35, seed=1):
    r = np.random.default_rng(seed)
    n = int(secs * SR); tt = np.arange(n) / SR
    env = np.exp(-decay * tt)
    irL = r.standard_normal(n) * env; irR = r.standard_normal(n) * env
    irL = lp(irL, 5000); irR = lp(irR, 5000)
    irL /= np.sqrt((irL ** 2).sum()); irR /= np.sqrt((irR ** 2).sum())
    mono = x if x.ndim == 1 else x.mean(1)
    L = fftconvolve(mono, irL)[: len(mono)]; R = fftconvolve(mono, irR)[: len(mono)]
    dry = np.stack([mono, mono], 1) if x.ndim == 1 else x
    return dry * (1 - wet) + np.stack([L, R], 1) * wet


# ------------------------------------------------------------------ voice
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", VOICE, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                     capture_output=True).stdout
v = np.frombuffer(raw, np.float32).astype(np.float64)
parts, last = [], 0
for p, g in GAPS:
    i = int(p * SR); parts += [v[last:i], np.zeros(int(g * SR))]; last = i
parts.append(v[last:])
voice = np.concatenate(parts)
voice = hp(voice, 70)
voice_st = np.zeros((N, 2)); voice_st[: len(voice)] = voice[:, None]


# ------------------------------------------------------------------ music: "Creeping Unease"
MUSIC = IN.replace("/in", "/in2") + "/music.mp3"
OFFSET = 160.0 - TOTAL          # the track's natural ending lands on the closing animation
mraw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{OFFSET:.3f}", "-i", MUSIC, "-ac", "2", "-ar", str(SR),
                       "-f", "f32le", "-"], capture_output=True).stdout
m = np.frombuffer(mraw, np.float32).astype(np.float64).reshape(-1, 2)
music = np.zeros((N, 2)); music[: min(N, len(m))] = m[:N]
q = ws(191)
ramp = np.interp(t_all, [0, 20, 58, q, we(200) + 0.3, ws(201) + 0.6, TOTAL],
                 [-4.0, -3.0, -1.5, 1.0, 1.0, -2.0, -1.0])
music *= (10 ** (ramp / 20))[:, None]
music[: int(0.25 * SR)] *= np.linspace(0, 1, int(0.25 * SR))[:, None]

# ------------------------------------------------------------------ cinematic SFX (no synth beeps)
def nz(n): return rng.standard_normal(n)

def mk_boom():
    """trailer impact: sub drop + low body + distant hall tail"""
    n = int(3.0 * SR); tt = np.arange(n) / SR
    f = 28 + 34 * np.exp(-tt * 4.5)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.6)
    body = lp(nz(n), 160, 4) * np.exp(-tt * 7) * 2.2
    air = bp(nz(n), 200, 1800, 2) * np.exp(-tt * 14) * 0.25
    att = np.minimum(1, tt / 0.004)
    return np.tanh((sub * 1.1 + body + air) * att * 1.1) * 0.9

def mk_hit():
    n = int(2.0 * SR); tt = np.arange(n) / SR
    f = 34 + 24 * np.exp(-tt * 6)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.5) * 0.6 + lp(nz(n), 140, 4) * np.exp(-tt * 10) * 1.2) * np.minimum(1, tt / 0.006)

def mk_swish():
    """smooth air pass-by centred on the cut (replaces the 8-bit glitch)"""
    n = int(0.7 * SR); x = nz(n); out = np.zeros(n); k = 28; seg = n // k
    for i in range(k):
        c = 300 + 2200 * np.sin(np.pi * i / k) ** 2
        out[i * seg:(i + 1) * seg] = bp(x[i * seg:(i + 1) * seg], c * 0.6, c * 1.6, 1)
    out = lp(out, 3000, 2)
    env = np.sin(np.linspace(0, np.pi, n)) ** 3
    return out * env * 0.55

def mk_riser():
    """reverse swell into a reveal"""
    n = int(1.2 * SR); tt = np.arange(n) / SR
    x = lp(nz(n), 2500, 2) * np.exp(-tt[::-1] * 0) * (tt / tt[-1]) ** 3
    return x * 0.5

def mk_stamp():
    n = int(0.9 * SR); tt = np.arange(n) / SR
    thud = lp(nz(n), 220, 4) * np.exp(-tt * 22) * 3.0
    low = np.sin(2 * np.pi * np.cumsum(70 + 40 * np.exp(-tt * 30)) / SR) * np.exp(-tt * 12) * 0.8
    slap = bp(nz(n), 600, 3000, 2) * np.exp(-tt * 70) * 0.35
    return np.tanh((thud + low + slap) * 1.2) * 0.85

def mk_gavel():
    n = int(1.2 * SR); tt = np.arange(n) / SR
    knock = bp(nz(n), 350, 1400, 2) * np.exp(-tt * 45) * 1.6
    body = np.sin(2 * np.pi * 190 * tt) * np.exp(-tt * 28) * 0.7 + lp(nz(n), 200, 4) * np.exp(-tt * 20) * 1.5
    return np.tanh((knock + body) * 1.3) * 0.9

def mk_tick(hi=True):
    """mechanical clock tick: filtered transient, no tone"""
    n = int(0.06 * SR); tt = np.arange(n) / SR
    lo, hi_f = (2500, 7000) if hi else (1800, 5000)
    return bp(nz(n), lo, hi_f, 2) * np.exp(-tt * 260) * 0.8 + lp(nz(n), 600) * np.exp(-tt * 150) * 0.4

bank = {"boom": mk_boom(), "hit": mk_hit(), "stamp": mk_stamp(), "gavel": mk_gavel()}
fx = np.zeros(N)
tick_hi = True
for t0, kind, g in SFX:
    if kind in ("type", "static"):
        continue
    if kind == "glitch":
        s = mk_swish(); t0 -= 0.35; g *= 0.6
    elif kind == "whoosh":
        s = mk_riser(); t0 -= 1.2
    elif kind == "tick":
        s = mk_tick(tick_hi); tick_hi = not tick_hi
    else:
        s = bank[kind]
    i = max(0, int(t0 * SR)); L = min(len(s), N - i)
    fx[i:i + L] += s[:L] * g
fx_st = reverb(fx, 3.2, 1.9, 0.32, 5)

# ------------------------------------------------------------------ silence windows (music + sfx)
gate = np.ones(N)
for a, b in SILENCES:
    gate[(t_all >= a) & (t_all < b)] = 0
gate = np.convolve(gate, np.ones(400) / 400, "same")  # ~9 ms fades
gate = gate[:, None]

def rms(x):
    return np.sqrt(np.mean(x[np.abs(x) > 1e-4] ** 2))

v_rms = rms(voice)
music *= (v_rms * 10 ** (-11 / 20)) / rms(music[: int(MAIN_LEN * SR)])   # music ~11 dB under the voice
fx_st *= (v_rms * 10 ** (-8 / 20)) / np.sqrt(np.mean(fx_st[np.abs(fx_st) > 1e-3] ** 2))

mix = voice_st + (music + fx_st) * gate
mix = mix[: int(TOTAL * SR)]
mix /= np.max(np.abs(mix)) / 0.89
for name, arr in (("mix", mix), ("music_only", music[: int(TOTAL * SR)] * gate[: int(TOTAL * SR)])):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    f"{W_DIR}/{name}.wav"], input=arr.astype(np.float32).tobytes(), check=True)
print("audio ok", mix.shape[0] / SR)
