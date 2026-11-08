import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {camPath, ip, V3} from '../lib/anim';
import {Mat, Person, Pig, wander} from '../three/Characters';
import {CameraRig, Stage} from '../three/World';
import {MIGUEL, OBRERO_2} from './common';

const PI = Math.PI;
const PENS = [-3.4, 0, 3.4];

const Rail: React.FC<{from: V3; to: V3; r?: number}> = ({from, to, r = 0.04}) => {
	const len = Math.hypot(to[0] - from[0], to[1] - from[1], to[2] - from[2]);
	const mid: V3 = [(from[0] + to[0]) / 2, (from[1] + to[1]) / 2, (from[2] + to[2]) / 2];
	const horizontalX = Math.abs(to[0] - from[0]) > 0.01;
	const horizontalZ = Math.abs(to[2] - from[2]) > 0.01;
	const rot: V3 = horizontalX ? [0, 0, PI / 2] : horizontalZ ? [PI / 2, 0, 0] : [0, 0, 0];
	return (
		<mesh position={mid} rotation={rot} castShadow>
			<cylinderGeometry args={[r, r, len, 8]} />
			<meshStandardMaterial color="#c3ccd3" metalness={0.6} roughness={0.3} />
		</mesh>
	);
};

const MaternityRoom: React.FC<{frame: number}> = ({frame}) => (
	<group>
		<mesh rotation={[-PI / 2, 0, 0]} receiveShadow>
			<planeGeometry args={[30, 20]} />
			<Mat color="#d3dcdf" rough={0.6} />
		</mesh>
		{/* zona de cada corral con piso distinto */}
		{PENS.map((x) => (
			<mesh key={x} rotation={[-PI / 2, 0, 0]} position={[x, 0.005, -1.9]} receiveShadow>
				<planeGeometry args={[3.3, 3.8]} />
				<Mat color="#c4ced2" rough={0.7} />
			</mesh>
		))}
		{/* pared del fondo con ventanas */}
		<mesh position={[0, 1.7, -3.95]} receiveShadow>
			<boxGeometry args={[30, 3.4, 0.2]} />
			<Mat color="#f2ead6" />
		</mesh>
		<mesh position={[0, 0.5, -3.83]}>
			<boxGeometry args={[30, 1.0, 0.05]} />
			<Mat color="#7fb2a3" />
		</mesh>
		{[-6.8, -3.4, 0, 3.4, 6.8].map((x) => (
			<group key={x} position={[x, 2.4, -3.83]}>
				<mesh>
					<boxGeometry args={[1.6, 0.9, 0.05]} />
					<Mat color="#ffffff" />
				</mesh>
				<mesh position={[0, 0, 0.03]}>
					<boxGeometry args={[1.45, 0.75, 0.02]} />
					<meshStandardMaterial color="#cfeeff" emissive="#e6f6ff" emissiveIntensity={0.9} />
				</mesh>
			</group>
		))}
		{/* vigas */}
		{[-6, -3, 0, 3, 6].map((x) => (
			<mesh key={x} position={[x, 3.4, 0]}>
				<boxGeometry args={[0.15, 0.15, 8]} />
				<Mat color="#9a8a76" />
			</mesh>
		))}
		<mesh position={[0, 3.55, 0]}>
			<boxGeometry args={[30, 0.05, 8]} />
			<Mat color="#e9e2d2" />
		</mesh>
		{/* barandas: frente y divisiones */}
		{[-5.1, -1.7, 1.7, 5.1].map((x) => (
			<group key={x}>
				{[0.35, 0.75].map((y) => (
					<Rail key={y} from={[x, y, -3.8]} to={[x, y, 0]} />
				))}
				<Rail from={[x, 0, 0]} to={[x, 0.95, 0]} r={0.05} />
			</group>
		))}
		{[0.35, 0.75].map((y) => (
			<Rail key={y} from={[-5.1, y, 0]} to={[5.1, y, 0]} />
		))}
		{/* comederos y lámparas de calor */}
		{PENS.map((x) => (
			<group key={x}>
				<mesh position={[x - 1.2, 0.2, -0.35]} castShadow>
					<boxGeometry args={[0.6, 0.35, 0.45]} />
					<meshStandardMaterial color="#b8c2c9" metalness={0.5} roughness={0.35} />
				</mesh>
				<group position={[x + 1.05, 1.5, -0.7]}>
					<mesh position={[0, 1.0, 0]}>
						<cylinderGeometry args={[0.01, 0.01, 2, 4]} />
						<Mat color="#555" />
					</mesh>
					<mesh rotation={[PI, 0, 0]}>
						<coneGeometry args={[0.28, 0.3, 18, 1, true]} />
						<meshStandardMaterial color="#c0392b" side={2} />
					</mesh>
					<mesh position={[0, -0.08, 0]}>
						<sphereGeometry args={[0.1, 12, 10]} />
						<meshStandardMaterial color="#ffb070" emissive="#ff7a2a" emissiveIntensity={2.5 + Math.sin(frame / 6 + x) * 0.2} />
					</mesh>
					<pointLight position={[0, -0.3, 0]} intensity={5} distance={4} color="#ff9a4a" />
				</group>
				{/* mantita de calor en el piso */}
				<mesh rotation={[-PI / 2, 0, 0]} position={[x + 1.05, 0.012, -0.7]}>
					<circleGeometry args={[0.6, 24]} />
					<meshStandardMaterial color="#ffd8a8" transparent opacity={0.45} />
				</mesh>
			</group>
		))}
	</group>
);

/** Cerda echada con lechones mamando. */
const SowWithLitter: React.FC<{x: number; frame: number; seed: number; litter: number}> = ({x, frame, seed, litter}) => {
	const phi = PI / 2 - 0.12;
	return (
		<group position={[x, 0, -2.2]}>
			<group rotation={[0, -PI / 2, 0]}>
				<group position={[0.58 * Math.sin(phi) + 0.0, 0.4 - 0.58 * Math.cos(phi) - 0.02, 0]}>
					<Pig position={[0, 0, 0]} lying frame={frame} seed={seed} scale={1.3} color="#f2a0a7" />
				</group>
			</group>
			{Array.from({length: litter}).map((_, i) => {
				const px = -0.75 + (i * 1.35) / Math.max(1, litter - 1);
				const nurse = Math.sin(frame * 0.5 + i * 1.3) * 0.5 + 0.5;
				return (
					<Pig
						key={i}
						position={[px, 0, 0.62 + nurse * 0.03]}
						rotY={PI + Math.sin(frame / 25 + i) * 0.12}
						scale={0.3}
						frame={frame}
						seed={seed * 10 + i}
						eat={0.25 + nurse * 0.2}
						color={i % 3 === 0 ? '#f7b9bd' : '#f4a7ac'}
					/>
				);
			})}
		</group>
	);
};

/** ESCENA 3 — Las cerdas reproductoras */
export const Scene3: React.FC<{duration: number}> = ({duration}) => {
	const f = useCurrentFrame();
	const enterEnd = 140;
	const mx = ip(f, [0, enterEnd], [-9.2, -3.4], (t) => t);
	const walking = ip(f, [enterEnd - 10, enterEnd], [1, 0]);
	const turn = ip(f, [enterEnd - 5, enterEnd + 20], [PI / 2, PI - 0.4]);
	const point = ip(f, [175, 195, 250, 270], [0, 1, 1, 0]);
	const pourT = ip(f, [90, 120, 200, 225], [0, 1, 1, 0]);

	const cam = camPath(
		f,
		0,
		duration,
		[
			[2.9, 1.65, 4.3],
			[1.8, 1.55, 4.1],
			[0.4, 1.4, 3.8],
			[0.1, 1.2, 3.3],
		],
		[
			[-6, 1.25, 1.4],
			[-4.5, 1.05, 0.8],
			[-1.6, 0.6, -0.9],
			[-0.3, 0.35, -1.8],
		],
	);
	// lechones que deambulan
	const roamers = [0, 1, 2, 3, 4].map((i) => {
		const pen = PENS[i % 3];
		const w = wander(700 + i * 13, f, {x: [pen - 1.3, pen + 1.4], z: [-1.0, -0.3]}, 1.6);
		return {w, i};
	});
	return (
		<AbsoluteFill>
			<Stage>
				<CameraRig pos={cam.pos} look={cam.look} fov={40} />
				<color attach="background" args={['#e9f3f6']} />
				<hemisphereLight args={['#ffffff', '#b9c4c8', 1.15]} />
				<ambientLight intensity={0.3} />
				<directionalLight
					position={[-4, 9, 7]}
					intensity={2.0}
					color="#fff4e0"
					castShadow
					shadow-mapSize-width={2048}
					shadow-mapSize-height={2048}
					shadow-camera-left={-10}
					shadow-camera-right={10}
					shadow-camera-top={10}
					shadow-camera-bottom={-10}
					shadow-bias={-0.0005}
				>
					<object3D attach="target" position={[0, 0, -1]} />
				</directionalLight>
				<MaternityRoom frame={f} />
				{PENS.map((x, i) => (
					<SowWithLitter key={x} x={x} frame={f} seed={i + 1} litter={[6, 7, 5][i]} />
				))}
				{roamers.map(({w, i}) => (
					<Pig
						key={i}
						position={[w.x, 0, w.z]}
						rotY={w.rotY}
						scale={0.3}
						frame={f}
						seed={60 + i}
						step={f * 0.6 + i}
						walking={1}
					/>
				))}
				{/* Miguel entra y observa */}
				<Person
					frame={f}
					{...MIGUEL}
					position={[mx, 0, 1.9]}
					rotY={turn}
					phase={(mx + 9.2) * 4.8}
					walking={walking}
					headYaw={ip(f, [40, 80, 120], [0, -0.5, -0.2])}
					headPitch={ip(f, [enterEnd, enterEnd + 30], [0, 0.18])}
					smile={0.8}
					rightArm={point > 0 ? [-1.25 * point, 0.15] : undefined}
					rightElbow={point > 0 ? -0.1 : undefined}
				/>
				{/* trabajador alimentando a una cerda */}
				<Person
					frame={f}
					{...OBRERO_2}
					position={[2.2, 0, 0.75]}
					rotY={PI + 0.1}
					seed={9}
					lean={0.1 + pourT * 0.1}
					headPitch={0.3}
					rightArm={[-0.8 - pourT * 0.4, 0.15]}
					rightElbow={-0.4}
					leftArm={[-0.2, 0.1]}
					rightHand={
						<group rotation={[1.2 + pourT * 1.0, 0, 0]} position={[0, -0.08, 0.05]}>
							<mesh castShadow>
								<cylinderGeometry args={[0.16, 0.12, 0.28, 16, 1, true]} />
								<meshStandardMaterial color="#f2c14e" side={2} />
							</mesh>
							<mesh position={[0, -0.13, 0]}>
								<cylinderGeometry args={[0.12, 0.12, 0.01, 16]} />
								<meshStandardMaterial color="#f2c14e" />
							</mesh>
						</group>
					}
				/>
				{/* alimento cayendo */}
				{pourT > 0.6 &&
					Array.from({length: 10}).map((_, i) => {
						const t = ((f * 0.06 + i / 10) % 1);
						return (
							<mesh key={i} position={[2.2 + 0.05 * Math.sin(i), 1.05 - t * 0.85, 0.1 - t * 0.3]}>
								<sphereGeometry args={[0.025, 6, 5]} />
								<Mat color="#a87b45" />
							</mesh>
						);
					})}
				<mesh position={[2.2, 0.38, -0.35]}>
					<boxGeometry args={[0.5, 0.02, 0.35]} />
					<Mat color="#a87b45" />
				</mesh>
			</Stage>
		</AbsoluteFill>
	);
};
