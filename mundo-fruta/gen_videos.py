"""Anima cada imagen aprobada con Veo 3.1 Lite (imagen = primer cuadro), 8 s, 9:16, con audio.
Uso: python3 gen_videos.py [numeros de escena...]"""
import base64, json, os, sys, time, urllib.request

from escenas import ESCENAS, NEGATIVO_VIDEO

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO = os.environ.get("MODELO_VIDEO", "veo-3.1-lite-generate-preview")
RES = os.environ.get("RESOLUCION", "1080p")
BASE = "https://generativelanguage.googleapis.com/v1beta"
KEY = os.environ.get("GEMINI_API_KEY", "proxy")
H = {"Content-Type": "application/json", "x-goog-api-key": KEY}

COMUN = ("3D animated feature film style, dark secret room, warm golden hanging lamp, soft smoke, chiaroscuro, "
         "film grain. One single continuous shot, no cuts. All dialogue in Latin American Spanish, no English. "
         "No text or subtitles on screen. Keep the characters exactly as in the first frame. ")


def pedir(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=H)
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def lanzar(esc):
    img = os.path.join(AQUI, "imagenes", f"escena_{esc['n']}.png")
    with open(img, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    body = {"instances": [{"prompt": COMUN + esc["video"],
                           "image": {"bytesBase64Encoded": data, "mimeType": "image/png"}}],
            "parameters": {"aspectRatio": "9:16", "durationSeconds": 8, "resolution": RES,
                           "negativePrompt": NEGATIVO_VIDEO}}
    op = pedir(f"{BASE}/models/{MODELO}:predictLongRunning", body)
    print("lanzada escena", esc["n"], op.get("name"))
    return op["name"]


def esperar(n, name):
    while True:
        op = pedir(f"{BASE}/{name}")
        if op.get("done"):
            break
        time.sleep(15)
    if "error" in op:
        print("ERROR escena", n, op["error"]); return
    resp = op["response"]
    vids = (resp.get("generateVideoResponse", {}).get("generatedSamples")
            or resp.get("generatedVideos") or [])
    if not vids:
        print("SIN VIDEO escena", n, json.dumps(resp)[:800]); return
    uri = vids[0]["video"]["uri"]
    out = os.path.join(AQUI, "videos", f"escena_{n}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    req = urllib.request.Request(uri, headers={"x-goog-api-key": KEY})
    with urllib.request.urlopen(req, timeout=300) as r, open(out, "wb") as f:
        f.write(r.read())
    print("OK", out)


if __name__ == "__main__":
    nums = {int(x) for x in sys.argv[1:]} or {e["n"] for e in ESCENAS}
    ops = []
    for e in ESCENAS:
        if e["n"] in nums:
            try:
                ops.append((e["n"], lanzar(e)))
            except urllib.error.HTTPError as err:
                print("ERROR escena", e["n"], err.code, err.read().decode()[:800])
    for n, name in ops:
        esperar(n, name)
