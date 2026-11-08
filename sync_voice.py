#!/usr/bin/env python3
"""Align the narrator script with assets/voz.mp3 and retime the video.

No speech-recognition model is needed: the script text is known, so we
1. detect the speech segments in the audio (ffmpeg silencedetect),
2. split the script into short phrases and count their syllables,
3. assign phrases to segments with dynamic programming so that each
   segment's duration matches its syllable count as closely as possible,
4. write assets/subtitles_timed.json and retime the scenes in video_spec.json.

If assets/voz_alineacion.json exists it is used as-is instead of step 3 (the
automatic guess); fix any phrase time there and re-run.
Run it again whenever the voice file changes:  python3 sync_voice.py
"""
import json
import math
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
VOICE = os.path.join(ROOT, "assets/voz.mp3")

# Script, one entry per scene id. Phrases are split on punctuation below.
SCRIPT = [
    (1, "En Puerto Plata hay familias que perdieron su tierra… sin haber vendido nada."),
    (2, "Herederos falsos."),
    (3, "Deslindes irregulares. Títulos que aparecen… de la nada. Desde Punta Rucia "
        "hasta Luperón, esto no es un rumor. Está en los tribunales."),
    (4, "¿Y sabe por qué pasa? Porque muchas familias dejan la herencia… \"pa' después\". "
        "El abuelo muere, nadie hace la sucesión, nadie deslinda…"),
    (5, "y esa tierra queda servida para el que llegue con papeles."),
    ("6a", "Tres cosas que usted puede hacer hoy. Uno: verifique en el Registro de Títulos "
           "a nombre de quién está su terreno."),
    ("6b", "Dos: si hay herederos, formalice la sucesión."),
    ("6c", "Tres: si va a comprar, no compre con una simple constancia sin revisión legal."),
    (7, "Su tierra es su historia. No deje que otro la escriba."),
    (8, "Sandoval Legal, abogados en Puerto Plata. Escríbanos y revisamos su caso."),
]


def speech_segments(path, noise="-35dB", min_sil=0.12):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af",
                          f"silencedetect=noise={noise}:d={min_sil}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    h, m, sec = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    dur = int(h) * 3600 + int(m) * 60 + float(sec)
    events = sorted([(float(x), "s") for x in re.findall(r"silence_start: (-?[\d.]+)", out)] +
                    [(float(x), "e") for x in re.findall(r"silence_end: ([\d.]+)", out)])
    segs, t, in_speech = [], 0.0, True
    for when, kind in events:
        when = max(0.0, when)
        if kind == "s" and in_speech:
            if when - t > 0.08:
                segs.append((t, when))
            in_speech = False
        elif kind == "e":
            t, in_speech = when, True
    if in_speech and dur - t > 0.08:
        segs.append((t, dur))
    return segs, dur


def syllables(text):
    t = text.lower()
    t = re.sub(r"[^a-záéíóúüñ ]", " ", t)
    n = 0
    for w in t.split():
        # vowel groups; strong-strong vowel pairs (ae, eo, ...) count as two
        groups = re.findall(r"[aeiouáéíóúü]+", w)
        for g in groups:
            n += 1 + len(re.findall(r"(?=[aeoáéó][aeoáéó])", g))
    return max(1, n)


def phrases():
    out = []
    for scene, text in SCRIPT:
        for p in re.split(r"(?<=[,.…?:!\"])\s+", text):
            p = p.strip()
            if p:
                out.append({"scene": scene, "text": p, "syl": syllables(p)})
    return out


def boundary_cost(text, gap):
    """Cost of a pause of `gap` seconds right after `text` (None = mid-phrase)."""
    end = text[-1] if text else ""
    long = gap >= 1.0
    if end in ".…?!\"":
        return 0.0 if long else 0.35
    if end in ",:":
        return 0.6 if long else 0.0
    return 4.0 if long else 1.2  # pause inside a phrase


def align(segs, units):
    total_syl = sum(u["syl"] for u in units)
    total_dur = sum(e - s for s, e in segs)
    rate = total_syl / total_dur  # syllables per second
    S, U = len(segs), len(units)
    INF = float("inf")
    pre = [0]
    for u in units:
        pre.append(pre[-1] + u["syl"])
    gaps = [segs[i + 1][0] - segs[i][1] for i in range(S - 1)] + [9.9]
    # State: (i segments used, j units fully used, f = fraction of unit j already
    # spoken in earlier segments, discretised). For simplicity a unit may be split
    # across at most 2 segments, at a syllable-proportional point chosen freely.
    dp = [[INF] * (U + 1) for _ in range(S + 1)]
    back = [[None] * (U + 1) for _ in range(S + 1)]
    dp[0][0] = 0.0

    def seg_cost(d, syl):
        return 2.0 * math.log(d * rate / syl) ** 2

    for i in range(1, S + 1):
        d = segs[i - 1][1] - segs[i - 1][0]
        g = gaps[i - 1]
        for j in range(1, U + 1):
            for k in range(max(0, j - 8), j):
                if dp[i - 1][k] == INF:
                    continue
                c = dp[i - 1][k] + seg_cost(d, pre[j] - pre[k]) + \
                    boundary_cost(units[j - 1]["text"], g)
                if c < dp[i][j]:
                    dp[i][j], back[i][j] = c, ("whole", k)
            # segments i-1 and i together cover units k..j-1 with a mid-phrase pause
            if i >= 2:
                d2 = d + segs[i - 2][1] - segs[i - 2][0]
                for k in range(max(0, j - 8), j):
                    if dp[i - 2][k] == INF:
                        continue
                    c = dp[i - 2][k] + seg_cost(d2, pre[j] - pre[k]) + \
                        boundary_cost("x", gaps[i - 2]) + boundary_cost(units[j - 1]["text"], g)
                    if c < dp[i][j]:
                        dp[i][j], back[i][j] = c, ("pair", k)
    groups, i, j = [], S, U
    while i > 0:
        kind, k = back[i][j]
        if kind == "whole":
            groups.append(([i - 1], k, j)); i -= 1
        else:
            groups.append(([i - 2, i - 1], k, j)); i -= 2
        j = k
    groups.reverse()
    timed = [dict(u) for u in units]
    for seg_ids, k, j in groups:
        # map syllables onto the concatenated speech time of these segments
        spans = [segs[x] for x in seg_ids]
        tot = sum(e - s for s, e in spans)
        syl = pre[j] - pre[k]

        def at(frac):
            t = frac * tot
            for s, e in spans:
                if t <= e - s + 1e-9:
                    return s + t
                t -= e - s
            return spans[-1][1]
        acc = 0
        for x in range(k, j):
            timed[x]["start"] = round(at(acc / syl), 2)
            acc += units[x]["syl"]
            timed[x]["end"] = round(at(acc / syl), 2)
    return timed, rate


def subtitle_lines(timed, max_chars=34):
    """Merge very short phrases with their neighbour for readable captions."""
    subs = []
    for u in timed:
        text = u["text"]
        if subs and (len(subs[-1]["text"]) + len(text) + 1 <= max_chars) and \
                subs[-1]["scene"] == u["scene"] and u["start"] - subs[-1]["end"] < 0.5:
            subs[-1]["text"] += " " + text
            subs[-1]["end"] = u["end"]
        else:
            subs.append({"scene": u["scene"], "text": text, "start": u["start"], "end": u["end"]})
    # hold each caption until the next one starts (max 0.6 s extra)
    for a, b in zip(subs, subs[1:]):
        a["end"] = round(min(b["start"], a["end"] + 0.6), 2)
    subs[-1]["end"] = round(subs[-1]["end"] + 0.6, 2)
    return subs


def main():
    manual = os.path.join(ROOT, "assets/voz_alineacion.json")
    if os.path.exists(manual):
        # Hand-checked alignment (edit this file to fix any subtitle timing).
        timed = json.load(open(manual, encoding="utf-8"))
        dur = speech_segments(VOICE)[1] if os.path.exists(VOICE) else timed[-1]["end"] + 0.3
        print(f"Voz: {dur:.2f}s · usando {os.path.relpath(manual, ROOT)}")
    else:
        segs, dur = speech_segments(VOICE)
        timed, rate = align(segs, phrases())
        print(f"Voz: {dur:.2f}s · {len(segs)} tramos de habla · {rate:.2f} sílabas/s")
    for u in timed:
        print(f"  {u['start']:6.2f}-{u['end']:6.2f}  [{u['scene']}] {u['text']}")

    first = {}
    for u in timed:
        first.setdefault(u["scene"], u["start"])

    spec_path = os.path.join(ROOT, "video_spec.json")
    spec = json.load(open(spec_path, encoding="utf-8"))
    lead = 0.25  # cut a little before the words
    total = round(math.ceil((dur + 2.0) * 10) / 10, 1)  # hold the closing ~2 s

    def cut(key, fallback):
        return round(max(0.0, first.get(key, fallback) - lead), 2)

    # Scene 3 (the stamp) cuts in on "Títulos que aparecen…", so scene 2 keeps
    # "Herederos falsos. Deslindes irregulares." and stays on screen long enough.
    titulos = next((u["start"] for u in timed if u["text"].startswith("Títulos")), None)
    bounds = {1: 0.0, 2: cut(2, 5), 3: round(titulos - lead, 2) if titulos else cut(3, 9), 4: cut(4, 15), 5: cut(5, 24),
              6: cut("6a", 30), 7: cut(7, 45), 8: cut(8, 50)}
    ids = sorted(bounds)
    for sc in spec["scenes"]:
        i = ids.index(sc["id"])
        sc["start"] = bounds[sc["id"]]
        sc["end"] = bounds[ids[i + 1]] if i + 1 < len(ids) else total
        if "steps" in sc:
            sb = [sc["start"], cut("6b", 35), cut("6c", 40), sc["end"]]
            for n, st in enumerate(sc["steps"]):
                st["start"], st["end"] = sb[n], sb[n + 1]
        if sc.get("overlay", {}).get("type") == "map":
            punta = next(u for u in timed if "Punta Rucia" in u["text"])
            sc["overlay"]["appearAt"] = round(punta["start"] - 0.2, 2)
        if sc["id"] == 8:
            sc["voiceover"] = SCRIPT[-1][1]
    spec["format"]["durationSec"] = total
    for s in spec["audio"].get("sfx", []):
        s["at"] = bounds[3]
    json.dump(spec, open(spec_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    subs = subtitle_lines(timed)
    json.dump([{k: s[k] for k in ("start", "end", "text")} for s in subs],
              open(os.path.join(ROOT, "assets/subtitles_timed.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\nEscenas:", {k: v for k, v in bounds.items()}, "· duración total", total)


if __name__ == "__main__":
    main()
