import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login } from "../services/api";
import type { Account } from "../types/emotion";

interface LoginProps {
  onSignedIn: (account: Account) => void;
}

export function Login({ onSignedIn }: LoginProps) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const account = await login(email.trim(), password);
      onSignedIn(account);
      navigate("/session", { replace: true });
    } catch (loginError) {
      // The server returns the same message for a wrong password and an
      // unknown address; passing it through keeps that property.
      setError(loginError instanceof Error ? loginError.message : "Could not sign in.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="page-shell auth-page">
      <header className="page-header">
        <p className="project-code">PCS26/146</p>
        <h1>Sign in</h1>
        <p>Your sessions and check-ins are private to your account.</p>
      </header>

      <form className="auth-form" onSubmit={submit}>
        {error && <p className="status-message status-error" role="alert">{error}</p>}

        <label htmlFor="login-email">Email</label>
        <input
          id="login-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        <button type="submit" className="secondary-button" disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="auth-alt">
        No account yet? <Link to="/register">Create one</Link>.
      </p>
    </main>
  );
}
