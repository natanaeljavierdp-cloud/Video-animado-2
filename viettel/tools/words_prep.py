# Limpia la transcripción palabra-por-palabra y genera build/words.js
import json
w=json.load(open('tools/words_raw.json'))
out=[]
i=0
while i<len(w):
    x=dict(w[i])
    if x['w']=='972' and w[i+1]['w']=='.5':
        x['w']='972.5'; x['e']=w[i+1]['e']; i+=1
    if x['w']=='MHz': x['w']='megahercios'
    if x['w'].startswith('Altis'): x['w']='Altice,'
    out.append(x)
    if x['w']=='investigar':
        x['e']=55.7
        out.append({'w':'el','s':55.7,'e':55.84}); out.append({'w':'dinero.','s':55.84,'e':56.18})
    i+=1
# cortar en frases
chunks=[];cur=[]
for k,x in enumerate(out):
    if cur and (x['s']-cur[-1]['e']>0.45 or len(cur)>=4 or len(' '.join(c['w'] for c in cur+[x]))>24):
        chunks.append(cur);cur=[]
    cur.append(x)
    if x['w'][-1] in '.,?:': chunks.append(cur);cur=[]
if cur: chunks.append(cur)
open('build/words.js','w').write('window.CHUNKS='+json.dumps([[{'w':c['w'].upper(),'s':c['s'],'e':c['e']} for c in ch] for ch in chunks],ensure_ascii=False)+';')
for ch in chunks: print(ch[0]['s'], ' '.join(c['w'] for c in ch))
