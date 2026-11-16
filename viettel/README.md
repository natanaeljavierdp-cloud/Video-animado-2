# Video Viettel – Capital Curioso (1080x1920, 78.5 s)

Resultado final: `out/viettel_capitalcurioso.mp4`

Regenerar:
1. `python3 tools/geo_prep.py` (requiere los GeoJSON de Natural Earth en `geo/`)
2. `python3 tools/words_prep.py` (subtítulos desde `tools/words_raw.json`, transcripción con faster-whisper)
3. `node tools/render.cjs out/p1.mp4 0 26.2` (etc.) – renderiza `build/video.html` con Playwright
4. `node tools/render.cjs --cues build/cues.json && python3 tools/audio.py` – música y efectos sintetizados
5. Mezcla con ffmpeg (narración + música con ducking + efectos, loudnorm -14 LUFS).

Escenas y tiempos: `build/scenes.js`.
