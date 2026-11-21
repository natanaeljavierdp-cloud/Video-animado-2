"""Paquete gráfico FRUTINOTICIASRD: sprites RGBA (PIL) y utilidades de animación.
Paleta: azul eléctrico, azul oscuro, rojo intenso, blanco, plateado y negro."""
import json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

FONTS = "/usr/share/fonts/opentype/inter/"
AZUL_E = (30, 144, 255)
AZUL_C = (64, 190, 255)
AZUL_O = (6, 22, 58)
AZUL_M = (14, 52, 120)
ROJO = (226, 22, 42)
ROJO_C = (255, 64, 74)
BLANCO = (255, 255, 255)
PLATA = (200, 210, 224)
NEGRO = (0, 0, 0)
# bandera dominicana
RD_AZUL = (0, 45, 98)
RD_ROJO = (206, 17, 38)

_fc = {}
def font(nombre, size):
    k = (nombre, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(FONTS + nombre + ".otf", size)
    return _fc[k]

# ------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp(x); return x ** 3
def ease_io(x): x = clamp(x); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def ventana(t, t0, t1, fin=0.3, fout=0.3):
    """Progreso de entrada (0..1) y salida (1..0) de un elemento visible entre t0 y t1."""
    if t < t0 or t > t1: return 0.0, 0.0
    return clamp((t - t0) / fin), clamp((t1 - t) / fout)

# ------------------------------------------------------------- helpers de sprites
def con_alpha(img, a):
    if a >= 0.999: return img
    if a <= 0.001: return None
    im = img.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return im

def recorte_h(img, frac, desde="izq"):
    """Revela horizontalmente una fracción del sprite."""
    frac = clamp(frac)
    if frac <= 0: return None
    w, h = img.size; ww = max(1, int(w * frac))
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rectangle([0, 0, ww, h] if desde == "izq" else [w - ww, 0, w, h] if desde == "der" else [(w - ww) // 2, 0, (w + ww) // 2, h], fill=255)
    im = img.copy(); im.putalpha(ImageChops.multiply(im.getchannel("A"), m)); return im

def destello(img, p, ancho=0.18, fuerza=0.85):
    """Barrido de luz diagonal sobre las zonas opacas del sprite (p: 0..1)."""
    if p <= 0 or p >= 1: return img
    w, h = img.size
    x = np.arange(w)[None, :] + np.arange(h)[:, None] * 0.45
    c = -0.3 * w + p * (1.6 * w)
    band = np.clip(1 - np.abs(x - c) / (ancho * w), 0, 1) ** 2 * fuerza
    arr = np.asarray(img).astype(np.float32)
    a = arr[..., 3:4] / 255
    arr[..., :3] = arr[..., :3] + (255 - arr[..., :3]) * band[..., None] * a
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")

def glow(img, radio=10, color=AZUL_E, fuerza=1.0, pad=None):
    pad = pad if pad is not None else radio * 3
    w, h = img.size
    base = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    a = Image.new("L", base.size, 0); a.paste(img.getchannel("A"), (pad, pad))
    a = a.filter(ImageFilter.GaussianBlur(radio)).point(lambda v: min(255, int(v * fuerza)))
    g = Image.new("RGBA", base.size, color + (0,)); g.putalpha(a)
    base.alpha_composite(g); base.alpha_composite(img, (pad, pad))
    return base, pad

def gradiente_v(w, h, c0, c1, a0=255, a1=255):
    t = np.linspace(0, 1, h)[:, None, None]
    c0 = np.array(c0 + (a0,), np.float32); c1 = np.array(c1 + (a1,), np.float32)
    arr = (c0 * (1 - t) + c1 * t) * np.ones((1, w, 1), np.float32)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")

def gradiente_h(w, h, c0, c1, a0=255, a1=255):
    t = np.linspace(0, 1, w)[None, :, None]
    c0 = np.array(c0 + (a0,), np.float32); c1 = np.array(c1 + (a1,), np.float32)
    arr = (c0 * (1 - t) + c1 * t) * np.ones((h, 1, 1), np.float32)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")

def texto_relleno(txt, fnt, relleno, stroke=0, stroke_color=(0, 0, 0)):
    """Texto con relleno de imagen (gradiente metálico) y contorno opcional."""
    bb = fnt.getbbox(txt, stroke_width=stroke)
    w, h = bb[2] - bb[0] + 4, bb[3] - bb[1] + 4
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).text((-bb[0] + 2, -bb[1] + 2), txt, font=fnt, fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if stroke:
        ms = Image.new("L", (w, h), 0)
        ImageDraw.Draw(ms).text((-bb[0] + 2, -bb[1] + 2), txt, font=fnt, fill=255, stroke_width=stroke, stroke_fill=255)
        sc = Image.new("RGBA", (w, h), stroke_color + (255,)); sc.putalpha(ms); out.alpha_composite(sc)
    fill = relleno.resize((w, h)) if isinstance(relleno, Image.Image) else Image.new("RGBA", (w, h), relleno + (255,))
    fill = fill.copy(); fill.putalpha(ImageChops.multiply(fill.getchannel("A"), m))
    out.alpha_composite(fill)
    return out

def metal(w, h):
    """Gradiente plateado metálico (blanco -> plata -> blanco)."""
    t = np.linspace(0, 1, h)
    v = 255 - 70 * np.exp(-((t - 0.58) / 0.16) ** 2) - 20 * t
    arr = np.stack([v * 0.96, v * 0.98, v, np.full_like(v, 255)], 1)[:, None, :] * np.ones((1, w, 1))
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")

def rojo_metal(w, h):
    t = np.linspace(0, 1, h)
    r = 255 - 40 * t; g = 70 - 50 * t; b = 80 - 50 * t
    arr = np.stack([r, g, b, np.full_like(r, 255)], 1)[:, None, :] * np.ones((1, w, 1))
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")

def sombra(img, dx=0, dy=6, radio=8, alpha=0.6):
    pad = radio * 3
    w, h = img.size
    out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    a = Image.new("L", out.size, 0); a.paste(img.getchannel("A"), (pad + dx, pad + dy))
    a = a.filter(ImageFilter.GaussianBlur(radio)).point(lambda v: int(v * alpha))
    s = Image.new("RGBA", out.size, (0, 4, 16, 0)); s.putalpha(a)
    out.alpha_composite(s); out.alpha_composite(img, (pad, pad))
    return out, pad

# ------------------------------------------------------------- marca
def wordmark(size=96):
    f = font("InterDisplay-BlackItalic", size)
    a = texto_relleno("FRUTINOTICIAS", f, metal(10, 10), stroke=3, stroke_color=AZUL_O)
    a = texto_relleno("FRUTINOTICIAS", f, metal(a.size[0], a.size[1]), stroke=3, stroke_color=AZUL_O)
    b = texto_relleno("RD", f, rojo_metal(10, 10), stroke=3, stroke_color=(60, 0, 8))
    b = texto_relleno("RD", f, rojo_metal(b.size[0], b.size[1]), stroke=3, stroke_color=(60, 0, 8))
    gap = int(size * 0.06)
    w = a.size[0] + gap + b.size[0]; h = max(a.size[1], b.size[1])
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.alpha_composite(a, (0, h - a.size[1])); im.alpha_composite(b, (a.size[0] + gap, h - b.size[1]))
    # barrido rojo bajo la marca (eco del logotipo del set, sin copiarlo)
    sw = Image.new("RGBA", (w, int(size * 0.2)), (0, 0, 0, 0))
    d = ImageDraw.Draw(sw)
    d.polygon([(int(w * 0.04), sw.size[1] - 2), (int(w * 0.98), 0), (int(w * 0.98), int(size * 0.07)), (int(w * 0.10), sw.size[1] - 1)], fill=ROJO + (255,))
    full = Image.new("RGBA", (w, h + sw.size[1] + 4), (0, 0, 0, 0))
    full.alpha_composite(sw, (0, h + 2)); full.alpha_composite(im, (0, 0))
    g, pad = glow(full, radio=14, color=AZUL_E, fuerza=0.9)
    s, pad2 = sombra(g, dy=5, radio=6, alpha=0.7)
    return s, pad + pad2

def chip(txt, fondo=ROJO, color=BLANCO, size=26, padx=16, pady=8, borde=None, fnt="InterDisplay-ExtraBold"):
    f = font(fnt, size)
    bb = f.getbbox(txt)
    w, h = bb[2] - bb[0] + 2 * padx, int(size * 1.0) + 2 * pady
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if fondo is not None:
        if isinstance(fondo, tuple): d.rounded_rectangle([0, 0, w - 1, h - 1], radius=5, fill=fondo + (255,))
    if borde: d.rounded_rectangle([0, 0, w - 1, h - 1], radius=5, outline=borde + (255,), width=2)
    d.text((padx - bb[0], (h - (bb[3] - bb[1])) // 2 - bb[1]), txt, font=f, fill=color + (255,))
    return im

def placa_3d(w, h, serio=False, oscuro=False):
    """Placa de titular con bisel metálico y profundidad."""
    im = Image.new("RGBA", (w, h + 10), (0, 0, 0, 0))
    # canto (extrusión)
    canto = gradiente_v(w, 14, (4, 12, 30), (0, 0, 0), 255, 255)
    im.alpha_composite(canto, (0, h - 4))
    top = (10, 30, 70) if oscuro else ((18, 58, 128) if not serio else (14, 40, 92))
    bot = (2, 8, 22) if oscuro else (5, 20, 56)
    cara = gradiente_v(w, h, top, bot, 248, 248)
    im.alpha_composite(cara, (0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 2], fill=PLATA + (255,))           # filo plateado
    d.rectangle([0, 3, w, 4], fill=(255, 255, 255, 90))
    d.rectangle([0, h - 3, w, h], fill=(AZUL_E if not oscuro else ROJO) + (255,))
    # reflejo superior suave
    refl = gradiente_v(w, h // 2, (255, 255, 255), (255, 255, 255), 36, 0)
    im.alpha_composite(refl, (0, 5))
    return im

def texto_3d(txt, size, color=BLANCO, extr=4, fnt="InterDisplay-BlackItalic"):
    f = font(fnt, size)
    bb = f.getbbox(txt)
    w, h = bb[2] - bb[0] + 8 + extr, bb[3] - bb[1] + 8 + extr
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i in range(extr, 0, -1):
        d.text((4 - bb[0] + i * 0.6, 4 - bb[1] + i), txt, font=f, fill=(4 + i * 3, 16 + i * 4, 44 + i * 6, 255))
    fill = metal(w, h) if color == "metal" else None
    if fill is not None:
        t = texto_relleno(txt, f, metal(w, h)); im.alpha_composite(t, (4 + bb[0] - f.getbbox(txt)[0] - 2, 2))
    else:
        d.text((4 - bb[0], 4 - bb[1]), txt, font=f, fill=color + (255,))
    return im

# ------------------------------------------------------------- mapa de RD
CIUDADES = {  # lat, lon (coordenadas públicas aproximadas del centro urbano)
    "Santo Domingo": (18.4861, -69.9312),
    "Santiago": (19.4517, -70.6970),
    "Puerto Plata": (19.7934, -70.6884),
    "Punta Cana": (18.5601, -68.3725),
}

class MapaRD:
    def __init__(self, ruta_json, w, h, pad=14):
        rings = json.load(open(ruta_json))["rings"]
        lat0 = 18.9; k = math.cos(math.radians(lat0))
        allp = [(lo * k, -la) for r in rings for lo, la in r]
        xs, ys = zip(*allp)
        sx = (w - 2 * pad) / (max(xs) - min(xs)); sy = (h - 2 * pad) / (max(ys) - min(ys)); s = min(sx, sy)
        ox = pad + ((w - 2 * pad) - s * (max(xs) - min(xs))) / 2 - s * min(xs)
        oy = pad + ((h - 2 * pad) - s * (max(ys) - min(ys))) / 2 - s * min(ys)
        self.proj = lambda lo, la: (ox + s * lo * k, oy + s * -la)
        self.rings = [[self.proj(lo, la) for lo, la in r] for r in rings]
        self.w, self.h = w, h
        self.ciudades = {n: self.proj(lo, la) for n, (la, lo) in CIUDADES.items()}
        # perímetro acumulado del anillo principal (para dibujo progresivo)
        r = self.rings[0]
        self.cum = np.concatenate([[0], np.cumsum([math.dist(r[i], r[i + 1]) for i in range(len(r) - 1)])])

    def relleno(self, escala=4):
        W, H = self.w * escala, self.h * escala
        m = Image.new("L", (W, H), 0); d = ImageDraw.Draw(m)
        for r in self.rings: d.polygon([(x * escala, y * escala) for x, y in r], fill=255)
        m = m.resize((self.w, self.h), Image.LANCZOS)
        g = gradiente_v(self.w, self.h, (40, 120, 230), (10, 40, 120), 255, 255)
        g.putalpha(m.point(lambda v: int(v * 0.55)))
        return g

    def contorno(self, prog, ancho=2, escala=3):
        """Contorno dibujado hasta 'prog' (0..1) con brillo; islas al final."""
        W, H = self.w * escala, self.h * escala
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        r = self.rings[0]; L = self.cum[-1] * clamp(prog)
        n = int(np.searchsorted(self.cum, L))
        pts = [(x * escala, y * escala) for x, y in r[:max(2, n + 1)]]
        for wd, col in ((ancho * 5, AZUL_E + (60,)), (ancho * 3, AZUL_C + (140,)), (ancho, BLANCO + (255,))):
            d.line(pts, fill=col, width=wd * escala // 2 + 1, joint="curve")
        if prog >= 0.98:
            for rr in self.rings[1:]:
                d.line([(x * escala, y * escala) for x, y in rr] + [(rr[0][0] * escala, rr[0][1] * escala)], fill=AZUL_C + (220,), width=ancho * escala // 2 + 1)
        cabeza = pts[-1] if prog < 0.98 else None
        im = im.resize((self.w, self.h), Image.LANCZOS)
        return im, (cabeza[0] / escala, cabeza[1] / escala) if cabeza else None
