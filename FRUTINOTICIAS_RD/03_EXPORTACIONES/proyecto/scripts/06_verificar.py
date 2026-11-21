"""Verificación del video final:
 1) Transcribe el audio exportado y compara palabra por palabra con la transcripción de los originales
    (orden, integridad y desfase temporal esperado según edl.json).
 2) Genera hojas de contacto de fotogramas reales del MP4 final para revisión visual."""
import subprocess, json, os, sys, re, unicodedata
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from comun import cargar_edl, tl, transcripcion, BUILD, PROY
from faster_whisper import WhisperModel
edl = cargar_edl(); SAL = os.path.dirname(PROY)
F = os.path.join(SAL, "FRUTINOTICIASRD_LANZAMIENTO_CINEMATOGRAFICO.mp4")
def norm(w): return re.sub(r"[^a-zñü]", "", unicodedata.normalize("NFC", w.lower()).replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u"))
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", F, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
m = WhisperModel("large-v3", device="cpu", compute_type="int8")
segs, _ = m.transcribe(audio, language="es", word_timestamps=True, beam_size=5)
got = [(norm(w.word), float(w.start)) for s in segs for w in s.words]
got = [g for g in got if g[0]]
tr = transcripcion(); exp = []
for c in edl["clips"]:
    for w in tr[c["archivo"]]["words"]:
        exp.append((norm(w["w"]), tl(edl, c["id"], w["s"]), c["id"]))
# alineación por secuencia
import difflib
sm = difflib.SequenceMatcher(a=[e[0] for e in exp], b=[g[0] for g in got], autojunk=False)
ok = 0; desf = []; faltan = []
for tag, a0, a1, b0, b1 in sm.get_opcodes():
    if tag == "equal":
        for i, j in zip(range(a0, a1), range(b0, b1)):
            ok += 1; desf.append(got[j][1] - exp[i][1])
    elif tag in ("replace", "delete"):
        faltan.append(("esperado", [e[0] for e in exp[a0:a1]], "oido", [g[0] for g in got[b0:b1]]))
    elif tag == "insert":
        faltan.append(("extra", [g[0] for g in got[b0:b1]]))
res = {"palabras_esperadas": len(exp), "coinciden_en_orden": ok, "diferencias": faltan,
       "desfase_medio_s": round(float(np.mean(desf)), 3), "desfase_max_abs_s": round(float(np.max(np.abs(desf))), 3)}
print(json.dumps(res, ensure_ascii=False, indent=1))
json.dump(res, open(os.path.join(SAL, "revision", "verificacion_dialogos.json"), "w"), ensure_ascii=False, indent=1)
# hojas de contacto
rev = os.path.join(SAL, "revision")
for k, (a, b) in enumerate(((0, 32), (32, 64))):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", str(b - a), "-i", F, "-vf",
                    "fps=1,scale=270:480,drawtext=fontfile=/usr/share/fonts/opentype/inter/Inter-Bold.otf:text='%{pts\\:hms}':x=6:y=6:fontsize=18:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=8x4",
                    "-frames:v", "1", os.path.join(rev, f"contacto_final_{k + 1}.jpg")], check=True)
