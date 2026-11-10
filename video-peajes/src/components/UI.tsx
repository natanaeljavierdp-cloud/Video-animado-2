import React from "react";
import { C, F } from "../theme";

/** Panel tipo "vidrio" azul marino con borde. */
export const Panel: React.FC<{ style?: React.CSSProperties; children: React.ReactNode; accent?: string }> = ({ style, children, accent = C.red }) => (
  <div
    style={{
      position: "absolute",
      background: "linear-gradient(160deg, rgba(22,51,92,0.92), rgba(8,24,48,0.94))",
      border: "2px solid rgba(255,255,255,0.14)",
      borderRadius: 34,
      boxShadow: "0 30px 80px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.12)",
      overflow: "hidden",
      ...style,
    }}
  >
    <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 10, background: accent }} />
    {children}
  </div>
);

/** Etiqueta pequeña (chip). */
export const Chip: React.FC<{ children: React.ReactNode; bg?: string; color?: string; style?: React.CSSProperties; size?: number }> = ({
  children,
  bg = C.red,
  color = C.white,
  style,
  size = 40,
}) => (
  <div
    style={{
      position: "absolute",
      background: bg,
      color,
      fontFamily: F.title,
      fontWeight: 800,
      fontSize: size,
      letterSpacing: 1,
      textTransform: "uppercase",
      padding: `${size * 0.32}px ${size * 0.62}px`,
      borderRadius: size * 0.35,
      boxShadow: "0 14px 34px rgba(0,0,0,0.45)",
      whiteSpace: "nowrap",
      ...style,
    }}
  >
    {children}
  </div>
);

/** Pequeña bandera dominicana. */
export const FlagRD: React.FC<{ w?: number; style?: React.CSSProperties }> = ({ w = 90, style }) => {
  const h = w * (2 / 3);
  return (
    <svg width={w} height={h} viewBox="0 0 30 20" style={style}>
      <rect width="30" height="20" fill="#fff" />
      <rect x="0" y="0" width="13" height="8" fill={C.rdBlue} />
      <rect x="17" y="0" width="13" height="8" fill={C.rdRed} />
      <rect x="0" y="12" width="13" height="8" fill={C.rdRed} />
      <rect x="17" y="12" width="13" height="8" fill={C.rdBlue} />
      <circle cx="15" cy="10" r="1.6" fill="#2a7d3a" />
    </svg>
  );
};

/** Franja de la bandera (toque de color). */
export const FlagStripe: React.FC<{ style?: React.CSSProperties; w?: number }> = ({ style, w = 160 }) => (
  <div style={{ position: "absolute", display: "flex", height: 8, width: w, borderRadius: 4, overflow: "hidden", ...style }}>
    <div style={{ flex: 1, background: C.rdBlue }} />
    <div style={{ flex: 0.35, background: "#fff" }} />
    <div style={{ flex: 1, background: C.rdRed }} />
  </div>
);

export const Label: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div
    style={{
      position: "absolute",
      fontFamily: F.body,
      fontWeight: 600,
      color: C.gray,
      fontSize: 38,
      lineHeight: 1.25,
      textShadow: "0 3px 12px rgba(0,0,0,0.6)",
      ...style,
    }}
  >
    {children}
  </div>
);
