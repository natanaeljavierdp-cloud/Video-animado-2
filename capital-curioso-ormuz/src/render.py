import sys, subprocess, skia
sys.path.insert(0, '.')
from scenes import frame, W, H, FPS
a, b, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                      '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
s = skia.Surface(W, H)
for i in range(a, b):
    c = s.getCanvas(); frame(c, i / FPS)
    p.stdin.write(s.makeImageSnapshot().tobytes())
    if i % 100 == 0: print(out, i, flush=True)
p.stdin.close(); p.wait()
