"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", display: "flex", minHeight: "100vh", alignItems: "center", justifyContent: "center", margin: 0 }}>
        <div style={{ textAlign: "center", padding: 24 }}>
          <h1 style={{ fontSize: 17, fontWeight: 600 }}>Something went wrong</h1>
          <p style={{ fontSize: 14, opacity: 0.7 }}>{error.digest ? `Reference ${error.digest}` : "The error was recorded."}</p>
          <button onClick={reset} style={{ marginTop: 16, padding: "8px 14px", borderRadius: 6, border: "1px solid currentColor", background: "transparent", cursor: "pointer" }}>Try again</button>
        </div>
      </body>
    </html>
  );
}
