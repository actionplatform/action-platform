import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DeploymentControls } from "./deployment-controls";
import { type DeploymentStep, controlsFor, currentWeight } from "./strategies";
import { StepTimeline } from "./step-timeline";
import { TrafficBar } from "./traffic-bar";

afterEach(cleanup);

const step = (index: number, kind: string, status: string, extra: Partial<DeploymentStep> = {}): DeploymentStep => ({ index, kind, status, ...extra });

const steps: DeploymentStep[] = [
  step(0, "deploy_new", "succeeded", { started_at: "2026-11-28T10:00:00Z", finished_at: "2026-11-28T10:00:20Z", params: { weight: 0 } }),
  step(1, "shift", "succeeded", { params: { weight: 5 }, detail: "5% routed" }),
  step(2, "pause", "running", { params: { seconds: 300 } }),
  step(3, "shift", "pending", { params: { weight: 25 } }),
  step(4, "health", "failed", { detail: "p95 above budget" }),
];

describe("StepTimeline", () => {
  it("renders every step with its label and weight", () => {
    render(<StepTimeline steps={steps} />);
    const items = within(screen.getByRole("list", { name: "Deployment steps" })).getAllByRole("listitem");
    expect(items).toHaveLength(5);
    expect(items.map((i) => i.getAttribute("data-status"))).toEqual(["succeeded", "succeeded", "running", "pending", "failed"]);
    expect(screen.getByText("Deploy new version")).toBeInTheDocument();
    expect(screen.getByText("5%")).toBeInTheDocument();
    expect(screen.getByText("25%")).toBeInTheDocument();
    expect(screen.getByText("20s")).toBeInTheDocument();
    expect(screen.getByText("5m")).toBeInTheDocument();
  });

  it("expands a row to show the result detail", () => {
    render(<StepTimeline steps={steps} />);
    expect(screen.queryByText("p95 above budget")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Health check/ }));
    expect(screen.getByText("p95 above budget")).toBeInTheDocument();
  });

  it("says so when nothing ran yet", () => {
    render(<StepTimeline steps={[]} />);
    expect(screen.getByText("No steps recorded yet.")).toBeInTheDocument();
  });
});

describe("TrafficBar", () => {
  it("shows the share of the new version", () => {
    render(<TrafficBar weight={25} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "25");
    expect(screen.getByText(/New version 25% · Current 75%/)).toBeInTheDocument();
  });

  it("follows the steps already shifted", () => {
    expect(currentWeight(steps)).toBe(5);
    expect(currentWeight([step(0, "deploy_new", "succeeded")])).toBe(0);
    expect(currentWeight([step(0, "shift", "succeeded", { params: { weight: 100 } })])).toBe(100);
  });
});

describe("controls per state", () => {
  it("offers only what is valid for the state", () => {
    expect(controlsFor("running", true)).toEqual(["pause", "abort"]);
    expect(controlsFor("paused", true)).toEqual(["resume", "promote", "abort"]);
    expect(controlsFor("awaiting_approval", true)).toEqual(["promote", "abort"]);
    for (const s of ["queued", "done", "failed", "rolling_back", "rolled_back", "aborted"]) expect(controlsFor(s, true)).toEqual([]);
  });

  it("offers nothing without the deploy permission", () => {
    expect(controlsFor("running", false)).toEqual([]);
    const { container } = render(<DeploymentControls state="paused" canDeploy={false} onAct={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the buttons of a paused deployment and acts", () => {
    const act = vi.fn();
    render(<DeploymentControls state="paused" canDeploy onAct={act} />);
    expect(screen.getAllByRole("button").map((b) => b.textContent?.trim())).toEqual(["Resume", "Promote", "Abort"]);
    fireEvent.click(screen.getByRole("button", { name: "Promote" }));
    expect(act).toHaveBeenCalledWith("promote");
  });

  it("confirms before aborting", () => {
    const act = vi.fn();
    render(<DeploymentControls state="running" canDeploy onAct={act} />);
    fireEvent.click(screen.getByRole("button", { name: "Abort" }));
    expect(act).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Abort deployment" }));
    expect(act).toHaveBeenCalledWith("abort");
  });
});
