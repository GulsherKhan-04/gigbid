import { NavLink, Outlet } from "react-router-dom";
import { useHealth } from "../lib/hooks";

const I = (d: string) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>
);
const NAV = [
  ["/inbox", "Inbox", "M3 13h5l2 3h4l2-3h5M5 5h14l2 8v6H3v-6z"],
  ["/pipeline", "Pipeline", "M4 5h4v14H4zM10 5h4v9h-4zM16 5h4v6h-4z"],
  ["/messages", "Messages", "M4 5h16v11H8l-4 4z"],
  ["/analytics", "Analytics", "M4 20V10M10 20V4M16 20v-7M22 20H2"],
  ["/settings", "Settings", "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19 12l2-1-1-3-2 .2-1.5-1.5L17 5l-3-1-1 2h-2L10 4 7 5l.5 1.7L6 8.2 4 8l-1 3 2 1v0l-2 1 1 3 2-.2 1.5 1.5L7 19l3 1 1-2h2l1 2 3-1-.5-1.7 1.5-1.5 2 .2 1-3z"],
] as const;

export default function Shell() {
  const degraded = useHealth();
  return (
    <div className="shell">
      <nav className="rail" aria-label="Main">
        <div className="mark" aria-hidden="true">
          <svg width="26" height="26" viewBox="0 0 32 32"><path d="M6 20h20" stroke="#FFE58A" strokeWidth="6" strokeLinecap="round" /><path d="M6 11h13" stroke="currentColor" strokeWidth="3" strokeLinecap="round" /></svg>
        </div>
        {NAV.map(([to, label, d]) => (
          <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : "")}>{I(d)}<span>{label}</span></NavLink>
        ))}
      </nav>
      <main className="main" id="main">
        {degraded.length > 0 && (
          <div className="banner" role="status" data-testid="degraded-banner">
            Marketplace connection is down ({degraded.join(", ")}). New work is queued and will resume automatically when it is back.
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
