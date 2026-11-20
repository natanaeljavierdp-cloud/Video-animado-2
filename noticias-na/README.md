# Noticias N A — "Sandy Brito" (edición con grafismo de TV)

Edición del video original de la presentadora fresa, **sin regenerar ni alterar la animación ni el audio**. El audio se conserva tal cual, solo con efectos de transición muy suaves (unos 25 dB por debajo de la voz).

## Entregables (`exportaciones/`)
| Archivo | Uso |
|---|---|
| `Noticias_NA_Sandy_Brito_Final.mp4` | Versión principal (grafismo de TV sobre la mesa) |
| `Noticias_NA_Sandy_Brito_Reels_TikTok.mp4` | Igual, pero con los gráficos dentro de las zonas seguras de Instagram Reels, Facebook Reels y TikTok |
| `previews/*.jpg` | Fotogramas de control |

Formato: 1080×1920 (9:16), 24 fps (igual que el original), H.264 High, CRF 16, AAC 256 kb/s 48 kHz estéreo, `faststart`. Duración: 7,92 s (la misma del original).

## Sincronización (desde `transcripcion.json`)
| Tiempo | Audio | Gráfico |
|---|---|---|
| 0,0–0,9 s | "Atención, noticia de última hora" | Logotipo + HUMOR, barra NOTICIAS N A, ÚLTIMA HORA, cintillo |
| 1,76 s | "**Sandy** (1,84) **Brito** (2,10)" | Entra la foto; el rótulo SANDY BRITO aparece con "Brito" |
| 3,94 s | "la **frente** (4,02)…" | El titular cambia a LA FRENTE GANA TERRENO |
| 5,72 s | fin de "economía." | Sale la foto (unos 4 s en pantalla) |
| 6,95–7,92 s | "…la cabeza bien puesta." | Sale el titular y aparece la marca Noticias N A |

## Recursos (`graficos/`)
PNG transparentes (logo, indicador HUMOR, etiqueta ÚLTIMA HORA, titulares, cintillo, recuadro de la foto y rótulo), `overlay_graficos_tv_alpha.webm` (todas las animaciones con canal alfa, para usar en otro editor) y `sfx_transiciones.wav`.

## Volver a generar o editar
```bash
pip install pillow numpy          # ffmpeg debe estar instalado
python3 scripts/render.py         # versión TV y versión Reels
python3 scripts/render.py --solo reels
```
Los textos, los colores, los tiempos (`T_*`), la velocidad del cintillo y las posiciones (`LAYOUTS`) están al principio de `scripts/render.py`.
La foto solo se recorta y se escala: no se retoca.
Fuentes: Oswald y Montserrat (licencia SIL OFL), en `fuentes/`.
