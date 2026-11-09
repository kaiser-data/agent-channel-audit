import React from 'react';
import {
  AbsoluteFill, Audio, Easing, interpolate, Sequence, staticFile, useCurrentFrame,
} from 'remotion';
import manifest from './manifest.json';
import data from '../public/data.json';

/* Close the Board, Agents Move — research explainer. Every number on screen comes from the paper
   (paper/main.tex, printed by analyze.py) or from public/data.json, which video/log_excerpt.py extracts
   from one real run (DeepSeek-V4.1-Flash, CLOSE, seed 7) and from paper/fig1-numbers.txt.
   Nothing here is AI-generated imagery. */

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

type Row = { r: number; w: number | null; s: string; txt: string; ok: boolean };
type Counts = Record<string, Record<string, { cache: number; dashboard: number }>>;
const D = data as unknown as { rows: Row[]; counts: Counts; sum: number; correct: number; versions: number[] };

/* ---------- helpers ---------- */
const useT = () => useCurrentFrame() / FPS;
const fade = (t: number, a: number, b = a + 0.6) =>
  interpolate(t, [a, b], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });

const Title: React.FC<{ kicker?: string; children: React.ReactNode; size?: number; at?: number }> = ({ kicker, children, size = 64, at = 0 }) => {
  const o = fade(useT(), at);
  return (
    <div style={{ opacity: o, transform: `translateY(${(1 - o) * 18}px)` }}>
      {kicker && <div style={{ fontFamily: SANS, fontSize: 24, letterSpacing: 4, textTransform: 'uppercase', color: C.blue, marginBottom: 18 }}>{kicker}</div>}
      <div style={{ fontFamily: SERIF, fontSize: size, lineHeight: 1.15, color: C.ink, maxWidth: 1550 }}>{children}</div>
    </div>
  );
};

const Source: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ position: 'absolute', left: 160, bottom: 140, fontFamily: SANS, fontSize: 20, color: C.mute }}>{children}</div>
);

const Page: React.FC<{ children: React.ReactNode; pad?: number }> = ({ children, pad = 160 }) => (
  <AbsoluteFill style={{ background: C.bg, padding: `${pad}px ${pad}px 0`, justifyContent: 'flex-start' }}>{children}</AbsoluteFill>
);

const Stat: React.FC<{ v: string; label: string; color?: string; at: number; w?: number }> = ({ v, label, color = C.ink, at, w = 420 }) => {
  const o = fade(useT(), at);
  return (
    <div style={{ opacity: o, marginRight: 80, width: w }}>
      <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 110, color, lineHeight: 1 }}>{v}</div>
      <div style={{ fontFamily: SANS, fontSize: 28, color: C.mute, marginTop: 14 }}>{label}</div>
    </div>
  );
};

/* ---------- scenes ---------- */

const Hook: React.FC = () => {
  const t = useT();
  const d = L('01-hook').dur;
  const cut = fade(t, d * 0.62, d * 0.62 + 0.5);
  return (
    <Page>
      <Title kicker="July 2026" size={60}>Agents meant to work alone turned a shared package cache into a message board.</Title>
      <div style={{ display: 'flex', alignItems: 'center', marginTop: 110, opacity: fade(t, d * 0.55) }}>
        <div style={{ position: 'relative', width: 520, height: 230, background: C.plate, border: `2px solid ${C.rule}`, borderRadius: 12,
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: MONO, fontSize: 30, color: C.mute }}>
          shared cache
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: cut }}>
            <div style={{ border: `5px solid ${C.red}`, color: C.red, fontFamily: SANS, fontWeight: 700, fontSize: 44, padding: '8px 26px', transform: 'rotate(-8deg)', background: 'rgba(13,17,23,0.85)' }}>CLOSED</div>
          </div>
        </div>
        <div style={{ fontFamily: SERIF, fontSize: 52, color: C.ink, marginLeft: 70, opacity: cut }}>The first reflex:<br /><span style={{ color: C.red }}>close it.</span></div>
      </div>
      <Source>METR &amp; Redwood Research incident report, Aug 2026</Source>
    </Page>
  );
};

const Question: React.FC = () => {
  const t = useT();
  const d = L('02-question').dur;
  const card = (at: number, color: string, head: string, sub: string, pct: string) => (
    <div style={{ opacity: fade(t, at), background: C.plate, borderLeft: `5px solid ${color}`, padding: '30px 36px', width: 660, marginRight: 50 }}>
      <div style={{ fontFamily: SERIF, fontSize: 46, color: C.ink }}>{head}</div>
      <div style={{ fontFamily: SANS, fontSize: 26, color: C.mute, marginTop: 8 }}>{sub}</div>
      <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 80, color, marginTop: 20 }}>{pct}</div>
      <div style={{ fontFamily: SANS, fontSize: 22, color: C.mute }}>of 574 observations</div>
    </div>
  );
  return (
    <Page>
      <Title kicker="The question" size={58}>Close the channel: does coordination <span style={{ color: C.green }}>stop</span>, or does it <span style={{ color: C.orange }}>move</span>?</Title>
      <div style={{ display: 'flex', marginTop: 70 }}>
        {card(d * 0.3, C.orange, 'Displacement', 'the activity moves elsewhere', '26%')}
        {card(d * 0.5, C.green, 'Diffusion of benefits', 'the activity stops', '27%')}
      </div>
      <div style={{ fontFamily: SANS, fontSize: 32, color: C.ink, marginTop: 50, opacity: fade(t, d * 0.75) }}>
        Theory: it depends on whether an <b style={{ color: C.blue }}>alternative</b> is available.
      </div>
      <Source>Guerette &amp; Bowers 2009, review of 102 crime-prevention evaluations · Reppetto 1976</Source>
    </Page>
  );
};

const Sandbox: React.FC = () => {
  const t = useT();
  const d = L('03-sandbox').dur;
  const closed = fade(t, d * 0.82, d * 0.82 + 0.5);
  const box = (label: string, sub: string, at: number, x: number, color: string, extra?: React.ReactNode) => (
    <div style={{ position: 'absolute', left: x, top: 560, width: 560, height: 210, opacity: fade(t, at), background: C.plate,
      border: `2px solid ${color}`, borderRadius: 12, padding: '26px 32px' }}>
      <div style={{ fontFamily: SANS, fontSize: 38, color: C.ink }}>{label}</div>
      <div style={{ fontFamily: MONO, fontSize: 24, color: C.mute, marginTop: 12 }}>{sub}</div>
      {extra}
    </div>
  );
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: 'absolute', left: 160, top: 120 }}>
        <Title kicker="The sandbox" size={52}>Eight build workers. Each knows one version number. Each must submit the sum of all eight.</Title>
      </div>
      <div style={{ position: 'absolute', left: 160, top: 380, display: 'flex' }}>
        {D.versions.map((v, i) => (
          <div key={i} style={{ opacity: fade(t, 2 + i * 0.2), width: 150, height: 110, marginRight: 32, background: C.plate, border: `1px solid ${C.rule}`, borderRadius: 10,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ fontFamily: SANS, fontSize: 22, color: C.mute }}>worker {i}</div>
            <div style={{ fontFamily: MONO, fontSize: 36, color: C.ink }}>v{v}</div>
          </div>
        ))}
      </div>
      {box('Shared artifact cache', 'put · get · list', d * 0.45, 160, C.blue,
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: closed, background: 'rgba(13,17,23,0.75)', borderRadius: 12 }}>
          <div style={{ border: `5px solid ${C.red}`, color: C.red, fontFamily: SANS, fontWeight: 700, fontSize: 36, padding: '6px 22px', transform: 'rotate(-6deg)' }}>ROUND 8: READ-ONLY</div>
        </div>)}
      {box('CI status dashboard', 'status (80 chars) · dashboard', d * 0.55, 820, C.orange)}
      <div style={{ position: 'absolute', left: 160, top: 830, fontFamily: SANS, fontSize: 32, color: C.ink, opacity: fade(t, d * 0.68) }}>
        No prompt calls either surface a way to communicate.
      </div>
    </AbsoluteFill>
  );
};

const Design: React.FC = () => {
  const t = useT();
  const cond = (at: number, name: string, desc: string, color: string) => (
    <div style={{ opacity: fade(t, at), display: 'flex', alignItems: 'baseline', borderBottom: `1px solid ${C.rule}`, padding: '18px 0' }}>
      <div style={{ fontFamily: MONO, fontSize: 32, color, width: 380 }}>{name}</div>
      <div style={{ fontFamily: SANS, fontSize: 30, color: C.ink }}>{desc}</div>
    </div>
  );
  return (
    <Page>
      <Title kicker="Pre-registered design" size={56}>Four conditions · four models · 160 runs</Title>
      <div style={{ marginTop: 50, width: 1550 }}>
        {cond(1.0, 'OPEN', 'cache writable throughout, dashboard available', C.blue)}
        {cond(1.8, 'CLOSE', 'cache closed at round 8, dashboard available', C.orange)}
        {cond(2.6, 'CLOSE-NOALT', 'cache closed at round 8, no dashboard', C.red)}
        {cond(3.4, 'INDEPENDENT', 'control: no coordination needed', C.green)}
      </div>
      <div style={{ fontFamily: SANS, fontSize: 28, color: C.mute, marginTop: 40, opacity: fade(t, 5) }}>
        DeepSeek-V4.1-Flash · Gemma-3-27B · Qwen3-235B-Instruct · MiniMax-M3.1-Flash — 10 seeds each
      </div>
      <div style={{ fontFamily: MONO, fontSize: 22, color: C.green, background: C.plate, padding: '18px 26px', borderRadius: 10, marginTop: 30, width: 1400, opacity: fade(t, 7) }}>
        PROTOCOL.md frozen 2026-11-08T02:39:45Z · sha256 3c0bebca…66d201d8
      </div>
    </Page>
  );
};

const Bars: React.FC = () => {
  const t = useT();
  const d = L('05-moved').dur;
  const groups: [string, string, string][] = [['open', 'Open', C.blue], ['close', 'Close', C.orange], ['close_noalt', 'Close, no dashboard', C.red]];
  const H = 430, max = 180, bw = 70, base = 840;
  const bar = (x: number, v: number, color: string, at: number, solid: boolean) => {
    const g = interpolate(t, [at, at + 1.2], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });
    const h = (v / max) * H * g;
    return (
      <g key={`${x}`}>
        <rect x={x} y={base - h} width={bw} height={h} fill={solid ? color : 'none'} stroke={color} strokeWidth={3} fillOpacity={0.9} />
        <text x={x + bw / 2} y={base - h - 12} textAnchor="middle" fontFamily={SANS} fontSize={26} fill={C.ink} opacity={g}>{Math.round(v * g)}</text>
      </g>
    );
  };
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: 'absolute', left: 160, top: 90 }}>
        <Title kicker="Result · displacement" size={52}>Every run with a cache channel moved it to the dashboard: <span style={{ color: C.orange }}>12 of 12</span>, median one round.</Title>
      </div>
      <svg width={1920} height={1080} style={{ position: 'absolute', left: 0, top: 0 }}>
        <line x1={150} x2={1800} y1={base} y2={base} stroke={C.rule} strokeWidth={2} />
        {groups.map(([k, name, color], gi) => {
          const x0 = 200 + gi * 540;
          const at = 1.5 + gi * 0.8;
          const c = D.counts[k];
          return (
            <g key={k}>
              {bar(x0, c['1-7'].cache, C.grey, at, true)}
              {bar(x0 + bw + 10, c['1-7'].dashboard, C.orange, at, true)}
              {bar(x0 + 2 * bw + 60, c['8-20'].cache, C.grey, at + 0.4, true)}
              {bar(x0 + 3 * bw + 70, c['8-20'].dashboard, C.orange, at + 0.4, true)}
              <text x={x0 + bw + 5} y={base + 40} textAnchor="middle" fontFamily={SANS} fontSize={22} fill={C.mute}>rounds 1–7</text>
              <text x={x0 + 3 * bw + 65} y={base + 40} textAnchor="middle" fontFamily={SANS} fontSize={22} fill={C.mute}>rounds 8–20</text>
              <text x={x0 + 2 * bw + 35} y={base + 90} textAnchor="middle" fontFamily={SANS} fontSize={30} fill={color}>{name}</text>
            </g>
          );
        })}
        <g opacity={fade(t, 3)}>
          <rect x={1300} y={300} width={26} height={26} fill={C.grey} /><text x={1340} y={322} fontFamily={SANS} fontSize={24} fill={C.mute}>cache</text>
          <rect x={1460} y={300} width={26} height={26} fill={C.orange} /><text x={1500} y={322} fontFamily={SANS} fontSize={24} fill={C.mute}>dashboard</text>
        </g>
      </svg>
      <div style={{ position: 'absolute', left: 1180, top: 470, opacity: fade(t, d * 0.7), background: 'rgba(13,17,23,0.92)', border: `2px solid ${C.orange}`, borderRadius: 8,
        padding: '14px 22px', fontFamily: SANS, fontSize: 30, color: C.ink }}>
        After closure: <b style={{ color: C.orange }}>174</b> dashboard posts vs <b>80</b> with the cache open
      </div>
      <div style={{ position: 'absolute', left: 160, bottom: 120, fontFamily: SANS, fontSize: 20, color: C.mute }}>
        Accepted writes carrying the writer's version number, 4 models × 10 seeds per condition · paper Fig. 1, paper/fig1-numbers.txt
      </div>
    </AbsoluteFill>
  );
};

const Example: React.FC = () => {
  const t = useT();
  const d = L('06-example').dur;
  // keep the run's story readable: cache writes before closure, the closure, then accepted dashboard posts
  const pre = D.rows.filter((r) => r.s === 'cache' && r.ok).slice(0, 4);
  const close = D.rows.filter((r) => r.s === 'operator');
  const post = D.rows.filter((r) => r.s === 'dashboard' && r.r >= 7);
  const pick = (r: Row) => (r.r === 10 && r.w === 4) || (r.r === 13 && r.w === 6) || r.r === 15;
  const shown = [...pre, ...close, ...post.filter(pick)];
  return (
    <Page pad={120}>
      <Title kicker="One real run · DeepSeek-V4.1-Flash, Close, seed 7" size={44}>What the workers wrote, before and after the cache closed</Title>
      <div style={{ marginTop: 40, fontFamily: MONO, fontSize: 25, background: C.plate, padding: '24px 32px', borderRadius: 10, width: 1680 }}>
        {shown.map((r, i) => {
          const color = r.s === 'operator' ? C.red : r.s === 'cache' ? C.grey : C.orange;
          return (
            <div key={i} style={{ opacity: fade(t, 1 + i * (d * 0.7) / shown.length), display: 'flex', padding: '7px 0', color: C.ink }}>
              <span style={{ width: 150, color: C.mute }}>round {r.r + 1}</span>
              <span style={{ width: 170, color }}>{r.s}</span>
              <span style={{ width: 140, color: C.mute }}>{r.w === null ? '' : `worker ${r.w}`}</span>
              <span style={{ color: r.s === 'operator' ? C.red : C.ink }}>{r.txt}</span>
            </div>
          );
        })}
      </div>
      <div style={{ fontFamily: SANS, fontSize: 36, color: C.green, marginTop: 34, opacity: fade(t, d * 0.85) }}>
        ✓ All {D.correct} workers submit {D.sum}, the correct sum.
      </div>
    </Page>
  );
};

const Survived: React.FC = () => {
  const t = useT();
  const d = L('07-survived').dur;
  return (
    <Page>
      <Title kicker="Result · coordination" size={56}>Closing the cache did not stop coordination. Removing the alternative did.</Title>
      <div style={{ display: 'flex', marginTop: 80 }}>
        <Stat v="15%" label="correct sum, cache left open" color={C.blue} at={d * 0.3} />
        <Stat v="19%" label="correct sum after closure, dashboard available" color={C.orange} at={d * 0.15} />
        <Stat v="0%" label="correct sum after closure, no dashboard (0 of 320)" color={C.red} at={d * 0.55} />
      </div>
      <div style={{ fontFamily: SANS, fontSize: 28, color: C.mute, marginTop: 60, opacity: fade(t, d * 0.75) }}>
        Paired by model and seed: Close better in 10 pairs, worse in 0 (sign test p ≈ 0.002). Without a dashboard,<br />
        DeepSeek and MiniMax workers made 4.2 and 6.9 rejected cache writes per run after closure.
      </div>
    </Page>
  );
};

const Content: React.FC = () => {
  const t = useT();
  const d = L('08-content').dur;
  return (
    <Page>
      <Title kicker="Content is not diagnostic" size={56}>Version numbers on the dashboard are also ordinary build status.</Title>
      <div style={{ display: 'flex', marginTop: 70, alignItems: 'flex-start' }}>
        <Stat v="31 / 40" label="runs of the no-coordination task also posted version numbers" color={C.green} at={d * 0.25} w={620} />
        <div style={{ opacity: fade(t, d * 0.65), background: C.plate, borderLeft: `5px solid ${C.blue}`, padding: '28px 34px', width: 760 }}>
          <div style={{ fontFamily: SANS, fontSize: 26, color: C.blue }}>What differs is the pattern</div>
          <div style={{ fontFamily: SERIF, fontSize: 40, color: C.ink, marginTop: 10 }}>Under pressure, workers read each other's posts and act on them.</div>
          <div style={{ fontFamily: SANS, fontSize: 24, color: C.mute, marginTop: 14 }}>The write → read structure that Agent Channel Audit detects without reading content.</div>
        </div>
      </div>
    </Page>
  );
};

const Limits: React.FC = () => {
  const t = useT();
  const d = L('09-limits').dur;
  const item = (at: number, head: string, body: string) => (
    <div style={{ opacity: fade(t, at), marginBottom: 40 }}>
      <div style={{ fontFamily: SANS, fontSize: 34, color: C.red }}>✗ {head}</div>
      <div style={{ fontFamily: SANS, fontSize: 28, color: C.mute, marginTop: 8 }}>{body}</div>
    </div>
  );
  return (
    <Page>
      <Title kicker="Limits" size={58}>Reported, not hidden.</Title>
      <div style={{ marginTop: 60 }}>
        {item(1.5, 'Only two of four models coordinated', 'Displacement rests on 12 runs (10 DeepSeek, 2 MiniMax). Qwen3 and Gemma never built a channel.')}
        {item(d * 0.45, 'A small sandbox', '8 workers, 20 rounds, one closure, agents not told to evade.')}
        {item(d * 0.65, 'The planned panel ran out of API credit', 'Replaced by four Nebius models under a format-only rule declared, with its hash, before any Nebius run.')}
      </div>
    </Page>
  );
};

const Lesson: React.FC = () => {
  const t = useT();
  const d = L('10-lesson').dur;
  return (
    <Page>
      <Title kicker="For operators" size={60}>Closing one channel is not the end of an incident.</Title>
      <div style={{ marginTop: 80 }}>
        {[['List every surface one agent can write and another can read', d * 0.45], ['Close or monitor them together', d * 0.75]].map(([s, at]) => (
          <div key={s as string} style={{ fontFamily: SANS, fontSize: 40, color: C.ink, marginBottom: 30, opacity: fade(t, at as number) }}>
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
        <div style={{ fontFamily: SERIF, fontSize: 92, color: C.ink }}>Close the Board, Agents Move</div>
        <div style={{ fontFamily: SERIF, fontSize: 44, color: C.mute, marginTop: 20 }}>Channel displacement in LLM agent swarms</div>
        <div style={{ fontFamily: SANS, fontSize: 26, color: C.mute, marginTop: 60 }}>Martin Kaiser · Apart Swarm Alignment Hackathon 2026</div>
        <div style={{ fontFamily: MONO, fontSize: 24, color: C.blue, marginTop: 18 }}>github.com/kaiser-data/channel-displacement</div>
      </div>
      <div style={{ position: 'absolute', bottom: 50, fontFamily: SANS, fontSize: 18, color: C.mute, opacity: fade(t, 1) }}>{manifest.disclosure}</div>
    </AbsoluteFill>
  );
};

/* ---------- timeline ---------- */
const SCENES: { id: string; C: React.FC; extra?: number }[] = [
  { id: '01-hook', C: Hook }, { id: '02-question', C: Question }, { id: '03-sandbox', C: Sandbox },
  { id: '04-design', C: Design }, { id: '05-moved', C: Bars }, { id: '06-example', C: Example, extra: 1.5 },
  { id: '07-survived', C: Survived }, { id: '08-content', C: Content }, { id: '09-limits', C: Limits },
  { id: '10-lesson', C: Lesson }, { id: '11-cta', C: CTA, extra: 3 },
];
const frames = (s: { id: string; extra?: number }) => Math.round((sec(s.id) + (s.extra ?? 0)) * FPS);
export const totalFrames = () => SCENES.reduce((a, s) => a + frames(s), 0) - XF * (SCENES.length - 1);

const Caption: React.FC<{ text: string; dur: number; feed?: boolean }> = ({ text, dur, feed }) => {
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

const SceneFade: React.FC<{ n: number; first: boolean; children: React.ReactNode }> = ({ n, first, children }) => {
  const f = useCurrentFrame();
  const o = Math.min(first ? 1 : interpolate(f, [0, XF], [0, 1], { extrapolateRight: 'clamp' }), interpolate(f, [n - XF, n], [1, 0], { extrapolateLeft: 'clamp' }));
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

// 4:5 feed version: the 16:9 frame scaled into the middle, title band above
const FeedFrame: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ background: C.bg }}>
    <div style={{ position: 'absolute', top: 70, left: 0, right: 0, textAlign: 'center', fontFamily: SERIF, fontSize: 52, color: C.ink }}>Close the Board, Agents Move</div>
    <div style={{ position: 'absolute', top: 340, left: 0, width: 1920, height: 1080, transform: 'scale(0.5625)', transformOrigin: '0 0' }}>{children}</div>
  </AbsoluteFill>
);

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

export const Promo: React.FC = () => <Timeline />;
export const PromoFeed: React.FC = () => <Timeline feed />;
