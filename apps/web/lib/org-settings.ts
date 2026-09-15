import { v1 } from "./v1";

export const DEFAULT_GIT_AUTHOR = { name: "Action Platform", email: "cloud@actionplatform.io" };

export type GitAuthor = { name: string; email: string };

export async function gitAuthorOf(): Promise<GitAuthor> {
  return v1.gitAuthor();
}
