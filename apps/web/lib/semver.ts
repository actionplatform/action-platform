export type Increment = "patch" | "minor" | "major";

export function bump(version: string | null, level: Increment): string {
  const base = (version ?? "0.0.0").split("-")[0];
  const [ma = 0, mi = 0, pa = 0] = base.split(".").map((n) => Number.parseInt(n, 10) || 0);
  if (level === "major") return `${ma + 1}.0.0`;
  if (level === "minor") return `${ma}.${mi + 1}.0`;
  return `${ma}.${mi}.${pa + 1}`;
}
