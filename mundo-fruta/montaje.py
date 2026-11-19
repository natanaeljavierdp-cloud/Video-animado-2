"""Une las 8 escenas, pone subtítulos grandes, el título de la revista y el cierre "¿Quién es? 👀 Parte 2".
Uso: python3 montaje.py   -> genera final/mundo_fruta_parte1.mp4"""
import os, subprocess

from PIL import Image, ImageDraw, ImageFont

from escenas import ESCENAS

AQUI = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(AQUI, "tmp")
FIN = os.path.join(AQUI, "final")
W, H, FPS = 1080, 1920, 30
DUR = 8.0
CIERRE = 3.0  # segundos extra en negro con el texto final
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

# Escenas donde se ve la revista -> posición del título (centro x, centro y) en píxeles 1080x1920
TITULO_EN = {1: (540, 1250), 2: (540, 1350), 4: (540, 1350), 6: (540, 1400), 8: (540, 700)}


def sh(*cmd):
    subprocess.run(cmd, check=True)


def texto_png(path, partes, alto=120, borde=8):
    """partes: lista de (texto, es_emoji). Dibuja en blanco con borde negro, fondo transparente."""
    f = ImageFont.truetype(BOLD, alto)
    fe = ImageFont.truetype(EMOJI, 109)
    trozos = []
    for t, emo in partes:
        if emo:
            im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((10, 10), t, font=fe, embedded_color=True)
            im = im.crop(im.getbbox()).resize((int(alto * 1.1), int(alto * 1.1)), Image.LANCZOS)
        else:
            bb = f.getbbox(t, stroke_width=borde)
            im = Image.new("RGBA", (bb[2] - bb[0], int(alto * 1.3)), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((-bb[0], int(alto * 0.1)), t, font=f, fill="white",
                                    stroke_width=borde, stroke_fill="black")
        trozos.append(im)
    ancho = sum(t.width for t in trozos) + 20 * (len(trozos) - 1)
    alto_t = max(t.height for t in trozos)
    out = Image.new("RGBA", (ancho, alto_t), (0, 0, 0, 0))
    x = 0
    for t in trozos:
        out.paste(t, (x, (alto_t - t.height) // 2), t)
        x += t.width + 20
    out.save(path)


def titulo_png(path):
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 64)
    t1, t2 = "The Fruitonomist", "2027"
    im = Image.new("RGBA", (760, 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, t in enumerate((t1, t2)):
        w = d.textlength(t, font=f)
        d.text(((760 - w) / 2, 10 + i * 85), t, font=f, fill=(255, 245, 225), stroke_width=4,
               stroke_fill=(150, 0, 0))
    im.save(path)


def ass_time(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def subtitulos(path):
    cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,DejaVu Sans,74,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,7,3,2,70,70,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lineas = []
    for e in ESCENAS:
        base = (e["n"] - 1) * DUR
        for a, b, t in e["subs"]:
            lineas.append(f"Dialogue: 0,{ass_time(base + a)},{ass_time(base + b)},Sub,,0,0,0,,{t}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(cab + "\n".join(lineas) + "\n")


def main():
    os.makedirs(TMP, exist_ok=True); os.makedirs(FIN, exist_ok=True)
    titulo = os.path.join(TMP, "titulo.png"); titulo_png(titulo)
    cierre = os.path.join(TMP, "cierre.png")
    l1, l2 = os.path.join(TMP, "c1.png"), os.path.join(TMP, "c2.png")
    texto_png(l1, [("¿Quién es?", False), ("👀", True)], alto=110)
    texto_png(l2, [("Parte 2", False)], alto=110)
    a, b = Image.open(l1), Image.open(l2)
    c = Image.new("RGBA", (max(a.width, b.width), a.height + b.height + 30), (0, 0, 0, 0))
    c.paste(a, ((c.width - a.width) // 2, 0), a); c.paste(b, ((c.width - b.width) // 2, a.height + 30), b)
    c.save(cierre)

    # 1) Normalizar cada escena (1080x1920, 30 fps, 8 s, audio estéreo) y poner el título si hay revista
    partes = []
    for e in ESCENAS:
        n = e["n"]
        src = os.path.join(AQUI, "videos", f"escena_{n}.mp4")
        dst = os.path.join(TMP, f"n{n}.mp4")
        vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
              f"trim=0:{DUR},setpts=PTS-STARTPTS[v0]")
        ins = ["-i", src]
        if n in TITULO_EN:
            cx, cy = TITULO_EN[n]
            ins += ["-loop", "1", "-i", titulo]
            vf += f";[v0][1:v]overlay={cx}-w/2:{cy}-h/2:shortest=1:enable='between(t,0.3,{DUR})'[v]"
        else:
            vf += ";[v0]null[v]"
        sh("ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", vf, "-map", "[v]", "-map", "0:a?",
           "-af", f"aresample=48000,apad,atrim=0:{DUR}", "-ac", "2", "-t", str(DUR),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           dst)
        partes.append(dst)

    # 2) Cierre: negro + texto final
    negro = os.path.join(TMP, "cierre.mp4")
    sh("ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=black:s={W}x{H}:r={FPS}:d={CIERRE}",
       "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(CIERRE),
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", negro)
    partes.append(negro)

    # 3) Unir todo
    lista = os.path.join(TMP, "lista.txt")
    with open(lista, "w") as f:
        f.writelines(f"file '{p}'\n" for p in partes)
    unido = os.path.join(TMP, "unido.mp4")
    sh("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lista, "-c", "copy", unido)

    # 4) Subtítulos + texto final (aparece en los últimos 1.5 s de la escena 8 y se queda en el cierre)
    ass = os.path.join(TMP, "subs.ass"); subtitulos(ass)
    t0 = 8 * DUR - 1.5
    out = os.path.join(FIN, "mundo_fruta_parte1.mp4")
    sh("ffmpeg", "-y", "-loglevel", "error", "-i", unido, "-loop", "1", "-i", cierre, "-filter_complex",
       f"[0:v]ass={ass}[s];[1:v]format=rgba,fade=in:st={t0}:d=0.6:alpha=1[c];"
       f"[s][c]overlay=(W-w)/2:(H-h)/2:shortest=1:enable='gte(t,{t0})'[v]",
       "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
       "-c:a", "copy", "-movflags", "+faststart", out)
    print("LISTO", out)


if __name__ == "__main__":
    main()
