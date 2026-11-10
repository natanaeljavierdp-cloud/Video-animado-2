import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile } from "remotion";
import { C, F, FPS, W } from "../theme";
import { easeInOut, easeOut, lerp, pop, ramp, shake } from "../anim";
import { SCENES } from "../timeline";
import { Backdrop } from "../components/Cinematic";
import { Chip, FlagStripe, Label, Panel } from "../components/UI";
import { Bill, Burst, Coin, Gavel, Marbete, Padlock, Piggy, PlateRD, Stamp } from "../components/Icons";
import mapData from "../data/map.json";

type P = { t: number };
const mapPath = (pts: number[][]) => "M" + pts.map((p) => p.join(" ")).join(" L");

/* ───────────────────────── Escena 6 — Comparación ───────────────────────── */
export const S06Comparacion: React.FC<P> = ({ t }) => {
  const { start, end } = SCENES.comparacion;
  const panel = pop(t, 31.85, { damping: 15 });
  // Gráfico: x en px del panel, y según valor
  const PW = 960, PH = 600;
  const yOf = (v: number) => 500 - (v / 600) * 320;
  const pts = [
    { x: 170, v: 60, label: "RD$60", cap: "Antes de 2025" },
    { x: 480, v: 100, label: "RD$100", cap: "Desde ene. 2025" },
    { x: 800, v: 500, label: "RD$500", cap: "Multa propuesta" },
  ];
  const seg1 = ramp(t, 32.25, 32.95, easeInOut);
  const seg2 = ramp(t, 33.25, 34.2, (x) => x * x);
  const boom = ramp(t, 34.2, 34.9);
  const hl100 = pop(t, 34.5, { damping: 8 });
  const ptIn = [pop(t, 32.1), pop(t, 32.95), pop(t, 34.2, { damping: 8 })];
  const sh = shake(t, 34.22, 12, 0.35);
  const mapIn = pop(t, 32.6, { damping: 15 });
  const hw = [
    { key: "duarte", name: "Autopista Duarte", color: C.red, at: 32.8 },
    { key: "lasAmericas", name: "Las Américas", color: "#fff", at: 33.1 },
    { key: "seisNoviembre", name: "6 de Noviembre", color: C.gold, at: 33.4 },
  ] as const;
  const mk = 330 / mapData.H;
  return (
    <AbsoluteFill style={{ transform: `translate(${sh.x}px, ${sh.y}px)` }}>
      <Backdrop src="media/fotos/tarifas-las-americas.jpg" t={t - start} dur={end - start} dim={0.85} focusX={0.4}
        from={{ s: 1.08, x: 0, y: 0 }} to={{ s: 1.2, x: 30, y: -20 }} />
      <Panel style={{ left: 60, top: 470, width: PW, height: PH, opacity: panel, transform: `translateY(${(1 - panel) * 60}px)` }}>
        <div style={{ position: "absolute", left: 48, top: 30, fontFamily: F.title, fontWeight: 800, fontSize: 36, color: "#fff" }}>
          Peaje para carros <span style={{ color: C.grayMid, fontWeight: 700 }}>(vehículos livianos)</span>
        </div>
        <svg width={PW} height={PH} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
          {[100, 300, 500].map((v) => (
            <g key={v}>
              <line x1="60" x2="920" y1={yOf(v)} y2={yOf(v)} stroke="rgba(255,255,255,0.12)" strokeWidth="2" />
            </g>
          ))}
          <line x1="60" x2="920" y1={yOf(0)} y2={yOf(0)} stroke="rgba(255,255,255,0.5)" strokeWidth="3" />
          <line x1={pts[0].x} y1={yOf(pts[0].v)} x2={lerp(pts[0].x, pts[1].x, seg1)} y2={lerp(yOf(pts[0].v), yOf(pts[1].v), seg1)} stroke="#fff" strokeWidth="9" strokeLinecap="round" />
          {seg2 > 0 && (
            <line x1={pts[1].x} y1={yOf(pts[1].v)} x2={lerp(pts[1].x, pts[2].x, seg2)} y2={lerp(yOf(pts[1].v), yOf(pts[2].v), seg2)} stroke={C.red} strokeWidth="9" strokeLinecap="round" strokeDasharray="22 14" />
          )}
          {pts.map((p, i) => (
            <g key={i} transform={`translate(${p.x} ${yOf(p.v)}) scale(${ptIn[i] * (i === 1 ? 1 + 0.35 * hl100 * (1 - ramp(t, 34.9, 35.4)) : 1)})`}>
              <circle r={i === 2 ? 22 : 16} fill={i === 2 ? C.red : "#fff"} stroke={i === 2 ? "#fff" : C.navy} strokeWidth="6" />
            </g>
          ))}
        </svg>
        {pts.map((p, i) => (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: p.x - 150, width: 300, top: yOf(p.v) - (i === 2 ? 118 : 104), textAlign: "center", fontFamily: F.num, fontSize: i === 2 ? 92 : 74, color: i === 2 ? C.red : "#fff", opacity: Math.min(1, ptIn[i]), textShadow: i === 2 ? "0 0 30px rgba(214,40,40,0.8)" : "none" }}>
              {p.label}
            </div>
            <div style={{ position: "absolute", left: p.x - 150, width: 300, top: yOf(0) + 16, textAlign: "center", fontFamily: F.body, fontWeight: 700, fontSize: 28, color: i === 2 ? C.red : C.gray, opacity: Math.min(1, ptIn[i]) }}>
              {p.cap}
            </div>
          </React.Fragment>
        ))}
        <div style={{ position: "absolute", left: pts[2].x, top: yOf(pts[2].v) }}>
          <Burst p={boom} r={170} />
        </div>
      </Panel>
      {/* Mini mapa con las tres autopistas */}
      <Panel accent={C.rdBlue} style={{ left: 60, top: 1095, width: PW, height: 345, opacity: mapIn, transform: `translateY(${(1 - mapIn) * 60}px)` }}>
        <svg width={mapData.W * mk} height={330} viewBox={`0 0 ${mapData.W} ${mapData.H}`} style={{ position: "absolute", left: 20, top: 8 }}>
          <path d={mapData.dr} fill="#1f477d" stroke="rgba(255,255,255,0.8)" strokeWidth="2.5" />
          {hw.map((h) => (
            <path key={h.key} d={mapPath(mapData.highways[h.key] as number[][])} fill="none" stroke={h.color} strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - ramp(t, h.at, h.at + 0.6, easeInOut)} />
          ))}
          <circle cx={mapData.santoDomingo[0]} cy={mapData.santoDomingo[1]} r="11" fill="#fff" stroke={C.navy} strokeWidth="4" />
        </svg>
        <div style={{ position: "absolute", left: 500, top: 46 }}>
          {hw.map((h, i) => (
            <div key={h.key} style={{ display: "flex", alignItems: "center", gap: 18, marginBottom: 30, opacity: ramp(t, h.at, h.at + 0.3), transform: `translateX(${(1 - ramp(t, h.at, h.at + 0.3)) * 30}px)` }}>
              <div style={{ width: 60, height: 12, borderRadius: 6, background: h.color }} />
              <div style={{ fontFamily: F.title, fontWeight: 800, fontSize: 36, color: "#fff" }}>{h.name}</div>
            </div>
          ))}
          <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 26, color: C.grayMid, marginTop: -6 }}>Principales autopistas · RD$100 por carro</div>
        </div>
      </Panel>
    </AbsoluteFill>
  );
};

/* ───────────────────────── Escena 7 — El marbete ───────────────────────── */
export const S07Marbete: React.FC<P> = ({ t }) => {
  const { start, end } = SCENES.marbete;
  const mb = pop(t, 36.25, { damping: 13 });
  const debt = pop(t, 36.75, { damping: 12 });
  const dgii = ramp(t, 38.15, 38.6, easeOut);
  const stampT = 39.62;
  const st = ramp(t, stampT - 0.22, stampT, (x) => x * x);
  const sh = shake(t, stampT, 20);
  return (
    <AbsoluteFill style={{ transform: `translate(${sh.x}px, ${sh.y}px)` }}>
      <Backdrop src="media/fotos/autopista-duarte.jpg" t={t - start} dur={end - start} dim={0.8} focusX={0.45} />
      <Chip bg="#fff" color={C.red} style={{ left: "50%", top: 480, transform: `translateX(-50%) scale(${debt})` }} size={44}>
        ⚠ Deudas de peaje
      </Chip>
      <div style={{ position: "absolute", left: 540 - 330, top: 640, transform: `scale(${mb}) rotate(${(1 - mb) * 10 - 3}deg)`, filter: t > stampT ? "saturate(0.55) brightness(0.85)" : "none" }}>
        <Marbete w={660} />
        {t > stampT - 0.22 && (
          <div style={{ position: "absolute", left: 30, top: 140, transform: `scale(${lerp(2.6, 1, st)}) rotate(-14deg)`, opacity: st }}>
            <Stamp w={600} />
          </div>
        )}
      </div>
      <div style={{ position: "absolute", left: 540, top: 860 }}>
        <Burst p={ramp(t, stampT, stampT + 0.6)} r={380} n={18} />
      </div>
      {/* Rótulo DGII */}
      <div style={{ position: "absolute", left: 60, right: 60, top: 1210, height: 170, display: "flex", overflow: "hidden", borderRadius: 22, clipPath: `inset(0 ${(1 - dgii) * 100}% 0 0)`, boxShadow: "0 20px 50px rgba(0,0,0,0.5)" }}>
        <div style={{ width: 250, background: C.red, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: F.title, fontWeight: 900, fontSize: 76, color: "#fff", letterSpacing: 2 }}>DGII</div>
        <div style={{ flex: 1, background: "rgba(255,255,255,0.96)", display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 34px" }}>
          <div style={{ fontFamily: F.title, fontWeight: 800, fontSize: 40, color: C.navy, lineHeight: 1.1 }}>Dirección General de Impuestos Internos</div>
          <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 28, color: "#4a5a70", marginTop: 6 }}>Podría negar el marbete si debes peajes</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ───────────────────────── Escena 8 — El dinero ───────────────────────── */
export const S08Dinero: React.FC<P> = ({ t }) => {
  const { start, end } = SCENES.dinero;
  const head = pop(t, 41.2, { damping: 14 });
  const big = 12000 * ramp(t, 42.35, 44.45, (x) => 1 - (1 - x) ** 3);
  const bigDone = pop(t, 44.45, { damping: 8 });
  const sec = pop(t, 44.9, { damping: 14 });
  const secVal = 92.5 * ramp(t, 45.0, 46.2, (x) => 1 - (1 - x) ** 3);
  const piggy = pop(t, 41.6, { damping: 12 });
  const ctl = pop(t, 47.25, { damping: 11 });
  const lockC = ramp(t, 47.7, 47.9);
  const fade = ramp(t, 47.1, 47.5);
  return (
    <AbsoluteFill>
      <Backdrop src="media/fotos/av-27-febrero.jpg" t={t - start} dur={end - start} dim={0.85} focusX={0.5} from={{ s: 1.05, x: 0, y: 0 }} to={{ s: 1.25, x: -30, y: 0 }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 480, textAlign: "center", opacity: head, transform: `translateY(${(1 - head) * 30}px)` }}>
        <div style={{ fontFamily: F.title, fontWeight: 800, fontSize: 40, letterSpacing: 3, color: C.gray }}>RECAUDACIÓN DE PEAJES EN 2025</div>
        <FlagStripe style={{ left: 465, top: 62 }} w={150} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 560, textAlign: "center", transform: `scale(${1 + 0.08 * bigDone * (1 - ramp(t, 44.6, 45.0))})` }}>
        <div style={{ fontFamily: F.num, fontSize: 250, lineHeight: 0.95, color: "#fff", textShadow: "0 12px 50px rgba(0,0,0,0.6)", opacity: ramp(t, 42.2, 42.4) }}>
          RD${Math.round(big).toLocaleString("en-US")}
        </div>
        <div style={{ fontFamily: F.title, fontWeight: 900, fontSize: 74, color: C.red, marginTop: -6, opacity: ramp(t, 43.4, 43.7) }}>millones+</div>
      </div>
      <Panel style={{ left: 110, right: 110, top: 925, height: 150, opacity: sec, transform: `translateY(${(1 - sec) * 40}px)` }}>
        <div style={{ position: "absolute", left: 50, top: 18, fontFamily: F.num, fontSize: 90, color: C.gold, lineHeight: 1.2 }}>{secVal.toFixed(1)}</div>
        <div style={{ position: "absolute", left: 250, top: 28, right: 20, fontFamily: F.body, fontWeight: 700, fontSize: 32, color: "#fff", lineHeight: 1.2 }}>
          millones de pasadas de vehículos en 2025
        </div>
      </Panel>
      {/* alcancía con monedas y billetes que caen */}
      <div style={{ position: "absolute", left: 540 - 160, top: 1170, transform: `scale(${piggy * (1 - 0.25 * fade)})`, opacity: 1 - 0.75 * fade }}>
        {Array.from({ length: 7 }).map((_, i) => {
          const period = 0.9;
          const t0 = 41.7 + i * 0.32;
          if (t < t0 || t > 47.4) return null;
          const p = ((t - t0) % period) / period;
          const isBill = i % 3 === 1;
          return (
            <div key={i} style={{ position: "absolute", left: 120 + ((i * 37) % 70) - 30, top: -150 + p * 200, opacity: p < 0.85 ? 1 : (1 - p) / 0.15, transform: `rotate(${(i % 2 ? 1 : -1) * p * 160}deg)` }}>
              {isBill ? <Bill w={130} /> : <Coin w={84} label="" />}
            </div>
          );
        })}
        <Piggy w={320} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1150, display: "flex", justifyContent: "center", alignItems: "center", gap: 26, transform: `scale(${ctl})` }}>
        <Padlock w={130} closed={lockC} />
        <div style={{ fontFamily: F.title, fontWeight: 900, fontSize: 64, color: "#fff", lineHeight: 1, background: C.red, padding: "22px 30px", borderRadius: 22 }}>
          CONTROL
          <br />
          MÁS ESTRICTO
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ───────────────────────── Escena 9 — Tarjeta de fuente ───────────────────────── */
const SERIF = "'DejaVu Serif', 'Liberation Serif', Georgia, serif";
const Mark: React.FC<{ p: number; children: React.ReactNode }> = ({ p, children }) => (
  <span style={{ backgroundImage: `linear-gradient(transparent 55%, rgba(214,40,40,0.45) 55%)`, backgroundSize: `${p * 100}% 100%`, backgroundRepeat: "no-repeat" }}>{children}</span>
);
export const S09Fuente: React.FC<P> = ({ t }) => {
  const { start, end } = SCENES.fuente;
  const card = pop(t, 49.75, { damping: 14 });
  const pend = pop(t, 51.85, { damping: 12 });
  const zig = Array.from({ length: 31 })
    .map((_, i) => `${(i / 30) * 100}% ${i % 2 ? 0 : 1.6}%`)
    .join(", ");
  const zigB = Array.from({ length: 31 })
    .map((_, i) => `${100 - (i / 30) * 100}% ${i % 2 ? 100 : 98.4}%`)
    .join(", ");
  return (
    <AbsoluteFill>
      <Backdrop src="media/fotos/congreso-nacional.jpg" t={t - start} dur={end - start} dim={0.9} blur={9} focusX={0.5} from={{ s: 1.15, x: 0, y: 0 }} to={{ s: 1.25, x: 0, y: -10 }} />
      <div
        style={{
          position: "absolute",
          left: 75,
          right: 75,
          top: 475,
          height: 640,
          background: "linear-gradient(170deg, #f7f2e4, #ece3cc)",
          clipPath: `polygon(${zig}, ${zigB})`,
          boxShadow: "0 30px 80px rgba(0,0,0,0.6)",
          transform: `rotate(${-2.2 + (1 - card) * -8}deg) scale(${0.8 + 0.2 * card}) translateY(${(1 - card) * 200}px)`,
          opacity: card,
          padding: "52px 58px",
          boxSizing: "border-box",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "3px solid #2b2b2b", paddingBottom: 12 }}>
          <span style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 34, color: "#1d1d1d", letterSpacing: 2 }}>REVISTA MERCADO</span>
          <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 24, color: "#555", alignSelf: "flex-end" }}>Economía · RD</span>
        </div>
        <div style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 50, lineHeight: 1.3, color: "#1d1d1d", marginTop: 34 }}>
          “Multa equivalente a <Mark p={ramp(t, 50.3, 50.9)}>cinco veces el monto adeudado</Mark>, con un mínimo de <Mark p={ramp(t, 50.9, 51.4)}>RD$500</Mark>”
        </div>
        <div style={{ position: "absolute", left: 58, right: 58, bottom: 52, fontFamily: F.body, fontWeight: 700, fontSize: 27, color: "#444", borderTop: "2px solid #bbb", paddingTop: 16 }}>
          Fuente: Revista Mercado / proyecto del Poder Ejecutivo
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1170, display: "flex", justifyContent: "center", alignItems: "center", gap: 20, transform: `scale(${pend})` }}>
        <div style={{ transform: `rotate(${Math.sin(t * 3) * 8}deg)`, transformOrigin: "70% 80%" }}>
          <Gavel w={200} />
        </div>
        <div style={{ fontFamily: F.title, fontWeight: 900, fontSize: 52, color: "#fff", background: "rgba(11,31,58,0.92)", border: `4px solid ${C.red}`, padding: "18px 28px", borderRadius: 20, lineHeight: 1.05 }}>
          PENDIENTE DE
          <br />
          <span style={{ color: C.red }}>APROBACIÓN</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ───────────────────────── Escena 10 — Encuesta ───────────────────────── */
export const S10Encuesta: React.FC<P> = ({ t }) => {
  const { start, end } = SCENES.encuesta;
  const card = pop(t, 53.95, { damping: 14 });
  const opts = [
    { icon: "🛣️", label: "Modernización", target: 0.44, at: 55.6, color: "#fff" },
    { icon: "💸", label: "Otra forma de cobrar", target: 0.47, at: 57.05, color: C.red },
  ];
  const cta = pop(t, 59.1, { damping: 9 });
  return (
    <AbsoluteFill>
      <Backdrop src="media/fotos/las-americas-km12.jpg" t={t - start} dur={end - start} dim={0.88} focusX={0.5} from={{ s: 1.05, x: 0, y: 0 }} to={{ s: 1.18, x: 0, y: -30 }} />
      <Panel style={{ left: 60, right: 60, top: 470, height: 690, opacity: card, transform: `translateY(${(1 - card) * 60}px)` }}>
        <Chip style={{ left: 50, top: 40 }} size={30}>
          Encuesta
        </Chip>
        <div style={{ position: "absolute", left: 50, right: 40, top: 128, fontFamily: F.title, fontWeight: 900, fontSize: 56, lineHeight: 1.1, color: "#fff" }}>
          ¿Modernización… o una forma más de <span style={{ color: C.red }}>cobrarte</span>?
        </div>
        {opts.map((o, i) => {
          const fill = ramp(t, o.at, o.at + 1.0, easeOut) * o.target + Math.sin(t * 5 + i * 2) * 0.015 * ramp(t, o.at + 1, o.at + 1.3);
          const act = pop(t, o.at, { damping: 10 });
          return (
            <div key={i} style={{ position: "absolute", left: 50, right: 50, top: 340 + i * 160, height: 130, borderRadius: 26, background: "rgba(255,255,255,0.08)", border: `3px solid ${t > o.at ? o.color : "rgba(255,255,255,0.25)"}`, overflow: "hidden", transform: `scale(${1 + 0.03 * act * (1 - ramp(t, o.at + 0.4, o.at + 0.8))})` }}>
              <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${fill * 100}%`, background: i === 0 ? "rgba(255,255,255,0.28)" : "rgba(214,40,40,0.65)" }} />
              <div style={{ position: "absolute", left: 30, top: 0, bottom: 0, display: "flex", alignItems: "center", gap: 22, fontFamily: F.title, fontWeight: 800, fontSize: 46, color: "#fff" }}>
                <span style={{ fontSize: 58 }}>{o.icon}</span> {o.label}
              </div>
              <div style={{ position: "absolute", right: 30, top: 0, bottom: 0, display: "flex", alignItems: "center", fontFamily: F.num, fontSize: 64, color: "#fff", opacity: ramp(t, o.at + 0.6, o.at + 1) }}>
                ?%
              </div>
            </div>
          );
        })}
      </Panel>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1200, textAlign: "center", transform: `scale(${cta})` }}>
        <div style={{ display: "inline-block", fontFamily: F.title, fontWeight: 900, fontSize: 64, color: "#fff", background: C.red, padding: "20px 40px", borderRadius: 24, boxShadow: "0 0 60px rgba(214,40,40,0.6)" }}>
          ¿Tú qué opinas? Comenta 👇
        </div>
        <div style={{ fontSize: 80, marginTop: 6, transform: `translateY(${Math.abs(Math.sin(t * 6)) * 18}px)` }}>⬇️</div>
      </div>
    </AbsoluteFill>
  );
};

/* ───────────────────────── Escena 11 — Cierre ───────────────────────── */
export const S11Cierre: React.FC<P> = ({ t }) => {
  const { start } = SCENES.cierre;
  const clipLen = 3.5;
  return (
    <AbsoluteFill style={{ background: "#0B2A5C" }}>
      {t < start + clipLen - 0.05 ? (
        <Sequence from={Math.round(start * FPS)} layout="none">
          <OffthreadVideo src={staticFile("media/capital_curioso_cierre.mp4")} muted style={{ width: W, height: 1920 }} />
        </Sequence>
      ) : (
        <Img src={staticFile("media/cierre-ultimo-cuadro.png")} style={{ width: W, height: 1920 }} />
      )}
    </AbsoluteFill>
  );
};

export { PlateRD };
