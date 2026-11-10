// Renderiza cuadros sueltos para revisión: node scripts/preview.mjs out_dir 1.5 6.2 ...
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import path from "node:path";
const [outDir, ...times] = process.argv.slice(2);
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const opts = { serveUrl, browserExecutable: "/opt/pw-browsers/chromium" };
const comp = await selectComposition({ ...opts, id: "Peajes" });
for (const s of times) {
  const frame = Math.round(parseFloat(s) * 30);
  await renderStill({ ...opts, composition: comp, frame, output: path.join(outDir, `f_${s}.jpg`), imageFormat: "jpeg", jpegQuality: 70, scale: 0.5 });
  console.log("ok", s);
}
