"""Frame renderer for the CPI night video. Usage: video.py <part> <nparts> | video.py --still t1,t2,..."""
import sys, subprocess, math, functools
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from plan import *

ANTON = f"{FONTS}/Anton-Regular.ttf"
OSWALD = f"{FONTS}/OswaldOswald.ttf"
POPPINS = f"{FONTS}/Poppins-Bold.ttf"
MONO = f"{FONTS}/SpaceMono-Bold.ttf"
REDf = np.array(RED, np.float32) / 255
N_MAIN = int(round(MAIN_LEN * FPS))
N_CIERRE = int(round(CIERRE_LEN * FPS))


def font(path, size, wght=None):
    f = ImageFont.truetype(path, size)
    if wght:
        try: f.set_variation_by_axes([wght])
        except Exception: pass
    return f


# ---------------------------------------------------------------- grading
def grade(path, bw=False, red_boost=1.0):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    L = 0.299 * R + 0.587 * G + 0.114 * B
    Lc = np.clip((L - 0.03) / 0.94, 0, 1) ** 1.18
    Lc = Lc * Lc * (3 - 2 * Lc) * 0.55 + Lc * 0.45          # mild S-curve
    if bw:
        out = Lc[..., None] * np.array([0.93, 0.96, 1.02], np.float32)
        return np.clip(out * 0.95, 0, 1)
    sh, mid, hi = (np.array(c, np.float32) for c in ((0.015, 0.025, 0.06), (0.15, 0.22, 0.36), (0.80, 0.86, 0.95)))
    x = Lc[..., None]
    tone = np.where(x < 0.5, sh + (mid - sh) * (x / 0.5), mid + (hi - mid) * ((x - 0.5) / 0.5))
    desat = (a * 0.35 + L[..., None] * 0.65) * np.array([0.88, 0.96, 1.12], np.float32)
    out = tone * 0.62 + desat * 0.38
    redness = np.clip((R - np.maximum(G, B)) * 2.6 - 0.12, 0, 1)[..., None] * red_boost
    redcol = REDf * (0.35 + 0.95 * x)
    out = out * (1 - redness * 0.85) + redcol * redness * 0.85
    return np.clip(out * 0.9, 0, 1)


@functools.lru_cache(None)
def src(name, bw=False):
    return (grade(f"{IMG}/{name}.jpg", bw, {"balanza": 0.25, "mazo": 0.6}.get(name, 1.0)) * 255).astype(np.uint8)


@functools.lru_cache(None)
def src_blur(name):
    s = src(name)
    h, w = s.shape[:2]; k = 400 / max(h, w)
    small = cv2.resize(s, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), 9)
    return (small.astype(np.float32) * 0.42).astype(np.uint8)


def kb(img, p, outw, outh, z0=1.0, z1=1.12, c0=(0.5, 0.5), c1=None):
    """Ken Burns: cover (outw,outh) from img at zoom lerp(z0,z1,p), centre lerp(c0,c1) (normalised)."""
    c1 = c1 or c0
    h, w = img.shape[:2]
    z = z0 + (z1 - z0) * p
    s = max(outw / w, outh / h) * z
    cx = (c0[0] + (c1[0] - c0[0]) * p) * w; cy = (c0[1] + (c1[1] - c0[1]) * p) * h
    hw, hh = outw / (2 * s), outh / (2 * s)
    cx = min(max(cx, hw), w - hw); cy = min(max(cy, hh), h - hh)
    M = np.float32([[s, 0, outw / 2 - s * cx], [0, s, outh / 2 - s * cy]])
    return cv2.warpAffine(img, M, (outw, outh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def to_f(a):
    return a.astype(np.float32) / 255


# ---------------------------------------------------------------- RGBA helpers
def paste(frame, rgba, x, y, opacity=1.0):
    """alpha-composite uint8 RGBA (numpy) onto float frame at (x,y), clipped."""
    h, w = rgba.shape[:2]
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    sub = rgba[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32) / 255
    al = sub[..., 3:4] * opacity
    frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - al) + sub[..., :3] * al


def pil_rgba(im):
    return np.asarray(im.convert("RGBA"))


@functools.lru_cache(None)
def text_img(text, path, size, color=(255, 255, 255), stroke=0, stroke_col=(0, 0, 0), spacing=0, wght=None, shadow=0):
    f = font(path, size, wght)
    bbox = f.getbbox(text, stroke_width=stroke)
    tw = bbox[2] - bbox[0] + spacing * len(text) + 2 * shadow + 8; th = bbox[3] - bbox[1] + 2 * shadow + 8
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = -bbox[0] + shadow + 4, -bbox[1] + shadow + 4
    if spacing:
        x = ox
        for ch in text:
            d.text((x, oy), ch, font=f, fill=color + (255,), stroke_width=stroke, stroke_fill=stroke_col)
            x += f.getlength(ch) + spacing
    else:
        d.text((ox, oy), text, font=f, fill=color + (255,), stroke_width=stroke, stroke_fill=stroke_col)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(shadow)))
        sh = Image.composite(Image.new("RGBA", im.size, (0, 0, 0, 230)), Image.new("RGBA", im.size, (0, 0, 0, 0)), sh.getchannel("A"))
        im = Image.alpha_composite(sh, im)
    return pil_rgba(im)


def grunge(rgba, seed, amount=0.35):
    r = np.random.default_rng(seed)
    h, w = rgba.shape[:2]
    n = cv2.resize(r.random((h // 6 + 1, w // 6 + 1)).astype(np.float32), (w, h))
    fine = r.random((h, w)).astype(np.float32)
    m = np.clip((n * 0.7 + fine * 0.3 - amount) * 3.5, 0, 1)
    out = rgba.copy(); out[..., 3] = (out[..., 3] * (0.25 + 0.75 * m)).astype(np.uint8)
    return out


@functools.lru_cache(None)
def stamp_img(lines, size=110, rot=-8, seed=1, box=True):
    lines = lines.split("|")
    f = font(ANTON, size)
    widths = [f.getbbox(l)[2] - f.getbbox(l)[0] for l in lines]
    lh = int(size * 1.15)
    pad = 34
    w = max(widths) + pad * 2; h = lh * len(lines) + pad * 2 - int(size * 0.1)
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    col = RED + (255,)
    if box:
        d.rounded_rectangle((20, 20, 20 + w, 20 + h), 14, outline=col, width=10)
        d.rounded_rectangle((36, 36, 4 + w, 4 + h), 8, outline=col, width=3)
    for i, l in enumerate(lines):
        bb = f.getbbox(l)
        d.text((20 + (w - widths[i]) / 2 - bb[0], 20 + pad + i * lh - bb[1] - int(size * 0.05)), l, font=f, fill=col)
    im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    return grunge(pil_rgba(im), seed, 0.28)


@functools.lru_cache(None)
def x_mark(size=300, seed=3):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    m = size * 0.12; wdt = int(size * 0.13)
    d.line((m, m, size - m, size - m), fill=RED + (255,), width=wdt)
    d.line((size - m, m, m, size - m), fill=RED + (255,), width=wdt)
    return grunge(pil_rgba(im), seed, 0.25)


def slam(frame, rgba, cx, cy, t, t0, opacity=0.95):
    """Stamp slam-in animation: big -> 1.0 in 0.12 s."""
    if t < t0: return
    k = min(1, (t - t0) / 0.12)
    sc = 1.0 + 0.9 * (1 - k) ** 2
    a = opacity * min(1, k * 1.6)
    img = rgba if sc == 1 else cv2.resize(rgba, None, fx=sc, fy=sc, interpolation=cv2.INTER_LINEAR)
    paste(frame, img, int(cx - img.shape[1] / 2), int(cy - img.shape[0] / 2), a)


# ---------------------------------------------------------------- static layers
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.5) / (H * 0.6)) ** 2)
VIGNETTE = (1 - 0.88 * np.clip((_r - 0.42) / 0.62, 0, 1) ** 1.5)
VIGNETTE *= 1 - 0.45 * np.clip(1 - yy / 560, 0, 1) ** 1.3          # darker top for subtitles
VIGNETTE *= 1 - 0.35 * np.clip((yy - 1550) / 370, 0, 1)              # darker bottom for the badge
VIGNETTE = VIGNETTE[..., None].astype(np.float32)


def glow(cx, cy, rad):
    g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * rad ** 2)))
    return (g[..., None] * REDf).astype(np.float32)

LEAKS = [glow(W * 1.05, H * 0.08, 520), glow(-W * 0.05, H * 0.9, 560), glow(W * 1.1, H * 0.75, 520), glow(-W * 0.1, H * 0.2, 500)]
_gr = np.random.default_rng(11)
GRAIN = [cv2.resize(_gr.standard_normal((H // 2, W // 2)).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
         for _ in range(10)]

GRID = np.zeros((H, W), np.float32)
GRID[::60, :] = 1; GRID[:, ::60] = 1
GRID = cv2.GaussianBlur(GRID, (3, 3), 0)[..., None]


def static_noise(h, w, rng, level=0.35):
    n = rng.random((h // 3 + 1, w // 3 + 1)).astype(np.float32)
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_NEAREST)
    bands = (rng.random((h // 3 + 1, 1)) > 0.93).astype(np.float32)
    bands = cv2.resize(bands, (1, h), interpolation=cv2.INTER_NEAREST)[:, :1]
    return (n * level + bands * 0.25)[..., None] * np.array([0.8, 0.85, 1.0], np.float32)


# ---------------------------------------------------------------- scene builders
def full(name, z0=1.02, z1=1.14, c0=(0.5, 0.5), c1=None, bw=False):
    def f(t, p, rng):
        return to_f(kb(src(name, bw), p, W, H, z0, z1, c0, c1))
    return f


PY0, PH = 560, 900


def brackets(frame, y0, h):
    L, th, m = 64, 6, 22
    for (x, y, dx, dy) in ((m, y0 + m, 1, 1), (W - m, y0 + m, -1, 1), (m, y0 + h - m, 1, -1), (W - m, y0 + h - m, -1, -1)):
        xa, xb = sorted((x, x + dx * L)); ya, yb = sorted((y, y + dy * L))
        frame[y:y + th if dy > 0 else y, :] if False else None
        frame[min(y, y + dy * th):max(y, y + dy * th), xa:xb] = REDf
        frame[ya:yb, min(x, x + dx * th):max(x, x + dx * th)] = REDf
    frame[y0:y0 + 3, :] = frame[y0:y0 + 3, :] * 0.4 + REDf * 0.6
    frame[y0 + h - 3:y0 + h, :] = frame[y0 + h - 3:y0 + h, :] * 0.4 + REDf * 0.6


def panel(name, z0=1.0, z1=1.12, c0=(0.5, 0.5), c1=None, y0=PY0, h=PH, extra=None):
    def f(t, p, rng):
        bg = cv2.resize(kb(src_blur(name), p, W // 4, H // 4, 1.1, 1.2), (W, H), interpolation=cv2.INTER_LINEAR)
        frame = to_f(bg)
        frame[y0:y0 + h] = to_f(kb(src(name), p, W, h, z0, z1, c0, c1))
        brackets(frame, y0, h)
        if extra: extra(frame, t, p, rng)
        return frame
    return f


def stack(rows, bw, xs=None, hold_static=True):
    """rows: list of (name, focus, appear_time). xs: list of X-stamp times per row."""
    hgt = [(0, 636), (642, 636), (1284, 636)]
    def f(t, p, rng):
        frame = np.zeros((H, W, 3), np.float32)
        for k, ((name, foc, ta), (y, hh)) in enumerate(zip(rows, hgt)):
            if t >= ta:
                pp = min(1, (t - ta) / 6)
                frame[y:y + hh] = to_f(kb(src(name, bw), pp, W, hh, 1.0 if bw else 1.15, 1.09 if bw else 1.24, foc))
                if t - ta < 0.1:  # flash on reveal
                    frame[y:y + hh] = np.clip(frame[y:y + hh] + (0.1 - (t - ta)) * 6, 0, 1)
            elif hold_static:
                frame[y:y + hh] = static_noise(hh, W, rng, 0.22)
            if xs and t >= xs[k]:
                slam(frame, x_mark(330, 3 + k), W // 2, y + hh // 2, t, xs[k], 0.9 if t < ws(86) else 0.35)
        frame[636:642] = REDf * 0.9; frame[1278:1284] = REDf * 0.9
        return frame
    return f


def black(t, p, rng):
    return np.zeros((H, W, 3), np.float32)


# --- overlays
def location_card(t0):
    l1, l2 = "SHENZHEN, CHINA", "19 NOV"
    def ex(frame, t, p, rng):
        dt = t - t0
        n1 = int(np.clip((dt - 0.25) / 0.075 + 1, 0, len(l1))); n2 = int(np.clip((dt - 1.5) / 0.075 + 1, 0, len(l2)))
        y = 1380
        if dt > 0.1:
            frame[y - 24:y - 18, 70:70 + min(940, int((dt - 0.1) * 3000))] = REDf
        if n1:
            paste(frame, text_img(l1[:n1], MONO, 64, shadow=6), 66, y)
        if n2:
            paste(frame, text_img(l2[:n2], MONO, 54, color=(214, 40, 40), shadow=6), 66, y + 96)
        cur_on = int(t * 2.5) % 2 == 0
        if cur_on and dt < 4:
            line = (l2[:n2] if n2 else l1[:n1])
            fs = 54 if n2 else 64
            cx = 70 + int(font(MONO, fs).getlength(line)) + 10; cy = y + (96 if n2 else 0) + 14
            frame[cy:cy + fs - 4, cx:cx + int(fs * 0.55)] = REDf
    return ex


def stamps(spec):
    """spec: list of (text, t0, cx, cy, size, rot)"""
    def ex(frame, t, p, rng):
        for i, (txt, t0, cx, cy, sz, rot) in enumerate(spec):
            slam(frame, stamp_img(txt, sz, rot, 10 + i), cx, cy, t, t0)
    return ex


def reticle(frame, t, p, rng):
    cx, cy = int(W * 0.5), PY0 + int(PH * 0.42)
    r = int(170 - 30 * min(1, p * 2))
    col = REDf
    cv_img = (frame * 255).astype(np.uint8)
    c = tuple(int(v) for v in RED[::-1])
    for rr, th in ((r, 4), (r + 40, 2)):
        cv2.circle(cv_img, (cx, cy), rr, (214, 40, 40), th, cv2.LINE_AA)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        cv2.line(cv_img, (cx + dx * (r - 40), cy + dy * (r - 40)), (cx + dx * (r + 70), cy + dy * (r + 70)), (214, 40, 40), 4, cv2.LINE_AA)
    frame[:] = cv_img.astype(np.float32) / 255
    if int(t * 3) % 2 == 0:
        paste(frame, text_img("● OBJETIVO", MONO, 34, color=(214, 40, 40)), cx + r - 20, cy - r - 70)


def collab_card(t0):
    capl = np.asarray(Image.open(f"{ASSETS}/logo_capital.png").convert("RGBA").resize((340, 521), Image.LANCZOS))
    sand = np.asarray(Image.open(f"{ASSETS}/logo_sandoval.png").convert("RGBA").resize((430, 430), Image.LANCZOS))
    t_cap, t_san = ws(44), ws(51)
    def f(t, p, rng):
        frame = np.ones((H, W, 3), np.float32) * np.array([0.01, 0.02, 0.05], np.float32)
        frame += GRID * np.array([0.05, 0.08, 0.15], np.float32)
        sy = int((t * 420) % (H + 200)) - 100
        frame[max(0, sy):max(0, sy + 4)] += np.array([0.08, 0.1, 0.16], np.float32)
        for tt, img, cy in ((t_cap, capl, 820), (t_san, sand, 1395)):
            if t >= tt:
                k = min(1, (t - tt) / 0.25)
                jitter = int((1 - k) * rng.integers(-30, 30))
                paste(frame, img, W // 2 - img.shape[1] // 2 + jitter, cy - img.shape[0] // 2, k)
        if t >= t_san - 0.25:
            paste(frame, text_img("×", POPPINS, 90, color=(214, 40, 40)), W // 2 - 30, 1080)
        frame[1110:1113, 120:420] = REDf * 0.7; frame[1110:1113, 660:960] = REDf * 0.7
        return frame
    return f


def members(t0):
    rows = [(165, "MÉXICO"), (166, "COLOMBIA"), (167, "BRASIL"), (168, "ARGENTINA"), (169, "REPÚBLICA DOMINICANA")]
    def f(t, p, rng):
        bg = cv2.resize(kb(src_blur("cpi_bandera"), p, W // 4, H // 4, 1.1, 1.25), (W, H))
        frame = to_f(bg) * 0.55 + GRID * np.array([0.04, 0.06, 0.12], np.float32)
        # radar sweep line
        sy = int(((t - t0) * 600) % H)
        frame[sy:sy + 3] += REDf * 0.35
        if t >= t0 + 0.15:
            paste(frame, text_img("ESTATUTO DE ROMA", MONO, 40, color=(214, 40, 40), spacing=6), 80, 560)
            paste(frame, text_img("ESTADOS PARTE · AMÉRICA LATINA", MONO, 32, color=(200, 210, 230), spacing=2), 80, 620)
            frame[690:693, 80:1000] = REDf * 0.8
        for k, (wi, name) in enumerate(rows):
            ta = ws(wi)
            if t < ta: continue
            k_a = min(1, (t - ta) / 0.15)
            y = 760 + k * 140
            last = wi == 169
            col = (214, 40, 40) if last else (255, 255, 255)
            frame[y + 28:y + 58, 80:110] = REDf
            img = text_img(name, ANTON, 92 if last else 84, color=col, shadow=4)
            paste(frame, img, 140 - int((1 - k_a) * 60), y, k_a)
        return frame
    return f


def question_split():
    tb, tp = ws(195), ws(198)
    def f(t, p, rng):
        frame = np.zeros((H, W, 3), np.float32)
        frame[0:957] = to_f(kb(src("balanza"), min(1, (t - tb) / 3), W, 957, 1.15, 1.3, (0.45, 0.42)))
        paste(frame, text_img("LA LEY", MONO, 44, color=(255, 255, 255), spacing=4, shadow=5), 60, 860)
        if t >= tp:
            frame[963:] = to_f(kb(src("tres_lideres"), min(1, (t - tp) / 3), W, 957, 1.2, 1.32, (0.5, 0.45)))
            paste(frame, text_img("LOS MÁS PODEROSOS", MONO, 44, color=(214, 40, 40), spacing=4, shadow=5), 60, 1020)
        else:
            frame[963:] = static_noise(957, W, rng, 0.2)
        frame[957:963] = REDf
        return frame
    return f


def cta():
    capl = np.asarray(Image.open(f"{ASSETS}/logo_capital.png").convert("RGBA").resize((300, 460), Image.LANCZOS))
    sand = np.asarray(Image.open(f"{ASSETS}/logo_sandoval.png").convert("RGBA").resize((380, 380), Image.LANCZOS))
    t_logo, t_c, t_s = ws(205), ws(210), ws(213)
    def f(t, p, rng):
        bg = cv2.resize(kb(src_blur("shenzhen_dia"), p, W // 4, H // 4, 1.1, 1.25), (W, H))
        frame = to_f(bg) * 0.75 + GRID * np.array([0.03, 0.05, 0.1], np.float32)
        if t < t_logo:
            q = text_img("?", ANTON, 560, color=(214, 40, 40), shadow=30)
            pulse = 0.85 + 0.15 * math.sin(t * 8)
            paste(frame, q, W // 2 - q.shape[1] // 2, 1000 - q.shape[0] // 2, pulse)
        else:
            k = min(1, (t - t_logo) / 0.25)
            for img, cx, cy, tt, handle in ((capl, 290, 990, t_c, None), (sand, 790, 990, t_s, "@sandoval_legal")):
                sc = 1 + 0.12 * max(0, 1 - abs(t - tt - 0.15) / 0.3) if t >= tt - 0.2 else 1
                im = img if sc == 1 else cv2.resize(img, None, fx=sc, fy=sc)
                paste(frame, im, cx - im.shape[1] // 2, cy - im.shape[0] // 2, k)
                if handle:
                    h_img = text_img(handle, POPPINS, 30, shadow=4)
                    paste(frame, h_img, cx - h_img.shape[1] // 2, 1205, k)
            paste(frame, text_img("×", POPPINS, 80, color=(214, 40, 40)), W // 2 - 26, 930, k)
            paste(frame, text_img("SÍGUENOS", ANTON, 70, color=(255, 255, 255), spacing=8, shadow=6), W // 2 - 190, 650, k)
        return frame
    return f


# ---------------------------------------------------------------- scene timeline
hook_rows = [("trump", (0.5, 0.3), 0.0), ("putin", (0.44, 0.33), ws(2)), ("xi", (0.56, 0.33), ws(4))]
stack2_rows = [("trump", (0.5, 0.32), 0), ("putin", (0.44, 0.3), 0), ("xi", (0.55, 0.3), 0)]
SC = [  # (start, end, fn, leak_index)
    (0.0, ws(7), stack(hook_rows, True), None),
    (ws(7), ws(14), lambda t, p, r, _f=full("shenzhen", 1.02, 1.16, (0.5, 0.55), (0.5, 0.45)), _o=location_card(ws(7)):
        (lambda fr: (_o(fr, t, p, r), fr)[1])(_f(t, p, r)), 0),
    (ws(14), ws(21), panel("tres_lideres_ilustracion", 1.0, 1.12, (0.45, 0.5), (0.55, 0.5)), 1),
    (ws(21), ws(27), panel("tres_lideres", 1.0, 1.10, (0.5, 0.5)), 2),
    (ws(27), ws(34), panel("tres_lideres", 1.35, 1.5, (0.48, 0.42), (0.52, 0.4)), 2),
    (ws(34), ws(39), panel("cpi_edificio", 1.0, 1.14, (0.35, 0.6), (0.45, 0.5)), 3),
    (ws(39), ws(53), collab_card(ws(39)), None),
    (ws(53), ws(65), panel("cpi_sala", 1.0, 1.15, (0.5, 0.45)), 0),
    (ws(65), ws(75), panel("cpi_bandera", 1.0, 1.14, (0.35, 0.4), (0.45, 0.45)), 1),
    (ws(75), ws(95), lambda t, p, r, _f=stack(stack2_rows, False, [ws(78), ws(79) + 0.12, ws(81)], False),
        _o=stamps([("FUERA DEL|ESTATUTO DE ROMA", ws(86), W // 2, 960, 100, -7)]):
        (lambda fr: (_o(fr, t, p, r), fr)[1])(_f(t, p, r)), None),
    (ws(95), we(99), panel("cpi_edificio", 1.6, 1.8, (0.14, 0.72), (0.14, 0.72)), 3),
    (we(99), ws(100), black, None),
    (ws(100), ws(109), full("balanza", 1.04, 1.2, (0.45, 0.45), (0.5, 0.5)), 2,
     ),
    (ws(109), ws(122), panel("putin", 1.0, 1.15, (0.42, 0.45), (0.4, 0.4),
                             extra=stamps([("ORDEN DE ARRESTO|VIGENTE", ws(119), W // 2, 1010, 96, 6)])), 0),
    (ws(122), ws(129), full("ucrania1", 1.04, 1.16, (0.5, 0.6), (0.5, 0.45)), 1),
    (ws(129), ws(138), full("ucrania2", 1.02, 1.16, (0.5, 0.4), (0.5, 0.55)), 3),
    (ws(138), ws(145), full("ucrania3", 1.04, 1.16, (0.4, 0.5), (0.6, 0.5)), 2),
    (ws(145), ws(150), full("mazo", 1.02, 1.18, (0.6, 0.55), (0.6, 0.6)), 1),
    (ws(150), ws(171), members(ws(150)), None),
    (ws(171), ws(181), panel("putin", 1.35, 1.5, (0.42, 0.33), (0.42, 0.33), extra=reticle), 0),
    (ws(181), ws(190), panel("cpi_sala", 1.3, 1.45, (0.5, 0.4), (0.55, 0.4)), 3),
    (ws(190), we(190), panel("tres_lideres_ilustracion", 1.1, 1.18, (0.5, 0.5)), 1),
    (we(190), ws(191), black, None),
    (ws(191), ws(195), panel("tres_lideres_ilustracion", 1.2, 1.38, (0.5, 0.48), (0.52, 0.45)), 0),
    (ws(195), ws(201), question_split(), None),
    (ws(201), MAIN_LEN + 0.01, cta(), 1),
]

# balanza scene gets the "NO ANULA NADA" stamp
_bal = SC[12][2]; _st = stamps([("NO ANULA|NADA", ws(106), W // 2, 1150, 130, -6)])
SC[12] = (SC[12][0], SC[12][1], lambda t, p, r: (lambda fr: (_st(fr, t, p, r), fr)[1])(_bal(t, p, r)), 2)
# hook: "FIRMADO" stamp on "firma"
_hk = SC[0][2]; _hs = stamps([("FIRMADO", ws(6), W // 2, 960, 150, -9)])
SC[0] = (0.0, ws(7), lambda t, p, r: (lambda fr: (_hs(fr, t, p, r), fr)[1])(_hk(t, p, r)), None)

BOOMS = [t for t, k, g in SFX if k == "boom"]
SHAKES = [t for t, k, g in SFX if k in ("boom", "stamp", "gavel")]

# ---------------------------------------------------------------- subtitles
KEY = {"hombres", "potencias", "firma", "shenzhen", "nunca", "corte", "penal", "internacional", "capital", "curioso",
       "sandoval", "legal", "jurisdicción", "inmunidad", "clave", "ninguno", "roma", "importante", "política",
       "jurídica", "anula", "arresto", "putin", "vigente", "ucrania", "presidente", "mapa", "latinoamérica",
       "república", "dominicana", "obligado", "mundo", "ley", "poderosos", "comentarios", "dos", "nada", "2023"}


def norm(w):
    return w.lower().strip("¿?¡!.,;:")


chunks, cur = [], []
for i, w in enumerate(WORDS):
    if cur:
        prev = WORDS[cur[-1]]["w"]
        txt = " ".join(WORDS[j]["w"] for j in cur + [i])
        if prev[-1] in ".,?" or len(cur) >= 4 or len(txt) > 24 or w["S"] - WORDS[cur[-1]]["E"] > 0.45:
            chunks.append(cur); cur = []
    cur.append(i)
chunks.append(cur)
CH = []
for k, c in enumerate(chunks):
    start = WORDS[c[0]]["S"]
    end = WORDS[c[-1]]["E"] + 0.5
    if k + 1 < len(chunks): end = min(end, WORDS[chunks[k + 1][0]]["S"])
    for a, b in SILENCES:
        if start < a < end: end = a
    CH.append((start, end, c))

SUB_FONT = 100


@functools.lru_cache(None)
def sub_img(ci, nvis):
    idx = CH[ci][2][:nvis]
    f = font(ANTON, SUB_FONT)
    words = [WORDS[i]["w"].upper() for i in idx]
    allw = [WORDS[i]["w"].upper() for i in CH[ci][2]]
    space = f.getlength(" ")
    # layout lines with the FULL chunk so words don't jump as they appear
    lines, line = [], []
    for j, w in enumerate(allw):
        test = line + [j]
        if sum(f.getlength(allw[q]) for q in test) + space * (len(test) - 1) > 960 and line:
            lines.append(line); line = [j]
        else:
            line = test
    lines.append(line)
    lh = int(SUB_FONT * 1.18)
    im = Image.new("RGBA", (W, lh * len(lines) + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for li, ln in enumerate(lines):
        tw = sum(f.getlength(allw[q]) for q in ln) + space * (len(ln) - 1)
        x = (W - tw) / 2
        for q in ln:
            if q < nvis:
                key = norm(allw[q]) in KEY
                d.text((x, 10 + li * lh), allw[q], font=f, fill=(RED if key else (255, 255, 255)) + (255,),
                       stroke_width=7, stroke_fill=(0, 0, 0))
            x += f.getlength(allw[q]) + space
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * 0.8)))
    return pil_rgba(Image.alpha_composite(sh, im))


def subtitles(frame, t):
    for ci, (a, b, c) in enumerate(CH):
        if a <= t < b:
            nvis = sum(1 for i in c if WORDS[i]["S"] <= t + 0.02)
            img = sub_img(ci, nvis)
            # pop on newest word: tiny vertical bump
            newest = max(WORDS[i]["S"] for i in c[:nvis])
            bump = int(max(0, 1 - (t - newest) / 0.1) * 8)
            paste(frame, img, 0, 250 - bump)
            return


# ---------------------------------------------------------------- badge
def make_badge():
    logo = Image.open(f"{ASSETS}/logo_sandoval.png").convert("RGBA").resize((128, 128), Image.LANCZOS)
    txt = Image.fromarray(text_img("En colaboración con", POPPINS, 26, shadow=4))
    im = Image.new("RGBA", (max(txt.width, 140) + 10, txt.height + 136), (0, 0, 0, 0))
    im.alpha_composite(txt, (0, 0)); im.alpha_composite(logo, (6, txt.height + 4))
    return pil_rgba(im)
BADGE = make_badge()


# ---------------------------------------------------------------- glitch
def glitch(frame, s, rng):
    out = frame.copy()
    dx = int(6 + 26 * s)
    out[:, dx:, 0] = frame[:, :-dx, 0]; out[:, :-dx, 2] = frame[:, dx:, 2]
    for _ in range(int(3 + 10 * s)):
        y = rng.integers(0, H - 10); h = int(rng.integers(6, 90)); sh = int(rng.integers(-120, 120) * s)
        out[y:y + h] = np.roll(out[y:y + h], sh, axis=1)
        if rng.random() < 0.35:
            out[y:y + h] = out[y:y + h] * 0.5 + (REDf if rng.random() < 0.6 else np.array([0.7, 0.8, 1.0], np.float32)) * 0.5 * s
    for _ in range(int(2 + 6 * s)):
        y = rng.integers(0, H); out[y:y + 2] = rng.random() * s
    return out


def render(i):
    rng = np.random.default_rng(i * 7919 + 3)
    t = i / FPS
    sc = next((s for s in SC if s[0] <= t < s[1]), SC[-1])
    p = (t - sc[0]) / max(0.001, sc[1] - sc[0])
    frame = sc[2](t, p, rng)
    is_black = sc[2] is black
    if not is_black:
        if sc[3] is not None:
            frame = frame + LEAKS[sc[3]] * (0.16 + 0.05 * math.sin(t * 1.7))
        frame = frame * VIGNETTE
    frame = frame + GRAIN[i % len(GRAIN)] * (0.045 if not is_black else 0.02)
    # boom: shake + red flash
    for tb in SHAKES:
        d = t - tb
        if 0 <= d < 0.35:
            amp = (1 - d / 0.35) ** 2
            sx, sy = int(rng.integers(-14, 15) * amp), int(rng.integers(-14, 15) * amp)
            frame = np.roll(frame, (sy, sx), axis=(0, 1))
    for tb in BOOMS:
        d = t - tb
        if 0 <= d < 0.2:
            frame = frame + REDf * 0.28 * (1 - d / 0.2)
            frame = frame * (1 + 0.25 * (1 - d / 0.2))
    for tg in GLITCH_TIMES:
        d = t - tg
        if -0.07 <= d < 0.2 and not is_black:
            frame = glitch(np.clip(frame, 0, 1), 1 - max(0, d) / 0.2, rng)
    frame = np.clip(frame, 0, 1)
    subtitles(frame, t)
    paste(frame, BADGE, 40, 1690, 0.7)
    return (frame * 255 + 0.5).astype(np.uint8)


def cierre_frames():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", CIERRE, "-vf", f"scale={W}:{H},fps={FPS}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    return fr[:N_CIERRE]


if __name__ == "__main__":
    if sys.argv[1] == "--still":
        for ts in sys.argv[2].split(","):
            Image.fromarray(render(int(float(ts) * FPS))).save(f"{W_DIR}/still_{ts}.jpg", quality=88)
        sys.exit()
    part, nparts = int(sys.argv[1]), int(sys.argv[2])
    a, b = part * N_MAIN // nparts, (part + 1) * N_MAIN // nparts
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                            "-pix_fmt", "yuv420p", f"{W_DIR}/part{part}.mp4"], stdin=subprocess.PIPE)
    for i in range(a, b):
        enc.stdin.write(render(i).tobytes())
    if part == nparts - 1:
        for fr in cierre_frames():
            enc.stdin.write(fr.tobytes())
    enc.stdin.close(); enc.wait()
    print("part", part, "done", a, b)
