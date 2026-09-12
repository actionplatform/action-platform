import { defineConfig } from "drizzle-kit";

export default defineConfig({
  dialect: "mysql",
  schema: "./lib/db/schema/mysql.ts",
  out: "./drizzle/mysql",
});
