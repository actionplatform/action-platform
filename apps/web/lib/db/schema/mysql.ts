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

export const team = mysqlTable("team", {
  id: varchar("id", { length: 36 }).primaryKey(),
  organizationId: varchar("organization_id", { length: 36 }).notNull().references(() => organization.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  slug: varchar("slug", { length: 255 }).notNull(),
  description: text("description"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const teamMember = mysqlTable("team_member", {
  id: varchar("id", { length: 36 }).primaryKey(),
  teamId: varchar("team_id", { length: 36 }).notNull().references(() => team.id, { onDelete: "cascade" }),
  userId: varchar("user_id", { length: 36 }).notNull().references(() => user.id, { onDelete: "cascade" }),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const project = mysqlTable("project", {
  id: varchar("id", { length: 36 }).primaryKey(),
  organizationId: varchar("organization_id", { length: 36 }).notNull().references(() => organization.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  slug: varchar("slug", { length: 255 }).notNull(),
  description: text("description"),
  teamId: varchar("team_id", { length: 36 }),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const app = mysqlTable("app", {
  id: varchar("id", { length: 36 }).primaryKey(),
  projectId: varchar("project_id", { length: 36 }).notNull().references(() => project.id, { onDelete: "cascade" }),
  registryId: varchar("registry_id", { length: 64 }).notNull().unique(),
  name: text("name").notNull(),
  sourceHostId: varchar("source_host_id", { length: 36 }),
  lastSyncedAt: timestamp("last_synced_at"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

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

export const release = mysqlTable("release", {
  id: varchar("id", { length: 36 }).primaryKey(),
  appId: varchar("app_id", { length: 36 }).notNull().references(() => app.id, { onDelete: "cascade" }),
  tag: varchar("tag", { length: 255 }).notNull(),
  name: text("name"),
  body: text("body"),
  url: text("url"),
  author: text("author"),
  sha: varchar("sha", { length: 64 }),
  prerelease: boolean("prerelease").notNull().default(false),
  draft: boolean("draft").notNull().default(false),
  publishedAt: timestamp("published_at"),
  source: varchar("source", { length: 16 }).notNull(),
  syncedAt: timestamp("synced_at").notNull().defaultNow(),
});

export const pullRequest = mysqlTable("pull_request", {
  id: varchar("id", { length: 36 }).primaryKey(),
  appId: varchar("app_id", { length: 36 }).notNull().references(() => app.id, { onDelete: "cascade" }),
  number: int("number").notNull(),
  title: text("title").notNull(),
  url: text("url").notNull(),
  author: text("author"),
  head: text("head").notNull(),
  base: text("base").notNull(),
  state: varchar("state", { length: 16 }).notNull(),
  draft: boolean("draft").notNull().default(false),
  createdAt: timestamp("created_at").notNull(),
  updatedAt: timestamp("updated_at").notNull(),
  mergedAt: timestamp("merged_at"),
  source: varchar("source", { length: 32 }).notNull(),
  syncedAt: timestamp("synced_at").notNull().defaultNow(),
});

export const templateSource = mysqlTable("template_source", {
  id: varchar("id", { length: 36 }).primaryKey(),
  organizationId: varchar("organization_id", { length: 36 }).notNull().references(() => organization.id, { onDelete: "cascade" }),
  name: varchar("name", { length: 64 }).notNull(),
  url: text("url").notNull(),
  ref: varchar("ref", { length: 128 }).notNull().default("v1"),
  sourceHostId: varchar("source_host_id", { length: 36 }),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const organizationSetting = mysqlTable("organization_setting", {
  organizationId: varchar("organization_id", { length: 36 }).primaryKey().references(() => organization.id, { onDelete: "cascade" }),
  gitAuthorName: varchar("git_author_name", { length: 255 }).notNull(),
  gitAuthorEmail: varchar("git_author_email", { length: 255 }).notNull(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

export const apiToken = mysqlTable("api_token", {
  id: varchar("id", { length: 36 }).primaryKey(),
  userId: varchar("user_id", { length: 36 }).notNull().references(() => user.id, { onDelete: "cascade" }),
  organizationId: varchar("organization_id", { length: 36 }).notNull().references(() => organization.id, { onDelete: "cascade" }),
  name: varchar("name", { length: 255 }).notNull(),
  scope: varchar("scope", { length: 255 }).notNull(),
  projectId: varchar("project_id", { length: 36 }),
  appId: varchar("app_id", { length: 36 }),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  expiresAt: timestamp("expires_at").notNull(),
  lastUsedAt: timestamp("last_used_at"),
  revokedAt: timestamp("revoked_at"),
});
