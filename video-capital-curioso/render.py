"""Render del video vertical (1080x1920, 30 fps) de Capital Curioso.

Uso:  python3 render.py            -> out/video_sin_audio.mp4
      python3 render.py --frame 12.3   -> out/frame_12.3.png (vista previa)
"""
import math, os, sys, json, subprocess
from multiprocessing import Process
import numpy as np
import cairo
from PIL import Image, ImageFilter, ImageEnhance

from timeline import *

W, H = 1080, 1920
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

# ---- Paleta: azul marino y rojo (colores de la bandera dominicana) ----
NAVY = (0.024, 0.071, 0.165)
NAVY2 = (0.043, 0.122, 0.259)
BLUE = (0.0, 0.176, 0.384)       # azul bandera RD  #002D62
BLUE_L = (0.18, 0.42, 0.85)      # azul vivo para mapas
RED = (0.808, 0.067, 0.149)      # rojo bandera RD  #CE1126
RED_L = (0.93, 0.18, 0.24)
WHITE = (1, 1, 1)
GREY = (0.72, 0.76, 0.84)
LAND = (0.16, 0.21, 0.30)

# ======================================================================
# utilidades de animación
# ======================================================================
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def prog(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else float(t >= a)

def ease(x):          # cubic out
    x = clamp(x); return 1 - (1 - x) ** 3

def ease_io(x):
    x = clamp(x); return 3 * x * x - 2 * x * x * x

def back(x, s=1.7):   # overshoot
    x = clamp(x); x -= 1; return x * x * ((s + 1) * x + s) + 1

def vis(t, t0, t1, fin=0.3, fout=0.25):
    if t < t0 or t > t1: return 0.0
    return min(ease(prog(t, t0, t0 + fin)), 1 - ease_io(prog(t, t1 - fout, t1)))

# ======================================================================
# fuentes y texto
# ======================================================================
FONTS = {"black": "Inter Black", "xbold": "Inter ExtraBold", "bold": "Inter",
         "semi": "Inter SemiBold", "med": "Inter Medium"}

def font(ctx, kind, size):
    fam = FONTS[kind]
    weight = cairo.FONT_WEIGHT_BOLD if kind == "bold" else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face(fam, cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)

def tw(ctx, s):
    return ctx.text_extents(s).x_advance

def spaced_width(ctx, s, sp):
    return sum(tw(ctx, ch) for ch in s) + sp * (len(s) - 1)

def text(ctx, s, x, y, color=WHITE, a=1.0, align="left", outline=0, ocol=(0, 0, 0), oa=0.85, sp=0):
    """Dibuja texto con línea base en y. align: left/center/right."""
    w = spaced_width(ctx, s, sp) if sp else tw(ctx, s)
    if align == "center": x -= w / 2
    elif align == "right": x -= w
    ctx.new_path()
    if sp:
        cx = x
        for ch in s:
            ctx.move_to(cx, y); ctx.text_path(ch); cx += tw(ctx, ch) + sp
    else:
        ctx.move_to(x, y); ctx.text_path(s)
    if outline:
        ctx.set_source_rgba(*ocol, oa * a); ctx.set_line_width(outline)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke_preserve()
    ctx.set_source_rgba(*color, a); ctx.fill()
    return w

def wrap(ctx, s, maxw):
    lines, cur = [], ""
    for word in s.split():
        test = (cur + " " + word).strip()
        if tw(ctx, test) <= maxw or not cur: cur = test
        else: lines.append(cur); cur = word
    if cur: lines.append(cur)
    return lines

def rrect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()

def card(ctx, x, y, w, h, a=1.0, accent=RED, r=26):
    # sombra
    ctx.set_source_rgba(0, 0, 0, 0.35 * a); rrect(ctx, x + 6, y + 12, w, h, r); ctx.fill()
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgba(0, *NAVY2, 0.93 * a); g.add_color_stop_rgba(1, *NAVY, 0.95 * a)
    ctx.set_source(g); rrect(ctx, x, y, w, h, r); ctx.fill()
    ctx.set_source_rgba(1, 1, 1, 0.13 * a); ctx.set_line_width(2); rrect(ctx, x, y, w, h, r); ctx.stroke()
    if accent:
        ctx.save(); rrect(ctx, x, y, w, h, r); ctx.clip()
        ctx.set_source_rgba(*accent, a); ctx.rectangle(x, y, w, 7); ctx.fill(); ctx.restore()

def group_begin(ctx):
    ctx.push_group()

def group_end(ctx, a):
    ctx.pop_group_to_source(); ctx.paint_with_alpha(clamp(a))

# ======================================================================
# íconos ilustrados (vectoriales)
# ======================================================================
def flag_rd(ctx, x, y, w, h, a=1.0):
    ctx.save(); rrect(ctx, x, y, w, h, h * 0.08); ctx.clip()
    ctx.set_source_rgba(1, 1, 1, a); ctx.rectangle(x, y, w, h); ctx.fill()
    cw = h * 0.16; mx, my = x + w / 2, y + h / 2
    for (qx, qy, col) in [(x, y, BLUE), (mx + cw / 2, y, RED), (x, my + cw / 2, RED), (mx + cw / 2, my + cw / 2, BLUE)]:
        ctx.set_source_rgba(*col, a); ctx.rectangle(qx, qy, w / 2 - cw / 2, h / 2 - cw / 2); ctx.fill()
    # escudo simplificado
    ctx.set_source_rgba(0.1, 0.45, 0.2, a); ctx.arc(mx, my, h * 0.11, 0, 2 * math.pi); ctx.set_line_width(h * 0.03); ctx.stroke()
    ctx.set_source_rgba(*BLUE, a); ctx.rectangle(mx - h * 0.04, my - h * 0.05, h * 0.08, h * 0.1); ctx.fill()
    ctx.restore()

def flag_slv(ctx, x, y, w, h, a=1.0):
    ctx.save(); rrect(ctx, x, y, w, h, h * 0.08); ctx.clip()
    for i, col in enumerate([(0.0, 0.28, 0.67), (1, 1, 1), (0.0, 0.28, 0.67)]):
        ctx.set_source_rgba(*col, a); ctx.rectangle(x, y + i * h / 3, w, h / 3 + 1); ctx.fill()
    ctx.set_source_rgba(0.85, 0.7, 0.2, a); ctx.set_line_width(h * 0.03)
    ctx.arc(x + w / 2, y + h / 2, h * 0.11, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()

def flag_hti(ctx, x, y, w, h, a=1.0):
    ctx.save(); rrect(ctx, x, y, w, h, h * 0.08); ctx.clip()
    ctx.set_source_rgba(0, 0.125, 0.62, a); ctx.rectangle(x, y, w, h / 2); ctx.fill()
    ctx.set_source_rgba(0.82, 0.06, 0.2, a); ctx.rectangle(x, y + h / 2, w, h / 2); ctx.fill()
    ctx.restore()

def icon_soldier(ctx, cx, cy, s, col=WHITE, a=1.0):
    """Silueta de soldado con casco y fusil. s = altura aprox."""
    k = s / 100.0
    ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k)
    ctx.set_source_rgba(*col, a)
    ctx.arc(0, -30, 15, 0, 2 * math.pi); ctx.fill()                                  # cabeza
    ctx.arc(0, -36, 20, math.pi, 2 * math.pi); ctx.close_path(); ctx.fill()           # casco
    ctx.rectangle(-25, -37, 50, 5); ctx.fill()                                       # ala del casco
    ctx.move_to(-30, -8); ctx.line_to(30, -8); ctx.line_to(24, 50); ctx.line_to(-24, 50); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(*NAVY, a); ctx.set_line_width(7)                             # fusil
    ctx.move_to(-30, 34); ctx.line_to(34, -14); ctx.stroke()
    ctx.set_source_rgba(*col, a); ctx.set_line_width(4)
    ctx.move_to(-32, 36); ctx.line_to(38, -17); ctx.stroke()
    ctx.restore()

def icon_fence(ctx, cx, cy, s, col=WHITE, a=1.0):
    k = s / 100.0
    ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k)
    ctx.set_source_rgba(*col, a); ctx.set_line_width(6)
    for px in (-45, -15, 15, 45):
        ctx.move_to(px, -30); ctx.line_to(px, 48); ctx.stroke()
    ctx.set_line_width(3)
    for i in range(-3, 4):
        ctx.move_to(-45 + i * 30, -24); ctx.line_to(-45 + i * 30 + 70, 46); ctx.stroke()
        ctx.move_to(45 - i * 30, -24); ctx.line_to(45 - i * 30 - 70, 46); ctx.stroke()
    ctx.set_line_width(5); ctx.move_to(-50, -24); ctx.line_to(50, -24); ctx.stroke()
    ctx.set_line_width(3)
    for i in range(6):                                            # alambre en espiral
        ctx.arc(-42 + i * 17, -38, 9, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()

def icon_scale(ctx, cx, cy, s, col=WHITE, a=1.0):
    k = s / 100.0
    ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k)
    ctx.set_source_rgba(*col, a); ctx.set_line_width(6); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(0, -44); ctx.line_to(0, 40); ctx.stroke()
    ctx.move_to(-26, 44); ctx.line_to(26, 44); ctx.stroke()
    ctx.move_to(-44, -30); ctx.line_to(44, -30); ctx.stroke()
    ctx.arc(0, -46, 6, 0, 2 * math.pi); ctx.fill()
    ctx.set_line_width(3)
    for sx in (-44, 44):
        ctx.move_to(sx, -30); ctx.line_to(sx - 16, 6); ctx.stroke()
        ctx.move_to(sx, -30); ctx.line_to(sx + 16, 6); ctx.stroke()
        ctx.arc(sx, 6, 20, 0, math.pi); ctx.close_path(); ctx.fill()
    ctx.restore()

def icon_globe(ctx, cx, cy, s, col=WHITE, a=1.0):
    r = s / 2
    ctx.save(); ctx.set_source_rgba(*col, a); ctx.set_line_width(max(2, s * 0.05))
    ctx.arc(cx, cy, r, 0, 2 * math.pi); ctx.stroke()
    for f in (0.45, 0.85):
        ctx.save(); ctx.translate(cx, cy); ctx.scale(f, 1); ctx.arc(0, 0, r, 0, 2 * math.pi); ctx.restore(); ctx.stroke()
    ctx.move_to(cx - r, cy); ctx.line_to(cx + r, cy); ctx.stroke()
    for dy in (-0.5, 0.5):
        hw = r * math.sqrt(1 - dy * dy)
        ctx.move_to(cx - hw, cy + dy * r); ctx.line_to(cx + hw, cy + dy * r); ctx.stroke()
    ctx.restore()

def icon_calendar(ctx, cx, cy, s, a=1.0):
    k = s / 100.0
    ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k)
    ctx.set_source_rgba(1, 1, 1, a); rrect(ctx, -45, -38, 90, 84, 12); ctx.fill()
    ctx.set_source_rgba(*RED, a); ctx.save(); rrect(ctx, -45, -38, 90, 84, 12); ctx.clip(); ctx.rectangle(-45, -38, 90, 26); ctx.fill(); ctx.restore()
    ctx.set_source_rgba(*NAVY, a)
    for rx in (-24, 24): rrect(ctx, rx - 5, -50, 10, 22, 4); ctx.fill()
    for i in range(4):
        for j in range(3):
            ctx.rectangle(-33 + i * 18, -2 + j * 15, 11, 9); ctx.fill()
    ctx.restore()

def icon_magnifier(ctx, cx, cy, s, a=1.0, draw=1.0, col=WHITE, qcol=RED):
    r = s * 0.32
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(*col, a); ctx.set_line_width(s * 0.085)
    ctx.new_path(); ctx.arc(cx - s * 0.08, cy - s * 0.08, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * clamp(draw / 0.7)); ctx.stroke()
    hp = clamp((draw - 0.7) / 0.3)
    if hp > 0:
        a0 = math.pi / 4; x0 = cx - s * 0.08 + r * math.cos(a0); y0 = cy - s * 0.08 + r * math.sin(a0)
        L = s * 0.32 * hp
        ctx.set_line_width(s * 0.12); ctx.move_to(x0, y0); ctx.line_to(x0 + L * math.cos(a0), y0 + L * math.sin(a0)); ctx.stroke()
    ctx.restore()

def icon_bubble(ctx, cx, cy, s, a=1.0, col=WHITE):
    ctx.save(); ctx.set_source_rgba(*col, a)
    rrect(ctx, cx - s / 2, cy - s * 0.38, s, s * 0.66, s * 0.18); ctx.fill()
    ctx.move_to(cx - s * 0.22, cy + s * 0.26); ctx.line_to(cx - s * 0.34, cy + s * 0.48); ctx.line_to(cx - s * 0.02, cy + s * 0.26); ctx.fill()
    ctx.set_source_rgba(*NAVY, a)
    for dx in (-0.22, 0, 0.22): ctx.arc(cx + dx * s, cy - s * 0.05, s * 0.06, 0, 2 * math.pi); ctx.fill()
    ctx.restore()

def icon_target_x(ctx, cx, cy, s, a=1.0):
    ctx.save(); ctx.set_source_rgba(*RED_L, a); ctx.set_line_width(s * 0.08)
    ctx.arc(cx, cy, s * 0.45, 0, 2 * math.pi); ctx.stroke(); ctx.arc(cx, cy, s * 0.22, 0, 2 * math.pi); ctx.stroke()
    ctx.set_line_width(s * 0.12); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(cx - s * 0.35, cy - s * 0.35); ctx.line_to(cx + s * 0.35, cy + s * 0.35); ctx.stroke()
    ctx.move_to(cx + s * 0.35, cy - s * 0.35); ctx.line_to(cx - s * 0.35, cy + s * 0.35); ctx.stroke()
    ctx.restore()

def icon_stadium(ctx, cx, cy, s, a=1.0):
    ctx.save(); ctx.set_source_rgba(1, 1, 1, a); ctx.set_line_width(s * 0.07)
    ctx.save(); ctx.translate(cx, cy); ctx.scale(1, 0.55); ctx.arc(0, 0, s * 0.48, 0, 2 * math.pi); ctx.restore(); ctx.stroke()
    ctx.save(); ctx.translate(cx, cy); ctx.scale(1, 0.55); ctx.arc(0, 0, s * 0.28, 0, 2 * math.pi); ctx.restore(); ctx.fill()
    ctx.restore()

# ======================================================================
# mapas (Natural Earth 1:10m)
# ======================================================================
GEO = json.load(open(os.path.join(HERE, "assets", "mapa_caribe.json")))

class Proj:
    def __init__(self, lon0, lon1, lat0, lat1, rect):
        x, y, w, h = rect
        self.k = math.cos(math.radians((lat0 + lat1) / 2))
        self.sc = min(w / ((lon1 - lon0) * self.k), h / (lat1 - lat0))
        self.lonc, self.latc = (lon0 + lon1) / 2, (lat0 + lat1) / 2
        self.cx, self.cy = x + w / 2, y + h / 2
    def __call__(self, lon, lat):
        return self.cx + (lon - self.lonc) * self.k * self.sc, self.cy - (lat - self.latc) * self.sc

def country_path(ctx, iso, P):
    for ring in GEO.get(iso, []):
        x, y = P(*ring[0]); ctx.move_to(x, y)
        for lon, lat in ring[1:]:
            ctx.line_to(*P(lon, lat))
        ctx.close_path()

def _border_line():
    """Frontera Haití–RD: vértices del anillo de Haití compartidos con RD."""
    dom = np.array([pt for r in GEO["DOM"] for pt in r])
    hti = max(GEO["HTI"], key=len)
    flags = []
    for lon, lat in hti:
        d = np.min(np.hypot(dom[:, 0] - lon, dom[:, 1] - lat))
        flags.append(d < 0.004)
    n = len(hti); best, cur, start, bstart = 0, 0, 0, 0
    for i in range(2 * n):
        if flags[i % n]:
            if cur == 0: start = i
            cur += 1
            if cur > best: best, bstart = cur, start
        else: cur = 0
    pts = [hti[(bstart + j) % n] for j in range(min(best, n))]
    if pts and pts[0][1] < pts[-1][1]: pts = pts[::-1]  # de norte a sur
    return pts

BORDER = _border_line()

def map_hispaniola(ctx, rect, t, hti_p, dom_p, a=1.0, labels=True, P=None, grid=True):
    x, y, w, h = rect
    P = P or Proj(-74.55, -68.25, 17.45, 20.15, (x + 20, y + 20, w - 40, h - 40))
    ctx.save(); rrect(ctx, x, y, w, h, 26); ctx.clip()
    if grid:
        ctx.set_source_rgba(1, 1, 1, 0.06 * a); ctx.set_line_width(1)
        for gx in range(int(x), int(x + w), 40): ctx.move_to(gx, y); ctx.line_to(gx, y + h)
        for gy in range(int(y), int(y + h), 40): ctx.move_to(x, gy); ctx.line_to(x + w, gy)
        ctx.stroke()
    # tierra base
    for iso in ("HTI", "DOM", "CUB", "JAM", "TCA", "BHS", "PRI"):
        ctx.new_path(); country_path(ctx, iso, P)
        ctx.set_source_rgba(*LAND, a); ctx.fill_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.18 * a); ctx.set_line_width(1.5); ctx.stroke()
    # Haití en rojo, RD en azul (con brillo)
    for iso, col, p in (("HTI", RED_L, hti_p), ("DOM", BLUE_L, dom_p)):
        if p <= 0: continue
        for gw, ga in ((18, 0.10), (10, 0.18), (4, 0.5)):
            ctx.new_path(); country_path(ctx, iso, P)
            ctx.set_source_rgba(*col, ga * p * a); ctx.set_line_width(gw); ctx.stroke()
        ctx.new_path(); country_path(ctx, iso, P)
        ctx.set_source_rgba(*col, 0.85 * p * a); ctx.fill_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.9 * p * a); ctx.set_line_width(2); ctx.stroke()
    ctx.restore()
    if labels:
        font(ctx, "black", 40)
        if hti_p > 0:
            lx, ly = P(-72.75, 18.95)
            text(ctx, "HAITÍ", lx, ly + 14 + (1 - ease(hti_p)) * 20, WHITE, ease(hti_p) * a, "center", outline=6, oa=0.5)
        if dom_p > 0:
            lx, ly = P(-70.35, 18.85)
            font(ctx, "black", 34)
            text(ctx, "REP. DOMINICANA", lx, ly + 12 + (1 - ease(dom_p)) * 20, WHITE, ease(dom_p) * a, "center", outline=6, oa=0.5)
    return P

# ======================================================================
# fotos con filtro cinematográfico oscuro
# ======================================================================
_PH = {}

def _surface_from_rgb(arr):
    h, w = arr.shape[:2]
    bgra = np.empty((h, w, 4), np.uint8)
    bgra[..., 0] = arr[..., 2]; bgra[..., 1] = arr[..., 1]; bgra[..., 2] = arr[..., 0]; bgra[..., 3] = 255
    s = cairo.ImageSurface.create_for_data(memoryview(bgra), cairo.FORMAT_RGB24, w, h, w * 4)
    return s, bgra

def photo(name):
    if name in _PH: return _PH[name]
    blur = name.endswith("B")
    im = Image.open(os.path.join(HERE, "assets", "fotos", name.rstrip("B") + ".jpg")).convert("RGB")
    if max(im.size) > 2000: im.thumbnail((2000, 2000), Image.LANCZOS)
    if min(im.size) < 1000:   # fotos pequeñas: ampliar con suavizado y realce leve
        f = 1000 / min(im.size)
        im = im.resize((int(im.width * f), int(im.height * f)), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    if blur: im = im.filter(ImageFilter.GaussianBlur(14))
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    a = lum[..., None] + (a - lum[..., None]) * 0.78           # menos saturación
    a = (a - 0.5) * 1.12 + 0.5                                  # contraste
    a = a * (0.55 if blur else 0.80)                            # oscurecer
    navy = np.array([0.02, 0.07, 0.17], np.float32)
    sh = (1 - np.clip(lum, 0, 1))[..., None] ** 1.5
    a = a * (1 - 0.30 * sh) + navy * 0.30 * sh                  # sombras azul marino
    a = a * np.array([0.97, 0.99, 1.04], np.float32)            # tono frío
    a = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    _PH[name] = _surface_from_rgb(a) + (im.width, im.height)
    return _PH[name]

def draw_photo(ctx, name, rect, fx, fy, zoom, dx=0.0, a=1.0):
    surf, _, iw, ih = photo(name)
    x, y, w, h = rect
    s = max(w / iw, h / ih) * zoom
    sw, sh = iw * s, ih * s
    ox = x + w / 2 - (fx + dx) * sw
    oy = y + h / 2 - fy * sh
    ox = min(x, max(x + w - sw, ox)); oy = min(y, max(y + h - sh, oy))
    ctx.save(); ctx.rectangle(x, y, w, h); ctx.clip()
    ctx.translate(ox, oy); ctx.scale(s, s)
    ctx.set_source_surface(surf, 0, 0); ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(a); ctx.restore()

def shot_at(t):
    idx = 0
    for i, sh in enumerate(SHOTS):
        if t >= sh[0]: idx = i
    return idx

def draw_shot(ctx, i, t, a=1.0):
    st, name, fx, fy, z0, z1, dx = SHOTS[i]
    en = SHOTS[i + 1][0] if i + 1 < len(SHOTS) else DURATION
    p = ease_io(prog(t, st, en + 0.4))
    if name == "SPLIT": draw_split_bg(ctx, t, a); return
    if name == "OUTRO": draw_outro_bg(ctx, t, a); return
    draw_photo(ctx, name, (0, 0, W, H), fx, fy, z0 + (z1 - z0) * p, dx * (p - 0.5), a)

def draw_background(ctx, t):
    i = shot_at(t)
    st = SHOTS[i][0]
    ctx.set_source_rgb(*NAVY); ctx.paint()
    XF = 0.32
    if i > 0 and t - st < XF:
        draw_shot(ctx, i - 1, t)
        k = ease_io((t - st) / XF)
        draw_shot(ctx, i, t, k)
        # destello de transición
        ctx.set_source_rgba(1, 1, 1, 0.10 * math.sin(math.pi * k)); ctx.paint()
    else:
        draw_shot(ctx, i, t)

# ======================================================================
# capas globales
# ======================================================================
def grade_overlays(ctx, t):
    g = cairo.LinearGradient(0, 0, 0, 700)
    g.add_color_stop_rgba(0, 0.01, 0.03, 0.08, 0.82); g.add_color_stop_rgba(1, 0.01, 0.03, 0.08, 0)
    ctx.set_source(g); ctx.rectangle(0, 0, W, 700); ctx.fill()
    g = cairo.LinearGradient(0, 1250, 0, H)
    g.add_color_stop_rgba(0, 0.01, 0.03, 0.08, 0); g.add_color_stop_rgba(1, 0.01, 0.03, 0.08, 0.85)
    ctx.set_source(g); ctx.rectangle(0, 1250, W, H - 1250); ctx.fill()
    # viñeta
    g = cairo.RadialGradient(W / 2, H / 2, H * 0.30, W / 2, H / 2, H * 0.72)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0.02, 0.62)
    ctx.set_source(g); ctx.paint()
    # leve dominante roja/azul en esquinas (look cine)
    g = cairo.RadialGradient(0, H, 50, 0, H, 900)
    g.add_color_stop_rgba(0, *RED, 0.16); g.add_color_stop_rgba(1, *RED, 0)
    ctx.set_source(g); ctx.paint()
    g = cairo.RadialGradient(W, 0, 50, W, 0, 900)
    g.add_color_stop_rgba(0, *BLUE_L, 0.16); g.add_color_stop_rgba(1, *BLUE_L, 0)
    ctx.set_source(g); ctx.paint()

def brand_bar(ctx, t):
    a = vis(t, 0.2, VOICE_END + 0.1, 0.5, 0.3)
    if a <= 0: return
    font(ctx, "black", 24); sp = 3
    label = "CAPITAL CURIOSO"
    lw = spaced_width(ctx, label, sp)
    total = 36 + 12 + lw + 16 + 42
    x0 = W / 2 - total / 2; y0 = 150
    ctx.set_source_rgba(*NAVY, 0.72 * a); rrect(ctx, x0 - 22, y0 - 26, total + 44, 52, 26); ctx.fill()
    ctx.set_source_rgba(1, 1, 1, 0.15 * a); ctx.set_line_width(1.5); rrect(ctx, x0 - 22, y0 - 26, total + 44, 52, 26); ctx.stroke()
    icon_magnifier(ctx, x0 + 18, y0, 34, a)
    font(ctx, "black", 13); text(ctx, "?", x0 + 15, y0 + 2, RED_L, a, "center")
    font(ctx, "black", 24)
    text(ctx, label, x0 + 48, y0 + 9, WHITE, a, sp=sp)
    flag_rd(ctx, x0 + 48 + lw + 16, y0 - 14, 42, 28, a)

def handle_tag(ctx, t):
    a = vis(t, 0.5, VOICE_END, 0.5, 0.3) * 0.75
    if a <= 0: return
    font(ctx, "semi", 26)
    text(ctx, "@capitalcuriosoo", W - 40, H - 60, WHITE, a, "right", outline=4, oa=0.4)

# ---------------- subtítulos palabra por palabra (arriba) ----------------
WORDS = load_words()

def build_chunks():
    chunks, cur = [], []
    for i, w in enumerate(WORDS):
        if cur:
            prev = cur[-1]
            chars = sum(len(x["w"]) + 1 for x in cur) + len(w["w"])
            if len(cur) >= 3 or chars > 19 or prev["w"][-1] in ".,?" or w["s"] - prev["e"] > 0.35:
                chunks.append(cur); cur = []
        cur.append(w)
    if cur: chunks.append(cur)
    out = []
    for k, c in enumerate(chunks):
        st = c[0]["s"] - 0.04
        nxt = chunks[k + 1][0]["s"] - 0.04 if k + 1 < len(chunks) else 1e9
        en = min(nxt, c[-1]["e"] + 0.45)
        out.append((st, en, c))
    return out

CHUNKS = build_chunks()

def subtitles(ctx, t):
    if t >= VOICE_END + 0.3: return
    for st, en, words in CHUNKS:
        if not (st <= t < en): continue
        size = 74
        font(ctx, "black", size)
        toks = [w["w"].upper().rstrip(".,") for w in words]
        space = tw(ctx, " ") * 1.1
        widths = [tw(ctx, s) for s in toks]
        total = sum(widths) + space * (len(toks) - 1)
        while total > 980:
            size -= 4; font(ctx, "black", size)
            space = tw(ctx, " ") * 1.1; widths = [tw(ctx, s) for s in toks]; total = sum(widths) + space * (len(toks) - 1)
        pop = back(prog(t, st, st + 0.16), 2.2)
        cy = 355
        ctx.save(); ctx.translate(W / 2, cy); ctx.scale(0.88 + 0.12 * pop, 0.88 + 0.12 * pop); ctx.translate(-W / 2, -cy)
        x = W / 2 - total / 2
        active = -1
        for i, w in enumerate(words):
            if t >= w["s"] - 0.03: active = i
        for i, (s, wd) in enumerate(zip(toks, widths)):
            if i == active:
                kk = back(prog(t, words[i]["s"] - 0.03, words[i]["s"] + 0.1), 2.5)
                padx, pady = 14, 12
                ctx.save(); ctx.translate(x + wd / 2, cy); ctx.scale(0.85 + 0.15 * kk, 0.85 + 0.15 * kk); ctx.translate(-(x + wd / 2), -cy)
                ctx.set_source_rgba(*RED, 0.95); rrect(ctx, x - padx, cy - size * 0.72 - pady + 4, wd + 2 * padx, size * 0.72 + 2 * pady + 4, 14); ctx.fill()
                text(ctx, s, x, cy + 6, WHITE, 1, outline=0)
                ctx.restore()
            else:
                a = 1.0 if i < active else 0.55
                text(ctx, s, x, cy + 6, WHITE, a, outline=10, oa=0.9)
            x += wd + space
        ctx.restore()

# ---------------- elementos reutilizables ----------------
def lower_third(ctx, t, t0, t1, name, role, flagfn=None, y=1440):
    a = vis(t, t0, t1, 0.05, 0.3)
    if a <= 0: return
    p = ease(prog(t, t0, t0 + 0.45))
    font(ctx, "black", 56); nw = tw(ctx, name)
    font(ctx, "semi", 32); rw = tw(ctx, role)
    bw = max(nw, rw) + 70 + (90 if flagfn else 0)
    x0 = 40
    group_begin(ctx)
    ctx.set_source_rgba(*RED, 1); ctx.rectangle(x0, y - 70 + (1 - p) * 70, 14, 150 * p); ctx.fill()
    ctx.save(); ctx.rectangle(x0 + 14, y - 80, bw * p, 170); ctx.clip()
    ctx.set_source_rgba(*NAVY, 0.94); ctx.rectangle(x0 + 14, y - 70, bw, 95); ctx.fill()
    ctx.set_source_rgba(*RED, 0.95); ctx.rectangle(x0 + 14, y + 25, max(rw + 50, 200), 55); ctx.fill()
    tx = x0 + 44 + (1 - p) * -40
    if flagfn:
        flagfn(ctx, tx, y - 50, 66, 44, 1); tx += 88
    font(ctx, "black", 56); text(ctx, name, tx, y + 2, WHITE)
    font(ctx, "semi", 32); text(ctx, role, x0 + 38, y + 64, WHITE)
    ctx.restore()
    group_end(ctx, a)

def source_tag(ctx, s, x, y, a, align="left"):
    font(ctx, "semi", 25)
    text(ctx, s, x, y, GREY, a * 0.95, align, outline=4, oa=0.5)

def big_title(ctx, t, t0, t1, lines, y, size=96, colors=None, a_mult=1.0):
    a = vis(t, t0, t1, 0.2, 0.25) * a_mult
    if a <= 0: return
    k = back(prog(t, t0, t0 + 0.35), 1.8)
    font(ctx, "black", size)
    ctx.save(); ctx.translate(W / 2, y); ctx.scale(0.75 + 0.25 * k, 0.75 + 0.25 * k); ctx.translate(-W / 2, -y)
    lh = size * 1.05
    y0 = y - (len(lines) - 1) * lh / 2 + size * 0.36
    for i, ln in enumerate(lines):
        col = colors[i] if colors else WHITE
        text(ctx, ln, W / 2, y0 + i * lh, col, a, "center", outline=14, ocol=(0.01, 0.03, 0.08), oa=0.92)
    ctx.restore()

def typed(s, t, t0, dur):
    n = int(len(s) * clamp((t - t0) / dur))
    return s[:n]

# ======================================================================
# ESCENAS
# ======================================================================
def scene1(ctx, t):
    a = vis(t, 0.15, S1[1] - 0.05, 0.45, 0.35)
    if a <= 0: return
    rect = (60, 760, 960, 520)
    group_begin(ctx)
    k = ease(prog(t, 0.15, 0.7))
    ctx.save(); ctx.translate(0, (1 - k) * 60)
    card(ctx, *rect)
    font(ctx, "xbold", 26); text(ctx, "LA ISLA DE LA ESPAÑOLA", 100, 812, GREY, 1, sp=3)
    hp = ease(prog(t, 3.25, 3.85)); dp = ease(prog(t, 4.5, 5.1))
    map_hispaniola(ctx, (60, 830, 960, 450), t, hp, dp)
    # pulso en Puerto Príncipe
    if hp > 0:
        P = Proj(-74.55, -68.25, 17.45, 20.15, (80, 850, 920, 410))
        px, py = P(-72.33, 18.54)
        for ph in (0, 0.5):
            q = ((t - 3.3 + ph) % 1.0)
            ctx.set_source_rgba(1, 1, 1, (1 - q) * 0.8 * hp); ctx.set_line_width(3); ctx.arc(px, py, 6 + 30 * q, 0, 2 * math.pi); ctx.stroke()
        ctx.set_source_rgba(1, 1, 1, hp); ctx.arc(px, py, 7, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    group_end(ctx, a)
    # Kicker inicial
    ka = vis(t, 0.3, 3.3, 0.3, 0.3)
    if ka > 0:
        font(ctx, "black", 40)
        s = "EL SALVADOR EN HAITÍ"
        w = tw(ctx, s)
        ctx.set_source_rgba(*RED, ka); rrect(ctx, W / 2 - w / 2 - 26, 600, w + 52, 70, 12); ctx.fill()
        text(ctx, s, W / 2, 650, WHITE, ka, "center")
    # Texto grande
    big_title(ctx, t, 4.95, S1[1] - 0.05, ["¿RD ESTÁ", "AYUDANDO?"], 1460, 120, [WHITE, RED_L])

def scene2(ctx, t):
    if not (S2[0] <= t < S2[1]): return
    # chip de fecha
    a = vis(t, 7.45, 9.6, 0.3, 0.25)
    if a > 0:
        group_begin(ctx)
        card(ctx, 140, 1180, 800, 200, 1)
        icon_calendar(ctx, 250, 1285, 110)
        font(ctx, "semi", 30); text(ctx, "TODO EMPEZÓ", 340, 1250, GREY, 1, sp=2)
        font(ctx, "black", 58); text(ctx, typed("FINALES DE OCTUBRE", t, 7.6, 1.1), 340, 1325, WHITE)
        group_end(ctx, a)
    # Bukele
    lower_third(ctx, t, 9.75, 14.0, "NAYIB BUKELE", "Presidente de El Salvador", flag_slv, y=1500)
    # mapa con flecha El Salvador -> Puerto Príncipe
    ma = vis(t, 10.35, 14.0, 0.4, 0.3)
    if ma > 0:
        group_begin(ctx)
        rect = (40, 820, 1000, 560)
        k = ease(prog(t, 10.35, 10.8))
        ctx.save(); ctx.translate(0, (1 - k) * 50)
        card(ctx, *rect)
        P = Proj(-91.5, -67.0, 11.6, 21.6, (60, 860, 960, 500))
        ctx.save(); rrect(ctx, *rect, 26); ctx.clip()
        ctx.set_source_rgba(1, 1, 1, 0.05); ctx.set_line_width(1)
        for lon in range(-92, -66, 2):
            x1, y1 = P(lon, 11); x2, y2 = P(lon, 22); ctx.move_to(x1, y1); ctx.line_to(x2, y2)
        for lat in range(11, 23, 2):
            x1, y1 = P(-92, lat); x2, y2 = P(-66, lat); ctx.move_to(x1, y1); ctx.line_to(x2, y2)
        ctx.stroke()
        for iso in GEO:
            ctx.new_path(); country_path(ctx, iso, P)
            col = {"SLV": (0.35, 0.6, 1.0), "HTI": RED_L, "DOM": BLUE_L}.get(iso, LAND)
            al = 0.95 if iso in ("SLV", "HTI", "DOM") else 1
            ctx.set_source_rgba(*col, al); ctx.fill_preserve()
            ctx.set_source_rgba(1, 1, 1, 0.16); ctx.set_line_width(1); ctx.stroke()
        ctx.restore()
        x0, y0 = P(-89.2, 13.7); x1, y1 = P(-72.33, 18.54)
        cxp, cyp = (x0 + x1) / 2, min(y0, y1) - 230
        ap = ease_io(prog(t, 10.9, 12.5))
        # curva cuadrática dibujándose
        N = 60; pts = []
        for i in range(int(N * ap) + 1):
            u = i / N
            pts.append(((1 - u) ** 2 * x0 + 2 * (1 - u) * u * cxp + u * u * x1, (1 - u) ** 2 * y0 + 2 * (1 - u) * u * cyp + u * u * y1))
        if len(pts) > 1:
            for lw, la, col in ((16, 0.18, RED_L), (6, 1, WHITE)):
                ctx.set_source_rgba(*col, la); ctx.set_line_width(lw); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.set_dash([] if lw > 10 else [18, 10])
                ctx.move_to(*pts[0])
                for p in pts[1:]: ctx.line_to(*p)
                ctx.stroke()
            ctx.set_dash([])
            (ax, ay), (bx, by) = pts[-2], pts[-1]
            ang = math.atan2(by - ay, bx - ax)
            ctx.save(); ctx.translate(bx, by); ctx.rotate(ang)
            ctx.set_source_rgba(*RED_L, 1); ctx.move_to(14, 0); ctx.line_to(-18, -16); ctx.line_to(-18, 16); ctx.close_path(); ctx.fill()
            ctx.restore()
        for (px, py, lab, al, dy) in ((x0, y0, "EL SALVADOR", "center", 50), (x1, y1, "PUERTO PRÍNCIPE", "center", 52)):
            ctx.set_source_rgba(1, 1, 1, 1); ctx.arc(px, py, 9, 0, 2 * math.pi); ctx.fill()
            font(ctx, "black", 32); text(ctx, lab, min(max(px, 170), 900), py + dy, WHITE, 1, al, outline=6, oa=0.6)
        # soldados enviados
        sa = ease(prog(t, 10.75, 11.2))
        if sa > 0:
            font(ctx, "black", 70)
            n = int(2000 * ease(prog(t, 10.75, 11.4)))
            text(ctx, f"{n:,}", 800, 1250, WHITE, sa, "center", outline=8, oa=0.6)
            font(ctx, "xbold", 30); text(ctx, "SOLDADOS ENVIADOS", 800, 1292, GREY, sa, "center", outline=5, oa=0.6)
        ctx.restore()
        group_end(ctx, ma)
    # 4 militares secuestrados
    ka = vis(t, 14.05, 16.8, 0.25, 0.25)
    if ka > 0:
        group_begin(ctx)
        card(ctx, 70, 1050, 940, 420)
        for i in range(4):
            tt = 14.1 + i * 0.3
            k = back(prog(t, tt, tt + 0.3), 2.2)
            if k <= 0: continue
            cx = 210 + i * 220; cy = 1190
            ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k); ctx.translate(-cx, -cy)
            ctx.set_source_rgba(*RED, 0.9); ctx.arc(cx, cy, 82, 0, 2 * math.pi); ctx.fill()
            icon_soldier(ctx, cx, cy + 6, 120, WHITE)
            ctx.set_source_rgba(1, 1, 1, 0.9); ctx.set_line_width(5)          # cuerda / esposas
            ctx.arc(cx, cy, 82, 0, 2 * math.pi); ctx.stroke()
            ctx.restore()
        k = ease(prog(t, 14.6, 15.0))
        font(ctx, "black", 120); text(ctx, "4", 150, 1420, RED_L, k)
        font(ctx, "black", 48); text(ctx, "MILITARES SALVADOREÑOS", 240, 1372, WHITE, k)
        font(ctx, "black", 48); text(ctx, "SECUESTRADOS", 240, 1428, RED_L, k)
        group_end(ctx, ka)
    # contador 2,000 -> 2,500
    ca = vis(t, 16.9, S2[1] - 0.05, 0.3, 0.3)
    if ca > 0:
        group_begin(ctx)
        k = back(prog(t, 16.9, 17.3), 1.6)
        ctx.save(); ctx.translate(W / 2, 1150); ctx.scale(0.8 + 0.2 * k, 0.8 + 0.2 * k); ctx.translate(-W / 2, -1150)
        card(ctx, 90, 900, 900, 520)
        n = 2000 + int(500 * ease_io(prog(t, 19.1, 20.2)))
        font(ctx, "black", 210)
        col = RED_L if t >= 20.2 else WHITE
        text(ctx, f"{n:,}", W / 2, 1150, col, 1, "center")
        font(ctx, "black", 50); text(ctx, "SOLDADOS EN HAITÍ", W / 2, 1230, WHITE, 1, "center", sp=2)
        # fila de soldados que crece
        m = 20 + int(5 * ease_io(prog(t, 19.1, 20.2)))
        for i in range(m):
            cx = 150 + (i % 25) * 32.5
            icon_soldier(ctx, cx, 1310, 46, RED_L if i >= 20 else (0.85, 0.88, 0.95), 1)
        source_tag(ctx, "Fuente: AP", 130, 1395, 1)
        flag_slv(ctx, 860, 935, 90, 60)
        ctx.restore()
        group_end(ctx, ca)

def scene3(ctx, t):
    if not (S3[0] <= t < S3[1]): return
    a = vis(t, 21.3, S3[1] - 0.05, 0.35, 0.3)
    if a > 0:
        group_begin(ctx)
        k = ease(prog(t, 21.3, 21.75))
        ctx.save(); ctx.translate(0, (1 - k) * 60)
        y0 = 1150
        card(ctx, 40, y0, 1000, 450)
        font(ctx, "xbold", 26); text(ctx, "LÍNEA DE TIEMPO", 80, y0 + 52, GREY, 1, sp=3)
        ly = y0 + 120
        lp1 = ease_io(prog(t, 21.4, 22.2)); lp2 = ease_io(prog(t, 26.9, 27.6))
        x_a, x_b, x_c = 80, 290, 790
        ctx.set_source_rgba(1, 1, 1, 0.18); ctx.set_line_width(6); ctx.move_to(x_a, ly); ctx.line_to(1000, ly); ctx.stroke()
        ctx.set_source_rgba(*RED_L, 1)
        ctx.move_to(x_a, ly); ctx.line_to(x_a + (x_b - x_a) * lp1 + (x_c - x_b) * lp2, ly); ctx.stroke()
        for (nx, t0, date, desc, icon) in ((x_b, 21.5, "MAR 10 NOV", "Destruyen cuartel de 400 Mawozo", "x"),
                                           (x_c - 0, 27.2, "JUE 12 NOV", "Toman el principal estadio", "st")):
            kk = back(prog(t, t0, t0 + 0.35), 2.2)
            if kk <= 0: continue
            ctx.set_source_rgba(*RED, 1); ctx.arc(nx, ly, 20 * kk, 0, 2 * math.pi); ctx.fill()
            ctx.set_source_rgba(1, 1, 1, 1); ctx.arc(nx, ly, 8 * kk, 0, 2 * math.pi); ctx.fill()
            col_x = 70 if nx < 500 else 560
            font(ctx, "black", 44); text(ctx, date, col_x + 20, ly + 85, RED_L, ease(prog(t, t0, t0 + 0.3)))
            font(ctx, "xbold", 38)
            s = typed(desc, t, t0 + 0.15, 1.2)
            for i, ln in enumerate(wrap(ctx, desc, 420)):
                shown = s[len(" ".join(wrap(ctx, desc, 420)[:i])) + (1 if i else 0):]
                shown = shown[:len(ln)]
                text(ctx, shown, col_x + 20, ly + 140 + i * 48, WHITE, 1)
            ia = ease(prog(t, t0 + 0.4, t0 + 0.8))
            if icon == "x": icon_target_x(ctx, col_x + 400, ly + 260, 70, ia)
            else: icon_stadium(ctx, col_x + 400, ly + 262, 80, ia)
        ctx.restore()
        group_end(ctx, a)
    # etiquetas sobre la foto
    la = vis(t, 23.95, 26.35, 0.3, 0.25)
    if la > 0:
        font(ctx, "black", 34); s = "PANDILLA 400 MAWOZO"; w = tw(ctx, s)
        ctx.set_source_rgba(*RED, la); rrect(ctx, 60, 860, w + 50, 64, 10); ctx.fill()
        text(ctx, s, 85, 905, WHITE, la)
        font(ctx, "semi", 28); text(ctx, "Anuncio de Nayib Bukele", 62, 960, GREY, la, outline=5, oa=0.6)
    la = vis(t, 27.6, 31.5, 0.3, 0.25)
    if la > 0:
        font(ctx, "black", 34); s = "ESTADIO SYLVIO CATOR"; w = tw(ctx, s)
        ctx.set_source_rgba(*BLUE, la * 0.95); rrect(ctx, 60, 860, w + 50, 64, 10); ctx.fill()
        ctx.set_source_rgba(*RED, la); ctx.rectangle(60, 860, 10, 64); ctx.fill()
        text(ctx, s, 88, 905, WHITE, la)
        font(ctx, "semi", 28); text(ctx, "Puerto Príncipe, Haití", 62, 960, GREY, la, outline=5, oa=0.6)
    # cifra grande
    ba = vis(t, 31.5, S3[1] - 0.05, 0.25, 0.3)
    if ba > 0:
        k = back(prog(t, 31.5, 31.85), 1.8)
        ctx.save(); ctx.translate(W / 2, 880); ctx.scale(0.7 + 0.3 * k, 0.7 + 0.3 * k); ctx.translate(-W / 2, -880)
        font(ctx, "black", 50); text(ctx, "OCUPADO DESDE", W / 2, 760, WHITE, ba, "center", outline=10, oa=0.85, sp=4)
        font(ctx, "black", 240)
        yr = 2024 if t > 31.9 else 2000 + int(24 * ease(prog(t, 31.5, 31.9)))
        text(ctx, str(yr), W / 2, 990, RED_L, ba, "center", outline=16, ocol=(0.01, 0.03, 0.08), oa=0.9)
        font(ctx, "semi", 30); text(ctx, "por pandillas", W / 2, 1050, GREY, ba, "center", outline=5, oa=0.7)
        ctx.restore()

def scene4(ctx, t):
    if not (S4[0] <= t < S4[1]): return
    # ¿Y NOSOTROS?
    a = vis(t, 34.55, 35.75, 0.15, 0.25)
    if a > 0:
        k = back(prog(t, 34.55, 34.9), 2)
        ctx.save(); ctx.translate(W / 2, 1150); ctx.scale(0.6 + 0.4 * k, 0.6 + 0.4 * k); ctx.translate(-W / 2, -960)
        flag_rd(ctx, W / 2 - 105, 1000, 210, 140, a)
        font(ctx, "black", 112); text(ctx, "¿Y NOSOTROS?", W / 2, 1270, WHITE, a, "center", outline=16, ocol=(0.01, 0.03, 0.08), oa=0.9)
        ctx.restore()
    lower_third(ctx, t, 35.75, 38.35, "LUIS ABINADER", "Presidente de la República Dominicana", flag_rd, y=1480)
    # tarjeta de cita
    qa = vis(t, 38.35, S4[1] - 0.05, 0.3, 0.3)
    if qa > 0:
        group_begin(ctx)
        k = ease(prog(t, 38.35, 38.8))
        ctx.save(); ctx.translate(0, (1 - k) * 60)
        x, y, w, h = 50, 1000, 980, 560
        card(ctx, x, y, w, h, 1, RED)
        font(ctx, "black", 220); text(ctx, "“", x + 30, y + 200, RED_L, 1)
        flag_rd(ctx, x + w - 130, y + 40, 84, 56)
        quote = [wd for wd in WORDS if 38.4 <= wd["s"] <= 42.9]
        font(ctx, "xbold", 50)
        lines, cur, curw = [], [], 0
        for wd in quote:
            s = wd["w"].rstrip(".")
            ww = tw(ctx, s + " ")
            if curw + ww > 820 and cur: lines.append(cur); cur, curw = [], 0
            cur.append((s, wd)); curw += ww
        if cur: lines.append(cur)
        ly = y + 160
        for ln in lines:
            lx = x + 70
            for s, wd in ln:
                on = t >= wd["s"] - 0.05
                col = WHITE if on else (0.55, 0.6, 0.7)
                if s.lower().startswith(("logística", "inteligencia")) and on: col = RED_L
                text(ctx, s, lx, ly, col, 1 if on else 0.6)
                lx += tw(ctx, s + " ")
            ly += 66
        font(ctx, "black", 36); text(ctx, "”", lx - 4, ly - 66, RED_L, 1)
        ctx.set_source_rgba(1, 1, 1, 0.2); ctx.rectangle(x + 70, y + h - 120, w - 140, 2); ctx.fill()
        font(ctx, "black", 32); text(ctx, "LUIS ABINADER", x + 70, y + h - 70, WHITE)
        font(ctx, "semi", 26); text(ctx, "Fuente: declaraciones a la prensa, 10 nov 2026", x + 70, y + h - 30, GREY)
        ctx.restore()
        group_end(ctx, qa)

def draw_split_bg(ctx, t, a=1.0):
    p = ease(prog(t, 45.05, 45.6))
    ctx.push_group()
    ctx.set_source_rgb(*NAVY); ctx.paint()
    hh = 957
    ctx.save(); ctx.translate(-(1 - p) * W, 0)
    zt = 1.04 + 0.08 * prog(t, 45, 55)
    draw_photo(ctx, "p02", (0, 0, W, hh), 0.30, 0.45, zt)
    ctx.restore()
    ctx.save(); ctx.translate((1 - p) * W, 0)
    draw_photo(ctx, "p08", (0, hh + 6, W, H - hh - 6), 0.5, 0.45, 1.12 - 0.08 * prog(t, 45, 55))
    ctx.restore()
    ctx.set_source_rgba(*RED, 1); ctx.rectangle(0, hh, W * p, 6); ctx.fill()
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)

def scene5(ctx, t):
    if not (S5[0] <= t < S5[1]): return
    big_title(ctx, t, 43.25, 45.1, ["PERO NO TODOS", "APLAUDEN"], 980, 110, [WHITE, RED_L])
    # panel ONU (mitad superior)
    a = vis(t, 45.35, S5[1] - 0.05, 0.3, 0.3)
    if a > 0:
        group_begin(ctx)
        k = ease(prog(t, 45.35, 45.8))
        ctx.save(); ctx.translate((1 - k) * -80, 0)
        card(ctx, 40, 560, 1000, 360, 1, BLUE_L)
        ctx.set_source_rgba(*BLUE_L, 1); ctx.arc(150, 670, 62, 0, 2 * math.pi); ctx.fill()
        icon_globe(ctx, 150, 670, 80, WHITE)
        font(ctx, "black", 58); text(ctx, "ONU", 240, 690, WHITE)
        font(ctx, "semi", 28); text(ctx, "Naciones Unidas advierte", 240, 730, GREY)
        font(ctx, "xbold", 42)
        s = typed("La mayoría no es parte de la fuerza antipandillas", t, 45.7, 1.5)
        for i, ln in enumerate(wrap(ctx, "La mayoría no es parte de la fuerza antipandillas", 900)):
            pre = len(" ".join(wrap(ctx, "La mayoría no es parte de la fuerza antipandillas", 900)[:i])) + (1 if i else 0)
            text(ctx, s[pre:pre + len(ln)], 80, 805 + i * 54, WHITE)
        ctx.restore()
        group_end(ctx, a)
    # panel Amnistía (mitad inferior)
    a = vis(t, 51.35, S5[1] - 0.05, 0.3, 0.3)
    if a > 0:
        group_begin(ctx)
        k = ease(prog(t, 51.35, 51.8))
        ctx.save(); ctx.translate((1 - k) * 80, 0)
        card(ctx, 40, 1180, 1000, 330, 1, RED)
        ctx.set_source_rgba(*RED, 1); ctx.arc(150, 1300, 66, 0, 2 * math.pi); ctx.fill()
        icon_scale(ctx, 150, 1302, 90, WHITE)
        font(ctx, "black", 46); text(ctx, "AMNISTÍA INTERNACIONAL:", 240, 1290, WHITE)
        font(ctx, "semi", 28); text(ctx, "Organización de derechos humanos", 240, 1332, GREY)
        font(ctx, "xbold", 44)
        text(ctx, typed("Respetar los derechos humanos", t, 51.6, 1.1), 80, 1440, WHITE)
        ctx.restore()
        group_end(ctx, a)

def scene6(ctx, t):
    if not (S6[0] <= t < S6[1]): return
    a = vis(t, 55.0, S6[1] - 0.05, 0.4, 0.3)
    if a <= 0: return
    group_begin(ctx)
    k = ease(prog(t, 55.0, 55.5))
    ctx.save(); ctx.translate(0, (1 - k) * 60)
    rect = (40, 620, 1000, 700)
    card(ctx, *rect)
    font(ctx, "xbold", 26); text(ctx, "FRONTERA DOMINICO-HAITIANA", 80, 672, GREY, 1, sp=3)
    P = Proj(-73.55, -69.95, 17.55, 20.05, (60, 690, 960, 620))
    dp = ease(prog(t, 56.45, 57.0))
    map_hispaniola(ctx, (40, 690, 1000, 630), t, 0.35, 0.4 + 0.6 * dp, 1, labels=False, P=P, grid=True)
    font(ctx, "black", 36)
    hx, hy = P(-72.65, 19.15); text(ctx, "HAITÍ", hx, hy, WHITE, 0.8, "center", outline=6, oa=0.5)
    dx_, dy_ = P(-70.75, 19.05); text(ctx, "LADO DOMINICANO" if dp > 0 else "RD", dx_, dy_, WHITE, 1, "center", outline=6, oa=0.5)
    # la frontera se dibuja sola
    bp = ease_io(prog(t, 57.8, 59.1))
    if bp > 0 and BORDER:
        n = max(2, int(len(BORDER) * bp))
        pts = [P(*q) for q in BORDER[:n]]
        for lw, la, col in ((22, 0.15, RED_L), (12, 0.3, RED_L), (5, 1, WHITE)):
            ctx.set_source_rgba(*col, la); ctx.set_line_width(lw); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.move_to(*pts[0])
            for p in pts[1:]: ctx.line_to(*p)
            ctx.stroke()
        if bp < 1:
            ctx.set_source_rgba(1, 1, 1, 1); ctx.arc(*pts[-1], 10, 0, 2 * math.pi); ctx.fill()
    # Jimaní
    ja = ease(prog(t, 58.9, 59.3))
    if ja > 0:
        jx, jy = P(-71.85, 18.49)
        for ph in (0, 0.5):
            q = ((t - 58.9 + ph) % 1.0)
            ctx.set_source_rgba(*RED_L, (1 - q) * ja); ctx.set_line_width(4); ctx.arc(jx, jy, 10 + 50 * q, 0, 2 * math.pi); ctx.stroke()
        ctx.set_source_rgba(*RED, ja); ctx.arc(jx, jy, 13, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(1, 1, 1, ja); ctx.arc(jx, jy, 5, 0, 2 * math.pi); ctx.fill()
        font(ctx, "black", 40); s = "JIMANÍ"; w = tw(ctx, s)
        lx, ly = jx + 40, jy + 60
        ctx.set_source_rgba(*RED, ja); rrect(ctx, lx, ly - 42, w + 36, 58, 10); ctx.fill()
        text(ctx, s, lx + 18, ly, WHITE, ja)
    ctx.restore()
    # íconos: soldado + verja
    for i, (t0, ic, lab) in enumerate(((59.75, "s", "MÁS MILITARES"), (60.95, "f", "VERJA EN CONSTRUCCIÓN"))):
        kk = back(prog(t, t0, t0 + 0.35), 2)
        if kk <= 0: continue
        cx = 290 + i * 500 - (40 if i == 0 else 0); cy = 1440
        ctx.save(); ctx.translate(cx, cy); ctx.scale(kk, kk); ctx.translate(-cx, -cy)
        bw = 440 if i else 380
        card(ctx, cx - bw / 2, cy - 75, bw, 150, 1, RED if i else BLUE_L, r=22)
        ctx.set_source_rgba(*(RED if i else BLUE), 1); ctx.arc(cx - bw / 2 + 75, cy, 52, 0, 2 * math.pi); ctx.fill()
        if ic == "s": icon_soldier(ctx, cx - bw / 2 + 75, cy + 6, 78, WHITE)
        else:
            ctx.save(); ctx.arc(cx - bw / 2 + 75, cy, 50, 0, 2 * math.pi); ctx.clip()
            icon_fence(ctx, cx - bw / 2 + 75, cy + 8, 60, WHITE); ctx.restore()
        font(ctx, "black", 30)
        ln = wrap(ctx, lab, bw - 170)
        for j, l in enumerate(ln):
            text(ctx, l, cx - bw / 2 + 150, cy + 10 - (len(ln) - 1) * 18 + j * 36, WHITE)
        ctx.restore()
    group_end(ctx, a)

def scene7(ctx, t):
    if not (S7[0] <= t < S7[1] + 0.05): return
    a = vis(t, 62.55, VOICE_END + 0.05, 0.3, 0.3)
    if a <= 0: return
    # pregunta palabra a palabra
    lines = [["¿DEBE", "RD"], ["SEGUIR", "APOYANDO"], ["A", "BUKELE"], ["EN", "HAITÍ?"]]
    times = [63.94, 64.3, 65.36, 65.74, 66.36, 66.46, 66.82, 66.96]
    font(ctx, "black", 100)
    y0 = 780; idx = 0
    big = ease(prog(t, 62.55, 62.9))
    ctx.save(); ctx.translate(0, (1 - big) * 40)
    font(ctx, "xbold", 34); text(ctx, "LA PREGUNTA ES…", W / 2, 625, GREY, a * big, "center", sp=4)
    font(ctx, "black", 100)
    for li, ln in enumerate(lines):
        widths = [tw(ctx, s) for s in ln]; sp = tw(ctx, " ")
        total = sum(widths) + sp * (len(ln) - 1)
        x = W / 2 - total / 2; y = y0 + li * 112
        for s, wd in zip(ln, widths):
            tt = times[idx] - 0.05; idx += 1
            k = back(prog(t, tt, tt + 0.25), 2)
            if k > 0:
                ctx.save(); ctx.translate(x + wd / 2, y - 40); ctx.scale(k, k); ctx.translate(-(x + wd / 2), -(y - 40))
                if s == "RD":
                    ctx.set_source_rgba(*BLUE_L, a); rrect(ctx, x - 12, y - 84, wd + 24, 98, 14); ctx.fill()
                    text(ctx, s, x, y, WHITE, a)
                else:
                    text(ctx, s, x, y, RED_L if s == "BUKELE" else WHITE, a, outline=14, ocol=(0.01, 0.03, 0.08), oa=0.9)
                ctx.restore()
            x += wd + sp
    ctx.restore()
    # encuesta
    pa = ease(prog(t, 67.7, 68.0))
    if pa > 0:
        group_begin(ctx)
        icon_bubble(ctx, 300, 1270, 70, 1)
        font(ctx, "black", 50); text(ctx, "COMENTA", 350, 1290, WHITE, 1, sp=3)
        group_end(ctx, pa * a)
    for i, (tt, lab, col) in enumerate(((68.15, "1 = SÍ", BLUE_L), (69.45, "2 = NO", RED))):
        k = back(prog(t, tt, tt + 0.3), 2.4)
        if k <= 0: continue
        cx = 285 + i * 510; cy = 1450
        ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k); ctx.translate(-cx, -cy)
        ctx.set_source_rgba(0, 0, 0, 0.4 * a); rrect(ctx, cx - 215, cy - 85 + 12, 430, 170, 30); ctx.fill()
        ctx.set_source_rgba(*col, a); rrect(ctx, cx - 215, cy - 85, 430, 170, 30); ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.35 * a); ctx.set_line_width(3); rrect(ctx, cx - 215, cy - 85, 430, 170, 30); ctx.stroke()
        font(ctx, "black", 84); text(ctx, lab, cx, cy + 30, WHITE, a, "center")
        ctx.restore()
    if t > 68.15:
        source_tag(ctx, "Encuesta en los comentarios", W / 2, 1600, a * ease(prog(t, 68.3, 68.7)), "center")

def draw_outro_bg(ctx, t, a=1.0):
    ctx.push_group()
    ctx.set_source_rgb(*NAVY); ctx.paint()
    g = cairo.RadialGradient(W / 2, 900, 50, W / 2, 900, 1000)
    g.add_color_stop_rgba(0, *NAVY2, 1); g.add_color_stop_rgba(1, 0.01, 0.03, 0.08, 1)
    ctx.set_source(g); ctx.paint()
    # rejilla en movimiento
    ctx.set_source_rgba(1, 1, 1, 0.05); ctx.set_line_width(1)
    off = (t * 30) % 60
    for gx in range(-60, W + 60, 60): ctx.move_to(gx + off, 0); ctx.line_to(gx + off, H)
    for gy in range(-60, H + 60, 60): ctx.move_to(0, gy + off); ctx.line_to(W, gy + off)
    ctx.stroke()
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)

def outro(ctx, t):
    if t < OUTRO[0]: return
    t0 = OUTRO[0] + 0.15
    d = ease_io(prog(t, t0, t0 + 0.9))
    cx, cy = W / 2 + 10, 820
    # halo rojo
    g = cairo.RadialGradient(cx, cy, 10, cx, cy, 420)
    g.add_color_stop_rgba(0, *RED, 0.35 * d); g.add_color_stop_rgba(1, *RED, 0)
    ctx.set_source(g); ctx.paint()
    icon_magnifier(ctx, cx, cy, 380, 1, d)
    qk = back(prog(t, t0 + 0.6, t0 + 1.0), 2.5)
    if qk > 0:
        ctx.save(); ctx.translate(cx - 30, cy - 30); ctx.scale(qk, qk)
        font(ctx, "black", 190); text(ctx, "?", 0, 68, RED_L, 1, "center")
        ctx.restore()
    tk = ease(prog(t, t0 + 0.9, t0 + 1.4))
    if tk > 0:
        font(ctx, "black", 92)
        text(ctx, "CAPITAL", W / 2, 1180 + (1 - tk) * 30, WHITE, tk, "center", sp=10)
        text(ctx, "CURIOSO", W / 2, 1285 + (1 - tk) * 30, RED_L, tk, "center", sp=10)
    hk = ease(prog(t, t0 + 1.3, t0 + 1.8))
    if hk > 0:
        font(ctx, "semi", 42); text(ctx, "@capitalcuriosoo", W / 2, 1390, GREY, hk, "center")
        flag_rd(ctx, W / 2 - 45, 1440, 90, 60, hk)
        font(ctx, "xbold", 34); text(ctx, "SÍGUENOS PARA MÁS", W / 2, 1580, WHITE, hk, "center", sp=4)
    ctx.set_source_rgba(0, 0, 0, ease_io(prog(t, DURATION - 0.45, DURATION))); ctx.paint()

# ======================================================================
def render_frame(t):
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(surf)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)
    draw_background(ctx, t)
    if t < OUTRO[0]: grade_overlays(ctx, t)
    scene1(ctx, t); scene2(ctx, t); scene3(ctx, t); scene4(ctx, t)
    scene5(ctx, t); scene6(ctx, t); scene7(ctx, t); outro(ctx, t)
    brand_bar(ctx, t); handle_tag(ctx, t)
    subtitles(ctx, t)
    if t < 0.35:  # entrada desde negro
        ctx.set_source_rgba(0, 0, 0, 1 - ease(t / 0.35)); ctx.paint()
    surf.flush()
    return surf

def worker(k, n0, n1):
    path = os.path.join(OUT, f"seg{k}.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "14",
                          "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for f in range(n0, n1):
        s = render_frame(f / FPS)
        p.stdin.write(bytes(s.get_data()))
    p.stdin.close(); p.wait()

def main():
    if "--frame" in sys.argv:
        for v in sys.argv[sys.argv.index("--frame") + 1:]:
            t = float(v); s = render_frame(t)
            s.write_to_png(os.path.join(OUT, f"frame_{v}.png")); print("ok", v)
        return
    total = int(round(DURATION * FPS))
    nproc = os.cpu_count() or 4
    step = math.ceil(total / nproc)
    ps = []
    for k in range(nproc):
        n0, n1 = k * step, min(total, (k + 1) * step)
        if n0 >= n1: continue
        p = Process(target=worker, args=(k, n0, n1)); p.start(); ps.append((k, p))
    for _, p in ps: p.join()
    with open(os.path.join(OUT, "segs.txt"), "w") as f:
        for k, _ in ps: f.write(f"file 'seg{k}.mp4'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(OUT, "segs.txt"),
                    "-c", "copy", os.path.join(OUT, "video_sin_audio.mp4")], check=True)
    for k, _ in ps: os.remove(os.path.join(OUT, f"seg{k}.mp4"))
    print("video listo:", total, "frames")

if __name__ == "__main__":
    main()
