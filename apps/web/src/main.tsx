import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Analytics from "./app/Analytics";
import Inbox from "./app/Inbox";
import JobDetail from "./app/JobDetail";
import Login from "./app/Login";
import Messages from "./app/Messages";
import Pipeline from "./app/Pipeline";
import RunViewer from "./app/RunViewer";
import Settings from "./app/Settings";
import Studio from "./app/Studio";
import Shell from "./components/Shell";
import { auth } from "./lib/api/client";
import "./styles.css";

const Private = ({ children }: { children: React.ReactNode }) => (auth.get() ? <>{children}</> : <Navigate to="/login" replace />);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<Private><Shell /></Private>}>
          <Route path="/inbox" element={<Inbox />} />
          <Route path="/jobs/:id" element={<JobDetail />} />
          <Route path="/studio/:id" element={<Studio />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route path="/messages" element={<Messages />} />
          <Route path="/runs/:id" element={<RunViewer />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/inbox" replace />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
