"""Synthesize royalty-free background music + SFX and mix with the voice. Output: mix.wav (stereo 48k)."""
import numpy as np, subprocess, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as T

SR = 48000
DUR = 60.30
N = int(SR * DUR)
rng = np.random.default_rng(3)


def load_voice():
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "voice.mp3", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    v = np.frombuffer(raw, dtype=np.float32).copy()
    out = np.zeros(N, np.float32)
    out[:min(N, len(v))] = v[:N]
    return out


def env_adsr(n, a, d, s, r, sus_len):
    A = int(a * SR); D = int(d * SR); R = int(r * SR); S_ = max(0, n - A - D - R)
    e = np.concatenate([np.linspace(0, 1, A, False), np.linspace(1, s, D, False), np.full(S_, s), np.linspace(s, 0, R)])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))


def lowpass(x, fc):
    # one-pole lowpass (applied twice)
    a = np.exp(-2 * np.pi * fc / SR)
    from scipy.signal import lfilter
    y = lfilter([1 - a], [1, -a], x)
    return lfilter([1 - a], [1, -a], y)


def highpass(x, fc):
    return x - lowpass(x, fc)


def note(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def music():
    L = np.zeros(N); Rr = np.zeros(N)
    t = np.arange(N) / SR
    bpm = 96
    beat = 60 / bpm
    bar = 4 * beat
    # chord progression Am - F - C - G  (midi roots)
    prog = [(57, [0, 3, 7, 12]), (53, [0, 4, 7, 12]), (48, [0, 4, 7, 12]), (55, [0, 4, 7, 11])]
    nbars = int(DUR / bar) + 2
    # pads: detuned saws, lowpassed, long attack
    pad = np.zeros(N)
    for b in range(nbars):
        root, iv = prog[b % 4]
        s0 = int(b * bar * SR); s1 = min(N, int((b + 1) * bar * SR + 0.8 * SR))
        if s0 >= N:
            break
        n = s1 - s0
        tt = np.arange(n) / SR
        e = env_adsr(n, 1.2, 0.5, 0.8, 1.0, n)
        sig = np.zeros(n)
        for k in iv[:3]:
            f = note(root + k + 12)
            for det in (-0.12, 0.0, 0.11):
                ph = rng.random() * 2 * np.pi
                sig += (2 * ((f * (1 + det / 100) * tt + ph / (2 * np.pi)) % 1) - 1)
        pad[s0:s1] += sig * e * 0.05
    pad = lowpass(pad, 900)
    # sub bass pulse on each beat (soft)
    bass = np.zeros(N)
    for b in range(nbars * 4):
        s0 = int(b * beat * SR)
        if s0 >= N:
            break
        root, _ = prog[(b // 4) % 4]
        f = note(root - 12)
        n = min(int(beat * SR * 0.95), N - s0)
        tt = np.arange(n) / SR
        e = np.exp(-tt * 3.0) * (1 - np.exp(-tt * 200))
        bass[s0:s0 + n] += np.sin(2 * np.pi * f * tt) * e * 0.22
    # arpeggio plucks (8th notes) entering after the intro
    arp = np.zeros(N)
    for k in range(int(DUR / (beat / 2))):
        s0 = int(k * beat / 2 * SR)
        b = int(k // 8)
        root, iv = prog[b % 4]
        m = root + 24 + iv[[0, 2, 1, 3, 2, 1, 3, 2][k % 8]]
        n = min(int(0.6 * SR), N - s0)
        if n <= 0:
            break
        tt = np.arange(n) / SR
        e = np.exp(-tt * 9)
        sig = np.sin(2 * np.pi * note(m) * tt) + 0.3 * np.sin(2 * np.pi * note(m) * 2 * tt) * np.exp(-tt * 20)
        arp[s0:s0 + n] += sig * e * 0.05
    # soft hats
    hat = np.zeros(N)
    for k in range(int(DUR / (beat / 2))):
        s0 = int((k * beat / 2 + beat / 4) * SR)
        n = min(int(0.05 * SR), N - s0)
        if n <= 0:
            break
        hat[s0:s0 + n] += rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 90) * 0.02
    hat = highpass(hat, 6000)
    # sections: intro pad only, arp from 6s, quieter during mechanical detail, swell at end
    sec_arp = np.interp(t, [0, 5.5, 6.5, 52, 57, 60.3], [0, 0, 1, 1, 0.6, 0])
    sec_all = np.interp(t, [0, 1.0, 58.6, 60.3], [0.4, 1, 1, 0])
    mono = pad + bass * np.interp(t, [0, 2.5, 3.5], [0, 0, 1]) + hat * sec_arp
    # stereo: arp pingpong
    pan = 0.5 + 0.35 * np.sin(2 * np.pi * t / (beat * 2))
    L = (mono + arp * sec_arp * (1 - pan) * 1.4) * sec_all
    Rr = (mono + arp * sec_arp * pan * 1.4) * sec_all
    # simple stereo widening reverb-ish (short delays)
    for d, g in ((0.031, 0.25), (0.047, 0.2), (0.089, 0.15)):
        k = int(d * SR)
        L[k:] += Rr[:-k] * g
        Rr[k:] += L[:-k] * g * 0.9
    return np.stack([L, Rr], 1)


# ---------------------------------------------------------------- SFX
def whoosh(dur, rise=True, fc0=300, fc1=4000, amp=0.5):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    tt = np.linspace(0, 1, n)
    out = np.zeros(n)
    seg = 512
    # time-varying lowpass via segment filtering
    from scipy.signal import butter, sosfilt
    for i in range(0, n, seg):
        u = tt[i]
        fc = fc0 + (fc1 - fc0) * (u if rise else 1 - u)
        sos = butter(2, [max(50, fc * 0.5), min(SR / 2 - 100, fc * 1.5)], btype='band', fs=SR, output='sos')
        out[i:i + seg] = sosfilt(sos, x[i:i + seg])
    e = np.sin(np.pi * tt) ** 1.5 if rise else np.sin(np.pi * tt) ** 1.5
    return out * e * amp


def click(amp=0.6, f=3200):
    n = int(0.06 * SR)
    tt = np.arange(n) / SR
    x = rng.standard_normal(n) * np.exp(-tt * 400) * 0.6 + np.sin(2 * np.pi * f * tt) * np.exp(-tt * 120)
    x += 0.5 * np.sin(2 * np.pi * f * 1.73 * tt) * np.exp(-tt * 180)
    return highpass(x, 900) * amp


def metal_ting(amp=0.35, f0=1800):
    n = int(0.9 * SR)
    tt = np.arange(n) / SR
    x = np.zeros(n)
    for k, (r, g, dec) in enumerate(((1.0, 1.0, 6), (2.76, 0.5, 9), (5.40, 0.3, 14), (8.93, 0.2, 20))):
        x += g * np.sin(2 * np.pi * f0 * r * tt + rng.random() * 6) * np.exp(-tt * dec)
    thud = np.sin(2 * np.pi * 120 * tt) * np.exp(-tt * 40) * 0.6
    tr = rng.standard_normal(n) * np.exp(-tt * 300) * 0.4
    return (x * 0.5 + thud + highpass(tr, 2000)) * amp


def chain_rattle(dur=0.5, amp=0.3):
    n = int(dur * SR)
    out = np.zeros(n)
    k = 0
    tpos = 0.0
    while tpos < dur - 0.03:
        c = click(0.25 + 0.15 * rng.random(), 2200 + 1800 * rng.random())
        s = int(tpos * SR)
        m = min(len(c), n - s)
        out[s:s + m] += c[:m] * (1 - tpos / dur) ** 0.7
        tpos += 0.018 + 0.03 * rng.random()
    tt = np.arange(n) / SR
    clunk = np.sin(2 * np.pi * 95 * tt) * np.exp(-tt * 25) * 0.5
    return (out + clunk) * amp


def add(buf, sig, t, gain=1.0, pan=0.5):
    s = int(t * SR)
    if s >= N:
        return
    m = min(len(sig), N - s)
    buf[s:s + m, 0] += sig[:m] * gain * (1 - pan) * 2 ** 0.5
    buf[s:s + m, 1] += sig[:m] * gain * pan * 2 ** 0.5


def sfx():
    b = np.zeros((N, 2))
    # explode whoosh
    add(b, whoosh(1.6, True, 200, 5000, 0.55), 2.45, pan=0.35)
    add(b, whoosh(1.4, False, 300, 3000, 0.35), 3.4, pan=0.65)
    # camera fly-through between parts
    add(b, whoosh(1.5, True, 150, 2500, 0.22), 4.6, pan=0.6)
    # shifter: lever press click (ratchet) + release
    add(b, click(0.9, 3400), 8.84, pan=0.5)
    add(b, click(0.5, 2600), 8.90, pan=0.5)
    add(b, click(0.35, 2000), 9.86, pan=0.5)
    # cable "zing" as the light pulse starts
    n = int(0.5 * SR); tt = np.arange(n) / SR
    zing = np.sin(2 * np.pi * (1200 + 1600 * tt) * tt) * np.exp(-tt * 6) * 0.12
    add(b, zing, 9.42)
    # rear upshift: click, chain engaging
    add(b, click(0.5, 3000), 18.35, pan=0.45)
    add(b, chain_rattle(0.9, 0.55), 19.5, pan=0.45)
    # downshift
    add(b, click(0.45, 2800), 28.6, pan=0.45)
    add(b, chain_rattle(0.8, 0.5), 29.9, pan=0.45)
    # front shift
    add(b, click(0.45, 2600), 33.6, pan=0.55)
    add(b, chain_rattle(0.9, 0.55), 34.8, pan=0.55)
    # transitions
    add(b, whoosh(0.9, True, 300, 4000, 0.30), 42.0, pan=0.4)
    add(b, whoosh(0.9, False, 300, 3000, 0.22), 44.4, pan=0.6)
    add(b, whoosh(0.9, True, 300, 4000, 0.22), 48.9, pan=0.4)
    add(b, whoosh(1.2, False, 200, 3500, 0.30), 51.8, pan=0.5)
    # road wind
    n = int(2.6 * SR)
    wind = lowpass(rng.standard_normal(n), 600) * np.sin(np.linspace(0, np.pi, n)) * 0.25
    add(b, wind, 42.3, pan=0.5)
    # reassembly: reverse whoosh then metal tings at landings
    add(b, whoosh(1.0, True, 200, 5000, 0.35), 52.0, pan=0.5)
    T.explode_final(55.0)
    for i, (name, tl) in enumerate(sorted(T.LANDINGS.items(), key=lambda a: a[1])):
        f0 = 1500 + 900 * ((i * 7) % 5) / 4
        add(b, metal_ting(0.30 if not name.startswith("bolt") else 0.18, f0), tl - 0.02, pan=0.3 + 0.4 * ((i * 3) % 5) / 4)
    # final soft low hit
    n = int(2.5 * SR); tt = np.arange(n) / SR
    boom = np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 1.8) * 0.35
    add(b, boom, 57.35)
    return b


def main():
    voice = load_voice()
    # voice level normalize (peak ~ -3 dBFS, keep dynamics)
    voice = voice / (np.max(np.abs(voice)) + 1e-9) * 0.70
    mus = music()
    mus = mus / (np.max(np.abs(mus)) + 1e-9) * 0.16
    # ducking under voice
    env = np.abs(voice)
    env = lowpass(env, 6)
    env = env / (env.max() + 1e-9)
    duck = 1 - 0.45 * np.clip(env * 4, 0, 1)
    mus *= duck[:, None]
    fx = sfx()
    fx *= 0.55
    mix = mus + fx + np.stack([voice, voice], 1)
    t = np.arange(N) / SR
    mix *= np.interp(t, [0, 0.05, 59.6, 60.3], [0, 1, 1, 0])[:, None]
    pk = np.max(np.abs(mix))
    if pk > 0.97:
        mix = mix / pk * 0.97
    import wave
    data = (mix * 32767).astype(np.int16)
    with wave.open("mix.wav", "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())
    print("peak", pk, "written mix.wav")


if __name__ == "__main__":
    main()
