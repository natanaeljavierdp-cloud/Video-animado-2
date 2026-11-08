import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {camPath, easeOut, ip} from '../lib/anim';
import {Mat, Person, Pig, wander} from '../three/Characters';
import {CameraRig, Stage} from '../three/World';
import {OBRERO_1} from './common';

const PI = Math.PI;

const FatteningPen: React.FC = () => (
	<group>
		<mesh rotation={[-PI / 2, 0, 0]} receiveShadow>
			<planeGeometry args={[40, 30]} />
			<Mat color="#cbc5b6" rough={0.9} />
		</mesh>
		{/* piso ranurado del corral */}
		{Array.from({length: 26}).map((_, i) => (
			<mesh key={i} position={[-7 + i * 0.55, 0.004, -2]} rotation={[-PI / 2, 0, 0]}>
				<planeGeometry args={[0.06, 8]} />
				<Mat color="#b4ad9c" />
			</mesh>
		))}
		{/* muros bajos */}
		<mesh position={[0, 0.6, -6.1]} castShadow receiveShadow>
			<boxGeometry args={[14.4, 1.2, 0.2]} />
			<Mat color="#efe6cf" />
		</mesh>
		{[1, -1].map((s) => (
			<mesh key={s} position={[7.2 * s, 0.6, -2]} castShadow receiveShadow>
				<boxGeometry args={[0.2, 1.2, 8.2]} />
				<Mat color="#efe6cf" />
			</mesh>
		))}
		{/* fondo del galpón */}
		<mesh position={[0, 2.5, -9]}>
			<boxGeometry args={[30, 5, 0.2]} />
			<Mat color="#f4ecd8" />
		</mesh>
		{[-8, -4, 0, 4, 8].map((x) => (
			<group key={x}>
				<mesh position={[x, 2, -8.88]}>
					<boxGeometry args={[2.4, 1.4, 0.05]} />
					<meshStandardMaterial color="#d8f0ff" emissive="#eaf7ff" emissiveIntensity={0.9} />
				</mesh>
				<mesh position={[x, 4.2, -3]}>
					<boxGeometry args={[0.18, 0.18, 14]} />
					<Mat color="#9a8a76" />
				</mesh>
			</group>
		))}
		<mesh position={[0, 4.4, -3]}>
			<boxGeometry args={[30, 0.06, 14]} />
			<Mat color="#7d8fa3" />
		</mesh>
		{/* baranda frontal */}
		{[0.45, 0.95].map((y) => (
			<mesh key={y} position={[0, y, 2.2]} rotation={[0, 0, PI / 2]}>
				<cylinderGeometry args={[0.045, 0.045, 14.4, 8]} />
				<meshStandardMaterial color="#c3ccd3" metalness={0.6} roughness={0.3} />
			</mesh>
		))}
		{[-7.1, -4.7, -2.3, 0, 2.3, 4.7, 7.1].map((x) => (
			<mesh key={x} position={[x, 0.55, 2.2]}>
				<cylinderGeometry args={[0.05, 0.05, 1.1, 8]} />
				<meshStandardMaterial color="#c3ccd3" metalness={0.6} roughness={0.3} />
			</mesh>
		))}
		{/* comedero largo */}
		<mesh position={[0, 0.2, 1.75]} castShadow receiveShadow>
			<boxGeometry args={[12, 0.4, 0.6]} />
			<meshStandardMaterial color="#9fa9b0" metalness={0.35} roughness={0.45} />
		</mesh>
		<mesh position={[0, 0.41, 1.75]}>
			<boxGeometry args={[11.8, 0.02, 0.48]} />
			<Mat color="#a87b45" rough={1} />
		</mesh>
	</group>
);

/** ESCENA 4 — El engorde de cerdos */
export const Scene4: React.FC<{duration: number}> = ({duration}) => {
	const f = useCurrentFrame();
	// crecimiento progresivo (time-lapse)
	const g = ip(f, [40, duration - 40], [0, 1]);
	const size = 0.58 + g * 0.6;
	const cam = camPath(
		f,
		0,
		duration,
		[
			[5.5, 2.2, 8.5],
			[3.0, 2.6, 9.0],
			[0.0, 3.2, 10.0],
			[-1.5, 3.8, 11.2],
		],
		[
			[1.2, 0.6, 0],
			[0.5, 0.7, -0.5],
			[0, 0.8, -1.5],
			[-0.5, 0.8, -1.8],
		],
	);
	// trabajador que reparte alimento a lo largo del comedero
	const wx = ip(f, [0, duration], [-4.5, 4.5], (t) => t);
	const toss = Math.max(0, Math.sin(f * 0.16));
	const eaters = [-4.2, -2.6, -1.0, 0.6, 2.2, 3.8];
	return (
		<AbsoluteFill>
			<Stage>
				<CameraRig pos={cam.pos} look={cam.look} fov={40} />
				<color attach="background" args={['#e8f1f4']} />
				<hemisphereLight args={['#ffffff', '#bdb6a6', 1.15]} />
				<ambientLight intensity={0.3} />
				<directionalLight
					position={[6, 10, 8]}
					intensity={2.2}
					color="#fff2dc"
					castShadow
					shadow-mapSize-width={2048}
					shadow-mapSize-height={2048}
					shadow-camera-left={-12}
					shadow-camera-right={12}
					shadow-camera-top={12}
					shadow-camera-bottom={-12}
					shadow-bias={-0.0005}
				>
					<object3D attach="target" position={[0, 0, -2]} />
				</directionalLight>
				<FatteningPen />
				{/* cerdos comiendo de frente a la cámara */}
				{eaters.map((x, i) => (
					<Pig
						key={i}
						position={[x, 0, 0.95 - size * 0.35]}
						rotY={Math.sin(i * 3) * 0.12}
						scale={size * (0.95 + (i % 3) * 0.05)}
						frame={f}
						seed={i}
						eat={Math.max(0, Math.sin(f * 0.2 + i * 1.3)) * 0.6 + 0.2}
					/>
				))}
				{/* cerdos caminando dentro del corral */}
				{Array.from({length: 6}).map((_, i) => {
					const w = wander(500 + i * 41, f, {x: [-6, 6], z: [-5.2, -1.6]}, 0.7);
					return (
						<Pig
							key={`w${i}`}
							position={[w.x, 0, w.z]}
							rotY={w.rotY}
							scale={size * (0.92 + (i % 3) * 0.06)}
							frame={f}
							seed={20 + i}
							step={f * 0.35 + i}
							walking={Math.min(1, w.speed * 50)}
						/>
					);
				})}
				{/* trabajador repartiendo alimento */}
				<Person
					frame={f}
					{...OBRERO_1}
					position={[wx, 0, 2.95]}
					rotY={PI / 2 - 0.5}
					phase={f * 0.2}
					walking={0.8}
					seed={4}
					headYaw={-0.6}
					rightArm={[-0.6 - toss * 0.7, 0.2]}
					rightElbow={-0.3}
					leftArm={[-0.25, 0.18]}
					leftElbow={-0.7}
					leftHand={
						<mesh position={[0, -0.1, 0.05]}>
							<cylinderGeometry args={[0.17, 0.13, 0.3, 14]} />
							<meshStandardMaterial color="#3b82c4" />
						</mesh>
					}
				/>
				{Array.from({length: 8}).map((_, i) => {
					const t = (f * 0.05 + i / 8) % 1;
					return (
						<mesh key={i} position={[wx - 0.3 + t * 0.4, 1.0 - t * 0.6, 2.6 - t * 0.85]}>
							<sphereGeometry args={[0.025, 6, 5]} />
							<Mat color="#a87b45" />
						</mesh>
					);
				})}
			</Stage>
			<GrowthOverlay progress={g} frame={f} />
		</AbsoluteFill>
	);
};

const GrowthOverlay: React.FC<{progress: number; frame: number}> = ({progress, frame}) => {
	const appear = ip(frame, [20, 40], [0, 1], easeOut);
	const stages = ['Lechón', 'Crecimiento', 'Finalización'];
	return (
		<AbsoluteFill style={{alignItems: 'flex-end', justifyContent: 'flex-start', padding: '70px 80px'}}>
			<div
				style={{
					opacity: appear,
					transform: `translateX(${(1 - appear) * 40}px)`,
					width: 560,
					padding: '24px 30px',
					borderRadius: 20,
					background: 'rgba(255,255,255,0.88)',
					boxShadow: '0 10px 30px rgba(0,0,0,0.25)',
					color: '#24402a',
				}}
			>
				<div style={{fontSize: 30, fontWeight: 800, letterSpacing: 1}}>CRECIMIENTO DEL CERDO</div>
				<div style={{position: 'relative', height: 26, marginTop: 18, borderRadius: 13, background: '#e3e8e0', overflow: 'hidden'}}>
					<div
						style={{
							width: `${progress * 100}%`,
							height: '100%',
							borderRadius: 13,
							background: 'linear-gradient(90deg, #f7b2b7, #e8707f)',
						}}
					/>
				</div>
				<div style={{display: 'flex', justifyContent: 'space-between', marginTop: 12, fontSize: 22, fontWeight: 600}}>
					{stages.map((s, i) => (
						<span key={s} style={{opacity: progress >= i / 2 - 0.02 ? 1 : 0.35}}>
							{s}
						</span>
					))}
				</div>
				<div style={{marginTop: 14, fontSize: 26, fontWeight: 700, color: '#c0392b', opacity: ip(progress, [0.85, 1], [0, 1])}}>
					Meta de venta: ≈ 100 kg por cerdo
				</div>
			</div>
		</AbsoluteFill>
	);
};
