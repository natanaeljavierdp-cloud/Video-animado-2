import {useThree} from '@react-three/fiber';
import {ThreeCanvas} from '@remotion/three';
import React, {useMemo} from 'react';
import {useVideoConfig} from 'remotion';
import {BackSide, BufferAttribute, CanvasTexture, Color, PerspectiveCamera, SphereGeometry, SRGBColorSpace} from 'three';
import {rng, V3} from '../lib/anim';
import {EggTray, Mat} from './Characters';

const PI = Math.PI;

/* ------------------------------------------------------------------ ESCENARIO */
export const Stage: React.FC<{children: React.ReactNode}> = ({children}) => {
	const {width, height} = useVideoConfig();
	return (
		<ThreeCanvas
			width={width}
			height={height}
			shadows
			gl={{antialias: true, preserveDrawingBuffer: true}}
			camera={{fov: 38, near: 0.1, far: 900, position: [0, 5, 20]}}
			style={{position: 'absolute', inset: 0}}
		>
			{children}
		</ThreeCanvas>
	);
};

export const CameraRig: React.FC<{pos: V3; look: V3; fov?: number}> = ({pos, look, fov = 38}) => {
	const camera = useThree((s) => s.camera) as PerspectiveCamera;
	camera.position.set(...pos);
	camera.lookAt(...look);
	if (camera.fov !== fov) {
		camera.fov = fov;
		camera.updateProjectionMatrix();
	}
	return null;
};

/* ------------------------------------------------------------------ CIELO Y LUZ */
export const Sky: React.FC<{top?: string; bottom?: string}> = ({top = '#3a86d8', bottom = '#d6eefc'}) => {
	const geo = useMemo(() => {
		const g = new SphereGeometry(600, 32, 24);
		const pos = g.attributes.position;
		const cols = new Float32Array(pos.count * 3);
		const ct = new Color(top);
		const cb = new Color(bottom);
		const c = new Color();
		for (let i = 0; i < pos.count; i++) {
			const h = Math.min(1, Math.max(0, pos.getY(i) / 600 * 1.7 + 0.04));
			c.copy(cb).lerp(ct, Math.pow(h, 0.75));
			cols[i * 3] = c.r;
			cols[i * 3 + 1] = c.g;
			cols[i * 3 + 2] = c.b;
		}
		g.setAttribute('color', new BufferAttribute(cols, 3));
		return g;
	}, [top, bottom]);
	return (
		<mesh geometry={geo}>
			<meshBasicMaterial vertexColors side={BackSide} fog={false} depthWrite={false} />
		</mesh>
	);
};

export const Clouds: React.FC<{frame: number}> = ({frame}) => {
	const list = useMemo(() => {
		const r = rng(99);
		return Array.from({length: 14}).map(() => ({
			x: -260 + r() * 520,
			y: 70 + r() * 50,
			z: -320 + r() * 240,
			s: 10 + r() * 14,
			n: 3 + Math.floor(r() * 3),
		}));
	}, []);
	return (
		<group>
			{list.map((c, i) => (
				<group key={i} position={[c.x + frame * 0.03, c.y, c.z]} scale={c.s}>
					{Array.from({length: c.n}).map((_, k) => (
						<mesh key={k} position={[k * 0.9 - c.n * 0.45, (k % 2) * 0.35, 0]} scale={[1.1, 0.75, 0.8]}>
							<sphereGeometry args={[1, 14, 10]} />
							<meshStandardMaterial color="#ffffff" roughness={1} emissive="#ffffff" emissiveIntensity={0.25} />
						</mesh>
					))}
				</group>
			))}
		</group>
	);
};

export const SunLights: React.FC<{size?: number; intensity?: number; center?: V3}> = ({
	size = 45,
	intensity = 2.8,
	center = [0, 0, 0],
}) => (
	<>
		<hemisphereLight args={['#cfe8ff', '#6b8f3a', 1.1]} />
		<ambientLight intensity={0.25} />
		<directionalLight
			position={[center[0] + 40, 60, center[2] + 30]}
			intensity={intensity}
			color="#fff0d8"
			castShadow
			shadow-mapSize-width={2048}
			shadow-mapSize-height={2048}
			shadow-camera-left={-size}
			shadow-camera-right={size}
			shadow-camera-top={size}
			shadow-camera-bottom={-size}
			shadow-camera-near={1}
			shadow-camera-far={200}
			shadow-bias={-0.0004}
			shadow-normalBias={0.02}
		>
			<object3D attach="target" position={center} />
		</directionalLight>
	</>
);

/* ------------------------------------------------------------------ TEXTURA DE TEXTO */
export function useLabel(lines: {text: string; size: number; color: string; weight?: number}[], w = 1024, h = 256, bg = '#ffffff') {
	return useMemo(() => {
		const c = document.createElement('canvas');
		c.width = w;
		c.height = h;
		const ctx = c.getContext('2d')!;
		ctx.fillStyle = bg;
		ctx.fillRect(0, 0, w, h);
		ctx.textAlign = 'center';
		ctx.textBaseline = 'middle';
		const total = lines.reduce((a, l) => a + l.size * 1.15, 0);
		let y = h / 2 - total / 2;
		for (const l of lines) {
			ctx.font = `${l.weight ?? 800} ${l.size}px Montserrat, 'DejaVu Sans', sans-serif`;
			ctx.fillStyle = l.color;
			ctx.fillText(l.text, w / 2, y + (l.size * 1.15) / 2);
			y += l.size * 1.15;
		}
		const t = new CanvasTexture(c);
		t.colorSpace = SRGBColorSpace;
		t.anisotropy = 4;
		return t;
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [JSON.stringify(lines), w, h, bg]);
}

/* ------------------------------------------------------------------ VEGETACIÓN */
export const Palm: React.FC<{position: V3; height?: number; lean?: number; rotY?: number; frame?: number}> = ({
	position,
	height = 7,
	lean = 0.15,
	rotY = 0,
	frame = 0,
}) => {
	const segs = 8;
	const sway = Math.sin(frame / 40 + position[0]) * 0.04;
	return (
		<group position={position} rotation={[0, rotY, 0]}>
			{Array.from({length: segs}).map((_, i) => {
				const t = i / segs;
				const x = Math.sin(t * 1.4) * lean * height * 0.5;
				return (
					<mesh key={i} position={[x, (i + 0.5) * (height / segs), 0]} rotation={[0, 0, -lean * t * 1.2]} castShadow>
						<cylinderGeometry args={[0.2 - t * 0.06, 0.24 - t * 0.06, height / segs + 0.3, 10]} />
						<Mat color={i % 2 ? '#8a6a48' : '#7a5c3d'} rough={1} />
					</mesh>
				);
			})}
			<group position={[Math.sin(1.4) * lean * height * 0.5, height, 0]} rotation={[sway, 0, sway]}>
				<mesh>
					<sphereGeometry args={[0.32, 10, 8]} />
					<Mat color="#5d7a2a" />
				</mesh>
				{Array.from({length: 9}).map((_, i) => (
					<group key={i} rotation={[0, (i / 9) * PI * 2, 0]}>
						<mesh position={[1.35, -0.35, 0]} rotation={[0, 0, -0.45 - (i % 3) * 0.12]} scale={[1, 0.08, 0.32]} castShadow>
							<sphereGeometry args={[1.5, 12, 8]} />
							<Mat color={i % 2 ? '#3f9a3a' : '#4daf43'} rough={0.8} />
						</mesh>
					</group>
				))}
				{[0, 1, 2].map((i) => (
					<mesh key={i} position={[Math.cos(i * 2) * 0.25, -0.35, Math.sin(i * 2) * 0.25]}>
						<sphereGeometry args={[0.16, 10, 8]} />
						<Mat color="#6b5a2a" />
					</mesh>
				))}
			</group>
		</group>
	);
};

export const RoundTree: React.FC<{position: V3; scale?: number; color?: string}> = ({position, scale = 1, color = '#3f9a45'}) => (
	<group position={position} scale={scale}>
		<mesh position={[0, 1.2, 0]} castShadow>
			<cylinderGeometry args={[0.22, 0.32, 2.4, 10]} />
			<Mat color="#73533a" rough={1} />
		</mesh>
		{[
			[0, 3.1, 0, 1.7],
			[1.0, 2.7, 0.3, 1.2],
			[-0.9, 2.8, -0.2, 1.25],
			[0.2, 3.9, -0.3, 1.15],
			[-0.2, 2.7, 0.9, 1.1],
		].map(([x, y, z, r], i) => (
			<mesh key={i} position={[x, y, z]} castShadow>
				<sphereGeometry args={[r, 16, 12]} />
				<Mat color={i % 2 ? color : '#4caf50'} rough={0.85} />
			</mesh>
		))}
	</group>
);

export const Banana: React.FC<{position: V3; frame?: number}> = ({position, frame = 0}) => (
	<group position={position}>
		<mesh position={[0, 0.9, 0]} castShadow>
			<cylinderGeometry args={[0.13, 0.18, 1.8, 8]} />
			<Mat color="#7f9a3a" />
		</mesh>
		{Array.from({length: 6}).map((_, i) => (
			<group key={i} position={[0, 1.8, 0]} rotation={[0, (i / 6) * PI * 2, 0]}>
				<mesh position={[0.7, 0.2, 0]} rotation={[0, 0, 0.5 + Math.sin(frame / 30 + i) * 0.05]} scale={[1, 0.06, 0.35]} castShadow>
					<sphereGeometry args={[0.9, 10, 8]} />
					<Mat color="#5cb848" />
				</mesh>
			</group>
		))}
	</group>
);

export const Bush: React.FC<{position: V3; scale?: number}> = ({position, scale = 1}) => (
	<group position={position} scale={scale}>
		{[
			[0, 0.4, 0, 0.6],
			[0.5, 0.3, 0.1, 0.45],
			[-0.45, 0.32, 0, 0.48],
		].map(([x, y, z, r], i) => (
			<mesh key={i} position={[x, y, z]} castShadow>
				<sphereGeometry args={[r, 12, 10]} />
				<Mat color={i ? '#4f9e3c' : '#5aae46'} />
			</mesh>
		))}
	</group>
);

/* ------------------------------------------------------------------ CONSTRUCCIONES */
export const GableRoof: React.FC<{w: number; d: number; h: number; color: string; overhang?: number}> = ({
	w,
	d,
	h,
	color,
	overhang = 0.5,
}) => {
	const half = w / 2 + overhang;
	const len = Math.hypot(half, h);
	const ang = Math.atan2(h, half);
	return (
		<group>
			{[1, -1].map((s) => (
				<mesh key={s} position={[(s * half) / 2, h / 2, 0]} rotation={[0, 0, -s * ang]} castShadow receiveShadow>
					<boxGeometry args={[len, 0.12, d + overhang * 2]} />
					<Mat color={color} rough={0.55} />
				</mesh>
			))}
			{/* acanalado del zinc */}
			{Array.from({length: Math.floor((d + overhang * 2) / 1.2)}).map((_, i) =>
				[1, -1].map((s) => (
					<mesh
						key={`${i}${s}`}
						position={[(s * half) / 2, h / 2 + 0.07, -d / 2 - overhang + 0.6 + i * 1.2]}
						rotation={[0, 0, -s * ang]}
					>
						<boxGeometry args={[len, 0.03, 0.08]} />
						<Mat color={color} rough={0.4} />
					</mesh>
				)),
			)}
		</group>
	);
};

/** Galpón largo (gallinero o porqueriza). Eje largo = Z. */
export const Shed: React.FC<{
	position: V3;
	w: number;
	d: number;
	wall?: string;
	roof?: string;
	low?: number;
	h?: number;
	mesh?: boolean;
	label?: string;
}> = ({position, w, d, wall = '#f4ead2', roof = '#c2492f', low = 1.0, h = 2.8, mesh = true, label}) => {
	const tex = useLabel(label ? [{text: label, size: 92, color: '#2d4a22'}] : [{text: '', size: 10, color: '#000'}], 1024, 192, '#fdf6e3');
	const postCount = Math.floor(d / 3) + 1;
	return (
		<group position={position}>
			<mesh position={[0, 0.06, 0]} receiveShadow>
				<boxGeometry args={[w + 0.6, 0.12, d + 0.6]} />
				<Mat color="#cfc8bb" />
			</mesh>
			{/* muros bajos */}
			{[1, -1].map((s) => (
				<mesh key={s} position={[(s * w) / 2, low / 2, 0]} castShadow receiveShadow>
					<boxGeometry args={[0.2, low, d]} />
					<Mat color={wall} />
				</mesh>
			))}
			{[1, -1].map((s) => (
				<mesh key={`e${s}`} position={[0, h / 2, (s * d) / 2]} castShadow receiveShadow>
					<boxGeometry args={[w, h, 0.2]} />
					<Mat color={wall} />
				</mesh>
			))}
			{/* hastial */}
			{[1, -1].map((s) => (
				<mesh key={`g${s}`} position={[0, h, (s * d) / 2]} rotation={[PI / 2, 0, 0]} scale={[w / 2, 1, 1.1]}>
					<cylinderGeometry args={[1, 1, 0.2, 3, 1, false, PI, PI]} />
					<Mat color={wall} />
				</mesh>
			))}
			{/* malla */}
			{mesh &&
				[1, -1].map((s) => (
					<mesh key={`m${s}`} position={[(s * w) / 2, low + (h - low) / 2, 0]}>
						<boxGeometry args={[0.04, h - low, d]} />
						<meshStandardMaterial color="#9aa3a8" transparent opacity={0.35} roughness={0.6} />
					</mesh>
				))}
			{/* columnas */}
			{Array.from({length: postCount}).map((_, i) =>
				[1, -1].map((s) => (
					<mesh key={`p${i}${s}`} position={[(s * w) / 2, h / 2, -d / 2 + (i * d) / (postCount - 1)]} castShadow>
						<boxGeometry args={[0.22, h, 0.22]} />
						<Mat color="#e6dcc3" />
					</mesh>
				)),
			)}
			<group position={[0, h, 0]}>
				<GableRoof w={w} d={d} h={w * 0.22} color={roof} />
			</group>
			{/* puerta */}
			<mesh position={[0, 1.05, d / 2 + 0.11]}>
				<boxGeometry args={[1.6, 2.1, 0.04]} />
				<Mat color="#6b4a2f" />
			</mesh>
			{label && (
				<mesh position={[0, h + 0.55, d / 2 + 0.13]}>
					<planeGeometry args={[w * 0.55, (w * 0.55 * 192) / 1024]} />
					<meshStandardMaterial map={tex} roughness={0.8} />
				</mesh>
			)}
		</group>
	);
};

export const House: React.FC<{position: V3; rotY?: number}> = ({position, rotY = 0}) => (
	<group position={position} rotation={[0, rotY, 0]}>
		<mesh position={[0, 1.5, 0]} castShadow receiveShadow>
			<boxGeometry args={[7, 3, 5]} />
			<Mat color="#49b3c9" />
		</mesh>
		<group position={[0, 3, 0]} rotation={[0, PI / 2, 0]}>
			<GableRoof w={5} d={7} h={1.6} color="#d1452e" />
		</group>
		<mesh position={[0, 1.05, 2.51]}>
			<boxGeometry args={[1.1, 2.1, 0.05]} />
			<Mat color="#f4d35e" />
		</mesh>
		{[-2.2, 2.2].map((x) => (
			<group key={x} position={[x, 1.7, 2.52]}>
				<mesh>
					<boxGeometry args={[1.2, 1, 0.05]} />
					<Mat color="#fef6e4" />
				</mesh>
				<mesh position={[0, 0, 0.02]}>
					<boxGeometry args={[1.0, 0.82, 0.04]} />
					<Mat color="#2f6b7a" rough={0.2} />
				</mesh>
			</group>
		))}
		{/* galería */}
		<mesh position={[0, 0.1, 3.3]} receiveShadow>
			<boxGeometry args={[7.4, 0.2, 1.6]} />
			<Mat color="#d8c7a8" />
		</mesh>
		{[-3.4, 0, 3.4].map((x) => (
			<mesh key={x} position={[x, 1.4, 4]} castShadow>
				<cylinderGeometry args={[0.08, 0.08, 2.6, 8]} />
				<Mat color="#fff" />
			</mesh>
		))}
		<mesh position={[0, 2.75, 3.4]} rotation={[0.18, 0, 0]} castShadow>
			<boxGeometry args={[7.8, 0.1, 2]} />
			<Mat color="#b33b26" />
		</mesh>
	</group>
);

export const Silo: React.FC<{position: V3}> = ({position}) => (
	<group position={position}>
		<mesh position={[0, 3.8, 0]} castShadow>
			<cylinderGeometry args={[1.5, 1.5, 5, 20]} />
			<meshStandardMaterial color="#cfd6dc" metalness={0.5} roughness={0.35} />
		</mesh>
		<mesh position={[0, 6.9, 0]} castShadow>
			<coneGeometry args={[1.55, 1.2, 20]} />
			<meshStandardMaterial color="#b8c1c9" metalness={0.5} roughness={0.35} />
		</mesh>
		<mesh position={[0, 0.9, 0]}>
			<coneGeometry args={[1.5, 1.6, 20, 1, true]} />
			<meshStandardMaterial color="#b8c1c9" metalness={0.5} roughness={0.35} side={2} />
		</mesh>
		{[0, 1, 2, 3].map((i) => (
			<mesh key={i} position={[Math.cos((i * PI) / 2 + 0.78) * 1.4, 0.9, Math.sin((i * PI) / 2 + 0.78) * 1.4]} castShadow>
				<boxGeometry args={[0.15, 1.8, 0.15]} />
				<Mat color="#8c959c" />
			</mesh>
		))}
	</group>
);

export const WaterTank: React.FC<{position: V3}> = ({position}) => (
	<group position={position}>
		{[0, 1, 2, 3].map((i) => (
			<mesh key={i} position={[(i % 2 ? 1 : -1) * 0.8, 2, (i < 2 ? 1 : -1) * 0.8]} castShadow>
				<boxGeometry args={[0.16, 4, 0.16]} />
				<Mat color="#7d7368" />
			</mesh>
		))}
		<mesh position={[0, 4.1, 0]} receiveShadow>
			<boxGeometry args={[2, 0.15, 2]} />
			<Mat color="#7d7368" />
		</mesh>
		<mesh position={[0, 4.9, 0]} castShadow>
			<cylinderGeometry args={[0.9, 0.9, 1.5, 18]} />
			<Mat color="#2b2b2b" rough={0.5} />
		</mesh>
	</group>
);

export const Fence: React.FC<{from: [number, number]; to: [number, number]; color?: string}> = ({from, to, color = '#e9dcc0'}) => {
	const len = Math.hypot(to[0] - from[0], to[1] - from[1]);
	const ang = Math.atan2(to[0] - from[0], to[1] - from[1]);
	const n = Math.max(2, Math.round(len / 2.5) + 1);
	return (
		<group position={[from[0], 0, from[1]]} rotation={[0, ang, 0]}>
			{Array.from({length: n}).map((_, i) => (
				<mesh key={i} position={[0, 0.6, (i * len) / (n - 1)]} castShadow>
					<boxGeometry args={[0.14, 1.2, 0.14]} />
					<Mat color={color} />
				</mesh>
			))}
			{[0.45, 0.95].map((y) => (
				<mesh key={y} position={[0, y, len / 2]} castShadow>
					<boxGeometry args={[0.06, 0.1, len]} />
					<Mat color={color} />
				</mesh>
			))}
		</group>
	);
};

export const Road: React.FC<{points: [number, number][]; width?: number; color?: string}> = ({points, width = 3.4, color = '#cfa46a'}) => (
	<group>
		{points.slice(1).map((p, i) => {
			const a = points[i];
			const len = Math.hypot(p[0] - a[0], p[1] - a[1]);
			const ang = Math.atan2(p[0] - a[0], p[1] - a[1]);
			return (
				<group key={i}>
					<mesh position={[(a[0] + p[0]) / 2, 0.02, (a[1] + p[1]) / 2]} rotation={[-PI / 2, 0, ang]} receiveShadow>
						<planeGeometry args={[width, len + width * 0.3]} />
						<Mat color={color} rough={1} />
					</mesh>
					<mesh position={[p[0], 0.021, p[1]]} rotation={[-PI / 2, 0, 0]} receiveShadow>
						<circleGeometry args={[width / 2, 20]} />
						<Mat color={color} rough={1} />
					</mesh>
				</group>
			);
		})}
	</group>
);

export const Truck: React.FC<{position: V3; rotY?: number; wheelRot?: number}> = ({position, rotY = 0, wheelRot = 0}) => {
	const tex = useLabel(
		[
			{text: 'HUEVOS FRESCOS', size: 96, color: '#c0392b'},
			{text: 'Granja Integrada', size: 64, color: '#2d6a31', weight: 700},
		],
		1024,
		320,
		'#fffaf0',
	);
	return (
		<group position={position} rotation={[0, rotY, 0]}>
			{/* chasis */}
			<mesh position={[0, 0.65, 0]} castShadow>
				<boxGeometry args={[1.9, 0.3, 4.6]} />
				<Mat color="#333" />
			</mesh>
			{/* cabina */}
			<mesh position={[0, 1.45, 1.55]} castShadow>
				<boxGeometry args={[1.9, 1.4, 1.4]} />
				<Mat color="#2e7fd6" rough={0.35} />
			</mesh>
			<mesh position={[0, 1.75, 2.26]}>
				<boxGeometry args={[1.6, 0.6, 0.04]} />
				<meshStandardMaterial color="#9fd3ff" roughness={0.1} metalness={0.2} />
			</mesh>
			{[1, -1].map((s) => (
				<mesh key={s} position={[0.96 * s, 1.75, 1.6]}>
					<boxGeometry args={[0.04, 0.5, 0.8]} />
					<meshStandardMaterial color="#9fd3ff" roughness={0.1} />
				</mesh>
			))}
			{[0.65, -0.65].map((x) => (
				<mesh key={x} position={[x, 1.0, 2.27]}>
					<boxGeometry args={[0.3, 0.18, 0.04]} />
					<Mat color="#fff7c2" emissive="#fff3a0" ei={0.4} />
				</mesh>
			))}
			{/* caja de carga */}
			<mesh position={[0, 1.75, -0.8]} castShadow>
				<boxGeometry args={[2.0, 2.0, 3.0]} />
				<Mat color="#fffaf0" rough={0.5} />
			</mesh>
			{[1, -1].map((s) => (
				<mesh key={s} position={[1.011 * s, 1.75, -0.8]} rotation={[0, (s * PI) / 2, 0]}>
					<planeGeometry args={[2.8, 0.875]} />
					<meshStandardMaterial map={tex} roughness={0.6} />
				</mesh>
			))}
			{/* ruedas */}
			{[
				[0.95, 1.5],
				[-0.95, 1.5],
				[0.95, -1.4],
				[-0.95, -1.4],
			].map(([x, z], i) => (
				<group key={i} position={[x, 0.45, z]} rotation={[wheelRot, 0, PI / 2]}>
					<mesh castShadow>
						<cylinderGeometry args={[0.45, 0.45, 0.32, 18]} />
						<Mat color="#1e1e1e" rough={0.9} />
					</mesh>
					<mesh position={[0, 0.17 * Math.sign(x), 0]}>
						<cylinderGeometry args={[0.22, 0.22, 0.02, 12]} />
						<Mat color="#c9ced3" />
					</mesh>
				</group>
			))}
		</group>
	);
};

export const Gate: React.FC<{position: V3}> = ({position}) => {
	const tex = useLabel(
		[
			{text: 'GRANJA INTEGRADA', size: 110, color: '#fdf6e3'},
			{text: 'Huevos · Reproducción · Engorde', size: 52, color: '#ffd166', weight: 600},
		],
		1400,
		300,
		'#2d6a31',
	);
	return (
		<group position={position}>
			{[1, -1].map((s) => (
				<mesh key={s} position={[2.6 * s, 2.2, 0]} castShadow>
					<boxGeometry args={[0.45, 4.4, 0.45]} />
					<Mat color="#8b5e3c" />
				</mesh>
			))}
			<mesh position={[0, 4.3, 0]} castShadow>
				<boxGeometry args={[6.2, 1.25, 0.18]} />
				<Mat color="#2d6a31" />
			</mesh>
			{[1, -1].map((s) => (
				<mesh key={s} position={[0, 4.3, 0.1 * s]} rotation={[0, s > 0 ? 0 : PI, 0]}>
					<planeGeometry args={[5.9, (5.9 * 300) / 1400]} />
					<meshStandardMaterial map={tex} roughness={0.7} />
				</mesh>
			))}
		</group>
	);
};

export const Wheelbarrow: React.FC<{position?: V3; rotY?: number; tilt?: number}> = ({position = [0, 0, 0], rotY = 0, tilt = 0}) => (
	<group position={position} rotation={[0, rotY, 0]}>
		<group rotation={[tilt, 0, 0]}>
			<mesh position={[0, 0.6, 0]} castShadow>
				<boxGeometry args={[0.7, 0.35, 0.9]} />
				<Mat color="#2f8f4e" rough={0.4} />
			</mesh>
			<mesh position={[0, 0.79, 0]}>
				<boxGeometry args={[0.6, 0.04, 0.8]} />
				<Mat color="#a0703c" />
			</mesh>
			{[1, -1].map((s) => (
				<mesh key={s} position={[0.25 * s, 0.6, -0.75]} rotation={[PI / 2 - 0.25, 0, 0]}>
					<cylinderGeometry args={[0.03, 0.03, 0.9, 6]} />
					<Mat color="#555" />
				</mesh>
			))}
		</group>
		<mesh position={[0, 0.22, 0.55]} rotation={[0, 0, PI / 2]} castShadow>
			<cylinderGeometry args={[0.22, 0.22, 0.12, 14]} />
			<Mat color="#222" />
		</mesh>
	</group>
);

/* ------------------------------------------------------------------ GRANJA EXTERIOR */
export const LAYOUT = {
	gallinero: [-15, 0, -10] as V3,
	cerdos1: [13, 0, -12] as V3,
	cerdos2: [22, 0, -12] as V3,
	casa: [-2, 0, -32] as V3,
	silo: [6, 0, -28] as V3,
	tanque: [-3.8, 0, -18] as V3,
	gate: [0, 0, 26] as V3,
};

export const Farm: React.FC<{frame: number; children?: React.ReactNode}> = ({frame, children}) => {
	const trees = useMemo(() => {
		const r = rng(5);
		const list: {kind: number; pos: V3; s: number; rot: number}[] = [];
		for (let i = 0; i < 70; i++) {
			const a = r() * PI * 2;
			const d = 42 + r() * 50;
			const pos: V3 = [Math.cos(a) * d, 0, Math.sin(a) * d - 8];
			list.push({kind: r() < 0.55 ? 0 : r() < 0.6 ? 1 : 2, pos, s: 0.8 + r() * 0.6, rot: r() * 6});
		}
		// árboles junto al camino
		for (let z = 40; z > 6; z -= 7) {
			list.push({kind: 0, pos: [-6.5, 0, z + r() * 2], s: 0.9 + r() * 0.3, rot: r() * 6});
			list.push({kind: 0, pos: [7, 0, z - 3 + r() * 2], s: 0.8 + r() * 0.3, rot: r() * 6});
		}
		return list;
	}, []);
	const hills = useMemo(() => {
		const r = rng(11);
		return Array.from({length: 16}).map((_, i) => {
			const a = (i / 16) * PI * 2 + r() * 0.3;
			const d = 150 + r() * 60;
			return {pos: [Math.cos(a) * d, -6, Math.sin(a) * d - 30] as V3, s: [40 + r() * 40, 16 + r() * 22, 30 + r() * 20] as V3, c: i % 3};
		});
	}, []);
	return (
		<group>
			<Sky />
			<fog attach="fog" args={['#cfeafc', 90, 330]} />
			<Clouds frame={frame} />
			{/* suelo */}
			<mesh rotation={[-PI / 2, 0, 0]} receiveShadow>
				<planeGeometry args={[900, 900]} />
				<Mat color="#82c35a" rough={1} />
			</mesh>
			{/* parches de pasto */}
			{Array.from({length: 22}).map((_, i) => {
				const r = rng(300 + i);
				return (
					<mesh key={i} position={[-60 + r() * 120, 0.01, -60 + r() * 100]} rotation={[-PI / 2, 0, r() * 3]} receiveShadow>
						<circleGeometry args={[3 + r() * 6, 18]} />
						<Mat color={i % 2 ? '#74b84d' : '#8ccb62'} rough={1} />
					</mesh>
				);
			})}
			{hills.map((h, i) => (
				<mesh key={i} position={h.pos} scale={h.s}>
					<sphereGeometry args={[1, 24, 16]} />
					<Mat color={['#5fa64a', '#6db352', '#4f9440'][h.c]} rough={1} />
				</mesh>
			))}
			{/* caminos */}
			<Road points={[[0, 80], [0.5, 40], [0, 18], [0, -2], [0, -26]]} />
			<Road points={[[0, 0], [-8, -2], [-15, -0.5]]} width={2.6} />
			<Road points={[[0, -2], [9, -1], [13, 0], [22, 0]]} width={2.6} />
			{/* edificaciones */}
			<Shed position={LAYOUT.gallinero} w={8} d={20} roof="#c2492f" label="GALLINERO" />
			<Shed position={LAYOUT.cerdos1} w={7} d={20} roof="#6f8aa6" wall="#f2e6c9" label="MATERNIDAD" mesh={false} low={1.3} />
			<Shed position={LAYOUT.cerdos2} w={7} d={20} roof="#6f8aa6" wall="#f2e6c9" label="ENGORDE" mesh={false} low={1.3} />
			<House position={LAYOUT.casa} />
			<Silo position={LAYOUT.silo} />
			<Silo position={[9.5, 0, -28]} />
			<WaterTank position={LAYOUT.tanque} />
			<Gate position={LAYOUT.gate} />
			{/* cercas */}
			<Fence from={[-3, 24]} to={[-3, 4]} />
			<Fence from={[3, 24]} to={[3, 6]} />
			{/* patio de las gallinas */}
			<Fence from={[-10.6, -4]} to={[-6, -4]} />
			<Fence from={[-6, -4]} to={[-6, -18]} />
			<Fence from={[-6, -18]} to={[-10.6, -18]} />
			{/* corral exterior de cerdos */}
			<Fence from={[9, 4]} to={[18, 4]} />
			<Fence from={[18, 4]} to={[18, 11]} />
			<Fence from={[18, 11]} to={[9, 11]} />
			<Fence from={[9, 11]} to={[9, 4]} />
			{/* vegetación */}
			{trees.map((t, i) =>
				t.kind === 0 ? (
					<Palm key={i} position={t.pos} height={6 + t.s * 2.5} rotY={t.rot} lean={0.1 + (i % 4) * 0.06} frame={frame} />
				) : t.kind === 1 ? (
					<RoundTree key={i} position={t.pos} scale={t.s} color={i % 2 ? '#3d8f3f' : '#47a447'} />
				) : (
					<Banana key={i} position={t.pos} frame={frame} />
				),
			)}
			{[
				[-20, 0, 6],
				[-24, 0, -2],
				[26, 0, 4],
				[-10, 0, -30],
				[12, 0, -34],
			].map((p, i) => (
				<RoundTree key={`r${i}`} position={p as V3} scale={1.1} />
			))}
			{[
				[-6, 0, 10],
				[6, 0, 14],
				[-7, 0, 20],
				[7, 0, 21],
				[-11, 0, 3],
				[19.5, 0, 6],
			].map((p, i) => (
				<Bush key={`b${i}`} position={p as V3} scale={1 + (i % 3) * 0.2} />
			))}
			{/* pila de bandejas junto al gallinero */}
			<EggTray position={[-12.6, 0.02, 1.6]} stacked={3} />
			{children}
		</group>
	);
};
