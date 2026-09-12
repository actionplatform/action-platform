import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  serverExternalPackages: ["postgres", "mysql2", "@libsql/client"],
};

export default config;
