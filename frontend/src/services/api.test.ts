import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { analyzeFacial, analyzeLiveAudio, analyzeText } from "./api";
import { makePrediction } from "../test/factories";

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
