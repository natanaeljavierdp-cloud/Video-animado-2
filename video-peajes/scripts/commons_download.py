# Descarga imágenes de Wikimedia Commons (licencias libres) y guarda créditos.
import json, sys, time, urllib.request, urllib.parse, urllib.error, re, os
UA = "CapitalCuriosoVideoBot/1.0 (educational video)"
FILES = {
 "peaje-las-americas.jpg": "File:Las Américas toll plaza at kilometer 22 of the Autopista Las Américas.jpg",
 "congreso-nacional.jpg": "File:Palacio del Congreso Nacional Santo Domingo.jpg",
 "las-americas-km12.jpg": "File:Autopista Las Américas at kilometer 12, near Avenida Hipódromo.jpg",
 "tarifas-las-americas.jpg": "File:Lista de tarifas del peaje Las Américas en la Autopista Las Américas.jpg",
 "peaje-6-noviembre.jpg": "File:Peaje de la Autopista 6 de Noviembre.jpg",
 "av-27-febrero.jpg": "File:27 de febrero, RD.jpg",
 "autopista-duarte.jpg": "File:Before the Monumental Avenue in the Autopista Duarte (DR-1) in Santo Domingo.jpg",
 "las-americas-la-caleta.jpg": "File:Autopista Las Américas en La Caleta.jpg",
 "santo-domingo-skyline.jpg": "File:View of Santo Domingo Skyline.jpg",
 "portico-peaje.jpg": "File:Toll gantry at I-88 WB exit to Eola Rd - Aurora, IL - May 2024.jpg",
}
def get(url):
    for i in range(8):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":UA}), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code!=429: raise
            time.sleep(int(e.headers.get("Retry-After") or 5*(i+1)))
out = sys.argv[1]; credits=[]
for name, title in FILES.items():
    p={"action":"query","titles":title,"prop":"imageinfo","iiprop":"url|size|extmetadata","iiurlwidth":2200,"format":"json"}
    d=json.loads(get("https://commons.wikimedia.org/w/api.php?"+urllib.parse.urlencode(p)))
    ii=list(d["query"]["pages"].values())[0]["imageinfo"][0]; em=ii["extmetadata"]
    import subprocess
    dest=os.path.join(out,name)
    if os.path.exists(dest) and os.path.getsize(dest)>50000:
        credits.append(dict(file=name,title=title,page=ii["descriptionurl"],author=re.sub("<[^>]+>","",em.get("Artist",{}).get("value","")).strip(),license=em.get("LicenseShortName",{}).get("value"))); continue
    u=ii["url"].split("?")[0]; parts=u.split("/commons/",1)
    fn=u.rsplit("/",1)[1]
    thumb = u if ii.get("width",0)<=1920 else parts[0]+"/commons/thumb/"+parts[1]+"/1920px-"+fn
    for i in range(6):
        code=subprocess.run(["curl","-sS","-m","120","-A",UA,"-o",dest,"-w","%{http_code}",thumb],capture_output=True,text=True).stdout
        print(" ",name,code,flush=True)
        if code=="200": break
        time.sleep(15*(i+1))
    artist=re.sub("<[^>]+>","",em.get("Artist",{}).get("value","")).strip()
    credits.append(dict(file=name,title=title,page=ii["descriptionurl"],author=artist,license=em.get("LicenseShortName",{}).get("value")))
    print(name, credits[-1]["license"], artist); time.sleep(6)
json.dump(credits, open(os.path.join(out,"credits.json"),"w"), ensure_ascii=False, indent=1)
