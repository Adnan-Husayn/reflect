import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import { AppNav } from "./components/AppNav";
import { RequireAuth } from "./components/RequireAuth";
import { useAuth } from "./hooks/useAuth";
import { CheckIn } from "./pages/CheckIn";
import { Landing } from "./pages/Landing";
import { LiveSession } from "./pages/LiveSession";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";

// Recharts is most of the bundle, and neither the landing page nor the live
// session needs any of it.
const Trends = lazy(() => import("./pages/Trends").then((m) => ({ default: m.Trends })));
const SessionDetail = lazy(() =>
  import("./pages/SessionDetail").then((m) => ({ default: m.SessionDetail })),
);
const Wellbeing = lazy(() => import("./pages/Wellbeing").then((m) => ({ default: m.Wellbeing })));

export default function App() {
  const { account, setAccount } = useAuth();

  const protect = (element: React.ReactNode) => (
    <RequireAuth account={account}>{element}</RequireAuth>
  );

  return (
    <>
      <AppNav account={account} onSignedOut={() => setAccount(null)} />
      <Suspense fallback={<p className="loading-note page-shell">Loading…</p>}>
        <Routes>
          {/* Public. A visitor lands here rather than on a sign-in form. */}
          <Route path="/" element={<Landing account={account} />} />
          <Route path="/login" element={<Login onSignedIn={setAccount} />} />
          <Route path="/register" element={<Register onSignedIn={setAccount} />} />
          <Route path="/session" element={protect(<LiveSession />)} />
          <Route path="/check-in" element={protect(<CheckIn />)} />
          <Route path="/this-week" element={protect(<Wellbeing />)} />
          <Route path="/trends" element={protect(<Trends />)} />
          <Route path="/sessions/:sessionId" element={protect(<SessionDetail />)} />
        </Routes>
      </Suspense>
    </>
  );
}
