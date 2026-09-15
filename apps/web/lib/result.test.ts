import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { GENERIC, TIMED_OUT, failed } from "./result";

describe("failed", () => {
  it("passes the API's own message through for a refusal", () => {
    expect(failed(new ApiError(400, "tag v1.0.0 already exists"))).toEqual({ ok: false, error: "tag v1.0.0 already exists" });
  });

  it("hides the detail of an unexpected error", () => {
    expect(failed(new TypeError("ECONNRESET 10.0.0.3"))).toEqual({ ok: false, error: GENERIC });
    expect(failed(new ApiError(502, "upstream connect error"))).toEqual({ ok: false, error: GENERIC });
    expect(failed("boom")).toEqual({ ok: false, error: GENERIC });
  });

  it("says when the API timed out", () => {
    expect(failed(new DOMException("aborted", "TimeoutError"))).toEqual({ ok: false, error: TIMED_OUT });
  });
});
