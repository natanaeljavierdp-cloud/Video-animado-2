import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { C, H, W } from "../theme";

/** Foto de fondo con movimiento lento (Ken Burns), oscurecida y con letterbox sutil. */
export const Backdrop: React.FC<{
  src: string;
  t: number; // segundos desde el inicio de la escena
  dur: number;
  from?: { s: number; x: number; y: number };
  to?: { s: number; x: number; y: number };
  dim?: number; // 0..1
  blur?: number;
  tint?: string;
  focusX?: number; // 0..1 posición horizontal del encuadre
}> = ({ src, t, dur, from = { s: 1.05, x: 0, y: 0 }, to = { s: 1.18, x: -30, y: -20 }, dim = 0.55, blur = 0, tint = C.navy, focusX = 0.5 }) => {
  const p = Math.max(0, Math.min(1, t / dur));
  const s = from.s + (to.s - from.s) * p;
  const x = from.x + (to.x - from.x) * p;
  const y = from.y + (to.y - from.y) * p;
  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: C.navyDeep }}>
      <Img
        src={staticFile(src)}
        style={{
          position: "absolute",
          height: H,
          width: "auto",
          left: "50%",
          top: 0,
          transform: `translateX(-${focusX * 100}%) translate(${x}px, ${y}px) scale(${s})`,
          transformOrigin: `${focusX * 100}% 50%`,
          filter: `blur(${blur}px) saturate(1.05) contrast(1.08)`,
        }}
      />
      {/* Tinte de marca */}
      <AbsoluteFill style={{ background: tint, opacity: dim * 0.55, mixBlendMode: "multiply" }} />
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, rgba(6,20,42,${0.82 * dim + 0.2}) 0%, rgba(6,20,42,${0.35 * dim}) 30%, rgba(6,20,42,${0.45 * dim}) 62%, rgba(6,20,42,${0.9 * dim + 0.1}) 100%)`,
        }}
      />
      <Letterbox />
    </AbsoluteFill>
  );
};

export const Letterbox: React.FC = () => (
  <>
    <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: 64, background: "linear-gradient(#000, rgba(0,0,0,0.85))" }} />
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 64, background: "linear-gradient(rgba(0,0,0,0.85), #000)" }} />
  </>
);

/** Fondo gráfico (sin foto) azul marino con rejilla sutil. */
export const NavyField: React.FC<{ t: number; grid?: boolean }> = ({ t, grid = true }) => (
  <AbsoluteFill style={{ background: `radial-gradient(120% 80% at 50% 45%, ${C.navyLight} 0%, ${C.navy} 45%, ${C.navyDeep} 100%)` }}>
    {grid && (
      <AbsoluteFill
        style={{
          opacity: 0.18,
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.25) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.25) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
          backgroundPosition: `0 ${(t * 12) % 60}px`,
        }}
      />
    )}
    <Letterbox />
  </AbsoluteFill>
);

/** Viñeta + grano fino, siempre encima. */
export const FilmLook: React.FC<{ frame: number }> = ({ frame }) => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <AbsoluteFill style={{ background: "radial-gradient(ellipse 85% 70% at 50% 50%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)" }} />
    <Img
      src={staticFile(`grain/g${Math.floor(frame / 2) % 6}.png`)}
      style={{ position: "absolute", inset: 0, width: W, height: H, opacity: 0.075, mixBlendMode: "overlay" }}
    />
  </AbsoluteFill>
);
