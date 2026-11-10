"""Música de suspenso + efectos sintetizados y mezcla con la narración.

Todo se genera con numpy (sin samples de terceros):
  - Cama: dron grave, cuerdas oscuras (sierras desafinadas filtradas), pulso tipo latido, tic-tac.
  - Efectos: "boom"/hit en cada dato fuerte, whoosh en transiciones, ticks en contadores.
  - La música va a ~20 % bajo la voz, con ducking automático cuando habla Jaider.
"""
import subprocess
import sys
import numpy as np

from timeline import HITS, WHOOSHES, TICK_RANGES, TOTAL, NARR_END, CIERRE_START

SR = 44100
rng = np.random.default_rng(7)


def n(t):
    return int(t * SR)


def lp(x, fc):
    """Paso bajo (respuesta tipo Butterworth de 2º orden aplicada por FFT)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    H = 1 / np.sqrt(1 + (f / fc) ** 4)  # 2º orden aprox (Butterworth magnitud)
    return np.fft.irfft(X * H, len(x))


def hp(x, fc):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    H = (f / fc) ** 2 / np.sqrt(1 + (f / fc) ** 4)
    return np.fft.irfft(X * H, len(x))


def saw(freq, t):
    ph = (freq * t) % 1.0
    return 2 * ph - 1


def reverb(x, decay=1.8, mix=0.35):
    L = n(decay)
    tt = np.arange(L) / SR
    ir = rng.standard_normal(L) * np.exp(-tt * 6.9 / decay)
    ir = lp(ir, 3500)
    ir /= np.sqrt((ir ** 2).sum())
    wet = np.fft.irfft(np.fft.rfft(x, len(x) + L) * np.fft.rfft(ir, len(x) + L))[: len(x)]
    return x * (1 - mix) + wet * mix * 2.2


def bed(total):
    N = n(total)
    t = np.arange(N) / SR
    out = np.zeros(N)

    # Progresión oscura (Am - F - Dm - E), 8 s por acorde
    chords = [
        [110.0, 130.81, 164.81],   # Am
        [87.31, 130.81, 174.61],   # F
        [73.42, 146.83, 174.61],   # Dm
        [82.41, 123.47, 207.65],   # E (con sensible)
    ]
    seg = 8.0
    strings = np.zeros(N)
    for k in range(int(np.ceil(total / seg)) + 1):
        ch = chords[k % 4]
        a, b = n(k * seg - 1.0), n((k + 1) * seg + 1.0)
        a, b = max(a, 0), min(b, N)
        if a >= b:
            continue
        tt = t[a:b]
        env = np.clip((tt - (k * seg - 1.0)) / 1.5, 0, 1) * np.clip(((k + 1) * seg + 1.0 - tt) / 1.5, 0, 1)
        s = np.zeros(b - a)
        for f0 in ch:
            for det in (-0.12, 0.0, 0.13):
                s += saw(f0 * (1 + det / 100 * 3), tt + rng.random())
        strings[a:b] += s * env
    strings = lp(strings, 700) * 0.06
    # trémolo lento tipo arco
    strings *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.23 * t)

    # Dron grave
    drone = (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82.41 * t + 1.0)
             + 0.3 * np.sin(2 * np.pi * 27.5 * t)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.07 * t))
    drone *= 0.16

    # Ruido oscuro (aire)
    air = lp(rng.standard_normal(N), 400) * 0.05

    # Pulso tipo latido (80 bpm) — dos golpes
    beat = np.zeros(N)
    period = 0.75
    kick_len = n(0.35)
    kt = np.arange(kick_len) / SR
    kick = np.sin(2 * np.pi * (45 + 60 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 11)
    tb = 0.0
    while tb < total:
        for off, g in ((0.0, 1.0), (0.22, 0.6)):
            i = n(tb + off)
            if i + kick_len < N:
                beat[i:i + kick_len] += kick * g
        tb += period
    beat *= 0.33

    # Tic-tac agudo suave (corcheas)
    tick = np.zeros(N)
    tl = n(0.03)
    tt = np.arange(tl) / SR
    clk = hp(rng.standard_normal(tl), 3000)[:tl] * np.exp(-tt * 180)
    tb = 0.0
    while tb < total:
        i = n(tb)
        if i + tl < N:
            tick[i:i + tl] += clk * (0.05 if int(tb / 0.375) % 2 else 0.08)
        tb += 0.375

    out = strings + drone + air + beat + tick
    # Intro: entra con el contador; el pulso arranca suave
    out *= np.clip(t / 0.4, 0, 1)
    return out


def boom(strength=1.0):
    L = n(2.5)
    t = np.arange(L) / SR
    sub = np.sin(2 * np.pi * (38 + 90 * np.exp(-t * 9)) * t) * np.exp(-t * 2.2)
    crack = lp(rng.standard_normal(L), 2500) * np.exp(-t * 28)
    body = lp(rng.standard_normal(L), 180) * np.exp(-t * 3.0) * 1.5
    x = sub * 1.0 + crack * 0.5 + body * 0.4
    x = reverb(x, 2.2, 0.3)
    x /= np.abs(x).max()
    return x * strength


def whoosh(dur=0.6):
    L = n(dur)
    t = np.arange(L) / SR
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    noise = rng.standard_normal(L)
    # barrido: mezcla de paso bajo y alto que se desplaza
    lo = lp(noise, 900)
    hi = hp(noise, 2500)
    mixc = t / dur
    x = (lo * (1 - mixc) + hi * mixc * 0.6) * env
    x /= np.abs(x).max()
    return x


def counter_tick():
    L = n(0.02)
    t = np.arange(L) / SR
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 300)


def place(buf, clip, at, gain):
    i = n(at)
    j = min(len(buf), i + len(clip))
    if i < len(buf):
        buf[i:j] += clip[: j - i] * gain


def load_voice(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def main(voice_path, out_wav):
    N = n(TOTAL)
    voice = np.zeros(N)
    v = load_voice(voice_path)
    voice[: len(v)] = v[:N]

    music = bed(TOTAL)
    music /= np.abs(music).max()

    # Ducking: envolvente de la voz
    env = np.abs(voice)
    win = n(0.25)
    env = np.convolve(env, np.ones(win) / win, mode="same")
    env = np.clip(env / (np.percentile(env[env > 0], 90) + 1e-9), 0, 1)
    duck = 1.0 - 0.55 * env  # baja aún más cuando hay voz
    t = np.arange(N) / SR
    # cama a ~20 % bajo la voz; sube en el cierre
    level = np.where(t < NARR_END, 0.20, 0.20 + 0.25 * np.clip((t - NARR_END) / 0.8, 0, 1))
    # la cama se apaga justo antes del golpe final
    level *= np.clip((TOTAL - 0.35 - t) / 0.4, 0, 1) + (t < TOTAL - 1.2)
    level = np.clip(level, 0, 0.45)
    music = music * level * duck

    sfx = np.zeros(N)
    b = boom()
    for at, s in HITS:
        place(sfx, b, at - 0.02, 0.55 * s)
    for at in WHOOSHES:
        w = whoosh(0.55)
        place(sfx, w, at - 0.35, 0.16)
    ct = counter_tick()
    for a, z, rate in TICK_RANGES:
        tt = a
        while tt < z:
            place(sfx, ct, tt, 0.10)
            tt += 1.0 / rate
    # golpe final del cierre
    place(sfx, boom(), CIERRE_START + 2.9, 0.75)

    voice_peak = np.abs(voice).max() + 1e-9
    voice = voice / voice_peak * 0.89
    mix = voice + music + sfx
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)  # limitador suave
    stereo = np.stack([mix, mix], axis=1).astype(np.float32)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    out_wav], input=stereo.tobytes(), check=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
