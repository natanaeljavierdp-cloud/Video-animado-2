"""Extrae la silueta de República Dominicana (ISO 214) desde world-atlas 2.0.2 (Natural Earth 1:10m,
dominio público; paquete ISC) y la guarda como lista de anillos lon/lat en assets/rd_silueta.json"""
import json, sys
topo=json.load(open(sys.argv[1])); out=sys.argv[2]
sx,sy=topo["transform"]["scale"]; tx,ty=topo["transform"]["translate"]
arcs=[]
for a in topo["arcs"]:
    x=y=0; pts=[]
    for dx,dy in a: x+=dx; y+=dy; pts.append((x*sx+tx, y*sy+ty))
    arcs.append(pts)
def arc(i): return arcs[i] if i>=0 else arcs[~i][::-1]
geom=[g for g in topo["objects"]["countries"]["geometries"] if g.get("id")=="214"][0]
print(geom["properties"], geom["type"])
polys=geom["arcs"] if geom["type"]=="MultiPolygon" else [geom["arcs"]]
rings=[]
for poly in polys:
    for ring in poly:
        pts=[]
        for i in ring: pts+= arc(i)[1:] if pts else arc(i)
        rings.append(pts)
rings.sort(key=len, reverse=True)
print([len(r) for r in rings])
json.dump({"fuente":"Natural Earth 1:10m via world-atlas@2.0.2","rings":rings},open(out,"w"))
