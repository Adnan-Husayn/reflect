import { Navigate, useLocation } from "react-router-dom";
import type { AuthState } from "../hooks/useAuth";

interface RequireAuthProps {
  account: AuthState;
  children: React.ReactNode;
}

export function RequireAuth({ account, children }: RequireAuthProps) {
  const location = useLocation();

  // Render nothing while the session is still resolving, rather than flashing
  // the login form at somebody who is already signed in.
  if (account === "loading") return null;

  if (account === null) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
