import {Config} from '@remotion/cli/config';

// WebGL por software (SwiftShader/ANGLE): funciona en servidores sin GPU.
Config.setChromiumOpenGlRenderer('swangle');
Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(92);
Config.setCodec('h264');
Config.setCrf(18);
Config.setPixelFormat('yuv420p');
if (process.env.REMOTION_BROWSER) {
	Config.setBrowserExecutable(process.env.REMOTION_BROWSER);
}
