import React from "react";
import { Composition, Still } from "remotion";
import { PeajesVideo } from "./Video";
import { Miniatura } from "./Thumbnail";
import { FPS, H, W } from "./theme";
import { TOTAL_SECONDS } from "./timeline";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Peajes" component={PeajesVideo} durationInFrames={Math.round(TOTAL_SECONDS * FPS)} fps={FPS} width={W} height={H} />
    <Still id="Miniatura" component={Miniatura} width={W} height={H} />
  </>
);
