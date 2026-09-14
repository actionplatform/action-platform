"use client";

export function lostConnection(e: unknown): boolean {
  return e instanceof TypeError && /fetch|network|load failed/i.test(e.message);
}

export async function call<T>(action: () => Promise<T>, fallback: (error: string) => T, whileAway = "The request may still have completed."): Promise<T> {
  try {
    return await action();
  } catch (e) {
    if (lostConnection(e)) return fallback(`Connection lost before the answer arrived. ${whileAway}`);
    throw e;
  }
}
