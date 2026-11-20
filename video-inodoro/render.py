"""Compositor: línea de tiempo de cámaras, transiciones con zoom + fundido, textura de papel, subtítulos y render a MP4.

Uso:
  python3 render.py frames 12.5 30 44.1      -> PNG de prueba en out/
  python3 render.py video                    -> out/video_sin_audio.mp4 (4 procesos)
"""
import math
import os
import subprocess
import sys
import numpy as np
import cairo
from PIL import Image

from common import *
import world_city as A
import world_bath as B
import world_plant as P
import captions

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)

DUR = 3632640 / 48000.0           # duración exacta de la voz decodificada
NFRAMES = int(round(DUR * FPS))   # 2270

# -------------------------------------------------------------------- cámaras
CAM_A = Cam([
    (0.0, -80, 120, 0.5), (1.3, -82, 50, 0.85), (2.4, -86, -40, 1.6), (3.2, -86, -80, 2.7),
    (47.8, -262, 236, 2.3), (49.0, -330, 268, 1.3), (50.4, -380, 255, 0.70), (51.9, 20, 430, 0.50),
    (53.2, 1150, 950, 0.62), (54.7, 1250, 1010, 1.35),
    (72.3, -86, -30, 2.3), (73.6, -80, 30, 1.15), (DUR, -45, 150, 0.40),
])
CAM_B = Cam([
    (2.2, 900, -350, 0.46), (3.4, 700, 560, 0.62), (4.4, 520, 1070, 0.98), (5.5, 480, 1075, 1.08),
    (6.6, 285, 900, 2.0), (8.5, 268, 892, 2.35), (10.5, 262, 900, 2.3), (11.9, 330, 860, 2.05),
    (13.4, 335, 900, 1.9), (15.0, 430, 1020, 1.45), (17.2, 600, 1180, 1.55), (19.4, 560, 1300, 1.9),
    (22.3, 490, 1320, 2.2), (24.4, 500, 1300, 2.0), (26.3, 540, 1260, 1.5), (28.5, 560, 1220, 1.15),
    (30.2, 380, 1000, 1.35), (31.8, 268, 900, 2.0), (33.6, 215, 880, 2.25), (35.4, 140, 1080, 1.55),
    (37.4, 200, 960, 1.85), (40.0, 262, 880, 2.15), (42.6, 205, 830, 2.45), (44.1, 300, 820, 2.0),
    (45.5, 420, 1280, 1.35), (46.9, 470, 1690, 1.45), (48.7, 1550, 1795, 1.35),
    (60.7, 660, 1250, 0.8), (62.4, 620, 1240, 1.4), (64.0, 520, 1330, 2.1), (66.4, 480, 1340, 2.3),
    (67.9, 430, 1420, 1.9), (69.6, 440, 1360, 2.1), (70.7, 500, 1120, 1.15), (71.9, 500, 1060, 1.0),
    (73.2, 840, 250, 0.40),
])
CAM_C = Cam([
    (53.8, 150, 1080, 0.6), (54.9, 520, 1150, 1.3), (56.0, 960, 1180, 1.2), (57.2, 1300, 1210, 1.4),
    (58.3, 1500, 1200, 1.25), (59.3, 2190, 1170, 1.3), (60.4, 2860, 1070, 1.2), (61.7, 3050, 1000, 0.7),
])

# (mundo, inicio, fin) con solapes = transiciones suaves
SEGS = [('A', -1, 3.15), ('B', 2.35, 48.65), ('A', 47.85, 54.65), ('C', 53.85, 61.65), ('B', 60.75, 73.25), ('A', 72.35, 99)]


def city_params(t):
    if t < 40:
        return dict()
    if t > 70:
        return dict()
    return dict(xray=prog(t, 47.9, 48.7), flow_main=prog(t, 47.9, 48.6), flow_all=prog(t, 51.0, 51.9), toplant=prog(t, 52.2, 52.9))


def render_world(name, t):
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(surf)
    if name == 'A':
        cx, cy, z = CAM_A.at(t)
        apply_cam(ctx, cx, cy, z, t)
        A.draw(ctx, t, **city_params(t))
        ctx.identity_matrix()
        oc = window(t, -1, 3.2, 0.01, 0.6) + window(t, 72.6, 99, 0.6, 0.01)
        A.overlay_clouds(ctx, t, z, oc)
    elif name == 'B':
        cx, cy, z = CAM_B.at(t)
        apply_cam(ctx, cx, cy, z, t)
        B.draw(ctx, t)
    else:
        cx, cy, z = CAM_C.at(t)
        apply_cam(ctx, cx, cy, z, t)
        P.draw(ctx, t)
    return surf


def paper_texture():
    path = os.path.join(OUT, 'paper.npy')
    if os.path.exists(path):
        return np.load(path)
    rng = np.random.default_rng(4)

    def noise(scale):
        small = rng.random((H // scale + 2, W // scale + 2)).astype(np.float32)
        im = Image.fromarray((small * 255).astype(np.uint8)).resize((W + 2 * scale, H + 2 * scale), Image.BICUBIC)
        return np.asarray(im, dtype=np.float32)[:H, :W] / 255.0

    n = 0.5 * noise(2) + 0.3 * noise(9) + 0.2 * noise(40)
    tex = 1.0 - 0.06 * (n - n.mean()) * 2.2 - 0.025
    # fibras
    fib = np.zeros((H, W), np.float32)
    for _ in range(700):
        x, y = rng.integers(0, W), rng.integers(0, H)
        ln = rng.integers(8, 40)
        ang = rng.random() * math.pi
        for k in range(ln):
            xx = int(x + math.cos(ang) * k)
            yy = int(y + math.sin(ang) * k)
            if 0 <= xx < W and 0 <= yy < H:
                fib[yy, xx] = 1
    tex -= 0.035 * fib
    # viñeta suave
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2)
    tex *= 1 - 0.10 * np.clip(d - 0.35, 0, 1) ** 1.5
    # tinte cálido de papel (BGR)
    t3 = np.stack([tex * 0.965, tex * 0.985, tex * 1.0], axis=-1)
    t16 = np.clip(t3 * 256, 0, 256).astype(np.uint32)
    np.save(path, t16)
    return t16


TEX = None


def frame(t):
    global TEX
    if TEX is None:
        TEX = paper_texture()
    active = [(n, a, b) for (n, a, b) in SEGS if a <= t < b]
    base = None
    for i, (n, a, b) in enumerate(active):
        surf = render_world(n, t)
        if base is None:
            base = surf
        else:
            # el mundo entrante se funde encima
            al = prog(t, a, min(b, a + 0.8), eio)
            c = cairo.Context(base)
            c.set_source_surface(surf, 0, 0)
            c.paint_with_alpha(al)
    base.flush()
    arr = np.ndarray((H, W, 4), np.uint8, base.get_data())
    rgb = arr[:, :, :3].astype(np.uint32)
    arr[:, :, :3] = np.minimum((rgb * TEX) >> 8, 255).astype(np.uint8)
    base.mark_dirty()
    ctx = cairo.Context(base)
    captions.draw(ctx, t)
    base.flush()
    return base


def worker(i0, i1, path):
    ff = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', path],
                          stdin=subprocess.PIPE)
    for i in range(i0, i1):
        s = frame(i / FPS)
        ff.stdin.write(bytes(s.get_data()))
        if i % 60 == 0:
            print(f'[{os.getpid()}] frame {i}/{i1}', flush=True)
    ff.stdin.close()
    ff.wait()


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'frames':
        for a in sys.argv[2:]:
            t = float(a)
            frame(t).write_to_png(os.path.join(OUT, f'f_{t:06.2f}.png'))
    elif mode == 'video':
        nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 4
        paper_texture()
        bounds = [round(k * NFRAMES / nproc) for k in range(nproc + 1)]
        procs = []
        for k in range(nproc):
            pid = os.fork()
            if pid == 0:
                worker(bounds[k], bounds[k + 1], os.path.join(OUT, f'seg{k}.mp4'))
                os._exit(0)
            procs.append(pid)
        for p in procs:
            os.waitpid(p, 0)
        with open(os.path.join(OUT, 'segs.txt'), 'w') as f:
            for k in range(nproc):
                f.write(f"file 'seg{k}.mp4'\n")
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', os.path.join(OUT, 'segs.txt'),
                        '-c', 'copy', os.path.join(OUT, 'video_sin_audio.mp4')], check=True)
        print('ok', NFRAMES, 'frames')
