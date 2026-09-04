import { useCallback, useEffect, useRef, useState } from "react";

interface LiveSessionOptions {
  onAudioSegment: (audio: Blob) => Promise<void>;
  onFaceFrame: (image: Blob) => Promise<void>;
}

const AUDIO_SEGMENT_MS = 5_000;
const FACE_FRAME_MS = 2_000;

export function useLiveSession({ onAudioSegment, onFaceFrame }: LiveSessionOptions) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const microphoneStream = useRef<MediaStream | null>(null);
  const cameraStream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const audioTimer = useRef<number | null>(null);
  const faceTimer = useRef<number | null>(null);
  const active = useRef(false);
  const audioBusy = useRef(false);
  const faceBusy = useRef(false);
  const onAudioSegmentRef = useRef(onAudioSegment);
  const onFaceFrameRef = useRef(onFaceFrame);
  const [isRunning, setIsRunning] = useState(false);
  const [microphoneActive, setMicrophoneActive] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [microphoneError, setMicrophoneError] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);

  useEffect(() => {
    onAudioSegmentRef.current = onAudioSegment;
    onFaceFrameRef.current = onFaceFrame;
  }, [onAudioSegment, onFaceFrame]);

  const stopTracks = useCallback(() => {
    microphoneStream.current?.getTracks().forEach((track) => track.stop());
    cameraStream.current?.getTracks().forEach((track) => track.stop());
    microphoneStream.current = null;
    cameraStream.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setMicrophoneActive(false);
    setCameraActive(false);
  }, []);

  const stopSession = useCallback(() => {
    active.current = false;
    if (audioTimer.current) window.clearTimeout(audioTimer.current);
    if (faceTimer.current) window.clearInterval(faceTimer.current);
    audioTimer.current = null;
    faceTimer.current = null;
    if (recorder.current?.state === "recording") recorder.current.stop();
    recorder.current = null;
    stopTracks();
    setIsRunning(false);
  }, [stopTracks]);

  const recordSegment = useCallback(() => {
    if (!active.current || !microphoneStream.current || audioBusy.current) return;
    const chunks: BlobPart[] = [];
    const nextRecorder = new MediaRecorder(microphoneStream.current);
    recorder.current = nextRecorder;
    nextRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data);
    };
    nextRecorder.onstop = async () => {
      if (!active.current || !chunks.length) return;
      audioBusy.current = true;
      try {
        await onAudioSegmentRef.current(new Blob(chunks, { type: nextRecorder.mimeType || "audio/webm" }));
      } finally {
        audioBusy.current = false;
        if (active.current) recordSegment();
      }
    };
    nextRecorder.start();
    audioTimer.current = window.setTimeout(() => {
      if (nextRecorder.state === "recording") nextRecorder.stop();
    }, AUDIO_SEGMENT_MS);
  }, []);

  const sendFaceFrame = useCallback(() => {
    const video = videoRef.current;
    if (!active.current || !video || !cameraStream.current || faceBusy.current || video.videoWidth === 0) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);
    faceBusy.current = true;
    canvas.toBlob(async (blob) => {
      if (!blob) {
        faceBusy.current = false;
        return;
      }
      try {
        await onFaceFrameRef.current(blob);
      } finally {
        faceBusy.current = false;
      }
    }, "image/jpeg", 0.82);
  }, []);

  const startSession = useCallback(async () => {
    if (active.current) return;
    active.current = true;
    setIsRunning(true);
    setMicrophoneError(null);
    setCameraError(null);

    try {
      microphoneStream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      setMicrophoneActive(true);
      recordSegment();
    } catch {
      setMicrophoneError("Microphone access was denied. You can still use the camera or typed-text fallback.");
    }

    try {
      cameraStream.current = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
      if (videoRef.current) {
        videoRef.current.srcObject = cameraStream.current;
        await videoRef.current.play();
      }
      setCameraActive(true);
      sendFaceFrame();
      faceTimer.current = window.setInterval(sendFaceFrame, FACE_FRAME_MS);
    } catch {
      setCameraError("Camera access was denied. You can still use spoken or typed text analysis.");
    }
  }, [recordSegment, sendFaceFrame]);

  useEffect(() => () => stopSession(), [stopSession]);

  return {
    videoRef,
    isRunning,
    microphoneActive,
    cameraActive,
    microphoneError,
    cameraError,
    startSession,
    stopSession,
  };
}
