"use server";

import { clearSessionCookie, requestClient, sessionCookie, setSessionCookie } from "./auth";
import { authApi, isAuthError } from "./auth-api";
import { failed, type Result } from "./result";

export async function signIn(email: string, password: string): Promise<Result> {
  try {
    const { ip, userAgent } = await requestClient();
    const signed = await authApi.signIn({ email, password, ip_address: ip, user_agent: userAgent }, ip);
    await setSessionCookie(signed.session.cookie, signed.session.expires_at);
    return { ok: true, data: null };
  } catch (e) {
    if (isAuthError(e, 401)) return { ok: false, error: "email or password is wrong" };
    if (isAuthError(e, 429)) return { ok: false, error: "too many attempts, wait a minute" };
    return failed(e);
  }
}

export async function signUp(name: string, email: string, password: string, invitationId: string | null = null): Promise<Result> {
  try {
    const { ip } = await requestClient();
    const signed = await authApi.signUp({ name, email, password, invitation_id: invitationId }, ip);
    await setSessionCookie(signed.session.cookie, signed.session.expires_at);
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function requestPasswordReset(email: string): Promise<Result> {
  try {
    const { ip } = await requestClient();
    await authApi.forgotPassword(email, ip);
    return { ok: true, data: null };
  } catch (e) {
    if (isAuthError(e, 429)) return { ok: false, error: "too many attempts, wait a minute" };
    if (isAuthError(e, 503)) return { ok: false, error: "password recovery is not available on this platform" };
    return failed(e);
  }
}

export async function resetPassword(token: string, password: string): Promise<Result> {
  try {
    const { ip } = await requestClient();
    await authApi.resetPassword({ token, password }, ip);
    return { ok: true, data: null };
  } catch (e) {
    if (isAuthError(e, 429)) return { ok: false, error: "too many attempts, wait a minute" };
    return failed(e);
  }
}

export async function signOut(): Promise<Result> {
  try {
    const cookie = await sessionCookie();
    if (cookie) {
      try {
        await authApi.signOut({ cookie });
      } catch (e) {
        if (!isAuthError(e, 401)) throw e;
      }
    }
    await clearSessionCookie();
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}
