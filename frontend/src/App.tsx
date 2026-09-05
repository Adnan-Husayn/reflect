import { Route, Routes } from "react-router-dom";
import { AppNav } from "./components/AppNav";
import { LiveSession } from "./pages/LiveSession";
import { SessionDetail } from "./pages/SessionDetail";
import { Trends } from "./pages/Trends";

export default function App() {
  return (
    <>
      <AppNav />
      <Routes>
        <Route path="/" element={<LiveSession />} />
        <Route path="/trends" element={<Trends />} />
        <Route path="/sessions/:sessionId" element={<SessionDetail />} />
      </Routes>
    </>
  );
}
