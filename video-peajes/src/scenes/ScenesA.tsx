import React from "react";
import { AbsoluteFill } from "remotion";
import { C, F, W } from "../theme";
import { easeInOut, easeOut, fmt, lerp, map, pop, ramp, shake } from "../anim";
import { SCENES } from "../timeline";
import { Backdrop, NavyField } from "../components/Cinematic";
import { Chip, FlagStripe, Label, Panel } from "../components/UI";
import {
  Burst,
  CalendarIcon,
  CarRear,
  Check,
  Coin,
  DocumentIcon,
  Marbete,
  Padlock,
  PlateRD,
  TeleSticker,
  TollBooth,
} from "../components/Icons";
import mapData from "../data/map.json";

type P = { t: number };

/* ───────────────────────── Escena 1 — Gancho ───────────────────────── */
export const S01Gancho: React.FC<P> = ({ t }) => {
  const { start, end } = SCENES.gancho;
  const barrier = ramp(t, 0.5, 2.3, easeInOut) * 82;
  const carP = ramp(t, 0.9, 6.2, easeInOut);
  const carY = lerp(1560, 1130, carP);
  const carW = lerp(560, 250, carP);
  const dimIllu = ramp(t, 3.6, 4.4);
  // x5
  const x5 = pop(t, 5.78, { damping: 9, stiffness: 180 });
  const x5Up = ramp(t, 7.45, 8.0, easeInOut);
  const sh = shake(t, 5.85, 22);
  // marbete + candado
  const mb = pop(t, 7.6, { damping: 13 });
  const lockIn = pop(t, 7.9, { damping: 11 });
  const closed = ramp(t, 8.25, 8.45, (x) => x * x);
  const flash = t > 8.45 ? Math.max(0, 1 - (t - 8.45) / 0.35) : 0;
  return (
    <AbsoluteFill style={{ transform: `translate(${sh.x}px, ${sh.y}px)` }}>
      <Backdrop src="media/fotos/peaje-las-americas.jpg" t={t - start} dur={end - start} dim={0.5 + 0.35 * dimIllu} focusX={0.45}
        from={{ s: 1.04, x: 0, y: 0 }} to={{ s: 1.22, x: 20, y: -30 }} />
      {/* Ilustración: barrera que se levanta sola y carro que pasa en cámara lenta */}
      <AbsoluteFill style={{ opacity: 1 - 0.7 * dimIllu, filter: `blur(${dimIllu * 3}px)` }}>
        <div style={{ position: "absolute", left: 420, top: 760 }}>
          <TollBooth w={620} angle={barrier} />
        </div>
        <div style={{ position: "absolute", left: W / 2 - carW / 2 - 90, top: carY - carW * 0.78 }}>
          <CarRear w={carW} />
        </div>
        {/* líneas de velocidad */}
        {[0, 1, 2, 3].map((i) => {
          const p = (t * 1.6 + i / 4) % 1;
          return <div key={i} style={{ position: "absolute", left: 120 + i * 230, top: 1450 - p * 500, width: 6, height: 120, background: "rgba(255,255,255,0.35)", borderRadius: 3, opacity: (1 - p) * (1 - dimIllu) }} />;
        })}
        <Chip bg="rgba(11,31,58,0.85)" style={{ left: 70, top: 500, opacity: ramp(t, 0.4, 0.9), border: "2px solid rgba(255,255,255,0.25)" }} size={36}>
          Sin detenerte
        </Chip>
      </AbsoluteFill>
      {/* x5 */}
      {t > 5.7 && (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: lerp(660, 470, x5Up),
            textAlign: "center",
            transform: `scale(${(3 - 2 * x5) * lerp(1, 0.42, x5Up)})`,
            transformOrigin: "50% 0%",
            opacity: Math.min(1, x5 * 2),
          }}
        >
          <div style={{ fontFamily: F.num, fontSize: 560, lineHeight: 0.9, color: C.red, WebkitTextStroke: "10px #fff", paintOrder: "stroke fill", textShadow: "0 0 80px rgba(214,40,40,0.8), 0 20px 50px rgba(0,0,0,0.6)" }}>
            x5
          </div>
          <div style={{ fontFamily: F.title, fontWeight: 900, fontSize: 64, color: "#fff", letterSpacing: 3, marginTop: -10, opacity: 1 - x5Up }}>
            TE PODRÍAN COBRAR
          </div>
        </div>
      )}
      {/* marbete con candado */}
      {t > 7.5 && (
        <div style={{ position: "absolute", left: 540 - 300, top: 820, transform: `scale(${mb}) rotate(${(1 - mb) * -8}deg)` }}>
          <Marbete w={600} />
          <div style={{ position: "absolute", left: 420, top: 200, transform: `scale(${lockIn})` }}>
            <Padlock w={210} closed={closed} />
            <div style={{ position: "absolute", left: -60, top: -40, width: 330, height: 330, borderRadius: "50%", background: "radial-gradient(circle, rgba(255,255,255,0.9), rgba(255,255,255,0) 60%)", opacity: flash }} />
          </div>
          <Chip style={{ left: 40, top: 430, opacity: ramp(t, 8.4, 8.7) }} size={42}>
            Marbete bloqueado
          </Chip>
        </div>
      )}
    </AbsoluteFill>
  );
};

/* ───────────────────────── Escena 2 — El proyecto ───────────────────────── */
export const S02Proyecto: React.FC<P> = ({ t }) => {
  const { start, end } = SCENES.proyecto;
  const routeP = ramp(t, 9.7, 11.1, easeInOut);
  const card = pop(t, 11.0, { damping: 14 });
  const flip = map(t, [11.35, 11.6], [0, 1]);
  const goal = pop(t, 12.35, { damping: 14 });
  return (
    <AbsoluteFill>
      <Backdrop src="media/fotos/congreso-nacional.jpg" t={t - start} dur={end - start} dim={0.55} focusX={0.5}
        from={{ s: 1.0, x: 0, y: 10 }} to={{ s: 1.14, x: -25, y: -20 }} />
      {/* Ruta Poder Ejecutivo → Senado */}
      <Chip bg="rgba(11,31,58,0.9)" style={{ left: 60, top: 500, opacity: ramp(t, 9.4, 9.8), border: "2px solid rgba(255,255,255,0.3)" }} size={34}>
        Poder Ejecutivo
      </Chip>
      <Chip style={{ right: 60, top: 500, transform: `scale(${pop(t, 11.0)})` }} size={34}>
        Senado
      </Chip>
      <svg width={W} height={140} style={{ position: "absolute", top: 560, left: 0 }}>
        <path d="M150 70 Q540 -10 930 70" fill="none" stroke="rgba(255,255,255,0.85)" strokeWidth={6} strokeDasharray="14 14" strokeDashoffset={-t * 40}
          style={{ clipPath: `inset(0 ${(1 - routeP) * 100}% 0 0)` }} />
      </svg>
      <div style={{ position: "absolute", left: lerp(90, 760, routeP), top: lerp(640, 600, Math.sin(routeP * Math.PI)), transform: `rotate(${lerp(-12, 8, routeP)}deg) scale(${lerp(0.9, 0.7, routeP)})`, opacity: ramp(t, 9.4, 9.8) * (1 - ramp(t, 11.1, 11.4)) }}>
        <DocumentIcon w={200} />
      </div>
      {/* Tarjeta de dato */}
      <Panel style={{ left: 60, right: 60, top: 930, height: 330, transform: `translateY(${(1 - card) * 120}px)`, opacity: card }}>
        <div style={{ position: "absolute", left: 50, top: 46 }}>
          <CalendarIcon w={210} flip={flip} />
        </div>
        <div style={{ position: "absolute", left: 300, top: 54, right: 30 }}>
          <div style={{ fontFamily: F.title, fontWeight: 800, fontSize: 40, color: "#fff", lineHeight: 1.15 }}>Proyecto depositado en el Senado</div>
          <div style={{ fontFamily: F.num, fontSize: 92, color: C.red, marginTop: 12, lineHeight: 1 }}>4 de noviembre</div>
          <div style={{ fontFamily: F.num, fontSize: 64, color: C.gray, lineHeight: 1 }}>de 2026</div>
        </div>
        <FlagStripe style={{ right: 40, top: 30 }} w={150} />
      </Panel>
      <Chip bg="#fff" color={C.navy} style={{ left: 60, top: 1300, transform: `scale(${goal})`, transformOrigin: "0 50%" }} size={36}>
        🛣️ Objetivo: modernizar los peajes
      </Chip>
    </AbsoluteFill>
  );
};

/* ───────────────────────── Escena 3 — Cómo funciona ───────────────────────── */
const ROAD_TOP = 600; // y absoluta del horizonte
export const S03Funciona: React.FC<P> = ({ t }) => {
  const { start, end } = SCENES.funciona;
  const carP = ramp(t, 14.05, 17.3, easeInOut);
  const carBottom = lerp(1430, 1000, carP);
  const carW = lerp(520, 210, carP);
  const gantryGlow = ramp(t, 16.4, 16.7) * (1 - ramp(t, 17.2, 17.6));
  const beam = t > 17.0 && t < 18.25 ? ramp(t, 17.0, 17.2) * (1 - ramp(t, 18.0, 18.25)) : 0;
  const plateX = W / 2;
  const plateY = carBottom - carW * 0.78 * (205 / 312);
  const scanLine = ramp(t, 17.35, 17.85);
  const card = pop(t, 17.45, { damping: 14 });
  const mode = t < 18.2 ? 0 : t < 20.72 ? 1 : 2;
  const modeIn = pop(t, mode === 0 ? 17.45 : mode === 1 ? 18.2 : 20.72, { damping: 13 });
  const ff = pop(t, 14.9, { damping: 12 });
  return (
    <AbsoluteFill>
      <Backdrop src="media/fotos/las-americas-km12.jpg" t={t - start} dur={end - start} dim={0.85} blur={7} />
      {/* Carretera en perspectiva */}
      <svg width={W} height={1920} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <linearGradient id="road" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#1b2533" stopOpacity="0.6" />
            <stop offset="1" stopColor="#2b3646" stopOpacity="0.97" />
          </linearGradient>
          <linearGradient id="beamg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={C.red} stopOpacity="0.9" />
            <stop offset="1" stopColor={C.red} stopOpacity="0.25" />
          </linearGradient>
        </defs>
        <polygon points={`470,${ROAD_TOP} 610,${ROAD_TOP} 1180,1480 -100,1480`} fill="url(#road)" />
        <line x1="470" y1={ROAD_TOP} x2="-100" y2="1480" stroke="#fff" strokeWidth="6" opacity="0.7" />
        <line x1="610" y1={ROAD_TOP} x2="1180" y2="1480" stroke="#fff" strokeWidth="6" opacity="0.7" />
        {Array.from({ length: 9 }).map((_, i) => {
          const p = ((i / 9 + t * 0.45) % 1) ** 2; // 0 horizonte → 1 cerca
          const y = ROAD_TOP + p * 880;
          return <rect key={i} x={540 - 3 - p * 9} y={y} width={6 + p * 18} height={10 + p * 90} fill={C.gold} opacity={0.85} />;
        })}
        {/* Pórtico */}
        <rect x="150" y="640" width="26" height="420" fill="#c7d0db" />
        <rect x="904" y="640" width="26" height="420" fill="#c7d0db" />
        <rect x="130" y="620" width="820" height="70" rx="8" fill="#e8edf3" stroke={gantryGlow > 0 ? C.red : "#9aa7b8"} strokeWidth={4 + gantryGlow * 6} />
        <rect x="350" y="575" width="380" height="54" rx="8" fill={C.navy} />
        <text x="540" y="613" textAnchor="middle" fontFamily="Montserrat" fontWeight={900} fontSize="28" fill="#fff" letterSpacing="3">
          PEAJE ELECTRÓNICO
        </text>
        {[340, 540, 740].map((x) => (
          <g key={x}>
            <rect x={x - 26} y="690" width="52" height="34" rx="6" fill="#20293a" />
            <circle cx={x} cy="707" r="9" fill={beam > 0 && x === 540 ? "#ff4040" : "#5a6b85"} />
          </g>
        ))}
        {/* Haz de escaneo */}
        {beam > 0 && (
          <g opacity={beam}>
            <polygon points={`540,712 ${plateX - 90},${plateY - 10} ${plateX + 90},${plateY - 10} `} fill="url(#beamg)" opacity={0.55} />
            <line x1={plateX - 80} x2={plateX + 80} y1={lerp(720, plateY, (t * 3) % 1)} y2={lerp(720, plateY, (t * 3) % 1)} stroke="#fff" strokeWidth="4" opacity={0.8} />
            <rect x={plateX - 70} y={plateY - 30} width="140" height="80" fill="none" stroke={C.red} strokeWidth="5" rx="6" />
          </g>
        )}
        {/* Ondas de telepeaje hacia el pórtico */}
        {mode >= 1 &&
          [0, 1, 2].map((i) => {
            const p = ((t - 18.2) * 1.2 + i / 3) % 1;
            return <circle key={i} cx={740} cy={707} r={20 + p * 120} fill="none" stroke="#fff" strokeWidth={5} opacity={(1 - p) * 0.8 * (1 - ramp(t, 20.6, 20.9))} />;
          })}
      </svg>
      <div style={{ position: "absolute", left: W / 2 - carW / 2, top: carBottom - carW * 0.78 }}>
        <CarRear w={carW} />
      </div>
      <Chip style={{ left: "50%", top: 470, transform: `translateX(-50%) scale(${ff})` }} size={46}>
        Sistema Free Flow
      </Chip>
      {/* Tarjeta explicativa */}
      <Panel style={{ left: 70, right: 70, top: 1100, height: 320, opacity: card, transform: `translateY(${(1 - card) * 80}px)` }}>
        <div style={{ position: "absolute", inset: 0, opacity: mode === 0 ? 1 : 0, transform: `scale(${mode === 0 ? modeIn : 1})` }}>
          <div style={{ position: "absolute", left: 50, top: 60 }}>
            <PlateRD w={420} />
            <div style={{ position: "absolute", left: 0, top: 0, width: 420, height: 210, overflow: "hidden" }}>
              <div style={{ position: "absolute", top: 0, bottom: 0, left: scanLine * 420 - 6, width: 12, background: C.redHot, boxShadow: `0 0 30px ${C.redHot}`, opacity: scanLine < 1 ? 1 : 0 }} />
            </div>
          </div>
          <div style={{ position: "absolute", left: 510, top: 90, display: "flex", alignItems: "center", gap: 16, opacity: ramp(t, 17.8, 17.95) }}>
            <Check w={74} p={ramp(t, 17.8, 18.0)} />
          </div>
          <div style={{ position: "absolute", left: 510, top: 180, fontFamily: F.title, fontWeight: 900, fontSize: 52, color: "#fff", lineHeight: 1, opacity: ramp(t, 17.8, 17.95) }}>
            Placa
            <br />
            <span style={{ color: C.green }}>leída ✓</span>
          </div>
        </div>
        <div style={{ position: "absolute", inset: 0, opacity: mode === 1 ? 1 : 0, transform: `scale(${mode === 1 ? modeIn : 1})` }}>
          <div style={{ position: "absolute", left: 40, top: 40 }}>
            <TeleSticker w={300} wave={(t - 18.2) * 1.2} />
          </div>
          <div style={{ position: "absolute", left: 390, top: 80, right: 30, fontFamily: F.title, fontWeight: 900, fontSize: 50, color: "#fff", lineHeight: 1.05 }}>
            Dispositivo de <span style={{ color: C.red }}>telepeaje</span>
            <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 30, color: C.gray, marginTop: 14 }}>Sticker en el parabrisas</div>
          </div>
        </div>
        <div style={{ position: "absolute", inset: 0, opacity: mode === 2 ? 1 : 0, transform: `scale(${mode === 2 ? modeIn : 1})`, display: "flex", alignItems: "center", justifyContent: "center", gap: 36 }}>
          <svg width="190" height="190" viewBox="0 0 190 190">
            <rect x="10" y="80" width="170" height="26" rx="13" fill="#fff" />
            {[0, 1, 2, 3].map((i) => <rect key={i} x={22 + i * 42} y="80" width="21" height="26" fill={C.red} />)}
            <circle cx="95" cy="93" r="84" fill="none" stroke={C.red} strokeWidth="14" />
            <line x1="35" y1="153" x2="155" y2="33" stroke={C.red} strokeWidth="14" />
          </svg>
          <div style={{ fontFamily: F.title, fontWeight: 900, fontSize: 70, color: "#fff", lineHeight: 0.95 }}>
            SIN
            <br />
            <span style={{ color: C.red }}>BARRERAS</span>
          </div>
        </div>
      </Panel>
    </AbsoluteFill>
  );
};

/* ───────────────────────── Escena 4 — Mapa ───────────────────────── */
const mapPath = (pts: number[][]) => "M" + pts.map((p) => p.join(" ")).join(" L");
export const S04Mapa: React.FC<P> = ({ t }) => {
  const MW = W; // ancho en pantalla
  const k0 = MW / mapData.W;
  const top = 640;
  const zoom = ramp(t, 21.95, 22.95, easeInOut);
  const s = lerp(1, 3.6, zoom);
  const cx = lerp(mapData.W / 2, 600, zoom);
  const cy = lerp(mapData.H / 2, 455, zoom);
  // punto del mapa → pantalla
  const toScreen = (p: number[]) => [(p[0] - cx) * s * k0 + MW / 2, (p[1] - cy) * s * k0 + top + (mapData.H * k0) / 2];
  const draw = ramp(t, 22.7, 23.6, easeInOut);
  const pin = pop(t, 23.25, { damping: 9 });
  const tag = pop(t, 23.45, { damping: 12 });
  const [px, py] = toScreen(mapData.peajeLasAmericas);
  const [sx, sy] = toScreen(mapData.santoDomingo);
  const tf = `translate(${MW / 2} ${top + (mapData.H * k0) / 2}) scale(${s * k0}) translate(${-cx} ${-cy})`;
  return (
    <AbsoluteFill>
      <NavyField t={t} />
      <svg width={W} height={1920} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="6" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <g transform={tf}>
          <path d={mapData.haiti} fill="#132a4a" stroke="rgba(255,255,255,0.25)" strokeWidth={1.2 / s} />
          <path d={mapData.dr} fill="#1f477d" stroke="#fff" strokeWidth={2.4 / s} />
          <path d={mapPath(mapData.highways.lasAmericas)} fill="none" stroke={C.red} strokeWidth={9 / s} strokeLinecap="round" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - draw} filter="url(#glow)" />
        </g>
      </svg>
      <div style={{ position: "absolute", left: 0, right: 0, top: 500, textAlign: "center", fontFamily: F.title, fontWeight: 900, fontSize: 50, letterSpacing: 6, color: "#fff", opacity: 1 - zoom }}>
        REPÚBLICA DOMINICANA
      </div>
      <FlagStripe style={{ left: 465, top: 575, opacity: 1 - zoom }} w={150} />
      {/* Santo Domingo */}
      <div style={{ position: "absolute", left: sx - 12, top: sy - 12, width: 24, height: 24, borderRadius: 12, background: "#fff", border: `5px solid ${C.navy}`, opacity: ramp(t, 22.6, 22.9) }} />
      <Label style={{ left: sx - 330, top: sy - 90, fontFamily: F.title, fontWeight: 900, fontSize: 40, color: "#fff", opacity: ramp(t, 22.6, 22.9) }}>SANTO DOMINGO</Label>
      <Label style={{ left: 140, top: sy + 110, fontFamily: F.title, fontWeight: 800, fontSize: 36, color: C.red, opacity: ramp(t, 23.2, 23.5), transform: "rotate(-3deg)" }}>
        Autopista Las Américas
      </Label>
      {/* Pin pulsante */}
      <div style={{ position: "absolute", left: px, top: py }}>
        {[0, 1].map((i) => {
          const p = ((t - 23.25) * 1.1 + i * 0.5) % 1;
          return t > 23.25 ? <div key={i} style={{ position: "absolute", left: -90 * p, top: -90 * p, width: 180 * p, height: 180 * p, borderRadius: "50%", border: `5px solid ${C.red}`, opacity: 1 - p }} /> : null;
        })}
        <svg width="90" height="120" viewBox="0 0 90 120" style={{ position: "absolute", left: -45, top: -116, transform: `scale(${pin})`, transformOrigin: "50% 100%" }}>
          <path d="M45 118 C45 118 6 70 6 42 A39 39 0 1 1 84 42 C84 70 45 118 45 118Z" fill={C.red} stroke="#fff" strokeWidth="5" />
          <circle cx="45" cy="42" r="15" fill="#fff" />
        </svg>
      </div>
      <Chip style={{ left: px - 190, top: py - 290, transform: `scale(${tag})` }} size={42}>
        Prueba piloto
      </Chip>
    </AbsoluteFill>
  );
};

/* ───────────────────────── Escena 5 — Las multas ───────────────────────── */
export const S05Multas: React.FC<P> = ({ t }) => {
  const { start, end } = SCENES.multas;
  const title = pop(t, 25.34, { damping: 10, stiffness: 220 });
  const coin = pop(t, 26.3, { damping: 11 });
  const split = ramp(t, 27.9, 28.45, easeOut);
  const count = 100 + 400 * ramp(t, 28.35, 30.5, (x) => 1 - (1 - x) ** 2);
  const fine = pop(t, 30.47, { damping: 9, stiffness: 200 });
  const sh = shake(t, 30.5, 16);
  return (
    <AbsoluteFill style={{ transform: `translate(${sh.x}px, ${sh.y}px)` }}>
      <Backdrop src="media/fotos/las-americas-la-caleta.jpg" t={t - start} dur={end - start} dim={0.8} focusX={0.5}
        from={{ s: 1.1, x: 0, y: 0 }} to={{ s: 1.2, x: -40, y: 10 }} />
      <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 55%, rgba(214,40,40,${0.25 * fine}), transparent 60%)` }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 470, textAlign: "center", transform: `scale(${2 - title}) rotate(${(1 - title) * -6}deg)`, opacity: Math.min(1, title * 2) }}>
        <span style={{ fontFamily: F.title, fontWeight: 900, fontSize: 92, color: "#fff", background: C.red, padding: "4px 34px", borderRadius: 16, letterSpacing: 4 }}>MULTAS</span>
      </div>
      <Label style={{ left: 0, right: 0, top: 610, textAlign: "center", fontSize: 40, opacity: ramp(t, 26.2, 26.5) }}>
        Si evades el pago…
      </Label>
      {/* monedas */}
      {[-2, -1, 0, 1, 2].map((i) => {
        const isMain = i === 0;
        const s = isMain ? coin : split;
        const x = 540 + i * 196 * split;
        const delay = Math.abs(i) * 0.06;
        const sp = isMain ? s : ramp(t, 27.9 + delay, 28.4 + delay, easeOut);
        if (!isMain && t < 27.9) return null;
        return (
          <div key={i} style={{ position: "absolute", left: x - 95, top: 715, transform: `scale(${sp}) translateY(${Math.sin(t * 4 + i) * 6}px)` }}>
            <Coin w={190} />
          </div>
        );
      })}
      <div style={{ position: "absolute", left: 0, right: 0, top: 940, textAlign: "center", fontFamily: F.num, fontSize: 96, color: C.gold, opacity: ramp(t, 28.0, 28.3) }}>
        RD$100 × 5
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1030, textAlign: "center", opacity: ramp(t, 28.3, 28.5) }}>
        <span style={{ fontFamily: F.num, fontSize: 210, color: "#fff", lineHeight: 1, textShadow: "0 10px 40px rgba(0,0,0,0.6)" }}>RD${fmt(count)}</span>
      </div>
      <div style={{ position: "absolute", left: 60, right: 60, top: 1255, height: 150, background: C.red, borderRadius: 26, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${fine})`, boxShadow: "0 0 80px rgba(214,40,40,0.7)" }}>
        <span style={{ fontFamily: F.title, fontWeight: 900, fontSize: 66, color: "#fff" }}>
          Multa mínima: <span style={{ fontFamily: F.num, fontSize: 104, verticalAlign: "-6px" }}>RD$500</span>
        </span>
      </div>
      <div style={{ position: "absolute", left: 540, top: 1330 }}>
        <Burst p={ramp(t, 30.5, 31.2)} r={420} />
      </div>
    </AbsoluteFill>
  );
};
