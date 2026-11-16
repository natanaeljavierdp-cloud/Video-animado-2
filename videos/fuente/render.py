#!/usr/bin/env python3
"""Sandoval Legal — 'Ese comentario te puede costar la cárcel' (1080x1920, 30fps)."""
import json, math, os, random, sys, subprocess
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

S = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
DUR = 79.5
FONTS = f"{S}/dl/fonts/ttf"
PH = f"{S}/in/fotos_sandoval"

NAVY = (11, 22, 44)
NAVY2 = (6, 13, 28)
GOLD = (212, 175, 95)
GOLD_L = (240, 210, 140)
SILVER = (196, 201, 210)
WHITE = (255, 255, 255)
RED = (200, 38, 45)

# ---------------------------------------------------------------- utils
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def ease_out(x): return 1 - (1 - x) ** 3
def ease_io(x): return 3 * x * x - 2 * x * x * x
def ease_back(x, s=1.7):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, x): return a + (b - a) * x

@lru_cache(None)
def font(name, size):
    m = {"cinzel": "cinzel-latin-700-normal", "cinzel9": "cinzel-latin-900-normal",
         "mont5": "montserrat-latin-500-normal", "mont7": "montserrat-latin-700-normal",
         "mont8": "montserrat-latin-800-normal", "mont9": "montserrat-latin-900-normal",
         "pfi": "playfair-display-latin-400-italic", "pf7": "playfair-display-latin-700-normal"}[name]
    return ImageFont.truetype(f"{FONTS}/{m}.ttf", size)

@lru_cache(4096)
def text_img(txt, fname, size, color=WHITE, shadow=True, glow=None, tracking=0, stroke=0):
    f = font(fname, size)
    if tracking:
        widths = [f.getlength(c) for c in txt]
        tw = int(sum(widths) + tracking * (len(txt) - 1))
    else:
        tw = int(f.getlength(txt))
    asc, desc = f.getmetrics()
    pad = int(size * 0.5) + 10
    im = Image.new("RGBA", (tw + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    def draw(dd, fill):
        if tracking:
            x = pad
            for c, w_ in zip(txt, widths):
                dd.text((x, pad), c, font=f, fill=fill, stroke_width=stroke, stroke_fill=fill)
                x += w_ + tracking
        else:
            dd.text((pad, pad), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=fill)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); draw(ImageDraw.Draw(sh), (0, 0, 0, 200))
        sh = sh.filter(ImageFilter.GaussianBlur(max(3, size // 14)))
        out.alpha_composite(sh, (0, max(2, size // 24)))
    if glow:
        g = Image.new("RGBA", im.size, (0, 0, 0, 0)); draw(ImageDraw.Draw(g), glow + (255,))
        g = g.filter(ImageFilter.GaussianBlur(size // 6))
        out.alpha_composite(g); out.alpha_composite(g)
    draw(d, color + (255,))
    out.alpha_composite(im)
    return out

def with_alpha(im, a):
    if a >= 0.999: return im
    im = im.copy()
    al = im.getchannel("A").point(lambda v: int(v * a))
    im.putalpha(al)
    return im

def paste(frame, im, cx, cy, alpha=1.0, scale=1.0, anchor="c"):
    if alpha <= 0.003 or scale <= 0.01: return
    if abs(scale - 1) > 0.003:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    im = with_alpha(im, alpha)
    if anchor == "c": x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    elif anchor == "l": x, y = int(cx), int(cy - im.height / 2)
    else: x, y = int(cx - im.width), int(cy - im.height / 2)
    # crop to frame
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + im.width), min(H, y + im.height)
    if x1 <= x0 or y1 <= y0: return
    if (x0, y0, x1, y1) != (x, y, x + im.width, y + im.height):
        im = im.crop((x0 - x, y0 - y, x1 - x, y1 - y))
    frame.alpha_composite(im, (x0, y0))

def rrect(size, radius, fill=None, outline=None, width=0, ss=3):
    w, h = size
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((width * ss // 2, width * ss // 2, w * ss - 1 - width * ss // 2, h * ss - 1 - width * ss // 2),
                        radius * ss, fill=fill, outline=outline, width=width * ss)
    return im.resize((w, h), Image.LANCZOS)

def shadowed(im, blur=18, off=10, op=170):
    pad = blur * 3
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, op)); sh.putalpha(im.getchannel("A").point(lambda v: v * op // 255))
    out.alpha_composite(sh, (pad, pad + off))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(im, (pad, pad))
    return out

# ---------------------------------------------------------------- icons (line art)
@lru_cache(None)
def icon(name, size=150, color=GOLD, lw=7):
    ss = 4; s = size * ss; L = lw * ss
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = color + (255,)
    def R(a, b, c_, d_): return (a * s, b * s, c_ * s, d_ * s)
    if name == "radio":
        d.rounded_rectangle(R(.1, .32, .9, .85), radius=.08 * s, outline=c, width=L)
        d.ellipse(R(.18, .45, .48, .75), outline=c, width=L)
        d.ellipse(R(.29, .56, .37, .64), fill=c)
        for y in (.48, .59, .7): d.line((.58 * s, y * s, .8 * s, y * s), fill=c, width=L)
        d.line((.25 * s, .32 * s, .72 * s, .1 * s), fill=c, width=L)
    elif name == "tv":
        d.rounded_rectangle(R(.08, .26, .92, .78), radius=.07 * s, outline=c, width=L)
        d.line((.35 * s, .1 * s, .5 * s, .26 * s), fill=c, width=L); d.line((.65 * s, .1 * s, .5 * s, .26 * s), fill=c, width=L)
        d.line((.32 * s, .9 * s, .68 * s, .9 * s), fill=c, width=L)
        d.line((.5 * s, .78 * s, .5 * s, .9 * s), fill=c, width=L)
    elif name == "stream":
        d.rounded_rectangle(R(.08, .2, .92, .8), radius=.1 * s, outline=c, width=L)
        d.polygon([(.42 * s, .36 * s), (.42 * s, .64 * s), (.66 * s, .5 * s)], fill=c)
        d.ellipse(R(.14, .26, .22, .34), fill=RED + (255,))
    elif name == "redes":
        d.rounded_rectangle(R(.08, .14, .92, .7), radius=.14 * s, outline=c, width=L)
        d.polygon([(.25 * s, .66 * s), (.25 * s, .9 * s), (.45 * s, .68 * s)], fill=c)
        # heart
        hx, hy, hr = .5 * s, .42 * s, .1 * s
        d.ellipse((hx - 2 * hr, hy - hr, hx, hy + hr * .9), fill=c)
        d.ellipse((hx, hy - hr, hx + 2 * hr, hy + hr * .9), fill=c)
        d.polygon([(hx - 1.95 * hr, hy + .15 * hr), (hx + 1.95 * hr, hy + .15 * hr), (hx, hy + 2.1 * hr)], fill=c)
    elif name == "lock":
        d.arc(R(.27, .08, .73, .58), 180, 360, fill=c, width=L)
        d.line((.27 * s + L / 2, .33 * s, .27 * s + L / 2, .45 * s), fill=c, width=L)
        d.line((.73 * s - L / 2, .33 * s, .73 * s - L / 2, .45 * s), fill=c, width=L)
        d.rounded_rectangle(R(.15, .44, .85, .92), radius=.08 * s, outline=c, width=L)
        d.ellipse(R(.44, .58, .56, .7), fill=c); d.rectangle(R(.475, .66, .525, .8), fill=c)
    elif name == "money":
        d.rectangle(R(.24, .1, .76, .55), outline=c, width=L)
        f = ImageFont.truetype(f"{FONTS}/montserrat-latin-900-normal.ttf", int(.34 * s))
        d.text((.5 * s, .33 * s), "$", font=f, fill=c, anchor="mm")
        d.rectangle(R(.08, .4, .92, .9), fill=(0, 0, 0, 0))
        d.rectangle(R(.08, .4, .92, .9), outline=c, width=L)
        d.line((.08 * s, .4 * s, .5 * s, .7 * s), fill=c, width=L); d.line((.92 * s, .4 * s, .5 * s, .7 * s), fill=c, width=L)
    elif name == "people":
        for cx_, sc in ((.33, 1), (.67, 1)):
            d.ellipse(R(cx_ - .12, .14, cx_ + .12, .38), outline=c, width=L)
            d.arc(R(cx_ - .22, .46, cx_ + .22, 1.2), 180, 360, fill=c, width=L)
        d.line((.06 * s, .83 * s, .94 * s, .83 * s), fill=c, width=L)
    elif name == "building":
        d.rectangle(R(.22, .12, .78, .88), outline=c, width=L)
        for i in range(3):
            for j in range(2):
                x = .32 + j * .24; y = .22 + i * .17
                d.rectangle(R(x, y, x + .12, y + .09), fill=c)
        d.rectangle(R(.43, .72, .57, .88), fill=c)
        d.line((.08 * s, .88 * s, .92 * s, .88 * s), fill=c, width=L)
    elif name == "scales":
        d.line((.5 * s, .12 * s, .5 * s, .82 * s), fill=c, width=L)
        d.line((.14 * s, .26 * s, .86 * s, .26 * s), fill=c, width=L)
        d.line((.3 * s, .88 * s, .7 * s, .88 * s), fill=c, width=L)
        d.ellipse(R(.45, .07, .55, .17), fill=c)
        for x in (.2, .8):
            d.line((x * s, .26 * s, (x - .12) * s, .56 * s), fill=c, width=L // 2)
            d.line((x * s, .26 * s, (x + .12) * s, .56 * s), fill=c, width=L // 2)
            d.chord(R(x - .15, .44, x + .15, .68), 0, 180, fill=c)
    elif name == "mic":
        d.rounded_rectangle(R(.36, .08, .64, .56), radius=.14 * s, outline=c, width=L)
        d.arc(R(.24, .3, .76, .7), 0, 180, fill=c, width=L)
        d.line((.5 * s, .7 * s, .5 * s, .86 * s), fill=c, width=L); d.line((.34 * s, .88 * s, .66 * s, .88 * s), fill=c, width=L)
    elif name == "x":
        d.line((.22 * s, .22 * s, .78 * s, .78 * s), fill=c, width=L); d.line((.78 * s, .22 * s, .22 * s, .78 * s), fill=c, width=L)
    return im.resize((size, size), Image.LANCZOS)

@lru_cache(None)
def icon_badge(name, size=190, ring=SILVER, col=GOLD, fill=(11, 22, 44, 225)):
    ss = 3; s = size * ss
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((6, 6, s - 7, s - 7), fill=fill, outline=ring + (255,), width=4 * ss)
    im = im.resize((size, size), Image.LANCZOS)
    ic = icon(name, int(size * .52), col, 6)
    im.alpha_composite(ic, ((size - ic.width) // 2, (size - ic.height) // 2))
    return shadowed(im, 12, 6, 150)

# ---------------------------------------------------------------- photos / Ken Burns
@lru_cache(None)
def photo(name, focus=0.5, focus_y=0.5, blur=0):
    im = Image.open(f"{PH}/{name}").convert("RGB")
    # cover 1.18x of frame so we can zoom/pan
    sc = max(W * 1.2 / im.width, H * 1.2 / im.height)
    im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
    if blur: im = im.filter(ImageFilter.GaussianBlur(blur))
    return im, focus, focus_y

@lru_cache(None)
def vignette(strength=0.85, red=False):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = (x - W / 2) / (W / 2); dy = (y - H / 2) / (H / 2)
    r = np.sqrt(dx * dx * 1.0 + dy * dy * 0.55)
    v = np.clip((r - 0.35) / 0.95, 0, 1) ** 1.6 * strength
    # extra darkening at top (subtitles) and bottom (frame)
    top = np.clip(1 - y / 620, 0, 1) ** 1.5 * 0.55
    bot = np.clip((y - 1400) / 520, 0, 1) ** 1.4 * 0.7
    v = np.clip(v + top + bot, 0, 0.96)
    a = (v * 255).astype(np.uint8)
    col = np.zeros((H, W, 4), np.uint8)
    col[..., :3] = (40, 4, 8) if red else NAVY2
    col[..., 3] = a
    return Image.fromarray(col, "RGBA")

def ken_burns(name, t, t0, t1, zoom=(1.0, 1.1), pan=(0, 0), focus=0.5, focus_y=0.5, dark=0.42, tint=0.28, blur=0):
    im, fx, fy = photo(name, focus, focus_y, blur)
    p = ease_io(prog(t, t0, max(0.01, t1 - t0 + 0.6)))
    z = lerp(zoom[0], zoom[1], p)
    # visible region in source pixels
    vw, vh = W * 1.2 / 1.2 / z * (im.width / (W * 1.2)) * 1.0, 0
    base = min(im.width / W, im.height / H)  # source px per output px at z=1 with full cover
    base = base / 1.18
    vw, vh = W * base / z, H * base / z
    cx = fx * im.width + pan[0] * p * im.width * 0.06
    cy = fy * im.height + pan[1] * p * im.height * 0.06
    cx = clamp(cx, vw / 2, im.width - vw / 2); cy = clamp(cy, vh / 2, im.height - vh / 2)
    box = (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2)
    fr = im.transform((W, H), Image.EXTENT, box, Image.BILINEAR)
    a = np.asarray(fr).astype(np.float32)
    a = a * (1 - dark)
    a = a * (1 - tint) + np.array(NAVY, np.float32) * tint * 1.6
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")

# ---------------------------------------------------------------- static frame overlay
@lru_cache(None)
def frame_overlay():
    ss = 2
    im = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    m = 28 * ss
    d.rectangle((m, m, W * ss - m, H * ss - m), outline=SILVER + (150,), width=2 * ss)
    L = 70 * ss; t_ = 6 * ss
    for (x, y, sx, sy) in ((m, m, 1, 1), (W * ss - m, m, -1, 1), (m, H * ss - m, 1, -1), (W * ss - m, H * ss - m, -1, -1)):
        d.line((x, y, x + sx * L, y), fill=SILVER + (255,), width=t_)
        d.line((x, y, x, y + sy * L), fill=SILVER + (255,), width=t_)
    # bottom info strip
    yb = 1640 * ss
    d.line((70 * ss, yb, (W - 70) * ss, yb), fill=SILVER + (170,), width=2 * ss)
    d.rectangle((70 * ss, yb - 3 * ss, 230 * ss, yb + 3 * ss), fill=GOLD + (255,))
    im = im.resize((W, H), Image.LANCZOS)
    # logo top-left
    lg = Image.open(f"{S}/work/logo_full.png").resize((150, 150), Image.LANCZOS)
    im.alpha_composite(shadowed(lg, 10, 4, 160), (60 - 30, 62 - 30 + 0))
    # header text next to logo
    t1 = text_img("SANDOVAL LEGAL", "cinzel", 38, GOLD, tracking=3)
    im.alpha_composite(t1, (225 - 29, 80 - 29 + 4))
    t2 = text_img("SOLUCIÓN JURÍDICA · RD", "mont7", 22, SILVER, tracking=4, shadow=True)
    im.alpha_composite(t2, (225 - 21, 135 - 21 + 4))
    # bottom labels
    b1 = text_img("@sandoval_legal", "mont8", 32, GOLD)
    im.alpha_composite(b1, (70 - 26, 1662 - 26 + 4))
    b2 = text_img("CÓDIGO PENAL · LEY 74-25", "mont7", 24, SILVER, tracking=3)
    im.alpha_composite(b2, (W - 70 - b2.width + 22, 1668 - 22 + 4))
    return im

# ---------------------------------------------------------------- subtitles
WORDS = json.load(open(f"{S}/work/words.json"))
FIX = {"Dominicano,": "dominicano,"}
WORDS = [[FIX.get(w, w), a, b] for w, a, b in WORDS]

def build_chunks():
    chunks, cur = [], []
    for i, w in enumerate(WORDS):
        if cur and len(" ".join(WORDS[j][0] for j in cur + [i])) > 19:
            chunks.append(cur); cur = []
        cur.append(i)
        txt = " ".join(WORDS[j][0] for j in cur)
        nxt_gap = WORDS[i + 1][1] - w[2] if i + 1 < len(WORDS) else 9
        if w[0][-1] in ".,?!" or len(cur) >= 4 or len(txt) >= 20 or nxt_gap > 0.35:
            chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    out = []
    for k, c in enumerate(chunks):
        s = WORDS[c[0]][1]
        e = WORDS[c[-1]][2] + 0.35
        if k + 1 < len(chunks): e = min(e + 0.6, WORDS[chunks[k + 1][0]][1])
        out.append((s, e, c))
    return out
CHUNKS = build_chunks()
SUB_END = 75.7

def draw_subs(frame, t):
    if t >= SUB_END: return
    for s, e, c in CHUNKS:
        if s - 0.05 <= t < e:
            break
    else:
        return
    f = font("mont9", 66)
    words = [WORDS[i][0].upper() for i in c]
    active = None
    for i in c:
        if WORDS[i][1] - 0.04 <= t: active = i
    sp = f.getlength(" ")
    widths = [f.getlength(w) for w in words]
    # line break if too wide
    lines, cur, cw = [], [], 0
    for k, w_ in enumerate(widths):
        if cur and cw + sp + w_ > 900:
            lines.append(cur); cur, cw = [], 0
        cw += (sp if cur else 0) + w_; cur.append(k)
    lines.append(cur)
    lh = 80
    y0 = 330 - (len(lines) - 1) * lh / 2
    pin = ease_out(prog(t, s - 0.05, 0.15))
    for li, ln in enumerate(lines):
        lw_ = sum(widths[k] for k in ln) + sp * (len(ln) - 1)
        x = W / 2 - lw_ / 2
        for k in ln:
            i = c[k]
            is_act = (i == active)
            said = WORDS[i][1] - 0.04 <= t
            col = GOLD_L if is_act else WHITE
            im = text_img(words[k], "mont9", 66, col, glow=(150, 110, 30) if is_act else None, stroke=0)
            pad = 33 + 10
            sc = 1.0
            if is_act:
                sc = 1 + 0.08 * (1 - ease_out(prog(t, WORDS[i][1] - 0.04, 0.18)))
            a = 1.0 if said else 0.55
            a *= pin
            paste(frame, im, x + widths[k] / 2, y0 + li * lh + (1 - pin) * 14, alpha=a, scale=sc)
            x += widths[k] + sp

# ---------------------------------------------------------------- reusable components
@lru_cache(None)
def tag_bar(art, title, accent=GOLD, w=None):
    a = text_img(art, "mont9", 34, NAVY2, shadow=False, tracking=2)
    b = text_img(title, "cinzel9", 54, WHITE, shadow=False, tracking=2)
    pa, pb = 27, 37
    aw = a.width - 2 * pa + 44
    bw = b.width - 2 * pb + 56
    hgt = 92
    tot = aw + bw
    im = Image.new("RGBA", (tot, hgt), (0, 0, 0, 0))
    im.alpha_composite(rrect((aw + 20, hgt), 10, fill=accent + (255,)), (0, 0))
    im.alpha_composite(rrect((bw + 10, hgt), 10, fill=(10, 20, 40, 235), outline=SILVER + (255,), width=3), (aw - 10, 0))
    im.alpha_composite(a, (22 - pa, (hgt - a.height) // 2 + 2))
    im.alpha_composite(b, (aw + 28 - pb, (hgt - b.height) // 2 + 4))
    return shadowed(im, 14, 6, 170)

def draw_tag(frame, t, t0, art, title, y=520, accent=GOLD, t_out=None):
    p = prog(t, t0, 0.45)
    if p <= 0: return
    a = ease_out(p)
    if t_out is not None: a *= 1 - prog(t, t_out, 0.3)
    full = tag_bar(art, title, accent)
    sc = min(1.0, 1000 / full.width)
    wv = int(full.width * ease_out(p))
    if wv < 4: return
    im = full.crop((0, 0, wv, full.height))
    paste(frame, im, W / 2 - full.width * sc / 2, y, alpha=a, anchor="l", scale=sc)

@lru_cache(None)
def panel(w, h, border=SILVER, fill=(9, 18, 38, 215), radius=26, bw=3):
    return shadowed(rrect((w, h), radius, fill=fill, outline=border + (255,), width=bw), 20, 10, 170)

def big_number_img(txt, size=220, color=GOLD_L):
    return text_img(txt, "mont9", size, color, glow=(150, 105, 25))

def counter_val(t, t0, target, d=0.55):
    p = prog(t, t0, d)
    return int(round(ease_out(p) * target))

# ---------------------------------------------------------------- scenes
def glitch(frame, t, seed):
    rnd = random.Random(seed)
    a = np.asarray(frame.convert("RGB")).copy()
    sh = rnd.randint(8, 22)
    a[..., 0] = np.roll(a[..., 0], sh, axis=1)
    a[..., 2] = np.roll(a[..., 2], -sh, axis=1)
    for _ in range(rnd.randint(4, 9)):
        y = rnd.randint(0, H - 80); hh = rnd.randint(10, 90); dx = rnd.randint(-90, 90)
        a[y:y + hh] = np.roll(a[y:y + hh], dx, axis=1)
    # scanlines
    a[::4] = (a[::4] * 0.75).astype(np.uint8)
    return Image.fromarray(a).convert("RGBA")

COMMENT = "Fulano es un ladrón, todos en la oficina lo saben..."

@lru_cache(None)
def comment_card(n):
    w, h = 900, 300
    im = rrect((w, h), 34, fill=(255, 255, 255, 245))
    d = ImageDraw.Draw(im)
    d.ellipse((34, 34, 104, 104), fill=(190, 196, 206))
    d.ellipse((56, 46, 82, 72), fill=(245, 245, 245)); d.chord((44, 70, 94, 120), 180, 360, fill=(245, 245, 245))
    d.text((124, 40), "usuario_anonimo", font=font("mont8", 32), fill=(20, 20, 30))
    d.text((124, 80), "Comentando ahora", font=font("mont5", 24), fill=(130, 135, 145))
    # text wrapping
    txt = COMMENT[:n]
    f = font("mont7", 40)
    words = txt.split(" "); lines, cur = [], ""
    for wd in words:
        if f.getlength((cur + " " + wd).strip()) > w - 90: lines.append(cur); cur = wd
        else: cur = (cur + " " + wd).strip()
    lines.append(cur)
    y = 140
    for ln in lines:
        d.text((44, y), ln, font=f, fill=(25, 25, 35)); y += 52
    # caret
    lx = 44 + f.getlength(lines[-1]) + 4
    d.rectangle((lx, y - 52 + 6, lx + 4, y - 52 + 46), fill=(30, 120, 255))
    # send button
    d.rounded_rectangle((w - 190, h - 74, w - 34, h - 26), 22, fill=(30, 120, 255))
    d.text((w - 112, h - 50), "Publicar", font=font("mont8", 24), fill=WHITE, anchor="mm")
    return shadowed(im, 22, 12, 180)

def scene_hook(fr, t):
    # typing 0.4 -> 3.3
    n = int(len(COMMENT) * clamp((t - 0.4) / 2.9))
    card_in = ease_back(prog(t, 0.1, 0.45))
    out = prog(t, 4.25, 0.35)
    if out < 1:
        y = 980 - 60 * out
        paste(fr, comment_card(n), W / 2, y + (1 - card_in) * 120, alpha=min(1, card_in * 1.4) * (1 - out * 0.75), scale=1 - 0.15 * out)
    if 3.55 <= t < 4.25:
        fr = glitch(fr, t, int(t * FPS))
    # 5 AÑOS
    if t >= 4.3:
        p = prog(t, 4.33, 0.25)
        v = counter_val(t, 4.33, 5, 0.42)
        sc = lerp(2.2, 1.0, ease_out(p))
        shake = (1 - prog(t, 4.75, 0.35)) * (6 if t > 4.75 else 0)
        num = big_number_img(str(v), 430)
        paste(fr, num, W / 2 + random.Random(int(t * 30)).uniform(-shake, shake), 960, alpha=ease_out(p), scale=sc)
        a2 = ease_out(prog(t, 4.75, 0.3))
        paste(fr, text_img("AÑOS", "mont9", 150, GOLD_L, glow=(150, 105, 25), tracking=10), W / 2, 1210, alpha=a2, scale=lerp(1.3, 1, a2))
        a3 = ease_out(prog(t, 5.25, 0.3))
        paste(fr, text_img("DE CÁRCEL", "cinzel9", 70, WHITE, tracking=8), W / 2, 1340 + (1 - a3) * 30, alpha=a3)
        # flash
        fl = 1 - prog(t, 4.33, 0.25)
        if fl > 0:
            fr.alpha_composite(Image.new("RGBA", (W, H), (255, 240, 200, int(120 * fl))))
    return fr

@lru_cache(None)
def doc_card():
    w, h = 820, 640
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.alpha_composite(rrect((w, h), 18, fill=(12, 24, 48, 240), outline=SILVER + (255,), width=4))
    im.alpha_composite(rrect((w - 36, h - 36), 12, fill=None, outline=SILVER + (150,), width=2), (18, 18))
    d = ImageDraw.Draw(im)
    def ct(y, txt, fn, sz, col, tr=0):
        ti = text_img(txt, fn, sz, col, shadow=False, tracking=tr)
        im.alpha_composite(ti, ((w - ti.width) // 2, y - ti.height // 2))
    ct(78, "REPÚBLICA DOMINICANA", "mont7", 26, SILVER, 8)
    sc_ = icon("scales", 120, GOLD, 6); im.alpha_composite(sc_, ((w - 120) // 2, 120))
    ct(310, "NUEVO", "cinzel9", 54, WHITE, 6)
    ct(380, "CÓDIGO PENAL", "cinzel9", 78, WHITE, 4)
    d.line((140, 450, w - 140, 450), fill=GOLD + (255,), width=3)
    ct(525, "LEY 74-25", "mont9", 92, GOLD_L, 6)
    return shadowed(im, 26, 14, 190)

def scene_context(fr, t):
    p = prog(t, 7.6, 0.6)
    if p > 0:
        a = ease_out(p)
        paste(fr, doc_card(), W / 2, 920 + (1 - a) * 260, alpha=a, scale=lerp(0.92, 1, a))
        # shimmer sweep across the card
    a2 = ease_out(prog(t, 9.5, 0.4))
    paste(fr, text_img("LO QUE DICES EN INTERNET", "mont8", 46, WHITE, tracking=2), W / 2, 1330 + (1 - a2) * 20, alpha=a2)
    a3 = ease_out(prog(t, 10.82, 0.4))
    paste(fr, text_img("TIENE CONSECUENCIAS", "mont9", 62, GOLD_L, glow=(120, 85, 20), tracking=2), W / 2, 1400 + (1 - a3) * 20, alpha=a3, scale=lerp(1.2, 1, a3))
    return fr

def scene_difam(fr, t):
    draw_tag(fr, t, 13.65, "ART. 208", "DIFAMACIÓN", 520)
    # definition 14.38 -> 23.0
    dout = prog(t, 24.6, 0.35)
    if t >= 14.3 and dout < 1:
        a = ease_out(prog(t, 14.38, 0.4)) * (1 - dout)
        paste(fr, panel(900, 330), W / 2, 790, alpha=a)
        paste(fr, text_img("ACUSAR PÚBLICAMENTE", "mont9", 52, WHITE, tracking=1), W / 2, 715, alpha=a)
        paste(fr, text_img("a alguien de un", "pfi", 46, SILVER), W / 2, 785, alpha=a)
        a2 = ease_out(prog(t, 16.28, 0.35)) * (1 - dout)
        paste(fr, text_img("HECHO CONCRETO", "mont9", 76, GOLD_L, glow=(140, 100, 20), tracking=2), W / 2, 868, alpha=a2, scale=lerp(1.3, 1, a2))
        a3 = ease_out(prog(t, 17.42, 0.35)) * (1 - dout)
        paste(fr, text_img("que daña su honor y su buen nombre", "pfi", 40, WHITE), W / 2, 1000, alpha=a3)
        # example (live)
        a4 = ease_out(prog(t, 19.2, 0.4)) * (1 - dout)
        if a4 > 0:
            paste(fr, panel(860, 250, border=SILVER, fill=(255, 255, 255, 235)), W / 2, 1250 + (1 - a4) * 40, alpha=a4)
            live = rrect((150, 52), 10, fill=RED + (255,))
            ImageDraw.Draw(live).text((75, 26), "● EN VIVO", font=font("mont8", 24), fill=WHITE, anchor="mm")
            paste(fr, live, 220, 1170 + (1 - a4) * 40, alpha=a4, anchor="l")
            paste(fr, text_img("Ej.: decir en un live", "mont7", 30, (90, 95, 110), shadow=False), 600, 1170 + (1 - a4) * 40, alpha=a4)
            a5 = ease_out(prog(t, 20.84, 0.35)) * (1 - dout)
            paste(fr, text_img("“Fulano se robó algo", "pf7", 50, (15, 25, 50), shadow=False), W / 2, 1245, alpha=a5)
            paste(fr, text_img("en su trabajo”", "pf7", 50, (15, 25, 50), shadow=False), W / 2, 1305, alpha=a5)
    # "y la ley lo dice clarito" -> icons 25.56, 26.34, 27.3, 28.12
    icons = [("radio", "RADIO", 25.56), ("tv", "TV", 26.34), ("stream", "STREAMING", 27.3), ("redes", "REDES", 28.12)]
    up = ease_io(prog(t, 29.1, 0.5))
    if t >= 24.9:
        a0 = ease_out(prog(t, 24.86, 0.4))
        paste(fr, text_img("APLICA EN:", "mont8", 44, SILVER, tracking=6), W / 2, lerp(760, 650, up), alpha=a0 * (1 - up))
        for k, (nm, lab, t0) in enumerate(icons):
            p = prog(t, t0 - 0.05, 0.4)
            if p <= 0: continue
            x = 165 + k * 250
            y = lerp(930, 720, up)
            sc = ease_back(p) * lerp(1, 0.72, up)
            paste(fr, icon_badge(nm), x, y, alpha=min(1, p * 2), scale=sc)
            paste(fr, text_img(lab, "mont8", 30, WHITE, tracking=2), x, y + lerp(140, 100, up), alpha=min(1, p * 2), scale=lerp(1, 0.85, up))
    if t >= 29.2:
        a = ease_out(prog(t, 29.26, 0.4))
        paste(fr, panel(940, 520, border=GOLD), W / 2, 1150, alpha=a, scale=lerp(0.9, 1, a))
        paste(fr, text_img("LA PENA", "mont8", 40, SILVER, tracking=8), W / 2, 950, alpha=a)
        v1 = counter_val(t, 29.96, 2, 0.35); v2 = counter_val(t, 30.42, 5, 0.45)
        a1 = ease_out(prog(t, 29.9, 0.25)); a2 = ease_out(prog(t, 30.36, 0.25))
        paste(fr, big_number_img(str(v1), 220), 330, 1110, alpha=a1, scale=lerp(1.5, 1, a1))
        paste(fr, text_img("A", "mont9", 90, WHITE), W / 2, 1120, alpha=a2)
        paste(fr, big_number_img(str(v2), 220), 750, 1110, alpha=a2, scale=lerp(1.5, 1, a2))
        a3 = ease_out(prog(t, 30.86, 0.35))
        paste(fr, text_img("AÑOS DE PRISIÓN", "mont9", 66, WHITE, tracking=3), W / 2, 1275, alpha=a3)
        a4 = ease_out(prog(t, 32.0, 0.35))
        paste(fr, text_img("+ MULTA", "mont9", 70, GOLD_L, glow=(130, 90, 20), tracking=4), W / 2, 1365, alpha=a4, scale=lerp(1.4, 1, a4))
    return fr

def scene_injuria(fr, t):
    draw_tag(fr, t, 33.2, "ART. 210", "INJURIA", 520)
    sout = ease_io(prog(t, 39.25, 0.4))
    if t >= 34.0 and sout < 1:
        for side, (verb, res, t0, x) in enumerate([("ACUSAR", "Difamación", 34.18, 290), ("INSULTAR", "Injuria", 35.7, 790)]):
            p = prog(t, t0, 0.45)
            if p <= 0: continue
            a = ease_out(p) * (1 - sout)
            dx = (1 - ease_out(p)) * (-200 if side == 0 else 200)
            hl = side == 1 and t >= 38.4
            bc = GOLD if hl else SILVER
            paste(fr, panel(440, 560, border=bc, bw=4 if hl else 3), x + dx, 960, alpha=a)
            paste(fr, icon_badge("mic" if side == 0 else "x", 150), x + dx, 790, alpha=a)
            paste(fr, text_img(verb, "mont9", 60, WHITE, tracking=2), x + dx, 930, alpha=a)
            paste(fr, text_img("=", "mont9", 70, GOLD_L), x + dx, 1015, alpha=a)
            sc = 1.0
            if hl: sc = 1 + 0.12 * (1 - ease_out(prog(t, 38.4, 0.4)))
            paste(fr, text_img(res, "pf7", 64, GOLD_L, glow=(130, 90, 20) if hl else None), x + dx, 1110, alpha=a, scale=sc)
        # VS divider
        av = ease_out(prog(t, 35.6, 0.3)) * (1 - sout)
        paste(fr, text_img("VS", "cinzel9", 48, SILVER), W / 2, 960, alpha=av)
        a2 = ease_out(prog(t, 36.38, 0.3)) * (1 - sout)
        paste(fr, text_img("insultar o humillar en público", "pfi", 42, WHITE), W / 2, 1300, alpha=a2)
    if t >= 39.25:
        a = ease_out(prog(t, 39.32, 0.4))
        paste(fr, panel(960, 560, border=GOLD), W / 2, 1050, alpha=a, scale=lerp(0.9, 1, a))
        paste(fr, text_img("LA PENA", "mont8", 40, SILVER, tracking=8), W / 2, 830, alpha=a)
        v1 = counter_val(t, 40.2, 15, 0.45); a1 = ease_out(prog(t, 40.2, 0.25))
        paste(fr, big_number_img(str(v1), 170), 280, 975, alpha=a1, scale=lerp(1.5, 1, a1))
        paste(fr, text_img("DÍAS", "mont9", 56, WHITE), 280, 1085, alpha=ease_out(prog(t, 40.66, 0.3)))
        paste(fr, text_img("A", "mont9", 70, WHITE), W / 2, 985, alpha=ease_out(prog(t, 41.04, 0.25)))
        v2 = counter_val(t, 41.28, 1, 0.2); a2 = ease_out(prog(t, 41.28, 0.25))
        paste(fr, big_number_img(str(v2), 170), 780, 975, alpha=a2, scale=lerp(1.5, 1, a2))
        paste(fr, text_img("AÑO", "mont9", 56, WHITE), 780, 1085, alpha=ease_out(prog(t, 41.4, 0.3)))
        a3 = ease_out(prog(t, 42.48, 0.35))
        paste(fr, text_img("+ MULTA", "mont9", 64, GOLD_L, glow=(130, 90, 20), tracking=3), W / 2, 1195, alpha=a3, scale=lerp(1.3, 1, a3))
        a4 = ease_out(prog(t, 43.42, 0.35))
        paste(fr, text_img("O AMBAS", "mont9", 52, WHITE, tracking=4), W / 2, 1270, alpha=a4)
    return fr

def scene_extors(fr, t):
    # red accent line
    pulse = 1 - prog(t, 44.56, 0.6)
    if pulse > 0:
        fr.alpha_composite(Image.new("RGBA", (W, H), RED + (int(70 * pulse),)))
    draw_tag(fr, t, 44.6, "ART. 209", "DIFAMACIÓN EXTORSIVA", 520, accent=(205, 50, 55))
    bout = ease_io(prog(t, 53.8, 0.4))
    if t >= 45.6 and bout < 1:
        a = ease_out(prog(t, 45.68, 0.4)) * (1 - bout)
        paste(fr, icon_badge("lock", 200, ring=(205, 60, 65)), 360, 760, alpha=a, scale=lerp(0.6, 1, a))
        a_ = ease_out(prog(t, 46.0, 0.4)) * (1 - bout)
        paste(fr, icon_badge("money", 200, ring=(205, 60, 65)), 720, 760, alpha=a_, scale=lerp(0.6, 1, a_))
        items = [("PUBLICAR algo de alguien", 46.28), ("o AMENAZAR con publicarlo", 47.88), ("para sacarle DINERO o un FAVOR", 49.26)]
        for k, (txt, t0) in enumerate(items):
            p = ease_out(prog(t, t0, 0.4)) * (1 - bout)
            y = 960 + k * 100
            col = GOLD_L if k == 2 else WHITE
            paste(fr, text_img(txt, "mont8", 46, col), W / 2 + (1 - p) * 80, y, alpha=p)
        a2 = ease_out(prog(t, 52.14, 0.4)) * (1 - bout)
        paste(fr, text_img("= DIFAMACIÓN EXTORSIVA", "mont9", 54, (235, 80, 80), glow=(120, 10, 10)), W / 2, 1300, alpha=a2, scale=lerp(1.3, 1, a2))
    if t >= 53.8:
        a = ease_out(prog(t, 54.0, 0.4))
        paste(fr, panel(960, 600, border=(205, 60, 65), bw=4), W / 2, 1060, alpha=a, scale=lerp(0.9, 1, a))
        change = prog(t, 59.36, 0.3)
        out1 = ease_io(prog(t, 57.2, 0.3))
        # first figure: 5 A 10 AÑOS + PRISIÓN MAYOR
        if change < 1:
            k = 1 - change
            v1 = counter_val(t, 54.76, 5, 0.3); a1 = ease_out(prog(t, 54.7, 0.25))
            v2 = counter_val(t, 55.32, 10, 0.35); a2 = ease_out(prog(t, 55.3, 0.25))
            y = lerp(1000, 940, out1)
            paste(fr, big_number_img(str(v1), 210), 290, y, alpha=a1 * k, scale=lerp(1.5, 1, a1) * lerp(1, .8, out1))
            paste(fr, text_img("A", "mont9", 80, WHITE), W / 2, y + 10, alpha=a2 * k)
            paste(fr, big_number_img(str(v2), 210), 770, y, alpha=a2 * k, scale=lerp(1.5, 1, a2) * lerp(1, .8, out1))
            a3 = ease_out(prog(t, 55.6, 0.3)) * k
            paste(fr, text_img("AÑOS", "mont9", 66, WHITE, tracking=4), W / 2, lerp(1150, 1065, out1), alpha=a3)
            a4 = ease_out(prog(t, 56.1, 0.35)) * k
            paste(fr, text_img("PRISIÓN MAYOR", "cinzel9", 72, (240, 90, 90), glow=(120, 10, 10), tracking=4), W / 2, lerp(1260, 1160, out1), alpha=a4, scale=lerp(1.3, 1, a4))
            a5 = ease_out(prog(t, 57.6, 0.35)) * k
            paste(fr, icon_badge("people", 170, ring=(205, 60, 65)), 340, 1290, alpha=a5, scale=ease_back(prog(t, 57.6, 0.4)) if a5 > 0 else 1)
            paste(fr, text_img("2 o más personas", "mont8", 44, WHITE), 690, 1290, alpha=a5)
        if t >= 59.3:
            p = prog(t, 59.36, 0.22)
            shake = (1 - prog(t, 59.5, 0.5)) * 14
            r = random.Random(int(t * 30))
            paste(fr, big_number_img("10", 340), W / 2 + r.uniform(-shake, shake), 990 + r.uniform(-shake, shake), alpha=ease_out(p), scale=lerp(2.4, 1, ease_out(p)))
            paste(fr, text_img("AÑOS", "mont9", 110, WHITE, tracking=8), W / 2, 1210, alpha=ease_out(prog(t, 59.64, 0.25)))
            fl = 1 - prog(t, 59.36, 0.3)
            if fl > 0: fr.alpha_composite(Image.new("RGBA", (W, H), (255, 220, 200, int(110 * fl))))
    return fr

@lru_cache(None)
def fact_card(art, l1, l2, ic, photo_name=None):
    w, h = 940, 440 if photo_name is None else 780
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.alpha_composite(rrect((w, h), 26, fill=(9, 18, 38, 232), outline=SILVER + (255,), width=4))
    y = 40
    if photo_name:
        ph = Image.open(f"{PH}/{photo_name}").convert("RGB")
        pw = w - 80; phh = 330
        sc = max(pw / ph.width, phh / ph.height); ph = ph.resize((int(ph.width * sc), int(ph.height * sc)), Image.LANCZOS)
        ph = ph.crop(((ph.width - pw) // 2, (ph.height - phh) // 2, (ph.width - pw) // 2 + pw, (ph.height - phh) // 2 + phh)).convert("RGBA")
        m = rrect((pw, phh), 16, fill=(255, 255, 255, 255)).getchannel("A"); ph.putalpha(m)
        im.alpha_composite(ph, (40, 40))
        im.alpha_composite(rrect((pw, phh), 16, outline=SILVER + (255,), width=3), (40, 40))
        y = 40 + phh + 20
    badge = icon_badge(ic, 150)
    im.alpha_composite(badge, (40 - (badge.width - 150) // 2, y + 20 - (badge.height - 150) // 2))
    tg = text_img(art, "mont9", 34, GOLD_L, shadow=False, tracking=3)
    im.alpha_composite(tg, (215 - 27, y + 20 - 27))
    f = font("mont8", 50); words = (l1).split(" "); lines, cur = [], ""
    for wd in words:
        if f.getlength((cur + " " + wd).strip()) > w - 260: lines.append(cur); cur = wd
        else: cur = (cur + " " + wd).strip()
    lines.append(cur)
    yy = y + 80
    for ln in lines:
        ti = text_img(ln, "mont8", 50, WHITE, shadow=False); im.alpha_composite(ti, (215 - 35, yy - 35)); yy += 62
    if l2:
        for ln in l2.split("\n"):
            ti = text_img(ln, "pfi", 38, SILVER, shadow=False); im.alpha_composite(ti, (215 - 29, yy - 29 + 6)); yy += 50
    return shadowed(im, 24, 12, 190)

def scene_facts(fr, t):
    a0 = ease_out(prog(t, 60.62, 0.3))
    o0 = 1 - prog(t, 64.4, 0.3)
    oj = rrect((230, 90), 16, fill=GOLD + (255,))
    ImageDraw.Draw(oj).text((115, 47), "¡OJO!", font=font("mont9", 54), fill=NAVY2, anchor="mm")
    paste(fr, shadowed(oj, 10, 5), W / 2, 540, alpha=a0 * o0, scale=lerp(1.6, 1, a0))
    c1 = ease_out(prog(t, 61.64, 0.45)); c1o = ease_io(prog(t, 64.5, 0.4))
    if c1 > 0 and c1o < 1:
        paste(fr, fact_card("ART. 212", "Las empresas también responden", "pueden responder penalmente\n(personas jurídicas)", "building"), W / 2 - c1o * 1100, 1000 + (1 - c1) * 200, alpha=c1)
    c2 = ease_out(prog(t, 64.64, 0.45))
    if c2 > 0:
        paste(fr, fact_card("ART. 211", "No aplica:", "discursos en el Congreso\nni escritos en juicios", "x", "foto7_congreso.jpg"), W / 2 + (1 - c2) * 1100, 1060, alpha=c2)
    return fr

@lru_cache(None)
def poll_sticker():
    w, h = 820, 430
    im = rrect((w, h), 40, fill=(255, 255, 255, 250))
    return im

def grad_text(txt, fname, size):
    f = font(fname, size)
    tw = int(f.getlength(txt)) + 20; asc, desc = f.getmetrics()
    m = Image.new("L", (tw, asc + desc + 10), 0); ImageDraw.Draw(m).text((10, 5), txt, font=f, fill=255)
    g = np.zeros((m.height, tw, 4), np.uint8)
    x = np.linspace(0, 1, tw)[None, :]
    c1 = np.array([248, 160, 50]); c2 = np.array([220, 40, 140]); c3 = np.array([120, 60, 230])
    col = np.where(x[..., None] < .5, c1 + (c2 - c1) * (x[..., None] * 2), c2 + (c3 - c2) * ((x[..., None] - .5) * 2))
    g[..., :3] = np.broadcast_to(col, (m.height, tw, 3)); g[..., 3] = np.asarray(m)
    return Image.fromarray(g, "RGBA")

def scene_close(fr, t):
    # 69.3 -> 73.0 : piénsalo dos veces
    o = 1 - prog(t, 72.9, 0.3)
    a = ease_out(prog(t, 69.4, 0.4)) * o
    paste(fr, text_img("ANTES DE PUBLICAR,", "mont9", 70, WHITE, tracking=2), W / 2, 880 + (1 - a) * 30, alpha=a)
    a2 = ease_out(prog(t, 71.82, 0.35)) * o
    paste(fr, text_img("PIÉNSALO", "cinzel9", 120, GOLD_L, glow=(140, 100, 20), tracking=4), W / 2, 1010, alpha=a2, scale=lerp(1.3, 1, a2))
    a3 = ease_out(prog(t, 72.14, 0.3)) * o
    paste(fr, text_img("DOS VECES", "cinzel9", 120, GOLD_L, glow=(140, 100, 20), tracking=4), W / 2, 1140, alpha=a3, scale=lerp(1.3, 1, a3))
    # 73.16 poll
    if t >= 73.0 and t < 76.3:
        p = prog(t, 73.1, 0.45); a = ease_back(p)
        out = ease_io(prog(t, 75.75, 0.4))
        st = Image.new("RGBA", (820, 430), (0, 0, 0, 0))
        st.alpha_composite(poll_sticker())
        q = grad_text("¿SABÍAS ESTO?", "mont9", 64)
        st.alpha_composite(q, ((820 - q.width) // 2, 40))
        vote = prog(t, 74.5, 0.6); v = ease_out(vote)
        for k, (lab, pct) in enumerate((("SÍ", 31), ("NO", 69))):
            y = 160 + k * 125
            st.alpha_composite(rrect((740, 100), 22, fill=(238, 239, 243, 255)), (40, y))
            if v > 0:
                bw = max(44, int(740 * pct / 100 * v))
                col = (150, 70, 230, 255) if k == 1 else (210, 214, 222, 255)
                st.alpha_composite(rrect((bw, 100), 22, fill=col), (40, y))
            d = ImageDraw.Draw(st)
            tc = (255, 255, 255) if (k == 1 and v > .5) else (40, 40, 60)
            if v > 0:
                d.text((80, y + 50), lab, font=font("mont9", 46), fill=tc, anchor="lm")
                d.text((740, y + 50), f"{int(pct * v)}%", font=font("mont9", 42), fill=(40, 40, 60) if k == 0 else (60, 30, 110), anchor="rm")
            else:
                d.text((410, y + 50), lab, font=font("mont9", 50), fill=(40, 40, 60), anchor="mm")
        paste(fr, shadowed(st, 26, 14, 190), W / 2, 980 - out * 60, alpha=min(1, p * 2) * (1 - out), scale=a * (1 - .1 * out))
        # tap ripple on NO
        tp = prog(t, 74.3, 0.5)
        if 0 < tp < 1:
            r = int(30 + 90 * tp)
            rp = Image.new("RGBA", (2 * r + 4, 2 * r + 4), (0, 0, 0, 0))
            ImageDraw.Draw(rp).ellipse((2, 2, 2 * r + 2, 2 * r + 2), outline=(255, 255, 255, int(255 * (1 - tp))), width=6)
            paste(fr, rp, W / 2 + 120, 980 - 215 + 285 + 50)
        a4 = ease_out(prog(t, 74.26, 0.35)) * (1 - out)
        paste(fr, text_img("Déjamelo en los comentarios", "pfi", 46, WHITE), W / 2, 1290, alpha=a4)
    return fr

# ---------------------------------------------------------------- outro (logo)
@lru_cache(None)
def outro_bg():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W / 2) / W) ** 2 + ((y - 840) / H) ** 2)
    k = np.clip(r / 0.75, 0, 1)
    c1 = np.array([24, 42, 76], np.float32); c2 = np.array(NAVY2, np.float32)
    a = c1 * (1 - k[..., None]) + c2 * k[..., None]
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")

@lru_cache(None)
def logo_disc(sz):
    return Image.open(f"{S}/work/logo_disc.png").resize((sz, sz), Image.LANCZOS)

def silver_ring(R, width, rot, sweep=1.0):
    ss = 2; s = (R * 2 + 40) * ss
    y, x = np.mgrid[0:s, 0:s].astype(np.float32)
    cx = cy = s / 2
    dx, dy = x - cx, y - cy
    r = np.sqrt(dx * dx + dy * dy) / ss
    ang = (np.degrees(np.arctan2(dy, dx)) + 360) % 360
    band = np.clip(1 - np.abs(r - R) / (width / 2), 0, 1)
    band = np.clip(band * 3, 0, 1)
    # metallic: conic highlights rotating
    th = np.radians(ang - rot)
    lum = 0.55 + 0.25 * np.cos(2 * th) + 0.35 * np.clip(np.cos(th), 0, 1) ** 8
    edge = np.clip(1 - np.abs(r - R) / (width / 2), 0, 1)
    lum = lum * (0.7 + 0.3 * edge)
    a = np.zeros((s, s, 4), np.float32)
    base = np.array([200, 205, 214], np.float32)
    a[..., :3] = np.clip(base[None, None] * lum[..., None] * 1.15, 0, 255)
    vis = ((ang - 270) % 360) <= sweep * 360 + 0.01
    a[..., 3] = band * 255 * vis
    im = Image.fromarray(a.astype(np.uint8), "RGBA")
    return im.resize((s // ss, s // ss), Image.LANCZOS)

def scene_outro(t):
    fr = outro_bg().copy()
    # glow rays
    p = prog(t, 75.85, 0.9)
    R = 330
    cx, cy = W / 2, 840
    gl = ease_out(prog(t, 76.2, 0.8))
    if gl > 0:
        g = Image.new("RGBA", (900, 900), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((90, 90, 810, 810), fill=GOLD + (int(70 * gl),))
        paste(fr, g.filter(ImageFilter.GaussianBlur(70)), cx, cy)
    ring_p = ease_io(prog(t, 75.85, 1.0))
    rot = (t - 75.85) * 140 + 200
    if ring_p > 0:
        paste(fr, silver_ring(R, 26, rot, ring_p), cx, cy)
    dp = ease_out(prog(t, 76.25, 0.7))
    if dp > 0:
        disc = logo_disc(2 * R - 24)
        paste(fr, disc, cx, cy, alpha=dp, scale=lerp(0.6, 1, ease_back(prog(t, 76.25, 0.7), 1.2)))
    # shine sweep across disc
    sw = prog(t, 77.3, 0.9)
    if 0 < sw < 1:
        sh = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
        dsh = ImageDraw.Draw(sh)
        x0 = -R + sw * 4 * R
        dsh.polygon([(x0, 0), (x0 + 90, 0), (x0 - 200 + 90, 2 * R), (x0 - 200, 2 * R)], fill=(255, 245, 220, 70))
        m = Image.new("L", sh.size, 0); ImageDraw.Draw(m).ellipse((12, 12, 2 * R - 12, 2 * R - 12), fill=255)
        sh.putalpha(ImageChops.multiply(sh.getchannel("A"), m))
        paste(fr, sh.filter(ImageFilter.GaussianBlur(6)), cx, cy)
    # line + slogan + handle
    lp = ease_out(prog(t, 76.6, 0.6))
    if lp > 0:
        ln = Image.new("RGBA", (int(520 * lp) + 2, 4), GOLD + (255,))
        paste(fr, ln, cx, 1255)
    a1 = ease_out(prog(t, 76.24, 0.5))
    paste(fr, text_img("Sandoval Legal:", "pf7", 62, GOLD_L, glow=(110, 80, 20)), cx, 1335 + (1 - a1) * 20, alpha=a1)
    a2 = ease_out(prog(t, 76.98, 0.5))
    paste(fr, text_img("donde la ley se entiende", "pfi", 62, GOLD_L, glow=(110, 80, 20)), cx, 1415 + (1 - a2) * 20, alpha=a2)
    a3 = ease_out(prog(t, 77.85, 0.5))
    paste(fr, text_img("@sandoval_legal", "mont8", 52, WHITE, tracking=2), cx, 1530, alpha=a3, scale=lerp(1.2, 1, a3))
    # silver frame
    fo = frame_overlay()
    return fr

# ---------------------------------------------------------------- timeline
# (start, end, photo, kwargs)
PHOTOS = [
    (0.0, 6.0, "foto1_escribiendo.jpg", dict(zoom=(1.12, 1.0), pan=(0, -1), focus_y=0.55)),
    (6.0, 13.6, "foto2_celular.jpg", dict(zoom=(1.0, 1.12), pan=(1, 0), focus=0.62)),
    (13.6, 24.8, "foto3_live.jpg", dict(zoom=(1.0, 1.1), pan=(-1, 0), focus=0.55)),
    (24.8, 33.1, "foto3b_live_alterna.jpg", dict(zoom=(1.12, 1.0), pan=(0, 1))),
    (33.1, 39.3, "foto4_discusion.jpg", dict(zoom=(1.0, 1.1), pan=(0, -1))),
    (39.3, 44.5, "foto4b_discusion_alterna.jpg", dict(zoom=(1.1, 1.0), pan=(1, 0), focus=0.42)),
    (44.5, 51.6, "foto5_sobre_dinero.jpg", dict(zoom=(1.0, 1.12), pan=(0, 1), dark=0.55, red=True)),
    (51.6, 60.5, "foto5b_sobre_alterna.jpg", dict(zoom=(1.12, 1.0), pan=(-1, 0), focus=0.45, dark=0.58, red=True)),
    (60.5, 64.6, "foto6_mazo.jpg", dict(zoom=(1.0, 1.1), pan=(0, 0), focus=0.5)),
    (64.6, 69.3, "foto7_congreso.jpg", dict(zoom=(1.0, 1.08), pan=(1, 0), blur=4)),
    (69.3, 75.9, "extra_escribiendo_post.jpg", dict(zoom=(1.0, 1.12), pan=(1, 0), focus=0.4)),
]
XF = 0.35  # crossfade

def bg_at(t):
    def render(i):
        s, e, nm, kw = PHOTOS[i]
        kw = dict(kw); red = kw.pop("red", False)
        im = ken_burns(nm, t, s, e, **kw)
        im.alpha_composite(vignette(0.9, red))
        return im
    idx = [i for i, (s, e, *_ ) in enumerate(PHOTOS) if s - XF <= t < e + 0.0001]
    if not idx: idx = [len(PHOTOS) - 1]
    cur = idx[-1]
    im = render(cur)
    s = PHOTOS[cur][0]
    if cur > 0 and t < s + XF:
        prev = render(cur - 1)
        k = ease_io(prog(t, s - 0.02, XF))
        im = Image.blend(prev, im, k)
    return im

SCENES = [(0, 6.0, scene_hook), (6.0, 13.6, scene_context), (13.6, 33.1, scene_difam), (33.1, 44.5, scene_injuria),
          (44.5, 60.5, scene_extors), (60.5, 69.3, scene_facts), (69.3, 76.3, scene_close)]

def render_frame(t):
    if t >= 76.15:
        fr = scene_outro(t)
        # brief crossfade from previous
        return fr
    fr = bg_at(t)
    for s, e, fn in SCENES:
        if s - 0.001 <= t < e + 0.25:
            if t >= e:  # fade-out tail
                tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                tmp2 = fn(tmp, t)
                fr.alpha_composite(with_alpha(tmp2, 1 - prog(t, e, 0.25)))
            else:
                fr = fn(fr, t)
    # scene transition flash / light leak
    for s, *_ in SCENES[1:]:
        k = 1 - abs(t - s) / 0.18
        if k > 0:
            fr.alpha_composite(Image.new("RGBA", (W, H), (255, 236, 200, int(60 * k))))
    fr.alpha_composite(frame_overlay())
    draw_subs(fr, t)
    if 75.75 <= t < 76.15:  # fade to outro
        k = prog(t, 75.75, 0.4)
        fr = Image.blend(fr, scene_outro(t), ease_io(k))
    return fr

def main():
    if sys.argv[1] == "still":
        for ts in sys.argv[2:]:
            render_frame(float(ts)).convert("RGB").save(f"{S}/chk/still_{float(ts):05.2f}.jpg", quality=88)
        return
    a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for f in range(a, b):
        p.stdin.write(render_frame(f / FPS).convert("RGB").tobytes())
    p.stdin.close(); p.wait()

if __name__ == "__main__":
    main()
