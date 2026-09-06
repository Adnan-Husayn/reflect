import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Login } from "./Login";
import * as api from "../services/api";

const account = { id: "u-1", email: "tester@example.com" };

function renderPage(onSignedIn = vi.fn()) {
  render(
    <MemoryRouter>
      <Login onSignedIn={onSignedIn} />
    </MemoryRouter>,
  );
  return onSignedIn;
}

describe("Login", () => {
  afterEach(() => vi.restoreAllMocks());

  it("signs in with the submitted credentials", async () => {
    const user = userEvent.setup();
    const login = vi.spyOn(api, "login").mockResolvedValue(account);
    const onSignedIn = renderPage();

    await user.type(screen.getByLabelText("Email"), "tester@example.com");
    await user.type(screen.getByLabelText("Password"), "a-long-enough-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(login).toHaveBeenCalledWith("tester@example.com", "a-long-enough-password"));
    expect(onSignedIn).toHaveBeenCalledWith(account);
  });

  it("passes the server's message through unchanged", async () => {
    const user = userEvent.setup();
    // The same message covers a wrong password and an unknown address; the
    // form must not add anything that distinguishes them.
    vi.spyOn(api, "login").mockRejectedValue(
      new Error("That email and password combination was not recognised."),
    );
    renderPage();

    await user.type(screen.getByLabelText("Email"), "tester@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That email and password combination was not recognised.",
    );
  });

  it("offers a route to registration", () => {
    renderPage();
    expect(screen.getByRole("link", { name: "Create one" })).toHaveAttribute("href", "/register");
  });
});
