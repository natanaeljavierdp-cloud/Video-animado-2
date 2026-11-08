import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {ip} from './lib/anim';
import {Scene1} from './scenes/Scene1';
import {Scene2} from './scenes/Scene2';
import {Scene3} from './scenes/Scene3';
import {Scene4} from './scenes/Scene4';
import {Scene5} from './scenes/Scene5';
import {Scene6} from './scenes/Scene6';
import timings from './timings.json';
import {Subtitles} from './ui/Subtitles';

const SCENES = [Scene1, Scene2, Scene3, Scene4, Scene5, Scene6];

const FadeIn: React.FC<{frames: number; enabled: boolean; children: React.ReactNode}> = ({frames, enabled, children}) => {
	const f = useCurrentFrame();
	const o = enabled ? ip(f, [0, frames], [0, 1]) : 1;
	return <AbsoluteFill style={{opacity: o}}>{children}</AbsoluteFill>;
};

export const GranjaVideo: React.FC = () => {
	const f = useCurrentFrame();
	const total = timings.durationInFrames;
	const fadeIn = ip(f, [0, 18], [1, 0]);
	return (
		<AbsoluteFill style={{background: '#000', fontFamily: 'Montserrat, sans-serif'}}>
			{timings.scenes.map((s, i) => {
				const C = SCENES[i];
				return (
					<Sequence key={i} from={s.from} durationInFrames={s.duration} name={`Escena ${i + 1}`}>
						<FadeIn frames={timings.transition} enabled={i > 0}>
							<C duration={s.duration} />
						</FadeIn>
					</Sequence>
				);
			})}
			{/* viñeta cinematográfica */}
			<AbsoluteFill
				style={{
					background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.38) 100%)',
					pointerEvents: 'none',
				}}
			/>
			<Subtitles />
			<AbsoluteFill style={{background: '#000', opacity: Math.max(fadeIn, ip(f, [total - 20, total - 1], [0, 1]))}} />
			<Audio src={staticFile('audio/mix.wav')} />
		</AbsoluteFill>
	);
};
