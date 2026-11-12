import json,sys
from faster_whisper import WhisperModel
m=WhisperModel("medium",device="cpu",compute_type="int8")
segs,info=m.transcribe(__import__("numpy").fromfile(sys.argv[1],dtype="float32"),language="es",word_timestamps=True,beam_size=5,initial_prompt="Maricarmen Abascal. Capital Curioso. Pepe Álvarez, UGT, CEOE.")
out=[]
for s in segs:
    for w in s.words: out.append({"w":w.word.strip(),"s":round(w.start,3),"e":round(w.end,3)})
    print(f"{s.start:.2f}-{s.end:.2f} {s.text}",flush=True)
json.dump(out,open(sys.argv[2],"w"),ensure_ascii=False,indent=0)
