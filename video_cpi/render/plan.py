"""Shared timeline for the CPI night video. All times in the FINAL timeline (seconds)."""
import json, os

S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = f"{S}/in"
IMG = f"{IN}/imagenes_video_cpi"
ASSETS = f"{S}/assets"
FONTS = f"{S}/fonts"
W_DIR = f"{S}/w"
VOICE = f"{IN}/fc18e521-content_7.mp3"
CIERRE = f"{IN}/c685b700-capital_curioso_cierre.mp4"

FPS = 30
W, H = 1080, 1920
RED = (214, 40, 40)

# 0.5 s of total silence inserted into the narration before the two key lines
GAPS = [(38.72, 0.5), (74.38, 0.5)]
VOICE_LEN = 83.33 + sum(g for _, g in GAPS)
MAIN_LEN = round(VOICE_LEN, 2)
CIERRE_LEN = 3.5
TOTAL = MAIN_LEN + CIERRE_LEN


def T(t):
    return t + sum(g for p, g in GAPS if t >= p)


WORDS = json.load(open(f"{W_DIR}/words.json"))
# onset corrections measured on the waveform
WORDS[99]["e"] = 38.50; WORDS[100]["s"] = 38.76
WORDS[190]["e"] = 74.24; WORDS[191]["s"] = 74.45
for w in WORDS:
    w["S"], w["E"] = T(w["s"]), T(w["e"])


def ws(i):
    return WORDS[i]["S"]


def we(i):
    return WORDS[i]["E"]


# Silence windows: music + sfx muted, picture goes black
SILENCES = [(we(99), ws(100)), (we(190), ws(191))]

# ---------------------------------------------------------------- SFX events
# (time, kind, gain)
SFX = []
def sfx(t, kind, g=1.0):
    SFX.append((t, kind, g))

# [1] hook
sfx(0.0, "static", 0.6); sfx(0.0, "boom", 1.0); sfx(0.0, "glitch", 0.7)
sfx(ws(2), "boom", 1.0); sfx(ws(2), "glitch", 0.7)
sfx(ws(4), "boom", 1.0); sfx(ws(4), "glitch", 0.7)
sfx(ws(6), "stamp", 1.0)
# [2] Shenzhen
sfx(ws(7) - 0.25, "whoosh", 0.7); sfx(ws(7), "glitch", 0.8)
for k in range(15):
    sfx(ws(7) + 0.25 + k * 0.075, "type", 0.5)
for k in range(6):
    sfx(ws(7) + 1.5 + k * 0.075, "type", 0.5)
sfx(ws(14), "boom", 0.9); sfx(ws(14), "glitch", 0.5)
sfx(ws(21), "glitch", 0.6)
sfx(ws(24), "boom", 0.8)
sfx(ws(27), "hit", 0.6)
sfx(ws(34), "glitch", 0.8); sfx(ws(36), "boom", 1.0)
# collab card
sfx(ws(39), "static", 0.5); sfx(ws(39), "glitch", 0.6)
sfx(ws(44), "hit", 0.6); sfx(ws(51), "hit", 0.6)
# declaration content
sfx(ws(53), "glitch", 0.7)
sfx(ws(65), "hit", 0.5)
sfx(ws(74), "boom", 0.9)
sfx(ws(75), "glitch", 0.8); sfx(ws(77), "boom", 0.9)
sfx(ws(78), "stamp", 0.8); sfx(ws(79) + 0.12, "stamp", 0.8); sfx(ws(81), "stamp", 0.8)
sfx(ws(86), "boom", 0.9); sfx(ws(86) + 0.05, "stamp", 0.9)
# "Pero aquí viene lo importante" -> clock, then silence
sfx(ws(95), "hit", 0.5)
for k in range(4):
    sfx(ws(95) + k * 0.42, "tick", 0.9 if k % 2 == 0 else 0.7)
sfx(ws(100), "boom", 1.0); sfx(ws(100), "glitch", 0.6)
sfx(ws(104), "boom", 1.0)
sfx(ws(106), "stamp", 1.0)
sfx(ws(109), "glitch", 0.8); sfx(ws(112), "boom", 0.9)
sfx(ws(119), "stamp", 1.0)
sfx(ws(120), "tick", 0.8); sfx(ws(121), "tick", 0.6)
sfx(ws(122), "glitch", 0.7)
sfx(ws(128), "hit", 0.5)
sfx(ws(137), "boom", 0.9)
sfx(ws(138), "glitch", 0.6)
sfx(ws(145), "hit", 0.6)
sfx(ws(147), "gavel", 0.7); sfx(ws(149), "gavel", 1.0); sfx(ws(149), "boom", 0.6)
# list of members
sfx(ws(150), "static", 0.5); sfx(ws(150), "glitch", 0.8)
sfx(ws(159), "hit", 0.6)
for i in (165, 166, 167, 168):
    sfx(ws(i), "tick", 0.8); sfx(ws(i), "type", 0.6)
sfx(ws(169), "boom", 1.0); sfx(ws(169), "stamp", 0.7)
sfx(ws(171), "glitch", 0.8); sfx(ws(177), "hit", 0.7)
sfx(ws(181), "glitch", 0.6); sfx(ws(184), "boom", 0.9)
sfx(ws(190), "whoosh", 0.6)
# key question after silence
sfx(ws(191), "boom", 1.2); sfx(ws(191), "glitch", 1.0)
sfx(ws(195), "boom", 1.0); sfx(ws(195), "glitch", 0.6)
sfx(ws(198), "boom", 1.0); sfx(ws(198), "glitch", 0.6)
# CTA
sfx(ws(201) - 0.2, "whoosh", 0.6); sfx(ws(201), "glitch", 0.6)
sfx(ws(205), "hit", 0.6)
sfx(ws(210), "hit", 0.5); sfx(ws(213), "hit", 0.5)
sfx(MAIN_LEN, "boom", 0.9); sfx(MAIN_LEN, "glitch", 0.5)

BOOM_TIMES = sorted(t for t, k, _ in SFX if k in ("boom", "gavel", "stamp"))
GLITCH_TIMES = sorted(t for t, k, _ in SFX if k == "glitch")
