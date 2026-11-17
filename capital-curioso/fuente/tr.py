import json,sys
from faster_whisper import WhisperModel
m=WhisperModel("small",device="cpu",compute_type="int8")
import numpy as np
a=np.fromfile(sys.argv[1],dtype=np.int16).astype(np.float32)/32768
segs,_=m.transcribe(a,language="es",word_timestamps=True,beam_size=5)
W=[]
for s in segs:
    print(f"[{s.start:.2f}-{s.end:.2f}] {s.text}")
    for w in s.words: W.append([w.word.strip(),round(w.start,3),round(w.end,3)])
json.dump(W,open("words.json","w"),ensure_ascii=False)
