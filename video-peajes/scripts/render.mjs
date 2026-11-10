// Render por partes (se pueden reanudar) + pista de audio completa; luego scripts/finalizar.sh las une.
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";
const CHUNK = 240;
fs.mkdirSync("out/partes", { recursive: true });
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const opts = { serveUrl, browserExecutable: "/opt/pw-browsers/chromium", timeoutInMilliseconds: 120000 };
const composition = await selectComposition({ ...opts, id: "Peajes" });
const n = composition.durationInFrames;
if (!fs.existsSync("out/audio.wav")) {
  await renderMedia({ ...opts, composition, codec: "wav", outputLocation: "out/audio.wav.tmp.wav" });
  fs.renameSync("out/audio.wav.tmp.wav", "out/audio.wav");
  console.log("audio listo");
}
for (let s = 0, i = 0; s < n; s += CHUNK, i++) {
  const file = `out/partes/parte-${String(i).padStart(2, "0")}.mp4`;
  if (fs.existsSync(file)) continue;
  await renderMedia({ ...opts, composition, codec: "h264", crf: 18, concurrency: 4, muted: true, frameRange: [s, Math.min(n, s + CHUNK) - 1], outputLocation: file + ".tmp.mp4" });
  fs.renameSync(file + ".tmp.mp4", file);
  console.log(`parte ${i} lista (${Math.min(n, s + CHUNK)}/${n})`);
}
console.log("listo");
