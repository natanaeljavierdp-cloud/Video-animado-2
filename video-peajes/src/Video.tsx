import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { FPS } from "./theme";
import { SCENES, TOTAL_SECONDS, TransitionType } from "./timeline";
import { SceneShell } from "./components/SceneShell";
import { FilmLook } from "./components/Cinematic";
import { Subtitles } from "./components/Subtitles";
import { S01Gancho, S02Proyecto, S03Funciona, S04Mapa, S05Multas } from "./scenes/ScenesA";
import { S06Comparacion, S07Marbete, S08Dinero, S09Fuente, S10Encuesta, S11Cierre } from "./scenes/ScenesB";
import { loadFonts } from "./fonts";

loadFonts();

const ORDER: [keyof typeof SCENES, React.FC<{ t: number }>][] = [
  ["gancho", S01Gancho],
  ["proyecto", S02Proyecto],
  ["funciona", S03Funciona],
  ["mapa", S04Mapa],
  ["multas", S05Multas],
  ["comparacion", S06Comparacion],
  ["marbete", S07Marbete],
  ["dinero", S08Dinero],
  ["fuente", S09Fuente],
  ["encuesta", S10Encuesta],
  ["cierre", S11Cierre],
];

// Efectos de sonido (segundo, archivo, volumen)
const SFX: [number, string, number][] = [
  ...ORDER.slice(1).map(([k]) => [SCENES[k].start - 0.12, "whoosh", 0.32] as [number, string, number]),
  [0.5, "whoosh", 0.18],
  [5.74, "impacto", 0.55],
  [8.42, "clic", 0.6],
  [17.85, "ding", 0.35],
  [25.3, "sello", 0.55],
  [26.3, "moneda", 0.35],
  [27.92, "moneda", 0.3],
  [28.05, "moneda", 0.25],
  [30.45, "impacto", 0.5],
  [34.2, "impacto", 0.35],
  [39.6, "sello", 0.6],
  [41.8, "moneda", 0.22],
  [42.7, "moneda", 0.22],
  [43.6, "moneda", 0.22],
  [44.45, "ding", 0.3],
  [47.25, "clic", 0.45],
  [51.85, "sello", 0.3],
  [57.6, "riser", 0.28],
  // tics de los contadores
  ...Array.from({ length: 16 }, (_, i) => [28.4 + i * 0.13, "tic", 0.18] as [number, string, number]),
  ...Array.from({ length: 15 }, (_, i) => [42.4 + i * 0.13, "tic", 0.16] as [number, string, number]),
];

const END = TOTAL_SECONDS;
const NARR_END = 59.75;

export const PeajesVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  return (
    <AbsoluteFill style={{ backgroundColor: "#06142A" }}>
      {ORDER.map(([key, Comp], i) => {
        const sc = SCENES[key];
        const next = ORDER[i + 1] ? SCENES[ORDER[i + 1][0]] : undefined;
        return (
          <SceneShell key={key} t={t} start={sc.start} end={sc.end} enter={sc.enter} exit={next?.enter as TransitionType | undefined}>
            <Comp t={t} />
          </SceneShell>
        );
      })}
      {t < SCENES.cierre.start && <Subtitles t={t} />}
      <FilmLook frame={frame} />

      {/* Audio: narración + música (≈ -20 dB bajo la voz) + efectos */}
      <Audio src={staticFile("media/narracion-peajes.mp3")} />
      <Audio
        src={staticFile("media/musica-investigations.mp3")}
        volume={(f) => {
          const s = f / FPS;
          const base = interpolate(s, [0, 1.2], [0, 0.085], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const outro = interpolate(s, [NARR_END, NARR_END + 0.6], [0, 0.16], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const fadeOut = interpolate(s, [END - 1.6, END], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (base + outro) * fadeOut;
        }}
      />
      {SFX.map(([s, name, vol], i) => (
        <Sequence key={i} from={Math.max(0, Math.round(s * FPS))} durationInFrames={Math.round(2 * FPS)} layout="none">
          <Audio src={staticFile(`sfx/${name}.wav`)} volume={vol} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
