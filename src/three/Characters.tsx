import React from 'react';
import {rng, V3} from '../lib/anim';

const PI = Math.PI;

type MatProps = {color: string; rough?: number; emissive?: string; ei?: number};
export const Mat: React.FC<MatProps> = ({color, rough = 0.75, emissive, ei = 0}) => (
	<meshStandardMaterial color={color} roughness={rough} metalness={0} emissive={emissive ?? '#000'} emissiveIntensity={ei} />
);

/* ------------------------------------------------------------------ PERSONAS */
export type PersonProps = {
	frame: number;
	position: V3;
	rotY?: number;
	/** fase del ciclo de caminar (radianes) */
	phase?: number;
	/** amplitud del caminar 0..1 */
	walking?: number;
	shirt: string;
	pants: string;
	skin: string;
	hat?: 'straw' | 'cap' | 'none';
	capColor?: string;
	mustache?: boolean;
	hair?: string;
	/** [rotX, rotZ] de cada brazo (rotX negativo = hacia delante) */
	leftArm?: [number, number];
	rightArm?: [number, number];
	leftElbow?: number;
	rightElbow?: number;
	headYaw?: number;
	headPitch?: number;
	lean?: number;
	smile?: number;
	seed?: number;
	rightHand?: React.ReactNode;
	leftHand?: React.ReactNode;
	scale?: number;
	overalls?: boolean;
	/** objeto cargado frente al torso (coordenadas del cuerpo) */
	front?: React.ReactNode;
};

const Arm: React.FC<{
	side: 1 | -1;
	rot: [number, number];
	elbow: number;
	shirt: string;
	skin: string;
	children?: React.ReactNode;
}> = ({side, rot, elbow, shirt, skin, children}) => (
	<group position={[0.3 * side, 1.5, 0]} rotation={[rot[0], 0, rot[1] * side]}>
		<mesh position={[0, -0.16, 0]} castShadow>
			<capsuleGeometry args={[0.085, 0.22, 6, 12]} />
			<Mat color={shirt} />
		</mesh>
		<group position={[0, -0.33, 0]} rotation={[elbow, 0, 0]}>
			<mesh position={[0, -0.13, 0]} castShadow>
				<capsuleGeometry args={[0.07, 0.2, 6, 12]} />
				<Mat color={skin} rough={0.6} />
			</mesh>
			<mesh position={[0, -0.3, 0]} castShadow>
				<sphereGeometry args={[0.085, 14, 12]} />
				<Mat color={skin} rough={0.6} />
			</mesh>
			<group position={[0, -0.36, 0.04]}>{children}</group>
		</group>
	</group>
);

export const Person: React.FC<PersonProps> = (p) => {
	const {
		frame,
		position,
		rotY = 0,
		phase = 0,
		walking = 0,
		shirt,
		pants,
		skin,
		hat = 'none',
		capColor = '#2b5d9b',
		mustache = false,
		hair = '#2a1a10',
		headYaw = 0,
		headPitch = 0,
		lean = 0,
		smile = 0.5,
		seed = 0,
		scale = 1,
		overalls = false,
	} = p;
	const swing = Math.sin(phase) * 0.55 * walking;
	const bob = Math.abs(Math.cos(phase)) * 0.05 * walking;
	const breathe = Math.sin(frame / 22 + seed) * 0.008;
	const blink = (frame + seed * 41) % 115 < 4 ? 0.12 : 1;
	const la = p.leftArm ?? [-swing * 0.9 + 0.05, 0.1];
	const ra = p.rightArm ?? [swing * 0.9 + 0.05, 0.1];
	const le = p.leftElbow ?? -0.15 - Math.max(0, -swing) * 0.4;
	const re = p.rightElbow ?? -0.15 - Math.max(0, swing) * 0.4;

	return (
		<group position={position} rotation={[0, rotY, 0]} scale={scale}>
			<group position={[0, bob, 0]} rotation={[lean, 0, 0]}>
				{/* piernas */}
				{[1, -1].map((s) => (
					<group key={s} position={[0.12 * s, 0.92, 0]} rotation={[s * swing, 0, 0]}>
						<mesh position={[0, -0.4, 0]} castShadow>
							<capsuleGeometry args={[0.105, 0.6, 6, 12]} />
							<Mat color={pants} />
						</mesh>
						<mesh position={[0, -0.84, 0.06]} castShadow>
							<boxGeometry args={[0.19, 0.12, 0.32]} />
							<Mat color="#3b2a1d" rough={0.5} />
						</mesh>
					</group>
				))}
				{/* torso */}
				<group position={[0, 0, 0]} scale={[1, 1 + breathe, 1]}>
					<mesh position={[0, 1.27, 0]} castShadow>
						<capsuleGeometry args={[0.27, 0.42, 8, 18]} />
						<Mat color={overalls ? pants : shirt} />
					</mesh>
					{overalls && (
						<mesh position={[0, 1.45, 0.02]} castShadow>
							<capsuleGeometry args={[0.272, 0.18, 8, 18]} />
							<Mat color={shirt} />
						</mesh>
					)}
					<mesh position={[0, 0.98, 0]}>
						<cylinderGeometry args={[0.255, 0.255, 0.06, 18]} />
						<Mat color="#4a3020" />
					</mesh>
					{/* botones / cuello */}
					<mesh position={[0, 1.62, 0.13]} rotation={[0.4, 0, 0]}>
						<torusGeometry args={[0.12, 0.03, 8, 16, PI]} />
						<Mat color={shirt} />
					</mesh>
				</group>
				{/* brazos */}
				<Arm side={-1} rot={la} elbow={le} shirt={shirt} skin={skin}>
					{p.leftHand}
				</Arm>
				<Arm side={1} rot={ra} elbow={re} shirt={shirt} skin={skin}>
					{p.rightHand}
				</Arm>
				{p.front}
				{/* cuello */}
				<mesh position={[0, 1.68, 0]}>
					<cylinderGeometry args={[0.09, 0.1, 0.14, 12]} />
					<Mat color={skin} rough={0.6} />
				</mesh>
				{/* cabeza */}
				<group position={[0, 1.95, 0]} rotation={[headPitch, headYaw, 0]}>
					<mesh castShadow scale={[1, 1.06, 1]}>
						<sphereGeometry args={[0.27, 28, 22]} />
						<Mat color={skin} rough={0.55} />
					</mesh>
					{/* orejas */}
					{[1, -1].map((s) => (
						<mesh key={s} position={[0.26 * s, 0, 0]} scale={[0.5, 1, 0.8]}>
							<sphereGeometry args={[0.07, 12, 10]} />
							<Mat color={skin} rough={0.6} />
						</mesh>
					))}
					{/* pelo */}
					<mesh position={[0, 0.06, -0.04]} scale={[1.03, 0.95, 1.02]}>
						<sphereGeometry args={[0.27, 24, 16, 0, PI * 2, 0, PI * 0.45]} />
						<Mat color={hair} rough={0.9} />
					</mesh>
					{/* ojos */}
					{[1, -1].map((s) => (
						<group key={s} position={[0.095 * s, 0.05, 0.225]} scale={[1, blink, 1]}>
							<mesh scale={[1, 1.15, 0.6]}>
								<sphereGeometry args={[0.062, 16, 14]} />
								<Mat color="#ffffff" rough={0.3} />
							</mesh>
							<mesh position={[0, -0.005, 0.035]}>
								<sphereGeometry args={[0.034, 12, 10]} />
								<Mat color="#2b1a0e" rough={0.2} />
							</mesh>
							<mesh position={[0.012, 0.012, 0.062]}>
								<sphereGeometry args={[0.009, 8, 6]} />
								<Mat color="#ffffff" emissive="#ffffff" ei={0.6} />
							</mesh>
						</group>
					))}
					{/* cejas */}
					{[1, -1].map((s) => (
						<mesh key={s} position={[0.1 * s, 0.135, 0.235]} rotation={[0, 0, -0.12 * s + smile * 0.08 * s]}>
							<capsuleGeometry args={[0.014, 0.07, 4, 8]} />
							<Mat color={hair} />
						</mesh>
					))}
					{/* nariz */}
					<mesh position={[0, -0.03, 0.27]} scale={[1, 0.9, 1]}>
						<sphereGeometry args={[0.055, 14, 12]} />
						<Mat color={skin} rough={0.5} />
					</mesh>
					{mustache && (
						<mesh position={[0, -0.095, 0.245]} rotation={[0, 0, PI / 2]}>
							<capsuleGeometry args={[0.025, 0.13, 6, 10]} />
							<Mat color={hair} rough={0.9} />
						</mesh>
					)}
					{/* boca sonriente */}
					<mesh position={[0, -0.13, 0.23]} rotation={[0.25, 0, PI]}>
						<torusGeometry args={[0.055 + smile * 0.015, 0.013, 6, 14, PI]} />
						<Mat color="#7a2e22" />
					</mesh>
					{/* mejillas */}
					{[1, -1].map((s) => (
						<mesh key={s} position={[0.16 * s, -0.06, 0.2]} scale={[1, 0.7, 0.4]}>
							<sphereGeometry args={[0.045, 10, 8]} />
							<meshStandardMaterial color="#e07a62" transparent opacity={0.35} />
						</mesh>
					))}
					{hat === 'straw' && (
						<group position={[0, 0.17, 0]} rotation={[-0.06, 0, 0]}>
							<mesh castShadow>
								<cylinderGeometry args={[0.5, 0.5, 0.03, 32]} />
								<Mat color="#e2c070" rough={0.95} />
							</mesh>
							<mesh position={[0, 0.12, 0]} castShadow>
								<cylinderGeometry args={[0.22, 0.27, 0.22, 24]} />
								<Mat color="#e8c878" rough={0.95} />
							</mesh>
							<mesh position={[0, 0.04, 0]}>
								<cylinderGeometry args={[0.272, 0.275, 0.06, 24]} />
								<Mat color="#7a3b1e" />
							</mesh>
						</group>
					)}
					{hat === 'cap' && (
						<group position={[0, 0.08, 0]} rotation={[-0.05, 0, 0]}>
							<mesh castShadow scale={[1.06, 0.82, 1.08]}>
								<sphereGeometry args={[0.29, 24, 14, 0, PI * 2, 0, PI / 2]} />
								<Mat color={capColor} />
							</mesh>
							<mesh position={[0, 0.0, 0.31]} scale={[1, 0.15, 1]}>
								<cylinderGeometry args={[0.18, 0.18, 0.1, 20, 1, false, -PI / 2, PI]} />
								<Mat color={capColor} />
							</mesh>
						</group>
					)}
				</group>
			</group>
		</group>
	);
};

/* ------------------------------------------------------------------ HUEVOS */
export const Egg: React.FC<{position?: V3; scale?: number; color?: string}> = ({position = [0, 0, 0], scale = 1, color = '#f1dcc0'}) => (
	<mesh position={position} scale={[scale, scale * 1.28, scale]} castShadow>
		<sphereGeometry args={[0.05, 14, 12]} />
		<Mat color={color} rough={0.45} />
	</mesh>
);

export const EggTray: React.FC<{position?: V3; rotation?: V3; filled?: number; stacked?: number}> = ({
	position = [0, 0, 0],
	rotation = [0, 0, 0],
	filled = 20,
	stacked = 1,
}) => (
	<group position={position} rotation={rotation}>
		{Array.from({length: stacked}).map((_, k) => (
			<group key={k} position={[0, k * 0.1, 0]}>
				<mesh castShadow receiveShadow>
					<boxGeometry args={[0.5, 0.04, 0.42]} />
					<Mat color="#c9b089" rough={1} />
				</mesh>
				{Array.from({length: 20}).map((__, i) =>
					i < (k === stacked - 1 ? filled : 20) ? (
						<Egg key={i} position={[-0.2 + (i % 5) * 0.1, 0.07, -0.15 + Math.floor(i / 5) * 0.1]} color={i % 3 ? '#f1dcc0' : '#e8cfa8'} />
					) : null,
				)}
			</group>
		))}
	</group>
);

/* ------------------------------------------------------------------ GALLINA */
export type ChickenProps = {
	position: V3;
	rotY?: number;
	peck?: number;
	step?: number;
	color?: string;
	scale?: number;
	sitting?: boolean;
	flap?: number;
	frame?: number;
	seed?: number;
};
export const Chicken: React.FC<ChickenProps> = ({
	position,
	rotY = 0,
	peck = 0,
	step = 0,
	color = '#b4612a',
	scale = 1,
	sitting = false,
	flap = 0,
	frame = 0,
	seed = 0,
}) => {
	const neck = color === '#f6f1e6' ? '#ffffff' : '#cf8240';
	const legA = Math.sin(step) * 0.5;
	const blink = (frame + seed * 31) % 90 < 3 ? 0.15 : 1;
	const headBob = Math.sin(step * 2) * 0.02;
	return (
		<group position={position} rotation={[0, rotY, 0]} scale={scale}>
			{!sitting &&
				[1, -1].map((s) => (
					<group key={s} position={[0.06 * s, 0.2, 0]} rotation={[s * legA, 0, 0]}>
						<mesh position={[0, -0.1, 0]}>
							<cylinderGeometry args={[0.017, 0.017, 0.2, 6]} />
							<Mat color="#f2b33d" />
						</mesh>
						<mesh position={[0, -0.195, 0.04]}>
							<boxGeometry args={[0.07, 0.015, 0.1]} />
							<Mat color="#f2b33d" />
						</mesh>
					</group>
				))}
			<group position={[0, sitting ? -0.16 : 0, 0]} rotation={[peck * 0.55, 0, 0]}>
				{/* cuerpo */}
				<mesh position={[0, 0.34, 0]} scale={[1, 0.95, 1.25]} castShadow>
					<sphereGeometry args={[0.2, 20, 16]} />
					<Mat color={color} rough={0.9} />
				</mesh>
				{/* cola */}
				<mesh position={[0, 0.47, -0.22]} rotation={[-0.7, 0, 0]} scale={[0.5, 1, 0.5]} castShadow>
					<coneGeometry args={[0.12, 0.28, 10]} />
					<Mat color={color === '#f6f1e6' ? '#efe8da' : '#6e3415'} rough={0.9} />
				</mesh>
				{/* alas */}
				{[1, -1].map((s) => (
					<mesh
						key={s}
						position={[0.17 * s, 0.36, -0.02]}
						rotation={[0, 0, s * (0.15 + flap * 0.9)]}
						scale={[0.35, 0.7, 1.05]}
						castShadow
					>
						<sphereGeometry args={[0.17, 14, 10]} />
						<Mat color={color === '#f6f1e6' ? '#ece5d6' : '#8f4a1f'} rough={0.9} />
					</mesh>
				))}
				{/* cuello y cabeza */}
				<group position={[0, 0.5 + headBob, 0.17]} rotation={[peck * 0.9, 0, 0]}>
					<mesh position={[0, -0.05, 0]} scale={[1, 1.2, 1]}>
						<sphereGeometry args={[0.1, 14, 12]} />
						<Mat color={neck} rough={0.9} />
					</mesh>
					<mesh position={[0, 0.05, 0.02]}>
						<sphereGeometry args={[0.095, 16, 14]} />
						<Mat color={neck} rough={0.85} />
					</mesh>
					{/* cresta */}
					{[-0.04, 0, 0.04].map((z, i) => (
						<mesh key={i} position={[0, 0.15 - Math.abs(z) * 0.6, z + 0.02]}>
							<sphereGeometry args={[0.038, 10, 8]} />
							<Mat color="#e0262b" rough={0.5} />
						</mesh>
					))}
					{/* pico */}
					<mesh position={[0, 0.04, 0.12]} rotation={[PI / 2, 0, 0]}>
						<coneGeometry args={[0.03, 0.08, 8]} />
						<Mat color="#f2b33d" rough={0.5} />
					</mesh>
					{/* barbilla */}
					<mesh position={[0, -0.03, 0.09]} scale={[0.7, 1.2, 0.7]}>
						<sphereGeometry args={[0.03, 8, 8]} />
						<Mat color="#e0262b" rough={0.5} />
					</mesh>
					{/* ojos */}
					{[1, -1].map((s) => (
						<group key={s} position={[0.07 * s, 0.07, 0.06]} scale={[1, blink, 1]}>
							<mesh>
								<sphereGeometry args={[0.024, 10, 8]} />
								<Mat color="#ffffff" rough={0.3} />
							</mesh>
							<mesh position={[0.008 * s, 0, 0.012]}>
								<sphereGeometry args={[0.015, 8, 8]} />
								<Mat color="#111" rough={0.2} />
							</mesh>
						</group>
					))}
				</group>
			</group>
		</group>
	);
};

/* ------------------------------------------------------------------ CERDO */
export type PigProps = {
	position: V3;
	rotY?: number;
	scale?: number;
	step?: number;
	walking?: number;
	eat?: number;
	lying?: boolean;
	frame?: number;
	seed?: number;
	color?: string;
	headYaw?: number;
};
export const Pig: React.FC<PigProps> = ({
	position,
	rotY = 0,
	scale = 1,
	step = 0,
	walking = 0,
	eat = 0,
	lying = false,
	frame = 0,
	seed = 0,
	color = '#f4a7ac',
	headYaw = 0,
}) => {
	const dark = '#e98b95';
	const leg = Math.sin(step) * 0.45 * walking;
	const breathe = 1 + Math.sin(frame / 18 + seed) * (lying ? 0.03 : 0.012);
	const blink = (frame + seed * 53) % 100 < 4 ? 0.15 : 1;
	const tailWag = Math.sin(frame / 4 + seed) * 0.4;
	const earFlop = Math.sin(frame / 9 + seed * 2) * 0.12;
	const bob = Math.abs(Math.cos(step)) * 0.025 * walking;
	return (
		<group position={position} rotation={[0, rotY, 0]} scale={scale}>
			<group
				rotation={lying ? [0, 0, PI / 2 - 0.12] : [0, 0, 0]}
				position={lying ? [0.18, 0.02, 0] : [0, bob, 0]}
			>
				{/* patas */}
				{[
					[0.2, 0.33, 1],
					[-0.2, 0.33, -1],
					[0.2, -0.33, -1],
					[-0.2, -0.33, 1],
				].map(([x, z, s], i) => (
					<group key={i} position={[x, 0.36, z]} rotation={[s * leg + (lying ? 0.4 : 0), 0, 0]} scale={lying ? [1, 0.65, 1] : 1}>
						<mesh position={[0, -0.17, 0]} castShadow>
							<cylinderGeometry args={[0.085, 0.075, 0.34, 10]} />
							<Mat color={color} rough={0.7} />
						</mesh>
						<mesh position={[0, -0.33, 0]}>
							<cylinderGeometry args={[0.076, 0.08, 0.06, 10]} />
							<Mat color={lying ? "#e3949c" : "#a8686f"} rough={0.6} />
						</mesh>
					</group>
				))}
				{/* cuerpo */}
				<mesh position={[0, 0.58, 0]} scale={[0.9 * breathe, 0.85 * breathe, 1.3]} castShadow receiveShadow>
					<sphereGeometry args={[0.45, 28, 22]} />
					<Mat color={color} rough={0.65} />
				</mesh>
				{/* cola */}
				<mesh position={[0, 0.7, -0.6]} rotation={[0.3, tailWag, 0]}>
					<torusGeometry args={[0.05, 0.018, 6, 14, PI * 1.6]} />
					<Mat color={color} />
				</mesh>
				{/* cabeza */}
				<group position={[0, 0.7, 0.5]} rotation={[eat * 0.6, headYaw, 0]}>
					<mesh position={[0, 0, 0.08]} castShadow>
						<sphereGeometry args={[0.31, 24, 20]} />
						<Mat color={color} rough={0.6} />
					</mesh>
					{/* hocico */}
					<mesh position={[0, -0.05, 0.38]} rotation={[PI / 2, 0, 0]}>
						<cylinderGeometry args={[0.13, 0.14, 0.12, 20]} />
						<Mat color={dark} rough={0.5} />
					</mesh>
					{[1, -1].map((s) => (
						<mesh key={s} position={[0.045 * s, -0.05, 0.445]} scale={[0.7, 1, 0.4]}>
							<sphereGeometry args={[0.028, 8, 8]} />
							<Mat color="#7a3c46" />
						</mesh>
					))}
					{/* orejas */}
					{[1, -1].map((s) => (
						<mesh
							key={s}
							position={[0.19 * s, 0.24, 0.05]}
							rotation={[0.6 + earFlop * s, 0, -0.5 * s]}
							scale={[1, 1, 0.35]}
						>
							<coneGeometry args={[0.11, 0.24, 12]} />
							<Mat color={dark} rough={0.6} />
						</mesh>
					))}
					{/* ojos */}
					{[1, -1].map((s) => (
						<group key={s} position={[0.12 * s, 0.09, 0.32]} scale={[1, blink, 1]}>
							<mesh>
								<sphereGeometry args={[0.045, 12, 10]} />
								<Mat color="#ffffff" rough={0.3} />
							</mesh>
							<mesh position={[0, 0, 0.03]}>
								<sphereGeometry args={[0.026, 10, 8]} />
								<Mat color="#1a1010" rough={0.2} />
							</mesh>
							<mesh position={[0.01, 0.012, 0.05]}>
								<sphereGeometry args={[0.007, 6, 6]} />
								<Mat color="#ffffff" emissive="#fff" ei={0.5} />
							</mesh>
						</group>
					))}
					{/* mejillas */}
					{[1, -1].map((s) => (
						<mesh key={s} position={[0.2 * s, -0.06, 0.26]} scale={[1, 0.7, 0.4]}>
							<sphereGeometry args={[0.05, 10, 8]} />
							<meshStandardMaterial color="#ff7f8a" transparent opacity={0.45} />
						</mesh>
					))}
				</group>
			</group>
		</group>
	);
};

/* ------------------------------------------------------------------ BANDADA / PIARA */

type Bounds = {x: [number, number]; z: [number, number]};

/** Movimiento determinista tipo "deambular" dentro de un rectángulo. */
export function wander(seed: number, frame: number, b: Bounds, speed = 1) {
	const r = rng(seed);
	const cx = b.x[0] + (b.x[1] - b.x[0]) * (0.2 + r() * 0.6);
	const cz = b.z[0] + (b.z[1] - b.z[0]) * (0.2 + r() * 0.6);
	const ax = Math.min(cx - b.x[0], b.x[1] - cx) * (0.4 + r() * 0.5);
	const az = Math.min(cz - b.z[0], b.z[1] - cz) * (0.4 + r() * 0.5);
	const w1 = (0.006 + r() * 0.008) * speed;
	const w2 = (0.005 + r() * 0.009) * speed;
	const p1 = r() * 6.28;
	const p2 = r() * 6.28;
	const t = frame;
	const x = cx + ax * Math.sin(w1 * t + p1);
	const z = cz + az * Math.sin(w2 * t + p2);
	const dx = ax * w1 * Math.cos(w1 * t + p1);
	const dz = az * w2 * Math.cos(w2 * t + p2);
	const v = Math.hypot(dx, dz);
	return {x, z, rotY: Math.atan2(dx, dz), speed: v, r};
}

export const Flock: React.FC<{
	frame: number;
	count: number;
	bounds: Bounds;
	seed?: number;
	y?: number;
	whiteRatio?: number;
}> = ({frame, count, bounds, seed = 1, y = 0, whiteRatio = 0.15}) => (
	<group>
		{Array.from({length: count}).map((_, i) => {
			const w = wander(seed * 1000 + i * 17, frame, bounds, 1);
			const pr = w.r();
			const peckRaw = Math.sin(frame * (0.18 + pr * 0.1) + pr * 20);
			const peckGate = Math.sin(frame * 0.03 + pr * 9) > 0.2 ? 1 : 0;
			const peck = Math.max(0, peckRaw) ** 4 * peckGate;
			const step = frame * w.speed * 22 + pr * 10;
			return (
				<Chicken
					key={i}
					frame={frame}
					seed={i}
					position={[w.x, y, w.z]}
					rotY={w.rotY}
					peck={peck}
					step={step}
					color={w.r() < whiteRatio ? '#f6f1e6' : i % 4 === 0 ? '#a35424' : '#b4612a'}
					scale={0.95 + w.r() * 0.15}
				/>
			);
		})}
	</group>
);

export const Herd: React.FC<{
	frame: number;
	count: number;
	bounds: Bounds;
	seed?: number;
	scale?: [number, number];
	speed?: number;
}> = ({frame, count, bounds, seed = 1, scale = [0.9, 1.1], speed = 0.6}) => (
	<group>
		{Array.from({length: count}).map((_, i) => {
			const w = wander(seed * 977 + i * 31, frame, bounds, speed);
			const pr = w.r();
			return (
				<Pig
					key={i}
					frame={frame}
					seed={i}
					position={[w.x, 0, w.z]}
					rotY={w.rotY}
					step={frame * w.speed * 9 + pr * 5}
					walking={Math.min(1, w.speed * 40)}
					scale={scale[0] + (scale[1] - scale[0]) * w.r()}
					headYaw={Math.sin(frame / 30 + i) * 0.2}
				/>
			);
		})}
	</group>
);
