# Texturas de grano fino (PNG con alfa) para el look cinematográfico.
import numpy as np; from PIL import Image; import os
os.makedirs("public/grain", exist_ok=True); rng = np.random.default_rng(3)
for i in range(6):
    n = rng.normal(128, 50, (960, 540)).clip(0, 255).astype(np.uint8)
    a = np.full_like(n, 255)
    Image.fromarray(np.stack([n, n, n, a], -1), "RGBA").save(f"public/grain/g{i}.png", optimize=True)
print("ok")
