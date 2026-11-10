# Video «Peajes sin casetas» — Capital Curioso (@capitalcuriosoo)

Video vertical 1080×1920, 30 fps, H.264, ~1:04 (narración de 59.7 s + cierre de marca), hecho con **React + Remotion**.

## Entregables (carpeta `entrega/`)

| Archivo | Qué es |
|---|---|
| `peajes-sin-casetas.mp4` | Video final con voz, música (≈ -20 dB bajo la voz) y efectos, normalizado a -14 LUFS para redes |
| `miniatura-peajes.png` | Portada 1080×1920: «¿Peajes SIN casetas? 🚗💸» + x5 en rojo |
| `../CREDITOS.md` | Fotos, música y fuentes de datos con enlaces + texto de atribución para la descripción |

## Cómo está hecho

- **Subtítulos palabra por palabra** arriba: la narración se transcribió con Whisper (`scripts/transcribe.py`, modelo *medium*) → `src/data/words.json`. La palabra que suena se pinta en rojo.
- **Escenas** (`src/scenes/`), con tiempos reales de la voz en `src/timeline.ts`:
  1. Gancho: barrera que se levanta sola, carro en cámara lenta, **x5**, marbete con candado.
  2. Proyecto: Poder Ejecutivo → Senado, tarjeta con calendario «4 de noviembre de 2026».
  3. Free Flow: pórtico, haz de escaneo, «Placa leída ✓», sticker de telepeaje, «Sin barreras».
  4. Mapa de RD (Natural Earth) con zoom a Santo Domingo, Las Américas en rojo y pin «Prueba piloto».
  5. Multas: moneda RD$100 → 5 monedas, contador RD$100 → RD$500, «Multa mínima: RD$500».
  6. Gráfico de línea RD$60 → RD$100 → RD$500 (explota en rojo) + mini mapa Duarte / Las Américas / 6 de Noviembre.
  7. Marbete con sello «BLOQUEADO» + rótulo DGII.
  8. Contador RD$12,000 millones+, 92.5 millones de pasadas, alcancía, «Control más estricto».
  9. Recorte de Revista Mercado + mazo «Pendiente de aprobación».
  10. Encuesta animada y «¿Tú qué opinas? Comenta 👇».
  11. Cierre de marca (el `capital_curioso_cierre.mp4` que enviaste).
- Look cinematográfico: Ken Burns sobre fotos reales de RD, letterbox sutil, viñeta, grano, transiciones wipe / zoom-through / máscara circular.

## Volver a generar (solo si quieres cambiar algo)

```bash
npm install
npm run render     # → out/peajes-sin-casetas.mp4
npm run thumb      # → out/miniatura.png
bash scripts/finalizar.sh   # normaliza el audio y copia a entrega/
```
