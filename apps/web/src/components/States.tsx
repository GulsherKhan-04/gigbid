import type { ReactNode } from "react";

export const Loading = ({ rows = 4 }: { rows?: number }) => (
  <div aria-busy="true" aria-live="polite">{Array.from({ length: rows }, (_, i) => <div key={i} className="skeleton" />)}<span className="sr-only">Loading</span></div>
);
export const ErrorBox = ({ message, retry }: { message: string; retry?: () => void }) => (
  <div className="error" role="alert">{message} {retry && <button className="btn-quiet" onClick={retry}>Try again</button>}</div>
);
export const Empty = ({ title, children }: { title: string; children?: ReactNode }) => (
  <div className="empty"><h2>{title}</h2>{children}</div>
);
