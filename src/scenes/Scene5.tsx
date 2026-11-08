import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {easeOut, ip, V3} from '../lib/anim';
import {CameraRig, Farm, Stage, SunLights} from '../three/World';
import {FarmLife} from './common';
import {EggIcon, PigIcon, SowIcon} from '../ui/Icons';

/** ESCENA 5 — El modelo financiero */
export const Scene5: React.FC<{duration: number}> = ({duration}) => {
	const f = useCurrentFrame();
	const a = ip(f, [0, duration], [0.35, -0.35], (t) => t);
	const r = 62;
	const pos: V3 = [Math.sin(a) * r, 34 + ip(f, [0, duration], [0, 6]), Math.cos(a) * r - 8];
	return (
		<AbsoluteFill>
			<Stage>
				<CameraRig pos={pos} look={[0, 0, -8]} fov={40} />
				<SunLights size={60} center={[0, 0, -6]} />
				<Farm frame={f + 600}>
					<FarmLife frame={f + 600} />
				</Farm>
			</Stage>
			<FinancialOverlay frame={f} />
		</AbsoluteFill>
	);
};

const CARD_W = 470;
const CARDS = [
	{
		x: 330,
		title: 'Huevos',
		text: 'Flujo frecuente de ingresos',
		color: '#f2a93b',
		icon: <EggIcon />,
		from: 18,
	},
	{
		x: 960,
		title: 'Reproducción',
		text: 'Producción de nuevos lechones',
		color: '#e8707f',
		icon: <SowIcon />,
		from: 38,
	},
	{
		x: 1590,
		title: 'Engorde',
		text: 'Ingresos por venta de cerdos',
		color: '#3f9a5a',
		icon: <PigIcon />,
		from: 58,
	},
];

/** Mini‑gráficos cualitativos (sin cifras inventadas). */
const MiniChart: React.FC<{kind: number; frame: number; color: string}> = ({kind, frame, color}) => {
	if (kind === 0) {
		// pulsos frecuentes y regulares
		return (
			<svg width={380} height={70}>
				{Array.from({length: 16}).map((_, i) => {
					const h = ip(frame, [i * 3, i * 3 + 10], [0, 1], easeOut) * (34 + (i % 3) * 6);
					return <rect key={i} x={6 + i * 23} y={62 - h} width={14} height={h} rx={4} fill={color} opacity={0.9} />;
				})}
			</svg>
		);
	}
	if (kind === 1) {
		// ciclo: cerda -> lechones -> engorde
		const rot = frame * 2.2;
		return (
			<svg width={380} height={70} viewBox="0 0 380 70">
				<g transform={`translate(60 35) rotate(${rot})`}>
					<circle r={24} fill="none" stroke={color} strokeWidth={6} strokeDasharray="30 10" />
				</g>
				{Array.from({length: 7}).map((_, i) => {
					const s = ip(frame, [8 + i * 5, 16 + i * 5], [0, 1], easeOut);
					return <circle key={i} cx={120 + i * 36} cy={36} r={12 * s} fill={color} opacity={0.85} />;
				})}
			</svg>
		);
	}
	// barras crecientes
	return (
		<svg width={380} height={70}>
			{Array.from({length: 6}).map((_, i) => {
				const h = ip(frame, [i * 5, i * 5 + 18], [0, 1], easeOut) * (12 + i * 10);
				return <rect key={i} x={20 + i * 58} y={64 - h} width={40} height={h} rx={5} fill={color} />;
			})}
			<path
				d="M20 58 L340 8"
				stroke="#24402a"
				strokeWidth={4}
				fill="none"
				strokeDasharray={360}
				strokeDashoffset={360 * (1 - ip(frame, [10, 40], [0, 1]))}
				markerEnd="url(#arrow)"
			/>
			<defs>
				<marker id="arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
					<path d="M0,0 L8,4 L0,8 z" fill="#24402a" />
				</marker>
			</defs>
		</svg>
	);
};

const FinancialOverlay: React.FC<{frame: number}> = ({frame}) => {
	const dim = ip(frame, [0, 20], [0, 1]);
	const center = ip(frame, [92, 112], [0, 1], easeOut);
	const CY = 560;
	return (
		<AbsoluteFill>
			<AbsoluteFill
				style={{
					opacity: dim,
					background: 'linear-gradient(180deg, rgba(8,30,18,0.55) 0%, rgba(8,30,18,0.35) 55%, rgba(8,30,18,0.5) 100%)',
				}}
			/>
			{/* conexiones */}
			<svg width={1920} height={1080} style={{position: 'absolute', inset: 0}}>
				{CARDS.map((c, i) => {
					const p = ip(frame, [c.from + 25, c.from + 55], [0, 1]);
					const d = `M ${c.x} 420 C ${c.x} 500, ${960 + (c.x - 960) * 0.35} ${CY - 90}, ${960 + (c.x - 960) * 0.3} ${CY - 70}`;
					return (
						<g key={i}>
							<path d={d} stroke="#ffffff" strokeOpacity={0.85} strokeWidth={5} fill="none" strokeDasharray="600" strokeDashoffset={600 * (1 - p)} />
							<path d={d} stroke={c.color} strokeWidth={5} fill="none" strokeDasharray="14 16" strokeDashoffset={-frame * 1.5} opacity={p} />
						</g>
					);
				})}
				{/* flechas de integración entre unidades */}
				<g opacity={ip(frame, [120, 140], [0, 1])}>
					<path d="M 1196 230 L 1352 230" stroke="#fff" strokeWidth={5} markerEnd="url(#w)" />
					<text x={1274} y={212} fill="#fff" fontSize={22} fontWeight={700} textAnchor="middle" fontFamily="Montserrat">
						lechones
					</text>
					<path d="M 566 230 L 722 230" stroke="#fff" strokeWidth={5} strokeDasharray="10 8" markerEnd="url(#w)" />
					<text x={644} y={212} fill="#fff" fontSize={22} fontWeight={700} textAnchor="middle" fontFamily="Montserrat">
						flujo de caja
					</text>
				</g>
				<defs>
					<marker id="w" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">
						<path d="M0,0 L10,5 L0,10 z" fill="#fff" />
					</marker>
				</defs>
			</svg>
			{/* tarjetas */}
			{CARDS.map((c, i) => {
				const p = ip(frame, [c.from, c.from + 18], [0, 1], easeOut);
				return (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: c.x - CARD_W / 2,
							top: 70,
							width: CARD_W,
							height: 350,
							opacity: p,
							transform: `translateY(${(1 - p) * 40}px) scale(${0.9 + p * 0.1})`,
							borderRadius: 26,
							background: 'rgba(255,255,255,0.94)',
							boxShadow: '0 16px 40px rgba(0,0,0,0.3)',
							borderTop: `10px solid ${c.color}`,
							padding: '22px 28px',
							boxSizing: 'border-box',
							color: '#1f3524',
						}}
					>
						<div style={{display: 'flex', alignItems: 'center', gap: 18}}>
							<div style={{width: 92, height: 92}}>{c.icon}</div>
							<div style={{fontSize: 40, fontWeight: 800}}>{c.title}</div>
						</div>
						<div style={{fontSize: 27, fontWeight: 600, marginTop: 12, lineHeight: 1.25}}>{c.text}</div>
						<div style={{marginTop: 18}}>
							<MiniChart kind={i} frame={Math.max(0, frame - c.from - 10)} color={c.color} />
						</div>
					</div>
				);
			})}
			{/* inversión */}
			<div
				style={{
					position: 'absolute',
					left: 960 - 430,
					top: CY - 70,
					width: 860,
					height: 230,
					opacity: center,
					transform: `scale(${0.8 + center * 0.2})`,
					borderRadius: 30,
					background: 'linear-gradient(135deg, #1f6b3a, #2e8b57)',
					border: '4px solid #ffd166',
					boxShadow: `0 0 ${40 + Math.sin(frame / 8) * 12}px rgba(255, 209, 102, 0.55), 0 20px 50px rgba(0,0,0,0.35)`,
					display: 'flex',
					flexDirection: 'column',
					alignItems: 'center',
					justifyContent: 'center',
					color: '#fff',
				}}
			>
				<div style={{fontSize: 34, fontWeight: 700, letterSpacing: 4, color: '#ffe8a6'}}>INVERSIÓN PROYECTADA</div>
				<div style={{fontSize: 96, fontWeight: 800, letterSpacing: 2, marginTop: 4}}>RD$5,000,000</div>
				<div style={{fontSize: 22, fontWeight: 600, marginTop: 2, opacity: 0.9}}>Con instalaciones existentes</div>
			</div>
			<div
				style={{
					position: 'absolute',
					left: 0,
					right: 0,
					top: CY + 178,
					textAlign: 'center',
					fontSize: 21,
					fontWeight: 500,
					color: 'rgba(255,255,255,0.85)',
					opacity: ip(frame, [130, 150], [0, 1]),
				}}
			>
				Cifras de ingresos y rentabilidad sujetas a un análisis financiero detallado.
			</div>
		</AbsoluteFill>
	);
};
