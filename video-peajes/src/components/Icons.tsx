import React from "react";
import { C, F } from "../theme";

/* Íconos e ilustraciones vectoriales originales (sin IA). */

/** Placa dominicana (vehículo privado). */
export const PlateRD: React.FC<{ w?: number; code?: string; style?: React.CSSProperties }> = ({ w = 300, code = "A485921", style }) => (
  <svg width={w} height={w * 0.5} viewBox="0 0 300 150" style={style}>
    <defs>
      <linearGradient id="plateg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#ffffff" />
        <stop offset="1" stopColor="#dfe6ee" />
      </linearGradient>
    </defs>
    <rect x="3" y="3" width="294" height="144" rx="14" fill="url(#plateg)" stroke="#1b2b44" strokeWidth="5" />
    <rect x="8" y="8" width="284" height="32" rx="8" fill={C.rdBlue} />
    <text x="150" y="31" textAnchor="middle" fontFamily="Inter" fontWeight={800} fontSize="19" fill="#fff" letterSpacing="2">
      REPÚBLICA DOMINICANA
    </text>
    <text x="150" y="118" textAnchor="middle" fontFamily="'Bebas Neue'" fontSize="84" fill="#0d1b2e" letterSpacing="6">
      {code}
    </text>
    <rect x="20" y="128" width="40" height="10" fill={C.rdRed} rx="2" />
    <rect x="240" y="128" width="40" height="10" fill={C.rdBlue} rx="2" />
  </svg>
);

/** Carro visto de atrás (con placa dominicana). */
export const CarRear: React.FC<{ w?: number; color?: string; brake?: number }> = ({ w = 420, color = "#D9DFE7", brake = 0 }) => (
  <svg width={w} height={w * 0.78} viewBox="0 0 400 312" style={{ overflow: "visible" }}>
    <defs>
      <linearGradient id="body" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#ffffff" />
        <stop offset="0.45" stopColor={color} />
        <stop offset="1" stopColor="#7f8a99" />
      </linearGradient>
      <linearGradient id="glass" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#3b5277" />
        <stop offset="1" stopColor="#0b1626" />
      </linearGradient>
    </defs>
    <ellipse cx="200" cy="296" rx="200" ry="20" fill="rgba(0,0,0,0.55)" />
    <rect x="34" y="228" width="66" height="70" rx="16" fill="#111" />
    <rect x="300" y="228" width="66" height="70" rx="16" fill="#111" />
    {/* techo / cabina */}
    <path d="M92 40 Q100 22 124 20 L276 20 Q300 22 308 40 L346 128 L54 128 Z" fill="url(#body)" />
    <path d="M110 46 Q115 34 132 33 L268 33 Q285 34 290 46 L318 118 L82 118 Z" fill="url(#glass)" />
    <path d="M140 40 L190 40 L150 112 L112 112 Z" fill="rgba(255,255,255,0.1)" />
    {/* carrocería */}
    <path d="M18 150 Q20 126 54 124 L346 124 Q380 126 382 150 L386 236 Q386 254 366 256 L34 256 Q14 254 14 236 Z" fill="url(#body)" />
    <rect x="14" y="236" width="372" height="22" rx="10" fill="#2a3240" />
    {/* luces traseras */}
    <path d="M26 146 L112 146 L104 184 L28 184 Z" fill={brake > 0 ? "#ff2a2a" : "#b3121b"} />
    <path d="M374 146 L288 146 L296 184 L372 184 Z" fill={brake > 0 ? "#ff2a2a" : "#b3121b"} />
    {brake > 0 && (
      <>
        <ellipse cx="66" cy="165" rx="70" ry="34" fill="rgba(255,40,40,0.35)" opacity={brake} />
        <ellipse cx="334" cy="165" rx="70" ry="34" fill="rgba(255,40,40,0.35)" opacity={brake} />
      </>
    )}
    <rect x="120" y="150" width="160" height="12" rx="6" fill="rgba(0,0,0,0.18)" />
    {/* placa */}
    <g transform="translate(140 176)">
      <rect width="120" height="60" rx="7" fill="#fff" stroke="#1b2b44" strokeWidth="3" />
      <rect x="3" y="3" width="114" height="13" rx="3" fill={C.rdBlue} />
      <text x="60" y="13" textAnchor="middle" fontFamily="Inter" fontWeight={800} fontSize="8" fill="#fff" letterSpacing="0.8">
        REPÚBLICA DOMINICANA
      </text>
      <text x="60" y="50" textAnchor="middle" fontFamily="'Bebas Neue'" fontSize="34" fill="#0d1b2e" letterSpacing="2">
        A485921
      </text>
    </g>
  </svg>
);

/** Marbete dominicano estilizado. */
export const Marbete: React.FC<{ w?: number; year?: string }> = ({ w = 420, year = "2026" }) => {
  // patrón tipo código QR (determinístico)
  const cells: React.ReactNode[] = [];
  let seed = 7;
  for (let y = 0; y < 9; y++)
    for (let x = 0; x < 9; x++) {
      seed = (seed * 9301 + 49297) % 233280;
      const corner = (x < 3 && y < 3) || (x > 5 && y < 3) || (x < 3 && y > 5);
      if (corner ? !(x % 6 === 1 && y % 6 === 1) : seed / 233280 > 0.5)
        cells.push(<rect key={`${x}-${y}`} x={x * 10} y={y * 10} width="10" height="10" fill="#0b1f3a" />);
    }
  return (
    <svg width={w} height={w * 0.66} viewBox="0 0 420 277">
      <defs>
        <linearGradient id="mbg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#fff6d6" />
          <stop offset="0.5" stopColor="#ffe38a" />
          <stop offset="1" stopColor="#f6c94a" />
        </linearGradient>
        <pattern id="guil" width="16" height="16" patternUnits="userSpaceOnUse">
          <circle cx="8" cy="8" r="6" fill="none" stroke="rgba(11,31,58,0.10)" strokeWidth="1.5" />
        </pattern>
      </defs>
      <rect x="4" y="4" width="412" height="269" rx="26" fill="url(#mbg)" stroke="#0b1f3a" strokeWidth="6" />
      <rect x="4" y="4" width="412" height="269" rx="26" fill="url(#guil)" />
      <rect x="4" y="4" width="412" height="62" rx="26" fill={C.navy} />
      <rect x="4" y="40" width="412" height="26" fill={C.navy} />
      <text x="28" y="47" fontFamily="Montserrat" fontWeight={900} fontSize="32" fill="#fff" letterSpacing="3">
        MARBETE
      </text>
      <g transform="translate(330 18)">
        <rect width="60" height="36" fill="#fff" rx="3" />
        <rect width="26" height="14" fill={C.rdBlue} />
        <rect x="34" width="26" height="14" fill={C.rdRed} />
        <rect y="22" width="26" height="14" fill={C.rdRed} />
        <rect x="34" y="22" width="26" height="14" fill={C.rdBlue} />
      </g>
      <text x="28" y="168" fontFamily="'Bebas Neue'" fontSize="118" fill={C.navy} letterSpacing="4">
        {year}
      </text>
      <text x="30" y="206" fontFamily="Inter" fontWeight={700} fontSize="21" fill={C.navy}>
        Impuesto de Circulación
      </text>
      <text x="30" y="242" fontFamily="Inter" fontWeight={800} fontSize="22" fill={C.red} letterSpacing="2">
        DGII · N° 0458921
      </text>
      <g transform="translate(300 96)">
        <rect x="-8" y="-8" width="106" height="106" fill="#fff" rx="6" />
        {cells}
      </g>
    </svg>
  );
};

/** Candado: `closed` 0→1 baja el arco. */
export const Padlock: React.FC<{ w?: number; closed?: number; color?: string }> = ({ w = 200, closed = 1, color = C.red }) => (
  <svg width={w} height={w * 1.2} viewBox="0 0 200 240" style={{ overflow: "visible" }}>
    <path
      d="M50 112 L50 70 Q50 18 100 18 Q150 18 150 70 L150 112"
      fill="none"
      stroke="#cfd6df"
      strokeWidth="26"
      strokeLinecap="round"
      transform={`translate(0 ${-(1 - closed) * 46})`}
    />
    <rect x="18" y="100" width="164" height="132" rx="26" fill={color} stroke="#7e0d0d" strokeWidth="4" />
    <rect x="18" y="100" width="164" height="30" rx="14" fill="rgba(255,255,255,0.18)" />
    <circle cx="100" cy="158" r="17" fill="#3d0606" />
    <rect x="92" y="164" width="16" height="36" rx="6" fill="#3d0606" />
  </svg>
);

/** Calendario con fecha. */
export const CalendarIcon: React.FC<{ w?: number; month?: string; day?: string; flip?: number }> = ({ w = 240, month = "NOV", day = "4", flip = 1 }) => (
  <svg width={w} height={w * 1.08} viewBox="0 0 240 260" style={{ overflow: "visible" }}>
    <rect x="10" y="26" width="220" height="226" rx="26" fill="#fff" />
    <rect x="10" y="26" width="220" height="70" rx="26" fill={C.red} />
    <rect x="10" y="66" width="220" height="30" fill={C.red} />
    <rect x="58" y="6" width="18" height="44" rx="9" fill={C.navy} />
    <rect x="164" y="6" width="18" height="44" rx="9" fill={C.navy} />
    <text x="120" y="80" textAnchor="middle" fontFamily="Montserrat" fontWeight={900} fontSize="40" fill="#fff" letterSpacing="4">
      {month}
    </text>
    <g transform={`translate(120 176) scale(1 ${flip}) translate(-120 -176)`}>
      <text x="120" y="222" textAnchor="middle" fontFamily="'Bebas Neue'" fontSize="150" fill={C.navy}>
        {day}
      </text>
    </g>
  </svg>
);

/** Documento oficial (proyecto de ley). */
export const DocumentIcon: React.FC<{ w?: number }> = ({ w = 220 }) => (
  <svg width={w} height={w * 1.3} viewBox="0 0 220 286">
    <path d="M12 12 L160 12 L208 60 L208 274 L12 274 Z" fill="#fbfaf6" stroke="#c9ced6" strokeWidth="3" />
    <path d="M160 12 L160 60 L208 60" fill="#e4e7ec" />
    <circle cx="110" cy="62" r="26" fill="none" stroke={C.navy} strokeWidth="5" />
    <path d="M110 44 L110 80 M92 62 L128 62" stroke={C.red} strokeWidth="5" />
    <text x="110" y="118" textAnchor="middle" fontFamily="Montserrat" fontWeight={900} fontSize="17" fill={C.navy}>
      PROYECTO DE LEY
    </text>
    {[140, 160, 180, 200, 220, 240].map((y, i) => (
      <rect key={y} x="34" y={y} width={i % 3 === 2 ? 100 : 152} height="8" rx="4" fill="#c6ccd6" />
    ))}
  </svg>
);

/** Moneda RD$. */
export const Coin: React.FC<{ w?: number; label?: string }> = ({ w = 200, label = "100" }) => (
  <svg width={w} height={w} viewBox="0 0 200 200" style={{ overflow: "visible" }}>
    <defs>
      <radialGradient id="coing" cx="35%" cy="30%" r="80%">
        <stop offset="0" stopColor="#fff3b8" />
        <stop offset="0.45" stopColor="#f4c542" />
        <stop offset="1" stopColor="#b5841a" />
      </radialGradient>
    </defs>
    <circle cx="100" cy="104" r="94" fill="#8a6211" />
    <circle cx="100" cy="96" r="94" fill="url(#coing)" />
    <circle cx="100" cy="96" r="76" fill="none" stroke="#b5841a" strokeWidth="5" strokeDasharray="5 7" />
    <text x="100" y="84" textAnchor="middle" fontFamily="Montserrat" fontWeight={900} fontSize="30" fill="#7a540c">
      RD$
    </text>
    <text x="100" y="138" textAnchor="middle" fontFamily="'Bebas Neue'" fontSize="68" fill="#5e3f05">
      {label}
    </text>
  </svg>
);

/** Billete RD$ estilizado. */
export const Bill: React.FC<{ w?: number }> = ({ w = 160 }) => (
  <svg width={w} height={w * 0.5} viewBox="0 0 160 80">
    <rect x="2" y="2" width="156" height="76" rx="8" fill="#8fd19e" stroke="#2c6e3f" strokeWidth="3" />
    <circle cx="80" cy="40" r="22" fill="none" stroke="#2c6e3f" strokeWidth="3" />
    <text x="80" y="49" textAnchor="middle" fontFamily="'Bebas Neue'" fontSize="26" fill="#1f5230">
      RD$
    </text>
    <text x="16" y="24" fontFamily="'Bebas Neue'" fontSize="18" fill="#1f5230">
      1000
    </text>
  </svg>
);

/** Alcancía. */
export const Piggy: React.FC<{ w?: number }> = ({ w = 360 }) => (
  <svg width={w} height={w * 0.8} viewBox="0 0 360 288" style={{ overflow: "visible" }}>
    <ellipse cx="180" cy="276" rx="150" ry="12" fill="rgba(0,0,0,0.4)" />
    <rect x="80" y="210" width="44" height="66" rx="14" fill="#a91c1c" />
    <rect x="236" y="210" width="44" height="66" rx="14" fill="#a91c1c" />
    <ellipse cx="180" cy="160" rx="150" ry="112" fill={C.red} />
    <ellipse cx="150" cy="120" rx="80" ry="44" fill="rgba(255,255,255,0.14)" />
    <path d="M110 70 L96 22 L150 54 Z" fill="#a91c1c" />
    <ellipse cx="318" cy="168" rx="34" ry="40" fill="#e24848" stroke="#a91c1c" strokeWidth="5" />
    <circle cx="312" cy="158" r="6" fill="#6b0f0f" />
    <circle cx="324" cy="178" r="6" fill="#6b0f0f" />
    <circle cx="262" cy="118" r="10" fill="#1a0505" />
    <rect x="140" y="52" width="90" height="16" rx="8" fill="#5c0b0b" />
    <path d="M30 150 Q6 140 14 118" fill="none" stroke="#a91c1c" strokeWidth="9" strokeLinecap="round" />
    <text x="170" y="200" textAnchor="middle" fontFamily="Montserrat" fontWeight={900} fontSize="44" fill="rgba(255,255,255,0.9)">
      RD$
    </text>
  </svg>
);

/** Mazo de juez. */
export const Gavel: React.FC<{ w?: number }> = ({ w = 260 }) => (
  <svg width={w} height={w} viewBox="0 0 260 260" style={{ overflow: "visible" }}>
    <g transform="rotate(-40 130 130)">
      <rect x="122" y="96" width="16" height="170" rx="8" fill="#8b5a2b" />
      <rect x="62" y="40" width="136" height="70" rx="18" fill="#a86a32" />
      <rect x="52" y="36" width="22" height="78" rx="8" fill="#d4a55a" />
      <rect x="186" y="36" width="22" height="78" rx="8" fill="#d4a55a" />
    </g>
  </svg>
);

/** Sello rojo "BLOQUEADO". */
export const Stamp: React.FC<{ text?: string; w?: number }> = ({ text = "BLOQUEADO", w = 560 }) => (
  <svg width={w} height={w * 0.3} viewBox="0 0 560 168">
    <defs>
      <filter id="rough" x="-10%" y="-20%" width="120%" height="140%">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4" />
        <feDisplacementMap in="SourceGraphic" scale="5" />
      </filter>
    </defs>
    <g filter="url(#rough)">
      <rect x="8" y="8" width="544" height="152" rx="18" fill="rgba(214,40,40,0.12)" stroke={C.red} strokeWidth="12" />
      <rect x="26" y="26" width="508" height="116" rx="10" fill="none" stroke={C.red} strokeWidth="4" />
      <text x="280" y="122" textAnchor="middle" fontFamily="Montserrat" fontWeight={900} fontSize="76" fill={C.red} letterSpacing="2">
        {text}
      </text>
    </g>
  </svg>
);

/** Sticker de telepeaje en parabrisas con ondas. */
export const TeleSticker: React.FC<{ w?: number; wave?: number }> = ({ w = 380, wave = 0 }) => (
  <svg width={w} height={w * 0.8} viewBox="0 0 380 304" style={{ overflow: "visible" }}>
    {/* parabrisas */}
    <path d="M30 290 L80 70 Q86 46 112 44 L268 44 Q294 46 300 70 L350 290 Z" fill="#1d3557" stroke="#c9d3df" strokeWidth="8" />
    <path d="M70 280 L110 90 L170 90 L120 280 Z" fill="rgba(255,255,255,0.07)" />
    {/* espejo */}
    <rect x="170" y="44" width="40" height="30" rx="6" fill="#0d1b2e" />
    {/* sticker */}
    <g transform="translate(232 76)">
      <rect width="58" height="44" rx="8" fill="#fff" stroke={C.red} strokeWidth="4" />
      <rect x="6" y="6" width="22" height="16" rx="3" fill={C.navy} />
      <text x="29" y="38" textAnchor="middle" fontFamily="Montserrat" fontWeight={900} fontSize="11" fill={C.red}>
        PASO
      </text>
    </g>
    {/* ondas */}
    {[0, 1, 2].map((i) => {
      const p = (wave + i / 3) % 1;
      return (
        <path
          key={i}
          d={`M${261 - 30 - p * 90} ${80 - 10 - p * 40} Q261 ${40 - p * 90} ${261 + 30 + p * 90} ${80 - 10 - p * 40}`}
          fill="none"
          stroke={C.white}
          strokeWidth="7"
          strokeLinecap="round"
          opacity={(1 - p) * (wave > 0 ? 1 : 0)}
        />
      );
    })}
  </svg>
);

/** Caseta de peaje con barrera (ángulo en grados: 0 = cerrada, 80 = abierta). */
export const TollBooth: React.FC<{ w?: number; angle?: number }> = ({ w = 500, angle = 0 }) => (
  <svg width={w} height={w * 1.1} viewBox="0 0 500 550" style={{ overflow: "visible" }}>
    {/* barrera */}
    <g transform={`rotate(${angle} 330 390)`}>
      <rect x="-330" y="378" width="660" height="26" rx="13" fill="#fff" stroke="#222" strokeWidth="3" />
      {Array.from({ length: 8 }).map((_, i) => (
        <rect key={i} x={-310 + i * 80} y="378" width="40" height="26" fill={C.red} />
      ))}
      <circle cx="-320" cy="391" r="10" fill="#ff4d4d" />
    </g>
    {/* poste de barrera */}
    <rect x="312" y="370" width="60" height="170" rx="10" fill="#e9edf2" stroke="#9aa7b8" strokeWidth="3" />
    <rect x="312" y="400" width="60" height="18" fill={C.red} />
    <circle cx="330" cy="390" r="14" fill="#333" />
    {/* caseta */}
    <rect x="380" y="150" width="200" height="390" rx="12" fill="#f0f3f7" stroke="#9aa7b8" strokeWidth="4" />
    <rect x="400" y="200" width="160" height="140" rx="8" fill="#203a5e" />
    <path d="M400 200 L470 200 L420 340 L400 340 Z" fill="rgba(255,255,255,0.12)" />
    <rect x="360" y="110" width="240" height="52" rx="8" fill={C.navy} />
    <text x="480" y="148" textAnchor="middle" fontFamily="Montserrat" fontWeight={900} fontSize="36" fill="#fff" letterSpacing="4">
      PEAJE
    </text>
    {/* semáforo */}
    <rect x="392" y="360" width="44" height="90" rx="10" fill="#1a1a1a" />
    <circle cx="414" cy="384" r="13" fill={angle > 40 ? "#3a0a0a" : "#ff2a2a"} />
    <circle cx="414" cy="426" r="13" fill={angle > 40 ? "#2bd673" : "#0a2a17"} />
  </svg>
);

/** Explosión de partículas (0→1). */
export const Burst: React.FC<{ p: number; r?: number; color?: string; n?: number }> = ({ p, r = 160, color = C.red, n = 14 }) => {
  if (p <= 0 || p >= 1) return null;
  return (
    <svg width={r * 2.4} height={r * 2.4} viewBox={`${-r * 1.2} ${-r * 1.2} ${r * 2.4} ${r * 2.4}`} style={{ position: "absolute", left: -r * 1.2, top: -r * 1.2, overflow: "visible" }}>
      <circle r={r * p} fill="none" stroke={color} strokeWidth={14 * (1 - p)} opacity={1 - p} />
      {Array.from({ length: n }).map((_, i) => {
        const a = (i / n) * Math.PI * 2;
        const d0 = r * 0.35 + r * 0.8 * p;
        const d1 = d0 + 40 * (1 - p);
        return (
          <line
            key={i}
            x1={Math.cos(a) * d0}
            y1={Math.sin(a) * d0}
            x2={Math.cos(a) * d1}
            y2={Math.sin(a) * d1}
            stroke={i % 2 ? color : "#fff"}
            strokeWidth={10 * (1 - p) + 2}
            strokeLinecap="round"
          />
        );
      })}
    </svg>
  );
};

export const Check: React.FC<{ w?: number; p?: number }> = ({ w = 60, p = 1 }) => (
  <svg width={w} height={w} viewBox="0 0 60 60">
    <circle cx="30" cy="30" r="28" fill={C.green} />
    <path d="M16 31 L26 41 L45 20" fill="none" stroke="#fff" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="50" strokeDashoffset={50 * (1 - p)} />
  </svg>
);

export const fontTitle = F.title;
