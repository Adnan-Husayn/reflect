import { useCallback, useRef, useState } from "react";
import { FusedIndicator } from "../components/FusedIndicator";
import { LiveEmotionIndicator } from "../components/LiveEmotionIndicator";
import { StatusMessage } from "../components/StatusMessage";
import { TypedTextFallback } from "../components/TypedTextFallback";
import { useLiveSession } from "../hooks/useLiveSession";
import { useSessionRecorder } from "../hooks/useSessionRecorder";
import { analyzeFacial, analyzeLiveAudio, analyzeText, fuseChannels } from "../services/api";
import type {
  Channel,
  EmotionPrediction,
  EmotionScores,
  FusionAnalysis,
} from "../types/emotion";
import { appendToHistory, averagePredictions } from "../utils/smoothing";

export function LiveSession() {
  const sessionToken = useRef(0);
  const faceHistory = useRef<EmotionPrediction[]>([]);
  const latestScores = useRef<Partial<Record<Channel, EmotionScores>>>({});
  const fusionBusy = useRef(false);

  const [transcript, setTranscript] = useState("");
  const [voicePrediction, setVoicePrediction] = useState<EmotionPrediction | null>(null);
  const [textPrediction, setTextPrediction] = useState<EmotionPrediction | null>(null);
  const [facePrediction, setFacePrediction] = useState<EmotionPrediction | null>(null);
  const [fusion, setFusion] = useState<FusionAnalysis | null>(null);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [faceError, setFaceError] = useState<string | null>(null);
  const [fusionError, setFusionError] = useState<string | null>(null);
  const [faceState, setFaceState] = useState("Waiting for camera");

  const recorder = useSessionRecorder();

  /** Record one channel reading and refresh the fused view. */
  const publish = useCallback(
    async (channel: Channel, prediction: EmotionPrediction, requestToken: number) => {
      if (requestToken !== sessionToken.current) return;

      latestScores.current = { ...latestScores.current, [channel]: prediction.scores };
      recorder.addReading({
        t: new Date().toISOString(),
        channel,
        label: prediction.label,
        confidence: prediction.confidence,
        scores: prediction.scores,
      });

      // One request in flight at a time, so a slow response cannot queue up
      // behind the 2-second facial tick.
      if (fusionBusy.current) return;
      fusionBusy.current = true;
      try {
        const analysis = await fuseChannels(latestScores.current);
        if (requestToken !== sessionToken.current) return;
        setFusion(analysis);
        setFusionError(null);
        if (analysis.fused) {
          recorder.addFusedReading({
            t: new Date().toISOString(),
            label: analysis.fused.label,
            confidence: analysis.fused.confidence,
            raw_confidence: analysis.fused.raw_confidence,
            attenuation: analysis.fused.attenuation,
            max_divergence: analysis.conflict.max_divergence,
            conflict: analysis.conflict.conflict_detected,
            scores: analysis.fused.scores,
          });
        }
      } catch (error) {
        if (requestToken === sessionToken.current) {
          setFusionError(error instanceof Error ? error.message : "Combined reading is unavailable.");
        }
      } finally {
        fusionBusy.current = false;
      }
    },
    [recorder],
  );

  const handleAudioSegment = useCallback(
    async (audio: Blob) => {
      const requestToken = sessionToken.current;
      try {
        const result = await analyzeLiveAudio(audio);
        if (requestToken !== sessionToken.current) return;
        setVoiceError(null);
        setVoicePrediction(result.audio_prediction);
        if (result.transcript) {
          setTranscript((current) => `${current}${current ? " " : ""}${result.transcript}`.trim());
        }
        if (result.text_prediction) setTextPrediction(result.text_prediction);

        if (result.audio_prediction) await publish("voice", result.audio_prediction, requestToken);
        if (result.text_prediction) await publish("text", result.text_prediction, requestToken);
      } catch (error) {
        if (requestToken === sessionToken.current) {
          setVoiceError(error instanceof Error ? error.message : "Live audio analysis is unavailable.");
        }
      }
    },
    [publish],
  );

  const handleFaceFrame = useCallback(
    async (image: Blob) => {
      const requestToken = sessionToken.current;
      try {
        const prediction = await analyzeFacial(image);
        if (requestToken !== sessionToken.current) return;
        faceHistory.current = appendToHistory(faceHistory.current, prediction);
        // The smoothed value is what the user sees, so it is also what is
        // recorded and what the fused reading is built from. Persisting a raw
        // frame the interface never displayed would make M4's session replay
        // disagree with what actually happened.
        const smoothed = averagePredictions(faceHistory.current);
        setFacePrediction(smoothed);
        setFaceError(null);
        setFaceState("Reading visible expression");
        await publish("face", smoothed, requestToken);
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
    },
    [publish],
  );

  const session = useLiveSession({ onAudioSegment: handleAudioSegment, onFaceFrame: handleFaceFrame });

  const startSession = async () => {
    sessionToken.current += 1;
    faceHistory.current = [];
    latestScores.current = {};
    setTranscript("");
    setVoicePrediction(null);
    setTextPrediction(null);
    setFacePrediction(null);
    setFusion(null);
    setVoiceError(null);
    setFaceError(null);
    setFusionError(null);
    setFaceState("Looking for a face");
    await recorder.start();
    await session.startSession();
  };

  const endSession = () => {
    sessionToken.current += 1;
    session.stopSession();
    void recorder.stop();
  };

  return (
    <main className="page-shell live-page">
      <header className="page-header">
        <p className="project-code">PCS26/146</p>
        <h1>Reflect</h1>
        <p>Live indicators from spoken words, vocal expression, and visible facial expression, and the combined reading they produce.</p>
      </header>

      <section className="session-layout" aria-label="Live emotion analysis session">
        <div className="session-panel">
          <div className="session-heading">
            <div><h2>Conversation session</h2><p>Start when you are ready. Audio and camera permission are requested separately.</p></div>
            <button type="button" className={session.isRunning ? "end-session-button" : "start-session-button"} onClick={session.isRunning ? endSession : startSession}>{session.isRunning ? "End session" : "Start session"}</button>
          </div>
          <StatusMessage message={session.microphoneError} />
          <StatusMessage message={session.cameraError} />
          <div className="session-status" role="status">
            <span className={session.isRunning ? "status-dot active" : "status-dot"} />
            {session.isRunning ? "Session running" : "Session not started"}
            <span>Microphone: {session.microphoneActive ? "on" : "off"}</span>
            <span>Camera: {session.cameraActive ? "on" : "off"}</span>
            {session.isRunning && !recorder.isRecording && (
              <span className="not-recording">Not recording</span>
            )}
          </div>
          <div className="live-camera-frame"><video ref={session.videoRef} muted playsInline aria-label="Live camera preview" className={session.cameraActive ? "" : "hidden"} />{!session.cameraActive && <p>Camera preview will appear here when permission is granted.</p>}</div>
          <div className="transcript-panel"><div><h3>Live transcript</h3><span>{session.microphoneActive ? "Listening in 5-second segments" : "Microphone is off"}</span></div><p>{transcript || "Your spoken words will appear here during the session."}</p></div>
        </div>

        <section className="indicators-panel" aria-labelledby="live-indicators-heading">
          <div className="indicators-heading">
            <h2 id="live-indicators-heading">Live indicators</h2>
            <p>Each channel is shown on its own, alongside the combined reading built from them.</p>
          </div>

          <FusedIndicator
            analysis={fusion}
            state={session.isRunning ? "Waiting for a reading from two channels" : "Session not started"}
            error={fusionError}
          />

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
