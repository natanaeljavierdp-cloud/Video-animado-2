import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { C, F } from "./theme";
import { CarRear, Marbete, Padlock } from "./components/Icons";
import { FlagStripe } from "./components/UI";
import { loadFonts } from "./fonts";

loadFonts();

/** Miniatura / portada: "¿Peajes SIN casetas? 🚗💸" + x5 en rojo. */
export const Miniatura: React.FC = () => (
  <AbsoluteFill style={{ background: C.navyDeep }}>
    <Img src={staticFile("media/fotos/peaje-las-americas.jpg")} style={{ position: "absolute", height: 1920, left: "50%", transform: "translateX(-45%) scale(1.15)", filter: "contrast(1.1) saturate(1.1)" }} />
    <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(6,20,42,0.92) 0%, rgba(6,20,42,0.45) 38%, rgba(6,20,42,0.55) 62%, rgba(6,20,42,0.95) 100%)" }} />
    <AbsoluteFill style={{ background: "radial-gradient(ellipse 85% 70% at 50% 50%, transparent 55%, rgba(0,0,0,0.6) 100%)" }} />
    <div style={{ position: "absolute", left: 60, right: 60, top: 230, textAlign: "center" }}>
      <div style={{ fontFamily: F.title, fontWeight: 900, fontSize: 132, lineHeight: 1.0, color: "#fff", WebkitTextStroke: "10px #000", paintOrder: "stroke fill", textShadow: "0 10px 30px rgba(0,0,0,0.7)" }}>
        ¿PEAJES <span style={{ color: C.red }}>SIN</span> CASETAS?
      </div>
      <div style={{ fontSize: 120, marginTop: 10 }}>🚗💸</div>
      <FlagStripe style={{ left: 380, top: -40 }} w={200} />
    </div>
    <div style={{ position: "absolute", left: 0, right: 0, top: 820, textAlign: "center", fontFamily: F.num, fontSize: 620, lineHeight: 0.9, color: C.red, WebkitTextStroke: "12px #fff", paintOrder: "stroke fill", textShadow: "0 0 90px rgba(214,40,40,0.85)", transform: "rotate(-4deg)" }}>
      x5
    </div>
    <div style={{ position: "absolute", left: 70, top: 1400, transform: "rotate(-6deg)" }}>
      <Marbete w={430} />
      <div style={{ position: "absolute", left: 320, top: 140 }}>
        <Padlock w={150} closed={1} />
      </div>
    </div>
    <div style={{ position: "absolute", right: 40, top: 1450 }}>
      <CarRear w={420} />
    </div>
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 70, textAlign: "center", fontFamily: F.title, fontWeight: 800, fontSize: 40, color: C.gray, letterSpacing: 2 }}>
      CAPITAL CURIOSO · @capitalcuriosoo
    </div>
  </AbsoluteFill>
);
