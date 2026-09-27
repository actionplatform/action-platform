import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { Dashboard, DashboardEvent } from "@/lib/insights";
import { DashboardView, grouped } from "./dashboard";

const event = (title: string, status: string, app = "a1"): DashboardEvent => ({ app_id: app, app, project_id: "p1", project: "platform", kind: "ci_run", title, status, at: null });

const data = (over: Partial<Dashboard> = {}): Dashboard => ({
  apps: 10,
  deployments_today: {},
  ci_today: {},
  releases_week: 1,
  without_ci: Array.from({ length: 9 }, (_, i) => ({ app_id: `w${i}`, app: `app-${i}`, project_id: "p1", project: "platform" })),
  events: [],
  ...over,
});

describe("DashboardView", () => {
  afterEach(cleanup);

  it("shows four metrics", () => {
    render(<DashboardView data={data()} />);
    for (const label of ["Apps", "Deployments today", "CI runs today", "Releases this week"]) expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.getByText("0 verified")).toBeInTheDocument();
  });

  it("lists five apps without CI and counts the rest from the data", () => {
    render(<DashboardView data={data()} />);
    expect(screen.getByText("9")).toBeInTheDocument();
    expect(screen.getByText("app-4")).toBeInTheDocument();
    expect(screen.queryByText("app-5")).not.toBeInTheDocument();
    expect(screen.getByText("+4 more apps")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View all apps/ })).toHaveAttribute("href", "/projects");
  });

  it("keeps the latest activity to five rows, identical runs grouped", () => {
    const events = [...Array.from({ length: 6 }, () => event("pypi 0.31.0", "failure")), event("Package Docker", "success"), event("ci-github", "success", "a2"), event("templates", "success", "a3"), event("ci-scripts", "failure", "a4"), event("ci-gitlab", "success", "a5")];
    render(<DashboardView data={data({ events })} />);
    expect(screen.getAllByText("pypi 0.31.0")).toHaveLength(1);
    expect(screen.getByText("×6")).toBeInTheDocument();
    expect(screen.queryByText("ci-gitlab")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View all activity/ })).toHaveAttribute("href", "/dashboard/activity");
  });
});

describe("grouped", () => {
  it("folds consecutive identical events only", () => {
    const g = grouped([event("x", "failure"), event("x", "failure"), event("y", "success"), event("x", "failure")]);
    expect(g.map((e) => [e.event.title, e.count])).toEqual([["x", 2], ["y", 1], ["x", 1]]);
  });
});
