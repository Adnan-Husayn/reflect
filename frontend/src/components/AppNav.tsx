import { Link, NavLink, useNavigate } from "react-router-dom";
import type { AuthState } from "../hooks/useAuth";
import { logout } from "../services/api";

const links = [
  { to: "/session", label: "Live session" },
  { to: "/check-in", label: "Check-in" },
  { to: "/this-week", label: "This week" },
  { to: "/trends", label: "Trends" },
];

interface AppNavProps {
  account: AuthState;
  onSignedOut: () => void;
}

export function AppNav({ account, onSignedOut }: AppNavProps) {
  const navigate = useNavigate();
  const signedIn = account !== null && account !== "loading";

  const signOut = async () => {
    try {
      await logout();
    } finally {
      // Clear local state regardless: if the call failed the cookie may still
      // be set, but leaving the UI signed in would be worse than a stale cookie.
      onSignedOut();
      navigate("/", { replace: true });
    }
  };

  return (
    <nav className="app-nav" aria-label="Main">
      <Link to="/" className="app-nav-brand">
        Reflect
      </Link>

      {signedIn &&
        links.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => (isActive ? "app-nav-link active" : "app-nav-link")}
          >
            {label}
          </NavLink>
        ))}

      {signedIn ? (
        <div className="app-nav-account">
          <span className="app-nav-email">{account.email}</span>
          <button type="button" className="text-button" onClick={signOut}>
            Sign out
          </button>
        </div>
      ) : (
        <div className="app-nav-account">
          <Link to="/login" className="app-nav-link">
            Sign in
          </Link>
        </div>
      )}
    </nav>
  );
}
