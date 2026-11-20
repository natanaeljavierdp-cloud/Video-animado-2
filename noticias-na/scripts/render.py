#!/usr/bin/env python3
"""
Noticias N A — edición del video "Sandy Brito".

Compone gráficos televisivos (lower thirds, cintillo, foto, logotipo) sobre
el video original SIN modificar su animación ni su audio.

Uso:
    python3 scripts/render.py                # versión TV  + versión Reels
    python3 scripts/render.py --solo tv      # sólo la versión TV
    python3 scripts/render.py --solo reels   # sólo la versión Reels/TikTok

Todos los tiempos de la sección TIMING proceden de la transcripción con marcas
de tiempo por palabra (ver transcripcion.json). Cambia un valor aquí y vuelve
a ejecutar para re-sincronizar.
"""
import argparse, json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

SRC_VIDEO = P("videos", "original.mp4")
SRC_PHOTO = P("fotos", "sandy_brito.jpg")
W, H = 1080, 1920

# ---------------------------------------------------------------- paleta
NAVY = (10, 26, 64)
NAVY2 = (18, 46, 108)
BLUE = (30, 110, 235)
RED = (214, 22, 40)
RED2 = (150, 8, 22)
WHITE = (255, 255, 255)
SILVER = (196, 204, 216)
SILVER2 = (232, 236, 242)

# ---------------------------------------------------------------- textos
ID_TEXT = ("NOTICIAS", "N A")
TAG_TEXT = "ÚLTIMA HORA"
HEAD_1 = "SANDY BRITO EN TENDENCIA"
HEAD_2 = "LA FRENTE GANA TERRENO"
TICKER = "HUMOR | La frente de Sandy Brito se roba los titulares | Noticias N A"
NAME = "SANDY BRITO"

# ---------------------------------------------------------------- TIMING (s)
# Transcripción: "Sandy" 1.84 · "Brito" 2.10–2.38 · "frente" 4.02 ·
# "economía." termina 5.72 · "Sandy, tranquilo…" 5.74–7.90
T_BUG_IN = 0.05          # logotipo + indicador HUMOR
T_ID_IN = 0.00           # barra NOTICIAS N A entra desde la izquierda
T_TAG_IN = 0.22          # etiqueta ÚLTIMA HORA
T_HEAD_IN = 0.35         # barra del titular
T_TICK_IN = 0.30         # cintillo
T_PHOTO_IN = 1.76        # foto entra justo al decir "Sandy" (1.84)
T_NAME_IN = 2.02         # rótulo SANDY BRITO al decir "Brito" (2.10)
T_SWAP = 3.94            # titular -> LA FRENTE GANA TERRENO ("frente" 4.02)
T_PHOTO_OUT = 5.72       # foto sale al terminar "economía." (~4 s en pantalla)
T_EXIT = 6.95            # salida del titular
T_STING = 7.12           # marca final Noticias N A
TICKER_SPEED = 185       # px/s
TICKER_PREROLL = 380     # px de texto ya visibles al aparecer el cintillo

FONT_OSW = P("fuentes", "Oswald.ttf")
FONT_MON = P("fuentes", "Montserrat.ttf")


def font(path, size, weight="Bold"):
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


# ---------------------------------------------------------------- utilidades
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, start, dur):
    return clamp((t - start) / dur)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in(x):
    return x ** 3


def ease_io(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def lerp(a, b, x):
    return a + (b - a) * x


def hgrad(w, h, c1, c2):
    a = np.linspace(0, 1, w)[None, :, None]
    arr = np.array(c1)[None, None, :] * (1 - a) + np.array(c2)[None, None, :] * a
    arr = np.repeat(arr, h, axis=0)
    return Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")


def vgrad(w, h, c1, c2):
    a = np.linspace(0, 1, h)[:, None, None]
    arr = np.array(c1)[None, None, :] * (1 - a) + np.array(c2)[None, None, :] * a
    arr = np.repeat(arr, w, axis=1)
    return Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")


def text_img(txt, fnt, fill, track=0, shadow=True):
    """Texto con interletrado y sombra suave, recortado a su caja."""
    asc, desc = fnt.getmetrics()
    widths = [fnt.getlength(c) for c in txt]
    w = int(sum(widths) + track * (len(txt) - 1)) + 8
    h = asc + desc + 8
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 4
    for c, cw in zip(txt, widths):
        d.text((x, 4), c, font=fnt, fill=fill)
        x += cw + track
    bbox = im.getbbox()
    im = im.crop((bbox[0], bbox[1], bbox[2], bbox[3]))
    if shadow:
        pad = 6
        out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
        sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
        a = im.split()[3].point(lambda v: v * 0.45)
        sh.paste((0, 0, 0, 255), (pad + 2, pad + 3), a)
        sh = sh.filter(ImageFilter.GaussianBlur(2.5))
        out.alpha_composite(sh)
        out.alpha_composite(im, (pad, pad))
        return out, pad
    return im, 0


def place_text(layer, txt_img, pad, cx=None, cy=None, x=None):
    """Centra verticalmente (y horizontalmente si cx) un texto en una capa."""
    tw, th = txt_img.size
    if cx is not None:
        x = int(cx - tw / 2)
    else:
        x = int(x - pad)
    y = int(cy - th / 2)
    layer.alpha_composite(txt_img, (x, y))


def with_alpha(img, a):
    if a >= 0.999:
        return img
    im = img.copy()
    im.putalpha(im.split()[3].point(lambda v: int(v * a)))
    return im


def paste(canvas, layer, x, y, alpha=1.0):
    """alpha_composite con recorte para coordenadas negativas/fuera de lienzo."""
    if alpha <= 0.003:
        return
    x, y = int(round(x)), int(round(y))
    lx0, ly0 = max(0, -x), max(0, -y)
    lx1 = min(layer.width, canvas.width - x)
    ly1 = min(layer.height, canvas.height - y)
    if lx1 <= lx0 or ly1 <= ly0:
        return
    part = layer.crop((lx0, ly0, lx1, ly1))
    canvas.alpha_composite(with_alpha(part, alpha), (x + lx0, y + ly0))


def shadow_of(img, blur=14, opacity=0.55, grow=0):
    pad = blur * 3
    sh = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    a = img.split()[3].point(lambda v: int(v * opacity))
    sh.paste((0, 0, 0, 255), (pad, pad), a)
    if grow:
        sh = sh.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    return sh.filter(ImageFilter.GaussianBlur(blur)), pad


def glow_of(img, color, blur=10, strength=1.0):
    pad = blur * 3
    g = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    a = img.split()[3].point(lambda v: int(min(255, v * strength)))
    g.paste(color + (255,), (pad, pad), a)
    return g.filter(ImageFilter.GaussianBlur(blur)), pad


def sweep(img, p, width=0.18, strength=0.55, angle=0.35):
    """Destello de luz diagonal que recorre un elemento (p de 0 a 1)."""
    if p <= 0 or p >= 1:
        return img
    w, h = img.size
    xs = np.arange(w)[None, :] + np.arange(h)[:, None] * angle
    span = w + h * angle
    center = lerp(-width * span, span * (1 + width), p)
    d = np.abs(xs - center) / (width * span * 0.5)
    band = np.clip(1 - d, 0, 1) ** 2 * strength
    a = np.asarray(img.split()[3], dtype=np.float32) / 255.0
    band = (band * a * 255).astype(np.uint8)
    hl = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    hl.putalpha(Image.fromarray(band, "L"))
    out = img.copy()
    out.alpha_composite(hl)
    return out


def clip_w(img, frac, from_left=True):
    """Recorta horizontalmente (efecto wipe)."""
    w = int(img.width * clamp(frac))
    if w <= 0:
        return None
    return img.crop((0, 0, w, img.height)) if from_left else img.crop((img.width - w, 0, img.width, img.height))


# ---------------------------------------------------------------- recursos
def make_logo(h):
    """Logotipo NOTICIAS N A: bloque azul + bloque rojo con filetes plateados."""
    f1 = font(FONT_OSW, int(h * 0.60), "Bold")
    f2 = font(FONT_OSW, int(h * 0.64), "Bold")
    t1, p1 = text_img(ID_TEXT[0], f1, WHITE, track=int(h * 0.05))
    t2, p2 = text_img(ID_TEXT[1], f2, WHITE, track=int(h * 0.08))
    padx = int(h * 0.32)
    w1 = t1.width - 2 * p1 + padx * 2
    w2 = t2.width - 2 * p2 + padx * 2
    slant = int(h * 0.28)
    w = w1 + w2 + slant
    logo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    m1 = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m1).polygon([(0, 0), (w1 + slant, 0), (w1, h), (0, h)], fill=255)
    m2 = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m2).polygon([(w1 + slant, 0), (w, 0), (w, h), (w1, h)], fill=255)
    logo.paste(vgrad(w, h, NAVY2, NAVY), (0, 0), m1)
    logo.paste(vgrad(w, h, (238, 40, 56), RED2), (0, 0), m2)
    d = ImageDraw.Draw(logo)
    lw = max(2, h // 22)
    d.rectangle([0, 0, w, lw - 1], fill=SILVER2)
    d.rectangle([0, h - lw, w, h], fill=SILVER)
    place_text(logo, t1, p1, cx=w1 / 2 + slant * 0.15, cy=h / 2)
    place_text(logo, t2, p2, cx=w1 + slant / 2 + w2 / 2 + slant * 0.15, cy=h / 2)
    return logo


def make_humor_badge(h):
    f = font(FONT_MON, int(h * 0.48), "ExtraBold")
    t, p = text_img("HUMOR · SÁTIRA", f, WHITE, track=3)
    w = t.width - 2 * p + int(h * 1.05)
    b = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=255)
    b.paste(hgrad(w, h, (232, 34, 52), RED2), (0, 0), m)
    ImageDraw.Draw(b).rounded_rectangle([1, 1, w - 2, h - 2], radius=h // 2, outline=(255, 255, 255, 150), width=2)
    # punto "en vivo"
    r = int(h * 0.14)
    cy = h // 2
    ImageDraw.Draw(b).ellipse([int(h * 0.32) - r, cy - r, int(h * 0.32) + r, cy + r], fill=WHITE)
    place_text(b, t, p, x=int(h * 0.62), cy=h / 2)
    return b


def make_tag(h):
    f = font(FONT_OSW, int(h * 0.50), "Bold")
    t, p = text_img(TAG_TEXT, f, WHITE, track=2)
    w = t.width - 2 * p + int(h * 0.55)
    tag = vgrad(w, h, (238, 40, 56), RED2)
    d = ImageDraw.Draw(tag)
    d.rectangle([0, 0, w, 2], fill=(255, 140, 150))
    place_text(tag, t, p, cx=w / 2, cy=h / 2)
    return tag


def make_headline_text(txt, h, max_w):
    size = int(h * 0.60)
    while True:  # ajusta el cuerpo de letra para que nunca se corte
        t, p = text_img(txt, font(FONT_OSW, size, "Bold"), NAVY, track=1, shadow=False)
        if t.width <= max_w or size < 30:
            return t
        size -= 1


def make_head_bar(w, h):
    bar = vgrad(w, h, (252, 253, 255), (206, 214, 226))
    d = ImageDraw.Draw(bar)
    d.rectangle([0, h - 5, w, h], fill=NAVY2)
    d.rectangle([0, 0, w, 1], fill=(255, 255, 255))
    return bar


def make_ticker_bar(w, h):
    bar = vgrad(w, h, NAVY2, NAVY)
    d = ImageDraw.Draw(bar)
    d.rectangle([0, 0, w, 2], fill=BLUE)
    d.rectangle([0, h - 2, w, h], fill=(6, 14, 36))
    return bar


def make_ticker_label(h):
    f = font(FONT_OSW, int(h * 0.56), "Bold")
    t, p = text_img("HUMOR", f, WHITE, track=3)
    w = t.width - 2 * p + int(h * 0.7)
    slant = int(h * 0.3)
    lab = Image.new("RGBA", (w + slant, h), (0, 0, 0, 0))
    m = Image.new("L", lab.size, 0)
    ImageDraw.Draw(m).polygon([(0, 0), (w + slant, 0), (w, h), (0, h)], fill=255)
    lab.paste(vgrad(w + slant, h, (238, 40, 56), RED2), (0, 0), m)
    place_text(lab, t, p, cx=w / 2, cy=h / 2)
    return lab


def make_ticker_strip(h):
    f = font(FONT_MON, int(h * 0.50), "SemiBold")
    seg, p = text_img(TICKER, f, WHITE, track=1)
    gap = int(h * 1.2)
    dot = Image.new("RGBA", (gap, seg.height), (0, 0, 0, 0))
    r = int(h * 0.09)
    ImageDraw.Draw(dot).ellipse([gap // 2 - r, seg.height // 2 - r, gap // 2 + r, seg.height // 2 + r], fill=RED)
    unit = Image.new("RGBA", (seg.width + gap, seg.height), (0, 0, 0, 0))
    unit.alpha_composite(seg)
    unit.alpha_composite(dot, (seg.width, 0))
    return unit


def make_photo_card(inner_w, inner_h, border):
    photo = ImageOps.exif_transpose(Image.open(SRC_PHOTO)).convert("RGB")
    pw, ph = photo.size  # 2252 x 4000
    # Encuadre del rostro (4:5) — sólo recorte y escalado, sin retoque facial.
    cw = int(pw * 0.66)
    ch = int(cw * inner_h / inner_w)
    cx0 = int(pw * 0.62) - cw // 2
    cy0 = int(ph * 0.165)
    photo = photo.crop((cx0, cy0, cx0 + cw, cy0 + ch)).resize((inner_w, inner_h), Image.LANCZOS)
    w, h = inner_w + border * 2, inner_h + border * 2
    # borde degradado azul -> rojo en diagonal
    a = (np.arange(w)[None, :] / w + np.arange(h)[:, None] / h) / 2
    a = np.clip((a - 0.25) / 0.5, 0, 1)[..., None]
    arr = np.array(BLUE)[None, None] * (1 - a) + np.array(RED)[None, None] * a
    card = Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")
    d = ImageDraw.Draw(card)
    d.rectangle([border - 3, border - 3, w - border + 2, h - border + 2], fill=SILVER2)
    card.paste(photo, (border, border))
    # viñeta interior muy suave para integrar la foto
    vg = Image.new("L", (inner_w, inner_h), 0)
    ImageDraw.Draw(vg).rectangle([0, 0, inner_w, inner_h], outline=70, width=3)
    vg = vg.filter(ImageFilter.GaussianBlur(10))
    dark = Image.new("RGBA", (inner_w, inner_h), (0, 0, 0, 0))
    dark.putalpha(vg)
    card.alpha_composite(dark, (border, border))
    d.rectangle([0, 0, w - 1, h - 1], outline=(255, 255, 255, 120), width=1)
    return card


def make_nameplate(w, h):
    f = font(FONT_OSW, int(h * 0.62), "Bold")
    t, p = text_img(NAME, f, WHITE, track=4)
    plate = vgrad(w, h, (236, 38, 54), RED2)
    d = ImageDraw.Draw(plate)
    d.rectangle([0, 0, w, 3], fill=SILVER2)
    d.rectangle([0, h - 6, w, h], fill=NAVY2)
    place_text(plate, t, p, cx=w / 2, cy=h / 2 - 2)
    return plate


# ---------------------------------------------------------------- layout
LAYOUTS = {
    # versión broadcast: grafismo sobre el frente de la mesa
    "tv": dict(lt_y=1430, bug_xy=(40, 70), card_x=678, card_y=400),
    # versión Reels/TikTok: todo dentro de las zonas seguras de la interfaz
    "reels": dict(lt_y=1262, bug_xy=(40, 230), card_x=640, card_y=420),
}


class Graphics:
    def __init__(self, layout):
        L = LAYOUTS[layout]
        self.L = L
        self.logo_bug = make_logo(58)
        self.humor = make_humor_badge(50)
        self.id_logo = make_logo(66)
        self.tag = make_tag(96)
        self.head_w = W - 80
        self.head_bar = make_head_bar(self.head_w - self.tag.width, 96)
        self.head1 = make_headline_text(HEAD_1, 96, self.head_bar.width - 48)
        self.head2 = make_headline_text(HEAD_2, 96, self.head_bar.width - 48)
        self.tick_h = 70
        self.tick_bar = make_ticker_bar(W, self.tick_h)
        self.tick_label = make_ticker_label(self.tick_h)
        self.tick_unit = make_ticker_strip(self.tick_h)
        n = math.ceil((W + TICKER_SPEED * 9) / self.tick_unit.width) + 2
        strip = Image.new("RGBA", (self.tick_unit.width * n, self.tick_unit.height), (0, 0, 0, 0))
        for i in range(n):
            strip.alpha_composite(self.tick_unit, (i * self.tick_unit.width, 0))
        self.tick_strip = strip
        self.card = make_photo_card(344, 430, 12)
        self.card_shadow, self.card_spad = shadow_of(self.card, blur=18, opacity=0.6)
        self.card_glow_b, self.card_gpad = glow_of(self.card, BLUE, blur=14, strength=0.9)
        self.card_glow_r, _ = glow_of(self.card, RED, blur=14, strength=0.9)
        self.plate = make_nameplate(self.card.width, 70)
        self.plate_shadow, self.plate_spad = shadow_of(self.plate, blur=10, opacity=0.5)
        self.sting = make_logo(118)
        self.head_glow_line = Image.new("RGBA", (self.head_w, 4), RED + (255,))
        self.head_glow, self.hg_pad = glow_of(self.head_glow_line, (255, 70, 80), blur=8, strength=1)
        self.tick_glow_line = Image.new("RGBA", (W, 3), BLUE + (255,))
        self.tick_glow, self.tg_pad = glow_of(self.tick_glow_line, (70, 150, 255), blur=8, strength=1)
        self.vignette = self._vignette()

    def _vignette(self):
        y, x = np.mgrid[0:H, 0:W]
        d = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H * 0.45) / (H * 0.62)) ** 2)
        a = (np.clip(d - 0.75, 0, 1) ** 1.6 * 150).astype(np.uint8)
        v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        v.putalpha(Image.fromarray(a, "L"))
        return v

    # ------------------------------------------------------------ fotograma
    def frame(self, t, dur):
        c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        c.alpha_composite(self.vignette)
        L = self.L
        y0 = L["lt_y"]
        pulse = 0.65 + 0.35 * math.sin(t * 2 * math.pi / 2.2)

        # --- bug superior: logotipo + HUMOR (permanente)
        pb = ease_out(prog(t, T_BUG_IN, 0.55))
        bx, by = L["bug_xy"]
        if pb > 0:
            lg = sweep(self.logo_bug, prog(t, 0.55, 0.7))
            sh, sp = shadow_of(lg, blur=8, opacity=0.45)
            paste(c, sh, bx - sp, by - sp + 4 + lerp(-30, 0, pb), pb)
            paste(c, lg, bx, by + lerp(-30, 0, pb), pb)
            ph = ease_out(prog(t, T_BUG_IN + 0.2, 0.5))
            hx = bx + self.logo_bug.width + 14
            hy = by + (self.logo_bug.height - self.humor.height) // 2
            paste(c, self.humor, hx + lerp(-20, 0, ph), hy, ph)

        # --- salida del bloque titular
        pe = ease_in(prog(t, T_EXIT, 0.38))
        exit_dx = -pe * (W + 100)

        # --- línea 1: identidad NOTICIAS N A (entra desde la izquierda)
        pi = ease_out(prog(t, T_ID_IN, 0.55))
        id_y = y0
        if pi > 0 and pe < 1:
            x = lerp(-self.id_logo.width - 60, 40, pi) + exit_dx
            sh, sp = shadow_of(self.id_logo, blur=10, opacity=0.5)
            paste(c, sh, x - sp, id_y - sp + 5)
            paste(c, sweep(self.id_logo, prog(t, 0.9, 0.7)), x, id_y)

        # --- línea 2: ÚLTIMA HORA | titular
        hy = y0 + self.id_logo.height + 8
        pt = ease_out(prog(t, T_TAG_IN, 0.45))
        ph = ease_out(prog(t, T_HEAD_IN, 0.55))
        if pt > 0 and pe < 1:
            # sombra del conjunto
            full = Image.new("RGBA", (self.head_w, 96), (0, 0, 0, 255))
            sh, sp = shadow_of(full, blur=14, opacity=0.5)
            paste(c, sh, 40 - sp + exit_dx, hy - sp + 8, min(pt, 1))
            # resplandor discreto en el borde superior
            paste(c, self.head_glow, 40 - self.hg_pad + exit_dx, hy - 2 - self.hg_pad, 0.55 * pulse * ph)
            # barra blanca/plata con wipe
            bar = self.head_bar.copy()
            # texto del titular (desliza hacia arriba; cambio a la 2ª frase)
            tx = 26
            cy = 96 // 2 - 3
            ps = ease_io(prog(t, T_SWAP, 0.42))
            pin = ease_out(prog(t, T_HEAD_IN + 0.2, 0.5))
            if ps < 1:
                ty = cy - self.head1.height / 2 + lerp(60, 0, pin) - ps * 96
                bar.alpha_composite(with_alpha(self.head1, pin * (1 - ps)), (tx, int(ty)))
            if ps > 0:
                ty = cy - self.head2.height / 2 + (1 - ps) * 96
                bar.alpha_composite(with_alpha(self.head2, ps), (tx, int(ty)))
            d = ImageDraw.Draw(bar)
            d.rectangle([0, 96 - 5, bar.width, 96], fill=NAVY2)
            bar = sweep(bar, prog(t, 1.0, 0.8), strength=0.45)
            bar = sweep(bar, prog(t, T_SWAP + 0.3, 0.8), strength=0.45)
            bw = clip_w(bar, ph)
            if bw is not None:
                paste(c, bw, 40 + self.tag.width + exit_dx, hy)
            tag = clip_w(self.tag, pt)
            if tag is not None:
                paste(c, tag, 40 + exit_dx, hy)

        # --- marca final Noticias N A
        pst = prog(t, T_STING, 0.42)
        if pst > 0:
            e = ease_out(pst)
            s = lerp(0.86, 1.0, e)
            lg = sweep(self.sting, prog(t, T_STING + 0.25, 0.6), strength=0.6)
            lg = lg.resize((int(lg.width * s), int(lg.height * s)), Image.LANCZOS)
            cx = W / 2
            cyy = y0 + (self.id_logo.height + 8 + 96) / 2
            gb, gp = glow_of(lg, (60, 130, 255), blur=16, strength=0.8)
            paste(c, gb, cx - lg.width / 2 - gp, cyy - lg.height / 2 - gp, 0.5 * e * pulse)
            sh, sp = shadow_of(lg, blur=14, opacity=0.55)
            paste(c, sh, cx - lg.width / 2 - sp, cyy - lg.height / 2 - sp + 8, e)
            paste(c, lg, cx - lg.width / 2, cyy - lg.height / 2, e)

        # --- línea 3: cintillo
        ty0 = hy + 96 + 8
        pk = ease_out(prog(t, T_TICK_IN, 0.5))
        if pk > 0:
            bar = self.tick_bar.copy()
            off = TICKER_PREROLL + max(0.0, t - T_TICK_IN) * TICKER_SPEED
            sx = W - off
            strip_y = (self.tick_h - self.tick_strip.height) // 2
            if sx < 0:
                bar.alpha_composite(self.tick_strip.crop((int(-sx), 0, int(-sx) + W, self.tick_strip.height)), (0, strip_y))
            else:
                part = self.tick_strip.crop((0, 0, max(1, W - int(sx)), self.tick_strip.height))
                bar.alpha_composite(part, (int(sx), strip_y))
            bar.alpha_composite(self.tick_label, (0, 0))
            paste(c, self.tick_glow, -self.tg_pad, ty0 - 1 - self.tg_pad, 0.6 * pulse * pk)
            bw = clip_w(bar, pk)
            if bw is not None:
                paste(c, bw, 0, ty0)

        # --- fotografía de Sandy Brito
        pin = ease_out(prog(t, T_PHOTO_IN, 0.48))
        pout = ease_in(prog(t, T_PHOTO_OUT, 0.45))
        if pin > 0 and pout < 1:
            a = min(pin, 1 - pout)
            dx = lerp(W - L["card_x"] + 40, 0, pin) + pout * (W - L["card_x"] + 40)
            s = lerp(0.92, 1.0, pin)
            card = sweep(self.card, prog(t, T_PHOTO_IN + 0.4, 0.75), strength=0.4)
            if s < 0.999:
                card = card.resize((int(card.width * s), int(card.height * s)), Image.LANCZOS)
            x = L["card_x"] + dx + (self.card.width - card.width) / 2
            y = L["card_y"] + (self.card.height - card.height) / 2
            sp = self.card_spad
            paste(c, self.card_shadow, x - sp + 6, y - sp + 12, a)
            gp = self.card_gpad
            g = 0.35 + 0.25 * pulse
            paste(c, self.card_glow_b, x - gp - 4, y - gp - 4, a * g)
            paste(c, self.card_glow_r, x - gp + 4, y - gp + 4, a * g)
            paste(c, card, x, y, a)
            # rótulo con el nombre
            pn = ease_out(prog(t, T_NAME_IN, 0.4))
            pno = ease_in(prog(t, T_PHOTO_OUT - 0.08, 0.3))
            if pn > 0:
                plate = clip_w(sweep(self.plate, prog(t, T_NAME_IN + 0.35, 0.7)), pn * (1 - pno))
                if plate is not None:
                    py = L["card_y"] + self.card.height - 8
                    px = L["card_x"] + dx
                    paste(c, self.plate_shadow, px - self.plate_spad, py - self.plate_spad + 6, a * pn)
                    paste(c, plate, px, py, a)
        return c


# ---------------------------------------------------------------- audio (SFX sutiles)
def synth_sfx(path, dur, sr=48000):
    n = int(dur * sr)
    out = np.zeros((n, 2), np.float32)
    rng = np.random.default_rng(7)

    def whoosh(t0, length=0.42, gain=0.05, pan=0.0):
        m = int(length * sr)
        noise = rng.standard_normal(m).astype(np.float32)
        # filtro paso-bajo con corte variable (barrido)
        cut = np.linspace(0.04, 0.35, m) * np.sin(np.linspace(0, np.pi, m)) + 0.02
        y = np.zeros(m, np.float32)
        acc = 0.0
        for i in range(m):
            acc += cut[i] * (noise[i] - acc)
            y[i] = acc
        y -= np.convolve(y, np.ones(64) / 64, mode="same")  # quita graves
        env = np.sin(np.linspace(0, np.pi, m)) ** 2
        y = y * env
        y = y / (np.abs(y).max() + 1e-9) * gain
        i0 = int(t0 * sr)
        i1 = min(n, i0 + m)
        out[i0:i1, 0] += y[: i1 - i0] * (1 - pan)
        out[i0:i1, 1] += y[: i1 - i0] * (1 + pan)

    def chime(t0, gain=0.035):
        m = int(0.9 * sr)
        tt = np.arange(m) / sr
        y = (np.sin(2 * np.pi * 1318.5 * tt) * 0.6 + np.sin(2 * np.pi * 1975.5 * tt) * 0.4)
        y *= np.exp(-tt * 5.5) * np.minimum(1, tt / 0.004)
        i0 = int(t0 * sr)
        i1 = min(n, i0 + m)
        out[i0:i1, :] += (y[: i1 - i0] * gain)[:, None]

    whoosh(0.02, 0.5, 0.05, -0.4)          # entrada de la barra
    whoosh(T_PHOTO_IN - 0.06, 0.45, 0.045, 0.5)   # entrada de la foto
    whoosh(T_SWAP - 0.02, 0.38, 0.03, 0.0)        # cambio de titular
    whoosh(T_PHOTO_OUT, 0.42, 0.035, 0.5)         # salida de la foto
    whoosh(T_EXIT, 0.4, 0.035, -0.4)              # salida del titular
    chime(T_STING + 0.05)                         # marca final
    pcm = (np.clip(out, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- render
def probe():
    j = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", SRC_VIDEO]))
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    num, den = map(int, v["r_frame_rate"].split("/"))
    return num / den, v["r_frame_rate"], float(j["format"]["duration"]), int(v.get("nb_frames", 0))


def render(layout, out_path, overlay_path=None):
    fps, fps_str, dur, nb = probe()
    g = Graphics(layout)
    sfx = P("graficos", "sfx_transiciones.wav")
    synth_sfx(sfx, dur + 0.2)

    dec = subprocess.Popen([
        "ffmpeg", "-v", "error", "-i", SRC_VIDEO,
        "-vf", f"scale={W}:{H}:flags=lanczos,unsharp=5:5:0.45:5:5:0.0,format=rgb24",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", fps_str, "-i", "-",
        "-i", SRC_VIDEO, "-i", sfx,
        "-filter_complex",
        "[1:a]aresample=48000[v];[2:a]aresample=48000[s];"
        "[v][s]amix=inputs=2:normalize=0:duration=first[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-level", "4.1",
        "-pix_fmt", "yuv420p", "-vf", "scale=out_color_matrix=bt709:out_range=tv",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-g", str(int(round(fps))), "-r", fps_str,
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", "-shortest", out_path], stdin=subprocess.PIPE)
    ovl = None
    if overlay_path:
        ovl = subprocess.Popen([
            "ffmpeg", "-v", "error", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-framerate", fps_str, "-i", "-",
            "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "30",
            "-row-mt", "1", "-deadline", "good", "-cpu-used", "4", overlay_path], stdin=subprocess.PIPE)

    fsize = W * H * 3
    i = 0
    stills = {1.0: "a_titular", 2.6: "b_foto_sandy", 4.6: "c_titular_frente", 7.7: "d_marca_final"}
    while True:
        buf = dec.stdout.read(fsize)
        if len(buf) < fsize:
            break
        t = i / fps
        base = Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, 1).convert("RGBA")
        over = g.frame(t, dur)
        base.alpha_composite(over)
        enc.stdin.write(base.convert("RGB").tobytes())
        if ovl:
            ovl.stdin.write(over.tobytes())
        for st, name in stills.items():
            if abs(t - st) < 0.5 / fps:
                base.convert("RGB").save(P("exportaciones", "previews", f"{layout}_{name}.jpg"), quality=90)
        i += 1
        if i % 24 == 0:
            print(f"  [{layout}] {i} fotogramas", file=sys.stderr)
    dec.wait()
    enc.stdin.close()
    enc.wait()
    if ovl:
        ovl.stdin.close()
        ovl.wait()
    print(f"OK {out_path} ({i} fotogramas)")
    return g


def export_assets(g):
    d = P("graficos")
    g.id_logo.save(os.path.join(d, "logo_noticias_na.png"))
    g.sting.save(os.path.join(d, "logo_noticias_na_grande.png"))
    g.humor.save(os.path.join(d, "indicador_humor.png"))
    g.tag.save(os.path.join(d, "etiqueta_ultima_hora.png"))
    g.tick_label.save(os.path.join(d, "cintillo_etiqueta_humor.png"))
    g.tick_unit.save(os.path.join(d, "cintillo_texto.png"))
    g.card.save(os.path.join(d, "recuadro_foto_sandy_brito.png"))
    g.plate.save(os.path.join(d, "rotulo_sandy_brito.png"))
    for name, txt in (("titular_1.png", g.head1), ("titular_2.png", g.head2)):
        bar = g.head_bar.copy()
        bar.alpha_composite(txt, (26, int(96 / 2 - 3 - txt.height / 2)))
        full = Image.new("RGBA", (g.tag.width + bar.width, 96))
        full.alpha_composite(g.tag)
        full.alpha_composite(bar, (g.tag.width, 0))
        full.save(os.path.join(d, name))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", choices=["tv", "reels"])
    ap.add_argument("--sin-overlay", action="store_true")
    a = ap.parse_args()
    os.makedirs(P("exportaciones", "previews"), exist_ok=True)
    if a.solo in (None, "tv"):
        g = render("tv", P("exportaciones", "Noticias_NA_Sandy_Brito_Final.mp4"),
                   None if a.sin_overlay else P("graficos", "overlay_graficos_tv_alpha.webm"))
        export_assets(g)
    if a.solo in (None, "reels"):
        render("reels", P("exportaciones", "Noticias_NA_Sandy_Brito_Reels_TikTok.mp4"))
