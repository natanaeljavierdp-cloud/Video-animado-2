# Convierte Natural Earth GeoJSON a un geo.js compacto (lon/lat simplificados)
import json, math, sys
def simp(ring, tol):
    out=[ring[0]]
    for p in ring[1:]:
        q=out[-1]
        if abs(p[0]-q[0])+abs(p[1]-q[1])>=tol: out.append(p)
    return [[round(x,3),round(y,3)] for x,y in out]
def polys(g):
    if g['type']=='Polygon': return [g['coordinates']]
    return g['coordinates']
def conv(path, tol, filt=None, minpts=4):
    d=json.load(open(path))
    res={}
    for f in d['features']:
        p=f['properties']; code=p.get('ADM0_A3') or p.get('ISO_A3')
        if filt and code not in filt: continue
        rings=[]
        for poly in polys(f['geometry']):
            r=simp(poly[0],tol)
            if len(r)>=minpts: rings.append(r)
        if rings: res[code]=rings
    return res
world=conv('geo/countries50.geojson',0.25)
world.pop('ATA',None)
hisp=conv('geo/countries10.geojson',0.004,{'DOM','HTI'})
mmr=conv('geo/countries10.geojson',0.03,{'MMR','THA','LAO','CHN','IND','BGD','VNM','KHM'})
open('build/geo.js','w').write('window.GEO='+json.dumps({'world':world,'hisp':hisp,'sea':mmr},separators=(',',':'))+';')
print(len(open('build/geo.js').read())//1024,'KB', len(world))
