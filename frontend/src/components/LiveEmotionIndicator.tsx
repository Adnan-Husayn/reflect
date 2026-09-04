import type { EmotionPrediction } from "../types/emotion";

interface LiveEmotionIndicatorProps {
  title: string;
  description: string;
  prediction: EmotionPrediction | null;
  state: string;
  error?: string | null;
}

const titleCase = (label: string) => label.charAt(0).toUpperCase() + label.slice(1);

export function LiveEmotionIndicator({ title, description, prediction, state, error }: LiveEmotionIndicatorProps) {
  const sortedScores = prediction ? Object.entries(prediction.scores).sort(([, left], [, right]) => right - left) : [];
  return (
    <article className="live-indicator" aria-live="polite">
      <div className="indicator-heading">
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
        <span className={prediction ? "live-badge active" : "live-badge"}>{prediction ? "Live" : state}</span>
      </div>
      {error ? (
        <p className="indicator-error" role="status">{error}</p>
      ) : prediction ? (
        <>
          <div className="indicator-result">
            <span>Current indicator</span>
            <strong>{titleCase(prediction.label)}</strong>
            <span>Model confidence {Math.round(prediction.confidence * 100)}%</span>
          </div>
          <details className="distribution-details">
            <summary>View emotion distribution</summary>
            <div className="score-list">
              {sortedScores.map(([label, score]) => (
                <div className="score-row" key={label}>
                  <span>{titleCase(label)}</span>
                  <div className="score-track"><div className="score-fill" style={{ width: `${Math.max(score * 100, 1)}%` }} /></div>
                  <span>{Math.round(score * 100)}%</span>
                </div>
              ))}
            </div>
          </details>
        </>
      ) : (
        <p className="indicator-waiting">{state}</p>
      )}
    </article>
  );
}
