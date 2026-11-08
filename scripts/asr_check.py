#!/usr/bin/env python3
"""Transcribe WAVs con Whisper (sherpa-onnx) y calcula el error por palabra (WER)
contra el texto esperado. Uso: asr_check.py MODEL_DIR "texto esperado" a.wav [b.wav ...]"""
import re, sys, unicodedata
import numpy as np, soundfile as sf, sherpa_onnx
from scipy import signal

def norm(t):
    t = unicodedata.normalize('NFD', t.lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return re.sub(r"[^a-z0-9ñ ]", " ", t).split()

def wer(ref, hyp):
    d = np.arange(len(hyp) + 1)
    for i, r in enumerate(ref, 1):
        prev, d[0] = d.copy(), i
        for j, h in enumerate(hyp, 1):
            d[j] = min(prev[j] + 1, d[j - 1] + 1, prev[j - 1] + (r != h))
    return d[-1] / len(ref)

m = sys.argv[1]
rec = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=f"{m}/small-encoder.int8.onnx", decoder=f"{m}/small-decoder.int8.onnx",
    tokens=f"{m}/small-tokens.txt", language="es", task="transcribe", num_threads=4)
ref = norm(sys.argv[2])
for f in sys.argv[3:]:
    x, sr = sf.read(f, dtype='float32')
    if x.ndim > 1: x = x.mean(1)
    if sr != 16000: x = signal.resample_poly(x, 16000, sr).astype('float32')
    s = rec.create_stream(); s.accept_waveform(16000, x); rec.decode_stream(s)
    hyp = s.result.text.strip()
    print(f"{f.split('/')[-1]:26s} WER {wer(ref, norm(hyp))*100:5.1f}%  | {hyp}")
