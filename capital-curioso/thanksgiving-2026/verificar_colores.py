#!/usr/bin/env python3
"""Revisa TODOS los fotogramas del MP4: busca rosado/pastel/morado/naranja intenso y fondos claros.

Uso: python3 verificar_colores.py build/capital_curioso_thanksgiving_oficial.mp4
"""
import subprocess, sys
import numpy as np

path = sys.argv[1]
W, H = 270, 480   # análisis a 1/4 de resolución (suficiente para zonas de color)
raw = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{H}", "-f", "rawvideo",
                        "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE).stdout

def hsv(a):
    a = a.astype(np.float32) / 255
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    d = mx - mn + 1e-6
    h = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = np.where(mx > 0, d / (mx + 1e-6), 0)
    return h, s, mx

worst = {"rosado/pastel": (0, -1), "morado": (0, -1), "naranja": (0, -1), "fondo claro": (0, -1)}
k = 0
flags = []
while True:
    buf = raw.read(W * H * 3)
    if len(buf) < W * H * 3: break
    a = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    h, s, v = hsv(a)
    lum = (.2126 * a[..., 0] + .7152 * a[..., 1] + .0722 * a[..., 2])
    m = {
        # rosado / salmón / coral / pastel: rojo-magenta claro y poco saturado
        "rosado/pastel": ((h >= 300) | (h <= 20)) & (s > .12) & (s < .62) & (v > .72),
        "morado": (h > 255) & (h < 300) & (s > .25) & (v > .35),
        "naranja": (h > 18) & (h < 45) & (s > .55) & (v > .75),
        "fondo claro": lum > 200,
    }
    stats = {n: float(x.mean() * 100) for n, x in m.items()}
    for n, pct in stats.items():
        if pct > worst[n][0]: worst[n] = (pct, k)
    if stats["rosado/pastel"] > .5 or stats["morado"] > .5 or stats["fondo claro"] > 25:
        flags.append((k, stats))
    k += 1

print(f"Fotogramas revisados: {k}")
for n, (pct, fi) in worst.items():
    print(f"  máximo {n:14s}: {pct:5.2f} % del cuadro (fotograma {fi}, {fi / 30:.2f} s)")
print(f"Fotogramas marcados (>0.5 % rosado/morado o >25 % claro): {len(flags)}")
for fi, st in flags[:20]:
    print("   ", fi, f"{fi / 30:.2f}s", {a: round(b, 2) for a, b in st.items()})
