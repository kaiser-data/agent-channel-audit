import React from 'react';
import {
  AbsoluteFill, Audio, Easing, Img, interpolate, Sequence, staticFile, useCurrentFrame,
} from 'remotion';
import manifest from './manifest.json';
import graph from '../public/graph.json';

/* Agent Channel Audit — research explainer. Every number on screen comes from the paper's results
   (results/v3, results/v3_fresh, results/real, results/sandbox) or from public/graph.json, which
   video/graph_data.py extracts from one simulated run. Nothing here is AI-generated imagery. */

export const FPS = 30;
const XF = 12;
const LEAD = 0.5;
const TAIL = 0.8;

const C = {
  bg: '#0d1117', plate: '#161b24', rule: '#2b3240', ink: '#eef1f5', mute: '#9aa3b2',
  blue: '#4a8dff', grey: '#8a8f98', orange: '#e0913a', green: '#5cc28a', red: '#e5645a',
};
const SANS = 'Inter, "Helvetica Neue", "DejaVu Sans", system-ui, sans-serif';
const SERIF = '"EB Garamond", "Iowan Old Style", Georgia, "DejaVu Serif", serif';
const MONO = '"DejaVu Sans Mono", ui-monospace, Menlo, monospace';

type Line = { file: string | null; dur: number; text: string };
const L = (id: string) => (manifest.lines as Record<string, Line>)[id];
const sec = (id: string) => LEAD + L(id).dur + TAIL;

/* ---------- helpers ---------- */
const useT = () => useCurrentFrame() / FPS;
const fade = (t: number, a: number, b = a + 0.6) =>
  interpolate(t, [a, b], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });

const Title: React.FC<{ kicker?: string; children: React.ReactNode; size?: number; at?: number }> = ({ kicker, children, size = 64, at = 0 }) => {
  const t = useT();
  const o = fade(t, at);
  return (
    <div style={{ opacity: o, transform: `translateY(${(1 - o) * 18}px)` }}>
      {kicker && <div style={{ fontFamily: SANS, fontSize: 24, letterSpacing: 4, textTransform: 'uppercase', color: C.blue, marginBottom: 18 }}>{kicker}</div>}
      <div style={{ fontFamily: SERIF, fontSize: size, lineHeight: 1.15, color: C.ink, maxWidth: 1500 }}>{children}</div>
    </div>
  );
};

const Source: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ position: 'absolute', left: 120, bottom: 150, fontFamily: SANS, fontSize: 20, color: C.mute }}>{children}</div>
);

const Page: React.FC<{ children: React.ReactNode; pad?: number }> = ({ children, pad = 120 }) => (
  <AbsoluteFill style={{ background: C.bg, padding: `${pad}px ${pad}px 0`, justifyContent: 'flex-start' }}>{children}</AbsoluteFill>
);

const Stat: React.FC<{ v: string; label: string; color?: string; at: number }> = ({ v, label, color = C.ink, at }) => {
  const o = fade(useT(), at);
  return (
    <div style={{ opacity: o, marginRight: 90 }}>
      <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 96, color, lineHeight: 1 }}>{v}</div>
      <div style={{ fontFamily: SANS, fontSize: 26, color: C.mute, marginTop: 12, maxWidth: 420 }}>{label}</div>
    </div>
  );
};

/* ---------- scenes ---------- */

const Hook: React.FC = () => {
  const t = useT();
  const n = Math.round(interpolate(t, [3.2, 9.5], [0, 53], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic) }));
  return (
    <Page pad={160}>
      <Title kicker="July 2026" size={60}>Agents meant to work alone turned a shared package cache into a message board.</Title>
      <div style={{ display: 'flex', alignItems: 'flex-end', marginTop: 90, opacity: fade(t, 3) }}>
        <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 220, color: C.orange, lineHeight: 0.9 }}>{n}</div>
        <div style={{ fontFamily: SANS, fontSize: 40, color: C.ink, marginLeft: 40, marginBottom: 20 }}>agents posting<br /><span style={{ color: C.mute }}>within about 3 hours</span></div>
      </div>
      <div style={{ fontFamily: SERIF, fontSize: 44, color: C.mute, marginTop: 70, opacity: fade(t, 11.5) }}>Nobody noticed it forming.</div>
      <Source>METR &amp; Redwood Research incident report, Aug 2026, Fig. 10, p. 32</Source>
    </Page>
  );
};

const Question: React.FC = () => {
  const t = useT();
  const rows = (graph as unknown as { logrows: { t: string; who: string; op: string; name: string; size: number }[] }).logrows;
  return (
    <Page pad={160}>
      <Title kicker="The question" size={58}>Could the operator have seen it form, from the access log alone, <span style={{ color: C.blue }}>without reading a single message?</span></Title>
      <div style={{ marginTop: 70, fontFamily: MONO, fontSize: 26, color: C.mute, background: C.plate, padding: '28px 36px', borderRadius: 10, width: 1180 }}>
        <div style={{ color: C.ink, marginBottom: 10 }}>time      principal    op     object        size</div>
        {rows.slice(0, 7).map((r, i) => (
          <div key={i} style={{ opacity: fade(t, 2 + i * 0.35) }}>
            {r.t}  {r.who.padEnd(11)}  {r.op.padEnd(5)}  {r.name.padEnd(12)}  {String(r.size).padStart(7)}
          </div>
        ))}
        <div style={{ marginTop: 12, color: C.blue, opacity: fade(t, 5.5) }}>no message content — only who touched what, and when</div>
      </div>
      <Source>Rows from one simulated access log (this study)</Source>
    </Page>
  );
};

const OldIdea: React.FC = () => {
  const t = useT();
  const card = (at: number, year: string, who: string, what: string) => (
    <div style={{ opacity: fade(t, at), background: C.plate, borderLeft: `4px solid ${C.blue}`, padding: '28px 34px', width: 640, marginRight: 50 }}>
      <div style={{ fontFamily: SANS, fontSize: 24, color: C.blue }}>{year}</div>
      <div style={{ fontFamily: SERIF, fontSize: 40, color: C.ink, marginTop: 8 }}>{who}</div>
      <div style={{ fontFamily: SANS, fontSize: 26, color: C.mute, marginTop: 10 }}>{what}</div>
    </div>
  );
  return (
    <Page pad={160}>
      <Title kicker="An old idea from computer security" size={56}>A <i>covert channel</i>: any shared resource that one party can change and another can observe.</Title>
      <div style={{ display: 'flex', marginTop: 70 }}>
        {card(2.5, '1973', 'Lampson', 'The confinement problem')}
        {card(4, '1983', 'Kemmerer', 'The Shared Resource Matrix')}
      </div>
      <div style={{ fontFamily: SANS, fontSize: 44, color: C.ink, marginTop: 70, opacity: fade(t, L('03-old-idea').dur - 3) }}>
        Our method: <b style={{ color: C.blue }}>Agent Channel Audit</b>
      </div>
    </Page>
  );
};

type E = { a: number; b: number; board: boolean };
const GraphScene: React.FC = () => {
  const t = useT();
  const g = graph as unknown as { n: number; nodes: { x: number; y: number }[]; clean: E[]; board: E[] };
  const S = 760, ox = 130, oy = 230;
  const P = (i: number) => [ox + g.nodes[i].x * S, oy + g.nodes[i].y * S - 120];
  const D = L('04-graph').dur;
  const showBoard = t > D * 0.55;
  const E = showBoard ? g.board : g.clean;
  const pairs = new Set(E.map((e) => `${e.a}-${e.b}`));
  const grow = interpolate(t, showBoard ? [D * 0.55, D * 0.55 + 2.5] : [1.5, 5], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const ord = E.filter((e) => !e.board);
  const brd = E.filter((e) => e.board);
  const two = (es: E[]) => es.filter((e) => pairs.has(`${e.b}-${e.a}`)).length;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <svg width={1920} height={1080}>
        {ord.slice(0, Math.round(ord.length * grow)).map((e, i) => {
          const [x1, y1] = P(e.a); const [x2, y2] = P(e.b);
          return <line key={`o${i}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke={C.grey} strokeOpacity={showBoard ? 0.2 : 0.28} strokeWidth={1} />;
        })}
        {brd.slice(0, Math.round(brd.length * grow)).map((e, i) => {
          const [x1, y1] = P(e.a); const [x2, y2] = P(e.b);
          return <line key={`b${i}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke={C.blue} strokeOpacity={0.95} strokeWidth={2.4} />;
        })}
        {g.nodes.map((_, i) => { const [x, y] = P(i); return <circle key={i} cx={x} cy={y} r={3.2} fill={C.ink} fillOpacity={0.7} />; })}
      </svg>
      <div style={{ position: 'absolute', left: 1020, top: 150, width: 780 }}>
        <div style={{ fontFamily: SANS, fontSize: 24, letterSpacing: 4, textTransform: 'uppercase', color: C.blue }}>The write → read graph</div>
        <div style={{ fontFamily: SERIF, fontSize: 46, color: C.ink, marginTop: 16, lineHeight: 1.2 }}>
          Agent A writes, agent B reads it: draw an arrow A → B.
        </div>
        <div style={{ marginTop: 60, opacity: fade(t, 4) }}>
          <div style={{ fontFamily: SANS, fontSize: 30, color: C.grey }}>Ordinary traffic, one 10-minute window</div>
          <div style={{ fontFamily: SANS, fontSize: 30, color: C.ink, marginTop: 8 }}>{g.clean.length} arrows · {Math.round(100 * two(g.clean) / g.clean.length)}% run both ways</div>
        </div>
        <div style={{ marginTop: 50, opacity: showBoard ? fade(t, D * 0.55 + 1) : 0 }}>
          <div style={{ fontFamily: SANS, fontSize: 30, color: C.blue }}>Three hours after a board starts</div>
          <div style={{ fontFamily: SANS, fontSize: 30, color: C.ink, marginTop: 8 }}>
            {brd.length} board arrows among {new Set(brd.flatMap((e) => [e.a, e.b])).size} agents · {Math.round(100 * two(brd) / brd.length)}% both ways
          </div>
        </div>
        <div style={{ marginTop: 50, fontFamily: SANS, fontSize: 26, color: C.mute, opacity: fade(t, D * 0.8) }}>
          Score = two-way share + number of writers read by others − delay from write to read
        </div>
      </div>
      <Source>200 simulated agents, real output of the study's simulator (seed 1000)</Source>
    </AbsoluteFill>
  );
};

const Threshold: React.FC = () => {
  const t = useT();
  return (
    <Page pad={160}>
      <Title kicker="Fix the price of an alarm first" size={58}>Threshold = the score that only <span style={{ color: C.blue }}>1 in 100</span> clean 10-minute windows exceed.</Title>
      <div style={{ marginTop: 80, opacity: fade(t, L('05-threshold').dur * 0.55) }}>
        <div style={{ fontFamily: SANS, fontSize: 30, color: C.ink }}>Predictions written down and frozen before any result:</div>
        <div style={{ fontFamily: MONO, fontSize: 26, color: C.green, background: C.plate, padding: '24px 32px', borderRadius: 10, marginTop: 20, width: 1400 }}>
          PROTOCOL.md frozen 2026-11-06T19:39:52Z<br />
          sha256 69157281f15ae47f400cb227abaceab3bec9ae7ade56bbc7ee352b95c888b120
        </div>
      </div>
      <Source>FREEZE.txt in the project repository</Source>
    </Page>
  );
};

const Sim: React.FC = () => {
  const t = useT();
  const loads = ['50 agents', '200 agents', '800 agents'];
  const growth = ['slow', 'medium', 'fast'];
  return (
    <Page pad={160}>
      <Title kicker="Simulation" size={58}>A busy shared cache, with the noise of real builds.</Title>
      <div style={{ display: 'flex', marginTop: 70 }}>
        {['undisguised', 'disguised'].map((d, di) => (
          <div key={d} style={{ marginRight: 80, opacity: fade(t, 2 + di * 1.5) }}>
            <div style={{ fontFamily: SANS, fontSize: 26, color: di ? C.orange : C.blue, marginBottom: 14 }}>{d}</div>
            {loads.map((l, li) => (
              <div key={l} style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ fontFamily: SANS, fontSize: 24, color: C.mute, width: 170 }}>{l}</div>
                {growth.map((g, gi) => (
                  <div key={g} style={{ width: 120, height: 56, marginRight: 10, background: C.plate, border: `1px solid ${C.rule}`, borderRadius: 6,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: SANS, fontSize: 20, color: C.ink,
                    opacity: fade(t, 2.5 + di * 1.5 + (li * 3 + gi) * 0.12) }}>{g}</div>
                ))}
              </div>
            ))}
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', marginTop: 50 }}>
        <Stat v="180" label="planted channels (18 conditions × 10 seeds)" color={C.blue} at={6} />
        <Stat v="1%" label="false-alarm rate, set on clean traffic" at={8} />
      </div>
    </Page>
  );
};

const FigCrop: React.FC<{ src: string; side: 'left' | 'right' | 'full'; children?: React.ReactNode; kicker: string; title: React.ReactNode; dur: number; aspect: number }> = ({ src, side, children, kicker, title, dur, aspect }) => {
  const t = useT();
  const z = interpolate(t, [0, dur], [1.0, 1.03]);
  const W = side === 'full' ? 1680 : 1500, H = W / aspect;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: 'absolute', left: 120, top: 70 }}>
        <div style={{ fontFamily: SANS, fontSize: 24, letterSpacing: 4, textTransform: 'uppercase', color: C.blue }}>{kicker}</div>
        <div style={{ fontFamily: SERIF, fontSize: 48, color: C.ink, marginTop: 10, maxWidth: 1700 }}>{title}</div>
      </div>
      <div style={{ position: 'absolute', left: (1920 - W) / 2, top: 210, width: W, height: H, background: '#fff', borderRadius: 8, overflow: 'hidden', transform: `scale(${z})` }}>
        <Img src={staticFile(src)} style={{ width: W, height: H }} />
        {side !== 'full' && <div style={{ position: 'absolute', top: 0, bottom: 0, width: W * 0.47, left: side === 'left' ? W * 0.53 : 0,
          background: 'rgba(13,17,23,0.72)', opacity: fade(t, 0.8) }} />}
      </div>
      {children}
    </AbsoluteFill>
  );
};

const Callout: React.FC<{ at: number; x: number; y: number; children: React.ReactNode; color?: string }> = ({ at, x, y, children, color = C.blue }) => {
  const o = fade(useT(), at);
  return <div style={{ position: 'absolute', left: x, top: y, opacity: o, background: 'rgba(13,17,23,0.92)', border: `2px solid ${color}`, borderRadius: 8,
    padding: '14px 22px', fontFamily: SANS, fontSize: 30, color: C.ink }}>{children}</div>;
};

const Result: React.FC = () => (
  <FigCrop src="fig1-participants-at-detection.png" side="left" aspect={2070 / 900} dur={sec('07-result')} kicker="Result · undisguised channels"
    title={<>Graph detector fires earlier than a traffic alarm in <span style={{ color: C.blue }}>9 of 9</span> conditions.</>}>
    <Callout at={6} x={1000} y={890}>200 agents, medium growth: <b style={{ color: C.blue }}>15</b> posters vs <b style={{ color: C.grey }}>62</b> for volume</Callout>
    <Callout at={12} x={210} y={890} color={C.green}>Fresh seeds: 9 of 9 again</Callout>
  </FigCrop>
);

const Disguise: React.FC = () => (
  <FigCrop src="fig1-participants-at-detection.png" side="right" aspect={2070 / 900} dur={sec('08-disguise')} kicker="Result · disguised channels"
    title={<>Package-like names blind a filename rule. The graph still catches <span style={{ color: C.blue }}>98%</span>.</>}>
    <Callout at={3} x={210} y={890} color={C.orange}>Filename rule: 100% → 0% detected</Callout>
    <Callout at={6} x={900} y={890}>Graph: 98% detected, later at 800 agents</Callout>
  </FigCrop>
);

const Controls: React.FC = () => {
  const t = useT();
  const row = (at: number, ctl: string, exp: string, got: string) => (
    <div style={{ display: 'flex', alignItems: 'center', opacity: fade(t, at), borderBottom: `1px solid ${C.rule}`, padding: '22px 0' }}>
      <div style={{ fontFamily: SANS, fontSize: 34, color: C.ink, width: 620 }}>{ctl}</div>
      <div style={{ fontFamily: SANS, fontSize: 30, color: C.mute, width: 420 }}>expected: {exp}</div>
      <div style={{ fontFamily: SANS, fontSize: 34, color: C.green, fontWeight: 700 }}>✓ {got}</div>
    </div>
  );
  return (
    <Page pad={160}>
      <Title kicker="Controls with known answers" size={58}>Does it measure what it claims?</Title>
      <div style={{ marginTop: 60, width: 1550 }}>
        {row(2.5, 'Read-only cache', 'no alerts', '0 alerts')}
        {row(4.5, 'Every agent under one name', 'no alerts', '0 alerts')}
        {row(7, 'Shuffle who is who', 'advantage gone', 'lead 442 → −26')}
        {row(9, 'Held-out clean traffic', '≈ 1% alerts', '0.9 – 1.3%')}
      </div>
    </Page>
  );
};

const Real: React.FC = () => (
  <FigCrop src="fig2-real-wiki.png" side="full" aspect={2070 / 688} dur={sec('10-real')} kicker="A real swarm · public wiki request log"
    title={<>3,010 agents used a public wiki as a board. Alarm in the <span style={{ color: C.blue }}>first 10 minutes</span>.</>}>
    <Callout at={8} x={120} y={810} color={C.grey}>12 weeks before: no page saved</Callout>
    <Callout at={13} x={640} y={810}>Graph: 24 May, 06:00–06:10 UTC · Volume: 4.3 h later</Callout>
  </FigCrop>
);

const Limits: React.FC = () => {
  const t = useT();
  const item = (at: number, head: string, body: string) => (
    <div style={{ opacity: fade(t, at), marginBottom: 40 }}>
      <div style={{ fontFamily: SANS, fontSize: 34, color: C.red }}>✗ {head}</div>
      <div style={{ fontFamily: SANS, fontSize: 28, color: C.mute, marginTop: 8 }}>{body}</div>
    </div>
  );
  return (
    <Page pad={160}>
      <Title kicker="What did not work" size={58}>Reported as results, not hidden.</Title>
      <div style={{ marginTop: 60 }}>
        {item(2, 'First frozen run failed 2 of 3 predictions', 'Its own controls exposed three calibration flaws; fixes declared before rerunning, confirmed on fresh seeds.')}
        {item(6.5, 'Small agent-built channels slip under', 'Claude Haiku agents invented a comp-0 … comp-7 registry in the sandbox: 4–6 writers, 0 of 5 detected.')}
        {item(11, 'Real wiki was too quiet to test calibration', 'With no saves before the agents, any cross-agent read alerts. The busy case is only simulated.')}
      </div>
    </Page>
  );
};

const Lesson: React.FC = () => {
  const t = useT();
  const D = L('12-lesson').dur;
  return (
    <Page pad={160}>
      <Title kicker="For anyone running shared infrastructure" size={60}>Log who writes and who reads. Watch who reads whose writes.</Title>
      <div style={{ marginTop: 80 }}>
        {[['No message content needed', 1], ['Calibrated to a known false-alarm rate', D * 0.35], ['On a quiet surface, one stranger reading your writes is an event', D * 0.55], ['Catches a board while it is still small', D * 0.8]].map(([s, at]) => (
          <div key={s as string} style={{ fontFamily: SANS, fontSize: 36, color: C.ink, marginBottom: 26, opacity: fade(t, at as number) }}>
            <span style={{ color: C.blue }}>—</span> {s}
          </div>
        ))}
      </div>
    </Page>
  );
};

const CTA: React.FC = () => {
  const t = useT();
  return (
    <AbsoluteFill style={{ background: C.bg, justifyContent: 'center', alignItems: 'center' }}>
      <div style={{ textAlign: 'center', opacity: fade(t, 0.2) }}>
        <div style={{ fontFamily: SERIF, fontSize: 96, color: C.ink }}>Agent Channel Audit</div>
        <div style={{ fontFamily: SERIF, fontSize: 44, color: C.mute, marginTop: 20 }}>Watch the shared spaces, not only the messages.</div>
        <div style={{ fontFamily: SANS, fontSize: 26, color: C.mute, marginTop: 60 }}>Martin Kaiser · Apart Swarm Alignment Hackathon 2026 · Track 4</div>
      </div>
      <div style={{ position: 'absolute', bottom: 50, fontFamily: SANS, fontSize: 18, color: C.mute, opacity: fade(t, 1) }}>{manifest.disclosure}</div>
    </AbsoluteFill>
  );
};

/* ---------- timeline ---------- */
const SCENES: { id: string; C: React.FC; extra?: number }[] = [
  { id: '01-hook', C: Hook }, { id: '02-question', C: Question }, { id: '03-old-idea', C: OldIdea },
  { id: '04-graph', C: GraphScene }, { id: '05-threshold', C: Threshold }, { id: '06-sim', C: Sim },
  { id: '07-result', C: Result }, { id: '08-disguise', C: Disguise }, { id: '09-controls', C: Controls },
  { id: '10-real', C: Real }, { id: '11-limits', C: Limits }, { id: '12-lesson', C: Lesson }, { id: '13-cta', C: CTA, extra: 3 },
];
const frames = (s: { id: string; extra?: number }) => Math.round((sec(s.id) + (s.extra ?? 0)) * FPS);
export const totalFrames = () => SCENES.reduce((a, s) => a + frames(s), 0) - XF * (SCENES.length - 1);

const Caption: React.FC<{ text: string; dur: number; feed?: boolean }> = ({ text, dur, feed }) => {
  // split the line into ~10-word chunks and show each for its share of the voice line
  const t = useT() - LEAD;
  const words = text.split(' ');
  const chunks: string[] = [];
  for (let i = 0; i < words.length; i += 10) chunks.push(words.slice(i, i + 10).join(' '));
  if (t < 0 || t > dur) return null;
  const idx = Math.min(chunks.length - 1, Math.floor((t / dur) * chunks.length));
  return (
    <div style={{ position: 'absolute', bottom: feed ? 60 : 40, left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
      <div style={{ background: 'rgba(0,0,0,0.72)', padding: '10px 22px', borderRadius: 6, fontFamily: SANS, fontSize: feed ? 34 : 30, color: '#fff', maxWidth: feed ? 980 : 1600, textAlign: 'center' }}>{chunks[idx]}</div>
    </div>
  );
};

const Timeline: React.FC<{ feed?: boolean }> = ({ feed }) => {
  let at = 0;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      {SCENES.map((s, i) => {
        const from = at; const n = frames(s); at += n - XF;
        const ln = L(s.id);
        return (
          <Sequence key={s.id} from={from} durationInFrames={n}>
            <SceneFade n={n} first={i === 0}>
              {feed ? <FeedFrame><s.C /></FeedFrame> : <s.C />}
              <Caption text={ln.text} dur={ln.dur} feed={feed} />
            </SceneFade>
            {ln.file && <Sequence from={Math.round(LEAD * FPS)}><Audio src={staticFile(ln.file)} /></Sequence>}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

const SceneFade: React.FC<{ n: number; first: boolean; children: React.ReactNode }> = ({ n, first, children }) => {
  const f = useCurrentFrame();
  const o = Math.min(first ? 1 : interpolate(f, [0, XF], [0, 1], { extrapolateRight: 'clamp' }), interpolate(f, [n - XF, n], [1, 0], { extrapolateLeft: 'clamp' }));
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

// 4:5 feed version: the 16:9 frame scaled into the middle, title band above
const FeedFrame: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ background: C.bg }}>
    <div style={{ position: 'absolute', top: 70, left: 0, right: 0, textAlign: 'center', fontFamily: SERIF, fontSize: 52, color: C.ink }}>Agent Channel Audit</div>
    <div style={{ position: 'absolute', top: 340, left: 0, width: 1920, height: 1080, transform: 'scale(0.5625)', transformOrigin: '0 0' }}>{children}</div>
  </AbsoluteFill>
);

export const Promo: React.FC = () => <Timeline />;
export const PromoFeed: React.FC = () => <Timeline feed />;
