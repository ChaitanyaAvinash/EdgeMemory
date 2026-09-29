import { ViewTransition } from "react";

// Re-mounted on every navigation. The View Transitions API fades the old page out and the new one in
// (app/globals.css .page-in / .page-out); browsers without it swap instantly.
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <ViewTransition enter="page-in" exit="page-out" default="none">
      <div>{children}</div>
    </ViewTransition>
  );
}
