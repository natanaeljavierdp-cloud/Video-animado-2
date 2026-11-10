# Capital Curioso — "¿SE ACABÓ EL DINERO DE EE.UU. PARA ISRAEL?"

Video vertical 9:16 (1080×1920, 30 fps, 79,8 s) formato INVESTIGACIÓN para @capitalcuriosoo.

**Video final:** `salida/capital_curioso_israel.mp4` (H.264 + AAC, audio normalizado a −14 LUFS).

## Cómo se hizo
- `timeline.py` — tiempos de cada escena, golpes de sonido, transiciones con lupa y tramos sin subtítulos,
  sincronizados con la transcripción por palabra de la narración (`assets/audio/transcripcion.json`).
- `render.py` — dibuja cada cuadro con PIL (Ken Burns en todas las fotos, textos palabra por palabra,
  contadores, sellos, hilos rojos, mapa, relojes, encuesta) y lo codifica con ffmpeg.
- `audio.py` — música de suspenso sintetizada (dron, cuerdas oscuras, latido, tic-tac), "boom" en cada dato,
  whoosh en los cortes y ticks en los contadores; la música va a ~20 % bajo la voz con ducking.

## Volver a generar
```bash
pip install pillow numpy pyshp
python3 render.py                     # video completo
python3 render.py --preview 12.5 40   # PNG de cuadros sueltos para revisar
```
Requiere ffmpeg. Fuentes: Anton, Poppins y Special Elite (Google Fonts, OFL). Mapa: Natural Earth (dominio público).

## Notas
- La narración dura 76,3 s (no 65 s), así que el video sigue al audio + 3,5 s del cierre animado.
- La foto `assets/img/lider_opositor.jpg` se usa como Yair Golan (asignación según el orden en que se
  subieron las imágenes). Si es otra persona, cambia el nombre en `sc_golan` / `sc_cita_golan`.
- Fuentes citadas en pantalla: Fox News, AFP/CNN, AP, Atlantic Council, CBS.
