"""Boceto CGI Motion 2.5D: anima la ilustracion de referencia con capas,
mapa de profundidad (paralaje), respiracion, parpadeo, gesto de cabeza,
sonrisa, mano y pelo. Bucle perfecto de 10 s a 30 fps, 1080x1920.

Uso:
  python3 animar_25d.py prep   <ref.png> <alpha.png> <depth.npy> <workdir>
  python3 animar_25d.py frames <workdir> [lista de frames, p.ej. 0,150,299]
  python3 animar_25d.py all    <workdir>
"""
import os, sys, math
import numpy as np
import cv2

S = 1.6                      # escala del lienzo de trabajo respecto a la referencia
OW, OH = 1080, 1920
FPS, T = 30, 10.0
N = int(FPS * T)
VIEW_W = 1240.0              # ancho (px lienzo) visible con zoom 1


# ---------------------------------------------------------------- utilidades
def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)

def sm(a, b, x):  # escalar
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)

def env(t, a, b, c, d):
    """sube de a->b, se mantiene, baja c->d"""
    return sm(a, b, t) * (1 - sm(c, d, t))


# ---------------------------------------------------------------- preparacion
def prep(ref, alpha_png, depth_npy, wd):
    os.makedirs(wd, exist_ok=True)
    img = cv2.imread(ref)
    h, w = img.shape[:2]
    cw, ch = int(round(w * S)), int(round(h * S))
    can = cv2.resize(img, (cw, ch), interpolation=cv2.INTER_LANCZOS4)
    a = cv2.imread(alpha_png, cv2.IMREAD_UNCHANGED)[:, :, 3]
    a = cv2.resize(a, (cw, ch), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255
    d = np.load(depth_npy).astype(np.float32)
    d = cv2.resize(d, (cw, ch), interpolation=cv2.INTER_LINEAR)
    d = cv2.GaussianBlur(d, (0, 0), 6)

    # acabado "render": suaviza trazos pictoricos conservando bordes
    fg = can.copy()
    for _ in range(2):
        fg = cv2.bilateralFilter(fg, 9, 22, 7)
    fg = cv2.addWeighted(fg, 0.75, can, 0.25, 0)

    # fondo: rellena lo que tapa la persona/sillon y lo desenfoca (bokeh)
    m = (a > 0.05).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((31, 31), np.uint8))
    small = cv2.resize(can, (cw // 4, ch // 4), interpolation=cv2.INTER_AREA)
    ms = cv2.resize(m, (cw // 4, ch // 4), interpolation=cv2.INTER_NEAREST)
    inp = cv2.inpaint(small, ms, 25, cv2.INPAINT_TELEA)
    inp = cv2.GaussianBlur(inp, (0, 0), 8)
    inp = cv2.resize(inp, (cw, ch), interpolation=cv2.INTER_CUBIC)
    mf = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 6)[..., None]
    bg = can.astype(np.float32) * (1 - mf) + inp.astype(np.float32) * mf
    bg = cv2.GaussianBlur(bg, (0, 0), 3.0)

    # mascara de pelo (zonas de mechones que cuelgan) en coords referencia
    hm = np.zeros((h, w), np.uint8)
    left = np.array([(335, 300), (445, 330), (455, 600), (440, 900), (385, 930),
                     (300, 760), (285, 470)], np.int32)
    right = np.array([(690, 300), (790, 330), (875, 480), (905, 700), (895, 870),
                      (835, 890), (775, 660), (715, 470)], np.int32)
    cv2.fillPoly(hm, [left, right], 255)
    hm = cv2.resize(hm, (cw, ch), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255
    hm = cv2.GaussianBlur(hm, (0, 0), 22)

    np.save(f"{wd}/fg.npy", fg)
    np.save(f"{wd}/alpha.npy", a)
    np.save(f"{wd}/depth_c.npy", d)
    np.save(f"{wd}/bg.npy", bg.astype(np.uint8))
    np.save(f"{wd}/hair.npy", hm)
    print("prep ok", cw, ch)


# ---------------------------------------------------------------- parpadeo
EYES = [  # esquina a, apice sup, esquina b, apice inf, lado exterior
    dict(a=(481, 196), u=(513, 182), b=(542, 202), l=(515, 204), outer=0),
    dict(a=(586, 206), u=(612, 187), b=(648, 193), l=(617, 207), outer=1),
]

def quad(p0, p1, p2, x):
    (x0, y0), (x1, y1), (x2, y2) = p0, p1, p2
    return (y0 * (x - x1) * (x - x2) / ((x0 - x1) * (x0 - x2)) +
            y1 * (x - x0) * (x - x2) / ((x1 - x0) * (x1 - x2)) +
            y2 * (x - x0) * (x - x1) / ((x2 - x0) * (x2 - x1)))

def blink(img, b):
    if b <= 0.002:
        return img
    out = img.copy()
    for e in EYES:
        xa, xb = e["a"][0] * S, e["b"][0] * S
        pa = (e["a"][0] * S, e["a"][1] * S); pb = (e["b"][0] * S, e["b"][1] * S)
        pu = (e["u"][0] * S, e["u"][1] * S); pl = (e["l"][0] * S, e["l"][1] * S)
        ml = 8 * S if e["outer"] == 0 else 2 * S      # margen extra del lado exterior
        mr = 8 * S if e["outer"] == 1 else 2 * S
        x0, x1 = int(xa - ml) - 2, int(xb + mr) + 3
        y0, y1 = int(pu[1] - 20 * S), int(pl[1] + 6 * S)
        X, Y = np.meshgrid(np.arange(x0, x1, dtype=np.float32),
                           np.arange(y0, y1, dtype=np.float32))
        xs = np.clip(X, xa, xb)
        U = quad(pa, pu, pb, xs)
        L = quad(pa, pl, pb, xs)
        E = U + b * (L - U - 0.6 * S)
        # piel del parpado: color muestreado justo encima de las pestanas
        # (por columna se toma la muestra mas clara: evita pestanas y cejas)
        samples = np.stack([cv2.remap(img, X, (U - k * S).astype(np.float32), cv2.INTER_LINEAR,
                                      borderMode=cv2.BORDER_REFLECT).astype(np.float32)
                            for k in np.arange(7.0, 14.5, 1.0)])
        idx = samples.sum(axis=3).argmax(axis=0)
        skin = np.take_along_axis(samples, idx[None, ..., None].repeat(3, axis=3), 0)[0]
        skin = cv2.GaussianBlur(skin, (0, 0), 4.0 * S)
        tout = (xs - xa) / (xb - xa)
        tout = 1 - tout if e["outer"] == 0 else tout
        Y0 = U - (7 + 5 * tout ** 2) * S
        rel = np.clip((Y - Y0) / np.maximum(E - Y0, 1), 0, 1)
        lid = skin * (1.03 - 0.16 * rel ** 1.6)[..., None]    # sombreado hacia el borde
        cover = np.where(Y < U, sm(0, 0.35, b) * smooth(Y0, Y0 + 2.5 * S, Y), 1.0)
        cover = cover * (1 - smooth(E, E + 1.0 * S, Y))
        cover = cv2.GaussianBlur(cover.astype(np.float32), (0, 0), 0.7)[..., None]
        patch = img[y0:y1, x0:x1].astype(np.float32) * (1 - cover) + lid * cover
        # linea de pestanas en el borde del parpado
        lm = np.zeros(X.shape, np.float32)
        xx = np.linspace(xa, xb, 60)
        Uc = quad(pa, pu, pb, xx); Lc = quad(pa, pl, pb, xx)
        Ec = Uc + b * (Lc - Uc - 0.6 * S)
        tpar = (xx - xa) / (xb - xa)
        if e["outer"] == 0:
            tpar = 1 - tpar
        thick = (0.6 + 1.1 * tpar ** 1.5) * S   # mas gruesa hacia el exterior
        for i in range(len(xx) - 1):
            cv2.line(lm, (int((xx[i] - x0) * 4), int((Ec[i] + 0.3 * S - y0) * 4)),
                     (int((xx[i + 1] - x0) * 4), int((Ec[i + 1] + 0.3 * S - y0) * 4)),
                     1.0, max(1, int(thick[i] * 4)), cv2.LINE_AA, shift=2)
        # pestanas cortas hacia abajo en la mitad exterior
        for i in range(2, len(xx) - 2, 3):
            if tpar[i] < 0.35:
                continue
            ln = (1.0 + 2.0 * tpar[i]) * S
            dxl = (-1 if e["outer"] == 0 else 1) * ln * 0.5 * tpar[i]
            p0 = (int((xx[i] - x0) * 4), int((Ec[i] + 0.5 * S - y0) * 4))
            p1 = (int((xx[i] + dxl - x0) * 4), int((Ec[i] + 0.5 * S + ln - y0) * 4))
            cv2.line(lm, p0, p1, 0.6, 2, cv2.LINE_AA, shift=2)
        lm = np.clip(cv2.GaussianBlur(lm, (0, 0), 0.6), 0, 1) * sm(0.2, 0.55, b)
        lash = np.array([28, 34, 52], np.float32)
        p = patch * (1 - lm[..., None]) + lash * lm[..., None]
        # mezcla con bordes suaves
        fx = smooth(xa - ml, xa - ml + 4, X) * (1 - smooth(xb + mr - 4, xb + mr, X))
        fy = smooth(y0, y0 + 4, Y) * (1 - smooth(y1 - 4, y1, Y))
        f = (fx * fy)[..., None]
        reg = out[y0:y1, x0:x1].astype(np.float32)
        out[y0:y1, x0:x1] = np.clip(reg * (1 - f) + p * f, 0, 255).astype(out.dtype)
    return out


def blink_amount(t):
    def one(tc):
        if tc < 0 or tc > 0.32:
            return 0.0
        if tc < 0.09:
            return sm(0, 0.09, tc)
        if tc < 0.13:
            return 1.0
        return 1 - sm(0.13, 0.32, tc)
    return max(one(t - 2.55), one(t - 8.35))


# ---------------------------------------------------------------- animacion
def rot_disp(X, Y, px, py, ang, w):
    """desplazamiento inverso de una rotacion 'ang' (rad) ponderada por w"""
    a = -ang * w
    c, s = np.cos(a), np.sin(a)
    dx, dy = X - px, Y - py
    return (c * dx - s * dy) - dx, (s * dx + c * dy) - dy

def gauss(X, Y, cx, cy, sg):
    return np.exp(-(((X - cx) ** 2 + (Y - cy) ** 2) / (2 * sg * sg)))

def ell_w(X, Y, cx, cy, rx, ry, r0, r1):
    r = np.sqrt(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2)
    return 1 - smooth(r0, r1, r)

def camera(t):
    u = t / T
    s = sm(0, 0.75, u) if u < 0.75 else 1 - sm(0.75, 1.0, u)
    z = 1 + 0.10 * s
    cx = 872 + 18 * math.sin(2 * math.pi * u)
    cy = 1122 - 50 * s
    zb = 1 + 0.06 * s
    bx = 872 + 5 * math.sin(2 * math.pi * u)
    by = 1122 - 60 * s
    return s, z, cx, cy, zb, bx, by


G = {}

def load(wd):
    for k in ["fg", "alpha", "depth_c", "bg", "hair"]:
        G[k] = np.load(f"{wd}/{k}.npy")
    rng = np.random.default_rng(7)
    G["bokeh"] = [dict(x=rng.uniform(150, 1650), y=rng.uniform(80, 1100),
                       r=rng.uniform(12, 34), a=rng.uniform(0.05, 0.14),
                       ph=rng.uniform(0, 2 * math.pi), rad=rng.uniform(6, 16),
                       col=(rng.uniform(0.85, 1.0), rng.uniform(0.9, 1.0), 1.0))
                  for _ in range(18)]
    ox, oy = np.meshgrid(np.arange(OW, dtype=np.float32), np.arange(OH, dtype=np.float32))
    G["ox"], G["oy"] = ox - OW / 2, oy - OH / 2
    ys = np.linspace(-1, 1, OH)[:, None]; xs = np.linspace(-1, 1, OW)[None, :]
    G["vig"] = (1 - 0.22 * smooth(0.55, 1.45, np.sqrt(xs ** 2 * 0.8 + ys ** 2))).astype(np.float32)


def render(fi):
    t = fi / FPS
    u = t / T
    s, z, cx, cy, zb, bx, by = camera(t)
    k = VIEW_W / OW
    ox, oy = G["ox"], G["oy"]

    # ---- fondo (capa lejana, zoom menor -> paralaje)
    bgs = G["bg"].astype(np.float32).copy()
    bl = np.zeros(bgs.shape[:2], np.float32); bc = np.zeros_like(bgs)
    for b in G["bokeh"]:
        x = b["x"] + b["rad"] * math.cos(2 * math.pi * u + b["ph"])
        y = b["y"] + b["rad"] * 0.6 * math.sin(2 * math.pi * u + b["ph"])
        a = b["a"] * (0.75 + 0.25 * math.sin(2 * math.pi * 2 * u + b["ph"]))
        tmp = np.zeros_like(bl)
        cv2.circle(tmp, (int(x * 4), int(y * 4)), int(b["r"] * 4), 1.0, -1, cv2.LINE_AA, shift=2)
        bl += tmp * a
        bc += tmp[..., None] * a * np.array(b["col"], np.float32)[::-1] * 255
    bl = cv2.GaussianBlur(bl, (0, 0), 2.5); bc = cv2.GaussianBlur(bc, (0, 0), 2.5)
    bgs = bgs * (1 - np.clip(bl, 0, 0.5)[..., None]) + bc + bgs * bl[..., None] * 0.4
    mbx = (bx + ox * k / zb).astype(np.float32)
    mby = (by + oy * k / zb).astype(np.float32)
    bgo = cv2.remap(bgs, mbx, mby, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)

    # ---- capa personaje: camara + profundidad
    X = cx + ox * k / z
    Y = cy + oy * k / z
    X = X.astype(np.float32); Y = Y.astype(np.float32)
    d = cv2.remap(G["depth_c"], X, Y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    par = (d - 0.75) * 0.22 * (z - 1)
    X = X - par * (X - cx) - (d - 0.75) * 10 * math.sin(2 * math.pi * u)
    Y = Y - par * (Y - cy)

    # ---- deformaciones del personaje (coords lienzo)
    dx = np.zeros_like(X); dy = np.zeros_like(Y)
    # respiracion (3 ciclos en el bucle)
    br = math.sin(2 * math.pi * 3 * u)
    wv = 1 - smooth(520 * S, 900 * S, Y)
    wx = smooth(180 * S, 260 * S, X) * (1 - smooth(900 * S, 980 * S, X))
    dy += 2.4 * S * br * wv * wx
    dx += -0.8 * S * br * wv * wx * np.clip((X - 565 * S) / (300 * S), -1, 1)

    # cabeza: inclinacion + leve asentimiento
    eh = env(t, 2.0, 3.3, 6.8, 8.9)
    ang = math.radians(2.4 * eh + 0.35 * math.sin(2 * math.pi * 2 * u))
    wh = ell_w(X, Y, 565 * S, 255 * S, 175 * S, 215 * S, 0.85, 1.75)
    rx, ry = rot_disp(X, Y, 560 * S, 430 * S, ang, wh)
    dx += rx; dy += ry
    dy += 1.2 * S * eh * wh            # sube un poco la cara al sonreir

    # sonrisa mas amplia + mejillas + leve entrecerrar de ojos
    es = env(t, 2.3, 3.6, 6.6, 8.6)
    for (mx, my, vx, vy) in [(510, 291, -2.6, -2.0), (610, 295, 2.6, -2.0)]:
        g = gauss(X, Y, mx * S, my * S, 15 * S) * es
        dx -= vx * S * g; dy -= vy * S * g
    for (mx, my) in [(498, 262), (628, 266)]:
        g = gauss(X, Y, mx * S, my * S, 22 * S) * es
        dy += 1.3 * S * g
    for (mx, my) in [(515, 207), (617, 209)]:
        g = gauss(X, Y, mx * S, my * S, 9 * S) * es
        dy += 0.9 * S * g

    # mano sobre la rodilla
    ehd = env(t, 4.0, 5.1, 5.4, 6.9)
    whd = ell_w(X, Y, 400 * S, 1268 * S, 115 * S, 108 * S, 0.8, 1.45)
    rx, ry = rot_disp(X, Y, 455 * S, 1185 * S, math.radians(-3.0 * ehd), whd)
    dx += rx; dy += ry
    dx += 2.0 * S * ehd * whd

    # pelo: vaiven suave, mas marcado entre 3.5 y 7.5 s
    hm = cv2.remap(G["hair"], X, Y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    A = (1.0 + 2.6 * env(t, 3.4, 4.6, 6.6, 8.2)) * S
    g = smooth(330 * S, 760 * S, Y)
    dx += A * hm * g * np.sin(2 * math.pi * 2 * u - (Y / S - 350) / 260)

    MX = (X + dx).astype(np.float32); MY = (Y + dy).astype(np.float32)
    fgimg = blink(G["fg"], blink_amount(t))
    fgo = cv2.remap(fgimg, MX, MY, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    al = cv2.remap(G["alpha"], MX, MY, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    al = np.clip(al, 0, 1)

    # ---- iluminacion tipo render: contraluz (rim), light wrap
    sh = cv2.warpAffine(al, np.float32([[1, 0, -9], [0, 1, 7]]), (OW, OH), borderMode=cv2.BORDER_REPLICATE)
    rim = np.clip(al - cv2.GaussianBlur(sh, (0, 0), 4), 0, 1)
    rim = cv2.GaussianBlur(rim, (0, 0), 2.0) * (1 - smooth(650, 1100, oy + OH / 2))
    fgo += rim[..., None] * np.array([205, 228, 255], np.float32) * 0.32
    edge = np.clip(al * (1 - cv2.GaussianBlur(al, (0, 0), 6)) * 2.2, 0, 1)
    bgb = cv2.GaussianBlur(bgo, (0, 0), 10)
    fgo = fgo * (1 - 0.35 * edge[..., None]) + bgb * 0.35 * edge[..., None]

    # sombra de contacto suave del personaje sobre el sillon/fondo
    shadow = cv2.GaussianBlur(al, (0, 0), 18)
    bgo = bgo * (1 - 0.18 * shadow[..., None])
    comp = fgo * al[..., None] + bgo * (1 - al[..., None])

    # ---- acabado: bloom, gradacion calida, vineta, nitidez
    lum = comp.mean(axis=2)
    hi = comp * smooth(170, 250, lum)[..., None]
    small = cv2.resize(hi, (OW // 4, OH // 4), interpolation=cv2.INTER_AREA)
    bloom = cv2.resize(cv2.GaussianBlur(small, (0, 0), 7), (OW, OH), interpolation=cv2.INTER_LINEAR)
    comp = comp + bloom * 0.12
    c = np.clip(comp / 255, 0, 1)
    c = c + 0.04 * (c - c * c) * (2 * c - 1)          # curva S suave
    c = c * np.array([0.985, 1.0, 1.03], np.float32)   # BGR: leve calidez
    c = c * G["vig"][..., None]
    c = np.clip(c * 255, 0, 255)
    blur = cv2.GaussianBlur(c, (0, 0), 1.2)
    c = np.clip(c + 0.15 * (c - blur), 0, 255)
    return c.astype(np.uint8)


def _work(args):
    wd, fi = args
    if not G:
        load(wd)
    cv2.imwrite(f"{wd}/frames/f{fi:04d}.png", render(fi))
    return fi


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "prep":
        prep(*sys.argv[2:6])
    else:
        wd = sys.argv[2]
        os.makedirs(f"{wd}/frames", exist_ok=True)
        fis = range(N) if mode == "all" else [int(v) for v in sys.argv[3].split(",")]
        load(wd)
        from multiprocessing import Pool
        with Pool(4) as p:
            for fi in p.imap_unordered(_work, [(wd, f) for f in fis]):
                if fi % 30 == 0:
                    print("frame", fi, flush=True)
