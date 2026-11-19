"""Capital Curioso — "Mismo juego, ¿mismo precio?" (GTA 6 en Latinoamérica)
Vertical 1080x1920 @30fps. Renders frames with Pillow and pipes them to ffmpeg.

Usage: python3 render.py <assets_dir> <out_dir> [start_s end_s]
assets_dir must contain: img/*.jpg, fonts/*.ttf, words.json, countries.geojson
"""
import json, math, os, sys, subprocess, random
from functools import lru_cache
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops

A = sys.argv[1]
OUT = sys.argv[2]
W, H, FPS = 1080, 1920, 30
END_MAIN = 63.55          # narration ends -> brand outro clip starts

NAVY = (10, 40, 90)
NAVY_D = (5, 20, 48)
NAVY_L = (36, 78, 150)
RED = (254, 74, 85)
WHITE = (255, 255, 255)
GREY = (176, 190, 214)

def F(name, size): return _font(name, size)
@lru_cache(None)
def _font(name, size):
    if name == "emoji":
        return ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)
    return ImageFont.truetype(f"{A}/fonts/{name}.ttf", size)

# ---------------------------------------------------------------- easing
def cl(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, t0, d): return cl((t - t0) / d)
def eo(x): return 1 - (1 - x) ** 3
def eio(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def eback(x, s=1.7):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, x): return a + (b - a) * x
def mix(c1, c2, x): return tuple(int(lerp(a, b, x)) for a, b in zip(c1, c2))

# ---------------------------------------------------------------- images
IMG = {
    "ctrl": "f4e70a91", "gamers": "dbebabcf", "headset": "ed439307", "redgamer": "1a7edcb2",
    "phones": "90c90b4a", "cover": "2dbeec4c", "miami": "5c56b047", "phoneguy": "9208a1ad",
    "trader": "ba0c37eb", "tired": "8e12a858", "worker": "ff7ed939", "money": "9040e09a",
    "ps": "d0d5b599",
}

@lru_cache(None)
def raw(key):
    im = ImageOps.exif_transpose(Image.open(f"{A}/img/{IMG[key]}-image.jpg")).convert("RGB")
    return im

@lru_cache(None)
def cover(key, scale=1.18, fx=0.5, fy=0.5, tint=0.0, blur=0, gray=False):
    """Image cover-cropped to (W*scale, H*scale) — headroom for Ken Burns."""
    im = raw(key)
    tw, th = int(W * scale), int(H * scale)
    r = max(tw / im.width, th / im.height)
    im = im.resize((math.ceil(im.width * r), math.ceil(im.height * r)), Image.LANCZOS)
    x = int((im.width - tw) * fx); y = int((im.height - th) * fy)
    im = im.crop((x, y, x + tw, y + th))
    if gray: im = ImageOps.grayscale(im).convert("RGB")
    if blur: im = im.filter(ImageFilter.GaussianBlur(blur))
    if tint: im = Image.blend(im, Image.new("RGB", im.size, NAVY_D), tint)
    return im

def kenburns(key, x, z0=1.0, z1=1.12, px=0.0, py=0.0, **kw):
    big = cover(key, **kw)
    s = big.width / W
    z = lerp(z0, z1, x)
    cw, ch = W * s / z, H * s / z
    cx = big.width / 2 + px * (big.width - cw) / 2 * (x * 2 - 1)
    cy = big.height / 2 + py * (big.height - ch) / 2 * (x * 2 - 1)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return big.resize((W, H), Image.BILINEAR, box=box).convert("RGBA")

@lru_cache(None)
def grad_overlay(top=0.75, mid=0.35, bot=0.9, col=NAVY_D):
    """Vertical navy gradient for legibility (dark at top for subtitles & bottom)."""
    g = Image.new("L", (1, H))
    for y in range(H):
        v = y / H
        a = lerp(top, mid, v / 0.35) if v < .35 else (mid if v < .6 else lerp(mid, bot, (v - .6) / .4))
        g.putpixel((0, y), int(255 * a))
    g = g.resize((W, H))
    o = Image.new("RGBA", (W, H), col + (0,)); o.putalpha(g)
    return o

@lru_cache(None)
def vignette():
    m = Image.new("L", (W // 4, H // 4), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((-W // 8, -H // 10, W // 4 + W // 8, H // 4 + H // 10), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(60)).resize((W, H))
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    o.putalpha(ImageOps.invert(m).point(lambda v: int(v * .55)))
    return o

@lru_cache(None)
def grain(i):
    rnd = random.Random(i)
    n = Image.effect_noise((W // 2, H // 2), 40).resize((W, H), Image.NEAREST)
    o = Image.new("RGBA", (W, H), (128, 128, 128, 0))
    o.putalpha(n.point(lambda v: int(abs(v - 128) * .18)))
    return o

# ---------------------------------------------------------------- text
@lru_cache(4096)
def txt(text, font, size, fill=WHITE, stroke=0, sfill=(0, 0, 0), shadow=10, track=0):
    f = F(font, size)
    if track:
        ws = [f.getbbox(c)[2] for c in text]
        tw = sum(ws) + track * (len(text) - 1)
    else:
        tw = int(f.getlength(text))
    asc, desc = f.getmetrics()
    pad = stroke + shadow * 2 + 8
    im = Image.new("RGBA", (tw + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    def draw(dd, col, sw, scol):
        if track:
            x = pad
            for c, cw in zip(text, ws):
                dd.text((x, pad), c, font=f, fill=col, stroke_width=sw, stroke_fill=scol); x += cw + track
        else:
            dd.text((pad, pad), text, font=f, fill=col, stroke_width=sw, stroke_fill=scol)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        draw(ImageDraw.Draw(sh), (0, 0, 0, 200), stroke + 2, (0, 0, 0, 200))
        sh = sh.filter(ImageFilter.GaussianBlur(shadow))
        im = Image.alpha_composite(im, ImageChops.offset(sh, 0, shadow // 2))
        d = ImageDraw.Draw(im)
    draw(d, fill, stroke, sfill)
    return im

@lru_cache(64)
def emoji(ch, size):
    f = F("emoji", 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    r = size / im.height
    return im.resize((int(im.width * r), size), Image.LANCZOS)

def put(canvas, im, cx, cy, scale=1.0, alpha=1.0, rot=0.0, anchor="c"):
    if alpha <= 0.003 or scale <= 0.01: return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if rot:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy(); im.putalpha(a)
    if anchor == "c": x, y = cx - im.width // 2, cy - im.height // 2
    elif anchor == "l": x, y = cx, cy - im.height // 2
    else: x, y = cx - im.width, cy - im.height // 2
    canvas.alpha_composite(im, (int(x), int(y))) if 0 <= x and 0 <= y and x + im.width <= W and y + im.height <= H \
        else canvas.paste(im, (int(x), int(y)), im)

def rrect(size, r, fill, outline=None, ow=0):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=fill, outline=outline, width=ow)
    return im

@lru_cache(None)
def glow_box(w, h, r, col, blur=26, alpha=200):
    pad = blur * 3
    im = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=col + (alpha,))
    return im.filter(ImageFilter.GaussianBlur(blur))

@lru_cache(None)
def card(w, h, r=28, fill=NAVY + (235,), outline=(255, 255, 255, 40), ow=2):
    sh = glow_box(w, h, r, (0, 0, 0), 30, 170)
    c = Image.new("RGBA", sh.size, (0, 0, 0, 0))
    c.alpha_composite(sh, (0, 16))
    c.alpha_composite(rrect((w, h), r, fill, outline, ow), ((sh.width - w) // 2, (sh.height - h) // 2))
    return c

# ---------------------------------------------------------------- flags
@lru_cache(None)
def flag(code, w=120, h=80):
    S = 4; fw, fh = w * S, h * S
    im = Image.new("RGB", (fw, fh), WHITE); d = ImageDraw.Draw(im)
    def star(cx, cy, r, col):
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5; rr = r if i % 2 == 0 else r * .4
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=col)
    if code == "CL":
        d.rectangle((0, fh / 2, fw, fh), fill=(213, 43, 30))
        d.rectangle((0, 0, fh / 2, fh / 2), fill=(0, 57, 166)); star(fh / 4, fh / 4, fh * .15, WHITE)
    elif code == "MX":
        d.rectangle((0, 0, fw / 3, fh), fill=(0, 104, 71)); d.rectangle((fw * 2 / 3, 0, fw, fh), fill=(206, 17, 38))
        d.ellipse((fw / 2 - fh * .14, fh / 2 - fh * .14, fw / 2 + fh * .14, fh / 2 + fh * .14), fill=(140, 90, 40))
        d.ellipse((fw / 2 - fh * .07, fh / 2 + fh * .02, fw / 2 + fh * .07, fh / 2 + fh * .16), fill=(0, 104, 71))
    elif code == "DO":
        cw = fh * .16
        d.rectangle((0, 0, fw / 2, fh / 2), fill=(0, 45, 98)); d.rectangle((fw / 2, 0, fw, fh / 2), fill=(206, 17, 38))
        d.rectangle((0, fh / 2, fw / 2, fh), fill=(206, 17, 38)); d.rectangle((fw / 2, fh / 2, fw, fh), fill=(0, 45, 98))
        d.rectangle((fw / 2 - cw / 2, 0, fw / 2 + cw / 2, fh), fill=WHITE); d.rectangle((0, fh / 2 - cw / 2, fw, fh / 2 + cw / 2), fill=WHITE)
        d.rectangle((fw / 2 - cw * .55, fh / 2 - cw * .65, fw / 2 + cw * .55, fh / 2 + cw * .65), fill=(30, 110, 60))
        d.rectangle((fw / 2 - cw * .3, fh / 2 - cw * .4, fw / 2 + cw * .3, fh / 2 + cw * .4), fill=WHITE)
    elif code == "CO":
        d.rectangle((0, 0, fw, fh / 2), fill=(252, 209, 22)); d.rectangle((0, fh / 2, fw, fh * .75), fill=(0, 56, 147))
        d.rectangle((0, fh * .75, fw, fh), fill=(206, 17, 38))
    elif code == "PE":
        d.rectangle((0, 0, fw / 3, fh), fill=(217, 16, 35)); d.rectangle((fw * 2 / 3, 0, fw, fh), fill=(217, 16, 35))
    elif code == "AR":
        d.rectangle((0, 0, fw, fh / 3), fill=(116, 172, 223)); d.rectangle((0, fh * 2 / 3, fw, fh), fill=(116, 172, 223))
        r = fh * .1
        for i in range(16):
            a = i * math.pi / 8
            d.line((fw / 2, fh / 2, fw / 2 + r * 1.6 * math.cos(a), fh / 2 + r * 1.6 * math.sin(a)), fill=(246, 180, 14), width=S * 2)
        d.ellipse((fw / 2 - r, fh / 2 - r, fw / 2 + r, fh / 2 + r), fill=(246, 180, 14))
    elif code == "US":
        for i in range(13):
            if i % 2 == 0: d.rectangle((0, fh * i / 13, fw, fh * (i + 1) / 13), fill=(178, 34, 52))
        d.rectangle((0, 0, fw * .4, fh * 7 / 13), fill=(60, 59, 110))
        for r_ in range(9):
            n = 6 if r_ % 2 == 0 else 5
            for c in range(n):
                x = fw * .4 * ((c + (0.5 if r_ % 2 == 0 else 1.0)) / 6.0) if n == 6 else fw * .4 * ((c + 1) / 6.0)
                y = fh * 7 / 13 * (r_ + 1) / 10
                d.ellipse((x - S * w / 120 * 3, y - S * w / 120 * 3, x + S * w / 120 * 3, y + S * w / 120 * 3), fill=WHITE)
    im = im.resize((w, h), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), max(4, h // 9), fill=255)
    im.putalpha(m)
    out = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((20, 26, 20 + w, 26 + h), 8, fill=(0, 0, 0, 160))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    out.alpha_composite(im, (20, 20))
    ImageDraw.Draw(out).rounded_rectangle((20, 20, 20 + w - 1, 20 + h - 1), max(4, h // 9), outline=(255, 255, 255, 90), width=2)
    return out

# ---------------------------------------------------------------- subtitles (word by word, top)
WORDS = json.load(open(f"{A}/words.json"))
def _clean(w):
    w = w.strip().upper().rstrip(",.")
    return w
CHUNKS = []
cur = []
for i, (w, s, e) in enumerate(WORDS):
    if cur and (s - cur[-1][2] > 0.32 or len(cur) >= 3 or cur[-1][0][-1] in ",.?"):
        CHUNKS.append(cur); cur = []
    cur.append((w, s, e))
CHUNKS.append(cur)
for i, c in enumerate(CHUNKS):
    nxt = CHUNKS[i + 1][0][1] if i + 1 < len(CHUNKS) else c[-1][2] + 0.5
    c_end = min(nxt, c[-1][2] + 0.6)
    CHUNKS[i] = (c[0][1], c_end, [(_clean(w), s) for w, s, _ in c])

def subtitles(cv, t):
    if t >= END_MAIN: return
    ch = next((c for c in CHUNKS if c[0] - 0.02 <= t < c[1]), None)
    if not ch: return
    t0, t1, ws = ch
    size = 74
    imgs = []
    for w, s in ws:
        on = t >= s
        active = on and (ws.index((w, s)) == len(ws) - 1 or t < ws[ws.index((w, s)) + 1][1])
        col = RED if active else WHITE
        im = txt(w, "Poppins-Black", size, col, 7, (0, 0, 0), 8)
        imgs.append((im, on, s, active))
    gap = -14
    total = sum(i.width for i, *_ in imgs) + gap * (len(imgs) - 1)
    lines = [imgs]
    if total > W - 80:
        k = max(1, len(imgs) - 1); lines = [imgs[:k], imgs[k:]]
    y = 250 if len(lines) == 1 else 205
    for line in lines:
        lw = sum(i.width for i, *_ in line) + gap * (len(line) - 1)
        x = (W - lw) // 2
        for im, on, s, active in line:
            if on:
                p = prog(t, s, 0.14)
                sc = lerp(0.6, 1.0, eback(p)) * (1.06 if active else 1.0)
                put(cv, im, x + im.width // 2, y, sc, cl(p * 2))
            else:
                put(cv, im, x + im.width // 2, y, 1.0, 0.25)
            x += im.width + gap
        y += 92

# ---------------------------------------------------------------- shared bits
def bg_grade(cv, t, top=.78, mid=.3, bot=.88):
    cv.alpha_composite(grad_overlay(top, mid, bot))

@lru_cache(None)
def logo_small():
    s = 40
    im = Image.new("RGBA", (s * 4, s * 4), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((12, 12, 112, 112), outline=WHITE, width=14)
    d.line((100, 100, 140, 140), fill=RED, width=18)
    d.text((62, 64), "?", font=F("Poppins-Black", 70), fill=RED, anchor="mm")
    im = im.resize((s, s), Image.LANCZOS)
    t = txt("@capitalcuriosoo", "Poppins-Bold", 30, WHITE, 0, shadow=6)
    o = Image.new("RGBA", (s + 10 + t.width, max(s, t.height)), (0, 0, 0, 0))
    o.alpha_composite(im, (0, (o.height - s) // 2)); o.alpha_composite(t, (s - 4, (o.height - t.height) // 2))
    return o

def watermark(cv, t):
    put(cv, logo_small(), W // 2, 1745, 1.0, 0.85)

def transition(cv, t, t0):
    """Quick red/white light-sweep at a scene cut."""
    x = (t - t0) / 0.32
    if not (-0.5 < x < 1.0): return
    if x < 0:
        a = cl(1 + x * 2); ov = Image.new("RGBA", (W, H), WHITE + (int(110 * (1 - a) ** 3 * 0),))
        return
    a = (1 - x) ** 2
    cv.alpha_composite(Image.new("RGBA", (W, H), WHITE + (int(170 * a),)))
    bx = int(lerp(-300, W + 300, eo(x)))
    band = Image.new("RGBA", (220, H), RED + (int(200 * (1 - x)),))
    cv.paste(band, (bx - 110, 0), band)

# ================================================================= SCENES
def s_hook(cv, t):
    x = t / 5.7
    cv.alpha_composite(kenburns("ctrl", x, 1.0, 1.22, 0.0, 0.25, scale=1.15, fy=0.35))
    bg_grade(cv, t, .8, .25, .92)
    p1, p2 = prog(t, 0.35, 0.35), prog(t, 2.9, 0.35)
    l1 = txt("MISMO JUEGO…", "Anton-Regular", 150, WHITE, 0, shadow=18)
    l2 = txt("¿MISMO PRECIO?", "Anton-Regular", 168, RED, 0, shadow=18)
    shake = math.sin(t * 60) * 6 * (1 - prog(t, 2.9, 0.5)) if t > 2.9 else 0
    put(cv, l1, W // 2, 1130, lerp(1.6, 1.0, eo(p1)), p1)
    put(cv, l2, W // 2 + shake, 1300, lerp(1.8, 1.0, eo(p2)), p2)
    # red underline grows
    if t > 3.2:
        w = int(820 * eo(prog(t, 3.2, 0.5)))
        cv.alpha_composite(rrect((max(w, 2), 14), 7, RED + (255,)), ((W - w) // 2, 1405))

def s_price(cv, t):
    lt = t - 5.7
    if t < 8.4:
        cv.alpha_composite(kenburns("money", lt / 2.7, 1.05, 1.15, 0.3, 0, scale=1.2, tint=.55, blur=6))
        bg_grade(cv, t, .8, .25, .85)
        art = cover_art()
        p = prog(t, 5.75, 0.5)
        put(cv, art, W // 2, int(lerp(1150, 930, eo(p))), lerp(.8, 1.0, eo(p)) * (1 + .03 * lt), p, rot=lerp(-6, -2, eo(p)))
        tag = price_tag()
        pt = prog(t, 6.45, 0.55)
        sw = math.sin((t - 6.45) * 7) * 10 * math.exp(-(t - 6.45) * 2.2) if t > 6.45 else 0
        put(cv, tag, int(lerp(W + 400, W // 2 + 40, eback(pt))), 1360, 1.0 + 0.08 * math.exp(-max(0, t - 7.0) * 8) * (t > 7.0), cl(pt * 3), rot=sw + 4)
    else:
        lt = t - 8.4
        cv.alpha_composite(kenburns("worker", lt / 4.6, 1.05, 1.18, 0.2, 0, scale=1.2, fx=.45, tint=.62, gray=True))
        bg_grade(cv, t, .82, .35, .9)
        p = prog(t, 8.45, 0.45)
        put(cv, flag("US", 300, 158), W // 2, int(lerp(420, 500, eo(p))), lerp(.6, 1, eback(p)), p)
        put(cv, txt("EE. UU.", "Poppins-ExtraBold", 46, WHITE, shadow=8, track=4), W // 2, 625, 1, p)
        clock(cv, t, W // 2, 990, 250)
        c0, c1 = 9.1, 11.26
        v = 11 * eio(prog(t, c0, c1 - c0))
        n = txt(f"{int(round(v))} HORAS", "Anton-Regular", 150, RED if t >= c1 else WHITE, 0, shadow=16)
        put(cv, n, W // 2, 1375, 1 + .12 * math.exp(-max(0, t - c1) * 6) * (t >= c1), prog(t, 8.9, .3))
        p2 = prog(t, 9.0, .4)
        put(cv, txt("de salario mínimo", "Poppins-Bold", 60, WHITE, shadow=8), W // 2, 1490, 1, p2)
        put(cv, txt("($7.25/h · edición estándar $79.99)", "Poppins-Medium", 34, GREY, shadow=6), W // 2, 1560, 1, prog(t, 11.6, .4))

@lru_cache(None)
def cover_art():
    im = raw("cover").crop((150, 395, 930, 1257)).resize((560, 619), Image.LANCZOS).convert("RGBA")
    o = Image.new("RGBA", (im.width + 24, im.height + 24), WHITE + (255,))
    o.alpha_composite(im, (12, 12))
    sh = Image.new("RGBA", (o.width + 120, o.height + 120), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((60, 75, 60 + o.width, 75 + o.height), fill=(0, 0, 0, 190))
    sh = sh.filter(ImageFilter.GaussianBlur(24)); sh.alpha_composite(o, (60, 60))
    return sh

@lru_cache(None)
def price_tag():
    w, h = 800, 210
    im = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(40 + 70, 40), (40 + w, 40), (40 + w, 40 + h), (40 + 70, 40 + h), (40, 40 + h / 2)]
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).polygon([(x, y + 12) for x, y in pts], fill=(0, 0, 0, 170))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(im)
    d.polygon(pts, fill=RED)
    d.ellipse((40 + 50, 40 + h / 2 - 16, 40 + 82, 40 + h / 2 + 16), fill=NAVY_D)
    d.line((40 + 120, 52, 40 + 120, 28 + h), fill=(255, 255, 255, 120), width=3)
    t1 = txt("GTA 6", "Anton-Regular", 80, WHITE, 0, shadow=0)
    t2 = txt("= $79.99", "Anton-Regular", 112, WHITE, 0, shadow=0)
    im.alpha_composite(t1, (40 + 140, 40 + h // 2 - t1.height // 2 + 6))
    im.alpha_composite(t2, (40 + 140 + t1.width - 4, 40 + h // 2 - t2.height // 2 + 4))
    return im

def clock(cv, t, cx, cy, r):
    p = prog(t, 8.6, .45)
    if p <= 0: return
    im = clock_face(r)
    lay = im.copy(); d = ImageDraw.Draw(lay); c = lay.width // 2
    spin = eio(prog(t, 9.1, 2.16))
    hours = 11 * spin
    am = hours * 2 * math.pi; ah = hours / 12 * 2 * math.pi
    # elapsed sector
    if spin > 0:
        d.pieslice((c - r + 30, c - r + 30, c + r - 30, c + r - 30), -90, -90 + 360 * hours / 12, fill=RED + (90,))
    d.line((c, c, c + (r * .48) * math.sin(ah), c - (r * .48) * math.cos(ah)), fill=WHITE, width=16)
    d.line((c, c, c + (r * .74) * math.sin(am), c - (r * .74) * math.cos(am)), fill=RED, width=9)
    d.ellipse((c - 16, c - 16, c + 16, c + 16), fill=RED)
    put(cv, lay, cx, cy, lerp(.5, 1, eback(p)), p)

@lru_cache(None)
def clock_face(r):
    s = 2 * r + 120; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); c = s // 2
    g = glow_box(2 * r, 2 * r, r, RED, 30, 90); im.alpha_composite(g, (c - g.width // 2, c - g.height // 2))
    d = ImageDraw.Draw(im)
    d.ellipse((c - r, c - r, c + r, c + r), fill=NAVY + (240,), outline=WHITE, width=12)
    for i in range(60):
        a = i / 60 * 2 * math.pi; l = 30 if i % 5 == 0 else 12; wd = 7 if i % 5 == 0 else 3
        d.line((c + (r - 22) * math.sin(a), c - (r - 22) * math.cos(a), c + (r - 22 - l) * math.sin(a), c - (r - 22 - l) * math.cos(a)), fill=WHITE, width=wd)
    return im

# ---------------- ranking
RANK = [  # code, name, value, label, t_start
    ("CL", "Chile", 4.0, "4 días", 15.10),
    ("MX", "México", 5.0, "~5 días", 17.64),
    ("DO", "Rep. Dominicana", 5.0, "5 días", 19.56),
    ("CO", "Colombia", 6.0, "~6 días", 24.98),
    ("PE", "Perú", 7.0, "~7 días", 26.40),
    ("AR", "Argentina", 8.5, "8.5 días", 28.72),
]
GROW = 0.95
BAR_X, BAR_MAX, Y0, ROW = 205, 600, 640, 152

def s_rank(cv, t):
    lt = t - 13.0
    arg_on = t > 29.6
    cv.alpha_composite(kenburns("tired" if t < 28.5 else "trader", prog(t, 13 if t < 28.5 else 28.5, 16), 1.05, 1.15, 0, .2, scale=1.15, tint=.86, blur=10))
    if t > 28.5 and t < 28.9:
        cv.alpha_composite(Image.new("RGBA", (W, H), NAVY_D + (int(255 * (1 - prog(t, 28.5, .4))),)))
    bg_grade(cv, t, .8, .3, .85)
    # title
    p = prog(t, 13.1, .5)
    put(cv, txt("¿CUÁNTOS DÍAS DE TRABAJO", "Anton-Regular", 76, WHITE, shadow=12), W // 2, int(lerp(470, 450, eo(p))), 1, p)
    t2 = txt("CUESTA GTA 6?", "Anton-Regular", 76, RED, shadow=12)
    put(cv, t2, W // 2, int(lerp(560, 540, eo(p))), 1, prog(t, 13.3, .5))
    for i, (code, name, val, lab, ts) in enumerate(RANK):
        y = Y0 + 50 + i * ROW
        pr = prog(t, ts - 0.25, 0.35)
        if pr <= 0: continue
        shake = 0
        is_ar = code == "AR"
        if is_ar and arg_on:
            shake = math.sin(t * 70) * 9 * max(0.0, 1 - prog(t, 29.6, 1.6)) + math.sin(t * 50) * 2.5
        xo = int(lerp(-80, 0, eo(pr))) + shake
        put(cv, flag(code, 110, 72), 30 + 75 + xo, y + 34, lerp(.6, 1, eback(pr)), pr)
        put(cv, txt(name.upper(), "Poppins-ExtraBold", 38, WHITE, shadow=6), BAR_X + xo - 8, y - 6, 1, pr, anchor="l")
        g = eo(prog(t, ts, GROW))
        v = val * g
        bw = max(16, int(BAR_MAX * v / 9.0))
        red = is_ar and arg_on
        col = mix((86, 140, 235), RED, prog(t, 29.6, .3) if is_ar else 0)
        # track
        cv.alpha_composite(rrect((BAR_MAX, 52), 26, (255, 255, 255, int(28 * pr))), (BAR_X + int(xo), y + 32))
        if red:
            gb = glow_box(bw, 52, 26, RED, 22, int(150 + 80 * math.sin(t * 12)))
            cv.alpha_composite(gb, (BAR_X + int(xo) - (gb.width - bw) // 2, y + 32 - (gb.height - 52) // 2))
        bar = rrect((bw, 52), 26, col + (int(255 * pr),))
        # highlight stripe
        ImageDraw.Draw(bar).rounded_rectangle((6, 6, max(7, bw - 7), 18), 6, fill=(255, 255, 255, 60))
        cv.alpha_composite(bar, (BAR_X + int(xo), y + 32))
        # counter
        if g >= 1: s = lab
        elif val % 1: s = f"{v:.1f} días"
        else: s = f"{int(v)} días"
        nc = RED if red else WHITE
        put(cv, txt(s, "Anton-Regular", 56, nc, shadow=8), BAR_X + int(xo) + bw + 22, y + 56, 1 + .15 * math.exp(-max(0, t - ts - GROW) * 7) * (t > ts + GROW), pr, anchor="l")
        if code == "DO":
            pm = prog(t, 22.7, .4)
            put(cv, txt("microempresa: ~9 días", "Poppins-SemiBold", 30, (255, 170, 176), shadow=5), BAR_X + 4, y + 102, 1, pm, anchor="l")
    put(cv, txt("Edición estándar · salario mínimo 2026 · mes de 30 días", "Poppins-Medium", 27, GREY, shadow=5), W // 2, Y0 + 50 + 6 * ROW + 10, 1, prog(t, 13.6, .6))

# ---------------- map
GEO = json.load(open(f"{A}/countries.geojson"))
LON0, LON1, LAT0, LAT1 = -118.5, -33.0, -56.5, 33.0
MX0, MY0, MW = 60, 600, 960
SC = MW / (LON1 - LON0)
def proj(lon, lat): return (MX0 + (lon - LON0) * SC, MY0 + (LAT1 - lat) * SC * 1.0)
LATAM = {f["properties"]["ADM0_A3"] for f in GEO["features"] if f["properties"]["CONTINENT"] in ("North America", "South America")} - {"USA", "CAN", "GRL", "BMU", "SPM", "FLK"}
HIGHL = [("MEX", "MÉXICO", 37.40), ("CHL", "CHILE", 38.20), ("ARG", "ARGENTINA", 38.62), ("DOM", "REP. DOMINICANA", 39.75)]
MAPS = 3
def _polys(code):
    for f in GEO["features"]:
        if f["properties"]["ADM0_A3"] != code: continue
        g = f["geometry"]; ps = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for p in ps: yield [proj(*pt) for pt in p[0]]

@lru_cache(None)
def map_base():
    im = Image.new("RGBA", (W * MAPS, H * MAPS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for f in GEO["features"]:
        c = f["properties"]["ADM0_A3"]
        if c in LATAM:
            for poly in _polys(c):
                d.polygon([(x * MAPS, y * MAPS) for x, y in poly], fill=NAVY_L + (255,), outline=(150, 180, 230, 255), width=MAPS * 2)
        elif c in ("USA",):
            for poly in _polys(c):
                d.polygon([(x * MAPS, y * MAPS) for x, y in poly], fill=(20, 45, 95, 255), outline=(60, 90, 150, 255), width=MAPS)
    im = im.resize((W, H), Image.LANCZOS)
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gl.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * .7)))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0)); out.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), (90, 150, 255)).split(), gl.getchannel("A"))))
    out.alpha_composite(im)
    return out

@lru_cache(None)
def map_hl(code):
    im = Image.new("RGBA", (W * MAPS, H * MAPS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for poly in _polys(code):
        d.polygon([(x * MAPS, y * MAPS) for x, y in poly], fill=RED + (255,), outline=WHITE + (255,), width=MAPS * 2)
    im = im.resize((W, H), Image.LANCZOS)
    g = Image.merge("RGBA", (*Image.new("RGB", (W, H), RED).split(), im.getchannel("A").filter(ImageFilter.GaussianBlur(16))))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0)); out.alpha_composite(g); out.alpha_composite(g); out.alpha_composite(im)
    return out

def centroid(code):
    pts = max(_polys(code), key=len)
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

def s_map(cv, t):
    cv.alpha_composite(kenburns("phones", prog(t, 33.7, 8.4), 1.05, 1.15, 0, .3, scale=1.15, tint=.86, blur=8))
    bg_grade(cv, t, .8, .4, .85)
    p = prog(t, 33.8, .7)
    base = map_base()
    put(cv, base, W // 2, H // 2 + int(lerp(40, 0, eo(p))), lerp(.92, 1, eo(p)), p)
    # search pill
    sp = prog(t, 34.0, .5)
    put(cv, search_pill(t), W // 2, 470, lerp(.8, 1, eback(sp)), sp)
    lab_pos = {"MEX": (-10, 0, "c"), "CHL": (-150, -150, "c"), "ARG": (70, 60, "c"), "DOM": (40, -60, "c")}
    for code, name, ts in HIGHL:
        hp = prog(t, ts, .35)
        if hp <= 0: continue
        pulse = 1 + 0.15 * math.sin((t - ts) * 9) * math.exp(-(t - ts) * 1.2)
        put(cv, map_hl(code), W // 2, H // 2, 1.0, hp)
        cx, cy = centroid(code)
        for k in range(2):
            rp = ((t - ts) * 0.9 + k * .5) % 1.0
            rad = int(20 + 70 * rp)
            ring = Image.new("RGBA", (2 * rad + 8, 2 * rad + 8), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse((4, 4, 2 * rad + 4, 2 * rad + 4), outline=RED + (int(230 * (1 - rp) * hp),), width=5)
            cv.alpha_composite(ring, (int(cx - rad - 4), int(cy - rad - 4)))
        dx, dy, _ = lab_pos[code]
        lbl = label_chip(name)
        put(cv, lbl, int(cx + dx + (120 if code == "DOM" else 0)), int(cy + dy), lerp(.5, 1, eback(hp)) * pulse ** .3, hp)
    tp = prog(t, 36.8, .45)
    tt = txt("TENDENCIA EN GOOGLE", "Anton-Regular", 92, WHITE, shadow=14)
    put(cv, tt, W // 2, 1570, lerp(1.4, 1, eo(tp)), tp)
    if tp > 0:
        w = int(700 * eo(prog(t, 37.0, .5)))
        cv.alpha_composite(rrect((max(2, w), 10), 5, RED + (255,)), ((W - w) // 2, 1640))

@lru_cache(None)
def label_chip(name):
    t = txt(name, "Poppins-ExtraBold", 34, WHITE, shadow=0)
    im = Image.new("RGBA", (t.width + 10, t.height - 10), (0, 0, 0, 0))
    c = card(t.width - 10, 60, 30, RED + (255,), (255, 255, 255, 200), 3)
    o = c.copy(); o.alpha_composite(t, ((o.width - t.width) // 2, (o.height - t.height) // 2 - 2))
    return o

def search_pill(t):
    q = "gta 6 precio"
    n = int(cl((t - 34.3) / 1.1) * len(q))
    s = q[:n] + ("|" if int(t * 3) % 2 == 0 else " ")
    base = search_base()
    o = base.copy()
    tx = txt(s, "Poppins-SemiBold", 44, (30, 40, 60), shadow=0)
    o.alpha_composite(tx, (o.width // 2 - 300, o.height // 2 - tx.height // 2))
    return o

@lru_cache(None)
def search_base():
    c = card(760, 100, 50, WHITE + (255,), None, 0).copy()
    d = ImageDraw.Draw(c); cx, cy = c.width // 2 - 330, c.height // 2
    d.ellipse((cx - 22, cy - 26, cx + 14, cy + 10), outline=(90, 100, 120), width=6); d.line((cx + 8, cy + 4, cx + 24, cy + 20), fill=(90, 100, 120), width=7)
    ex = c.width // 2 + 330
    d.line([(ex - 40, cy + 14), (ex - 18, cy - 6), (ex - 4, cy + 6), (ex + 20, cy - 18)], fill=RED, width=7)
    d.polygon([(ex + 24, cy - 24), (ex + 6, cy - 22), (ex + 22, cy - 6)], fill=RED)
    return c

# ---------------- Lucía + Vice City
@lru_cache(None)
def lucia_photo():
    im = raw("cover").crop((388, 418, 598, 632)).resize((600, 611), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(2, 60, 2)).convert("RGBA")
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), 26, fill=255)
    im.putalpha(m)
    c = card(im.width + 16, im.height + 16, 32, WHITE + (255,), None, 0).copy()
    c.alpha_composite(im, ((c.width - im.width) // 2, (c.height - im.height) // 2))
    return c

def s_lucia(cv, t):
    cv.alpha_composite(kenburns("cover", prog(t, 42, 5.7), 1.1, 1.2, 0, 0, scale=1.2, fy=.3, tint=.72, blur=22))
    bg_grade(cv, t, .8, .3, .85)
    p = prog(t, 42.25, .5)
    put(cv, lucia_photo(), W // 2, int(lerp(900, 820, eo(p))), lerp(.85, 1, eo(p)) * (1 + .015 * (t - 42)), p)
    # "PERFIL" tab
    pt = prog(t, 42.5, .35)
    tab = txt("PERFIL", "Poppins-ExtraBold", 30, WHITE, shadow=0, track=6)
    tb = card(tab.width - 10, 52, 8, RED + (255,), None, 0).copy(); tb.alpha_composite(tab, ((tb.width - tab.width) // 2, (tb.height - tab.height) // 2))
    put(cv, tb, W // 2, 470, 1, pt)
    # lower third
    np_ = prog(t, 45.25, .4)
    nb = name_bar()
    put(cv, nb, int(lerp(-600, W // 2, eo(np_))), 1240, 1, np_)
    sp = prog(t, 43.2, .45)
    put(cv, sub_bar(), int(lerp(W + 600, W // 2, eo(sp))), 1375, 1, sp)

@lru_cache(None)
def name_bar():
    t = txt("LUCÍA CAMINOS", "Anton-Regular", 110, WHITE, shadow=0)
    c = card(900, 150, 10, NAVY + (250,), (255, 255, 255, 60), 2).copy()
    ImageDraw.Draw(c).rectangle((c.width // 2 - 450, c.height // 2 - 75, c.width // 2 - 432, c.height // 2 + 75), fill=RED)
    c.alpha_composite(t, ((c.width - t.width) // 2 + 6, (c.height - t.height) // 2 - 4))
    return c

@lru_cache(None)
def sub_bar():
    t = txt("Primera protagonista latina de GTA", "Poppins-Bold", 44, WHITE, shadow=0)
    c = card(t.width + 20, 84, 10, RED + (255,), None, 0).copy()
    c.alpha_composite(t, ((c.width - t.width) // 2, (c.height - t.height) // 2 - 2))
    return c

def s_miami(cv, t):
    cv.alpha_composite(kenburns("miami", prog(t, 47.55, 3.4), 1.0, 1.14, 0, -.4, scale=1.15, fy=.4))
    bg_grade(cv, t, .78, .1, .7)
    p = prog(t, 47.75, .45)
    put(cv, vice_label(), W // 2, 1300, lerp(1.4, 1, eback(p)), p)
    pp = prog(t, 47.7, .5)
    put(cv, pin(), W // 2, int(lerp(1040, 1110, eback(pp))), 1, pp)

@lru_cache(None)
def vice_label():
    a = txt("VICE CITY", "Anton-Regular", 120, WHITE, shadow=0)
    e = txt("=", "Anton-Regular", 120, RED, shadow=0)
    b = txt("MIAMI", "Anton-Regular", 120, WHITE, shadow=0)
    wsum = a.width + e.width + b.width + 8
    c = card(wsum + 40, 170, 18, NAVY + (225,), RED + (255,), 5).copy()
    x = (c.width - wsum) // 2
    for im in (a, e, b):
        c.alpha_composite(im, (x, (c.height - im.height) // 2 - 4)); x += im.width + 4
    return c

@lru_cache(None)
def pin():
    im = Image.new("RGBA", (140, 180), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((20, 10, 120, 110), fill=RED); d.polygon([(28, 80), (112, 80), (70, 165)], fill=RED)
    d.ellipse((50, 40, 90, 80), fill=WHITE)
    g = Image.new("RGBA", im.size, (0, 0, 0, 0)); g.alpha_composite(im); return g

# ---------------- numbers
def s_numbers(cv, t):
    k = "headset" if t < 53.0 else "redgamer"
    cv.alpha_composite(kenburns(k, prog(t, 50.85 if t < 53 else 53, 3), 1.05, 1.15, 0.3, 0, scale=1.15, fx=.55, tint=.6))
    if 53.0 <= t < 53.3: cv.alpha_composite(Image.new("RGBA", (W, H), NAVY_D + (int(255 * (1 - prog(t, 53, .3))),)))
    bg_grade(cv, t, .82, .4, .85)
    # card 1
    p1 = prog(t, 50.85, .4)
    put(cv, card(900, 330, 30), W // 2, 700, lerp(.85, 1, eback(p1)), p1)
    v = int(round(99 * eo(prog(t, 50.95, .75))))
    nn = txt(f"{v}", "Anton-Regular", 210, RED if v == 99 else WHITE, shadow=10)
    put(cv, nn, W // 2 - 110, 660, 1 + .1 * math.exp(-max(0, t - 51.7) * 6) * (t > 51.7), p1)
    put(cv, txt("/100", "Anton-Regular", 110, WHITE, shadow=8), W // 2 + 130, 690, 1, p1)
    put(cv, txt("METACRITIC", "Poppins-Black", 62, WHITE, shadow=6, track=10), W // 2, 810, 1, prog(t, 51.4, .4))
    # card 2
    p2 = prog(t, 53.1, .4)
    put(cv, card(900, 400, 30), W // 2, 1180, lerp(.85, 1, eback(p2)), p2)
    v2 = 7 * eo(prog(t, 53.2, .8))
    nn = txt(f"+{int(round(v2))} MILLONES", "Anton-Regular", 140, RED if v2 > 6.99 else WHITE, shadow=10)
    put(cv, nn, W // 2, 1120, 1 + .1 * math.exp(-max(0, t - 54.0) * 6) * (t > 54.0), p2)
    put(cv, txt("viendo en vivo en 3 horas", "Poppins-Bold", 54, WHITE, shadow=6), W // 2, 1235, 1, prog(t, 54.7, .4))
    # live chip
    lp = prog(t, 53.3, .3)
    chip = live_chip(int(t * 2) % 2 == 0)
    put(cv, chip, W // 2, 1010, 1, lp)

@lru_cache(None)
def live_chip(on):
    t = txt("EN VIVO", "Poppins-ExtraBold", 32, WHITE, shadow=0, track=4)
    c = card(t.width + 40, 56, 28, RED + (255,), None, 0).copy(); d = ImageDraw.Draw(c)
    cx = (c.width - t.width) // 2 - 10
    d.ellipse((cx - 8, c.height // 2 - 9, cx + 10, c.height // 2 + 9), fill=WHITE if on else (255, 180, 185))
    c.alpha_composite(t, (cx + 14, (c.height - t.height) // 2 - 2))
    return c

# ---------------- poll
def s_poll(cv, t):
    cv.alpha_composite(kenburns("phoneguy", prog(t, 57.25, 6.3), 1.05, 1.2, 0, .3, scale=1.15, fy=.4, tint=.55))
    bg_grade(cv, t, .82, .45, .88)
    p = prog(t, 57.35, .45)
    put(cv, card(940, 760, 40, (255, 255, 255, 245), None, 0), W // 2, 1060, lerp(.8, 1, eback(p)), p)
    q1 = txt("¿CUÁNTOS DÍAS", "Anton-Regular", 100, NAVY, shadow=0)
    q2 = txt("EN TU PAÍS?", "Anton-Regular", 100, NAVY, shadow=0)
    qp = prog(t, 58.45, .4)
    put(cv, q1, W // 2, 790, lerp(1.3, 1, eo(qp)), qp)
    put(cv, q2, W // 2 - 50, 900, lerp(1.3, 1, eo(qp)), qp)
    bounce = math.sin(t * 8) * 10
    put(cv, emoji("👇", 90), W // 2 + q2.width // 2 + 10, int(905 + bounce), 1, prog(t, 58.9, .3))
    for i, (em, s, ts) in enumerate([("🎮", "LO COMPRO YA", 61.05), ("💸", "ESPERO QUE BAJE", 62.3)]):
        op = prog(t, ts, .4)
        y = 1080 + i * 160
        sel = t > ts + 0.45
        put(cv, poll_opt(em, s, False), int(lerp(W // 2 + (300 if i else -300), W // 2, eo(op))), y, lerp(.8, 1, eback(op)) * (1 + .03 * math.sin(t * 6 + i * 2) * sel), op)
    put(cv, txt("Déjalo en los comentarios", "Poppins-SemiBold", 40, WHITE, shadow=8), W // 2, 1525, 1, prog(t, 61.5, .5))

@lru_cache(None)
def poll_opt(em, s, sel):
    c = card(800, 124, 62, (234, 239, 248, 255), NAVY + (255,), 4).copy()
    e = emoji(em, 70)
    tx = txt(s, "Poppins-Black", 52, NAVY, shadow=0)
    tw = e.width + 24 + tx.width
    x = (c.width - tw) // 2
    c.alpha_composite(e, (x, (c.height - e.height) // 2)); c.alpha_composite(tx, (x + e.width + 24, (c.height - tx.height) // 2 - 2))
    return c

# ---------------------------------------------------------------- frame
CUTS = [5.7, 13.0, 33.7, 42.15, 47.55, 50.85, 57.25]
SCENES = [(0, 5.7, s_hook), (5.7, 13.0, s_price), (13.0, 33.7, s_rank), (33.7, 42.15, s_map),
          (42.15, 47.55, s_lucia), (47.55, 50.85, s_miami), (50.85, 57.25, s_numbers), (57.25, END_MAIN, s_poll)]

def frame(t):
    cv = Image.new("RGBA", (W, H), NAVY_D + (255,))
    for a, b, fn in SCENES:
        if a <= t < b: fn(cv, t); break
    if 8.35 <= t < 8.7:  # mini cut inside price scene
        transition(cv, t, 8.4)
    for c in CUTS: transition(cv, t, c)
    cv.alpha_composite(vignette())
    cv.alpha_composite(grain(int(t * FPS) % 6))
    subtitles(cv, t)
    watermark(cv, t)
    if t < 0.25: cv.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - t / .25)))))
    if t > END_MAIN - .2:
        cv.alpha_composite(Image.new("RGBA", (W, H), NAVY + (int(255 * prog(t, END_MAIN - .2, .2)),)))
    return cv.convert("RGB")

def render_range(args):
    i0, i1, path = args
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(i0, i1):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()
    return path

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if len(sys.argv) > 3 and sys.argv[3] == "stills":
        for s in sys.argv[4:]:
            frame(float(s)).save(f"{OUT}/still_{float(s):05.2f}.jpg", quality=85)
        sys.exit()
    n = int(round(END_MAIN * FPS))
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    step = math.ceil(n / k)
    jobs = [(i, min(n, i + step), f"{OUT}/part{j:02d}.mp4") for j, i in enumerate(range(0, n, step))]
    with Pool(k) as pool:
        parts = pool.map(render_range, jobs)
    with open(f"{OUT}/parts.txt", "w") as f:
        for pth in parts: f.write(f"file '{os.path.abspath(pth)}'\n")
    print("frames", n)
