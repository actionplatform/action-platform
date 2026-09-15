export type Preset = { type: string; stack: string | null; template: string; source?: string } | null;

export type Config = {
  name: string;
  directory: string;
  packageName: string;
  description: string;
  githubOwner: string;
  ci: boolean;
  ciProvider: string;
  cloud: string | null;
};

export type ProjectOption = { id: string; name: string };
export type OwnerOption = { account: string; ok: boolean; why: string | null };
export type HostOption = { id: string; name: string; kind: string; defaultOwner: string | null; owners: readonly OwnerOption[]; installUrl: string | null; problem: string | null };

export const CI_PROVIDERS = ["github", "gitlab", "jenkins", "bitbucket"];
export const CONTINUE = ["Continue to stack", "Continue to template", "Continue to configuration", "Continue to review", "Create project"];

export function ownerOf(host: HostOption | null): string | null {
  if (!host) return null;
  if (host.owners.length === 0) return host.kind === "bitbucket" ? null : host.defaultOwner;
  return host.owners.some((o) => o.account === host.defaultOwner) ? host.defaultOwner : host.owners[0].account;
}

export function ciFor(kind: string | undefined): string {
  return kind === "gitlab" ? "gitlab" : kind === "bitbucket" ? "bitbucket" : "github";
}

export function plural(n: number, word: string) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}
