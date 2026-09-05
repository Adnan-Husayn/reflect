import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";

afterEach(cleanup);

// jsdom implements no ResizeObserver, which Recharts' ResponsiveContainer
// requires. The charts cannot be measured under jsdom regardless — the
// container reports zero width — so the chart tests assert on captions and
// headings rather than on rendered geometry.
if (!("ResizeObserver" in globalThis)) {
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;
}

// The environment provides a bare object for localStorage with none of the
// Storage methods on it, so anything reading or writing it throws. Replace it
// with a real in-memory implementation and reset between tests, so consent
// state cannot leak from one test into the next.
class MemoryStorage implements Storage {
  private entries = new Map<string, string>();

  get length(): number {
    return this.entries.size;
  }

  clear(): void {
    this.entries.clear();
  }

  getItem(key: string): string | null {
    return this.entries.get(key) ?? null;
  }

  key(index: number): string | null {
    return [...this.entries.keys()][index] ?? null;
  }

  removeItem(key: string): void {
    this.entries.delete(key);
  }

  setItem(key: string, value: string): void {
    this.entries.set(key, String(value));
  }
}

const storage = new MemoryStorage();
Object.defineProperty(globalThis, "localStorage", { value: storage, configurable: true });

beforeEach(() => storage.clear());
