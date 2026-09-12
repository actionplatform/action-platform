import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { nextCookies } from "better-auth/next-js";
import { bearer, deviceAuthorization, organization } from "better-auth/plugins";
import { readConfig } from "./config";
import { type Connection, getConnection } from "./db";

function create(conn: Connection, authSecret: string | undefined, allowSignUp = false) {
  return betterAuth({
    secret: authSecret,
    baseURL: process.env.BETTER_AUTH_URL,
    database: drizzleAdapter(conn.db, { provider: conn.engine, schema: conn.schema }),
    emailAndPassword: { enabled: true, disableSignUp: !allowSignUp },
    plugins: [
      organization(),
      deviceAuthorization({ verificationUri: "/device", expiresIn: "10m", interval: "3s" }),
      bearer(),
      nextCookies(),
    ],
  });
}

export type Auth = ReturnType<typeof create>;

export async function getSetupAuth(): Promise<Auth> {
  return create(await getConnection(), readConfig().authSecret, true);
}

let cached: { key: string; auth: Auth } | null = null;

export async function getAuth(): Promise<Auth> {
  const { databaseUrl, authSecret } = readConfig();
  const key = `${databaseUrl}|${authSecret}`;

  if (cached?.key !== key) {
    cached = { key, auth: create(await getConnection(), authSecret) };
  }

  return cached.auth;
}
