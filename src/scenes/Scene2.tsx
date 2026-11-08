import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {camPath, ip, V3} from '../lib/anim';
import {Chicken, Egg, EggTray, Flock, Mat, Person} from '../three/Characters';
import {CameraRig, Farm, Stage, SunLights, Truck} from '../three/World';
import {FarmLife, OBRERO_1, OBRERO_2, walkBetween} from './common';

const PI = Math.PI;
const NEST_Z = [-9.6, -8.2, -6.8, -5.4, -4.0, -2.6, -1.2];

/** Interior del gallinero (coordenadas locales). */
const CoopInterior: React.FC<{frame: number}> = ({frame}) => (
	<group>
		{/* piso con cama de paja */}
		<mesh rotation={[-PI / 2, 0, 0]} position={[0, 0, -4]} receiveShadow>
			<planeGeometry args={[10, 20]} />
			<Mat color="#e4cd8e" rough={1} />
		</mesh>
		{Array.from({length: 40}).map((_, i) => (
			<mesh key={i} rotation={[-PI / 2, 0, i]} position={[-4.5 + ((i * 3.7) % 9), 0.005, -13 + ((i * 5.3) % 17)]} receiveShadow>
				<circleGeometry args={[0.5 + (i % 3) * 0.3, 10]} />
				<Mat color={i % 2 ? '#d9bd73' : '#ecd9a2'} rough={1} />
			</mesh>
		))}
		{/* fondo */}
		<mesh position={[0, 1.6, -14]} receiveShadow>
			<boxGeometry args={[10, 3.2, 0.2]} />
			<Mat color="#f4ead2" />
		</mesh>
		{/* paredes laterales: muro bajo + ventanales con malla */}
		{[1, -1].map((s) => (
			<group key={s} position={[5 * s, 0, -4]}>
				<mesh position={[0, 0.5, 0]} receiveShadow castShadow>
					<boxGeometry args={[0.2, 1, 20]} />
					<Mat color="#f4ead2" />
				</mesh>
				<mesh position={[0.15 * s, 1.95, 0]}>
					<boxGeometry args={[0.05, 1.9, 20]} />
					<meshStandardMaterial color="#d7f0ff" emissive="#eaf7ff" emissiveIntensity={0.9} />
				</mesh>
				{Array.from({length: 7}).map((_, i) => (
					<mesh key={i} position={[0, 1.6, -9.5 + i * 3.2]} castShadow>
						<boxGeometry args={[0.24, 3.2, 0.24]} />
						<Mat color="#e8dec4" />
					</mesh>
				))}
				{/* malla */}
				{Array.from({length: 40}).map((_, i) => (
					<mesh key={`m${i}`} position={[-0.02 * s, 1.95, -13.8 + i * 0.5]}>
						<boxGeometry args={[0.01, 1.9, 0.015]} />
						<Mat color="#8b949a" />
					</mesh>
				))}
			</group>
		))}
		{/* techo interior y vigas */}
		{[1, -1].map((s) => (
			<mesh key={s} position={[2.6 * s, 3.65, -4]} rotation={[0, 0, -0.32 * s]}>
				<boxGeometry args={[5.8, 0.08, 20]} />
				<Mat color="#a4523c" />
			</mesh>
		))}
		{Array.from({length: 7}).map((_, i) => (
			<mesh key={i} position={[0, 3.15, -12.5 + i * 3.2]}>
				<boxGeometry args={[10, 0.14, 0.14]} />
				<Mat color="#8a6a4a" />
			</mesh>
		))}
		{/* lámparas */}
		{[-9, -3, 3].map((z) => (
			<group key={z} position={[0, 2.7, z]}>
				<mesh>
					<coneGeometry args={[0.25, 0.2, 16, 1, true]} />
					<meshStandardMaterial color="#e8e8e8" side={2} />
				</mesh>
				<mesh position={[0, -0.05, 0]}>
					<sphereGeometry args={[0.09, 10, 8]} />
					<meshStandardMaterial color="#fff6d8" emissive="#fff1c0" emissiveIntensity={2} />
				</mesh>
			</group>
		))}
		{/* nidales en la pared izquierda */}
		<group position={[-4.4, 0, 0]}>
			<mesh position={[0, 0.3, -5.4]} castShadow receiveShadow>
				<boxGeometry args={[0.9, 0.6, 9.8]} />
				<Mat color="#9c6b3e" />
			</mesh>
			<mesh position={[0, 1.42, -5.4]} castShadow>
				<boxGeometry args={[1.0, 0.08, 10]} />
				<Mat color="#8a5a32" />
			</mesh>
			{NEST_Z.map((z) => (
				<group key={z} position={[0, 0.6, z]}>
					{[1, -1].map((s) => (
						<mesh key={s} position={[0, 0.4, 0.68 * s]} castShadow>
							<boxGeometry args={[0.9, 0.8, 0.06]} />
							<Mat color="#b07b46" />
						</mesh>
					))}
					<mesh position={[0, 0.06, 0]}>
						<cylinderGeometry args={[0.45, 0.4, 0.12, 14]} />
						<Mat color="#e6c56b" rough={1} />
					</mesh>
				</group>
			))}
			<mesh position={[0.48, 0.66, -5.4]}>
				<boxGeometry args={[0.08, 0.12, 9.8]} />
				<Mat color="#7a4e2a" />
			</mesh>
		</group>
		{/* comederos lineales */}
		{[-0.4, 2.6].map((x) => (
			<group key={x} position={[x, 0, -5.5]}>
				<mesh position={[0, 0.16, 0]} castShadow receiveShadow>
					<boxGeometry args={[0.45, 0.22, 9]} />
					<meshStandardMaterial color="#c9ced3" metalness={0.4} roughness={0.4} />
				</mesh>
				<mesh position={[0, 0.27, 0]}>
					<boxGeometry args={[0.36, 0.02, 8.8]} />
					<Mat color="#b88a4a" rough={1} />
				</mesh>
			</group>
		))}
		{/* bebederos colgantes */}
		{[-10, -6, -2].map((z) => (
			<group key={z} position={[1.1, 0, z]}>
				<mesh position={[0, 1.2, 0]}>
					<cylinderGeometry args={[0.01, 0.01, 2.2, 4]} />
					<Mat color="#555" />
				</mesh>
				<mesh position={[0, 0.2, 0]}>
					<cylinderGeometry args={[0.3, 0.2, 0.12, 16]} />
					<meshStandardMaterial color="#e74c3c" roughness={0.4} />
				</mesh>
			</group>
		))}
	</group>
);

/** ESCENA 2 — Las gallinas ponedoras */
export const Scene2: React.FC<{duration: number}> = ({duration}) => {
	const f = useCurrentFrame();
	const truckStart = duration - 112;
	const interior = f < truckStart + 14;

	// --- interior
	const cam = camPath(
		f,
		0,
		truckStart,
		[
			[0.8, 2.2, 7.5],
			[0.9, 1.7, 3.0],
			[0.6, 1.55, 0.9],
			[-0.6, 1.5, -0.6],
		],
		[
			[-0.5, 0.8, -6],
			[-2.0, 0.6, -4.5],
			[-4.0, 0.8, -2.2],
			[-4.2, 1.0, -5.5],
		],
	);
	// trabajador que recoge huevos
	const cyc = (f % 48) / 48;
	const reach = Math.sin(cyc * PI * 2) * 0.5 + 0.5;
	const eggT = cyc < 0.5 ? null : (cyc - 0.5) / 0.5;
	const collected = Math.min(19, 8 + Math.floor(f / 48));
	// trabajador que lleva bandejas hacia la puerta
	const w2 = walkBetween(f, [1.2, -11], [1.2, 1.8], 0.03, 25, 90);
	// gallina que pone un huevo (nidal más cercano)
	const rise = ip(f, [120, 150], [0, 1]);
	const eggPop = ip(f, [140, 160], [0, 1]);

	// --- exterior: camión
	const tf = f - truckStart;
	const tz = ip(tf, [0, 112], [4, 30], (t) => t * t * 0.4 + t * 0.6);
	const truckCam = camPath(tf, 0, 112, [[6.5, 1.6, 16], [6, 2.4, 21], [5.5, 3.6, 26]], [[0.8, 1.4, 6], [0.8, 1.6, 14], [0.8, 1.8, 26]]);

	const fade = ip(f, [truckStart, truckStart + 14], [0, 1]);

	return (
		<AbsoluteFill>
			{interior && (
				<Stage>
					<CameraRig pos={cam.pos} look={cam.look} fov={42} />
					<hemisphereLight args={['#fff7e6', '#c9a15a', 1.0]} />
					<ambientLight intensity={0.35} />
					<directionalLight
						position={[14, 12, 4]}
						intensity={2.4}
						color="#fff0d6"
						castShadow
						shadow-mapSize-width={2048}
						shadow-mapSize-height={2048}
						shadow-camera-left={-14}
						shadow-camera-right={14}
						shadow-camera-top={14}
						shadow-camera-bottom={-14}
						shadow-bias={-0.0005}
					>
						<object3D attach="target" position={[0, 0, -4]} />
					</directionalLight>
					<pointLight position={[0, 2.5, -3]} intensity={6} distance={12} color="#ffe2a8" />
					<pointLight position={[0, 2.5, -9]} intensity={6} distance={12} color="#ffe2a8" />
					<color attach="background" args={['#dcefff']} />
					<CoopInterior frame={f} />
					<Flock frame={f} count={30} bounds={{x: [-3.4, 4.4], z: [-12.5, 0.2]}} seed={21} whiteRatio={0.12} />
					{/* gallinas comiendo en el comedero */}
					{Array.from({length: 8}).map((_, i) => (
						<Chicken
							key={`c${i}`}
							frame={f}
							seed={i + 50}
							position={[-0.4 + (i % 2 ? 0.45 : -0.45), 0, -9 + i * 1.0]}
							rotY={i % 2 ? -PI / 2 : PI / 2}
							peck={Math.max(0, Math.sin(f * 0.25 + i * 1.7)) ** 3}
						/>
					))}
					{/* gallinas echadas en los nidales */}
					{NEST_Z.map((z, i) =>
						i === 6 ? null : i % 2 === 0 ? (
							<Chicken key={`n${i}`} frame={f} seed={i + 80} position={[-4.4, 0.62, z]} rotY={PI / 2} sitting />
						) : (
							<group key={`e${i}`}>
								<Egg position={[-4.5, 0.74, z + 0.1]} />
								<Egg position={[-4.3, 0.74, z - 0.12]} color="#e8cfa8" />
							</group>
						),
					)}
					{/* la gallina que pone un huevo */}
					<Chicken
						frame={f}
						seed={99}
						position={[-4.3 + rise * 0.55, 0.62 - rise * 0.62 + Math.sin(rise * PI) * 0.35, -1.2 + rise * 0.3]}
						rotY={PI / 2 + rise * 0.6}
						sitting={rise < 0.5}
						flap={Math.sin(rise * PI) * 0.8}
						step={f * 0.4}
					/>
					<Egg position={[-4.4, 0.74, -1.2]} scale={eggPop} />
					{eggPop > 0.9 && f > 150 && f < 200 && (
						<mesh position={[-4.4, 0.9, -1.2]} scale={ip(f, [150, 175], [0.3, 1.4])}>
							<torusGeometry args={[0.18, 0.012, 6, 24]} />
							<meshBasicMaterial color="#fff5c0" transparent opacity={ip(f, [150, 195], [0.9, 0])} />
						</mesh>
					)}
					{/* trabajador recogiendo huevos */}
					<Person
						frame={f}
						{...OBRERO_1}
						position={[-3.15, 0, -5.4]}
						rotY={-PI / 2 + 0.25}
						seed={3}
						lean={0.12}
						headPitch={0.2}
						rightArm={[-0.9 - reach * 0.5, 0.15]}
						rightElbow={-0.3 - (1 - reach) * 0.6}
						leftArm={[-0.5, 0.1]}
						leftElbow={-1.0}
						front={<EggTray position={[-0.12, 1.08, 0.5]} filled={collected} />}
						rightHand={eggT === null ? <Egg position={[0, -0.04, 0.05]} /> : null}
					/>
					{/* trabajador con bandejas */}
					<Person
						frame={f}
						{...OBRERO_2}
						position={[w2.x, 0, w2.z]}
						rotY={w2.rotY}
						phase={w2.phase}
						walking={w2.walking}
						seed={7}
						rightArm={[-0.55, 0.12]}
						leftArm={[-0.55, 0.12]}
						rightElbow={-1.0}
						leftElbow={-1.0}
						front={<EggTray position={[0, 1.08, 0.5]} stacked={3} />}
					/>
				</Stage>
			)}
			{f >= truckStart && (
				<AbsoluteFill style={{opacity: fade}}>
					<Stage>
						<CameraRig pos={truckCam.pos} look={truckCam.look} fov={40} />
						<SunLights size={40} center={[0, 0, 15]} />
						<Farm frame={f + 300}>
							<FarmLife frame={f + 300} />
							<Truck position={[0.8, 0, tz]} wheelRot={tz * 2.2} />
						</Farm>
					</Stage>
				</AbsoluteFill>
			)}
		</AbsoluteFill>
	);
};

export type {V3};
