import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../services/api";
import type { Account } from "../types/emotion";

const MIN_PASSWORD_LENGTH = 10;

interface RegisterProps {
  onSignedIn: (account: Account) => void;
}

export function Register({ onSignedIn }: RegisterProps) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const tooShort = password.length > 0 && password.length < MIN_PASSWORD_LENGTH;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const account = await register(email.trim(), password);
      onSignedIn(account);
      navigate("/session", { replace: true });
    } catch (registerError) {
      setError(
        registerError instanceof Error ? registerError.message : "Could not create the account.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="page-shell auth-page">
      <header className="page-header">
        <p className="project-code">PCS26/146</p>
        <h1>Create an account</h1>
        <p>
          Reflect records what you choose to record, and only you can see it. You can delete
          everything at any time from the check-in page.
        </p>
      </header>

      <form className="auth-form" onSubmit={submit}>
        {error && <p className="status-message status-error" role="alert">{error}</p>}

        <label htmlFor="register-email">Email</label>
        <input
          id="register-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <label htmlFor="register-password">Password</label>
        <input
          id="register-password"
          type="password"
          autoComplete="new-password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <span className={tooShort ? "field-hint warning" : "field-hint"}>
          At least {MIN_PASSWORD_LENGTH} characters.
        </span>

        <button
          type="submit"
          className="secondary-button"
          disabled={isSubmitting || password.length < MIN_PASSWORD_LENGTH}
        >
          {isSubmitting ? "Creating…" : "Create account"}
        </button>
      </form>

      <p className="auth-alt">
        Already have an account? <Link to="/login">Sign in</Link>.
      </p>
    </main>
  );
}
