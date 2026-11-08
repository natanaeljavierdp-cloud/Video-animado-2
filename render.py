#!/usr/bin/env python3
"""Render "Su tierra es su historia" from video_spec.json.

Usage:
    python3 render.py                 # full render -> out/su-tierra-es-su-historia.mp4
    python3 render.py --stills        # one PNG per scene in out/stills/ (fast check)
    python3 render.py --half          # 540x960 preview render (4x faster)

Missing assets are handled gracefully:
  * a missing scene image is replaced by a labelled placeholder,
  * a missing logo is skipped,
  * missing audio files are skipped (the video renders silent).
If assets/subtitles_timed.json exists (list of {"start","end","text"}), it
replaces the automatic phrase timing for the subtitles.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
SPEC = json.load(open(os.path.join(ROOT, "video_spec.json"), encoding="utf-8"))
W, H = SPEC["format"]["width"], SPEC["format"]["height"]
FPS = SPEC["format"]["fps"]
DUR = SPEC["format"]["durationSec"]
COL = {k: v for k, v in SPEC["brand"]["colors"].items()}
SAFE_TOP = SPEC["brand"]["safeArea"]["top"]
SAFE_BOTTOM = SPEC["brand"]["safeArea"]["bottom"]

# Source images are 16:9, the video is 9:16. Each image is shown in a large
# central "band" with Ken Burns motion, over a blurred, navy-tinted copy of
# itself that fills the rest of the frame.
BAND_TOP, BAND_H = 470, 1000
BAND_FEATHER = 110
# Horizontal focus (0..1) of each image inside the band crop.
FOCUS = {
    "01_familia_cerca": 0.40,
    "02_arbol_genealogico": 0.50,
    "03_sello_titulo": 0.55,
    "04_casa_mecedora": 0.64,
    "05_terreno_se_vende": 0.34,
    "06a_registro_titulos": 0.42,
    "06b_familia_firmando": 0.50,
    "06c_lupa_contrato": 0.52,
    "07_familia_feliz": 0.46,
}
TRANSITION = {"crossfade": 0.6, "wipe": 0.5, "fadeToNavy": 0.6}


def hex_rgb(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def color(name, a=255):
    return hex_rgb(COL.get(name, name), a)


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_in_out(p):
    return 0.5 - 0.5 * math.cos(math.pi * clamp(p))


def ease_out_expo(p):
    p = clamp(p)
    return 1.0 if p >= 1 else 1 - 2 ** (-10 * p)


def ease_out_cubic(p):
    return 1 - (1 - clamp(p)) ** 3


def ease_out_back(p, s=1.9):
    p = clamp(p) - 1
    return p * p * ((s + 1) * p + s) + 1


EASE = {"easeOutExpo": ease_out_expo, None: ease_in_out}

# ---------------------------------------------------------------- fonts / text
FONT_FILES = {
    "title": (os.path.join(ROOT, "assets/fonts/PlayfairDisplay-VF.ttf"), 700),
    "body": (os.path.join(ROOT, "assets/fonts/Montserrat-VF.ttf"), 600),
}
_font_cache = {}


def font(style, size):
    key = (style, size)
    if key not in _font_cache:
        path, wght = FONT_FILES[style]
        f = ImageFont.truetype(path, size)
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
        _font_cache[key] = f
    return _font_cache[key]


def wrap(text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if fnt.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


_text_cache = {}


def text_layer(text, style, size, fill, max_w=940, stroke=None, shadow=True,
               line_gap=1.18, box=None):
    """Return an RGBA image containing centred, wrapped text."""
    key = (text, style, size, fill, max_w, stroke, shadow, box)
    if key in _text_cache:
        return _text_cache[key]
    fnt = font(style, size)
    lines = wrap(text, fnt, max_w)
    lh = int(size * line_gap)
    widths = [fnt.getlength(l) for l in lines]
    pad_x, pad_y = (box[0], box[1]) if box else (0, 0)
    margin = 40
    tw = int(max(widths)) + 2 * pad_x + 2 * margin
    th = lh * len(lines) + 2 * pad_y + 2 * margin
    img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    if box:
        bd = ImageDraw.Draw(img)
        bd.rounded_rectangle([margin, margin, tw - margin, th - margin],
                             radius=box[2], fill=box[3])
    if shadow:
        sh = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        for i, l in enumerate(lines):
            x = (tw - widths[i]) / 2
            y = margin + pad_y + i * lh + 6
            sd.text((x, y), l, font=fnt, fill=(0, 0, 0, 200))
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        img = Image.alpha_composite(img, sh)
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        x = (tw - widths[i]) / 2
        y = margin + pad_y + i * lh
        if stroke:
            d.text((x, y), l, font=fnt, fill=fill, stroke_width=stroke[0],
                   stroke_fill=stroke[1])
        else:
            d.text((x, y), l, font=fnt, fill=fill)
    _text_cache[key] = img
    return img


def paste_layer(canvas, layer, cx, cy, alpha=1.0, scale=1.0):
    if alpha <= 0.003:
        return
    if abs(scale - 1.0) > 1e-3:
        nw = max(1, int(layer.width * scale))
        nh = max(1, int(layer.height * scale))
        layer = layer.resize((nw, nh), Image.BICUBIC)
    if alpha < 0.999:
        a = layer.getchannel("A").point(lambda v: int(v * alpha))
        layer = layer.copy()
        layer.putalpha(a)
    x = int(round(cx - layer.width / 2))
    y = int(round(cy - layer.height / 2))
    canvas.alpha_composite(layer, (max(0, x), max(0, y)),
                           (max(0, -x), max(0, -y)))


# ---------------------------------------------------------------- images
_img_cache = {}


def placeholder(name):
    img = Image.new("RGB", (1280, 720), color("navy")[:3])
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 1240, 680], outline=color("gold")[:3], width=6)
    f = font("body", 44)
    for i, line in enumerate(["FALTA LA IMAGEN", name]):
        tw = f.getlength(line)
        d.text(((1280 - tw) / 2, 300 + i * 70), line, font=f,
               fill=color("cream")[:3])
    return img


def load_image(path):
    if path in _img_cache:
        return _img_cache[path]
    full = os.path.join(ROOT, path)
    name = os.path.splitext(os.path.basename(path))[0]
    src = Image.open(full).convert("RGB") if os.path.exists(full) else placeholder(name + ".png")
    # Blurred, navy-tinted full-frame background (static per image).
    s = max(W / src.width, H / src.height)
    bg = src.resize((int(src.width * s) + 1, int(src.height * s) + 1), Image.BICUBIC)
    bx, by = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((bx, by, bx + W, by + H)).filter(ImageFilter.GaussianBlur(38))
    bg = Image.blend(bg, Image.new("RGB", (W, H), color("navy")[:3]), 0.55)
    _img_cache[path] = (src, bg.convert("RGBA"), name)
    return _img_cache[path]


_band_mask = None


def band_mask():
    global _band_mask
    if _band_mask is None:
        m = Image.new("L", (W, BAND_H), 255)
        d = ImageDraw.Draw(m)
        for i in range(BAND_FEATHER):
            v = int(255 * ease_in_out(i / BAND_FEATHER))
            d.line([(0, i), (W, i)], fill=v)
            d.line([(0, BAND_H - 1 - i), (W, BAND_H - 1 - i)], fill=v)
        _band_mask = m
    return _band_mask


def ken_burns(src, focus_x, motion, p):
    """Crop+resize the source for progress p in [0,1] into a W x BAND_H band."""
    base = max(W / src.width, BAND_H / src.height)
    mtype = motion.get("type", "zoomIn")
    ease = EASE.get(motion.get("easing"), ease_in_out)
    e = ease(p)
    dx = dy = 0.0
    if mtype in ("zoomIn", "zoomOut"):
        z = motion.get("from", 1.0) + (motion.get("to", 1.1) - motion.get("from", 1.0)) * e
    else:
        z = motion.get("zoom", 1.15)
        dist = motion.get("distance", 100) / (base * z)  # output px -> source px
        if mtype == "panDown":
            dy = (e - 0.5) * dist
        elif mtype == "panUp":
            dy = (0.5 - e) * dist
        elif mtype == "panRight":
            dx = (e - 0.5) * dist
        elif mtype == "panLeft":
            dx = (0.5 - e) * dist
    vw, vh = W / (base * z), BAND_H / (base * z)
    cx = clamp(focus_x * src.width + dx, vw / 2, src.width - vw / 2)
    cy = clamp(src.height / 2 + dy, vh / 2, src.height - vh / 2)
    box = (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2)
    return src.resize((W, BAND_H), Image.BICUBIC, box=box)


def image_frame(path, motion, p, opacity=1.0, bg_override=None):
    src, bg, name = load_image(path)
    canvas = (bg_override or bg).copy()
    band = ken_burns(src, FOCUS.get(name, 0.5), motion, p).convert("RGBA")
    mask = band_mask()
    if opacity < 0.999:
        mask = mask.point(lambda v: int(v * opacity))
    canvas.paste(band, (0, BAND_TOP), mask)
    return canvas


# ---------------------------------------------------------------- subtitles
def split_phrases(text, max_chars=34):
    text = text.replace("…", "… ").strip()
    parts = re.split(r"(?<=[,.…?:!])\s+", text)
    out = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        words, cur = part.split(), ""
        for w in words:
            trial = (cur + " " + w).strip()
            if len(trial) > max_chars and cur:
                out.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            out.append(cur)
    # merge very short tails ("Uno:", "Dos:") into the next phrase
    merged = []
    for ph in out:
        if merged and len(merged[-1]) <= 6:
            merged[-1] = merged[-1] + " " + ph
        else:
            merged.append(ph)
    return merged


def build_subtitles():
    timed = os.path.join(ROOT, "assets/subtitles_timed.json")
    if os.path.exists(timed):
        return json.load(open(timed, encoding="utf-8"))
    subs = []
    for sc in SPEC["scenes"]:
        vo = sc.get("voiceover")
        if not vo:
            continue
        start, end = sc["start"] + 0.15, sc["end"] - 0.2
        phrases = split_phrases(vo)
        total = sum(len(p) + 6 for p in phrases)
        t = start
        for ph in phrases:
            d = (end - start) * (len(ph) + 6) / total
            subs.append({"start": round(t, 3), "end": round(t + d, 3), "text": ph})
            t += d
    return subs


SUBS = build_subtitles()
SUB_CFG = SPEC["subtitles"]


def sub_box_color():
    m = re.match(r"rgba\((\d+),(\d+),(\d+),([\d.]+)\)", SUB_CFG["background"].replace(" ", ""))
    return (int(m[1]), int(m[2]), int(m[3]), int(float(m[4]) * 255))


def draw_subtitles(canvas, t):
    if not SUB_CFG.get("enabled"):
        return
    for s in SUBS:
        if s["start"] <= t < s["end"]:
            layer = text_layer(s["text"], SUB_CFG["style"], 50, color(SUB_CFG["color"]),
                               max_w=880, shadow=False, line_gap=1.25,
                               box=(30, 18, 22, sub_box_color()))
            a = clamp((t - s["start"]) / 0.12)
            bottom = H - SAFE_BOTTOM
            paste_layer(canvas, layer, W / 2, bottom - layer.height / 2 + 40, a)
            return


# ---------------------------------------------------------------- overlays
def draw_map(canvas, alpha):
    """Small stylised map of the north coast with two gold points."""
    if alpha <= 0:
        return
    mw, mh = 860, 250
    m = Image.new("RGBA", (mw, mh), (0, 0, 0, 0))
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, mw - 1, mh - 1], radius=26, fill=color("navy", 225),
                        outline=color("gold", 255), width=3)
    # ocean label and a hand-made coastline (west -> east)
    pts = [(40, 92), (120, 100), (170, 130), (250, 120), (330, 104), (420, 112),
           (500, 140), (560, 128), (640, 108), (720, 116), (820, 104)]
    d.line(pts, fill=color("cream", 230), width=5, joint="curve")
    d.text((mw / 2, 46), "OCÉANO ATLÁNTICO", font=font("body", 24),
           fill=color("cream", 150), anchor="mm")
    for (x, y), label in (((170, 130), "Punta Rucia"), ((560, 128), "Luperón")):
        d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=color("gold"))
        d.ellipse([x - 26, y - 26, x + 26, y + 26], outline=color("gold", 140), width=3)
        d.text((x, y + 66), label, font=font("body", 38), fill=color("gold"), anchor="mm")
    paste_layer(canvas, m, W / 2, BAND_TOP + BAND_H - 200 - (1 - ease_out_cubic(alpha)) * -30,
                ease_out_cubic(alpha))


def flash_shake(canvas, t, at, dur=0.35):
    """Hit at `at`: brief white flash + camera shake (matches golpe.mp3)."""
    k = (t - at) / dur
    if not (0 <= k < 1):
        return canvas
    amp = 22 * (1 - k)
    ox = int(amp * math.sin(t * 90))
    oy = int(amp * math.cos(t * 70))
    shaken = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    shaken.paste(canvas, (ox, oy))
    flash = Image.new("RGBA", (W, H), (255, 255, 255, int(150 * (1 - k) ** 2)))
    return Image.alpha_composite(shaken, flash)


# ---------------------------------------------------------------- scenes
NAVY_BG = None


def navy_bg():
    global NAVY_BG
    if NAVY_BG is None:
        import random
        rnd = random.Random(7)
        base = Image.new("RGB", (W // 4, H // 4), color("navy")[:3])
        px = base.load()
        r0, g0, b0 = color("navy")[:3]
        for y in range(base.height):
            for x in range(base.width):
                n = rnd.randint(-5, 5)
                px[x, y] = (r0 + n, g0 + n, b0 + n)
        tex = base.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(1.2))
        # subtle vignette
        vig = Image.new("L", (W, H), 0)
        vd = ImageDraw.Draw(vig)
        for i in range(0, 400, 4):
            vd.rectangle([i, i, W - i, H - i], outline=int(90 * (1 - i / 400)))
        vig = vig.filter(ImageFilter.GaussianBlur(60))
        tex.paste((4, 12, 26), (0, 0), vig)
        NAVY_BG = tex.convert("RGBA")
    return NAVY_BG


def title_anim(t, start, delay=0.15, dur=0.55):
    p = clamp((t - start - delay) / dur)
    return ease_out_cubic(p), (1 - ease_out_cubic(p)) * 40


def draw_scene_texts(canvas, sc, t):
    for i, tx in enumerate(sc.get("text", [])):
        style = tx["style"]
        size = 92 if style == "title" else 64
        fill = color(tx["color"])
        stroke = (3, color("cream")) if tx["color"] == "alert" else None
        layer = text_layer(tx["value"], style, size, fill, stroke=stroke)
        a, dy = title_anim(t, sc["start"], delay=0.15 + 0.12 * i)
        if tx.get("position") == "lowerThird":
            cy = BAND_TOP + BAND_H - 230
        else:  # title zone between the top safe area and the image band
            cy = SAFE_TOP + 115 if layer.height < 230 else SAFE_TOP + 140
        paste_layer(canvas, layer, W / 2, cy + dy, a)


def render_image_scene(sc, t):
    p = (t - sc["start"]) / (sc["end"] - sc["start"])
    canvas = image_frame(sc["image"], sc.get("motion", {}), p)
    if sc.get("overlay", {}).get("type") == "map":
        draw_map(canvas, clamp((t - sc["overlay"]["appearAt"]) / 0.6))
    draw_scene_texts(canvas, sc, t)
    for sfx in SPEC["audio"].get("sfx", []):
        if sc["start"] <= sfx["at"] < sc["end"]:
            canvas = flash_shake(canvas, t, sfx["at"])
    return canvas


def render_steps_scene(sc, t):
    steps = sc["steps"]
    st = sc.get("stepStyle", {})
    cur = steps[-1]
    for s in steps:
        if t < s["end"]:
            cur = s
            break
    p = (t - cur["start"]) / (cur["end"] - cur["start"])
    canvas = image_frame(cur["image"], {"type": "zoomIn", "from": 1.0, "to": 1.08}, p,
                         opacity=st.get("imageOpacity", 0.35), bg_override=navy_bg())
    # cross-fade between steps
    idx = steps.index(cur)
    if idx > 0 and t - cur["start"] < 0.3:
        prev = steps[idx - 1]
        prev_c = image_frame(prev["image"], {"type": "zoomIn", "from": 1.0, "to": 1.08}, 1.0,
                             opacity=st.get("imageOpacity", 0.35), bg_override=navy_bg())
        canvas = Image.blend(prev_c, canvas, (t - cur["start"]) / 0.3)
    lt = t - cur["start"]
    # big gold number, pop-in
    num = text_layer(str(cur["n"]), "title", 360, color(st.get("numberColor", "gold")),
                     shadow=True)
    ps = clamp(lt / 0.45)
    paste_layer(canvas, num, W / 2, 790, clamp(lt / 0.15), max(0.01, ease_out_back(ps)))
    # step dots
    for j in range(len(steps)):
        x = W / 2 + (j - 1) * 48
        r = 11 if j == idx else 7
        dd = ImageDraw.Draw(canvas)
        dd.ellipse([x - r, SAFE_TOP + 40 - r, x + r, SAFE_TOP + 40 + r],
                   fill=color("gold") if j <= idx else color("cream", 90))
    a1, dy1 = title_anim(t, cur["start"], delay=0.25)
    a2, dy2 = title_anim(t, cur["start"], delay=0.45)
    paste_layer(canvas, text_layer(cur["title"], "title", 96, color("cream")), W / 2,
                1090 + dy1, a1)
    sub = cur["subtitle"][0].upper() + cur["subtitle"][1:]
    paste_layer(canvas, text_layer(sub, "body", 52, color("gold"), max_w=900), W / 2,
                1215 + dy2, a2)
    return canvas


def render_cta_scene(sc, t):
    canvas = navy_bg().copy()
    lt = t - sc["start"]
    logo = sc.get("logo")
    texts = list(sc["text"])
    has_logo = logo and os.path.exists(os.path.join(ROOT, logo["file"]))
    if has_logo:
        # The logo already carries the firm's name: show it big, skip the name line.
        li = Image.open(os.path.join(ROOT, logo["file"])).convert("RGBA")
        li.thumbnail((560, 560), Image.LANCZOS)
        p = clamp(lt / 0.8)
        paste_layer(canvas, li, W / 2, 620, p, 0.92 + 0.08 * ease_out_cubic(p))
        texts = texts[1:]
        top, rows = 1010, [(58, 0), (60, 150), (50, 235)]
    else:
        top, rows = 760, [(118, 0), (58, 118), (60, 290), (50, 380)]
    for i, (size, dy) in enumerate(rows):
        if i >= len(texts):
            continue
        tx = texts[i]
        layer = text_layer(tx["value"], tx["style"], size, color(tx["color"]), max_w=960)
        a, off = title_anim(t, sc["start"], delay=0.5 + 0.3 * i)
        paste_layer(canvas, layer, W / 2, top + dy + off, a)
    line_y = top + (75 if has_logo else 200)
    w = 260 * ease_out_cubic(clamp((lt - 0.9) / 0.5))
    if w > 1:
        ImageDraw.Draw(canvas).line([(W / 2 - w / 2, line_y), (W / 2 + w / 2, line_y)],
                                    fill=color("gold"), width=4)
    return canvas


def render_scene(sc, t):
    if "steps" in sc:
        return render_steps_scene(sc, t)
    if "image" in sc:
        return render_image_scene(sc, t)
    return render_cta_scene(sc, t)


def render_frame(t):
    scenes = SPEC["scenes"]
    idx = next((i for i, s in enumerate(scenes) if t < s["end"]), len(scenes) - 1)
    sc = scenes[idx]
    canvas = render_scene(sc, t)
    tr = sc.get("transitionOut", "cut")
    d = TRANSITION.get(tr, 0)
    if d and idx + 1 < len(scenes) and t > sc["end"] - d:
        k = ease_in_out((t - (sc["end"] - d)) / d)
        nxt = scenes[idx + 1]
        if tr == "fadeToNavy":
            canvas = Image.blend(canvas, navy_bg(), k)
        else:
            other = render_scene(nxt, nxt["start"])
            if tr == "crossfade":
                canvas = Image.blend(canvas, other, k)
            elif tr == "wipe":
                x = int(W * k)
                canvas.paste(other.crop((0, 0, x, H)), (0, 0))
                if 0 < x < W:
                    ImageDraw.Draw(canvas).rectangle([x - 4, 0, x + 4, H], fill=color("gold"))
    # fade in from navy at the very start
    if t < 0.25:
        canvas = Image.blend(navy_bg(), canvas, t / 0.25)
    draw_subtitles(canvas, t)
    return canvas.convert("RGB")


# ---------------------------------------------------------------- output
def audio_args():
    a = SPEC["audio"]
    inputs, filters, labels = [], [], []
    n = 1  # input 0 is the video pipe

    def add(path):
        nonlocal n
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            print(f"  (sin audio: falta {path})")
            return None
        inputs.extend(["-i", full])
        n += 1
        return n - 1

    vi = add(a["voiceover"])
    if vi is not None:
        filters.append(f"[{vi}:a]aresample=48000,volume=1.0[vo]")
        labels.append("[vo]")
    mi = add(a["music"])
    if mi is not None:
        filters.append(f"[{mi}:a]aresample=48000,volume={a['musicVolume']},"
                       f"atrim=0:{DUR},afade=t=out:st={DUR - 2.5}:d=2.5[mu]")
        labels.append("[mu]")
    for j, s in enumerate(a.get("sfx", [])):
        si = add(s["file"])
        if si is not None:
            ms = int(s["at"] * 1000)
            filters.append(f"[{si}:a]aresample=48000,adelay={ms}|{ms}[sfx{j}]")
            labels.append(f"[sfx{j}]")
    if not labels:
        return inputs, []
    filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=longest,"
                   f"apad,atrim=0:{DUR}[aout]")
    return inputs, ["-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[aout]",
                    "-c:a", "aac", "-b:a", "192k"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--half", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", SPEC["project"] + ".mp4"))
    args = ap.parse_args()
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)

    if args.stills:
        d = os.path.join(ROOT, "out", "stills")
        os.makedirs(d, exist_ok=True)
        times = []
        for sc in SPEC["scenes"]:
            if "steps" in sc:
                times += [(f"{sc['id']}{chr(96 + s['n'])}", s["start"] + 2.5) for s in sc["steps"]]
            else:
                times.append((str(sc["id"]), sc["start"] + (sc["end"] - sc["start"]) * 0.6))
        for name, t in times:
            render_frame(t).save(os.path.join(d, f"escena_{name}.png"))
            print("still", name, t)
        return

    ow, oh = (W // 2, H // 2) if args.half else (W, H)
    ain, amap = audio_args()
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{ow}x{oh}", "-r", str(FPS), "-i", "-", *ain]
    cmd += amap or ["-map", "0:v"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-t", str(DUR), args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(round(DUR * FPS))
    for f in range(total):
        img = render_frame(f / FPS)
        if args.half:
            img = img.resize((ow, oh), Image.BILINEAR)
        proc.stdin.write(img.tobytes())
        if f % FPS == 0:
            print(f"\r  {f // FPS:>2}/{DUR}s", end="", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"\nListo: {args.out}")


if __name__ == "__main__":
    sys.exit(main())
