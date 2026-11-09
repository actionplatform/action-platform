import { describe, expect, it } from "vitest";
import { googleStartPath, loginWithError } from "./google-sign-in-path";

describe("googleStartPath", () => {
  it("carries where to land after Google", () => {
    expect(googleStartPath("/invite/inv 1")).toBe("/api/sign-in/google/start?next=%2Finvite%2Finv+1");
  });
});

describe("loginWithError", () => {
  it("sends the reason to the login page", () => {
    const url = new URL(loginWithError("no account for eve@example.com: an owner has to invite you"), "http://local");
    expect(url.pathname).toBe("/login");
    expect(url.searchParams.get("error")).toBe("no account for eve@example.com: an owner has to invite you");
  });
});
