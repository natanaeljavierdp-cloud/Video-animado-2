import React from 'react';
import {Flock, Herd, Person, PersonProps} from '../three/Characters';
import {EggTray} from '../three/Characters';
import {Wheelbarrow} from '../three/World';

/** Vestuario fijo para mantener la continuidad de personajes en todas las escenas. */
export const MIGUEL = {
	shirt: '#c0392b',
	pants: '#2f4f7f',
	skin: '#a86b4a',
	hat: 'straw' as const,
	mustache: true,
	hair: '#2a1a10',
};
export const OBRERO_1 = {
	shirt: '#2e8b57',
	pants: '#3d3d46',
	skin: '#8d5a3b',
	hat: 'cap' as const,
	capColor: '#f2c14e',
	hair: '#1b120c',
};
export const OBRERO_2 = {
	shirt: '#f0e6d2',
	pants: '#2b5c9e',
	skin: '#c48a62',
	hat: 'cap' as const,
	capColor: '#e74c3c',
	hair: '#3a2416',
	overalls: true,
};

/** Camina de ida y vuelta entre A y B, con pausas en los extremos. */
export function walkBetween(frame: number, a: [number, number], b: [number, number], speed = 0.04, pause = 30, offset = 0) {
	const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
	const walkF = len / speed;
	const cycle = 2 * (walkF + pause);
	const t = (((frame + offset) % cycle) + cycle) % cycle;
	let d: number;
	let dir: 1 | -1;
	let moving = true;
	if (t < walkF) {
		d = t * speed;
		dir = 1;
	} else if (t < walkF + pause) {
		d = len;
		dir = 1;
		moving = false;
	} else if (t < 2 * walkF + pause) {
		d = len - (t - walkF - pause) * speed;
		dir = -1;
	} else {
		d = 0;
		dir = -1;
		moving = false;
	}
	const u = d / len;
	const x = a[0] + (b[0] - a[0]) * u;
	const z = a[1] + (b[1] - a[1]) * u;
	const ang = Math.atan2(b[0] - a[0], b[1] - a[1]);
	return {x, z, rotY: dir === 1 ? ang : ang + Math.PI, phase: (frame + offset) * speed * 4.6, walking: moving ? 1 : 0, dir};
}

/** Vida de la granja vista desde el exterior (gallinas, cerdos y trabajadores). */
export const FarmLife: React.FC<{frame: number; workers?: boolean}> = ({frame, workers = true}) => {
	const w1 = walkBetween(frame, [-12.5, 2.2], [-2.2, 6], 0.035, 40, 60);
	const w2 = walkBetween(frame, [2.2, 1.2], [11, 1.2], 0.03, 50, 0);
	const carry: Partial<PersonProps> = {rightArm: [-0.55, 0.12], leftArm: [-0.55, 0.12], rightElbow: -1.0, leftElbow: -1.0};
	return (
		<group>
			<Flock frame={frame} count={16} bounds={{x: [-10.3, -6.4], z: [-17.6, -4.4]}} seed={3} />
			<Flock frame={frame + 400} count={6} bounds={{x: [-14, -11.5], z: [1.2, 4]}} seed={8} />
			<Herd frame={frame} count={4} bounds={{x: [9.6, 17.4], z: [4.6, 10.4]}} seed={4} />
			{workers && (
				<>
					<Person
						frame={frame}
						{...OBRERO_1}
						position={[w1.x, 0, w1.z]}
						rotY={w1.rotY}
						phase={w1.phase}
						walking={w1.walking}
						seed={2}
						{...carry}
						front={<EggTray position={[0, 1.08, 0.5]} stacked={2} />}
					/>
					<Person
						frame={frame}
						{...OBRERO_2}
						position={[w2.x, 0, w2.z]}
						rotY={w2.rotY}
						phase={w2.phase}
						walking={w2.walking}
						seed={5}
						rightArm={[-0.5, 0.05]}
						leftArm={[-0.5, 0.05]}
					/>
					<Wheelbarrow
						position={[w2.x + Math.sin(w2.rotY) * 1.15, 0, w2.z + Math.cos(w2.rotY) * 1.15]}
						rotY={w2.rotY}
						tilt={-0.12}
					/>
				</>
			)}
		</group>
	);
};
