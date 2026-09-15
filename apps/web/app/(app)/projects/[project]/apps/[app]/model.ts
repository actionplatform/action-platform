import type { Grants } from "@/lib/permissions";
import type { AppDetail, Branch, Commit, GitflowReport } from "@/lib/api";

export type AppView = {
  projectId: string;
  projectName: string;
  projectSlug: string;
  orgSlug: string;
  appId: string;
  registryId: string;
  name: string;
  repository: string | null;
  repositoryUrl: string | null;
  sourceKind: string | null;
  branch: string;
  version: string | null;
  latestTag: string | null;
  workingTree: "clean" | "dirty" | "unknown";
  tags: string[];
  labels: string[];
  releaseStrategy: string | null;
  commitConvention: string | null;
  ci: string | null;
  deploy: Record<string, unknown>;
  services: string[];
  health: GitflowReport;
  commits: Commit[];
  branches: Branch[];
  isStableBranch: boolean;
  stableBranches: string[];
  onProtectedBranch: boolean;
  branchKinds: string[];
  lastSyncedAt: string | null;
  manifest: string;
  changes: string[];
  can: Grants;
  type: string | null;
  language: string | null;
};

const SOURCES: Record<string, string> = { github: "GitHub", gitlab: "GitLab", bitbucket: "Bitbucket", generic: "Git" };
const CIS: Record<string, string> = { github: "GitHub Actions", gitlab: "GitLab CI", jenkins: "Jenkins", bitbucket: "Bitbucket Pipelines" };

export function sourceLabel(kind: string | null): string {
  return kind ? (SOURCES[kind] ?? kind) : "None";
}

export function ciLabel(ci: string | null): string | null {
  return ci ? (CIS[ci] ?? ci) : null;
}

export function toView(input: { projectId: string; projectName: string; projectSlug: string; orgSlug: string; appId: string; appName: string; detail: AppDetail; health: GitflowReport; commits: Commit[]; branches: Branch[]; tags: string[]; lastSyncedAt: Date | null; manifest: string; changes: string[]; grants: Grants; rules: { kinds: string[]; protected: string[] } }): AppView {
  const { detail } = input;
  const meta = detail.project;
  const repo = detail.source_host.repo || null;
  const kind = detail.source_host.kind || null;
  const url = detail.url ? detail.url.replace(/\.git$/, "") : null;
  return {
    projectId: input.projectId,
    projectName: input.projectName,
    projectSlug: input.projectSlug,
    orgSlug: input.orgSlug,
    appId: input.appId,
    registryId: detail.id,
    name: input.appName || meta.name,
    repository: repo,
    repositoryUrl: url,
    sourceKind: kind,
    branch: detail.branch,
    version: detail.last_version ?? null,
    latestTag: detail.latest_tag ?? null,
    workingTree: detail.branch ? (detail.clean ? "clean" : "dirty") : "unknown",
    tags: input.tags,
    labels: [meta.type, meta.language, meta.ci ? `ci: ${meta.ci}` : null].filter((x): x is string => !!x),
    releaseStrategy: detail.release.strategy ?? null,
    commitConvention: detail.release.changelog ?? null,
    ci: meta.ci ?? null,
    deploy: detail.deploy,
    services: Object.keys(detail.services),
    health: input.health,
    commits: input.commits,
    branches: input.branches,
    isStableBranch: input.branches.some((b) => b.name === detail.branch && b.stable),
    stableBranches: input.branches.filter((b) => b.stable).map((b) => b.name),
    onProtectedBranch: input.rules.protected.includes(detail.branch),
    branchKinds: input.rules.kinds,
    lastSyncedAt: input.lastSyncedAt ? input.lastSyncedAt.toISOString() : null,
    manifest: input.manifest,
    changes: input.changes,
    can: input.grants,
    type: meta.type ?? null,
    language: meta.language ?? null,
  };
}
