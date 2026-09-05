import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  analyzeFacial,
  analyzeLiveAudio,
  analyzeText,
  createSession,
  endSession,
  fuseChannels,
  postReadings,
} from "./api";
import { makeFusion, makePrediction, makeScores } from "../test/factories";

const prediction = makePrediction({ joy: 0.87, neutral: 0.13 });

function mockResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, json: () => Promise.resolve(body) } as Response;
}

describe("api client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("posts text as JSON to the text endpoint", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(prediction));

    await expect(analyzeText("I feel calm today.")).resolves.toEqual(prediction);

    const [url, options] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toContain("/predict/text");
    expect(options?.method).toBe("POST");
    expect(options?.body).toBe(JSON.stringify({ text: "I feel calm today." }));
  });

  it("sends uploads as multipart form data with a filename", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(prediction));

    await analyzeFacial(new Blob(["frame"], { type: "image/jpeg" }));

    const [url, options] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toContain("/predict/facial");
    expect(options?.body).toBeInstanceOf(FormData);
    const file = (options?.body as FormData).get("file") as File;
    expect(file.name).toBe("captured-face.jpg");
  });

  it("surfaces the server's detail message on failure", async () => {
    vi.mocked(fetch).mockResolvedValue(
      mockResponse({ detail: "No face was detected in the captured image." }, false, 400),
    );

    await expect(analyzeFacial(new Blob([""]))).rejects.toThrow(
      "No face was detected in the captured image.",
    );
  });

  it("falls back to a generic message when the error body is unreadable", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error("not json")),
    } as unknown as Response);

    await expect(analyzeText("hello")).rejects.toThrow("Unable to complete analysis.");
  });

  it("returns the transcript alongside independent predictions", async () => {
    const body = {
      transcript: "I feel calmer today.",
      audio_prediction: makePrediction({ neutral: 0.7, sadness: 0.3 }),
      text_prediction: makePrediction({ joy: 0.6, neutral: 0.4 }),
    };
    vi.mocked(fetch).mockResolvedValue(mockResponse(body));

    const result = await analyzeLiveAudio(new Blob(["segment"]));

    expect(result.transcript).toBe("I feel calmer today.");
    expect(result.audio_prediction?.label).toBe("neutral");
    expect(result.text_prediction?.label).toBe("joy");
  });
});

describe("fusion and session persistence", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("sends only the channels that have a reading", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse(makeFusion()));

    await fuseChannels({ text: makeScores({ joy: 1 }), voice: makeScores({ sadness: 1 }) });

    const [url, options] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toContain("/analyze/fusion");
    expect(JSON.parse(String(options?.body))).toEqual({
      text: makeScores({ joy: 1 }),
      voice: makeScores({ sadness: 1 }),
    });
  });

  it("returns the fused reading with its attenuation", async () => {
    vi.mocked(fetch).mockResolvedValue(
      mockResponse(makeFusion({ confidence: 0.07, rawConfidence: 0.55, conflict: true })),
    );

    const analysis = await fuseChannels({ text: makeScores({ joy: 1 }) });

    expect(analysis.fused?.confidence).toBe(0.07);
    expect(analysis.fused?.raw_confidence).toBe(0.55);
    expect(analysis.conflict.conflict_detected).toBe(true);
  });

  it("opens a session", async () => {
    vi.mocked(fetch).mockResolvedValue(
      mockResponse({ id: "s-1", started_at: "2026-09-05T12:00:00Z", ended_at: null }),
    );

    await expect(createSession()).resolves.toMatchObject({ id: "s-1" });
    const [url, options] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toContain("/sessions");
    expect(options?.method).toBe("POST");
  });

  it("posts a reading batch to the session", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({}));
    const batch = {
      readings: [
        {
          t: "2026-09-05T12:00:00.000Z",
          channel: "face" as const,
          label: "joy" as const,
          confidence: 0.8,
          scores: makeScores({ joy: 1 }),
        },
      ],
      fused: [],
    };

    await postReadings("s-1", batch);

    const [url, options] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toContain("/sessions/s-1/readings");
    expect(JSON.parse(String(options?.body))).toEqual(batch);
  });

  it("never includes a transcript field in a reading batch", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({}));

    await postReadings("s-1", {
      readings: [
        {
          t: "2026-09-05T12:00:00.000Z",
          channel: "text",
          label: "joy",
          confidence: 0.8,
          scores: makeScores({ joy: 1 }),
        },
      ],
      fused: [],
    });

    const body = String(vi.mocked(fetch).mock.calls[0][1]?.body);
    expect(body).not.toContain("transcript");
    expect(Object.keys(JSON.parse(body).readings[0]).sort()).toEqual([
      "channel",
      "confidence",
      "label",
      "scores",
      "t",
    ]);
  });

  it("closes the session and returns its summary", async () => {
    vi.mocked(fetch).mockResolvedValue(
      mockResponse({ session_id: "s-1", n_readings: 3, mean_valence: 0.4 }),
    );

    const summary = await endSession("s-1");

    expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain("/sessions/s-1/end");
    expect(summary.mean_valence).toBe(0.4);
  });
});
