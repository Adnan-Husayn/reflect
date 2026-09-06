import { useEffect, useRef, useState } from "react";

/**
 * The hero animation is the product, not decoration.
 *
 * Three lines, one per channel, each following the cursor with a different
 * pull — spoken words strongly, vocal expression about half as much, visible
 * facial expression barely. Dragging through the field physically pulls them
 * apart, the divergence figure climbs, and past the threshold the readout
 * turns clay. That is the real `/analyze/fusion` mechanism, made playable:
 * someone who idles here for three seconds has understood the thesis.
 */

const WIDTH = 1440;
const HEIGHT = 400;
const MIDLINE = HEIGHT / 2;
const THRESHOLD = 0.35;
const SAMPLES = 76;

interface Channel {
  id: string;
  label: string;
  colour: string;
  offset: number;
  amplitude: number;
  /** How hard this channel follows the cursor. */
  strength: number;
}

const CHANNELS: Channel[] = [
  { id: "text", label: "Spoken words", colour: "var(--channel-text)", offset: 0, amplitude: 18, strength: 0.92 },
  { id: "voice", label: "Vocal expression", colour: "var(--channel-voice)", offset: 2.1, amplitude: 14, strength: 0.58 },
  { id: "face", label: "Visible facial expression", colour: "var(--channel-face)", offset: 4.0, amplitude: 11, strength: 0.3 },
];

function yAt(channel: Channel, x: number, t: number, cx: number, cy: number): number {
  const drift =
    MIDLINE +
    Math.sin(x / 210 + t + channel.offset) * channel.amplitude +
    Math.sin(x / 83 + t * 0.6 + channel.offset) * 4;
  const dx = (x - cx) / 280;
  const influence = Math.exp(-dx * dx);
  return drift + (cy - drift) * channel.strength * influence;
}

function pathFor(channel: Channel, t: number, cx: number, cy: number): string {
  let path = "";
  for (let index = 0; index <= SAMPLES; index += 1) {
    const x = (WIDTH * index) / SAMPLES;
    path += `${index === 0 ? "M" : " L"}${x.toFixed(1)} ${yAt(channel, x, t, cx, cy).toFixed(1)}`;
  }
  return path;
}

/** Spread of the three channels at the cursor, mapped onto [0, 1]. */
function divergenceAt(t: number, cx: number, cy: number): number {
  const ys = CHANNELS.map((channel) => yAt(channel, cx, t, cx, cy));
  const spread = Math.max(...ys) - Math.min(...ys);
  return Math.min(1, spread / (HEIGHT * 0.42));
}

export function DivergenceField() {
  const frame = useRef<number | null>(null);
  const target = useRef({ x: WIDTH / 2, y: MIDLINE });
  const svgRef = useRef<SVGSVGElement>(null);
  const [{ t, cx, cy }, setState] = useState({ t: 0, cx: WIDTH / 2, cy: MIDLINE });

  useEffect(() => {
    // Ambient drift stops under reduced motion; the cursor response stays,
    // because that is the explanation rather than the decoration.
    let reduced = false;
    try {
      reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch {
      reduced = false;
    }

    const loop = () => {
      setState((current) => ({
        t: reduced ? current.t : current.t + 0.01,
        cx: current.cx + (target.current.x - current.cx) * 0.085,
        cy: current.cy + (target.current.y - current.cy) * 0.085,
      }));
      frame.current = requestAnimationFrame(loop);
    };
    frame.current = requestAnimationFrame(loop);
    return () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current);
    };
  }, []);

  const track = (event: React.PointerEvent<SVGSVGElement>) => {
    const box = svgRef.current?.getBoundingClientRect();
    if (!box) return;
    target.current = {
      x: ((event.clientX - box.left) / box.width) * WIDTH,
      y: ((event.clientY - box.top) / box.height) * HEIGHT,
    };
  };

  const rest = () => {
    target.current = { x: WIDTH / 2, y: MIDLINE };
  };

  const divergence = divergenceAt(t, cx, cy);
  const inConflict = divergence >= THRESHOLD;

  return (
    <div className="field-wrap">
      <svg
        ref={svgRef}
        className="field"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="none"
        onPointerMove={track}
        onPointerLeave={rest}
        role="img"
        aria-label="Three lines, one per channel, following the cursor with different strengths. Moving across them pulls the channels apart and raises the divergence reading."
      >
        {CHANNELS.map((channel) => (
          <path
            key={channel.id}
            d={pathFor(channel, t, cx, cy)}
            fill="none"
            stroke={channel.colour}
            strokeWidth={1.6}
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>

      <div className="field-readout">
        <div className="field-figure">
          <span className={inConflict ? "field-value conflict" : "field-value"}>
            {divergence.toFixed(2)}
          </span>
          <span className={inConflict ? "field-label conflict" : "field-label"}>
            {inConflict ? "the channels disagree" : "the channels agree"}
          </span>
        </div>
        <span className="field-threshold">provisional threshold {THRESHOLD.toFixed(2)}</span>
      </div>

      <ul className="field-key">
        {CHANNELS.map((channel) => (
          <li key={channel.id}>
            <span className="field-swatch" style={{ background: channel.colour }} />
            {channel.label}
          </li>
        ))}
      </ul>

      <p className="field-caption">
        Move your cursor across the field. Each channel follows it with a different pull — the way
        three models respond differently to the same moment.
      </p>
    </div>
  );
}
