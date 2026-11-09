export const GOOGLE_PATH = "/api/sign-in/google";

export function googleStartPath(next: string): string {
  return `${GOOGLE_PATH}/start?${new URLSearchParams({ next })}`;
}

export function loginWithError(message: string): string {
  return `/login?${new URLSearchParams({ error: message })}`;
}
