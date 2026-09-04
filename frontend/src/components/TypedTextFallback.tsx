import { useState } from "react";
import type { EmotionPrediction } from "../types/emotion";
import { LiveEmotionIndicator } from "./LiveEmotionIndicator";

interface TypedTextFallbackProps {
  onAnalyze: (text: string) => Promise<EmotionPrediction>;
}

export function TypedTextFallback({ onAnalyze }: TypedTextFallbackProps) {
  const [text, setText] = useState("");
  const [prediction, setPrediction] = useState<EmotionPrediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const analyze = async () => {
    if (!text.trim()) return;
    setIsAnalyzing(true);
    setError(null);
    try {
      setPrediction(await onAnalyze(text.trim()));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to analyze typed text.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <details className="typed-fallback">
      <summary>Analyze typed text instead</summary>
      <div className="typed-fallback-content">
        <label htmlFor="typed-text">Text to analyze</label>
        <textarea id="typed-text" value={text} onChange={(event) => setText(event.target.value.slice(0, 5000))} placeholder="Type something to analyze..." rows={4} maxLength={5000} />
        <div className="typed-controls">
          <span>{text.length.toLocaleString()} / 5,000 characters</span>
          <button type="button" className="secondary-button" onClick={analyze} disabled={!text.trim() || isAnalyzing}>{isAnalyzing ? "Analyzing..." : "Analyze text"}</button>
        </div>
        {(prediction || error) && <LiveEmotionIndicator title="Typed Text" description="One-time fallback analysis" prediction={prediction} state="Waiting for typed text" error={error} />}
      </div>
    </details>
  );
}
