import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ScopeProvider, useScope } from "@/components/layout/scope";
import type { ActiveDeployment, Dashboard, DashboardEvent } from "@/lib/insights";
import { DashboardView } from "./dashboard";
import { DashboardError } from "./dashboard-error";
import { grouped } from "./events";
import { REFRESH_MS } from "./in-progress";

const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router, usePathname: () => "/dashboard" }));

const NOW = Date.UTC(2026, 10, 24, 15, 0, 0);

const event = (title: string, status: string, app = "a1"): DashboardEvent => ({ app_id: app, app, project_id: "p1", project: "platform", kind: "ci_run", title, status, at: null });

const active = (id: string, over: Partial<ActiveDeployment> = {}): ActiveDeployment => ({ id, app_id: "a1", app: "api", project_id: "p1", project: "core", target: "lambda-prod", kind: "aws/lambda", stage: "prod", version: "0.59.1", status: "running", started_at: "2026-11-24T14:57:46Z", url: null, ...over });

const data = (over: Partial<Dashboard> = {}): Dashboard => ({
  apps: 10,
  deployments_today: {},
  ci_today: {},
  releases_week: 1,
  without_ci: [],
  events: [],
  in_progress: [],
  ...over,
});

function view(d: Dashboard, orgId = "o1") {
  return render(<ScopeProvider><DashboardView key={orgId} data={d} orgId={orgId} /></ScopeProvider>);
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "Date"] });
  vi.setSystemTime(NOW);
  router.push.mockClear();
  router.refresh.mockClear();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("metrics", () => {
  it("shows four cards with the day's details, red only on failures", () => {
    view(data({ apps: 20, deployments_today: { success: 139, verified: 13, failure: 4 }, ci_today: { success: 12, failure: 1 }, releases_week: 7 }));
    const metrics = screen.getByTestId("metrics");
    for (const label of ["Apps", "Deployments today", "CI runs today", "Releases this week"]) expect(within(metrics).getByText(label)).toBeInTheDocument();
    expect(within(metrics).getByText("152")).toHaveClass("text-foreground");
    expect(within(metrics).getByText("13")).toBeInTheDocument();
    expect(within(metrics).getByText(/13 verified/)).toBeInTheDocument();
    expect(within(metrics).getByText("4 failed")).toHaveClass("text-status-bad");
    expect(within(metrics).getByText("1 failed")).toHaveClass("text-status-bad");
  });

  it("does not colour zero failures", () => {
    view(data());
    for (const el of within(screen.getByTestId("metrics")).getAllByText("0 failed")) expect(el).not.toHaveClass("text-status-bad");
  });
});

describe("deployments in progress", () => {
  it("lists the active deployments with environment, status and elapsed time", () => {
    view(data({ in_progress: [active("d1"), active("d2", { target: "amplify-dev", version: "0.48.0-rc.2", stage: "dev", status: "queued", started_at: "2026-11-24T14:59:12Z" })] }));
    const rows = screen.getAllByTestId("in-progress-row");
    expect(rows).toHaveLength(2);
    expect(screen.getByTestId("in-progress-count")).toHaveTextContent("2 in progress");
    expect(within(rows[0]).getByRole("link")).toHaveTextContent("lambda-prod 0.59.1");
    expect(within(rows[0]).getByRole("link")).toHaveAttribute("href", "/projects/p1/apps/a1/deployments");
    expect(within(rows[0]).getByText("prod")).toBeInTheDocument();
    expect(within(rows[0]).getByText("running")).toHaveClass("text-status-run");
    expect(within(rows[0]).getByText("2m 14s")).toBeInTheDocument();
    expect(within(rows[1]).getByText("queued")).toBeInTheDocument();
    expect(within(rows[1]).getByText("48s")).toBeInTheDocument();
  });

  it("counts running when every deployment runs and shows a dash without a start", () => {
    view(data({ in_progress: [active("d1", { started_at: null, stage: null })] }));
    expect(screen.getByTestId("in-progress-count")).toHaveTextContent("1 running");
    expect(within(screen.getByTestId("in-progress-row")).getAllByText("—")).toHaveLength(2);
  });

  it("ticks the elapsed time and refreshes while a deployment is active", () => {
    view(data({ in_progress: [active("d1")] }));
    act(() => { vi.advanceTimersByTime(1000); });
    expect(screen.getByText("2m 15s")).toBeInTheDocument();
    act(() => { vi.advanceTimersByTime(REFRESH_MS); });
    expect(router.refresh).toHaveBeenCalled();
  });

  it("says so when nothing is in progress and does not poll", () => {
    view(data());
    expect(screen.getByText("No deployments in progress")).toBeInTheDocument();
    expect(screen.queryByTestId("in-progress-count")).not.toBeInTheDocument();
    act(() => { vi.advanceTimersByTime(REFRESH_MS * 2); });
    expect(router.refresh).not.toHaveBeenCalled();
  });

  it("drops a deployment once the backend no longer returns it", () => {
    const { rerender } = view(data({ in_progress: [active("d1"), active("d2")] }));
    rerender(<ScopeProvider><DashboardView key="o1" data={data({ in_progress: [active("d2")] })} orgId="o1" /></ScopeProvider>);
    expect(screen.getAllByTestId("in-progress-row")).toHaveLength(1);
  });

  it("turns rows into blocks below the container breakpoint and a table above it", () => {
    view(data({ in_progress: [active("d1")] }));
    const panel = screen.getByRole("region", { name: "Deployments in progress" });
    expect(panel).toHaveClass("@container");
    const header = screen.getByText("Current step").parentElement!;
    expect(header).toHaveClass("hidden", "@2xl:grid");
    const row = screen.getByTestId("in-progress-row");
    expect(row).toHaveClass("flex", "flex-col", "@2xl:grid");
    expect(row.querySelector(".\\@2xl\\:contents")).not.toBeNull();
  });
});

describe("lower panels", () => {
  it("keeps the latest activity to five rows, identical runs grouped, with aligned status and time", () => {
    const events = [...Array.from({ length: 6 }, () => event("pypi 0.31.0", "failure")), event("Package Docker", "success"), event("ci-github", "success", "a2"), event("templates", "success", "a3"), event("ci-scripts", "failure", "a4"), event("ci-gitlab", "success", "a5")];
    const { container } = view(data({ events }));
    expect(screen.getAllByText("pypi 0.31.0")).toHaveLength(1);
    expect(screen.getByText("×6")).toBeInTheDocument();
    expect(screen.queryByText("ci-gitlab")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View all activity/ })).toHaveAttribute("href", "/dashboard/activity");
    for (const cell of container.querySelectorAll('[data-column="status"]')) expect(cell).toHaveClass("sm:w-[88px]");
  });

  it("counts the day's failures in needs attention", () => {
    view(data({ deployments_today: { failure: 4 }, ci_today: { failure: 1 } }));
    const panel = screen.getByText("Needs attention").closest("section")!;
    expect(within(panel).getByText("Deployment failures").nextSibling).toHaveTextContent("4");
    expect(within(panel).getByText("CI failures").nextSibling).toHaveTextContent("1");
  });

  it("shows full CI coverage", () => {
    view(data({ apps: 20 }));
    expect(screen.getByText("20 of 20 apps")).toBeInTheDocument();
    expect(screen.getByText("All apps have CI configured")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "CI coverage" })).toHaveAttribute("aria-valuenow", "100");
  });

  it("shows partial CI coverage with the apps to connect", () => {
    const without_ci = Array.from({ length: 5 }, (_, i) => ({ app_id: `w${i}`, app: `app-${i}`, project_id: "p1", project: "platform" }));
    view(data({ apps: 10, without_ci }));
    expect(screen.getByText("5 of 10 apps")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "CI coverage" })).toHaveAttribute("aria-valuenow", "50");
    expect(screen.getByRole("link", { name: "app-0" })).toHaveAttribute("href", "/projects/p1/apps/w0/ci/connect");
    expect(screen.getByText("+2 more")).toBeInTheDocument();
  });

  it("has an empty CI coverage state without apps", () => {
    view(data({ apps: 0 }));
    expect(screen.getByText("No apps yet")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("stacks the lower panels until the wide breakpoint and wraps metrics in two columns on medium screens", () => {
    view(data());
    expect(screen.getByTestId("metrics")).toHaveClass("grid-cols-1", "sm:grid-cols-2", "xl:grid-cols-4");
    expect(screen.getByTestId("lower")).toHaveClass("grid-cols-1", "xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]");
  });
});

describe("workspace switch", () => {
  function Switch({ to }: { to: string }) {
    const { setSwitchingTo } = useScope();
    useEffect(() => { setSwitchingTo(to); }, [to, setSwitchingTo]);
    return null;
  }

  it("hides the previous workspace's data while switching and shows the new one after", () => {
    const old = data({ apps: 3, in_progress: [active("old", { target: "old-target" })] });
    const { rerender } = render(<ScopeProvider><Switch to="o2" /><DashboardView key="o1" data={old} orgId="o1" /></ScopeProvider>);
    expect(screen.getByTestId("dashboard-skeleton")).toBeInTheDocument();
    expect(screen.queryByText("old-target")).not.toBeInTheDocument();

    rerender(<ScopeProvider><Switch to="o2" /><DashboardView key="o2" data={data({ apps: 7 })} orgId="o2" /></ScopeProvider>);
    expect(screen.queryByTestId("dashboard-skeleton")).not.toBeInTheDocument();
    expect(within(screen.getByTestId("metrics")).getByText("7")).toBeInTheDocument();
    expect(screen.queryByText("old-target")).not.toBeInTheDocument();
  });
});

describe("DashboardError", () => {
  it("explains the failure and retries", () => {
    vi.useRealTimers();
    render(<DashboardError reason="The platform took too long to answer. Try again in a moment." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Couldn’t load the dashboard");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });
});

describe("grouped", () => {
  it("folds consecutive identical events only", () => {
    const g = grouped([event("x", "failure"), event("x", "failure"), event("y", "success"), event("x", "failure")]);
    expect(g.map((e) => [e.event.title, e.count])).toEqual([["x", 2], ["y", 1], ["x", 1]]);
  });
});
