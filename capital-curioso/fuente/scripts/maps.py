# Build SVG path strings for map views (equirectangular w/ cos(lat0) scaling)
import json, math
d=json.load(open("dl/countries.geojson"))
def view(lon0,lon1,lat0,lat1,W,H,hi,minarea=0):
    latc=(lat0+lat1)/2; k=math.cos(math.radians(latc))
    sx=W/((lon1-lon0)*k); sy=H/(lat1-lat0); s=min(sx,sy)
    ox=(W-(lon1-lon0)*k*s)/2; oy=(H-(lat1-lat0)*s)/2
    P=lambda lo,la:((lo-lon0)*k*s+ox,(lat1-la)*s+oy)
    out=[]
    for f in d["features"]:
        iso=f["properties"]["ISO_A3"]; g=f["geometry"]
        polys=g["coordinates"] if g["type"]=="MultiPolygon" else [g["coordinates"]]
        parts=[]
        for poly in polys:
            for ring in poly:
                if not any(lon0-15<lo<lon1+15 and lat0-15<la<lat1+15 for lo,la in ring): continue
                pts=[P(lo,la) for lo,la in ring]
                parts.append("M"+"L".join(f"{x:.1f},{y:.1f}" for x,y in pts)+"Z")
        if parts: out.append({"iso":iso,"name":f["properties"]["NAME"],"d":"".join(parts),"hi":iso in hi})
    return {"W":W,"H":H,"paths":out,"proj":[lon0,lon1,lat0,lat1,k,s,ox,oy]}
def pt(v,lo,la):
    lon0,lon1,lat0,lat1,k,s,ox,oy=v["proj"]; return [(lo-lon0)*k*s+ox,(lat1-la)*s+oy]
me=view(30,66,8,40,1000,900,["QAT"])
me["qat"]=pt(me,51.2,25.3)
world=view(-95,70,-8,52,1000,600,["DOM","QAT"])
world["sdq"]=pt(world,-69.9,18.48); world["doh"]=pt(world,51.53,25.29)
isl=view(-74.8,-68.0,17.3,20.2,1000,520,["DOM"])
isl["sdq"]=pt(isl,-69.93,18.48)
json.dump({"me":me,"world":world,"isl":isl},open("build/maps.json","w"))
print(me["qat"],world["sdq"],world["doh"],isl["sdq"])
