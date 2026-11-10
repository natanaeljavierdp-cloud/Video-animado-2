import { Easing, interpolate, spring } from "remotion";
import { FPS } from "./theme";

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
/** 0→1 entre a y b (segundos), con easing. */
export const ramp = (t: number, a: number, b: number, ease: (x: number) => number = Easing.bezier(0.33, 0, 0.2, 1)) =>
  ease(clamp01((t - a) / (b - a)));
export const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);
export const easeIn = Easing.bezier(0.5, 0, 0.75, 0);
/** Resorte que arranca en `at` (segundos). */
export const pop = (t: number, at: number, cfg: { damping?: number; stiffness?: number; mass?: number } = {}) =>
  t < at ? 0 : spring({ frame: (t - at) * FPS, fps: FPS, config: { damping: 12, stiffness: 160, mass: 0.8, ...cfg } });
export const lerp = (a: number, b: number, p: number) => a + (b - a) * p;
export const map = (t: number, input: number[], output: number[]) =>
  interpolate(t, input, output, { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
/** Sacudida de cámara que decae tras `at`. */
export const shake = (t: number, at: number, amp = 18, dur = 0.45) => {
  if (t < at || t > at + dur) return { x: 0, y: 0 };
  const k = 1 - (t - at) / dur;
  return { x: Math.sin(t * 95) * amp * k, y: Math.cos(t * 77) * amp * k };
};
export const fmt = (n: number) => Math.round(n).toLocaleString("en-US");
