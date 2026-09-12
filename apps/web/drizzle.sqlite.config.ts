import { defineConfig } from "drizzle-kit";

export default defineConfig({
  dialect: "sqlite",
  schema: "./lib/db/schema/sqlite.ts",
  out: "./drizzle/sqlite",
});
