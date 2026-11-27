import type { CiStage } from "@/lib/ci-kinds";

export type StageColumn = { stage: CiStage; branches: { stage: CiStage; depth: number }[] };

export function stageColumns(stages: CiStage[]): StageColumn[] {
  const ids = new Set(stages.map((s) => s.id));
  const children = new Map<string, CiStage[]>();
  for (const s of stages) {
    if (s.parentId && ids.has(s.parentId)) children.set(s.parentId, [...(children.get(s.parentId) ?? []), s]);
  }
  const below = (id: string, depth: number, seen: Set<string>): { stage: CiStage; depth: number }[] =>
    (children.get(id) ?? []).flatMap((c) => (seen.has(c.id) ? [] : (seen.add(c.id), [{ stage: c, depth }, ...below(c.id, depth + 1, seen)])));
  return stages
    .filter((s) => !s.parentId || !ids.has(s.parentId))
    .map((s) => ({ stage: s, branches: below(s.id, 1, new Set([s.id])) }));
}
