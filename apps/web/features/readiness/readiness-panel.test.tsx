import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ReadinessRow } from "@/lib/releases";

const actions = vi.hoisted(() => ({ checkReadiness: vi.fn(), readiness: vi.fn() }));

vi.mock("./actions", () => actions);

import { ReadinessPanel } from "./readiness-panel";

const blocked: ReadinessRow = {
  stage: "prod",
  status: "done",
  verdict: "blocked",
  checks: [
    { id: "manifest", ok: true, detail: "manifest is valid", level: "config", severity: "error" },
    { id: "credentials", ok: false, detail: "no token for prod", level: "access", severity: "error", fix: "Add a deploy token", target: "aws" },
    { id: "version", ok: false, detail: "older than live", level: "state", severity: "warning" },
  ],
};

const pending: ReadinessRow = { stage: "dev", status: "queued", verdict: "pending", checks: [] };

function panel(initial: ReadinessRow[], canCheck = true) {
  return render(<ReadinessPanel projectId="p1" appId="a1" tag="v1.0.0" initial={initial} canCheck={canCheck} />);
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("ReadinessPanel", () => {
  it("says nothing was checked and offers the re-check", () => {
    panel([]);
    expect(screen.getByText(/Not checked yet/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Re-check/ })).toBeEnabled();
  });

  it("hides the re-check from someone who cannot run it", () => {
    panel([], false);
    expect(screen.queryByRole("button", { name: /Re-check/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/Re-check runs/)).not.toBeInTheDocument();
  });

  it("shows the verdict of a stage and lists failures before passes", () => {
    panel([blocked]);
    expect(screen.getByText("Blocked")).toBeInTheDocument();
    const ids = screen.getAllByRole("listitem").map((li) => within(li).getByText(/^(manifest|credentials|version)$/).textContent);
    expect(ids).toEqual(["credentials", "version", "manifest"]);
  });

  it("explains how to fix a failed check but not a passing one", () => {
    panel([blocked]);
    expect(screen.getByText("Add a deploy token")).toBeInTheDocument();
    expect(screen.getAllByText("Fix:")).toHaveLength(1);
  });

  it("marks failures by severity", () => {
    panel([blocked]);
    expect(screen.getByLabelText("failed")).toBeInTheDocument();
    expect(screen.getByLabelText("warning")).toBeInTheDocument();
    expect(screen.getByLabelText("ok")).toBeInTheDocument();
  });

  it("tells that the worker is running while a stage is pending and disables the re-check", () => {
    panel([pending]);
    expect(screen.getByText("Checking…")).toBeInTheDocument();
    expect(screen.getByText("The worker is running the checks.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Re-check/ })).toBeDisabled();
  });

  it("re-checks and shows the new rows", async () => {
    actions.checkReadiness.mockResolvedValue({ ok: true, data: { jobs: ["j"], readiness: [{ stage: "dev", status: "done", verdict: "ok", checks: [] }] } });
    panel([blocked]);
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: /Re-check/ })); });
    expect(actions.checkReadiness).toHaveBeenCalledWith("p1", "a1", "v1.0.0");
    expect(screen.getByText("Deployable")).toBeInTheDocument();
    expect(screen.queryByText("Blocked")).not.toBeInTheDocument();
  });

  it("shows why a re-check failed and keeps the rows", async () => {
    actions.checkReadiness.mockResolvedValue({ ok: false, error: "no worker" });
    panel([blocked]);
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: /Re-check/ })); });
    expect(screen.getByText("no worker")).toBeInTheDocument();
    expect(screen.getByText("Blocked")).toBeInTheDocument();
  });

  it("polls while pending and stops once the stage settles", async () => {
    vi.useFakeTimers();
    actions.readiness.mockResolvedValue({ ok: true, data: [{ stage: "dev", status: "done", verdict: "ok", checks: [] }] });
    panel([pending]);
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(actions.readiness).toHaveBeenCalledWith("p1", "a1", "v1.0.0");
    expect(screen.getByText("Deployable")).toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(9000); });
    expect(actions.readiness).toHaveBeenCalledTimes(1);
  });
});
