import json,sys
from faster_whisper import WhisperModel
m=WhisperModel("medium",device="cpu",compute_type="int8")
import numpy as np; a=np.fromfile(sys.argv[1],dtype=np.float32)
segs,_=m.transcribe(a,language="es",word_timestamps=True,beam_size=5)
out=[]
for s in segs:
    print(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text}")
    for w in s.words: out.append({"w":w.word.strip(),"s":round(w.start,3),"e":round(w.end,3)})
json.dump(out,open(sys.argv[2],"w"),ensure_ascii=False,indent=0)
