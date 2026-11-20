"""Subtítulos: arriba al centro, 1-4 palabras, letra negra muy gruesa con halo blanco.
Palabras clave en rojo, palabras de relleno en gris. Sincronizados con los tiempos por palabra."""
import json
import math
import os
import cairo
from common import *

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "Inter Display Black"

# *palabra* = clave (rojo). Cada fragmento = 1-4 palabras del guion, en orden.
CHUNKS = """¿Alguna vez|te has preguntado|qué pasa|cuando jalas|la *cadena*|del *inodoro*?|Vamos por *dentro*.
|Todo empieza|en el *tanque*.|Ahí espera|el *agua limpia*,|*quietecita*,|lista para *trabajar*.
|Cuando bajas|la *palanca*,|se levanta|un *tapón de goma*|en el fondo|del *tanque*…|y el agua|*cae de golpe*|a la *taza*.
|Esa *fuerza*|empuja todo|hacia un *tubo curvo*|escondido dentro|del inodoro:|el *sifón*.
|Cuando el *sifón*|se llena,|crea una *succión*|que jala todo|hacia *abajo*.|Ese es|el *sonido*|que escuchas.
|Mientras tanto,|el *tanque* se vacía|y un *flotador*|baja.|Al bajar,|abre una *válvula*,|y entra|*agua nueva*|desde la *tubería*|de la casa.
|El agua *sube*,|el *flotador*|sube con ella…|y cuando llega|al *nivel correcto*,|cierra la *válvula*.|*Listo* para|la próxima.
|¿Y lo que|se fue?|Viaja por|la *tubería*|de tu casa|hasta el|*alcantarillado*|de la calle,|se junta|con la de|todo el *barrio*,|y termina|en una *planta*|de *tratamiento*.
|Allí *separan*|los *sólidos*,|unas *bacterias* buenas|se *comen*|la *suciedad*,|y el agua,|ya *limpia*,|regresa al *río*.
|Y *fíjate*|en algo:|en la taza|siempre queda|un *poquito*|de *agua*.|Ese poquito|es un *sello*|que no deja|que los|*malos olores*|de la tubería|suban a tu *baño*.
|Todo eso pasa|en unos|*diez segundos*.|*Síguenos*|para ver|más cosas…|por *dentro*."""

FILLER = set("el la los las un una unas unos de del a al en y que se con por para lo tu es ese eso".split())


def build():
    words = json.load(open(os.path.join(HERE, 'words.json')))
    chunks = [c.strip() for c in CHUNKS.replace('\n', '').split('|') if c.strip()]
    out = []
    wi = 0
    for c in chunks:
        toks = []
        key = False
        for raw in c.split(' '):
            starts = raw.startswith('*') or raw.startswith('¿*')
            if starts:
                key = True
            clean = raw.replace('*', '')
            toks.append((clean, key))
            if raw.rstrip('.,…?:').endswith('*'):
                key = False
        n = len(toks)
        assert 1 <= n <= 4, c
        s = words[wi]['s']
        e = words[wi + n - 1]['e']
        out.append(dict(toks=toks, s=s, e=e))
        wi += n
    assert wi == len(words), (wi, len(words))
    # tiempos de visualización
    for i, c in enumerate(out):
        c['on'] = max(0.0, c['s'] - 0.06)
        nxt = out[i + 1]['s'] - 0.06 if i + 1 < len(out) else 999
        c['off'] = min(nxt, c['e'] + 0.55)
    return out


CAPS = build()


def color_for(word, key):
    if key:
        return PAL['red']
    w = word.lower().strip('¿?.,…:')
    if w in FILLER:
        return C('#7d7d7d')
    return C('#141414')


def draw(ctx, t):
    cur = None
    for c in CAPS:
        if c['on'] <= t < c['off']:
            cur = c
            break
    if cur is None:
        return
    Pen.z = 1.0
    age = t - cur['on']
    k = clamp(age / 0.22)
    sc = 0.55 + 0.45 * back(k)
    alpha = clamp(age / 0.08)
    yoff = (1 - ss(k)) * 26
    ctx.save()
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    size = 100
    ctx.set_font_size(size)
    texts = [w.upper() for w, _ in cur['toks']]
    space = size * 0.27
    widths = [ctx.text_extents(x).x_advance for x in texts]
    # partir en 2 líneas si no cabe
    maxw = 940
    lines = [list(range(len(texts)))]
    total = sum(widths) + space * (len(texts) - 1)
    if total > maxw and len(texts) > 1:
        best = None
        for cut in range(1, len(texts)):
            a = sum(widths[:cut]) + space * (cut - 1)
            b = sum(widths[cut:]) + space * (len(texts) - cut - 1)
            m = max(a, b)
            if best is None or m < best[0]:
                best = (m, cut)
        lines = [list(range(best[1])), list(range(best[1], len(texts)))]
        total = best[0]
    fit = min(1.0, maxw / total)
    ctx.translate(W / 2, 300 + yoff)
    ctx.scale(sc * fit, sc * fit)
    lh = size * 1.08
    y0 = -lh * (len(lines) - 1) / 2
    ctx.push_group()
    for pass_ in range(3):
        for li, idxs in enumerate(lines):
            lw_ = sum(widths[i] for i in idxs) + space * (len(idxs) - 1)
            x = -lw_ / 2
            y = y0 + li * lh + size * 0.36
            for i in idxs:
                ctx.move_to(x, y + (8 if pass_ == 0 else 0))
                ctx.text_path(texts[i])
                if pass_ == 0:      # sombra suave
                    ctx.save()
                    ctx.translate(0, 0)
                    setc(ctx, C('#000000', 0.22))
                    ctx.set_line_width(30)
                    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
                    ctx.stroke()
                    ctx.restore()
                elif pass_ == 1:    # halo blanco
                    setc(ctx, PAL['white'])
                    ctx.set_line_width(24)
                    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
                    ctx.stroke()
                else:
                    setc(ctx, color_for(cur['toks'][i][0], cur['toks'][i][1]))
                    ctx.fill()
                x += widths[i] + space
        if pass_ == 0:
            # desplazar la sombra hacia abajo
            pass
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
    ctx.restore()


if __name__ == '__main__':
    for c in CAPS:
        print(f"{c['on']:6.2f}-{c['off']:6.2f}  " + ' '.join(('[' + w + ']') if k else w for w, k in c['toks']))
