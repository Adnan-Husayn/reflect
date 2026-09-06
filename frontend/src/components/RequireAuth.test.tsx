import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { RequireAuth } from "./RequireAuth";
import type { AuthState } from "../hooks/useAuth";

function renderAt(account: AuthState) {
  return render(
    <MemoryRouter initialEntries={["/trends"]}>
      <Routes>
        <Route
          path="/trends"
          element={
            <RequireAuth account={account}>
              <p>Private content</p>
            </RequireAuth>
          }
        />
        <Route path="/login" element={<p>Sign in form</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RequireAuth", () => {
  it("renders the page for a signed-in account", () => {
    renderAt({ id: "u-1", email: "tester@example.com" });
    expect(screen.getByText("Private content")).toBeInTheDocument();
  });

  it("redirects a signed-out visitor to the login form", () => {
    renderAt(null);
    expect(screen.getByText("Sign in form")).toBeInTheDocument();
    expect(screen.queryByText("Private content")).not.toBeInTheDocument();
  });

  it("renders nothing while the session is still resolving", () => {
    const { container } = renderAt("loading");
    // Neither the private page nor the login form: flashing the form at
    // somebody already signed in is worse than a moment of blankness.
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByText("Sign in form")).not.toBeInTheDocument();
  });
});
