# Curious Capital — "Officials moving onto military bases" (1080x1920, 69.6 s)

- `curious_capital_bases.mp4` — final video.
- `render.html` — all motion graphics (canvas), timed to the narration word timestamps in `data.js`.
- `audio.py` — synthesizes suspense music + SFX and mixes them under `narration.mp3`.
- `render.cjs` — renders frames with headless Chromium and encodes with ffmpeg.

Re-render (e.g. after adding `imagenes/fortmyer.jpg`):
    python3 audio.py && node render.cjs video 4
    ffmpeg -y -i build/video_noaudio.mp4 -i build/mix.wav -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart curious_capital_bases.mp4
