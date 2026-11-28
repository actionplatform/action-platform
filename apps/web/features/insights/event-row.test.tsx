import { describe, expect, it } from "vitest";
import { eventKind } from "@/lib/insights";
import { eventHref } from "./event-row";

describe("eventHref", () => {
  it("opens the tab where each kind of event lives", () => {
    const at = (kind: string) => eventHref({ kind, project_id: "p1", app_id: "a1" });
    expect(at("release")).toBe("/projects/p1/apps/a1/releases");
    expect(at("deployment")).toBe("/projects/p1/apps/a1/deployments");
    expect(at("ci_run")).toBe("/projects/p1/apps/a1/pipelines");
    expect(at("pull_request")).toBe("/projects/p1/apps/a1");
    expect(at("protection")).toBe("/projects/p1/apps/a1/activity?kind=protection");
  });
});

describe("eventKind", () => {
  it("accepts only the kinds the API filters on", () => {
    expect(eventKind("release")).toBe("release");
    expect(eventKind(["deployment", "release"])).toBe("deployment");
    expect(eventKind("audit")).toBeNull();
    expect(eventKind(undefined)).toBeNull();
  });
});
