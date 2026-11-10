// Render del video con la API de Remotion (sin la barra de progreso de la CLI).
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import path from "node:path";
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const opts = { serveUrl, browserExecutable: "/opt/pw-browsers/chromium", timeoutInMilliseconds: 120000 };
const composition = await selectComposition({ ...opts, id: "Peajes" });
let last = -1;
await renderMedia({
  ...opts, composition, codec: "h264", crf: 18, concurrency: 4,
  outputLocation: "out/render-bruto.mp4",
  onProgress: ({ progress }) => { const p = Math.floor(progress * 20); if (p !== last) { last = p; console.log(`${p * 5}%`); } },
});
console.log("listo");
