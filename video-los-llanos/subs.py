"""Construye los grupos de subtítulos (2-4 palabras) a partir de build/words.json
(marcas por palabra de Whisper) y escribe build/subs.json + los_llanos_subtitulos.srt."""
import json, re

words = json.load(open("build/words.json"))

# Correcciones de palabras mal transcritas (sección 3.4 del brief + errores vistos)
FIX = {
    "LIBERTAD": "¡libertad!",
    "Lleve": "Llueve",
    "sismab": "SISMAP",
    "Botar": "Votar",
    "gobierno": "Gobierno",
    "este.": "Este.",
}
out = []
for i, w in enumerate(words):
    t = w["w"]
    t = FIX.get(t, t)
    if t.lower().startswith("llanos"):
        t = "Llanos" + t[6:]
        if out and out[-1]["w"].lower() == "los" and out[-2]["w"] != "de":
            out[-1]["w"] = "Los"
    if t.lower().startswith("sismap"):
        t = "SISMAP" + t[6:]
    if t == "están" and out and out[-1]["w"] == "Llanos":
        t = "está"  # guion: "Los Llanos está en el puesto 146"
    if t == "jóvenes" and words[i + 1]["w"] == "pierde":
        t = "jóvenes,"
    out.append({"w": t, "s": w["s"], "e": w["e"]})

# Arreglo del primer segundo: Whisper pone "Este" en 0.0
groups = []
cur = []
for i, w in enumerate(out):
    cur.append(w)
    nxt = out[i + 1] if i + 1 < len(out) else None
    chars = sum(len(x["w"]) + 1 for x in cur)
    end_punct = re.search(r"[.,?!:;…]$", w["w"]) is not None
    gap = (nxt["s"] - w["e"]) if nxt else 9
    nxt_len = len(nxt["w"]) if nxt else 0
    keep = nxt is not None and (nxt["w"].startswith("Llanos") or nxt["w"].startswith("Matas")
                                or (w["w"] in ("San", "José") and len(cur) < 4))
    if keep and not end_punct:
        continue
    if (nxt is None or end_punct or gap > 0.35 or len(cur) >= 4
            or chars + nxt_len > 20 or (len(cur) >= 2 and chars + nxt_len > 17 and nxt_len > 8)):
        groups.append(cur)
        cur = []

subs = []
for gi, g in enumerate(groups):
    start = g[0]["s"]
    end = g[-1]["e"]
    if gi + 1 < len(groups):
        end = min(end + 0.35, groups[gi + 1][0]["s"])
    else:
        end = end + 0.6
    subs.append({"start": round(start, 3), "end": round(end, 3), "words": g})

json.dump(subs, open("build/subs.json", "w"), ensure_ascii=False, indent=1)


def ts(x):
    ms = int(round(x * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


with open("los_llanos_subtitulos.srt", "w", encoding="utf-8") as f:
    for i, s in enumerate(subs, 1):
        f.write(f"{i}\n{ts(s['start'])} --> {ts(s['end'])}\n{' '.join(w['w'] for w in s['words'])}\n\n")
print(len(subs), "grupos")
for s in subs[:12]:
    print(s["start"], s["end"], " ".join(w["w"] for w in s["words"]))
