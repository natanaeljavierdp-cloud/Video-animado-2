"""Música de fondo cinematográfica de suspenso (sintetizada, libre de derechos)
+ efectos de sonido sincronizados con las escenas.

Genera: build/musica.wav (estéreo 44.1 kHz)
"""
import numpy as np
import wave
import os

SR = 44100
DUR = 70.4
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)

HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, "build"), exist_ok=True)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def env_window(a, b, fade=1.5):
    """1 entre a y b con fundidos suaves."""
    return smoothstep((t - a + fade) / fade) * smoothstep((b - t + fade) / fade)


def lowpass_fft(x, cutoff, hp=0.0):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = 1 / (1 + (f / cutoff) ** 4)
    if hp > 0:
        g *= 1 / (1 + (hp / np.maximum(f, 1e-3)) ** 4)
    return np.fft.irfft(X * g, len(x))


# ---------------------------------------------------------------- cuerdas
# Progresión (tiempo de inicio, fin, notas MIDI)
CHORDS = [
    (0.0, 5.6, [38, 50, 53, 57]),      # Dm
    (5.4, 14.3, [38, 50, 53, 57, 62]),  # Dm (mapa)
    (14.1, 21.2, [34, 46, 50, 53]),    # Bb
    (21.0, 32.2, [31, 43, 50, 55, 58]),  # Gm
    (32.0, 37.2, [33, 45, 52, 57, 61]),  # A (tensión)
    (37.0, 54.5, [38, 39, 50, 51, 57]),  # clúster oscuro D/Eb
    (54.3, 61.5, [34, 46, 53, 58]),    # Bb
    (61.3, 66.8, [33, 45, 52, 57]),    # A
    (66.6, 70.4, [38, 50, 57, 62]),    # D (resolución con el logo)
]


def string_voice(freq, start, end):
    seg = env_window(start, end, 1.6)
    out = np.zeros(N)
    vib = 1 + 0.0025 * np.sin(2 * np.pi * (4.6 + rng.random()) * t + rng.random() * 6)
    for det in (-0.0018, 0.0, 0.0021):
        ph = 2 * np.pi * np.cumsum(freq * (1 + det) * vib) / SR
        for k in range(1, 14):
            if freq * k > 2400:
                break
            amp = (1 / k) * (1 / (1 + (freq * k / 700) ** 2))
            out += amp * np.sin(k * ph + rng.random() * 6.28)
    # respiración lenta del arco
    swell = 0.75 + 0.25 * np.sin(2 * np.pi * t / (6.0 + rng.random() * 3) + rng.random() * 6)
    return out * seg * swell


strings = np.zeros(N)
for a, b, notes in CHORDS:
    for n in notes:
        w = 1.0 if n < 45 else 0.55
        strings += w * string_voice(midi(n), a, b)
strings = lowpass_fft(strings, 1400, hp=35)
strings /= np.max(np.abs(strings)) + 1e-9

# ---------------------------------------------------------------- pulsos graves
def thump(at, f0=52, dec=0.35, amp=1.0):
    out = np.zeros(N)
    i0 = int(at * SR)
    L = int(SR * 1.2)
    if i0 >= N:
        return out
    L = min(L, N - i0)
    tt = np.arange(L) / SR
    f = f0 * (1 + 1.4 * np.exp(-tt / 0.03))
    ph = 2 * np.pi * np.cumsum(f) / SR
    out[i0:i0 + L] = amp * np.sin(ph) * np.exp(-tt / dec)
    return out


pulses = np.zeros(N)
# heartbeat lento: activa desde el mapa, se intensifica, se detiene en el giro oscuro
bpm_sections = [(5.6, 21.0, 0.86, 0.55), (21.0, 32.0, 0.70, 0.75), (32.0, 36.8, 0.70, 0.8),
                (40.6, 54.0, 1.15, 0.6), (54.4, 61.2, 0.86, 0.45), (61.4, 66.4, 0.62, 0.7)]
for a, b, step, amp in bpm_sections:
    x = a
    while x < b:
        pulses += thump(x, 50, 0.28, amp)
        pulses += thump(x + 0.22, 46, 0.22, amp * 0.45)  # "lub-dub"
        x += step

# ---------------------------------------------------------------- impactos y efectos
def boom(at, amp=1.0, length=3.5):
    out = thump(at, 38, 0.9, amp)
    i0 = int(at * SR)
    L = min(int(SR * length), N - i0)
    if L <= 0:
        return out
    tt = np.arange(L) / SR
    nz = rng.standard_normal(L)
    nz = lowpass_fft(nz, 180)
    out[i0:i0 + L] += amp * 0.9 * nz / (np.max(np.abs(nz)) + 1e-9) * np.exp(-tt / 0.9)
    return out


def riser(end, length=1.4, amp=0.5, hi=False):
    out = np.zeros(N)
    i1 = int(end * SR)
    i0 = max(0, i1 - int(length * SR))
    L = i1 - i0
    tt = np.linspace(0, 1, L)
    nz = rng.standard_normal(L)
    nz = lowpass_fft(nz, 5000 if hi else 2500, hp=300)
    nz /= np.max(np.abs(nz)) + 1e-9
    out[i0:i1] = amp * nz * tt ** 2.5
    return out


def whoosh(at, amp=0.45, length=0.6):
    out = np.zeros(N)
    i0 = int(at * SR)
    L = min(int(length * SR), N - i0)
    tt = np.linspace(0, 1, L)
    nz = rng.standard_normal(L)
    nz = lowpass_fft(nz, 3000, hp=400)
    nz /= np.max(np.abs(nz)) + 1e-9
    out[i0:i0 + L] = amp * nz * np.sin(np.pi * tt) ** 2
    return out


def shimmer(at, amp=0.25):
    """Destello de luz: brillo agudo corto."""
    out = np.zeros(N)
    i0 = int(at * SR)
    L = min(int(0.9 * SR), N - i0)
    tt = np.arange(L) / SR
    s = np.zeros(L)
    for f in (2093, 2637, 3136, 4186):
        s += np.sin(2 * np.pi * f * tt + rng.random() * 6)
    nz = lowpass_fft(rng.standard_normal(L), 9000, hp=4000)
    s = s / 4 + 0.6 * nz / (np.max(np.abs(nz)) + 1e-9)
    out[i0:i0 + L] = amp * s * np.exp(-tt / 0.25) * smoothstep(tt / 0.02)
    return out


def crumble(a, b, amp=0.35):
    """Desintegración: granos de ruido."""
    out = np.zeros(N)
    for _ in range(int((b - a) * 70)):
        at = a + rng.random() * (b - a)
        i0 = int(at * SR)
        L = int(SR * (0.01 + rng.random() * 0.04))
        tt = np.arange(L) / SR
        out[i0:i0 + L] += amp * rng.random() * rng.standard_normal(L) * np.exp(-tt / 0.01)
    return lowpass_fft(out, 6000, hp=600)


def tick(at, amp=0.25):
    out = np.zeros(N)
    i0 = int(at * SR)
    L = int(SR * 0.03)
    tt = np.arange(L) / SR
    out[i0:i0 + L] = amp * np.sin(2 * np.pi * 1800 * tt) * np.exp(-tt / 0.004)
    return out


def stamp(at, amp=0.9):
    out = thump(at, 70, 0.12, amp)
    i0 = int(at * SR)
    L = int(SR * 0.15)
    tt = np.arange(L) / SR
    out[i0:i0 + L] += amp * 0.7 * lowpass_fft(rng.standard_normal(L), 1500) * np.exp(-tt / 0.03)
    return out


sfx = np.zeros(N)
sfx += boom(0.0, 0.9)
sfx += crumble(0.8, 2.8, 0.5)
sfx += riser(5.35, 1.3, 0.35)
sfx += boom(5.45, 0.8)
sfx += shimmer(5.5, 0.18)
sfx += stamp(6.8, 0.5)                     # rótulo 2016
sfx += boom(8.15, 0.55)                    # SINIZACIÓN
sfx += whoosh(12.5, 0.3)
sfx += riser(14.15, 1.2, 0.35, hi=True)
sfx += shimmer(14.15, 0.2)
for k in range(40):                        # contador
    sfx += tick(14.3 + k * 0.08, 0.16)
for at in (18.32, 19.2, 20.0):             # alteradas / cerradas / demolidas
    sfx += stamp(at, 0.55)
sfx += riser(21.0, 1.0, 0.3)
sfx += boom(21.05, 0.6)
for at in (23.34, 24.9, 26.54, 27.46):     # tachados
    sfx += whoosh(at - 0.05, 0.35, 0.35)
    sfx += stamp(at + 0.1, 0.4)
sfx += shimmer(29.7, 0.2)                  # pagoda
sfx += riser(32.0, 1.2, 0.3, hi=True)
sfx += shimmer(32.0, 0.2)
sfx += whoosh(33.3, 0.35, 1.2)             # deslizador antes/después
sfx += riser(37.0, 1.6, 0.45)
sfx += boom(37.05, 1.0, 5.0)               # "pero hay algo más"
sfx += stamp(40.64, 0.9)                   # sello CONFIDENCIAL
for at in (45.96, 47.6, 51.88):            # resaltados
    sfx += whoosh(at, 0.25, 0.3)
sfx += boom(53.3, 0.9)                     # COMO EL SARS
sfx += whoosh(54.3, 0.3, 0.7)
sfx += riser(61.4, 1.0, 0.3)
sfx += boom(61.45, 0.7)
sfx += boom(64.0, 0.4)
sfx += riser(66.6, 1.2, 0.4, hi=True)
sfx += shimmer(66.6, 0.3)
sfx += boom(66.65, 0.7, 3.5)

# ---------------------------------------------------------------- mezcla
music = 0.55 * strings + 0.5 * pulses
# la música sube un poco al final (cierre de marca) y baja en la parte del documento
music *= 1 + 0.4 * env_window(66.6, 70.4, 0.4)
music *= smoothstep(t / 0.4) * smoothstep((DUR - t) / 1.2)
bed = music + 0.6 * sfx

L = bed.copy()
R = bed.copy()
# ensanchar las cuerdas en estéreo con un retardo leve
d = int(0.011 * SR)
R[d:] = 0.55 * strings[:-d] * 0.55 + 0.5 * pulses[d:] + 0.6 * sfx[d:]
R[d:] = R[d:] * (1 + 0.4 * env_window(66.6, 70.4, 0.4)[d:]) * (smoothstep(t / 0.4) * smoothstep((DUR - t) / 1.2))[d:]
st = np.stack([L, R], 1)
st /= np.max(np.abs(st)) + 1e-9
st *= 0.89

out = os.path.join(HERE, "build", "musica.wav")
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((st * 32767).astype("<i2").tobytes())
print("ok", out)
