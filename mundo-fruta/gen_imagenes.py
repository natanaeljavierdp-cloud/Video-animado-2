"""Genera la imagen fija 9:16 de cada escena con el modelo de imagen de Gemini.
Uso: python3 gen_imagenes.py [numeros de escena...]   (sin argumentos = las 8)
La clave la inyecta el proxy del entorno (cabecera x-goog-api-key)."""
import base64, json, os, sys, urllib.request

from escenas import ESCENAS, ESTILO, PERS

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO = os.environ.get("MODELO_IMAGEN", "gemini-3-pro-image-preview")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent"
KEY = os.environ.get("GEMINI_API_KEY", "proxy")


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def generar(esc):
    partes = []
    for p in esc["pers"]:
        partes.append({"text": f"Reference image for {PERS[p]}:"})
        partes.append({"inline_data": {"mime_type": "image/png",
                                       "data": b64(os.path.join(AQUI, "personajes", p + ".png"))}})
    lista = "; ".join(PERS[p] for p in esc["pers"])
    partes.append({"text": f"{ESTILO}\nCharacters in this shot: {lista}.\nScene: {esc['imagen']}"})
    body = {"contents": [{"role": "user", "parts": partes}],
            "generationConfig": {"responseModalities": ["IMAGE"],
                                 "imageConfig": {"aspectRatio": "9:16"}}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.load(r)
    for c in res.get("candidates", []):
        for part in c.get("content", {}).get("parts", []):
            d = part.get("inlineData") or part.get("inline_data")
            if d:
                out = os.path.join(AQUI, "imagenes", f"escena_{esc['n']}.png")
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out, "wb") as f:
                    f.write(base64.b64decode(d["data"]))
                print("OK", out)
                return
    print("SIN IMAGEN escena", esc["n"], json.dumps(res)[:800])


if __name__ == "__main__":
    nums = {int(x) for x in sys.argv[1:]} or {e["n"] for e in ESCENAS}
    for e in ESCENAS:
        if e["n"] in nums:
            try:
                generar(e)
            except urllib.error.HTTPError as err:
                print("ERROR escena", e["n"], err.code, err.read().decode()[:800])
