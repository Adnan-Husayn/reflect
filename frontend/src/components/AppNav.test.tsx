import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AppNav } from "./AppNav";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppNav />
    </MemoryRouter>,
  );
}

describe("AppNav", () => {
  it("links to every page", () => {
    renderAt("/");
    expect(screen.getByRole("link", { name: "Live session" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Check-in" })).toHaveAttribute("href", "/check-in");
    expect(screen.getByRole("link", { name: "Trends" })).toHaveAttribute("href", "/trends");
  });

  it("marks the check-in active on its own route", () => {
    renderAt("/check-in");
    expect(screen.getByRole("link", { name: "Check-in" })).toHaveClass("active");
    expect(screen.getByRole("link", { name: "Live session" })).not.toHaveClass("active");
  });

  it("marks the live session active only on the index route", () => {
    renderAt("/");
    expect(screen.getByRole("link", { name: "Live session" })).toHaveClass("active");
    expect(screen.getByRole("link", { name: "Trends" })).not.toHaveClass("active");
  });

  it("marks trends active on a trends URL", () => {
    renderAt("/trends");
    expect(screen.getByRole("link", { name: "Trends" })).toHaveClass("active");
    // `end` on the index link stops it matching every route.
    expect(screen.getByRole("link", { name: "Live session" })).not.toHaveClass("active");
  });
})
