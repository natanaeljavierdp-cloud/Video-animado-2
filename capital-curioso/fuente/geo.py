import json,sys
G=sys.argv[1]; OUT=sys.argv[2]
def decode(topo):
    tr=topo.get('transform'); arcs=[]
    for a in topo['arcs']:
        x=y=0; pts=[]
        for p in a:
            if tr:
                x+=p[0]; y+=p[1]
                pts.append((x*tr['scale'][0]+tr['translate'][0], y*tr['scale'][1]+tr['translate'][1]))
            else: pts.append(tuple(p))
        arcs.append(pts)
    def ring(idx):
        r=[]
        for i in idx:
            a=arcs[i] if i>=0 else arcs[~i][::-1]
            r.extend(a if not r else a[1:])
        return r
    def geom(g):
        if g['type']=='Polygon': return [[ring(r) for r in g['arcs']]]
        if g['type']=='MultiPolygon': return [[ring(r) for r in p] for p in g['arcs']]
        return []
    return geom
def simp(r,step):
    return r[::step] if len(r)>step*6 else r
# world
t=json.load(open(G+'/world-atlas-2.0.2/package/countries-110m.json'))
geom=decode(t); world=[]
for g in t['objects']['countries']['geometries']:
    polys=[]
    for p in geom(g):
        for r in p[:1]:
            pts=[((lon+180)/360, (83-lat)/(83+58)) for lon,lat in r if lat>-58]
            if len(pts)>2: polys.append([[round(a,4),round(b,4)] for a,b in pts])
    world.append({'id':g.get('id'),'name':g['properties'].get('name'),'p':polys})
# US
t=json.load(open(G+'/us-atlas-3.0.1/package/states-albers-10m.json'))
geom=decode(t); us=[]
for g in t['objects']['states']['geometries']:
    polys=[]; cx=cy=n=0
    for p in geom(g):
        r=simp(p[0],3)
        polys.append([[round(x/975,4),round(y/610,4)] for x,y in r])
        for x,y in p[0]: cx+=x;cy+=y;n+=1
    us.append({'id':g['id'],'name':g['properties']['name'],'p':polys,'c':[cx/n/975,cy/n/610]})
open(OUT,'w').write('window.GEO='+json.dumps({'world':world,'us':us})+';')
print(len(world),len(us), [ (u['id'],u['name']) for u in us if u['id'] in ('11','36','06','17','48','13','53','12','08','25','04')])
