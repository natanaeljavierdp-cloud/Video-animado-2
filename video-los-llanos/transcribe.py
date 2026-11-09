import json, sys
from faster_whisper import WhisperModel
m = WhisperModel(sys.argv[2] if len(sys.argv)>2 else "small", device="cpu", compute_type="int8")
import numpy as np
audio = np.fromfile("build/narr16k.f32", dtype=np.float32)
segs, info = m.transcribe(audio, language="es", word_timestamps=True, beam_size=5,
    initial_prompt="San José de los Llanos, SISMAP Municipal, San José de las Matas, llaneros, guagua.")
words=[]
for s in segs:
    for w in s.words:
        words.append({"w": w.word.strip(), "s": round(w.start,3), "e": round(w.end,3)})
json.dump(words, open("build/words.json","w"), ensure_ascii=False, indent=0)
print(" ".join(f"{x['w']}[{x['s']:.1f}]" for x in words))
