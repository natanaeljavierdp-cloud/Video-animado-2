import json, sys
from faster_whisper import WhisperModel
m = WhisperModel("medium", device="cpu", compute_type="int8")
import numpy as np
audio=np.fromfile(sys.argv[1],dtype=np.int16).astype(np.float32)/32768
segs, info = m.transcribe(audio, language="es", word_timestamps=True, beam_size=5,
  initial_prompt="Sandoval Legal. Código Penal, Ley 74-25, artículo 276, artículo 275. causa probable.")
out=[]
for s in segs:
    for w in s.words:
        out.append({"w":w.word.strip(),"s":round(w.start,3),"e":round(w.end,3)})
    print(round(s.start,2), round(s.end,2), s.text, flush=True)
json.dump(out, open(sys.argv[2],"w"), ensure_ascii=False, indent=0)
