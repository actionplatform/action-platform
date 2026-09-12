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
    // Accounts are created by the setup wizard (and invites later), never
    // from the public form.
    emailAndPassword: { enabled: true, disableSignUp: !allowSignUp },
    plugins: [
      nextCookies(),
      // Organization › Project › App: the org is the tenant; the session
      // carries the active one.
      organization(),
      // CLI / MCP: `action-platform login` gets a device code, the user
      // approves it at /device in the browser, the CLI polls for a token.
      deviceAuthorization({ verificationUri: "/device", expiresIn: "10m", interval: "3s" }),
      // ...and then sends it as `Authorization: Bearer <token>`.
      bearer(),
    ],
  });
}

export type Auth = ReturnType<typeof create>;

// Only the setup wizard uses this, to create the first account.
export async function getSetupAuth(): Promise<Auth> {
  return create(await getConnection(), readConfig().authSecret, true);
}

let cached: { key: string; auth: Auth } | null = null;

// Built on first use and rebuilt when the config changes, so the setup
// wizard can point it at a database without a restart.
export async function getAuth(): Promise<Auth> {
  const { databaseUrl, authSecret } = readConfig();
  const key = `${databaseUrl}|${authSecret}`;

  if (cached?.key !== key) {
    cached = { key, auth: create(await getConnection(), authSecret) };
  }

  return cached.auth;
}
