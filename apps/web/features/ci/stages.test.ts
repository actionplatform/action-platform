import { describe, expect, it } from "vitest";
import type { CiStage } from "@/lib/ci-kinds";
import { stageColumns } from "./stages";

const stage = (id: string, parentId: string | null = null): CiStage => ({ id, name: `s${id}`, status: "success", startedAt: null, durationMs: null, parentId });

describe("stageColumns", () => {
  it("puts parallel branches under the stage they run in", () => {
    const columns = stageColumns([stage("1"), stage("2"), stage("3", "2"), stage("4", "2"), stage("5", "4"), stage("6")]);
    expect(columns.map((c) => c.stage.id)).toEqual(["1", "2", "6"]);
    expect(columns[1].branches.map((b) => [b.stage.id, b.depth])).toEqual([["3", 1], ["4", 1], ["5", 2]]);
  });

  it("treats a stage whose parent is unknown as a column of its own", () => {
    expect(stageColumns([stage("1", "missing")]).map((c) => c.stage.id)).toEqual(["1"]);
  });
});
