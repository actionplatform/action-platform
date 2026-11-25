import { describe, expect, it } from "vitest";
import { eventKind } from "@/lib/insights";
import { eventHref } from "./event-row";

describe("eventHref", () => {
  it("opens the tab where each kind of event lives", () => {
    const at = (kind: string) => eventHref({ kind, project_id: "p1", app_id: "a1" });
    expect(at("release")).toBe("/projects/p1/apps/a1/releases");
    expect(at("deployment")).toBe("/projects/p1/apps/a1/deployments");
    expect(at("ci_run")).toBe("/projects/p1/apps/a1/activity?kind=ci_run");
    expect(at("pull_request")).toBe("/projects/p1/apps/a1/activity?kind=pull_request");
  });
});

describe("eventKind", () => {
  it("accepts only the kinds the API filters on", () => {
    expect(eventKind("release")).toBe("release");
    expect(eventKind(["ci_run", "release"])).toBe("ci_run");
    expect(eventKind("audit")).toBeNull();
    expect(eventKind(undefined)).toBeNull();
  });
});
