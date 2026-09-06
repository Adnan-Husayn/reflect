import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AppNav } from "./AppNav";

const account = { id: "u-1", email: "tester@example.com" };

function renderAt(path: string, auth: typeof account | null = account) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppNav account={auth} onSignedOut={() => {}} />
    </MemoryRouter>,
  );
}

describe("AppNav", () => {
  it("links to every page when signed in", () => {
    renderAt("/session");
    expect(screen.getByRole("link", { name: "Reflect" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Live session" })).toHaveAttribute("href", "/session");
    expect(screen.getByRole("link", { name: "Check-in" })).toHaveAttribute("href", "/check-in");
    expect(screen.getByRole("link", { name: "This week" })).toHaveAttribute("href", "/this-week");
    expect(screen.getByRole("link", { name: "Trends" })).toHaveAttribute("href", "/trends");
  });

  it("marks only the current route active", () => {
    renderAt("/session");
    expect(screen.getByRole("link", { name: "Live session" })).toHaveClass("active");
    expect(screen.getByRole("link", { name: "Trends" })).not.toHaveClass("active");
  });

  it("marks trends active on a trends URL", () => {
    renderAt("/trends");
    expect(screen.getByRole("link", { name: "Trends" })).toHaveClass("active");
    expect(screen.getByRole("link", { name: "Live session" })).not.toHaveClass("active");
  });

  it("offers a signed-out visitor the brand and a way in, and nothing private", () => {
    renderAt("/", null);
    expect(screen.getByRole("link", { name: "Reflect" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
    expect(screen.queryByRole("link", { name: "Trends" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Check-in" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
  });

  it("shows the account and a sign-out control when signed in", () => {
    renderAt("/session");
    expect(screen.getByText("tester@example.com")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
  });

  it("keeps the brand link available to everyone", () => {
    renderAt("/trends");
    expect(screen.getByRole("link", { name: "Reflect" })).toBeInTheDocument();
  });
});
