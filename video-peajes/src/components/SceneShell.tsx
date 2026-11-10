import React from "react";
import { AbsoluteFill } from "remotion";
import { C, H, W } from "../theme";
import { TRANSITION, TransitionType } from "../timeline";
import { easeInOut, ramp } from "../anim";

/**
 * Muestra una escena entre [start, end + TRANSITION] y aplica la transición de entrada.
 * La escena siguiente se dibuja encima y "revela" su contenido (wipe, zoom-through o máscara circular).
 */
export const SceneShell: React.FC<{
  t: number;
  start: number;
  end: number;
  enter: TransitionType;
  exit?: TransitionType;
  children: React.ReactNode;
}> = ({ t, start, end, enter, exit, children }) => {
  if (t < start || t > end + TRANSITION) return null;
  const pin = ramp(t, start, start + TRANSITION, easeInOut);
  const pout = ramp(t, end, end + TRANSITION, easeInOut);
  let style: React.CSSProperties = {};
  let overlay: React.ReactNode = null;
  if (enter === "wipe" && pin < 1) {
    const edge = -260 + pin * (W + 520);
    style.clipPath = `polygon(0 0, ${edge + 180}px 0, ${edge - 180}px ${H}px, 0 ${H}px)`;
    overlay = (
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        <polygon points={`${edge + 180},0 ${edge + 236},0 ${edge - 124},${H} ${edge - 180},${H}`} fill={C.red} />
        <polygon points={`${edge + 236},0 ${edge + 250},0 ${edge - 110},${H} ${edge - 124},${H}`} fill="#fff" opacity={0.85} />
      </svg>
    );
  }
  if (enter === "zoom" && pin < 1) {
    style.transform = `scale(${1.25 - 0.25 * pin})`;
    style.opacity = pin;
    style.filter = `blur(${(1 - pin) * 14}px)`;
  }
  if (enter === "iris" && pin < 1) {
    style.clipPath = `circle(${pin * 1150}px at 50% 50%)`;
  }
  // salida tipo zoom-through: la escena saliente se acerca y se desenfoca
  if (exit === "zoom" && pout > 0) {
    style.transform = `scale(${1 + 0.35 * pout})`;
    style.filter = `blur(${pout * 10}px)`;
  }
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ ...style, overflow: "hidden", transformOrigin: "50% 50%" }}>{children}</AbsoluteFill>
      {overlay}
    </AbsoluteFill>
  );
};
