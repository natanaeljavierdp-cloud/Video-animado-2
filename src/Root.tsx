import React from 'react';
import {Composition} from 'remotion';
import '@fontsource/montserrat/500.css';
import '@fontsource/montserrat/600.css';
import '@fontsource/montserrat/700.css';
import '@fontsource/montserrat/800.css';
import {GranjaVideo} from './GranjaVideo';
import timings from './timings.json';

export const RemotionRoot: React.FC = () => (
	<Composition
		id="GranjaIntegrada"
		component={GranjaVideo}
		durationInFrames={timings.durationInFrames}
		fps={timings.fps}
		width={1920}
		height={1080}
	/>
);
