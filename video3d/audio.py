"""Synthesize royalty-free background music + SFX and mix with the voice."""
import numpy as np, subprocess, os, json
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100
DUR = 84.43
N = int(DUR * SR) + SR
rng = np.random.default_rng(3)


def t_arr(n):
    return np.arange(n) / SR


def env_adsr(n, a=0.01, d=0.1, s=0.6, r=0.2):
    e = np.ones(n) * s
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na = min(na, n)
    e[:na] = np.linspace(0, 1, na)
    if na + nd < n:
        e[na:na + nd] = np.linspace(1, s, nd)
    if nr < n:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def note_f(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lowpass(x, fc):
    # simple one-pole
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def lp_fast(x, fc):
    from scipy.signal import butter, sosfilt
    sos = butter(2, fc, 'low', fs=SR, output='sos')
    return sosfilt(sos, x)


def hp_fast(x, fc):
    from scipy.signal import butter, sosfilt
    sos = butter(2, fc, 'high', fs=SR, output='sos')
    return sosfilt(sos, x)


def bp_fast(x, lo, hi):
    from scipy.signal import butter, sosfilt
    sos = butter(2, [lo, hi], 'band', fs=SR, output='sos')
    return sosfilt(sos, x)


# ------------------------------------------------------------- music
def music():
    bpm = 104
    beat = 60 / bpm
    out = np.zeros(N)
    # I - V - vi - IV in G major
    prog = [(55, [55, 59, 62]), (62, [62, 66, 69]), (64, [64, 67, 71]), (60, [60, 64, 67])]
    bar = 4 * beat
    nbars = int(DUR / bar) + 2
    for b in range(nbars):
        root, chord = prog[b % 4]
        t0 = b * bar
        # soft pad
        n = int(bar * SR)
        tt = t_arr(n)
        pad = sum(np.sin(2 * np.pi * note_f(m) * tt) + 0.3 * np.sin(4 * np.pi * note_f(m) * tt) for m in chord)
        pad *= env_adsr(n, 0.3, 0.3, 0.8, 0.4) * 0.05
        i0 = int(t0 * SR)
        out[i0:i0 + n] += pad[:max(0, min(n, N - i0))]
        # bass on beats 1 and 3
        for k in (0, 2):
            nb = int(beat * 1.6 * SR)
            tb = t_arr(nb)
            bs = np.sin(2 * np.pi * note_f(root - 24) * tb) * np.exp(-tb * 3) * 0.22
            j = int((t0 + k * beat) * SR)
            out[j:j + nb] += bs[:max(0, min(nb, N - j))]
        # plucky arpeggio (8ths)
        arp = chord + [chord[1] + 12, chord[0] + 12, chord[2], chord[1], chord[0] + 12]
        for k in range(8):
            m = arp[k % len(arp)] + 12
            npk = int(beat / 2 * 1.5 * SR)
            tp = t_arr(npk)
            f = note_f(m)
            pl = (np.sin(2 * np.pi * f * tp) + 0.4 * np.sin(2 * np.pi * 2 * f * tp) + 0.15 * np.sin(2 * np.pi * 3 * f * tp)) * np.exp(-tp * 9) * 0.08
            j = int((t0 + k * beat / 2) * SR)
            out[j:j + npk] += pl[:max(0, min(npk, N - j))]
        # light drums: kick 1&3, clap 2&4, hats 8ths
        for k in range(4):
            j = int((t0 + k * beat) * SR)
            if k in (0, 2):
                nk = int(0.25 * SR)
                tk = t_arr(nk)
                kick = np.sin(2 * np.pi * (50 + 90 * np.exp(-tk * 30)) * tk) * np.exp(-tk * 14) * 0.35
                out[j:j + nk] += kick[:max(0, min(nk, N - j))]
            else:
                nc = int(0.18 * SR)
                cl = bp_fast(rng.standard_normal(nc), 900, 3000) * np.exp(-t_arr(nc) * 22) * 0.12
                out[j:j + nc] += cl[:max(0, min(nc, N - j))]
        for k in range(8):
            j = int((t0 + k * beat / 2) * SR)
            nh = int(0.05 * SR)
            hh = hp_fast(rng.standard_normal(nh), 7000) * np.exp(-t_arr(nh) * 70) * (0.05 if k % 2 else 0.035)
            out[j:j + nh] += hh[:max(0, min(nh, N - j))]
    # fade in/out
    out[:int(1.0 * SR)] *= np.linspace(0, 1, int(1.0 * SR))
    fo0, fo1 = int(82.6 * SR), int(84.4 * SR)
    out[fo0:fo1] *= np.linspace(1, 0, fo1 - fo0)
    out[fo1:] = 0
    return out


# ------------------------------------------------------------- sfx
def whoosh(dur=0.8):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    tt = np.linspace(0, 1, n)
    # sweeping band-pass via chunked filtering
    y = np.zeros(n)
    seg = 1024
    from scipy.signal import butter, sosfilt
    for i in range(0, n, seg):
        c = 300 + 2500 * np.sin(np.pi * tt[i]) ** 2
        sos = butter(2, [c * 0.6, c * 1.4], 'band', fs=SR, output='sos')
        y[i:i + seg] = sosfilt(sos, x[i:i + seg])
    return y * np.sin(np.pi * tt) ** 1.5 * 0.5


def pop():
    n = int(0.18 * SR)
    tt = t_arr(n)
    f = 300 + 700 * np.exp(-tt * 40)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 28) * 0.55


def click():
    n = int(0.06 * SR)
    tt = t_arr(n)
    c = hp_fast(rng.standard_normal(n), 2500) * np.exp(-tt * 160) * 0.6
    c += np.sin(2 * np.pi * 2200 * tt) * np.exp(-tt * 120) * 0.35
    return c


def v10_roar(dur=1.7):
    n = int(dur * SR)
    tt = t_arr(n)
    u = tt / dur
    rpm = 1800 + 6500 * np.sin(np.pi * np.clip(u * 1.15, 0, 1)) ** 1.2
    fire = rpm / 60 * 5  # V10 four-stroke: 5 firings per revolution
    ph = 2 * np.pi * np.cumsum(fire) / SR
    sig = np.zeros(n)
    for h in range(1, 9):
        sig += np.sin(h * ph + rng.random() * 6) / h ** 0.9
    sig += 0.5 * np.sin(0.5 * ph)  # half-order growl
    sig = np.tanh(sig * 1.6)
    sig += 0.25 * bp_fast(rng.standard_normal(n), 200, 2500)
    sig = lp_fast(sig, 3500)
    e = np.minimum(1, u * 12) * np.minimum(1, (1 - u) * 4)
    return sig * e * 0.32


def mixin(buf, x, t, g=1.0):
    j = int(t * SR)
    m = min(len(x), len(buf) - j)
    buf[j:j + m] += x[:m] * g


def main():
    voice, vsr = sf.read(os.path.join(HERE, 'voz.wav'))
    if voice.ndim > 1:
        voice = voice.mean(1)
    assert vsr == SR
    mus = music()
    sfx = np.zeros(N)
    mixin(sfx, whoosh(0.9), 7.05, 0.9)
    mixin(sfx, pop() * 0.6, 9.25)
    mixin(sfx, v10_roar(1.8), 21.30, 1.0)
    mixin(sfx, click(), 40.45)
    for tc in (64.45, 67.32, 69.22):
        mixin(sfx, click(), tc)
    mixin(sfx, whoosh(0.6), 76.5, 0.8)
    mixin(sfx, pop(), 77.92)
    mixin(sfx, whoosh(0.7), 45.35, 0.5)
    # duck music under the voice (gentle)
    env = np.abs(np.pad(voice, (0, N - len(voice)))[:N])
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    env = uniform_filter1d(maximum_filter1d(env, int(0.15 * SR)), int(0.25 * SR))
    duck = 1 - 0.35 * np.clip(env / 0.2, 0, 1)
    v = np.pad(voice, (0, N - len(voice)))[:N]
    v = v / (np.max(np.abs(v)) + 1e-9) * 0.89
    mix = v + mus * 0.16 * duck + sfx * 0.55
    mix = mix[:int(DUR * SR)]
    peak = np.max(np.abs(mix))
    if peak > 0.98:
        mix *= 0.98 / peak
    sf.write(os.path.join(HERE, 'mix.wav'), np.stack([mix, mix], 1), SR)
    print('peak', peak)


if __name__ == '__main__':
    main()
