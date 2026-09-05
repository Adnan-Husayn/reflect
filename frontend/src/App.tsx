import { useCallback, useRef, useState } from "react";
import { LiveEmotionIndicator } from "./components/LiveEmotionIndicator";
import { StatusMessage } from "./components/StatusMessage";
import { TypedTextFallback } from "./components/TypedTextFallback";
import { useLiveSession } from "./hooks/useLiveSession";
import { analyzeFacial, analyzeLiveAudio, analyzeText } from "./services/api";
import type { EmotionPrediction } from "./types/emotion";
import { appendToHistory, averagePredictions } from "./utils/smoothing";

export default function App() {
  const sessionToken = useRef(0);
  const faceHistory = useRef<EmotionPrediction[]>([]);
  const [transcript, setTranscript] = useState("");
  const [voicePrediction, setVoicePrediction] = useState<EmotionPrediction | null>(null);
  const [textPrediction, setTextPrediction] = useState<EmotionPrediction | null>(null);
  const [facePrediction, setFacePrediction] = useState<EmotionPrediction | null>(null);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [faceError, setFaceError] = useState<string | null>(null);
  const [faceState, setFaceState] = useState("Waiting for camera");

  const handleAudioSegment = useCallback(async (audio: Blob) => {
    const requestToken = sessionToken.current;
    try {
      const result = await analyzeLiveAudio(audio);
      if (requestToken !== sessionToken.current) return;
      setVoiceError(null);
      setVoicePrediction(result.audio_prediction);
      if (result.transcript) setTranscript((current) => `${current}${current ? " " : ""}${result.transcript}`.trim());
      if (result.text_prediction) setTextPrediction(result.text_prediction);
    } catch (error) {
      if (requestToken === sessionToken.current) setVoiceError(error instanceof Error ? error.message : "Live audio analysis is unavailable.");
    }
  }, []);

  const handleFaceFrame = useCallback(async (image: Blob) => {
    const requestToken = sessionToken.current;
    try {
      const prediction = await analyzeFacial(image);
      if (requestToken !== sessionToken.current) return;
      faceHistory.current = appendToHistory(faceHistory.current, prediction);
      setFacePrediction(averagePredictions(faceHistory.current));
      setFaceError(null);
      setFaceState("Reading visible expression");
    } catch (error) {
      if (requestToken !== sessionToken.current) return;
      const message = error instanceof Error ? error.message : "Face analysis is unavailable.";
      if (message === "No face was detected in the captured image.") {
        setFacePrediction(null);
        setFaceError(null);
        setFaceState("Face not visible");
      } else {
        setFaceError(message);
      }
    }
  }, []);

  const session = useLiveSession({ onAudioSegment: handleAudioSegment, onFaceFrame: handleFaceFrame });

  const startSession = async () => {
    sessionToken.current += 1;
    faceHistory.current = [];
    setTranscript("");
    setVoicePrediction(null);
    setTextPrediction(null);
    setFacePrediction(null);
    setVoiceError(null);
    setFaceError(null);
    setFaceState("Looking for a face");
    await session.startSession();
  };

  const endSession = () => {
    sessionToken.current += 1;
    session.stopSession();
  };

  return (
    <main className="page-shell live-page">
      <header className="page-header">
        <p className="project-code">PCS26/146</p>
        <h1>Reflect</h1>
        <p>Live, independent indicators from spoken words, vocal expression, and visible facial expression.</p>
      </header>

      <section className="session-layout" aria-label="Live emotion analysis session">
        <div className="session-panel">
          <div className="session-heading">
            <div><h2>Conversation session</h2><p>Start when you are ready. Audio and camera permission are requested separately.</p></div>
            <button type="button" className={session.isRunning ? "end-session-button" : "start-session-button"} onClick={session.isRunning ? endSession : startSession}>{session.isRunning ? "End session" : "Start session"}</button>
          </div>
          <StatusMessage message={session.microphoneError} />
          <StatusMessage message={session.cameraError} />
          <div className="session-status" role="status"><span className={session.isRunning ? "status-dot active" : "status-dot"} />{session.isRunning ? "Session running" : "Session not started"}<span>Microphone: {session.microphoneActive ? "on" : "off"}</span><span>Camera: {session.cameraActive ? "on" : "off"}</span></div>
          <div className="live-camera-frame"><video ref={session.videoRef} muted playsInline aria-label="Live camera preview" className={session.cameraActive ? "" : "hidden"} />{!session.cameraActive && <p>Camera preview will appear here when permission is granted.</p>}</div>
          <div className="transcript-panel"><div><h3>Live transcript</h3><span>{session.microphoneActive ? "Listening in 5-second segments" : "Microphone is off"}</span></div><p>{transcript || "Your spoken words will appear here during the session."}</p></div>
        </div>

        <section className="indicators-panel" aria-labelledby="live-indicators-heading">
          <div className="indicators-heading"><h2 id="live-indicators-heading">Live indicators</h2><p>These channels are shown independently and are not combined.</p></div>
          <LiveEmotionIndicator title="Spoken words" description="Emotion classification from the local English transcript" prediction={textPrediction} state={session.microphoneActive ? "Waiting for speech" : "Microphone is off"} />
          <LiveEmotionIndicator title="Vocal expression" description="Emotion classification from the latest voice segment" prediction={voicePrediction} state={session.microphoneActive ? "Listening for a voice segment" : "Microphone is off"} error={voiceError} />
          <LiveEmotionIndicator title="Visible facial expression" description="Smoothed expression indicator from recent camera frames" prediction={facePrediction} state={faceState} error={faceError} />
        </section>
      </section>

      <TypedTextFallback onAnalyze={analyzeText} />
      <footer>Visible facial expression and model confidence are indicators only. This tool is not a diagnosis, a substitute for therapy, or a measure of a person’s internal emotional state.</footer>
    </main>
  );
}
