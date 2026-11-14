from faster_whisper import WhisperModel
import json,sys
m=WhisperModel("medium",device="cpu",compute_type="int8")
prompt="¿Por qué los hombres más poderosos de Estados Unidos ya no duermen en sus casas? Scott Bessent, Marco Rubio, Pete Hegseth, Fort McNair, Kristi Noem, Anacostia-Bolling, Dan Driscoll, Myer-Henderson Hall, Stephen Miller, Pam Bondi, Todd Blanche."
import subprocess,numpy as np
aud=np.frombuffer(subprocess.run(["ffmpeg","-v","error","-i",sys.argv[1],"-ac","1","-ar","16000","-f","f32le","-"],capture_output=True).stdout,dtype=np.float32)
segs,info=m.transcribe(aud,language="es",word_timestamps=True,initial_prompt=prompt,vad_filter=False)
out=[]
for s in segs:
  for w in s.words: out.append([w.word.strip(),round(w.start,3),round(w.end,3)])
json.dump(out,open(sys.argv[2],"w"),ensure_ascii=False)
print(len(out)); print(" ".join(w[0] for w in out))
