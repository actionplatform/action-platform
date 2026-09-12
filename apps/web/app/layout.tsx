import type { ReactNode } from "react";
import "./globals.css";

export const metadata = { title: "action-platform" };
export const dynamic = "force-dynamic";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
