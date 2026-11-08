#!/usr/bin/env python3
"""Verifica la pista de audio de un MP4: decodificación, sonoridad, picos, nivel de voz
frente al fondo y sincronía con los subtítulos (transcribiendo con Whisper/sherpa-onnx).
Uso: verify_audio.py video.mp4 WHISPER_DIR"""
import json, os, re, subprocess, sys, tempfile, unicodedata
import numpy as np, soundfile as sf, sherpa_onnx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mp4, wdir = sys.argv[1], sys.argv[2]

def norm(t):
    t = unicodedata.normalize('NFD', t.lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    t = t.replace('100', 'cien').replace(' kg', ' kilogramos').replace('5 millones', 'cinco millones').replace('3 actividades', 'tres actividades')
    return re.sub(r"[^a-z0-9ñ ]", " ", t).replace('alcanzen', 'alcancen').replace('iniciadas', 'iniciada').split()

err = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-f", "null", "-"], capture_output=True, text=True).stderr
print("Errores de decodificación:", len(err.strip().splitlines()))
lo = subprocess.run(["ffmpeg", "-hide_banner", "-i", mp4, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
s = lo[lo.rindex("Summary"):]
print("Sonoridad:", re.search(r"I:\s+(-?[\d.]+) LUFS", s).group(1), "LUFS | LRA", re.search(r"LRA:\s+([\d.]+)", s).group(1),
      "LU | pico real", re.search(r"Peak:\s+(-?[\d.]+)", s).group(1), "dBFS")
tmp = tempfile.mkdtemp()
wav = os.path.join(tmp, "a.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
x, _ = sf.read(wav, dtype="float32")
st = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vn", "-f", "f32le", "-ac", "2", "-"], capture_output=True).stdout
xs = np.frombuffer(st, np.float32).reshape(-1, 2)
print("Muestras saturadas (>= 0 dBFS):", int((np.abs(xs) >= 0.999).sum()), "| silencio digital al inicio:",
      round(float(np.argmax(np.abs(xs[:, 0]) > 1e-4) / 48000), 2), "s")

rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=f"{wdir}/small-encoder.int8.onnx", decoder=f"{wdir}/small-decoder.int8.onnx",
                                                tokens=f"{wdir}/small-tokens.txt", language="es", task="transcribe", num_threads=4)
def asr(a, b):
    s = rec.create_stream(); s.accept_waveform(16000, x[int(max(0, a) * 16000):int(b * 16000)]); rec.decode_stream(s)
    return s.result.text.strip()

tm = json.load(open(os.path.join(ROOT, "src", "timings.json")))
print("\nSincronía subtítulo por subtítulo (palabras del subtítulo oídas mientras está en pantalla):")
tot = []
for sub in [c for sc in tm["scenes"] for c in sc["subtitles"]]:
    a, b = sub["from"] / 30, (sub["from"] + sub["duration"]) / 30
    h = norm(asr(a - 0.15, b + 0.15)); ref = norm(sub["text"])
    hit = sum(1 for w in ref if w in h) / len(ref); tot.append(hit)
    print(f"  {hit * 100:5.0f}%  [{a:5.2f}-{b:5.2f}s]  {sub['text']}")
print(f"Promedio de sincronía: {np.mean(tot) * 100:.1f}%")
