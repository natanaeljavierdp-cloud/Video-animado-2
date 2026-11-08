import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {camPath, easeOut, ip} from '../lib/anim';
import {Person} from '../three/Characters';
import {CameraRig, Farm, Stage, SunLights} from '../three/World';
import timings from '../timings.json';
import {Emblem} from '../ui/Icons';
import {FarmLife, MIGUEL} from './common';

const PI = Math.PI;

/** ESCENA 6 — La visión de futuro */
export const Scene6: React.FC<{duration: number}> = ({duration}) => {
	const f = useCurrentFrame();
	const endFrom = duration - timings.endCardFrames - 20;
	const M: [number, number, number] = [1.0, 0, 8.5];
	const cam = camPath(
		f,
		0,
		endFrom + 40,
		[
			[-1.0, 1.8, 4.4],
			[-3.0, 2.3, 9.8],
			[-3.5, 7, 21],
			[2, 22, 44],
			[8, 42, 68],
		],
		[
			[1.0, 1.65, 8.5],
			[0.3, 1.5, 5.5],
			[0, 1, -4],
			[0, 0, -7],
			[0, 0, -9],
		],
	);
	const nod = Math.sin(f / 9) * 0.06 * ip(f, [30, 60, 110, 130], [0, 1, 1, 0]);
	const g = ip(f, [55, 80, 150, 175], [0, 1, 1, 0]);
	return (
		<AbsoluteFill>
			<Stage>
				<CameraRig pos={cam.pos} look={cam.look} fov={38} />
				<SunLights size={60} center={[0, 0, -2]} />
				<Farm frame={f + 900}>
					<FarmLife frame={f + 900} />
					<Person
						frame={f}
						{...MIGUEL}
						position={M}
						rotY={PI - 0.25 + ip(f, [0, 60], [0.6, 0])}
						smile={1}
						headPitch={nod - 0.05}
						headYaw={ip(f, [140, 220], [0, -0.5])}
						rightArm={[-0.55 * g, 0.1 + 0.95 * g]}
						rightElbow={-0.15 - 0.1 * g}
					/>
				</Farm>
			</Stage>
			<EndCard frame={f - endFrom} />
		</AbsoluteFill>
	);
};

const EndCard: React.FC<{frame: number}> = ({frame}) => {
	if (frame < 0) return null;
	const bg = ip(frame, [0, 25], [0, 1]);
	const logo = ip(frame, [8, 30], [0, 1], easeOut);
	const title = ip(frame, [16, 38], [0, 1], easeOut);
	const tag = ip(frame, [30, 52], [0, 1], easeOut);
	return (
		<AbsoluteFill
			style={{
				background: `radial-gradient(ellipse at center, rgba(10,40,20,${0.55 * bg}) 0%, rgba(5,20,10,${0.85 * bg}) 100%)`,
				alignItems: 'center',
				justifyContent: 'center',
				flexDirection: 'column',
				color: '#fff',
			}}
		>
			<div style={{opacity: logo, transform: `scale(${0.7 + logo * 0.3}) rotate(${(1 - logo) * -25}deg)`}}>
				<Emblem size={210} />
			</div>
			<div
				style={{
					marginTop: 26,
					fontSize: 124,
					fontWeight: 800,
					letterSpacing: 10 + (1 - title) * 20,
					opacity: title,
					textShadow: '0 6px 30px rgba(0,0,0,0.5)',
				}}
			>
				GRANJA INTEGRADA
			</div>
			<div style={{width: 520 * tag, height: 4, background: '#ffd166', borderRadius: 2, margin: '14px 0 22px'}} />
			<div style={{fontSize: 48, fontWeight: 600, color: '#ffe8a6', opacity: tag, transform: `translateY(${(1 - tag) * 20}px)`}}>
				Producción inteligente. Crecimiento sostenible.
			</div>
			<div style={{marginTop: 36, fontSize: 24, fontWeight: 500, opacity: tag * 0.8, letterSpacing: 3}}>
				PROYECTO AGROPECUARIO · REPÚBLICA DOMINICANA
			</div>
		</AbsoluteFill>
	);
};
