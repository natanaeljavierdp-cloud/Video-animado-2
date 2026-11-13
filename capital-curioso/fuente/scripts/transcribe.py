import json, sys
from faster_whisper import WhisperModel
m = WhisperModel("medium", device="cpu", compute_type="int8")
import numpy as np
audio=np.fromfile("voice16.raw",dtype=np.float32)
segs, info = m.transcribe(audio, language="es", word_timestamps=True, beam_size=5)
out=[]
for s in segs:
    for w in s.words:
        out.append({"w":w.word.strip(),"s":round(w.start,3),"e":round(w.end,3)})
    print(f"[{s.start:.2f}-{s.end:.2f}] {s.text}", flush=True)
json.dump(out, open("words.json","w"), ensure_ascii=False, indent=0)
