import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {camPath, easeOut, ip, V3} from '../lib/anim';
import {Person} from '../three/Characters';
import {CameraRig, Farm, Stage, SunLights} from '../three/World';
import {FarmLife, MIGUEL} from './common';

const lerp3 = (a: V3, b: V3, t: number): V3 => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

/** ESCENA 1 — El nacimiento de una idea */
export const Scene1: React.FC<{duration: number}> = ({duration}) => {
	const f = useCurrentFrame();
	const walkEnd = 215;
	// Miguel camina por el camino hacia la granja
	const dist = ip(f, [0, walkEnd], [0, 9.5], (t) => t);
	const mz = 17 - dist;
	const walking = ip(f, [walkEnd - 10, walkEnd], [1, 0]);
	const phase = dist * 4.8;
	const headYaw = ip(f, [70, 100, 130, 165, 200, 225, 250], [0, 0.65, 0.65, -0.6, -0.6, -0.1, 0.25]);
	const point = ip(f, [walkEnd + 5, walkEnd + 22, duration - 30, duration - 10], [0, 1, 1, 0.3]);
	const miguelPos: V3 = [0.6, 0, mz];

	// Cámara: sobrevuelo aéreo que desciende hasta acompañar a Miguel
	const aerial = camPath(f, 0, 190, [[30, 46, 92], [18, 26, 58], [7, 9, 36], [4, 4, 26]], [[0, 0, -8], [0, 0, -6], [0, 1, 4], [0, 1.4, 8]]);
	const followPos: V3 = [miguelPos[0] + 3.2, 2.3, mz + 3.8];
	const followLook: V3 = [miguelPos[0] - 1.6, 1.5, mz - 7];
	const k = ip(f, [120, 205], [0, 1]);
	const pos = lerp3(aerial.pos, followPos, k);
	const look = lerp3(aerial.look, followLook, k);
	// ligero empuje final
	const push = ip(f, [205, duration], [0, 1]);
	const finalPos: V3 = lerp3(pos, [miguelPos[0] + 3.3, 1.95, mz - 0.4], push);

	// Título de apertura
	const tIn = ip(f, [8, 30], [0, 1], easeOut);
	const tOut = ip(f, [92, 112], [1, 0]);
	return (
		<AbsoluteFill>
			<Stage>
				<CameraRig pos={finalPos} look={look} fov={36} />
				<SunLights size={55} />
				<Farm frame={f}>
					<FarmLife frame={f + 120} />
					<Person
						frame={f}
						{...MIGUEL}
						position={miguelPos}
						rotY={Math.PI}
						phase={phase}
						walking={walking}
						headYaw={headYaw}
						smile={0.6}
						rightArm={point > 0 ? [-1.45 * point, 0.1 + 0.35 * point] : undefined}
						rightElbow={point > 0 ? -0.15 : undefined}
					/>
				</Farm>
			</Stage>
			<AbsoluteFill style={{justifyContent: 'flex-start', alignItems: 'center', paddingTop: 120, opacity: tIn * tOut}}>
				<div
					style={{
						transform: `translateY(${(1 - tIn) * 30}px) scale(${0.96 + tIn * 0.04})`,
						textAlign: 'center',
						color: '#fff',
						textShadow: '0 4px 24px rgba(0,0,0,0.55), 0 2px 4px rgba(0,0,0,0.5)',
					}}
				>
					<div style={{fontSize: 108, fontWeight: 800, letterSpacing: 6}}>GRANJA INTEGRADA</div>
					<div
						style={{
							marginTop: 10,
							fontSize: 46,
							fontWeight: 600,
							color: '#ffe08a',
							letterSpacing: 1,
						}}
					>
						Tres Producciones, Un Solo Negocio
					</div>
				</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

