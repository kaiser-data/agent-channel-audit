import { Composition } from 'remotion';
import { Promo, PromoFeed, totalFrames, FPS } from './Promo';

export const Root: React.FC = () => (
  <>
    <Composition id="Promo" component={Promo} durationInFrames={totalFrames()} fps={FPS} width={1920} height={1080} />
    <Composition id="PromoFeed" component={PromoFeed} durationInFrames={totalFrames()} fps={FPS} width={1080} height={1350} />
  </>
);
