import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdoptionView } from "./adoption-view";
import { type AdoptionRow, stateLabel, toOpen } from "./model";

const startInstall = vi.fn(async () => ({ ok: true as const, data: { job: "j1" } }));
vi.mock("./actions", () => ({
  startInstall: (...args: unknown[]) => startInstall(...(args as [])),
  installJob: vi.fn(async () => ({ ok: true as const, data: { status: "queued", result: null, error: null } })),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

const row = (name: string, state: string, extra: Partial<AdoptionRow> = {}): AdoptionRow => ({ app_id: `a-${name}`, name, registry_id: `r-${name}`, state, ...extra });

const rows = [
  row("shop", "missing", { language: "python", ci: "github", version: "1.4.0" }),
  row("site", "pr_open", { pull_request: { number: 7, url: "https://code.example/pr/7" } }),
  row("docs", "failed", { reason: "unknown language: pick one" }),
  row("done", "installed"),
  row("new", "unchecked"),
];

describe("stateLabel", () => {
  it("names every state the way the issue asks", () => {
    expect(stateLabel(rows[0]).label).toBe("no platform.toml");
    expect(stateLabel(rows[1]).label).toBe("install PR #7 open");
    expect(stateLabel(rows[2]).label).toBe("failed: unknown language: pick one");
    expect(stateLabel(rows[3]).label).toBe("installed");
    expect(stateLabel(rows[4]).label).toBe("not checked");
  });
});

describe("toOpen", () => {
  it("keeps the apps whose dry run planned an install", () => {
    const plan = { type: "web", language: "python", ci: "github", detected_ci: [], created: ["platform.toml"], kept: [], warnings: [], version: "0.0.0", version_source: "default", base: "main", branch: "chore/platform" };
    const run = {
      dry_run: true,
      branch: "chore/platform",
      opened: 0,
      skipped: 1,
      failed: 1,
      apps: [
        { app_id: "a", name: "a", state: "missing", skipped: false, reason: null, pull_request: null, plan },
        { app_id: "b", name: "b", state: "installed", skipped: true, reason: null, pull_request: null, plan: null },
        { app_id: "c", name: "c", state: "failed", skipped: false, reason: "archived: the repository is read-only", pull_request: null, plan: null },
      ],
    };
    expect(toOpen(run).map((a) => a.app_id)).toEqual(["a"]);
    expect(toOpen(null)).toEqual([]);
  });
});

describe("AdoptionView", () => {
  afterEach(() => {
    cleanup();
    startInstall.mockClear();
  });

  it("shows each app's state and links its open pull request", () => {
    render(<AdoptionView projectId="p1" rows={rows} canManage options={{ types: [{ id: "web", label: "Web" }] }} />);
    expect(screen.getByText("install PR #7 open")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open pull request/i })).toHaveAttribute("href", "https://code.example/pr/7");
    expect(screen.getByText("language python · CI github · version 1.4.0")).toBeInTheDocument();
  });

  it("previews the apps that are not on the platform yet", async () => {
    render(<AdoptionView projectId="p1" rows={rows} canManage options={{ types: [{ id: "web", label: "Web" }] }} />);
    fireEvent.click(screen.getByRole("button", { name: /install selected/i }));
    await waitFor(() => expect(startInstall).toHaveBeenCalled());
    expect(startInstall).toHaveBeenCalledWith("p1", { apps: ["a-shop", "a-docs", "a-new"], type: "web", ci: null, language: null, code: "platform", dry_run: true });
  });

  it("asks for a role that manages projects before installing", () => {
    render(<AdoptionView projectId="p1" rows={rows} canManage={false} options={{ types: [] }} />);
    expect(screen.queryByRole("button", { name: /install selected/i })).toBeNull();
    expect(screen.getByText(/needs a role that manages projects/)).toBeInTheDocument();
  });
});
