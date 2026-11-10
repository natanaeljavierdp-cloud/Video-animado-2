import json, sys
from faster_whisper import WhisperModel
m = WhisperModel("medium", device="cpu", compute_type="int8")
import numpy as np, soundfile as sf; a,_=sf.read(sys.argv[1], dtype="float32"); segs, info = m.transcribe(a, language="es", word_timestamps=True, beam_size=5,
  initial_prompt="Peajes, marbete, Senado, telepeaje, pórtico, Las Américas, Impuestos Internos, Free Flow.")
words=[]
for s in segs:
    print(f"[{s.start:.2f}-{s.end:.2f}] {s.text}")
    for w in s.words: words.append({"word":w.word.strip(),"start":round(w.start,3),"end":round(w.end,3)})
json.dump(words, open(sys.argv[2],"w"), ensure_ascii=False, indent=1)
