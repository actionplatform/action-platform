import { eq } from "drizzle-orm";
import { q } from "./db/query";

export const DEFAULT_GIT_AUTHOR = { name: "Action Platform", email: "cloud@actionplatform.io" };

export type GitAuthor = { name: string; email: string };

export async function gitAuthorOf(orgId: string): Promise<GitAuthor> {
  const { db, t } = await q();
  const rows = await db.select().from(t.organizationSetting).where(eq(t.organizationSetting.organizationId, orgId)).limit(1);
  const row = rows[0];
  return row ? { name: row.gitAuthorName, email: row.gitAuthorEmail } : DEFAULT_GIT_AUTHOR;
}

export async function setGitAuthor(orgId: string, author: GitAuthor): Promise<GitAuthor> {
  const name = author.name.trim();
  const email = author.email.trim().toLowerCase();
  if (!name) throw new Error("name is required");
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) throw new Error("enter a valid email");
  const { db, t } = await q();
  const existing = await db.select({ id: t.organizationSetting.organizationId }).from(t.organizationSetting).where(eq(t.organizationSetting.organizationId, orgId)).limit(1);
  const now = new Date();
  if (existing.length) {
    await db.update(t.organizationSetting).set({ gitAuthorName: name, gitAuthorEmail: email, updatedAt: now }).where(eq(t.organizationSetting.organizationId, orgId));
  } else {
    await db.insert(t.organizationSetting).values({ organizationId: orgId, gitAuthorName: name, gitAuthorEmail: email, updatedAt: now });
  }
  return { name, email };
}
