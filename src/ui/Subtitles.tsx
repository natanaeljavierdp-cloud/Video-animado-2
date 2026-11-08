import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {ip} from '../lib/anim';
import timings from '../timings.json';

const SUBS = timings.scenes.flatMap((s) => s.subtitles);

export const Subtitles: React.FC = () => {
	const f = useCurrentFrame();
	const cur = SUBS.find((s) => f >= s.from && f < s.from + s.duration + 6);
	if (!cur) return null;
	const local = f - cur.from;
	const o = Math.min(ip(local, [0, 5], [0, 1]), ip(local, [cur.duration + 1, cur.duration + 6], [1, 0]));
	return (
		<AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 64}}>
			<div
				style={{
					opacity: o,
					transform: `translateY(${(1 - o) * 10}px)`,
					maxWidth: 1500,
					padding: '14px 34px',
					borderRadius: 14,
					background: 'rgba(10, 20, 12, 0.62)',
					color: '#fff',
					fontSize: 44,
					fontWeight: 600,
					lineHeight: 1.3,
					textAlign: 'center',
					textShadow: '0 2px 6px rgba(0,0,0,0.6)',
					letterSpacing: 0.2,
				}}
			>
				{cur.text}
			</div>
		</AbsoluteFill>
	);
};
