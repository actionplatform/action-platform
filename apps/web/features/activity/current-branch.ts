import type { CiRun } from "@/lib/ci-kinds";
import type { StoredPullRequest } from "@/lib/pull-requests";
import type { AppView } from "@/features/projects";

type BranchState = Pick<AppView, "branch" | "can" | "repositoryUrl" | "onProtectedBranch" | "workingTree" | "health">;

export function proposeBlocker(view: BranchState, openPull: Pick<StoredPullRequest, "number"> | null): string | null {
  if (!view.can["app.flow"]) return "Your role cannot open pull requests.";
  if (!view.repositoryUrl) return "Push the repository first.";
  if (view.onProtectedBranch) return `${view.branch} is protected: start a <kind>/<code> branch to propose a change.`;
  if (openPull) return `Pull request #${openPull.number} is already open from ${view.branch}.`;
  if (view.workingTree !== "clean") return "Commit or discard the pending changes first.";
  if (view.health.checked_commits === 0) return `${view.branch} has no commits beyond its base yet.`;
  return null;
}

export function latestRunOn(runs: CiRun[], branch: string): CiRun | null {
  return runs.find((r) => r.branch === branch) ?? null;
}

export function openPullFrom(pulls: Pick<StoredPullRequest, "number" | "head" | "state" | "url">[], branch: string) {
  return pulls.find((p) => p.state === "open" && p.head === branch) ?? null;
}
