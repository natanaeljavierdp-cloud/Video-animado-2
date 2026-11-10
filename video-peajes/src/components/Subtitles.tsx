import React, { useMemo } from "react";
import words from "../data/words.json";
import { C, F, SAFE, W } from "../theme";
import { pop } from "../anim";

type Wd = { word: string; start: number; end: number };
type Chunk = { words: Wd[]; start: number; end: number };

const MAX_WORDS = 4;
const MAX_CHARS = 19;

const buildChunks = (ws: Wd[]): Chunk[] => {
  const chunks: Chunk[] = [];
  let cur: Wd[] = [];
  const flush = () => {
    if (cur.length) chunks.push({ words: cur, start: cur[0].start, end: cur[cur.length - 1].end });
    cur = [];
  };
  ws.forEach((w, i) => {
    const prev = cur[cur.length - 1];
    const len = cur.reduce((a, x) => a + x.word.length + 1, 0) + w.word.length;
    if (prev && (cur.length >= MAX_WORDS || len > MAX_CHARS || /[.,?!…]$/.test(prev.word) || w.start - prev.end > 0.35)) flush();
    cur.push(w);
    if (i === ws.length - 1) flush();
  });
  // Cada bloque se queda en pantalla hasta que empieza el siguiente (máx. 0.6 s de cola)
  return chunks.map((c, i) => ({ ...c, end: Math.min(chunks[i + 1]?.start ?? c.end + 0.6, c.end + 0.6) }));
};

/** Subtítulos palabra por palabra en la zona superior. La palabra actual en rojo. */
export const Subtitles: React.FC<{ t: number }> = ({ t }) => {
  const chunks = useMemo(() => buildChunks(words as Wd[]), []);
  const chunk = chunks.find((c) => t >= c.start - 0.04 && t < c.end);
  if (!chunk) return null;
  const enter = pop(t, chunk.start - 0.04, { damping: 14, stiffness: 260 });
  return (
    <div
      style={{
        position: "absolute",
        top: SAFE.subTop,
        left: 50,
        width: W - 100,
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        alignContent: "flex-start",
        gap: 0,
        transform: `scale(${0.88 + 0.12 * enter}) translateY(${(1 - enter) * 16}px)`,
        opacity: Math.min(1, enter * 1.6),
      }}
    >
      {chunk.words.map((w, i) => {
        const next = chunk.words[i + 1];
        const active = t >= w.start - 0.03 && t < (next ? next.start - 0.03 : chunk.end);
        const said = t >= w.start - 0.03;
        const k = active ? pop(t, w.start - 0.03, { damping: 10, stiffness: 300 }) : 0;
        return (
          <span
            key={i}
            style={{
              fontFamily: F.title,
              fontWeight: 900,
              fontSize: 78,
              lineHeight: 1.12,
              textTransform: "uppercase",
              letterSpacing: -0.5,
              color: active ? C.red : C.white,
              opacity: said || active ? 1 : 0.92,
              WebkitTextStroke: "11px #000",
              paintOrder: "stroke fill",
              textShadow: "0 6px 18px rgba(0,0,0,0.7)",
              display: "inline-block",
              margin: "0 16px",
              transform: `scale(${1 + 0.04 * k})`,
            }}
          >
            {w.word}
          </span>
        );
      })}
    </div>
  );
};
