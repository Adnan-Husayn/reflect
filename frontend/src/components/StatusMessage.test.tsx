import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusMessage } from "./StatusMessage";

describe("StatusMessage", () => {
  it("renders nothing when there is no message", () => {
    const { container } = render(<StatusMessage message={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("announces errors assertively so a denied permission is not missed", () => {
    render(<StatusMessage message="Microphone permission was denied." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Microphone permission was denied.");
  });

  it("announces informational messages politely", () => {
    render(<StatusMessage message="Camera is starting." tone="info" />);
    expect(screen.getByRole("status")).toHaveTextContent("Camera is starting.");
  });
});
