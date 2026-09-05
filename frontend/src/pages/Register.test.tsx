import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Register } from "./Register";
import * as api from "../services/api";

const account = { id: "u-1", email: "new@example.com" };

function renderPage(onSignedIn = vi.fn()) {
  render(
    <MemoryRouter>
      <Register onSignedIn={onSignedIn} />
    </MemoryRouter>,
  );
  return onSignedIn;
}

describe("Register", () => {
  afterEach(() => vi.restoreAllMocks());

  it("will not submit a password below the minimum length", async () => {
    const user = userEvent.setup();
    const register = vi.spyOn(api, "register").mockResolvedValue(account);
    renderPage();

    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Password"), "short");

    expect(screen.getByRole("button", { name: "Create account" })).toBeDisabled();
    expect(register).not.toHaveBeenCalled();
  });

  it("creates the account once the password is long enough", async () => {
    const user = userEvent.setup();
    const register = vi.spyOn(api, "register").mockResolvedValue(account);
    const onSignedIn = renderPage();

    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Password"), "a-long-enough-password");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => expect(register).toHaveBeenCalled());
    expect(onSignedIn).toHaveBeenCalledWith(account);
  });

  it("says data can be deleted at any time", () => {
    renderPage();
    expect(screen.getByText(/delete\s+everything at any time/)).toBeInTheDocument();
  });

  it("surfaces a failure without revealing whether the address is taken", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "register").mockRejectedValue(
      new Error("That email and password combination was not recognised."),
    );
    renderPage();

    await user.type(screen.getByLabelText("Email"), "taken@example.com");
    await user.type(screen.getByLabelText("Password"), "a-long-enough-password");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("was not recognised");
    expect(alert.textContent?.toLowerCase()).not.toContain("already");
  });
});
