import numpy as np
from PIL import Image
def outline(beauty_png, id_png, ink=(10, 10, 14)):
    b = np.asarray(Image.open(beauty_png).convert('RGBA')).astype(np.float32) / 255
    idm = np.asarray(Image.open(id_png).convert('RGBA')).astype(np.int32)
    key = (idm[..., 0] << 16) | (idm[..., 1] << 8) | idm[..., 2]
    key = np.where(idm[..., 3] > 127, key, -1)
    p = np.pad(key, 1, mode='edge')
    e = ((p[:-2, 1:-1] != key) | (p[2:, 1:-1] != key) | (p[1:-1, :-2] != key) | (p[1:-1, 2:] != key)).astype(np.float32)
    q = np.pad(e, 1)
    e = np.maximum.reduce([e, q[:-2, 1:-1], q[2:, 1:-1], q[1:-1, :-2], q[1:-1, 2:]])
    q = np.pad(e, 1, mode='edge')
    e = (4 * e + q[:-2, 1:-1] + q[2:, 1:-1] + q[1:-1, :-2] + q[1:-1, 2:]) / 8
    a = b[..., 3]
    col = b[..., :3] * a[..., None]
    inkc = np.array(ink, np.float32) / 255
    out_a = e + a * (1 - e)
    out_c = inkc * e[..., None] + col * (1 - e[..., None])
    out = out_c / np.maximum(out_a[..., None], 1e-4)
    img = np.concatenate([out, out_a[..., None]], -1)
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
