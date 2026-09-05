import type { Channel, FusionAnalysis } from "../types/emotion";

interface FusedIndicatorProps {
  analysis: FusionAnalysis | null;
  state: string;
  error?: string | null;
}

const CHANNEL_NAMES: Record<Channel, string> = {
  text: "spoken words",
  voice: "vocal expression",
  face: "visible facial expression",
};

const titleCase = (label: string) => label.charAt(0).toUpperCase() + label.slice(1);
const percent = (value: number) => Math.round(value * 100);

function describePair(pair: Channel[] | null): string {
  if (!pair || pair.length < 2) return "The channels disagree.";
  const [first, second] = pair;
  return `${titleCase(CHANNEL_NAMES[first])} and ${CHANNEL_NAMES[second]} disagree.`;
}

export function FusedIndicator({ analysis, state, error }: FusedIndicatorProps) {
  if (error) {
    return (
      <article className="fused-indicator" aria-live="polite">
        <h2>Combined reading</h2>
        <p className="indicator-error" role="status">{error}</p>
      </article>
    );
  }

  if (!analysis?.fused) {
    return (
      <article className="fused-indicator" aria-live="polite">
        <h2>Combined reading</h2>
        <p className="indicator-waiting">{state}</p>
      </article>
    );
  }

  const { fused, conflict } = analysis;
  const divergence = conflict.max_divergence;
  const isConflict = conflict.conflict_detected;

  return (
    <article className={isConflict ? "fused-indicator conflict" : "fused-indicator"} aria-live="polite">
      <div className="fused-heading">
        <h2>Combined reading</h2>
        <span className="fused-channel-count">
          {conflict.channels_compared.length} of 3 channels
        </span>
      </div>

      <div className="fused-result">
        <strong>{titleCase(fused.label)}</strong>
        {/* The attenuated confidence, never raw_confidence. */}
        <span className="fused-confidence">{percent(fused.confidence)}% model confidence</span>
      </div>

      {isConflict ? (
        <div className="fused-conflict">
          <p className="fused-conflict-headline">{describePair(conflict.most_divergent_pair)}</p>
          <p className="fused-conflict-detail">
            Confidence is reduced from {percent(fused.raw_confidence)}% to{" "}
            {percent(fused.confidence)}% because the channels do not agree.
          </p>
        </div>
      ) : (
        <p className="fused-agreement">
          The channels broadly agree, so the combined confidence is close to its unadjusted value.
        </p>
      )}

      {divergence !== null && (
        <div className="divergence">
          <div className="divergence-track">
            <div className="divergence-fill" style={{ width: `${Math.max(divergence * 100, 1)}%` }} />
            <div
              className="divergence-threshold"
              style={{ left: `${conflict.threshold * 100}%` }}
              aria-hidden="true"
            />
          </div>
          <div className="divergence-scale">
            <span>0.00 agree</span>
            <span>{conflict.threshold.toFixed(2)} threshold</span>
            <span>1.00 disagree</span>
          </div>
          <p className="divergence-reading">
            <strong>{divergence.toFixed(2)}</strong> maximum divergence, against a provisional
            threshold of {conflict.threshold.toFixed(2)}.
          </p>
        </div>
      )}

      {conflict.pairs.length > 0 && (
        <details className="divergence-details">
          <summary>View pairwise divergence</summary>
          <table>
            <thead>
              <tr>
                <th scope="col">Channel pair</th>
                <th scope="col">JS</th>
                <th scope="col">Cosine</th>
              </tr>
            </thead>
            <tbody>
              {conflict.pairs.map((pair) => (
                <tr key={pair.channels.join("-")}>
                  <td>
                    {titleCase(CHANNEL_NAMES[pair.channels[0]])} → {CHANNEL_NAMES[pair.channels[1]]}
                  </td>
                  <td>{pair.jensen_shannon.toFixed(2)}</td>
                  <td>{pair.cosine_distance.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}

      <p className="fused-caveat">
        A conflict means the channels disagree. It is <strong>not</strong> evidence that a person is
        concealing an emotion, and it is not a diagnosis. The threshold is provisional and has not
        yet been derived from labelled data.
      </p>
    </article>
  );
}
