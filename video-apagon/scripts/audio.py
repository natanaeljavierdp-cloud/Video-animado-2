# Música de suspenso + efectos de sonido sintetizados (sin samples externos) y mezcla con la voz.
# Uso: python3 scripts/audio.py voz.mp3 salida.wav
import sys, json
import numpy as np
from scipy import signal
from scipy.io import wavfile
import subprocess

SR = 44100
VOICE, OUT = sys.argv[1], sys.argv[2]
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', VOICE, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
voice = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()
N = len(voice); DUR = N / SR
t = np.arange(N) / SR
rng = np.random.default_rng(7)
W = json.load(open('data/words.json'))
ws = lambda i: W[i]['s']

def note(n):  # MIDI → Hz
    return 440 * 2 ** ((n - 69) / 12)

def env_adsr(n, a, r):
    e = np.ones(n); ka = int(a * SR); kr = int(r * SR)
    if ka: e[:ka] = np.linspace(0, 1, ka)
    if kr: e[-kr:] *= np.linspace(1, 0, kr)
    return e

def reverb(x, secs=2.2, mix=.35, seed=1):
    r = np.random.default_rng(seed)
    n = int(secs * SR); ir = r.standard_normal((n, 2)) * np.exp(-np.linspace(0, 7, n))[:, None]
    ir = signal.lfilter(*signal.butter(1, 6000 / (SR / 2)), ir, axis=0)
    wet = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], 1)
    wet /= (np.abs(wet).max() + 1e-9) / (np.abs(x).max() + 1e-9)
    return x * (1 - mix) + wet * mix

# ------------------------- MÚSICA -------------------------
mus = np.zeros((N, 2))
# progresión Dm – Bb – Gm – A (8 s por acorde)
chords = [[50, 53, 57], [46, 50, 53], [43, 46, 50], [45, 49, 52]]
CH = 8.0
for k in range(int(DUR // CH) + 2):
    st = k * CH; ch = chords[k % 4]
    if st > DUR: break
    a, b = int(st * SR), min(N, int((st + CH + 2.5) * SR))
    tt = np.arange(b - a) / SR
    e = np.minimum(1, tt / 2.5) * np.clip((CH + 2.5 - tt) / 2.5, 0, 1)
    for n in ch:
        f = note(n)
        for det, pan in ((-0.12, .3), (0.12, .7)):
            v = sum(np.sin(2 * np.pi * (f * h + det) * tt + h) / h ** 1.6 for h in range(1, 6))
            mus[a:b, 0] += v * e * (1 - pan) * .05
            mus[a:b, 1] += v * e * pan * .05
# filtro paso bajo con apertura lenta
sos = signal.butter(2, 900 / (SR / 2), output='sos')
mus = signal.sosfilt(sos, mus, axis=0)
# dron grave en Re
lfo = 1 + .25 * np.sin(2 * np.pi * .07 * t)
drone = (np.sin(2 * np.pi * 36.71 * t) * .5 + np.sin(2 * np.pi * 73.42 * t + .4 * np.sin(2 * np.pi * .3 * t)) * .35) * lfo * .16
mus += drone[:, None]
# latido grave (lub-dub) cada 1.25 s, hasta el cierre
def thump(f0=58, dur=.35, amp=1.):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f0 * (1 + 1.5 * np.exp(-tt * 40))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 13) * amp
beat = 0.6
while beat < 72.3:
    for off, amp in ((0, .28), (.24, .18)):
        x = thump(amp=amp); a = int((beat + off) * SR); b = min(N, a + len(x))
        mus[a:b] += x[:b - a, None]
    beat += 1.25
# campanitas lejanas
for st, n in ((4.0, 74), (12.9, 77), (20.5, 72), (28.6, 74), (36.0, 81), (43.3, 77), (50.9, 74), (58.6, 79), (66.0, 81)):
    nn = int(3.5 * SR); tt = np.arange(nn) / SR; a = int(st * SR); b = min(N, a + nn)
    x = (np.sin(2 * np.pi * note(n) * tt) + .3 * np.sin(2 * np.pi * note(n) * 2.01 * tt)) * np.exp(-tt * 1.3) * .035
    mus[a:b, 0] += x[:b - a] * .7; mus[a:b, 1] += x[:b - a]
# acorde final en Re mayor para el cierre
a = int(74.05 * SR); tt = np.arange(N - a) / SR
for n in (62, 66, 69, 74):
    mus[a:, :] += (np.sin(2 * np.pi * note(n) * tt) * np.exp(-tt * 1.2) * np.minimum(1, tt / .05) * .06)[:, None]
mus = reverb(mus, 3.0, .45, 3)
# fundidos
fade = np.ones(N); fade[:int(1.2 * SR)] = np.linspace(0, 1, int(1.2 * SR)); fade[-int(.35 * SR):] *= np.linspace(1, 0, int(.35 * SR))
mus *= fade[:, None]
mus /= np.abs(mus).max()

# ducking: la música baja mientras habla la voz
venv = np.abs(voice).mean(1)
venv = signal.sosfilt(signal.butter(1, 3 / (SR / 2), output='sos'), venv)
venv = venv / (venv.max() + 1e-9)
duck = 1 - .45 * np.clip(venv * 4, 0, 1)
mus *= duck[:, None]

# ------------------------- EFECTOS -------------------------
sfx = np.zeros((N, 2))
def put(x, st, gain=1., pan=.5):
    if x.ndim == 1: x = np.stack([x * (1 - pan) * 2 ** .5, x * pan * 2 ** .5], 1) * .75
    a = int(st * SR); b = min(N, a + len(x))
    if a >= N: return
    sfx[a:b] += x[:b - a] * gain

def whoosh(dur=.55, up=True):
    n = int(dur * SR); tt = np.linspace(0, 1, n)
    nz = rng.standard_normal(n)
    out = np.zeros(n); fc = (300 + 3500 * (tt if up else 1 - tt) ** 1.5)
    # filtro paso banda variable por bloques
    blk = 512
    for i in range(0, n, blk):
        f = fc[i]; sos = signal.butter(2, [max(60, f * .5) / (SR / 2), min(SR / 2 - 100, f * 1.6) / (SR / 2)], 'band', output='sos')
        out[i:i + blk] = signal.sosfilt(sos, nz[i:i + blk])
    e = np.sin(np.pi * tt) ** 2
    out = out * e
    l = out; r = np.roll(out, 120)
    pan = np.linspace(.2, .8, n)
    return np.stack([l * (1 - pan), r * pan], 1) / (np.abs(out).max() + 1e-9) * .5

def pop(f0=900, f1=420, dur=.09):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = np.linspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 45) * .5

def tick(dur=.03, hp=3000):
    n = int(dur * SR); x = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 250)
    return signal.sosfilt(signal.butter(2, hp / (SR / 2), 'high', output='sos'), x) * .35

def ding(f=1318.5):
    n = int(.6 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * tt) + .5 * np.sin(2 * np.pi * f * 1.5 * tt)) * np.exp(-tt * 8) * np.minimum(1, tt / .004) * .25

def power_down(dur=.55):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = 420 * np.exp(-tt * 5) + 40
    x = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 4)
    x = signal.sosfilt(signal.butter(2, 1500 / (SR / 2), output='sos'), x)
    cr = rng.standard_normal(n) * (rng.random(n) > .985) * .8
    return (x * .4 + cr * np.exp(-tt * 6) * .3)

def thud(dur=.6):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = 95 * np.exp(-tt * 6) + 42
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 7)
    nz = signal.sosfilt(signal.butter(2, 2500 / (SR / 2), output='sos'), rng.standard_normal(n)) * np.exp(-tt * 30)
    return body * .8 + nz * .5

def boom(dur=2.4):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = 60 * np.exp(-tt * 1.5) + 30
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.8)
    rum = signal.sosfilt(signal.butter(2, 180 / (SR / 2), output='sos'), rng.standard_normal(n)) * np.exp(-tt * 1.4) * 4
    return (body + rum) * .55

def zap(dur=.35):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = signal.square(2 * np.pi * 120 * tt) * (rng.random(n) > .5) * np.exp(-tt * 8)
    return signal.sosfilt(signal.butter(2, 3000 / (SR / 2), output='sos'), x) * .18

def tick_run(st, dur, steps):
    for i in range(steps):
        p = 1 - (1 - i / steps) ** 3  # siguen la curva ease-out del contador
        put(tick(), st + p * dur, .6, .5)

def scribble(dur=.6):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = signal.sosfilt(signal.butter(2, [1500 / (SR / 2), 6000 / (SR / 2)], 'band', output='sos'), rng.standard_normal(n))
    return x * (.5 + .5 * np.sin(2 * np.pi * 9 * tt) ** 2) * np.sin(np.pi * tt / dur) * .25

# --- Escena 1
put(whoosh(.5), ws(4) - .35, .5); put(pop(), ws(4) - .1, .9)
put(whoosh(.45), 3.0, .35); put(pop(700, 380), 3.3, .5)
put(whoosh(.5), ws(13) - .2, .4); tick_run(ws(14) - .45, 1.1, 18)
for i in range(3): put(pop(800 + i * 120, 500), 5.7 + i * .12, .55, .3 + i * .2)
for i, w in enumerate((17, 19, 22)): put(power_down(), ws(w), .55, .3 + i * .2)
put(whoosh(.45), ws(23) - .3, .35); put(pop(), ws(23), .6)
put(thud(), ws(30) - .05, .9)
# --- Escena 2
put(whoosh(.6), 12.7, .45); put(pop(), ws(34) - .1, .5)
tick_run(ws(37) - .05, .7, 12); tick_run(ws(39) - .05, .7, 12)
put(whoosh(.6), 17.7, .4); put(pop(), ws(42) - .1, .5)
put(scribble(), ws(49), .7); put(pop(1000, 600), ws(49) + .6, .5)
put(pop(650, 330), ws(52) - .05, .55)
put(thud(), ws(57) - .05, .9)
put(whoosh(.5), 24.4, .35)
put(pop(), 24.75, .5); put(pop(900, 500), ws(66) - .05, .55); put(pop(1000, 560), ws(66) + .75, .55)
# --- Escena 3
put(whoosh(.6), 28.35, .45); put(pop(), 28.65, .5)
put(whoosh(.5), ws(73) - .3, .4); put(ding(880), ws(74), .35)
put(pop(), ws(77) - .1, .5)
put(whoosh(.5), ws(82) - .35, .4)
for i in range(13): put(tick(.02, 4500), ws(85) - .4 + i * .1, .5, .35)
put(pop(), ws(85), .45); put(pop(700, 380), ws(91) - .05, .45)
put(pop(), ws(93) - .1, .5)
for i in range(8): put(tick(.02, 5000), ws(95) + i * .2, .45, .7)
put(whoosh(.5), ws(99) - .35, .4)
put(ding(), ws(102), .5, .35); put(ding(1568), ws(105), .5, .65)
put(pop(), ws(108) - .1, .5)
put(ding(), ws(112), .5, .35); put(ding(1568), ws(115), .5, .65)
# --- Escena 4
put(whoosh(.7), 43.05, .45); put(pop(600, 300), ws(116) - .15, .5)
put(pop(), 44.0, .45, .75)
put(thud(.4), ws(121), .6)
put(whoosh(.5), 46.65, .35); put(pop(900, 500), ws(124), .5, .3)
put(whoosh(.5), ws(135) - .35, .4); put(pop(), ws(135) - .1, .55)
put(boom(), 51.6, .6); put(power_down(.8), 51.6, .45)
put(pop(800, 450), ws(139) - .05, .45)
tick_run(ws(141) - .05, 1.4, 16)
put(zap(), 55.55, .8)
put(pop(), ws(148), .55); put(power_down(.6), ws(149) + .2, .5)
put(pop(700, 380), ws(153) - .1, .45)
# --- Escena 5
put(whoosh(.6), 58.35, .4)
put(pop(), ws(158), .4); put(pop(700, 380), ws(160), .4)
put(whoosh(.5), ws(166) - .5, .4); put(pop(600, 300), ws(166) - .25, .6)
put(whoosh(.45), 62.5, .3)
for i, w in enumerate((169, 170, 172, 173, 176, 177, 181)):
    put(pop(1000, 700, .05), ws(w) - .08, .35); put(ding(1318.5 * 2 ** (i / 12)), ws(w) + .06, .4, .65)
put(thud(.5), ws(182) - .1, .5); put(thud(), ws(185) - .1, .8)
# --- Escena 6 y cierre
put(whoosh(.5), 72.1, .4); put(pop(), ws(187) - .1, .5)
put(pop(900, 500), 72.8, .45, .4); put(pop(800, 420), 72.95, .45, .6)
put(tick(.03, 2000), 73.38, .8); put(whoosh(.35), 73.4, .3, )
put(whoosh(.5), 73.85, .45)
for i, n in enumerate((74, 78, 81, 86)):
    nn = int(1.2 * SR); tt = np.arange(nn) / SR
    put((np.sin(2 * np.pi * note(n) * tt) + .3 * np.sin(4 * np.pi * note(n) * tt)) * np.exp(-tt * 4) * .25, 74.2 + i * .07, .7, .35 + i * .1)

sfx = reverb(sfx, 1.2, .18, 5)

# ------------------------- MEZCLA -------------------------
mix = voice * 1.0 + mus * .16 + sfx * .38
peak = np.abs(mix).max()
mix = mix / peak * .97 if peak > .97 else mix
wavfile.write(OUT, SR, mix.astype(np.float32))
print('ok', DUR, 'peak', peak)
if len(sys.argv) > 3:  # stems para revisar la mezcla
    wavfile.write(sys.argv[3] + '_mus.wav', SR, (mus * .16).astype(np.float32))
    wavfile.write(sys.argv[3] + '_sfx.wav', SR, (sfx * .38).astype(np.float32))
