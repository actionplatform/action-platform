import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CiState } from "@/lib/ci-kinds";
import type { AppView } from "@/features/projects";
import { CurrentBranchCard } from "./current-branch-card";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }) }));
vi.mock("@/features/ci/actions", () => ({ startCi: vi.fn(), syncCi: vi.fn(), linkCi: vi.fn() }));

const view = (over: Partial<AppView> = {}) => ({
  projectId: "p1",
  appId: "a1",
  branch: "feature/7-login",
  can: { "app.flow": true, "app.configure": true },
  repositoryUrl: "https://github.com/acme/app",
  onProtectedBranch: false,
  workingTree: "clean",
  health: { branch: "feature/7-login", problems: [], checked_commits: 3, ok: true },
  ...over,
}) as AppView;

const ci = (runs: Partial<CiState["runs"][number]>[] = [], kind = "github_actions"): CiState => ({
  link: { kind, ciHostId: null, job: "" },
  runs: runs.map((r, i) => ({ id: `r${i}`, source: kind, number: 10 - i, status: "success", name: null, url: null, branch: null, sha: null, trigger: null, startedAt: null, durationMs: null, syncedAt: "2026-11-25T10:00:00", ...r })),
  error: null,
  total: runs.length,
  page: 1,
  per: 100,
});

const props = { newHref: "/projects/p1/apps/a1/pull-requests/new", ciSettingsHref: "/projects/p1/apps/a1/settings?tab=ci" };

describe("CurrentBranchCard", () => {
  afterEach(cleanup);

  it("shows the branch's latest run with a link to the CI and opens a pull request", () => {
    render(<CurrentBranchCard view={view()} ci={ci([{ branch: "main", status: "failure" }, { branch: "feature/7-login", status: "success", name: "CI", url: "https://ci.example/run/9" }])} pulls={[]} {...props} />);
    expect(screen.getByText("Passed")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^CI/ })).toHaveAttribute("href", "https://ci.example/run/9");
    expect(screen.getByRole("link", { name: "Open pull request" })).toHaveAttribute("href", props.newHref);
    expect(screen.getByText("3 commits to propose.")).toBeInTheDocument();
  });

  it("disables the pull request when there is nothing to propose", () => {
    render(<CurrentBranchCard view={view({ branch: "develop", onProtectedBranch: true })} ci={ci()} pulls={[]} {...props} />);
    expect(screen.getByRole("button", { name: "Open pull request" })).toBeDisabled();
    expect(screen.getByText(/develop is protected/)).toBeInTheDocument();
    expect(screen.getByText(/No run on/)).toBeInTheDocument();
  });

  it("points at the open pull request instead of opening another", () => {
    render(<CurrentBranchCard view={view()} ci={ci()} pulls={[{ number: 4, head: "feature/7-login", state: "open", url: "https://github.com/acme/app/pull/4" } as never]} {...props} />);
    expect(screen.getByRole("link", { name: /#4 open/ })).toHaveAttribute("href", "https://github.com/acme/app/pull/4");
    expect(screen.getByRole("button", { name: "Open pull request" })).toBeDisabled();
  });

  it("sends to Settings to connect a CI", () => {
    render(<CurrentBranchCard view={view()} ci={ci([], "none")} pulls={[]} {...props} />);
    expect(screen.getByRole("link", { name: "Connect CI" })).toHaveAttribute("href", props.ciSettingsHref);
    expect(screen.queryByRole("button", { name: /Run CI/ })).toBeNull();
  });
});
