// better-auth core tables, mysql dialect. Keep in sync with pg.ts and sqlite.ts.
import { boolean, int, mysqlTable, text, timestamp, varchar } from "drizzle-orm/mysql-core";

export const user = mysqlTable("user", {
  id: varchar("id", { length: 36 }).primaryKey(),
  name: text("name").notNull(),
  email: varchar("email", { length: 255 }).notNull().unique(),
  emailVerified: boolean("email_verified").notNull().default(false),
  image: text("image"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

export const session = mysqlTable("session", {
  id: varchar("id", { length: 36 }).primaryKey(),
  expiresAt: timestamp("expires_at").notNull(),
  token: varchar("token", { length: 255 }).notNull().unique(),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
  ipAddress: text("ip_address"),
  userAgent: text("user_agent"),
  userId: varchar("user_id", { length: 36 }).notNull().references(() => user.id, { onDelete: "cascade" }),
  activeOrganizationId: varchar("active_organization_id", { length: 36 }),
});

export const account = mysqlTable("account", {
  id: varchar("id", { length: 36 }).primaryKey(),
  accountId: text("account_id").notNull(),
  providerId: text("provider_id").notNull(),
  userId: varchar("user_id", { length: 36 }).notNull().references(() => user.id, { onDelete: "cascade" }),
  accessToken: text("access_token"),
  refreshToken: text("refresh_token"),
  idToken: text("id_token"),
  accessTokenExpiresAt: timestamp("access_token_expires_at"),
  refreshTokenExpiresAt: timestamp("refresh_token_expires_at"),
  scope: text("scope"),
  password: text("password"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

export const verification = mysqlTable("verification", {
  id: varchar("id", { length: 36 }).primaryKey(),
  identifier: varchar("identifier", { length: 255 }).notNull(),
  value: text("value").notNull(),
  expiresAt: timestamp("expires_at").notNull(),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

// better-auth deviceAuthorization plugin: CLI/MCP login through the browser.
export const deviceCode = mysqlTable("device_code", {
  id: varchar("id", { length: 36 }).primaryKey(),
  deviceCode: varchar("device_code", { length: 255 }).notNull(),
  userCode: varchar("user_code", { length: 32 }).notNull(),
  userId: varchar("user_id", { length: 36 }),
  expiresAt: timestamp("expires_at").notNull(),
  status: varchar("status", { length: 16 }).notNull(),
  lastPolledAt: timestamp("last_polled_at"),
  pollingInterval: int("polling_interval"),
  clientId: text("client_id"),
  scope: text("scope"),
});

// better-auth organization plugin: the tenant, its members and invitations.
export const organization = mysqlTable("organization", {
  id: varchar("id", { length: 36 }).primaryKey(),
  name: text("name").notNull(),
  slug: varchar("slug", { length: 255 }).notNull().unique(),
  logo: text("logo"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  metadata: text("metadata"),
});

export const member = mysqlTable("member", {
  id: varchar("id", { length: 36 }).primaryKey(),
  organizationId: varchar("organization_id", { length: 36 }).notNull().references(() => organization.id, { onDelete: "cascade" }),
  userId: varchar("user_id", { length: 36 }).notNull().references(() => user.id, { onDelete: "cascade" }),
  role: varchar("role", { length: 32 }).notNull(),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const invitation = mysqlTable("invitation", {
  id: varchar("id", { length: 36 }).primaryKey(),
  organizationId: varchar("organization_id", { length: 36 }).notNull().references(() => organization.id, { onDelete: "cascade" }),
  email: varchar("email", { length: 255 }).notNull(),
  role: varchar("role", { length: 32 }),
  status: varchar("status", { length: 16 }).notNull(),
  expiresAt: timestamp("expires_at").notNull(),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  inviterId: varchar("inviter_id", { length: 36 }).notNull().references(() => user.id, { onDelete: "cascade" }),
});

// Organization › Project › App. A project groups apps; an app is one git
// repository the Python API manages (registry id in `registryId`).
export const project = mysqlTable("project", {
  id: varchar("id", { length: 36 }).primaryKey(),
  organizationId: varchar("organization_id", { length: 36 }).notNull().references(() => organization.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  slug: varchar("slug", { length: 255 }).notNull(),
  description: text("description"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const app = mysqlTable("app", {
  id: varchar("id", { length: 36 }).primaryKey(),
  projectId: varchar("project_id", { length: 36 }).notNull().references(() => project.id, { onDelete: "cascade" }),
  registryId: varchar("registry_id", { length: 64 }).notNull().unique(),
  name: text("name").notNull(),
  sourceHostId: varchar("source_host_id", { length: 36 }),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

// Code hosts an organization can push to: GitHub, GitLab, Bitbucket or any
// git server. The token is encrypted with the app secret before it is stored.
export const sourceHost = mysqlTable("source_host", {
  id: varchar("id", { length: 36 }).primaryKey(),
  organizationId: varchar("organization_id", { length: 36 }).notNull().references(() => organization.id, { onDelete: "cascade" }),
  kind: varchar("kind", { length: 16 }).notNull(),
  name: text("name").notNull(),
  baseUrl: text("base_url"),
  username: text("username"),
  tokenEncrypted: text("token_encrypted").notNull(),
  defaultOwner: text("default_owner"),
  authKind: varchar("auth_kind", { length: 16 }).notNull().default("token"),
  login: text("login"),
  refreshTokenEncrypted: text("refresh_token_encrypted"),
  expiresAt: timestamp("expires_at"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});
