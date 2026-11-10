import { continueRender, delayRender, staticFile } from "remotion";
const faces: [string, string, string][] = [
  ["Montserrat", "montserrat-latin-700-normal.woff2", "700"],
  ["Montserrat", "montserrat-latin-800-normal.woff2", "800"],
  ["Montserrat", "montserrat-latin-900-normal.woff2", "900"],
  ["Inter", "inter-latin-400-normal.woff2", "400"],
  ["Inter", "inter-latin-500-normal.woff2", "500"],
  ["Inter", "inter-latin-600-normal.woff2", "600"],
  ["Inter", "inter-latin-700-normal.woff2", "700"],
  ["Inter", "inter-latin-800-normal.woff2", "800"],
  ["Bebas Neue", "bebas-neue-latin-400-normal.woff2", "400"],
];
let started = false;
export const loadFonts = () => {
  if (started || typeof document === "undefined") return;
  started = true;
  const handle = delayRender("Cargando fuentes", { timeoutInMilliseconds: 120000, retries: 2 });
  Promise.all(
    faces.map(([family, file, weight]) =>
      new FontFace(family, `url(${staticFile("fonts/" + file)}) format('woff2')`, { weight })
        .load()
        .then((f) => document.fonts.add(f)),
    ),
  )
    .then(() => continueRender(handle))
    .catch((e) => {
      console.error(e);
      continueRender(handle);
    });
};
