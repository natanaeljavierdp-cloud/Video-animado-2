"""Construye la banda sonora completa:
  - VOZ: audio original de cada clip (mismos recortes que el video), paso-altos 70 Hz,
    reducción de ruido muy suave y ganancia para igualar sonoridad entre clips. Sin otra alteración.
  - MÚSICA: composición original sintetizada aquí mismo (sin muestras de terceros):
    pad cinematográfico, bajo pulsante, reloj de noticiero, percusión grave, arpegio y firma final.
  - SFX: impacto inicial, whooshes de transición, destellos y blips digitales, firma sonora.
  - Ducking automático de música/SFX con la envolvente de la voz y pausas dramáticas.
Salida: build/voz.wav, build/musica.wav, build/sfx.wav, build/mezcla.wav (48 kHz estéreo, float32).
"""
import subprocess, json, re, sys, os
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(__file__))
from comun import cargar_edl, tl, BUILD

SR = 48000
edl = cargar_edl()
FPS = edl["fps"]
N = int(round(edl["dur_total"] * SR))
rng = np.random.default_rng(20261121)


def lufs_de(path_or_args):
    out = subprocess.run(["ffmpeg", "-nostats", *path_or_args, "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])


def write_wav(path, x):
    x = np.asarray(x, np.float32)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "pcm_f32le", path], input=x.astype("<f4").tobytes(), check=True)


def wav_lufs(x):
    p = os.path.join(BUILD, "_tmp_lufs.wav"); write_wav(p, x)
    return lufs_de(["-i", p])


# ---------------------------------------------------------------- VOZ
voz = np.zeros((N, 2))
info_voz = []
for c in edl["clips"]:
    ss, dur = c["in"] / FPS, c["frames"] / FPS
    base = ["-ss", f"{ss:.4f}", "-t", f"{dur:.4f}", "-i", c["ruta"]]
    filtro = "highpass=f=70,afftdn=nr=6:nf=-50"
    out = subprocess.run(["ffmpeg", "-v", "error", *base, "-af", filtro, "-ac", "2", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(out, "<f4").reshape(-1, 2).astype(float)
    i_lufs = wav_lufs(a)
    g = 10 ** ((edl["audio"]["voz_objetivo_lufs_por_clip"] - i_lufs) / 20)
    a = a * g
    nf = int(0.008 * SR)
    a[:nf] *= np.linspace(0, 1, nf)[:, None]; a[-nf:] *= np.linspace(1, 0, nf)[:, None]
    s = int(round(c["t0"] * SR)); n = min(len(a), N - s)
    voz[s:s + n] += a[:n]
    info_voz.append({"clip": c["id"], "lufs_original": round(i_lufs, 1), "ganancia_db": round(20 * np.log10(g), 2)})
print("voz:", info_voz)
json.dump(info_voz, open(os.path.join(BUILD, "voz_ganancias.json"), "w"), indent=1)

# envolvente de voz para ducking
mono = np.abs(voz).mean(1)
w = int(0.03 * SR)
env = np.sqrt(np.convolve(mono ** 2, np.ones(w) / w, "same"))
env_db = 20 * np.log10(env + 1e-9)
active = np.clip((env_db + 45) / 15, 0, 1)            # 0 = silencio, 1 = voz plena
# ataque rápido, liberación lenta
duck = np.zeros_like(active); k_a = 1 - np.exp(-1 / (0.015 * SR)); k_r = 1 - np.exp(-1 / (0.30 * SR))
v = 0.0
for i in range(0, len(active), 48):                   # resolución 1 ms
    tgt = active[i]
    v += (tgt - v) * (1 - (1 - (k_a if tgt > v else k_r)) ** 48)
    duck[i:i + 48] = v

# ---------------------------------------------------------------- utilidades de síntesis
t_all = np.arange(N) / SR
BPM = 100.0; BEAT = 60 / BPM; BAR = 4 * BEAT


def sos_lp(fc, order=2): return signal.butter(order, fc, "low", fs=SR, output="sos")
def sos_hp(fc, order=2): return signal.butter(order, fc, "high", fs=SR, output="sos")
def sos_bp(lo, hi, order=2): return signal.butter(order, [lo, hi], "band", fs=SR, output="sos")


def add(buf, x, t0, pan=0.0, gain=1.0):
    s = int(round(t0 * SR))
    if s >= N: return
    if s < 0: x = x[-s:]; s = 0
    n = min(len(x), N - s)
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    if x.ndim == 1:
        buf[s:s + n, 0] += x[:n] * l * gain * 1.414; buf[s:s + n, 1] += x[:n] * r * gain * 1.414
    else:
        buf[s:s + n] += x[:n] * gain


def saw(freq, dur, harm=10, det=0.0):
    t = np.arange(int(dur * SR)) / SR
    y = np.zeros_like(t)
    for k in range(1, harm + 1):
        if freq * k > 9000: break
        y += np.sin(2 * np.pi * freq * (1 + det) * k * t + k) / k
    return y


def reverb_ir(dur=2.4, decay=0.7):
    n = int(dur * SR); t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-t / decay * 3)[:, None]
    ir = signal.sosfilt(sos_lp(6000), ir, axis=0)
    ir[:int(0.012 * SR)] = 0
    return ir / np.sqrt((ir ** 2).sum(0))


IR = reverb_ir()


def reverb(x, wet=0.3):
    if x.ndim == 1: x = np.stack([x, x], 1)
    y = np.stack([signal.fftconvolve(x[:, i], IR[:, i])[:len(x)] for i in range(2)], 1)
    return x * (1 - wet) + y * wet


def midi(m): return 440 * 2 ** ((m - 69) / 12)


# ---------------------------------------------------------------- MÚSICA
mus = np.zeros((N, 2))
T_CL = {c["id"]: c["t0"] for c in edl["clips"]}
T_END = edl["frames_clips"] / FPS
# progresión (re menor): Dm | Bb | Gm | A
prog = [(50, [62, 65, 69]), (46, [62, 65, 70]), (43, [62, 67, 70]), (45, [61, 64, 69])]
n_bars = int(np.ceil(T_END / BAR))


def seccion(t):
    if t < T_CL["02"]: return "intriga"
    if t < T_CL["04"]: return "presentacion"
    if t < T_CL["06"]: return "humor"
    if t < T_CL["07"]: return "credibilidad"
    if t < T_CL["08"]: return "subida"
    return "cierre"


# pad
for b in range(n_bars):
    t0 = b * BAR; root, chord = prog[b % 4]
    dur = BAR + 0.6
    x = np.zeros(int(dur * SR))
    for m in chord + [root + 12]:
        for d in (-0.004, 0.0, 0.004):
            x += saw(midi(m), dur, harm=7, det=d)
    tt = np.arange(len(x)) / SR
    envp = np.minimum(1, tt / 0.5) * np.minimum(1, (dur - tt) / 0.6)
    sec = seccion(t0)
    lvl = {"intriga": 0.55, "presentacion": 0.6, "humor": 0.5, "credibilidad": 0.75, "subida": 0.7, "cierre": 0.8}[sec]
    x = signal.sosfilt(sos_lp(1400 if sec != "credibilidad" else 900), x) * envp * lvl * 0.05
    add(mus, x, t0, pan=0)

# bajo pulsante en corcheas
for b in range(n_bars):
    root = prog[b % 4][0] - 12
    for e in range(8):
        t0 = b * BAR + e * BEAT / 2
        if t0 >= T_END: break
        sec = seccion(t0)
        dur = BEAT / 2
        x = saw(midi(root + (12 if e % 4 == 3 and sec in ("humor", "subida", "cierre") else 0)), dur, harm=12)
        tt = np.arange(len(x)) / SR
        x = signal.sosfilt(sos_lp(700 + 500 * (e == 0)), x) * np.exp(-tt * 9) * np.minimum(1, tt / 0.004)
        add(mus, x * 0.10 * (1.15 if e % 2 == 0 else 0.8), t0)

# reloj de noticiero (semicorcheas)
click = signal.sosfilt(sos_bp(5000, 10000), rng.standard_normal(int(0.012 * SR))) * np.exp(-np.arange(int(0.012 * SR)) / SR * 400)
for i in range(int(T_END / (BEAT / 4))):
    t0 = i * BEAT / 4
    sec = seccion(t0)
    acc = 1.0 if i % 4 == 0 else 0.45
    add(mus, click * 0.07 * acc * (0.7 if sec == "presentacion" else 1.0), t0, pan=0.35 if i % 2 else -0.35)

# percusión grave (taiko)
def taiko(g=1.0):
    n = int(0.9 * SR); tt = np.arange(n) / SR
    f = 52 + 70 * np.exp(-tt * 30)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 5.5)
    nz = signal.sosfilt(sos_lp(900), rng.standard_normal(n)) * np.exp(-tt * 28) * 0.5
    return (x + nz) * g

for b in range(n_bars):
    t0 = b * BAR
    sec = seccion(t0)
    if sec in ("presentacion", "subida", "cierre"):
        add(mus, taiko(0.30), t0); add(mus, taiko(0.20), t0 + 2.5 * BEAT)
        if sec != "presentacion": add(mus, taiko(0.16), t0 + 3.5 * BEAT)
    elif sec == "humor":
        add(mus, taiko(0.22), t0)
    elif sec == "intriga" and b % 2 == 1:
        add(mus, taiko(0.18), t0)

# arpegio (bloques de humor y subida)
for b in range(n_bars):
    root, chord = prog[b % 4]
    for s16 in range(16):
        t0 = b * BAR + s16 * BEAT / 4
        sec = seccion(t0)
        if sec not in ("humor", "subida", "cierre") or t0 >= T_END: continue
        if sec == "humor" and s16 % 2: continue
        m = (chord + [chord[0] + 12])[s16 % 4] + 12
        n = int(0.18 * SR); tt = np.arange(n) / SR
        x = (np.sin(2 * np.pi * midi(m) * tt) + 0.3 * np.sin(4 * np.pi * midi(m) * tt)) * np.exp(-tt * 22)
        add(mus, x * 0.035, t0, pan=-0.5 if s16 % 2 else 0.5)

# cuerdas graves sostenidas en credibilidad
t_c0, t_c1 = T_CL["06"], T_CL["07"]
x = sum(saw(midi(38), t_c1 - t_c0 + 0.5, harm=9, det=d) for d in (-0.003, 0.003))
tt = np.arange(len(x)) / SR
x = signal.sosfilt(sos_lp(500), x) * np.minimum(1, tt / 1.0) * np.minimum(1, (len(x) / SR - tt) / 0.5) * 0.06
add(mus, x, t_c0)

mus = reverb(mus, 0.22)
# la música rítmica termina justo al entrar el end card (fundido de 80 ms)
s_end = int(T_END * SR); r = int(0.08 * SR)
mus[s_end:] = 0; mus[s_end - r:s_end] *= np.linspace(1, 0, r)[:, None]

# firma final de marca (re mayor) sobre el end card
t_s = T_END
n = int((edl["dur_total"] - t_s + 0.01) * SR); tt = np.arange(n) / SR
sting = np.zeros(n)
for m in (38, 50, 57, 62, 66, 69, 74):
    sting += saw(midi(m), n / SR, harm=8, det=0.002) * (0.9 if m < 60 else 0.6)
sting = signal.sosfilt(sos_lp(2200), sting) * np.exp(-tt * 1.1) * np.minimum(1, tt / 0.02) * 0.05
bell = sum(np.sin(2 * np.pi * midi(m) * tt) for m in (86, 90, 93)) * np.exp(-tt * 2.2) * 0.03
mus_end = reverb(sting + bell, 0.35)
fade_tail = np.minimum(1, (n / SR - tt) / 0.5)[:, None]
add(mus, mus_end * fade_tail, t_s)

# pausas dramáticas (la música calla antes del remate)
pause = np.ones(N)
for cid, a, b in edl["audio"]["pausas_dramaticas"]:
    s, e = int(tl(edl, cid, a) * SR), int(tl(edl, cid, b) * SR)
    r = int(0.06 * SR)
    pause[s:e] = 0.08
    pause[s - r:s] = np.linspace(1, 0.08, r); pause[e:e + r] = np.minimum(pause[e:e + r], np.linspace(0.08, 1, r))

# ---------------------------------------------------------------- SFX
sfx = np.zeros((N, 2))


def impacto(g=1.0, dur=1.6):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = 34 + 40 * np.exp(-tt * 9)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.6)
    crack = signal.sosfilt(sos_lp(2800), rng.standard_normal(n)) * np.exp(-tt * 16) * 0.6
    return reverb((sub + crack) * g, 0.3)


def whoosh(dur=0.38, g=1.0, sube=True):
    n = int(dur * SR); tt = np.arange(n) / SR
    nz = rng.standard_normal(n)
    out = np.zeros(n); seg = 256
    for i in range(0, n, seg):
        p = i / n
        fc = 300 * (14 ** (p if sube else 1 - p))
        sos = sos_bp(fc * 0.6, min(fc * 1.8, 20000))
        out[i:i + seg] = signal.sosfilt(sos, nz[max(0, i - 2048):i + seg])[-len(nz[i:i + seg]):]
    envw = np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 1.5
    x = out * envw * g
    pan = np.linspace(-0.8, 0.8, n)
    return np.stack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)], 1) * 1.4


def blip(f1=1300, f2=1900, g=1.0):
    n = int(0.07 * SR); tt = np.arange(n) / SR
    a = np.sin(2 * np.pi * f1 * tt) * np.exp(-tt * 60)
    b = np.sin(2 * np.pi * f2 * tt) * np.exp(-tt * 60)
    x = np.concatenate([a, b * 0.8])
    return x * g


def brillo(g=1.0, dur=0.6):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * tt + i) for i, f in enumerate((3520, 4186, 5274, 6272)))
    x *= (0.6 + 0.4 * np.sin(2 * np.pi * 24 * tt)) * np.exp(-tt * 5) * np.minimum(1, tt / 0.03)
    return reverb(x * g, 0.4)


log_sfx = []
def poner(nombre, x, t0, pan=0.0, g=1.0):
    add(sfx, x, t0, pan, g); log_sfx.append((round(t0, 2), nombre))

poner("impacto de apertura", impacto(0.55), 0.0)
poner("whoosh apertura", whoosh(0.45, 0.5, sube=False), 0.0)
poner("brillo logotipo", brillo(0.10), 1.05)
poner("blip mapa", blip(g=0.06), 0.4)
for c in edl["clips"][1:]:
    poner(f"whoosh transición -> {c['id']}", whoosh(0.36, 0.42), c["t0"] - 0.18)
    poner("impacto suave de corte", impacto(0.12, 0.8), c["t0"])
poner("whoosh -> end card", whoosh(0.45, 0.5), T_END - 0.2)
poner("impacto firma final", impacto(0.6), T_END)
poner("brillo firma final", brillo(0.16, 1.2), T_END + 0.25)
G = edl["graficos"]
poner("blip rótulo", blip(g=0.07), tl(edl, "02", G["rotulo_presentadora"]["desde"]))
poner("brillo rótulo", brillo(0.06), tl(edl, "02", G["rotulo_presentadora"]["desde"]) + 0.45)
for h in G["titulares"]:
    poner(f"blip titular {h['texto']}", blip(1100, 1650, g=0.06), tl(edl, h["clip"], h["desde"]))
for m in G["mapa_superior"]:
    poner("blip mapa", blip(1500, 2100, g=0.05), tl(edl, m["clip"], m["desde"]))
for tt_, lab in G["verificacion"]["checks"]:
    poner(f"check {lab}", blip(1800, 2400, g=0.05), tl(edl, "06", tt_))
poner("batería vacía", blip(900, 500, g=0.07), tl(edl, "04", G["bateria_paciencia"]["drena"][1]))
poner("carga atascada", blip(700, 600, g=0.06), tl(edl, "05", G["carga_promesa"]["atasco"]))

# ---------------------------------------------------------------- MEZCLA
mus *= pause[:, None]
music_gain_duck = 1 - 0.72 * duck            # ~ -11 dB bajo la voz
sfx_gain_duck = 1 - 0.45 * duck
# normalización de stems: música alrededor de -23.5 LUFS antes del ducking
g_m = 10 ** ((-23.5 - wav_lufs(mus)) / 20); mus *= g_m
sfx *= 0.7
mix = voz + mus * music_gain_duck[:, None] + sfx * sfx_gain_duck[:, None]
pk = np.abs(mix).max()
print("pico mezcla:", pk, "  ganancia música:", 20 * np.log10(g_m))
write_wav(os.path.join(BUILD, "voz.wav"), voz)
write_wav(os.path.join(BUILD, "musica.wav"), mus * music_gain_duck[:, None])
write_wav(os.path.join(BUILD, "sfx.wav"), sfx * sfx_gain_duck[:, None])
write_wav(os.path.join(BUILD, "mezcla.wav"), mix / max(1.0, pk / 0.95))
json.dump(log_sfx, open(os.path.join(BUILD, "sfx_log.json"), "w"), ensure_ascii=False, indent=0)
os.remove(os.path.join(BUILD, "_tmp_lufs.wav"))
print("ok", N / SR, "s")
