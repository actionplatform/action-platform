import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  // Self-contained server for the Docker image: .next/standalone + static.
  output: "standalone",
  // Migrations are read from disk at runtime; keep them out of the bundle.
  serverExternalPackages: ["postgres", "mysql2", "@libsql/client"],
};

export default config;
