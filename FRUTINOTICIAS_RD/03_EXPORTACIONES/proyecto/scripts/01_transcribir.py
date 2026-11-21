"""Transcribe los 8 clips originales con faster-whisper (timestamps por palabra)."""
import json, sys, glob, os, subprocess
import numpy as np
from faster_whisper import WhisperModel
SRC = sys.argv[1]; OUT = sys.argv[2]
model = WhisperModel(sys.argv[3] if len(sys.argv) > 3 else "large-v3", device="cpu", compute_type="int8")
res = {}
for f in sorted(glob.glob(os.path.join(SRC, "*.mp4"))):
    pcm = subprocess.run(["ffmpeg","-v","error","-i",f,"-ac","1","-ar","16000","-f","s16le","-"],capture_output=True,check=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32)/32768.0
    segs, info = model.transcribe(audio, language="es", word_timestamps=True, beam_size=5, vad_filter=False)
    words = []; text = []
    for s in segs:
        text.append(s.text.strip())
        for w in s.words: words.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)})
    res[os.path.basename(f)] = {"text": " ".join(text), "words": words}
    print(os.path.basename(f), "|", " ".join(text), flush=True)
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
