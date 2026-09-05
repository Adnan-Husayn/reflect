import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(cleanup);

// jsdom implements no ResizeObserver, which Recharts' ResponsiveContainer
// requires. The charts themselves cannot be measured under jsdom regardless —
// the container reports zero width — so the chart tests assert on captions and
// headings rather than on rendered geometry.
if (!("ResizeObserver" in globalThis)) {
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;
}
