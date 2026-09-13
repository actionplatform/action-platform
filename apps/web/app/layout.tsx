import type { ReactNode } from "react";
import { sentryMeta } from "@/lib/sentry";
import "./globals.css";

export const metadata = { title: "action-platform" };
export const dynamic = "force-dynamic";

export default function RootLayout({ children }: { children: ReactNode }) {
  const sentry = sentryMeta();
  return (
    <html lang="en">
      <head>{sentry && <meta name="sentry" content={JSON.stringify(sentry)} />}</head>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
