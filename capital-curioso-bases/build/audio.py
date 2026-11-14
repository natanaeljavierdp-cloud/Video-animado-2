# Sintetiza música de suspenso + efectos de sonido y mezcla con narracion.mp3 -> build/mezcla.wav
import json, subprocess, wave
import numpy as np

SR = 44100
T = json.load(open('build/timeline.json'))
DUR = T['dur']
N = int(DUR * SR)
rng = np.random.default_rng(7)
t = np.arange(N) / SR


def fft_filter(x, lo=None, hi=None):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if hi: m *= 1 / (1 + (f / hi) ** 4)
    if lo: m *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)
    return np.fft.irfft(X * m, len(x))


def env(n, a, d):
    e = np.ones(n)
    na, nd = int(a * SR), int(d * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nd: e[-nd:] *= np.linspace(1, 0, nd)
    return e


def norm(x, peak=1.0):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def mtof(m): return 440 * 2 ** ((m - 69) / 12)


# ---------------- MÚSICA ----------------
music = np.zeros((N, 2))
# progresión Dm - Bb - Gm - A (4 s por acorde, 60 BPM)
chords = [[50, 53, 57], [46, 50, 53], [43, 46, 50], [45, 49, 52]]
bass_notes = [38, 34, 31, 33]
CH = 4.0
# drone grave continuo
dr = np.zeros(N)
for h in range(1, 9):
    dr += np.sin(2 * np.pi * mtof(26) * h * t + rng.random() * 6) / h
    dr += np.sin(2 * np.pi * mtof(26) * 1.003 * h * t + rng.random() * 6) / h
dr = fft_filter(dr, hi=180) * (0.6 + 0.4 * np.sin(2 * np.pi * t / 9))
music[:, 0] += norm(dr, .35); music[:, 1] += norm(dr, .35)
# pad
pad = np.zeros((N, 2))
for i in range(int(DUR / CH) + 1):
    c = chords[i % 4]; s0 = int(i * CH * SR); n = min(int((CH + 1) * SR), N - s0)
    if n <= 0: break
    tt = np.arange(n) / SR; e = env(n, 1.2, 1.4)
    for k, note in enumerate(c):
        for ch, det in enumerate([0.997, 1.003]):
            sig = sum(np.sin(2 * np.pi * mtof(note + 12) * det * h * tt) / h ** 1.5 for h in (1, 2, 3))
            pad[s0:s0 + n, ch] += sig * e
for ch in range(2): pad[:, ch] = fft_filter(pad[:, ch], hi=1400)
music += norm(pad, .22)
# bajo pulsante (latido) y ostinato en corcheas
beat = 60 / 96
pulse = np.zeros(N); ost = np.zeros(N); tick = np.zeros(N)
nb = int(DUR / beat)
for b in range(nb):
    s0 = int(b * beat * SR); ci = int(b * beat / CH) % 4
    # latido
    for off, amp in [(0, 1), (0.18, .6)]:
        p0 = s0 + int(off * SR); n = int(.35 * SR)
        if p0 + n < N:
            tt = np.arange(n) / SR
            f = mtof(bass_notes[ci]) * (1 + 0.6 * np.exp(-tt * 30))
            pulse[p0:p0 + n] += amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9)
    # ostinato (2 por pulso)
    for half in range(2):
        p0 = s0 + int(half * beat / 2 * SR); n = int(.3 * SR)
        if p0 + n < N:
            tt = np.arange(n) / SR
            note = chords[ci][(b * 2 + half) % 3] + 12
            ost[p0:p0 + n] += (np.sin(2 * np.pi * mtof(note) * tt) + .3 * np.sin(4 * np.pi * mtof(note) * tt)) * np.exp(-tt * 14)
    # tic de reloj
    p0 = s0; n = int(.03 * SR)
    if p0 + n < N: tick[p0:p0 + n] += rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 200)
tick = fft_filter(tick, lo=3000)
# intensidad: arranca suave, sube en el bloque de mapas y baja en el cierre
inten = np.interp(t, [0, 4, T['s3'], T['s4'], T['s8'], T['s10'], T['s11'], DUR - 1, DUR], [.55, .7, .8, 1, 1, .9, .75, .5, 0])
ostg = np.interp(t, [0, T['s2'], T['s4'], T['s10'], T['s11'], DUR], [0, .4, 1, 1, .3, 0])
for ch in range(2):
    music[:, ch] += norm(pulse, .45) + norm(ost, .12) * ostg * (1 if ch else .8) + norm(tick, .05) * ostg
music *= inten[:, None]
# corte en "PERO NO ES EL ÚNICO": silencio breve de la música
gap = np.interp(t, [T['s3'] - .3, T['s3'] - .05, T['s3'] + .6, T['s4']], [1, .15, .15, 1])
gap[t < T['s3'] - .3] = 1; gap[t > T['s4']] = 1
music *= gap[:, None]

# ---------------- EFECTOS ----------------
sfx = np.zeros((N, 2))


def add(x, at, gain=1.0, pan=0.0):
    s0 = int(at * SR)
    if s0 < 0: x = x[-s0:]; s0 = 0
    n = min(len(x), N - s0)
    if n <= 0: return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    sfx[s0:s0 + n, 0] += x[:n] * gain * l * 1.414
    sfx[s0:s0 + n, 1] += x[:n] * gain * r * 1.414


def whoosh(d=.6, lo=300, hi=6000):
    n = int(d * SR); tt = np.arange(n) / SR
    noise = rng.standard_normal(n)
    a = fft_filter(noise, lo=lo, hi=lo * 3); b = fft_filter(noise, lo=hi / 3, hi=hi)
    k = tt / d
    e = np.sin(np.pi * k) ** 2
    return norm((a * (1 - k) + b * k) * e, 1)


def boom():
    n = int(2.2 * SR); tt = np.arange(n) / SR
    f = 30 + 90 * np.exp(-tt * 6)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.8)
    nz = fft_filter(rng.standard_normal(n), hi=900) * np.exp(-tt * 7)
    hit = fft_filter(rng.standard_normal(n), lo=1500) * np.exp(-tt * 30)
    return norm(sub + .5 * norm(nz) + .25 * norm(hit), 1)


def riser(d=1.0):
    n = int(d * SR); tt = np.arange(n) / SR
    nz = fft_filter(rng.standard_normal(n), lo=800, hi=8000) * (tt / d) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * (tt / d) ** 2) / SR) * (tt / d) ** 2
    return norm(nz + .3 * tone, 1)


def pin():
    n = int(.7 * SR); tt = np.arange(n) / SR
    pop = np.sin(2 * np.pi * np.cumsum(900 - 600 * np.minimum(tt * 20, 1)) / SR) * np.exp(-tt * 40)
    bell = (np.sin(2 * np.pi * 1318 * tt) + .5 * np.sin(2 * np.pi * 1976 * tt) + .25 * np.sin(2 * np.pi * 2637 * tt)) * np.exp(-tt * 7)
    return norm(pop + .6 * bell, 1)


def click(f=2400):
    n = int(.06 * SR); tt = np.arange(n) / SR
    return norm(np.sin(2 * np.pi * f * tt) * np.exp(-tt * 90) + .3 * rng.standard_normal(n) * np.exp(-tt * 200), 1)


def stamp():
    n = int(.6 * SR); tt = np.arange(n) / SR
    th = fft_filter(rng.standard_normal(n), hi=500) * np.exp(-tt * 18)
    k = np.sin(2 * np.pi * np.cumsum(140 - 80 * np.minimum(tt * 10, 1)) / SR) * np.exp(-tt * 14)
    return norm(norm(th) + k, 1)


def chime():
    n = int(2.5 * SR); tt = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * mtof(m) * tt) * np.exp(-tt * (2 + i)) for i, m in enumerate([74, 81, 86, 90]))
    return norm(x, 1)


W1 = whoosh(); W2 = whoosh(.45, 600, 9000); WS = whoosh(.3, 1500, 10000)
# transiciones
for c in ['s2', 's4', 's8', 's9', 's10', 's11']:
    add(W1, T[c] - .32, .55)
add(riser(.9), T['s3'] - .9, .35)
add(boom(), T['s3'] + .06, .95)
# deslizamientos del mapa
for c in ['s5', 's6', 's7']:
    add(whoosh(1.1, 200, 4000), T[c] - .05, .45)
# pines del mapa
for k in ['mcnair', 'jbab', 'myer', 'unknown']:
    add(pin(), T[k] + .42, .55)
add(pin(), T['cemetery'] + .1, .3)
# escena 1
add(WS, 1.75, .35); add(stamp(), 1.95, .3); add(W2, 2.85, .35)
# escena 2
add(W2, T['b_name'], .25, -.3)
add(click(1200), T['b_house'] + .1, .35); add(WS, T['b_arrow'], .3, .3); add(click(1600), T['b_base'] + .1, .35)
add(W2, T['b_quote'], .3, .3)
add(stamp(), T['b_stamp'] + .2, .8)
# tarjetas de personas
for k, pan in [('rubio', -.3), ('hegseth', .3), ('noem', -.3), ('driscoll', -.3), ('miller', -.4), ('bondi', 0), ('blanche', .4)]:
    add(WS, T[k] - .05, .22, pan)
add(WS, T['cg_house'], .2, .3); add(WS, T['cemetery'], .2, .3)
# contador
cp = T['eight'] + .3 - T['count']
for i in range(8):
    tt = T['count'] + cp * (1 - (1 - (i + 1) / 8) ** (1 / 3)) - .02
    add(click(1800 + i * 120), tt, .4)
add(stamp(), T['eight'] + .3, .35)
# motivos
for k in ['m_iran', 'm_cart', 'm_viol']:
    add(W2, T[k] - .15, .35, .4); add(click(900), T[k] + .2, .3)
# mapa general: líneas
for i in range(3): add(WS, T['lines'] - .45 + i * .3, .25, (i - 1) * .5)
add(stamp(), T['generals'], .3)
# encuesta
add(W2, T['p_prot'] - .2, .3, -.3); add(W2, T['p_gob'] - .2, .3, .3); add(click(1000), T['p_gob'] - .3, .35)
add(click(1500), T['p_cta'] - .2, .3)
# cierre
add(chime(), T['s11'] + .55, .4)

# ---------------- MEZCLA ----------------
voz = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', 'narracion.mp3', '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                   capture_output=True).stdout, dtype=np.float32).astype(np.float64)
v = np.zeros(N); v[:min(N, len(voz))] = voz[:N]
v = norm(v, .89)
# ducking: la música baja cuando habla la voz
envv = np.convolve(np.abs(v), np.ones(int(.15 * SR)) / int(.15 * SR), 'same')
duck = 1 - .45 * np.clip(envv / (np.percentile(envv, 90) + 1e-9), 0, 1)
import os, sys
TRACK = sys.argv[1] if len(sys.argv) > 1 else None
OFFSET = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
MLEVEL = float(sys.argv[3]) if len(sys.argv) > 3 else 0.055
if TRACK and os.path.exists(TRACK):
    # pista descargada: se recorta a la duración, con fundidos, hueco en "PERO NO ES EL ÚNICO" y ducking
    tr = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(OFFSET), '-i', TRACK, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'],
                                      capture_output=True).stdout, dtype=np.float32).astype(np.float64).reshape(-1, 2)
    m = np.zeros((N, 2)); m[:min(N, len(tr))] = tr[:N]
    m /= np.sqrt((m ** 2).mean()) + 1e-9
    shape = np.interp(t, [0, 1.2, DUR - 2.8, DUR], [0, 1, 1, 0]) * gap
    music = m * MLEVEL * shape[:, None] * duck[:, None]
else:
    music = norm(music, 1) * 0.13 * duck[:, None]
sfx = sfx * 0.5
mix = music + sfx + v[:, None]
# limitador suave
mix = np.tanh(mix * 1.05) / np.tanh(1.05)
mix *= np.interp(t, [0, .05, DUR - .6, DUR], [0, 1, 1, 0])[:, None]
pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
with wave.open('build/mezcla.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok', DUR, 'pico', float(np.max(np.abs(mix))))
