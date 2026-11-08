import React from 'react';

export const EggIcon: React.FC = () => (
	<svg viewBox="0 0 100 100" width="100%" height="100%">
		<circle cx="50" cy="50" r="48" fill="#fff4dc" />
		<ellipse cx="50" cy="54" rx="24" ry="31" fill="#f1d9b5" stroke="#c99a5b" strokeWidth="3" />
		<ellipse cx="41" cy="42" rx="6" ry="10" fill="#fff" opacity="0.7" />
	</svg>
);

export const PigIcon: React.FC = () => (
	<svg viewBox="0 0 100 100" width="100%" height="100%">
		<circle cx="50" cy="50" r="48" fill="#e6f4ea" />
		<path d="M27 30 L22 14 L38 24 Z" fill="#e8707f" />
		<path d="M73 30 L78 14 L62 24 Z" fill="#e8707f" />
		<circle cx="50" cy="52" r="30" fill="#f4a7ac" />
		<ellipse cx="50" cy="62" rx="14" ry="10" fill="#e8707f" />
		<circle cx="45" cy="62" r="3" fill="#7a3c46" />
		<circle cx="55" cy="62" r="3" fill="#7a3c46" />
		<circle cx="39" cy="44" r="4" fill="#1a1010" />
		<circle cx="61" cy="44" r="4" fill="#1a1010" />
	</svg>
);

export const SowIcon: React.FC = () => (
	<svg viewBox="0 0 100 100" width="100%" height="100%">
		<circle cx="50" cy="50" r="48" fill="#fde8ea" />
		<ellipse cx="48" cy="50" rx="30" ry="19" fill="#f4a7ac" />
		<circle cx="76" cy="45" r="13" fill="#f4a7ac" />
		<ellipse cx="86" cy="48" rx="5" ry="6" fill="#e8707f" />
		<circle cx="78" cy="41" r="2.5" fill="#1a1010" />
		<path d="M70 33 L72 24 L78 32 Z" fill="#e8707f" />
		{[30, 44, 58].map((x) => (
			<g key={x}>
				<ellipse cx={x} cy={78} rx={8} ry={6} fill="#f7b9bd" />
				<circle cx={x + 7} cy={76} r={4} fill="#f7b9bd" />
			</g>
		))}
	</svg>
);

/** Emblema de la granja: tres producciones en un solo círculo. */
export const Emblem: React.FC<{size?: number}> = ({size = 220}) => (
	<svg viewBox="0 0 220 220" width={size} height={size}>
		<circle cx="110" cy="110" r="104" fill="#2d6a31" stroke="#ffd166" strokeWidth="6" />
		<circle cx="110" cy="110" r="88" fill="none" stroke="#ffd166" strokeOpacity="0.5" strokeWidth="2" strokeDasharray="6 6" />
		<path d="M30 140 Q110 100 190 140 L190 160 Q110 210 30 160 Z" fill="#6fbf4a" />
		<path d="M60 128 L60 98 L84 82 L108 98 L108 128 Z" fill="#fdf6e3" />
		<path d="M54 100 L84 76 L114 100" stroke="#d1452e" strokeWidth="8" fill="none" strokeLinejoin="round" />
		<rect x="78" y="108" width="12" height="20" fill="#8b5e3c" />
		<g transform="translate(130 80)">
			<ellipse cx="0" cy="18" rx="11" ry="14" fill="#f1d9b5" stroke="#c99a5b" strokeWidth="2" />
		</g>
		<g transform="translate(150 112)">
			<ellipse cx="0" cy="0" rx="16" ry="11" fill="#f4a7ac" />
			<circle cx="14" cy="-3" r="7" fill="#f4a7ac" />
			<ellipse cx="20" cy="-2" rx="3" ry="3.5" fill="#e8707f" />
		</g>
		<path d="M110 30 L114 42 L127 42 L117 50 L121 62 L110 54 L99 62 L103 50 L93 42 L106 42 Z" fill="#ffd166" />
	</svg>
);
