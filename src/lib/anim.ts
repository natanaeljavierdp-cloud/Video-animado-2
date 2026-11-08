import {Easing, interpolate} from 'remotion';
import {CatmullRomCurve3, Vector3} from 'three';

export type V3 = [number, number, number];

export const ease = Easing.bezier(0.45, 0, 0.55, 1);
export const easeOut = Easing.bezier(0.16, 1, 0.3, 1);

export const ip = (
	f: number,
	inR: number[],
	outR: number[],
	e: (t: number) => number = ease,
) =>
	interpolate(f, inR, outR, {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing: e,
	});

/** Generador pseudoaleatorio determinista (mulberry32). */
export function rng(seed: number) {
	let a = seed >>> 0;
	return () => {
		a |= 0;
		a = (a + 0x6d2b79f5) | 0;
		let t = Math.imul(a ^ (a >>> 15), 1 | a);
		t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

/** Trayectoria de cámara suave (Catmull-Rom) recorrida con easing. */
export function camPath(
	frame: number,
	from: number,
	to: number,
	positions: V3[],
	targets: V3[],
	e: (t: number) => number = ease,
) {
	const p = ip(frame, [from, to], [0, 1], e);
	const pc = new CatmullRomCurve3(positions.map((v) => new Vector3(...v)), false, 'centripetal');
	const tc = new CatmullRomCurve3(targets.map((v) => new Vector3(...v)), false, 'centripetal');
	const a = pc.getPoint(p);
	const b = tc.getPoint(p);
	return {pos: [a.x, a.y, a.z] as V3, look: [b.x, b.y, b.z] as V3};
}
