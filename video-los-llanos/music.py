"""Genera la música de suspenso (drone + latido + risers/golpes) y la mezcla con la
narración con ducking automático. Salida: build/mezcla.wav (48 kHz estéreo)."""
import numpy as np
from scipy import signal
import subprocess, json

SR = 48000
TOTAL = json.load(open("timeline.json"))["total"]
HITS = json.load(open("timeline.json"))["hits"]          # golpes graves
SILENCE = json.load(open("timeline.json"))["music_dip"]  # [ini, fin] música casi muda
N = int(TOTAL * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)

# --- Narración (sin editar) ---
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", "assets/narracion.mp3", "-ac", "2", "-ar", str(SR),
                      "-f", "f32le", "-"], capture_output=True, check=True).stdout
narr = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)
voice = np.zeros((N, 2), np.float32)
voice[:min(N, len(narr))] = narr[:N]


def lp(x, fc, order=4):
    sos = signal.butter(order, fc, "low", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def hp(x, fc, order=2):
    sos = signal.butter(order, fc, "high", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


# --- Drone: 55 Hz + 82.5 Hz (quinta), sierras suaves, filtro paso bajo con LFO ---
def saw(f, ph=0.0):
    return 2 * ((f * t + ph) % 1.0) - 1


lfo = 0.5 + 0.5 * np.sin(2 * np.pi * t / 11.0)
drone = (0.55 * saw(55) + 0.45 * saw(55.15, .3) + 0.40 * saw(82.5, .1) + 0.30 * saw(82.2, .6)
         + 0.25 * np.sin(2 * np.pi * 27.5 * t))
# filtro variable: mezcla de dos paso-bajo según el LFO
drone = (1 - lfo) * lp(drone, 160) + lfo * lp(drone, 380)
drone *= 0.85 + 0.15 * np.sin(2 * np.pi * t / 7.3)
# capa alta tenue (aire) — ruido filtrado
air = lp(hp(rng.standard_normal(N), 900), 2500) * 0.035 * (0.6 + 0.4 * np.sin(2 * np.pi * t / 13))
drone_l = drone + air
drone_r = np.roll(drone, 240) + np.roll(air, 900)

# --- Latido cada 1.2 s (lub-dub) ---
beat = np.zeros(N)
def thump(at, amp, f0=58, dur=0.28):
    i0 = int(at * SR)
    n = int(dur * SR)
    if i0 >= N:
        return
    n = min(n, N - i0)
    tt = np.arange(n) / SR
    f = f0 * (1 + 0.6 * np.exp(-tt * 30))
    ph = 2 * np.pi * np.cumsum(f) / SR
    beat[i0:i0 + n] += amp * np.sin(ph) * np.exp(-tt * 14) * (1 - np.exp(-tt * 400))

x = 0.6
while x < TOTAL - 2.5:
    thump(x, 0.9)
    thump(x + 0.22, 0.55)
    x += 1.2

# --- Risers (1.6 s antes) y golpes graves en momentos clave ---
fx = np.zeros(N)
for h in HITS:
    # riser: ruido filtrado con volumen y brillo crecientes
    d = 1.6
    i0, i1 = int((h - d) * SR), int(h * SR)
    n = i1 - i0
    tt = np.linspace(0, 1, n)
    nz = rng.standard_normal(n)
    r = 0.5 * hp(lp(nz, 1800), 300) * tt ** 2.2
    r += 0.15 * np.sin(2 * np.pi * np.cumsum(80 + 220 * tt ** 2) / SR) * tt ** 2
    fx[i0:i1] += r
    # golpe: caída de 70 Hz a 32 Hz + transitorio
    n = int(2.6 * SR)
    n = min(n, N - i1)
    tt = np.arange(n) / SR
    f = 32 + 40 * np.exp(-tt * 6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    boom = 1.6 * np.sin(ph) * np.exp(-tt * 1.6)
    boom += 0.6 * lp(rng.standard_normal(n), 900) * np.exp(-tt * 18)
    fx[i1:i1 + n] += boom

music_l = 0.33 * drone_l + 0.55 * beat + 0.65 * fx
music_r = 0.33 * drone_r + 0.55 * beat + 0.65 * fx
music = np.stack([music_l, music_r], 1)
music /= np.sqrt((music ** 2).mean()) + 1e-9  # RMS = 1

# --- Niveles: voz como referencia; música -20 dB al hablar, -14 dB en pausas ---
v_mono = np.abs(voice).mean(1)
win = int(0.05 * SR)
env = np.sqrt(np.convolve(v_mono ** 2, np.ones(win) / win, "same"))
speech_rms = np.sqrt((v_mono[env > 0.02] ** 2).mean())
talking = (env > 0.015).astype(float)
# suavizado tipo compresor: ataque 60 ms, liberación 450 ms
g = np.zeros(N)
a_att, a_rel = np.exp(-1 / (0.06 * SR)), np.exp(-1 / (0.45 * SR))
# vectorizado por bloques de 10 ms para velocidad
blk = SR // 100
tb = talking[: N // blk * blk].reshape(-1, blk).max(1)
gb = np.zeros_like(tb)
acc = 0.0
ab, rb = np.exp(-1 / 6), np.exp(-1 / 45)
for i, v in enumerate(tb):
    acc = (ab * acc + (1 - ab) * v) if v > acc else (rb * acc + (1 - rb) * v)
    gb[i] = acc
duck = np.interp(np.arange(N), np.arange(len(gb)) * blk, gb)
level_db = -14 + (-6) * duck  # -14 dB pausas, -20 dB con voz
# bajón casi a silencio ("NOS ACOSTUMBRAMOS")
a, b = SILENCE
dip = np.clip(np.minimum((t - (a - 0.25)) / 0.25, ((b + 0.4) - t) / 0.4), 0, 1)
level_db += -24 * dip
gain = speech_rms * 10 ** (level_db / 20)
# fades: 2 s entrada, 3 s salida
gain *= np.clip(t / 2.0, 0, 1) * np.clip((TOTAL - t) / 3.0, 0, 1)
mix = voice + music * gain[:, None]
peak = np.abs(mix).max()
if peak > 0.98:
    mix *= 0.98 / peak
import wave
pcm = (mix * 32767).astype("<i2")
with wave.open("build/mezcla.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
# música sola, por si se quiere editar en CapCut
mus = music * gain[:, None] / max(peak, 1)
with wave.open("build/musica_sola.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(mus, -1, 1) * 32767).astype("<i2").tobytes())
print("ok", TOTAL, "s, pico", peak)
