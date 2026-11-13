"""Episodio 1 - arma la linea de tiempo, las envolventes de voz (para animar)
y la mezcla final de audio (voces + ambiente sintetizado).

Uso: python3 audio_ep1.py <carpeta_salida>
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(HERE, "audio")
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
SR = 48000
FPS = 30


def load(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def norm_voice(x, target_db=-17.0):
    # normaliza por RMS de las partes con voz
    a = np.abs(x)
    win = int(0.05 * SR)
    env = np.sqrt(np.convolve(x * x, np.ones(win) / win, mode="same"))
    act = env > env.max() * 0.15
    rms = np.sqrt(np.mean(x[act] ** 2)) if act.any() else 1e-3
    g = 10 ** (target_db / 20) / max(rms, 1e-5)
    y = x * g
    peak = np.abs(y).max()
    if peak > 0.97:
        y *= 0.97 / peak
    return y


def envelope(x):
    hop = SR // FPS
    n = int(np.ceil(len(x) / hop))
    e = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) if len(x[i * hop:(i + 1) * hop]) else 0 for i in range(n)])
    if e.max() > 0:
        e = e / np.percentile(e, 95)
    return np.clip(e, 0, 1.2).round(3).tolist()


# --- clips elegidos (toma a) -------------------------------------------------
C = {}
for name in ["00_narrador", "01_mik_a", "02_sic_a", "03_mar_a", "04_nj_a", "05_dp_a", "06_bol_a",
             "07_dob_a", "08_mikv_a", "09_bolv_a", "10_mard_a", "11_dpd_a", "12_nj_a", "13_sic_a",
             "14_mar_a", "15_dob_a", "L_mar_a", "L_mik_a", "L_nj_a", "L_bol_a",
             "L_mar_b", "L_mik_b", "L_nj_b", "L_bol_b"]:
    C[name] = norm_voice(load(os.path.join(AUD, name + ".mp3")))


def dur(n):
    return len(C[n]) / SR


# --- linea de tiempo ---------------------------------------------------------
cues = []  # (start, clip, speaker, text, gain, subtitle?)


def add(start, clip, who, text, gain=1.0, sub=True, maxlen=None, fade=0.0):
    d = dur(clip) if maxlen is None else min(maxlen, dur(clip))
    cues.append(dict(start=round(start, 3), end=round(start + d, 3), clip=clip, who=who,
                     text=text, gain=gain, sub=sub, fade=fade))
    return start + d


t = add(2.0, "00_narrador", "NARRADOR", "Esta es la historia de cómo empezaron Los Morenos Chocolate.", gain=1.35)
CARDS_START = 8.6
CARD_LEN = 1.15
t = CARDS_START + 7 * CARD_LEN + 0.25
t = add(t, "01_mik_a", "MIKIBIRY", "¡Fuiste tú que le diste a la Babe!") - 0.5
t = add(t, "02_sic_a", "EL SICARIO", "¿Yo? ¡Fuiste tú, no te haga'!") - 0.5
t = add(t, "03_mar_a", "MARINO EL EPC", "¡A mí no me metan en esa vaina!") - 0.5
t = add(t, "04_nj_a", "EL NJ", "¡Fuiste tú, fuiste tú!") + 0.4
DP_START = t
t = add(t, "05_dp_a", "DOBLE P", "¡Hagan silencio! Que aquí to' sabemo' quién fue el único que le dio... Sabemo' que fue El Bolen.") + 0.8
t = add(t, "06_bol_a", "EL BOLEN", "¡¿Yo?! ¡Yo no fui na'! ¡Dejen su vaina conmigo!") + 0.6
t = add(t, "07_dob_a", "EL DOBLÓN", "Nosotro' lo que deberíamo' e' ponerno' a cantar, en ve' de tá discutiendo por disparate.") + 0.3
add(t, "08_mikv_a", "TODOS", "Sí, e' verdá.")
t = add(t + 0.15, "09_bolv_a", "TODOS", "Sí, e' verdá.", sub=False) - 0.2
add(t, "10_mard_a", "TODOS", "¡Vamo' a darle!")
t = add(t + 0.12, "11_dpd_a", "TODOS", "¡Vamo' a darle!", sub=False) + 0.6
t = add(t, "12_nj_a", "EL NJ", "Pero tienen que dejar su lío por mujere', que aquí to' somo' pana y no' la' podemo' repartir entre to'.") + 0.5
t = add(t, "13_sic_a", "EL SICARIO", "Tú tiene' razón... pero no me toquen a Checa, que esa e' mía y de má' nadie.") + 0.25
LAUGH1 = t
for i, c in enumerate(["L_mar_a", "L_mik_a", "L_nj_a", "L_bol_a"]):
    add(LAUGH1 + i * 0.12, c, "RISAS", "", gain=0.75, sub=False, maxlen=3.4, fade=1.0)
t = add(LAUGH1 + 2.6, "14_mar_a", "MARINO EL EPC", "¡Tú tá pasao! Eso e' del barrio, muchacho. Eso e' patrimonio del ayuntamiento.")
LAUGH2 = t - 0.6
for i, c in enumerate(["L_mar_b", "L_mik_b", "L_nj_b", "L_bol_b"]):
    add(LAUGH2 + i * 0.15, c, "RISAS", "", gain=0.95, sub=False, maxlen=5.2, fade=1.6)
t = add(LAUGH2 + 4.0, "15_dob_a", "EL DOBLÓN", "Ya, dejen su' chiste' y vamo' a ponerno' a escribir, que la gente necesita má' contenido.")
DOB2_END = t
TOTAL = round(t + 9.4, 2)

# momento en que Doble P dice "Sabemo' que fue El Bolen" (ultima pausa del clip)
dpx = C["05_dp_a"]
hop = SR // 100
e = np.array([np.sqrt(np.mean(dpx[i:i + hop] ** 2)) for i in range(0, len(dpx) - hop, hop)])
quiet = e < e.max() * 0.06
best = None
i = 0
while i < len(quiet):
    if quiet[i]:
        j = i
        while j < len(quiet) and quiet[j]:
            j += 1
        if (j - i) >= 18 and j < len(quiet) - 30:
            best = j
        i = j
    else:
        i += 1
BOLEN_REVEAL = round(DP_START + (best / 100 if best else dur("05_dp_a") - 2.0), 2)

# --- mezcla de voces ---------------------------------------------------------
N = int(TOTAL * SR)
mix = np.zeros(N, dtype=np.float32)
for c in cues:
    x = C[c["clip"]][: int((c["end"] - c["start"]) * SR)].copy()
    if c["fade"] > 0:
        f = int(c["fade"] * SR)
        x[-f:] *= np.linspace(1, 0, f)
    s = int(c["start"] * SR)
    mix[s:s + len(x)] += x[: N - s] * c["gain"]
    c["env"] = envelope(x * c["gain"])

# --- ambiente sintetizado (sin derechos) -------------------------------------
rng = np.random.default_rng(7)
tt = np.arange(N) / SR


def onepole(x, fc):
    # implementacion rapida via FFT (respuesta de un polo)
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    H = 1 / np.sqrt(1 + (f / fc) ** 2)
    return np.fft.irfft(X * H, n).astype(np.float32)


def bandpass(x, lo, hi):
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    H = np.exp(-0.5 * ((np.log(np.maximum(f, 1)) - np.log(np.sqrt(lo * hi))) / (np.log(hi / lo) / 2)) ** 2)
    return np.fft.irfft(X * H, n).astype(np.float32)


# brisa: ruido filtrado con oleadas lentas
breeze = onepole(rng.standard_normal(N).astype(np.float32), 500)
gust = 0.55 + 0.45 * np.sin(2 * np.pi * 0.07 * tt + 1) * np.sin(2 * np.pi * 0.023 * tt + 0.3)
leaves = bandpass(rng.standard_normal(N).astype(np.float32), 2500, 7000) * (0.4 + 0.6 * gust ** 2)
breeze = breeze / np.abs(breeze).max() * gust * 0.05 + leaves / np.abs(leaves).max() * 0.012

# gente a lo lejos: ruido de banda de voz con modulacion silabica
crowd = np.zeros(N, dtype=np.float32)
for k in range(6):
    v = bandpass(rng.standard_normal(N).astype(np.float32), 250 + 60 * k, 1400 + 100 * k)
    syl = np.clip(np.sin(2 * np.pi * (3.2 + 0.7 * k) * tt + rng.uniform(0, 6)) + rng.uniform(-0.3, 0.2), 0, 1)
    phrase = np.clip(np.sin(2 * np.pi * (0.11 + 0.03 * k) * tt + rng.uniform(0, 6)) * 1.5, 0, 1)
    crowd += v / np.abs(v).max() * syl * phrase
crowd = crowd / np.abs(crowd).max() * 0.018


def motor(t0, length, direction=1, vol=0.05, stop=False):
    """moto pasando (o llegando y apagandose si stop=True)."""
    n = int(length * SR)
    s = int(t0 * SR)
    if s >= N:
        return
    n = min(n, N - s)
    u = np.arange(n) / SR
    p = u / length
    if stop:
        rpm = 52 - 26 * np.clip(p * 1.3, 0, 1)
        amp = np.clip(p * 4, 0, 1) * np.where(p < 0.82, 1, np.clip((1 - p) / 0.18, 0, 1))
    else:
        rpm = 48 + 8 * np.tanh((p - 0.5) * 6) * -direction  # efecto doppler
        amp = np.exp(-((p - 0.5) / 0.22) ** 2)
    ph = 2 * np.pi * np.cumsum(rpm) / SR
    w = np.zeros(n, dtype=np.float32)
    for h in range(1, 14):
        w += np.sin(h * ph) / h ** 0.9
    w *= 0.6 + 0.4 * np.sign(np.sin(ph * 0.5))
    w += 0.35 * onepole(rng.standard_normal(n).astype(np.float32), 900) * 6
    w = onepole(w, 1500)
    w = w / np.abs(w).max() * amp * vol
    mix_amb[s:s + n] += w


mix_amb = (breeze + crowd).astype(np.float32)
for (t0, ln, d, v) in [(3.0, 5.0, 1, 0.035), (19.0, 4.5, -1, 0.02), (40.0, 5.5, 1, 0.025),
                        (57.0, 4.0, -1, 0.018), (68.0, 5.0, 1, 0.02), (TOTAL - 9, 5.0, -1, 0.03)]:
    motor(t0, ln, d, v)
# Mikibiry llega en motor
motor(0.0, 6.0, 1, 0.08, stop=True)

# pajaritos
for k in range(14):
    t0 = rng.uniform(0, TOTAL - 1)
    s = int(t0 * SR)
    for c in range(rng.integers(2, 5)):
        n = int(0.09 * SR)
        u = np.arange(n) / SR
        f = 3200 + 1500 * np.sin(np.pi * u / 0.09) + rng.uniform(-300, 300)
        ch = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * u / 0.09) * 0.006
        ss = s + int(c * 0.13 * SR)
        if ss + n < N:
            mix_amb[ss:ss + n] += ch

# ambiente baja un poco cuando hay voces
duck = np.ones(N, dtype=np.float32)
for c in cues:
    a, b = int(c["start"] * SR), int(c["end"] * SR)
    duck[a:b] = 0.6
duck = onepole(duck, 2)
final = mix + mix_amb * duck
# fade in/out
fi = int(0.8 * SR)
final[:fi] *= np.linspace(0, 1, fi)
fo = int(2.0 * SR)
final[-fo:] *= np.linspace(1, 0, fo)
final = np.clip(final, -0.98, 0.98)

wav = os.path.join(OUT, "mezcla_ep1.wav")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                "-ac", "2", "-c:a", "pcm_s16le", wav], input=final.astype(np.float32).tobytes(), check=True)

info = dict(total=TOTAL, fps=FPS, cards_start=CARDS_START, card_len=CARD_LEN, dp_start=DP_START,
            bolen_reveal=BOLEN_REVEAL, laugh1=LAUGH1, laugh2=LAUGH2, dob2_end=DOB2_END, cues=cues)
with open(os.path.join(OUT, "timeline_ep1.json"), "w") as f:
    json.dump(info, f, ensure_ascii=False)
print("TOTAL", TOTAL, "BOLEN_REVEAL", BOLEN_REVEAL)
for c in cues:
    print(f'{c["start"]:6.2f} {c["end"]:6.2f} {c["who"]:14s} {c["text"][:50]}')
