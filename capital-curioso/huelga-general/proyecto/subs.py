import json
w=json.load(open('../words.json'))
m=[]
for x in w:
    if m and (x['w'] in ('%','.000','.000.')):
        m[-1]['w']+=x['w']; m[-1]['e']=x['e']; continue
    m.append(dict(x))
fix={'gobierno':'Gobierno'}
for x in m: x['w']=fix.get(x['w'],x['w'])
chunks=[];cur=[]
for i,x in enumerate(m):
    cur.append(x)
    nxt=m[i+1] if i+1<len(m) else None
    brk = x['w'][-1] in '.,?!' or len(cur)>=4 or (nxt and nxt['s']-x['e']>0.3) or not nxt
    if x['w'].lower() in ('se','de','la','en','los','a','el','que','un','una','y','del','las') and len(cur)<5 and nxt and nxt['s']-x['e']<0.3: brk=False
    if len(cur)<=2 and x['w'][-1]==',' and nxt and len(''.join(c['w'] for c in cur))<9: brk=False
    if brk: chunks.append(cur);cur=[]
out=[]
for i,c in enumerate(chunks):
    end = min(chunks[i+1][0]['s'], c[-1]['e']+0.6) if i+1<len(chunks) else c[-1]['e']+0.4
    out.append({'s':c[0]['s'],'e':end,'w':[[x['w'],x['s'],x['e']] for x in c]})
json.dump(out,open('subs.json','w'),ensure_ascii=False)
for c in out: print(f"{c['s']:.2f}-{c['e']:.2f}", ' '.join(x[0] for x in c['w']))
