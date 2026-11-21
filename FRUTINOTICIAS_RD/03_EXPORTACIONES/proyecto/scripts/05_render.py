"""Render final de FRUTINOTICIASRD_LANZAMIENTO_CINEMATOGRAFICO.mp4
Base: clips originales recortados según edl.json, escalados 720x1280 -> 1080x1920 (lanczos, sin deformar).
Encima: paquete gráfico (graficos.py) + subtítulos quemados + transiciones.
Protección: cada elemento decorativo comprueba la caja de la cabeza de Dania (build/zonas_cabeza.json)
fotograma a fotograma y se desvanece si la invadiría. Se registra un informe QA en build/qa_overlay.json.
Uso: python3 05_render.py [--preview SEG_INI SEG_FIN] [--frames f1,f2,...]
"""
import subprocess, json, math, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
from comun import cargar_edl, tl, transcripcion, BUILD, ASSETS, PROY
import graficos as G
from graficos import (font, ease_out, ease_in, ease_io, clamp, ventana, con_alpha, recorte_h, destello,
                      glow, chip, placa_3d, texto_3d, wordmark, gradiente_v, gradiente_h, MapaRD,
                      AZUL_E, AZUL_C, AZUL_O, AZUL_M, ROJO, ROJO_C, BLANCO, PLATA, RD_AZUL, RD_ROJO)

edl = cargar_edl(); FPS = edl["fps"]; W, H = 1080, 1920
GR = edl["graficos"]
NF = edl["frames_total"]
SALIDA_DIR = os.path.dirname(PROY)
SALIDA = os.path.join(SALIDA_DIR, "FRUTINOTICIASRD_LANZAMIENTO_CINEMATOGRAFICO.mp4")

# ------------------------------------------------------------------ zonas protegidas (cabeza)
zon = json.load(open(os.path.join(BUILD, "zonas_cabeza.json")))
cabeza = [None] * NF
for c in edl["clips"]:
    bx = zon[c["archivo"]]
    # rellenar huecos con el vecino válido
    last = None; filled = []
    for b in bx:
        last = b if b else last; filled.append(last)
    nxt = None
    for i in range(len(filled) - 1, -1, -1):
        nxt = filled[i] if filled[i] else nxt; filled[i] = filled[i] or nxt
    arr = np.array(filled, float)
    # rechazo de detecciones atípicas (saltos bruscos) con mediana móvil de 9 fotogramas
    med = np.array([np.median(arr[max(0, i - 4):i + 5], 0) for i in range(len(arr))])
    z = c.get("zoom_recorte", 1.0)
    cw, ch = 720 / z, 1280 / z; cx0 = (720 - cw) / 2
    for k in range(c["frames"]):
        x0, y0, x1, y1 = med[c["in"] + k]
        sx, sy = W / cw, H / ch
        m = 26
        cabeza[c["t0_frame"] + k] = (int((x0 - cx0) * sx) - m, int(y0 * sy) - m, int((x1 - cx0) * sx) + m, int(y1 * sy) + m)


def interseca(b, box):
    if b is None or box is None: return 0.0
    ix = max(0, min(b[2], box[2]) - max(b[0], box[0])); iy = max(0, min(b[3], box[3]) - max(b[1], box[1]))
    return ix * iy / max(1, (box[2] - box[0]) * (box[3] - box[1]))


class Lienzo:
    """Capa de gráficos de un fotograma con protección automática de la cabeza."""
    def __init__(self, fi):
        self.im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); self.fi = fi
        self.box = cabeza[fi] if fi < len(cabeza) else None
        self.conflictos = []

    def poner(self, spr, x, y, alpha=1.0, nombre="", proteger=True):
        if spr is None or alpha <= 0.001: return
        x, y = int(round(x)), int(round(y))
        if proteger and self.box:
            # caja opaca real del sprite
            bb = spr.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
            if bb:
                ov = interseca(self.box, (x + bb[0], y + bb[1], x + bb[2], y + bb[3]))
                if ov > 0:
                    alpha *= clamp(1 - ov * 8)
                    self.conflictos.append((nombre, round(ov, 3)))
        spr = con_alpha(spr, alpha)
        if spr is not None: self.im.alpha_composite(spr, (x, y)) if x >= 0 and y >= 0 else self._pegar_neg(spr, x, y)

    def _pegar_neg(self, spr, x, y):
        w, h = spr.size
        cx, cy = max(0, -x), max(0, -y)
        if cx >= w or cy >= h: return
        self.im.alpha_composite(spr.crop((cx, cy, w, h)), (max(0, x), max(0, y)))


# ------------------------------------------------------------------ subtítulos
def parse_marcas(linea):
    segs = []; i = 0; cur = ""; modo = None
    for ch in linea:
        if ch in "*{}":
            if cur: segs.append((cur, modo)); cur = ""
            modo = (None if modo == "rojo" else "rojo") if ch == "*" else ("azul" if ch == "{" else None)
        else: cur += ch
    if cur: segs.append((cur, modo))
    return segs

F_SUB = font("InterDisplay-ExtraBold", 58)
def sprite_sub(texto):
    lineas = texto.split("\n")
    lh = 72; ims = []
    for ln in lineas:
        segs = parse_marcas(ln)
        ancho = sum(F_SUB.getlength(s) for s, _ in segs)
        im = Image.new("RGBA", (int(ancho) + 40, lh + 24), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        x = 20
        for s, m in segs:
            col = {None: (255, 255, 255), "rojo": (255, 62, 72), "azul": (92, 196, 255)}[m]
            d.text((x, 10), s, font=F_SUB, fill=col + (255,), stroke_width=6, stroke_fill=(6, 14, 34, 255))
            x += F_SUB.getlength(s)
        ims.append(im)
    w = max(i.size[0] for i in ims); h = lh * len(ims) + 26
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for k, i in enumerate(ims): out.alpha_composite(i, ((w - i.size[0]) // 2, k * lh))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0)); a = out.getchannel("A").filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * 0.55))
    sh.putalpha(a); fin = Image.new("RGBA", out.size, (0, 0, 0, 0)); fin.alpha_composite(sh, (0, 0))
    fin.alpha_composite(out); return fin

tr = transcripcion()
cues = []
for c in edl["clips"]:
    words = tr[c["archivo"]]["words"]; k = 0; lst = []
    for n, txt in edl["subtitulos"][c["id"]]:
        ws = words[k:k + n]; k += n
        lst.append([ws[0]["s"], ws[-1]["e"], txt])
    assert k == len(words), f"clip {c['id']}: {k} palabras usadas de {len(words)}"
    cin, cout = c["in"] / FPS, c["out"] / FPS
    for i, (s, e, txt) in enumerate(lst):
        s0 = max(cin, s - 0.05)
        e0 = min(cout - 0.02, e + 0.45, lst[i + 1][0] - 0.05 if i + 1 < len(lst) else 99)
        cues.append({"t0": tl(edl, c["id"], s0), "t1": tl(edl, c["id"], e0), "texto": txt, "spr": None})

def srt_time(t):
    ms = int(round(t * 1000)); return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
with open(os.path.join(SALIDA_DIR, "FRUTINOTICIASRD_LANZAMIENTO_CINEMATOGRAFICO.srt"), "w", encoding="utf-8") as f:
    for i, q in enumerate(cues, 1):
        limpio = re.sub(r"[*{}]", "", q["texto"])
        f.write(f"{i}\n{srt_time(q['t0'])} --> {srt_time(q['t1'])}\n{limpio}\n\n")

SUB_CY = 1248
def dibujar_subs(L, t):
    for q in cues:
        if q["t0"] <= t <= q["t1"]:
            if q["spr"] is None: q["spr"] = sprite_sub(q["texto"])
            pin, pout = ventana(t, q["t0"], q["t1"], 0.12, 0.10)
            a = min(ease_out(pin), pout); dy = (1 - ease_out(pin)) * 14
            s = q["spr"]; L.poner(s, (W - s.size[0]) / 2, SUB_CY - s.size[1] / 2 + dy, a, "subtitulo")

# ------------------------------------------------------------------ mapa (panel superior izquierdo)
MP_X, MP_Y, MP_W, MP_H = 36, 118, 404, 232
mapa_pq = MapaRD(os.path.join(ASSETS, "rd_silueta.json"), MP_W - 24, MP_H - 56, pad=10)
mapa_pq_fill = mapa_pq.relleno()
F_LBL = font("InterDisplay-Bold", 15)

def panel_mapa_base():
    im = Image.new("RGBA", (MP_W, MP_H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, MP_W - 1, MP_H - 1], 8, fill=(4, 16, 44, 175), outline=AZUL_E + (200,), width=2)
    for gx in range(12, MP_W, 28): d.line([(gx, 44), (gx, MP_H - 8)], fill=(80, 150, 255, 26))
    for gy in range(44, MP_H, 28): d.line([(8, gy), (MP_W - 8, gy)], fill=(80, 150, 255, 26))
    # esquinas de enfoque
    for (x, y, sx, sy) in ((4, 4, 1, 1), (MP_W - 5, 4, -1, 1), (4, MP_H - 5, 1, -1), (MP_W - 5, MP_H - 5, -1, -1)):
        d.line([(x, y), (x + 18 * sx, y)], fill=BLANCO + (230,), width=3); d.line([(x, y), (x, y + 18 * sy)], fill=BLANCO + (230,), width=3)
    # franja con los colores de la bandera
    for i, col in enumerate((RD_AZUL, BLANCO, RD_ROJO)):
        d.rectangle([16 + i * 22, 16, 16 + i * 22 + 18, 22], fill=col + (255,))
    d.text((90, 10), "REPÚBLICA DOMINICANA", font=font("InterDisplay-ExtraBold", 19), fill=BLANCO + (255,))
    d.line([(16, 36), (MP_W - 16, 36)], fill=ROJO + (220,), width=2)
    return im
PANEL_MAPA = panel_mapa_base()

ETIQ = {"Santo Domingo": (8, 6, "l"), "Santiago": (-10, 2, "r"), "Puerto Plata": (10, -18, "l"), "Punta Cana": (-10, -22, "r")}

def dibujar_ciudades(d, mapa, nombres, t_rel, t_base, ox, oy, f_lbl, escala=1.0, lineas=False):
    for i, n in enumerate(nombres):
        ti = t_rel - (t_base + 0.22 * i)
        if ti < 0: continue
        x, y = mapa.ciudades[n]; x += ox; y += oy
        a = ease_out(ti / 0.25)
        for k in range(2):  # anillos de pulso
            ph = ((ti * 0.9 + k * 0.5) % 1.0)
            r = (4 + 18 * ph) * escala
            d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 70, 80, int(200 * (1 - ph) * a)), width=max(1, int(2 * escala)))
        r = 5 * escala
        d.ellipse([x - r - 2, y - r - 2, x + r + 2, y + r + 2], fill=(255, 255, 255, int(255 * a)))
        d.ellipse([x - r, y - r, x + r, y + r], fill=ROJO + (int(255 * a),))
        dx, dy, al = ETIQ[n]
        lab = n.upper()
        tw = f_lbl.getlength(lab)
        tx = x + dx * escala if al == "l" else x + dx * escala - tw
        d.text((tx, y + dy * escala), lab, font=f_lbl, fill=(255, 255, 255, int(240 * clamp(ti / 0.35))), stroke_width=2, stroke_fill=(4, 14, 40, int(220 * a)))
    if lineas and len(nombres) > 1:
        tl0 = t_rel - (t_base + 0.22 * len(nombres))
        if tl0 > 0:
            sd = mapa.ciudades["Santo Domingo"]
            for j, n in enumerate(nombres):
                if n == "Santo Domingo": continue
                p = clamp((tl0 - 0.15 * j) / 0.5)
                if p <= 0: continue
                cx, cy = mapa.ciudades[n]
                x1 = sd[0] + (cx - sd[0]) * p; y1 = sd[1] + (cy - sd[1]) * p
                d.line([(sd[0] + ox, sd[1] + oy), (x1 + ox, y1 + oy)], fill=AZUL_C + (170,), width=2)
                # pulso viajando por la línea
                q = (tl0 * 0.8 + j * 0.3) % 1.0
                if p >= 1:
                    px, py = sd[0] + (cx - sd[0]) * q + ox, sd[1] + (cy - sd[1]) * q + oy
                    d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(255, 255, 255, 230))

def dibujar_mapa_panel(L, t, ev):
    t0 = tl(edl, ev["clip"], ev["desde"]); t1 = tl(edl, ev["clip"], ev["hasta"])
    if not (t0 <= t <= t1): return
    pin, pout = ventana(t, t0, t1, 0.3, 0.3)
    tr_ = t - t0
    spr = PANEL_MAPA.copy()
    mx, my = 12, 46
    # relleno tras dibujar el contorno
    pf = clamp((tr_ - 1.0) / 0.5)
    if pf > 0: spr.alpha_composite(con_alpha(mapa_pq_fill, pf), (mx, my))
    cont, cabeza_lin = mapa_pq.contorno(clamp((tr_ - 0.15) / 0.95), ancho=2)
    spr.alpha_composite(cont, (mx, my))
    d = ImageDraw.Draw(spr)
    if cabeza_lin:
        hx, hy = cabeza_lin[0] + mx, cabeza_lin[1] + my
        d.ellipse([hx - 5, hy - 5, hx + 5, hy + 5], fill=(255, 255, 255, 255))
    # línea de escaneo
    sxp = mx + ((tr_ * 0.45) % 1.0) * (MP_W - 24)
    d.line([(sxp, my), (sxp, MP_H - 10)], fill=AZUL_C + (90,), width=2)
    dibujar_ciudades(d, mapa_pq, ev["ciudades"], tr_, 1.1, mx, my, F_LBL, lineas=len(ev["ciudades"]) > 2)
    spr = recorte_h(spr, ease_out(pin), "izq")
    L.poner(spr, MP_X, MP_Y, pout, "mapa_superior")

# ------------------------------------------------------------------ intro
WM, WM_PAD = wordmark(84)
CH_ESTRENO = chip("ESTRENO OFICIAL", ROJO, size=26)
CH_SATIRA = chip("SÁTIRA Y HUMOR", (6, 22, 58), PLATA, size=26, borde=PLATA)

def linea_digital(L, y, p, color, desde="izq", grosor=3, largo=1.0, nombre="linea"):
    if p <= 0: return
    w = int(W * largo * ease_out(p))
    if w < 4: return
    im = Image.new("RGBA", (w, 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    g = gradiente_h(w, grosor, color, color, 30, 255) if desde == "izq" else gradiente_h(w, grosor, color, color, 255, 30)
    im.alpha_composite(g, (0, 10 - grosor // 2))
    hx = w - 6 if desde == "izq" else 6
    d.ellipse([hx - 5, 5, hx + 5, 15], fill=(255, 255, 255, 230))
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    x = 0 if desde == "izq" else W - w
    L.poner(im, x, y - 10, 1.0, nombre)

def dibujar_intro(L, t):
    ev = GR["intro"]; t0 = tl(edl, ev["clip"], ev["desde"]); t1 = tl(edl, ev["clip"], ev["hasta"])
    if not (t0 <= t <= t1): return
    out = clamp((t1 - t) / 0.4)
    # líneas digitales rojas y azules que enmarcan la zona inferior
    for y, col, dsd, dl in ((1316, ROJO, "izq", 0.0), (1322, AZUL_E, "der", 0.08), (1508, AZUL_E, "izq", 0.12), (1514, ROJO, "der", 0.2)):
        p = clamp((t - t0 - dl) / 0.55) * out
        linea_digital(L, y, p, col, dsd, nombre="lineas_intro")
    # marca FRUTINOTICIASRD
    p = clamp((t - t0 - 0.3) / 0.5)
    if p > 0:
        s = recorte_h(WM, ease_out(p), "centro")
        s = destello(s, clamp((t - t0 - 0.95) / 0.7)) if s is not None else None
        L.poner(s, (W - WM.size[0]) / 2, 1338 - WM_PAD + (1 - out) * 30, out, "marca_intro")
    # chips
    for k, (c, dl) in enumerate(((CH_ESTRENO, 0.9), (CH_SATIRA, 1.05))):
        p = ease_out(clamp((t - t0 - dl) / 0.3))
        if p > 0:
            tot = CH_ESTRENO.size[0] + 18 + CH_SATIRA.size[0]
            x = (W - tot) / 2 + (0 if k == 0 else CH_ESTRENO.size[0] + 18)
            L.poner(c, x, 1452 + (1 - p) * 18, p * out, "chips_intro")

# ------------------------------------------------------------------ rótulo de la presentadora
def sprite_rotulo(nombre, cargo):
    fn = font("InterDisplay-Black", 64); fc = font("InterDisplay-SemiBold", 28)
    w = int(max(fn.getlength(nombre), fc.getlength(cargo))) + 90; h = 128
    panel = gradiente_h(w, h, (10, 36, 96), (4, 14, 40), 245, 225)
    d = ImageDraw.Draw(panel)
    d.rectangle([0, 0, w, 3], fill=PLATA + (255,)); d.rectangle([0, h - 3, w, h], fill=AZUL_E + (255,))
    refl = gradiente_v(w, h // 2, (255, 255, 255), (255, 255, 255), 30, 0); panel.alpha_composite(refl, (0, 4))
    d.text((34, 12), nombre, font=fn, fill=BLANCO + (255,))
    partes = cargo.split("|")
    x = 36
    d.text((x, 84), partes[0].strip(), font=fc, fill=PLATA + (255,)); x += fc.getlength(partes[0].strip() + " ")
    d.text((x, 82), "|", font=fc, fill=ROJO_C + (255,)); x += fc.getlength("| ")
    d.text((x, 84), partes[1].strip(), font=fc, fill=BLANCO + (255,))
    acento = Image.new("RGBA", (14, h), ROJO + (255,))
    return panel, acento

ROT_P, ROT_A = sprite_rotulo(GR["rotulo_presentadora"]["nombre"], GR["rotulo_presentadora"]["cargo"])
ROT_P_S, ROT_PAD = G.sombra(ROT_P, dy=6, radio=8, alpha=0.6)

def dibujar_rotulo(L, t):
    ev = GR["rotulo_presentadora"]; t0 = tl(edl, ev["clip"], ev["desde"]); t1 = tl(edl, ev["clip"], ev["hasta"])
    if not (t0 <= t <= t1): return
    x, y = 56, 1340
    pa = ease_out((t - t0) / 0.18); out = clamp((t1 - t) / 0.45)
    pw = ease_out((t - t0 - 0.12) / 0.4) * ease_io(out / 1.0 if out < 1 else 1)
    if pw > 0:
        s = recorte_h(ROT_P_S, pw, "izq")
        s = destello(s, clamp((t - t0 - 0.8) / 0.8)) if s is not None else None
        L.poner(s, x + 20 - ROT_PAD, y - ROT_PAD, min(1, out * 1.5), "rotulo")
    if pa > 0:
        a = ROT_A.crop((0, 0, 14, max(1, int(ROT_A.size[1] * pa))))
        L.poner(a, x, y, out, "rotulo_acento")

# ------------------------------------------------------------------ titulares
F_TIT = 60
def sprite_titular(ev):
    txt = texto_3d(ev["texto"], F_TIT, BLANCO, extr=4)
    sub = texto_3d(ev["sub"], 44, ROJO_C, extr=3) if ev.get("sub") else None
    w = max(txt.size[0], sub.size[0] if sub else 0) + 64
    h = 98 + (58 if sub else 0)
    placa = placa_3d(w, h, serio=ev.get("serio", False), oscuro=ev["texto"].startswith("HUMOR"))
    capa_txt = Image.new("RGBA", placa.size, (0, 0, 0, 0))
    capa_txt.alpha_composite(txt, (30, 16))
    if sub: capa_txt.alpha_composite(sub, (32, 16 + txt.size[1] - 6))
    fondo_chip = AZUL_E if ev.get("serio") else ROJO
    ch = chip(ev["chip"], fondo_chip, size=22, padx=12, pady=6)
    return placa, capa_txt, ch

TITS = []
for ev in GR["titulares"]:
    pl, tx, ch = sprite_titular(ev)
    pl_s, pad = G.sombra(pl, dy=8, radio=10, alpha=0.65)
    TITS.append(dict(ev=ev, placa=pl_s, pad=pad, txt=tx, chip=ch, t0=tl(edl, ev["clip"], ev["desde"]), t1=tl(edl, ev["clip"], ev["hasta"])))

def dibujar_titulares(L, t):
    for T in TITS:
        if not (T["t0"] <= t <= T["t1"]): continue
        ev = T["ev"]; tr_ = t - T["t0"]; out = clamp((T["t1"] - t) / 0.35)
        x, y = 56, 1342
        pw = ease_out(tr_ / 0.3)
        placa = recorte_h(T["placa"], pw, "izq")
        if placa is None: continue
        # barrido de luz de entrada y, si procede, sobre la palabra clave
        p_gl = clamp((tr_ - 0.55) / 0.7)
        if ev.get("barrido_en") is not None:
            tb = tl(edl, ev["clip"], ev["barrido_en"])
            if t >= tb: p_gl = clamp((t - tb) / 0.6)
        placa = destello(placa, p_gl, fuerza=0.6)
        sx = (1 - ease_in(1 - out)) if out < 1 else 1
        L.poner(placa, x - T["pad"] + (1 - out) * 40, y - T["pad"], out, "titular")
        # texto con máscara de revelado
        pt = ease_out((tr_ - 0.12) / 0.35)
        txt = recorte_h(T["txt"], pt, "izq")
        a_txt = out
        if ev.get("parpadeo"):
            a0, a1 = [tl(edl, ev["clip"], v) for v in ev["parpadeo"]]
            if a0 <= t <= a1:
                fi = int((t - a0) * FPS)
                a_txt *= [1, 0.15, 1, 1, 0.25, 0.1, 1, 1, 0.4, 1, 1, 1, 0.2, 1, 1, 1, 1, 1, 1, 1][fi % 20]
        L.poner(txt, x + (1 - out) * 40, y, a_txt, "titular_texto")
        pc = ease_out((tr_ - 0.3) / 0.2)
        if pc > 0: L.poner(T["chip"], x + 8, y - 24 + (1 - pc) * 10, pc * out, "titular_chip")

# ------------------------------------------------------------------ batería de paciencia (clip 04)
def dibujar_bateria(L, t):
    ev = GR["bateria_paciencia"]; t0 = tl(edl, "04", ev["desde"]); t1 = tl(edl, "04", ev["hasta"])
    if not (t0 <= t <= t1): return
    d0, d1 = [tl(edl, "04", v) for v in ev["drena"]]
    pin, pout = ventana(t, t0, t1, 0.3, 0.3)
    nivel = 1 - ease_io((t - d0) / (d1 - d0))
    w, h = 560, 104
    im = placa_3d(w, h); d = ImageDraw.Draw(im)
    d.text((28, 28), "PACIENCIA", font=font("InterDisplay-BlackItalic", 44), fill=BLANCO + (255,))
    bx, by, bw, bh = 300, 24, 200, 56
    d.rounded_rectangle([bx, by, bx + bw, by + bh], 8, outline=BLANCO + (255,), width=4)
    d.rectangle([bx + bw + 3, by + 16, bx + bw + 12, by + bh - 16], fill=BLANCO + (255,))
    vacia = nivel <= 0.02
    parp = vacia and int(t * 6) % 2 == 0
    segs = 5
    for i in range(segs):
        if nivel > i / segs + 0.01:
            col = ROJO if nivel < 0.3 else (AZUL_C if nivel < 0.65 else BLANCO)
            sx0 = bx + 9 + i * (bw - 18) / segs
            d.rectangle([sx0 + 2, by + 9, sx0 + (bw - 18) / segs - 3, by + bh - 9], fill=col + (255,))
    if vacia:
        d.rounded_rectangle([bx, by, bx + bw, by + bh], 8, outline=(ROJO if parp else BLANCO) + (255,), width=4)
    s, pad = G.sombra(im, dy=8, radio=10, alpha=0.6)
    s = recorte_h(s, ease_out(pin), "izq")
    L.poner(s, 56 - pad, 1342 - pad, pout, "bateria")

# ------------------------------------------------------------------ carga de promesa (clip 05)
def dibujar_carga(L, t):
    ev = GR["carga_promesa"]; t0 = tl(edl, "05", ev["desde"]); t1 = tl(edl, "05", ev["hasta"])
    if not (t0 <= t <= t1): return
    ta = tl(edl, "05", ev["atasco"])
    pin, pout = ventana(t, t0, t1, 0.3, 0.3)
    w, h = 700, 118
    im = placa_3d(w, h); d = ImageDraw.Draw(im)
    atascado = t >= ta
    etiqueta = "SIGUE CARGANDO..." if atascado else "PROMESA EN PROCESO"
    d.text((84, 14), etiqueta, font=font("InterDisplay-BlackItalic", 40), fill=BLANCO + (255,))
    # spinner
    cx, cy = 44, 40
    for k in range(10):
        ang = 2 * math.pi * k / 10 + t * 5
        a = int(255 * ((k + 1) / 10))
        d.ellipse([cx + 18 * math.cos(ang) - 4, cy + 18 * math.sin(ang) - 4, cx + 18 * math.cos(ang) + 4, cy + 18 * math.sin(ang) + 4], fill=(255, 255, 255, a))
    # barra de progreso que avanza muy poco y se atasca
    prog = 0.12 * ease_out((t - t0) / 2.2)
    bx, by, bw, bh = 30, 78, w - 60, 18
    d.rounded_rectangle([bx, by, bx + bw, by + bh], 9, fill=(255, 255, 255, 40), outline=(255, 255, 255, 120), width=2)
    col = ROJO if (atascado and int(t * 6) % 2 == 0) else AZUL_C
    d.rounded_rectangle([bx + 3, by + 3, bx + 3 + max(10, (bw - 6) * prog), by + bh - 3], 6, fill=col + (255,))
    s, pad = G.sombra(im, dy=8, radio=10, alpha=0.6)
    s = recorte_h(s, ease_out(pin), "izq")
    L.poner(s, 56 - pad, 1342 - pad, pout, "carga_promesa")

# ------------------------------------------------------------------ verificación y líneas de datos (clip 06)
def icono_check(size=26):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size - 1, size - 1], fill=AZUL_E + (255,))
    d.line([(size * 0.27, size * 0.52), (size * 0.44, size * 0.70), (size * 0.75, size * 0.33)], fill=BLANCO + (255,), width=max(2, size // 8), joint="curve")
    return im
CHK = icono_check()

def dibujar_verificacion(L, t):
    ev = GR["verificacion"]; t0 = tl(edl, "06", ev["desde"]); t1 = tl(edl, "06", ev["hasta"])
    if not (t0 <= t <= t1): return
    out = clamp((t1 - t) / 0.3)
    x = 56
    for tt_, lab in ev["checks"]:
        tc = tl(edl, "06", tt_)
        if t < tc: continue
        p = ease_out((t - tc) / 0.25)
        c = chip(lab, (6, 22, 58), BLANCO, size=22, padx=12, pady=7, borde=AZUL_E)
        im = Image.new("RGBA", (c.size[0] + 34, c.size[1]), (0, 0, 0, 0))
        im.alpha_composite(CHK, (0, (c.size[1] - 26) // 2)); im.alpha_composite(c, (34, 0))
        L.poner(im, x, 1458 + (1 - p) * 14, p * out, "verificacion")
        x += im.size[0] + 14

def dibujar_lineas_datos(L, t):
    ev = GR["lineas_datos"]; t0 = tl(edl, "06", ev["desde"]); t1 = tl(edl, "06", ev["hasta"])
    if not (t0 <= t <= t1): return
    pin, pout = ventana(t, t0, t1, 0.5, 0.4)
    a = ease_out(pin) * pout
    im = Image.new("RGBA", (W, 230), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k, yy in enumerate((6, 222)):
        d.line([(40, yy), (W - 40, yy)], fill=AZUL_E + (110,), width=1)
        for i in range(40, W - 40, 40): d.line([(i, yy - 3), (i, yy + 3)], fill=AZUL_C + (120,), width=1)
        for j in range(3):
            px = 40 + (((t - t0) * (0.35 + 0.1 * j) + j * 0.33 + k * 0.5) % 1.0) * (W - 80)
            d.ellipse([px - 3, yy - 3, px + 3, yy + 3], fill=(255, 255, 255, 230))
            d.line([(px - 60, yy), (px, yy)], fill=AZUL_C + (160,), width=2)
    L.poner(im, 0, 1300, a, "lineas_datos")

# ------------------------------------------------------------------ barra informativa (ticker)
TK_Y, TK_H = 1508, 58
F_TK = font("InterDisplay-Bold", 28)
def sprite_ticker_texto():
    s = GR["ticker_texto"] * 3
    w = int(F_TK.getlength(GR["ticker_texto"]))
    im = Image.new("RGBA", (int(F_TK.getlength(s)) + 10, TK_H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = 0
    for ch_ in s:
        col = ROJO_C if ch_ in "•|" else BLANCO
        d.text((x, 12), ch_, font=F_TK, fill=col + (255,)); x += F_TK.getlength(ch_)
    return im, w
TK_TXT, TK_PERIOD = sprite_ticker_texto()
TK_LAB = chip("SÁTIRA Y HUMOR", ROJO, size=24, padx=18, pady=13)
def sprite_ticker_barra():
    im = gradiente_v(W, TK_H, (10, 34, 86), (3, 12, 34), 238, 238); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 2], fill=ROJO + (255,)); d.rectangle([0, TK_H - 2, W, TK_H], fill=PLATA + (180,))
    return im
TK_BAR = sprite_ticker_barra()
TK_EVS = [(tl(edl, *e["desde"]), tl(edl, *e["hasta"])) for e in GR["ticker"]]

def dibujar_ticker(L, t):
    for t0, t1 in TK_EVS:
        if not (t0 <= t <= t1): continue
        pin, pout = ventana(t, t0, t1, 0.4, 0.4)
        p = ease_out(pin) * ease_io(pout)
        bar = TK_BAR.copy()
        off = int(((t - t0) * 120) % TK_PERIOD)
        lab_w = TK_LAB.size[0]
        bar.alpha_composite(TK_TXT.crop((off, 0, off + W - lab_w - 16, TK_H)), (lab_w + 16, 0))
        lab = Image.new("RGBA", (lab_w + 10, TK_H), (0, 0, 0, 0))
        lab.alpha_composite(gradiente_v(lab_w, TK_H, (240, 40, 56), (170, 10, 26)), (0, 0))
        ImageDraw.Draw(lab).polygon([(lab_w, 0), (lab_w + 10, 0), (lab_w, TK_H)], fill=(170, 10, 26, 255))
        lab.alpha_composite(TK_LAB.crop((0, 0, lab_w, TK_LAB.size[1])), (0, (TK_H - TK_LAB.size[1]) // 2))
        bar.alpha_composite(lab, (0, 0))
        bar = recorte_h(bar, p, "izq")
        L.poner(bar, 0, TK_Y, 1.0, "ticker")

# ------------------------------------------------------------------ transiciones
CORTES = [c["t0_frame"] for c in edl["clips"][1:]] + [edl["frames_clips"]]
def banda_luz():
    bw = 2200
    x = np.arange(bw)[None, :] - np.arange(H)[:, None] * 0.36
    def b(c, ancho): return np.clip(1 - np.abs(x - c) / ancho, 0, 1) ** 2
    core = b(1100, 70); halo = b(1100, 320) * 0.55
    red = b(1100 - 330, 22) * 0.9; blu = b(1100 + 300, 30) * 0.9
    rgb = np.zeros((H, bw, 3), np.float32); a = np.zeros((H, bw), np.float32)
    for col, m in (((255, 255, 255), core), ((60, 170, 255), halo), ((235, 30, 50), red), ((40, 150, 255), blu)):
        rgb += np.array(col, np.float32)[None, None] * m[..., None]; a += m
    a = np.clip(a, 0, 1); rgb = rgb / np.maximum(1e-3, np.maximum(a, (rgb.max(2) / 255)))[..., None]
    return np.dstack([rgb.clip(0, 255), a * 255]).astype(np.uint8)
BANDA = banda_luz()

def transicion(base_rgba, fi, box):
    """Barrido luminoso de 0.33 s centrado en cada corte (4 fotogramas antes, 4 después)."""
    for c in CORTES:
        k = fi - c
        if -4 <= k <= 3:
            p = (k + 4.5) / 8.0
            off = int(-1500 + p * (W + 1700))
            x0 = max(0, -off); x1 = min(BANDA.shape[1], W - off)
            if x1 <= x0: continue
            band = np.zeros((H, W, 4), np.uint8)
            band[:, off + x0:off + x1] = BANDA[:, x0:x1]
            intens = math.sin(math.pi * p) * 0.85
            band[..., 3] = (band[..., 3] * intens).astype(np.uint8)
            if box:  # sobre la cabeza la luz pasa atenuada
                bx0, by0, bx1, by1 = [max(0, v) for v in box]
                band[by0:by1, bx0:bx1, 3] = (band[by0:by1, bx0:bx1, 3] * 0.35).astype(np.uint8)
            base_rgba.alpha_composite(Image.fromarray(band, "RGBA"))
            # destello breve en el fotograma de corte
            if k in (0, 1):
                fl = Image.new("RGBA", (W, H), (255, 255, 255, int(40 if k == 0 else 18)))
                base_rgba.alpha_composite(fl)
            # líneas veloces roja/azul en zonas libres
            L = Lienzo(fi); L.box = None
            pp = clamp((k + 4) / 7)
            linea_digital(L, 1318, pp, ROJO, "izq"); linea_digital(L, 1506, pp, AZUL_E, "der")
            base_rgba.alpha_composite(con_alpha(L.im, math.sin(math.pi * pp) + 0.001) or L.im)
            return True
    return False

# ------------------------------------------------------------------ end card
EC_MAPA = MapaRD(os.path.join(ASSETS, "rd_silueta.json"), 820, 520, pad=16)
EC_FILL = EC_MAPA.relleno()
WM_EC, WM_EC_PAD = wordmark(104)
F_EC_LBL = font("InterDisplay-Bold", 24)
ec_fondo = None

def end_card(t_rel, ultimo):
    global ec_fondo
    if ec_fondo is None:
        b = ultimo.filter(ImageFilter.GaussianBlur(26))
        arr = np.asarray(b).astype(np.float32) * 0.28
        arr[..., 2] += 18; arr[..., 1] += 4
        yy = np.linspace(-1, 1, H)[:, None]; xx = np.linspace(-1, 1, W)[None, :]
        vig = 1 - 0.55 * np.clip(xx ** 2 * 0.6 + yy ** 2 * 0.8, 0, 1)
        ec_fondo = Image.fromarray((arr * vig[..., None]).clip(0, 255).astype(np.uint8)).convert("RGBA")
    im = ec_fondo.copy()
    L = Lienzo(10 ** 9); L.box = None
    # rejilla digital tenue
    d = ImageDraw.Draw(im)
    for gy in range(0, H, 60): d.line([(0, gy), (W, gy)], fill=(40, 120, 255, 14))
    # mapa grande
    mx, my = (W - 820) // 2, 380
    pf = clamp((t_rel - 0.55) / 0.4)
    if pf > 0: L.poner(con_alpha(EC_FILL, pf), mx, my, 1, proteger=False)
    cont, _ = EC_MAPA.contorno(ease_out(t_rel / 0.7), ancho=3)
    L.poner(cont, mx, my, 1, proteger=False)
    cap = Image.new("RGBA", (820, 520), (0, 0, 0, 0))
    dibujar_ciudades(ImageDraw.Draw(cap), EC_MAPA, ["Santo Domingo", "Santiago", "Puerto Plata", "Punta Cana"], t_rel, 0.6, 0, 0, F_EC_LBL, escala=1.6, lineas=True)
    L.poner(cap, mx, my, 1, proteger=False)
    # marca
    p = ease_out((t_rel - 0.2) / 0.45)
    s = recorte_h(WM_EC, p, "centro")
    if s is not None:
        s = destello(s, clamp((t_rel - 0.75) / 0.7))
        L.poner(s, (W - WM_EC.size[0]) / 2, 1000 - WM_EC_PAD, 1, proteger=False)
    # franja de bandera
    pb = ease_out((t_rel - 0.5) / 0.3)
    if pb > 0:
        fr = Image.new("RGBA", (int(300 * pb) + 1, 6), (0, 0, 0, 0)); dd = ImageDraw.Draw(fr)
        for i, col in enumerate((RD_AZUL, BLANCO, RD_ROJO)): dd.rectangle([i * 100, 0, i * 100 + 96, 6], fill=col + (255,))
        L.poner(fr, (W - 300) / 2, 1172, 1, proteger=False)
    pl = ease_out((t_rel - 0.65) / 0.35)
    if pl > 0:
        f1 = font("InterDisplay-ExtraBold", 38)
        lema = GR["end_card"]["lema"]
        im2 = Image.new("RGBA", (int(f1.getlength(lema)) + 10, 56), (0, 0, 0, 0))
        ImageDraw.Draw(im2).text((5, 4), lema, font=f1, fill=BLANCO + (255,))
        L.poner(im2, (W - im2.size[0]) / 2, 1206 + (1 - pl) * 16, pl, proteger=False)
        c = chip(GR["end_card"]["pie"], (6, 22, 58), PLATA, size=24, borde=ROJO)
        L.poner(c, (W - c.size[0]) / 2, 1290 + (1 - pl) * 16, pl, proteger=False)
    im.alpha_composite(L.im)
    return im

# ------------------------------------------------------------------ lector de fotogramas base
def lector_base():
    for c in edl["clips"]:
        z = c.get("zoom_recorte", 1.0)
        vf = f"trim=start_frame={c['in']}:end_frame={c['out']},setpts=PTS-STARTPTS"
        if z != 1.0:
            cw = int(round(720 / z / 2) * 2); ch = int(round(1280 / z / 2) * 2)
            vf += f",crop={cw}:{ch}:{(720 - cw) // 2}:0"
        vf += f",scale={W}:{H}:flags=lanczos+accurate_rnd+full_chroma_int:in_color_matrix=bt601:in_range=tv,format=rgb24"
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", c["ruta"], "-vf", vf, "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
        n = 0
        while True:
            buf = p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3: break
            yield Image.frombuffer("RGB", (W, H), buf).copy(), c; n += 1
        p.wait()
        assert n == c["frames"], (c["id"], n, c["frames"])

def limpiar_texto(img, c):
    """Elimina texto incrustado (p. ej. 'Dania Frut:16' del clip 08) sobre el escritorio mediante inpainting
    localizado: solo se modifican los píxeles del texto, lejos de Dania y del logotipo."""
    import cv2
    x0, y0, x1, y1 = c["limpiar_texto"]
    m = 24
    arr = np.asarray(img).copy()
    reg = arr[y0 - m:y1 + m, x0 - m:min(W, x1 + m)].copy()
    g = cv2.cvtColor(reg, cv2.COLOR_RGB2GRAY).astype(np.float32)
    # fondo = mediana horizontal (la superficie del escritorio está formada por bandas horizontales)
    from scipy.ndimage import median_filter
    fondo = median_filter(g, size=(1, 121), mode="nearest")
    mask = (g - fondo) > 5
    lim = np.zeros_like(mask); lim[m:-m, m:-m] = True
    mask = cv2.dilate((mask & lim).astype(np.uint8), np.ones((7, 15), np.uint8)) > 0
    # relleno: interpolación lineal por fila entre los píxeles válidos más cercanos
    xs = np.arange(reg.shape[1])
    for yy in range(reg.shape[0]):
        mm = mask[yy]
        if mm.any() and (~mm).sum() > 2:
            for ch in range(3):
                reg[yy, mm, ch] = np.interp(xs[mm], xs[~mm], reg[yy, ~mm, ch].astype(np.float32)).astype(np.uint8)
    reg = cv2.GaussianBlur(reg, (3, 3), 0) * mask[..., None] + reg * (~mask[..., None])
    arr[y0 - m:y1 + m, x0 - m:min(W, x1 + m)] = reg
    return Image.fromarray(arr)

def punch_in(img, fi):
    for c in CORTES[:-1]:
        k = fi - c
        if 0 <= k < 7:
            z = 1 + 0.035 * (1 - ease_out(k / 7))
            w2, h2 = W / z, H / z
            return img.resize((W, H), Image.BICUBIC, box=((W - w2) / 2, (H - h2) / 2, (W + w2) / 2, (H + h2) / 2))
    return img

# ------------------------------------------------------------------ composición de un fotograma
qa = []
def componer(base, fi):
    t = fi / FPS
    if fi < edl["frames_clips"]:
        base = punch_in(base, fi).convert("RGBA")
        L = Lienzo(fi)
        dibujar_lineas_datos(L, t)
        for ev in GR["mapa_superior"]: dibujar_mapa_panel(L, t, ev)
        dibujar_intro(L, t)
        dibujar_rotulo(L, t)
        dibujar_titulares(L, t)
        dibujar_bateria(L, t); dibujar_carga(L, t); dibujar_verificacion(L, t)
        dibujar_ticker(L, t)
        dibujar_subs(L, t)
        # QA: cobertura de la capa de gráficos dentro de la caja de la cabeza
        cov = 0.0
        if L.box:
            x0, y0, x1, y1 = [max(0, v) for v in L.box]
            a = np.asarray(L.im.getchannel("A"))[y0 + 26:y1 - 26, x0 + 26:x1 - 26]
            cov = float((a > 25).mean()) if a.size else 0.0
        # QA: cobertura en la banda del logotipo del set (y 360-1000)
        band = np.asarray(L.im.getchannel("A"))[360:1000]
        qa.append({"f": fi, "cabeza_cubierta": round(cov, 4), "banda_logo_cubierta": round(float((band > 25).mean()), 4), "conflictos": L.conflictos})
        base.alpha_composite(L.im)
        en_trans = transicion(base, fi, L.box)
        if fi == 0 or fi == 1 or fi == 2:   # destello de apertura (revelado)
            base.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, [90, 45, 15][fi])))
    else:
        base = end_card(t - edl["frames_clips"] / FPS, base)
        transicion(base, fi, None)
        k = NF - fi
        if k <= 8: base.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - k / 8) ** 1.5))))
    return base.convert("RGB")

# ------------------------------------------------------------------ main
def loudnorm_params():
    out = subprocess.run(["ffmpeg", "-nostats", "-i", os.path.join(BUILD, "mezcla.wav"), "-af",
                          f"loudnorm=I={edl['audio']['mezcla_final_lufs']}:TP={edl['audio']['true_peak_db']}:LRA=11:print_format=json",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(out[out.rindex("{"):out.rindex("}") + 1])
    return (f"loudnorm=I={edl['audio']['mezcla_final_lufs']}:TP={edl['audio']['true_peak_db']}:LRA=11:"
            f"measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
            f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")

if __name__ == "__main__":
    args = sys.argv[1:]
    solo = None
    if "--frames" in args:
        solo = set(int(x) for x in args[args.index("--frames") + 1].split(","))
        os.makedirs(os.path.join(SALIDA_DIR, "revision", "fotogramas"), exist_ok=True)
    enc = None
    if solo is None:
        enc = subprocess.Popen([
            "ffmpeg", "-v", "error", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-i", os.path.join(BUILD, "mezcla.wav"),
            "-map", "0:v", "-map", "1:a",
            "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-level", "4.1",
            "-x264-params", "keyint=48:min-keyint=24", "-pix_fmt", "yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
            "-af", loudnorm_params() + ",aresample=48000",
            "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", "-shortest", SALIDA + ".tmp.mp4"], stdin=subprocess.PIPE)
    fi = 0; ultimo = None
    gen = lector_base()
    import time; t_ini = time.time()
    while fi < NF:
        if fi < edl["frames_clips"]:
            base, c = next(gen)
            if c.get("limpiar_texto"): base = limpiar_texto(base, c)
            ultimo = base
        else:
            base = ultimo
        if solo is None or fi in solo:
            fr = componer(base, fi)
            if solo is not None:
                fr.save(os.path.join(SALIDA_DIR, "revision", "fotogramas", f"f{fi:04d}.jpg"), quality=88)
            else:
                enc.stdin.write(fr.tobytes())
        if fi % 100 == 0: print(f"fotograma {fi}/{NF}  {time.time() - t_ini:.0f}s", flush=True)
        fi += 1
        if solo is not None and fi > max(solo): break
    if enc:
        enc.stdin.close(); rc = enc.wait()
        assert rc == 0, "ffmpeg falló"
        os.replace(SALIDA + ".tmp.mp4", SALIDA)
        json.dump(qa, open(os.path.join(BUILD, "qa_overlay.json"), "w"))
        print("OK ->", SALIDA)
