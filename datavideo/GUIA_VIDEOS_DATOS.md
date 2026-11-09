# Videos con gráficos estadísticos animados (TikTok / Instagram)

Guía para que Claude Code genere videos verticales con visualizaciones de datos **solo con código** (Python + matplotlib + ffmpeg), sin Canva ni otras apps. Pensado para videos cortos sobre temas de República Dominicana.

## Qué produce

- MP4 vertical **1080×1920**, 30 fps, H.264 (`yuv420p`), listo para TikTok, Reels y Shorts.
- Dos tipos de gráfico: **barras** que crecen una a una, o **línea** que se va dibujando.
- Un **contador grande** que sube junto con la animación (por ejemplo, de 0 a 10.760.028).
- Título, subtítulo y **fuente** de los datos en pantalla.
- Duración típica: unos 6 s de animación + 2,5 s de pausa final, para un total cercano a 8,5 s.

## Requisitos

```bash
python3 -c "import matplotlib, numpy"   # matplotlib 3.x, numpy
ffmpeg -version
```

Si falta algo: `pip install matplotlib numpy` y, para ffmpeg, `brew install ffmpeg` (Mac) o `sudo apt install ffmpeg` (Linux).
La fuente por defecto es **Inter**. Si no está instalada, cambia `"fuente"` en el JSON a `"DejaVu Sans"` o a otra fuente del sistema.

## Estructura del proyecto

```
datavideo/
├── generar_video.py      # el generador (código completo abajo)
├── datos/
│   └── poblacion_rd.json # un JSON por video
└── salida/
    └── poblacion_rd.mp4
```

## Cómo usarlo

```bash
python3 generar_video.py datos/poblacion_rd.json salida/poblacion_rd.mp4
```

Para revisar un fotograma sin abrir el video:

```bash
ffmpeg -y -ss 8 -i salida/poblacion_rd.mp4 -frames:v 1 revision.png
```

## Formato del JSON

| Campo | Obligatorio | Descripción |
|---|---|---|
| `tipo` | no | `"barras"` (por defecto) o `"linea"` |
| `titulo` | sí | Texto grande arriba. Usa `\n` para partir líneas (máximo 2 líneas). |
| `subtitulo` | no | Línea gris debajo del título |
| `etiquetas` | sí | Valores del eje X (años, provincias…) |
| `valores` | sí | Números, en el mismo orden que `etiquetas` |
| `etiqueta_contador` | no | Texto debajo del contador; se le añade la etiqueta actual (por ejemplo, "habitantes en" + "2022") |
| `formato_corto` | no | Formato de las cifras sobre cada barra, por ejemplo `{"escala": 1000000, "decimales": 1, "sufijo": " M"}` |
| `prefijo` / `sufijo` / `decimales` / `escala` | no | Formato del contador grande (por ejemplo, `"prefijo": "US$"`, `"sufijo": "%"`) |
| `separador_es` | no | `true` por defecto: 10.760.028 y 1,5 (formato dominicano/español) |
| `fuente` | sí | Fuente de los datos. Siempre se muestra. |
| `duracion_animacion` | no | Segundos que dura la animación (6 por defecto) |
| `pausa_final` | no | Segundos con el gráfico completo al final (2,5 por defecto) |
| `audio` | no | MP3 de la narración (ruta relativa al JSON). El video dura lo que dure el audio + `cola_audio` (1 s por defecto) y se une solo. |
| `tiempos` | no | Segundo en que empieza a crecer cada barra (uno por etiqueta). Sacarlos de la transcripción con tiempos por palabra (ElevenLabs Scribe). |
| `duracion_barra` | no | Segundos que tarda en crecer cada barra cuando se usa `tiempos` (1 por defecto) |
| `remate` | no | Frase final que aparece en grande, por ejemplo `{"texto": "×5 en 70 años", "inicio": 20.0}` |
| `estilo` | no | Para cambiar colores o la fuente: `fondo`, `texto`, `texto_suave`, `acento`, `barra`, `rejilla`, `fuente` |

### Ejemplo verificado (población de RD según los censos de la ONE)

```json
{
  "tipo": "barras",
  "titulo": "¿Cuántos dominicanos\nhay?",
  "subtitulo": "Población según cada censo nacional",
  "etiquetas": [1950, 1960, 1970, 1981, 1993, 2002, 2010, 2022],
  "valores": [2135872, 3047070, 4009458, 5545741, 7293390, 8562541, 9445281, 10760028],
  "etiqueta_contador": "habitantes en",
  "formato_corto": {"escala": 1000000, "decimales": 1, "sufijo": " M"},
  "fuente": "ONE, censos nacionales 1950–2022",
  "duracion_animacion": 6.0,
  "pausa_final": 2.5
}
```

## Reglas de diseño (siempre respetarlas)

1. **Zona segura de TikTok/Reels:** no poner nada importante en los ~300 px de abajo (descripción del video) ni en los ~150 px de la derecha (botones). El script ya deja esos márgenes; no los cambies.
2. **Máximo 8 elementos** por gráfico. Si hay más, se agrupan o se elige lo más relevante. Más de 8 no se lee en el celular.
3. **Un solo mensaje por video.** El dato final, en color de acento, es la conclusión.
4. **Siempre mostrar la fuente** (ONE, Banco Central, Banco Mundial, etc.).
5. Usar números con formato dominicano: punto para los miles y coma para los decimales.

## Datos: cómo conseguirlos y verificarlos

- Fuentes preferidas para RD: **ONE** (one.gob.do), **Banco Central** (bancentral.gov.do), **MEPyD**, **Banco Mundial** y **CEPAL**.
- Antes de generar el video, **verificar cada cifra en al menos una fuente oficial** y anotar en `fuente` el nombre exacto y el año.
- No inventar ni estimar valores. Si falta un año, se deja fuera.

## Sincronizar con la narración (ElevenLabs)

- El script reparte el tiempo por igual: cada barra o punto aparece cada `duracion_animacion / n` segundos.
- Si la narración ya está hecha, mide su duración con `ffprobe -v error -show_entries format=duration -of csv=p=0 voz.mp3` y ajusta `duracion_animacion` para que la última barra aparezca cuando el narrador diga la cifra final.
- Para unir la voz y el video directamente con ffmpeg:

```bash
ffmpeg -i salida/video.mp4 -i voz.mp3 -c:v copy -c:a aac -shortest salida/video_con_voz.mp4
```

- Para añadir música de fondo a bajo volumen:

```bash
ffmpeg -i salida/video_con_voz.mp4 -i musica.mp3 -filter_complex "[1:a]volume=0.12[m];[0:a][m]amix=inputs=2:duration=first[a]" -map 0:v -map "[a]" -c:v copy -c:a aac salida/final.mp4
```

## Flujo de trabajo para Claude Code

1. Recibir el tema del video y buscar los datos en una fuente oficial.
2. Crear `datos/<tema>.json` siguiendo el formato de arriba.
3. Ejecutar `generar_video.py`.
4. Extraer 2 fotogramas (a mitad de la animación y al final) y **revisarlos visualmente**: que no haya textos encimados, que las cifras se lean y que nada caiga fuera de la zona segura.
5. Corregir y volver a generar si hace falta.
6. Si hay narración, ajustar el tiempo y unir el audio.

## Código completo: `generar_video.py`

```python
#!/usr/bin/env python3
"""
Generador de videos verticales (1080x1920) con gráficos estadísticos animados.
Uso:  python3 generar_video.py config.json salida.mp4
Requiere: python3, matplotlib, numpy, ffmpeg.
"""
import json, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.animation import FuncAnimation, FFMpegWriter

# ---------- Estilo por defecto (se puede sobreescribir en el JSON -> "estilo") ----------
ESTILO = {
    "fondo": "#0F1419",
    "texto": "#F5F5F5",
    "texto_suave": "#9AA4AE",
    "acento": "#E8B23A",      # barra/linea destacada
    "barra": "#3A7BD5",       # barras normales
    "rejilla": "#2A323B",
    "fuente": "Inter",
}

FPS = 30
W, H = 1080, 1920
DPI = 120


def ease(t):
    """Ease-out cúbico: arranca rápido y frena suave."""
    t = np.clip(t, 0, 1)
    return 1 - (1 - t) ** 3


def formatear(v, cfg):
    dec = cfg.get("decimales", 0)
    esc = cfg.get("escala", 1)
    txt = f"{v / esc:,.{dec}f}"
    if cfg.get("separador_es", True):  # 10,760,028 -> 10.760.028 ; 1.5 -> 1,5
        txt = txt.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{cfg.get('prefijo', '')}{txt}{cfg.get('sufijo', '')}"


def main(ruta_cfg, ruta_salida):
    cfg = json.load(open(ruta_cfg, encoding="utf-8"))
    est = {**ESTILO, **cfg.get("estilo", {})}
    plt.rcParams["font.family"] = est["fuente"]

    etiquetas = [str(e) for e in cfg["etiquetas"]]
    valores = np.array(cfg["valores"], dtype=float)
    n = len(valores)
    tipo = cfg.get("tipo", "barras")          # "barras" | "linea"
    dur_anim = cfg.get("duracion_animacion", 6.0)
    dur_pausa = cfg.get("pausa_final", 2.5)
    total = int((dur_anim + dur_pausa) * FPS)
    paso = dur_anim / n                         # segundos por elemento

    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=est["fondo"])

    # Textos fijos
    fig.text(0.07, 0.92, cfg.get("titulo", ""), color=est["texto"], fontsize=40,
             fontweight="bold", va="top", wrap=True)
    fig.text(0.07, 0.795, cfg.get("subtitulo", ""), color=est["texto_suave"],
             fontsize=22, va="top")
    fig.text(0.07, 0.165, "Fuente: " + cfg.get("fuente", ""), color=est["texto_suave"],
             fontsize=16)
    contador = fig.text(0.07, 0.755, "", color=est["acento"], fontsize=64,
                        fontweight="bold", va="top")
    etiqueta_contador = fig.text(0.07, 0.685, "", color=est["texto"], fontsize=22, va="top")

    ax = fig.add_axes([0.08, 0.235, 0.78, 0.40])  # zona segura TikTok/Reels
    ax.set_facecolor(est["fondo"])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=est["texto_suave"], labelsize=18, length=0)
    ax.set_yticks([])
    ymax = valores.max() * 1.18
    ax.set_ylim(0, ymax)
    x = np.arange(n)
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas, rotation=0 if n <= 8 else 45)
    ax.axhline(0, color=est["rejilla"], lw=2)

    if tipo == "barras":
        barras = ax.bar(x, np.zeros(n), width=0.68, color=est["barra"])
        textos = [ax.text(i, 0, "", ha="center", va="bottom", color=est["texto"],
                          fontsize=16, fontweight="bold") for i in range(n)]
    else:
        linea, = ax.plot([], [], color=est["acento"], lw=6, solid_capstyle="round")
        punto, = ax.plot([], [], "o", color=est["acento"], ms=18)
        textos = [ax.text(i, 0, "", ha="center", va="bottom", color=est["texto"],
                          fontsize=16, fontweight="bold") for i in range(n)]

    corto = {**cfg, **cfg.get("formato_corto", {})}

    def actualizar(f):
        t = f / FPS
        actual = 0.0
        idx_actual = 0
        if tipo == "barras":
            for i, b in enumerate(barras):
                p = ease((t - i * paso) / (paso * 1.6))
                h = valores[i] * p
                b.set_height(h)
                # La barra que está creciendo ahora va en color de acento
                b.set_color(est["acento"] if i == min(int(t / paso), n - 1) else est["barra"])
                if p > 0.05:
                    textos[i].set_position((i, h + ymax * 0.01))
                    textos[i].set_text(formatear(h, corto))
                if p > 0:
                    actual, idx_actual = h, i
        else:
            prog = min(t / dur_anim, 1) * (n - 1)
            k = int(np.floor(prog))
            fr = prog - k
            xs = list(x[:k + 1]); ys = list(valores[:k + 1])
            if k < n - 1:
                xs.append(k + fr); ys.append(valores[k] + (valores[k + 1] - valores[k]) * fr)
            linea.set_data(xs, ys)
            punto.set_data([xs[-1]], [ys[-1]])
            for i in range(n):
                if i <= prog + 1e-6:
                    textos[i].set_position((i - 0.15, valores[i] + ymax * 0.06))
                    textos[i].set_text(formatear(valores[i], corto))
            actual, idx_actual = ys[-1], min(k, n - 1)
        contador.set_text(formatear(actual, cfg))
        etiqueta_contador.set_text(f"{cfg.get('etiqueta_contador', '')} {etiquetas[idx_actual]}".strip())
        return []

    anim = FuncAnimation(fig, actualizar, frames=total, blit=False)
    writer = FFMpegWriter(fps=FPS, codec="libx264",
                          extra_args=["-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "18"])
    anim.save(ruta_salida, writer=writer, dpi=DPI)
    print("Listo:", ruta_salida)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
```

### Ejemplo con narración sincronizada

Ver `datos/poblacion_rd.json`: cada año entra cuando la voz lo nombra (1950 a 2,2 s, 1981 a 6,4 s, 2002 a 10,5 s, 2022 a 15,1 s); los años que no se mencionan entran en las pausas, y el remate aparece cuando dice "se multiplicó por cinco".

```bash
python3 generar_video.py datos/poblacion_rd.json salida/poblacion_rd_voz.mp4
```

Nota: el bloque de código de arriba es la versión original; `generar_video.py` de esta carpeta ya incluye `audio`, `tiempos` y `remate`.

## Ideas para ampliarlo

- Modo **"carrera de barras"** (bar chart race), por ejemplo provincias por población a lo largo de los censos.
- Modo **comparación** (RD frente a otros países del Caribe) con barras horizontales.
- Gancho inicial de 1 segundo con el número final en grande antes de empezar la animación.
- Procesar por lotes todos los JSON de `datos/` con un solo comando.
