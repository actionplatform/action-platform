import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { nextCookies } from "better-auth/next-js";
import { db } from "./db";
import * as schema from "./db/schema";

export const auth = betterAuth({
  database: drizzleAdapter(db, { provider: "sqlite", schema }),
  emailAndPassword: { enabled: true },
  // First user to sign up owns the instance; later sign-ups need an invite.
  // Until invites exist, AP_OPEN_SIGNUP=true keeps the form open.
  plugins: [nextCookies()],
});

export type Session = typeof auth.$Infer.Session;
