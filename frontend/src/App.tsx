import { Route, Routes } from "react-router-dom";
import { AppNav } from "./components/AppNav";
import { RequireAuth } from "./components/RequireAuth";
import { useAuth } from "./hooks/useAuth";
import { CheckIn } from "./pages/CheckIn";
import { LiveSession } from "./pages/LiveSession";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { SessionDetail } from "./pages/SessionDetail";
import { Trends } from "./pages/Trends";

export default function App() {
  const { account, setAccount } = useAuth();

  const protect = (element: React.ReactNode) => (
    <RequireAuth account={account}>{element}</RequireAuth>
  );

  return (
    <>
      <AppNav account={account} onSignedOut={() => setAccount(null)} />
      <Routes>
        <Route path="/login" element={<Login onSignedIn={setAccount} />} />
        <Route path="/register" element={<Register onSignedIn={setAccount} />} />
        <Route path="/" element={protect(<LiveSession />)} />
        <Route path="/check-in" element={protect(<CheckIn />)} />
        <Route path="/trends" element={protect(<Trends />)} />
        <Route path="/sessions/:sessionId" element={protect(<SessionDetail />)} />
      </Routes>
    </>
  );
}
