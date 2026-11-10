import json, sys, urllib.request, urllib.parse, urllib.error
UA = "CapitalCuriosoVideoBot/1.0 (educational video)"
def search(q, n=12):
    p = {"action":"query","generator":"search","gsrsearch":q,"gsrnamespace":6,"gsrlimit":n,"prop":"imageinfo",
         "iiprop":"url|size|mime|extmetadata","iiurlwidth":1600,"format":"json"}
    r = urllib.request.Request("https://commons.wikimedia.org/w/api.php?"+urllib.parse.urlencode(p), headers={"User-Agent":UA})
    import time
    for i in range(6):
        try:
            d = json.load(urllib.request.urlopen(r, timeout=30)); break
        except urllib.error.HTTPError as e:
            if e.code!=429: raise
            time.sleep(int(e.headers.get("Retry-After") or 5*(i+1)))
    time.sleep(1.5)
    out=[]
    for pg in d.get("query",{}).get("pages",{}).values():
        ii = pg["imageinfo"][0]; em = ii.get("extmetadata",{})
        out.append(dict(title=pg["title"], w=ii["width"], h=ii["height"], mime=ii["mime"], url=ii["url"], thumb=ii.get("thumburl"),
            page=ii["descriptionurl"], lic=em.get("LicenseShortName",{}).get("value"), artist=em.get("Artist",{}).get("value","")[:80]))
    return out
for q in sys.argv[1:]:
    print("=== ", q)
    for o in search(q): print(f"{o['mime']:12} {o['w']}x{o['h']} {o['lic']} | {o['title']}")
