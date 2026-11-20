# Música de fondo espacial sintetizada (libre de derechos): pads suaves + arpegio lento.
import numpy as np, wave, sys
sr = 44100; dur = float(sys.argv[1]) + 0.5; n = int(sr * dur); t = np.arange(n) / sr
def f(m): return 440 * 2 ** ((m - 69) / 12)
chords = [[57, 60, 64, 71], [53, 57, 60, 67], [48, 55, 60, 64], [55, 59, 62, 69]]  # Am9 F C G
bar = 4.8
out = np.zeros(n)
rng = np.random.RandomState(3)
for i in range(int(dur / bar) + 1):
    c = chords[i % 4]; s0 = int(i * bar * sr); s1 = min(n, int((i + 1) * bar * sr) + int(1.5 * sr))
    if s0 >= n: break
    tt = np.arange(s1 - s0) / sr; L = bar + 1.5
    env = np.minimum(1, tt / 1.6) * np.clip((L - tt) / 1.6, 0, 1)
    for m in c:
        for d in (-0.12, 0.0, 0.12):
            out[s0:s1] += 0.035 * np.sin(2 * np.pi * f(m) * (1 + d / 100) * tt + rng.rand() * 6) * env
    out[s0:s1] += 0.07 * np.sin(2 * np.pi * f(c[0] - 12) * tt) * env
    # arpegio tipo campanita
    arp = [c[0] + 24, c[2] + 12, c[1] + 24, c[3] + 12]
    for k in range(8):
        a0 = s0 + int(k * bar / 8 * sr); a1 = min(n, a0 + int(1.8 * sr))
        if a0 >= n or rng.rand() < 0.3: continue
        ta = np.arange(a1 - a0) / sr; m = arp[k % 4]
        out[a0:a1] += 0.03 * (np.sin(2 * np.pi * f(m) * ta) + 0.25 * np.sin(4 * np.pi * f(m) * ta)) * np.exp(-ta * 2.2)
# eco simple
d = int(0.42 * sr); e = out.copy(); e[d:] += 0.35 * out[:-d]; out = e
fade = np.minimum(1, t / 2.0) * np.clip((dur - 0.5 - t) / 3.0, 0, 1)
out *= fade; out /= np.abs(out).max()
w = wave.open('out/music.wav', 'w'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
w.writeframes((out * 0.9 * 32767).astype(np.int16).tobytes()); w.close()
