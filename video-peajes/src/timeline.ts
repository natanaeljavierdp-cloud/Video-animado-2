// Tiempos (segundos) tomados de la transcripción con marcas por palabra (Whisper).
export type TransitionType = "wipe" | "zoom" | "iris" | "cut";
export const SCENES = {
  gancho: { start: 0, end: 9.25, enter: "cut" as TransitionType },
  proyecto: { start: 9.25, end: 13.85, enter: "wipe" as TransitionType },
  funciona: { start: 13.85, end: 21.8, enter: "zoom" as TransitionType },
  mapa: { start: 21.8, end: 24.55, enter: "iris" as TransitionType },
  multas: { start: 24.55, end: 31.75, enter: "wipe" as TransitionType },
  comparacion: { start: 31.75, end: 36.1, enter: "zoom" as TransitionType },
  marbete: { start: 36.1, end: 40.95, enter: "wipe" as TransitionType },
  dinero: { start: 40.95, end: 49.65, enter: "zoom" as TransitionType },
  fuente: { start: 49.65, end: 53.85, enter: "wipe" as TransitionType },
  encuesta: { start: 53.85, end: 59.85, enter: "iris" as TransitionType },
  cierre: { start: 59.85, end: 64.0, enter: "zoom" as TransitionType },
};
export const TOTAL_SECONDS = 64.0;
export const TRANSITION = 0.42; // duración de cada transición (s)
