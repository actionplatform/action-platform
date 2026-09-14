const CONTROL = /[\u0000-\u001f\u007f]/;

export function safePath(value: string | null | undefined, fallback: string): string {
  if (!value) return fallback;
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("\\") || CONTROL.test(value)) return fallback;
  try {
    const parsed = new URL(value, "http://local");
    if (parsed.origin !== "http://local") return fallback;
    return parsed.pathname + parsed.search + parsed.hash;
  } catch {
    return fallback;
  }
}
