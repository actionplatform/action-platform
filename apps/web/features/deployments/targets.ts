type TargetSpec = { name?: string; kind?: string; stages?: string[] };

export function targetsOf(deploy: Record<string, unknown>, stage: string | null = null): string | null {
  const names: string[] = [];
  if (typeof deploy.target === "string") names.push(deploy.target);
  for (const t of Array.isArray(deploy.targets) ? (deploy.targets as TargetSpec[]) : []) {
    const name = t.name ?? t.kind;
    if (name && (stage === null || !t.stages?.length || t.stages.includes(stage))) names.push(name);
  }
  return names.length ? names.join(", ") : null;
}
