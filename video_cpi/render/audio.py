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

# ------------------------------------------------------------------ intensity curve
q = ws(191)  # "¿quién controla el mundo?"
key = [(0, 0.30), (4.3, 0.38), (18.0, 0.45), (23.0, 0.42), (38.5, 0.62), (43.5, 0.62),
       (58.5, 0.72), (74.7, 1.0), (q, 1.0), (we(200) + 0.2, 1.0), (ws(201) + 0.4, 0.42), (MAIN_LEN, 0.5), (TOTAL, 0.2)]
I = np.interp(t_all, [k[0] for k in key], [k[1] for k in key])


def saw(freq, n_harm=18, phase0=0.0):
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(freq, (N,))) / SR + phase0
    out = np.zeros(N)
    for k in range(1, n_harm + 1):
        out += np.sin(k * ph) / k
    return out


# drone: D1 + D2 detuned saws, low-passed
drone = sum(saw(f * d, 12, rng.uniform(0, 6)) for f in (36.71, 73.42) for d in (0.997, 1.0, 1.003))
drone = lp(drone, 260, 2) * 0.35
drone_hi = lp(sum(saw(f * d, 14, rng.uniform(0, 6)) for f in (146.83, 220.0) for d in (0.996, 1.004)), 900) * 0.12
drone_mix = drone * (0.6 + 0.4 * I) + drone_hi * np.clip((I - 0.4) * 1.6, 0, 1)

# heartbeat pulse, accelerating with intensity
hb = np.zeros(N)
def kick(f0=110, f1=42, dur=0.35, amp=1.0):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt * 28)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9) * amp
    return np.tanh(s * 1.6)
k_lub, k_dub = kick(), kick(95, 40, 0.3, 0.65)
tb = 0.15
while tb < MAIN_LEN:
    bpm = 56 + 44 * np.interp(tb, t_all[::100], I[::100]) ** 1.3
    i = int(tb * SR)
    for kk, off in ((k_lub, 0), (k_dub, int(0.19 * SR))):
        j = i + off; hb[j: j + len(kk)] += kk[: max(0, min(len(kk), N - j))]
    tb += 60 / bpm
hb = lp(hb, 180) * 0.9 * (0.55 + 0.45 * I)

# tense strings: tremolo clusters entering in layers, plus rising glissando at the end
def string_layer(freqs, start, fade=4.0, trem=9.0, cutoff=2400):
    out = np.zeros(N)
    for f in freqs:
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t_all + rng.uniform(0, 6))
        out += saw(f * vib, 16, rng.uniform(0, 6))
    out = lp(out, cutoff, 2)
    tremolo = 0.55 + 0.45 * np.abs(np.sin(np.pi * trem * t_all))
    env = np.clip((t_all - start) / fade, 0, 1)
    return out * tremolo * env

s1 = string_layer([146.83, 220.0], 4.3) * 0.10                      # D3 A3
s2 = string_layer([293.66, 311.13, 349.23], 23.0, 6) * 0.07          # D4 Eb4 F4 cluster
s3 = string_layer([587.33, 622.25], 43.5, 8, 11, 3500) * 0.045      # D5 Eb5 high tension
# rising glissando from 58.5 to the question (semitone every ~2.5 s)
g_start, g_end = 58.5, ws(191)
semis = np.clip((t_all - g_start) / (g_end - g_start), 0, 1) * 7
gl = np.zeros(N)
for base in (293.66, 440.0, 587.33):
    gl += saw(base * 2 ** (semis / 12), 14, rng.uniform(0, 6))
gl = lp(gl, 3000) * (0.55 + 0.45 * np.abs(np.sin(np.pi * 12 * t_all)))
gl *= np.clip((t_all - g_start) / 6, 0, 1) * (t_all < g_end + 3.2) * 0.05
strings = (s1 + s2 + s3) * (0.4 + 0.6 * I) + gl
strings_st = reverb(strings, 2.8, 2.6, 0.45, 3)

# climax hold after the question, then a soft dark pad under the CTA
music = np.stack([drone_mix, drone_mix], 1) * 0.9 + np.stack([hb, hb], 1) + strings_st
cta = ws(201)
fade_cta = np.clip(1 - (t_all - (cta - 0.3)) / 1.2, 0.45, 1)[:, None]
music *= fade_cta
music[t_all >= MAIN_LEN + 0.05] *= np.exp(-(t_all[t_all >= MAIN_LEN + 0.05] - MAIN_LEN) * 1.4)[:, None]

# ------------------------------------------------------------------ SFX
def env_exp(n, d):
    return np.exp(-np.arange(n) / SR * d)

def mk_boom():
    n = int(2.2 * SR); tt = np.arange(n) / SR
    f = 32 + 70 * np.exp(-tt * 6)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.2)
    noise = lp(rng.standard_normal(n), 400) * np.exp(-tt * 9) * 0.8
    crack = hp(rng.standard_normal(n), 2000) * np.exp(-tt * 60) * 0.25
    return np.tanh((sub * 1.3 + noise + crack) * 1.4)

def mk_hit():
    n = int(1.2 * SR); tt = np.arange(n) / SR
    f = 50 + 60 * np.exp(-tt * 15)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 5) * 0.7 + lp(rng.standard_normal(n), 900) * np.exp(-tt * 25) * 0.3

def mk_glitch():
    n = int(0.28 * SR); out = np.zeros(n); i = 0
    while i < n:
        L = int(rng.uniform(0.008, 0.04) * SR)
        kind = rng.integers(3)
        tt = np.arange(L) / SR
        if kind == 0: seg = np.sign(np.sin(2 * np.pi * rng.uniform(200, 3000) * tt))
        elif kind == 1: seg = rng.standard_normal(L)
        else: seg = np.round(rng.standard_normal(L) * 3) / 3
        out[i:i + L] = seg[: max(0, min(L, n - i))] * rng.uniform(0.3, 1); i += L
    out = hp(out, 300) * np.linspace(1, 0.3, n)
    return out * 0.45

def mk_static(d=0.9):
    n = int(d * SR); x = bp(rng.standard_normal(n), 800, 9000)
    crackle = (rng.random(n) > 0.997) * rng.standard_normal(n) * 3
    env = np.minimum(1, np.arange(n) / (0.02 * SR)) * np.linspace(1, 0, n) ** 0.7
    return (x * 0.35 + crackle * 0.3) * env

def mk_stamp():
    n = int(0.6 * SR); tt = np.arange(n) / SR
    thud = np.sin(2 * np.pi * np.cumsum(140 * np.exp(-tt * 10) + 55) / SR) * np.exp(-tt * 18)
    click = hp(rng.standard_normal(n), 1500) * np.exp(-tt * 120) * 0.8
    slap = bp(rng.standard_normal(n), 300, 2500) * np.exp(-tt * 40) * 0.6
    return np.tanh((thud + click + slap) * 1.5) * 0.9

def mk_gavel():
    n = int(1.0 * SR); tt = np.arange(n) / SR; out = np.zeros(n)
    for f, d, a in ((620, 38, 0.7), (1130, 50, 0.5), (1870, 70, 0.35), (2900, 90, 0.2), (180, 25, 0.6)):
        out += np.sin(2 * np.pi * f * tt) * np.exp(-tt * d) * a
    out += hp(rng.standard_normal(n), 2500) * np.exp(-tt * 150) * 0.6
    return np.tanh(out * 1.4)

def mk_tick(hi=True):
    n = int(0.09 * SR); tt = np.arange(n) / SR
    f = 3200 if hi else 2500
    return (np.sin(2 * np.pi * f * tt) * 0.6 + bp(rng.standard_normal(n), 1500, 7000) * 0.5) * np.exp(-tt * 140)

def mk_type():
    n = int(0.05 * SR); tt = np.arange(n) / SR
    return bp(rng.standard_normal(n), 1200, 6000) * np.exp(-tt * 200) * 0.7 + np.sin(2 * np.pi * 180 * tt) * np.exp(-tt * 120) * 0.3

def mk_whoosh():
    n = int(0.9 * SR); x = rng.standard_normal(n); out = np.zeros(n); seg = n // 20
    for k in range(20):
        lo = 200 + 4000 * (k / 20) ** 2
        out[k * seg:(k + 1) * seg] = bp(x[k * seg:(k + 1) * seg], lo, lo * 2.5)
    return out * np.sin(np.linspace(0, np.pi, n)) ** 2 * 0.5

bank = {"boom": mk_boom(), "hit": mk_hit(), "stamp": mk_stamp(), "gavel": mk_gavel(),
        "type": None, "tick": None, "glitch": None, "static": None, "whoosh": mk_whoosh()}
fx = np.zeros(N)
tick_hi = True
for t0, kind, g in SFX:
    if kind == "glitch": s = mk_glitch()
    elif kind == "static": s = mk_static()
    elif kind == "type": s = mk_type()
    elif kind == "tick": s = mk_tick(tick_hi); tick_hi = not tick_hi
    else: s = bank[kind]
    if kind == "whoosh": t0 = t0 - 0.6
    i = max(0, int(t0 * SR)); L = min(len(s), N - i)
    fx[i:i + L] += s[:L] * g
fx_st = reverb(fx, 2.0, 3.2, 0.28, 5)

# ------------------------------------------------------------------ silence windows (music + sfx)
gate = np.ones(N)
for a, b in SILENCES:
    gate[(t_all >= a) & (t_all < b)] = 0
gate = np.convolve(gate, np.ones(400) / 400, "same")  # ~9 ms fades
gate = gate[:, None]

def rms(x):
    return np.sqrt(np.mean(x[np.abs(x) > 1e-4] ** 2))

v_rms = rms(voice)
music *= (v_rms * 10 ** (-10 / 20)) / rms(music[: int(MAIN_LEN * SR)])   # music ~10 dB under the voice
fx_st *= (v_rms * 10 ** (-4 / 20)) / np.sqrt(np.mean(fx_st[np.abs(fx_st) > 1e-3] ** 2))

mix = voice_st + (music + fx_st) * gate
mix = mix[: int(TOTAL * SR)]
mix /= np.max(np.abs(mix)) / 0.89
for name, arr in (("mix", mix), ("music_only", music[: int(TOTAL * SR)] * gate[: int(TOTAL * SR)])):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    f"{W_DIR}/{name}.wav"], input=arr.astype(np.float32).tobytes(), check=True)
print("audio ok", mix.shape[0] / SR)
