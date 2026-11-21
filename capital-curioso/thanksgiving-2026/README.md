# Capital Curioso — "Tu cena de Thanksgiving subió" (vertical 9:16)

Video de 1080x1920 a 30 fps generado por código con `render.py`, usando la narración y las fotos entregadas.

```bash
pip install pillow numpy          # ffmpeg debe estar instalado
python3 render.py                 # → build/capital_curioso_thanksgiving.mp4
python3 render.py --stills 14.8 30.5   # cuadros de prueba en build/stills/
```

## Sincronía
`assets/transcripcion_palabras.json` tiene los tiempos por palabra de la narración (Whisper `medium`).
Corrección manual: Whisper omitió la palabra **"caro."** (24.56–25.14 s), confirmada con una segunda pasada.

| Escena | Tiempo | Fondo |
|---|---|---|
| 1. Gancho | 0–5.6 s | 01_familia_cocina |
| 2. El costo | 5.6–22.3 s | 09_ilustracion_mesa |
| 3. El pavo | 22.3–31.3 s | 07_pavo_buffet (desenfocado) + 08_pavo_horneado al centro |
| 4. El culpable | 31.3–44.8 s | 05_mangueras → 04_gasolinera → 06_camion_cisterna |
| 5. La salida | 44.8–57.0 s | 03_mercado |
| 6. Cierre | 57.0–64.5 s | 02_padre_hijo_mesa |
| Marca | 64.5–68.0 s | cierre animado de Capital Curioso |

Cifras en pantalla: $58.63 · +6% · 2022 · $21.50 · $23.68 · $6.53 · $39 (y "Ahorras $19.63" = 58.63 − 39).
Las curvas del precio de la cena y del diésel son ilustrativas (sin valores intermedios inventados).

## Créditos
- Música: "Wallpaper" — Kevin MacLeod (incompetech.com). Licencia Creative Commons: By Attribution 4.0
  (http://creativecommons.org/licenses/by/4.0/). **Incluir este crédito en la descripción del video.**
- Efectos de sonido (pop, caja registradora, whoosh): sintetizados en `render.py`.
- Tipografía: Poppins (SIL Open Font License). Emojis: Noto Color Emoji.
- Mapa: contornos de `world.geo.json` (dominio público, Natural Earth).
