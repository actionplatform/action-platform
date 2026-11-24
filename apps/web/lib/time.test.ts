import { describe, expect, it } from "vitest";
import { elapsed, relativeTime, utc } from "./time";

describe("relativeTime", () => {
  const now = Date.UTC(2026, 8, 15, 12, 0, 0);

  it("reads a naive timestamp as UTC", () => {
    expect(utc("2026-09-15T11:00:00").toISOString()).toBe("2026-09-15T11:00:00.000Z");
  });

  it("rounds to the unit a person would say", () => {
    expect(relativeTime("2026-09-15T11:59:50Z", now)).toBe("just now");
    expect(relativeTime("2026-09-15T11:38:00Z", now)).toBe("22 min ago");
    expect(relativeTime("2026-09-15T05:00:00Z", now)).toBe("7 hours ago");
    expect(relativeTime("2026-09-14T12:00:00Z", now)).toBe("yesterday");
    expect(relativeTime("2026-09-13T12:00:00Z", now)).toBe("2 days ago");
  });
});

describe("elapsed", () => {
  const now = Date.UTC(2026, 8, 15, 12, 0, 0);

  it("counts from the start in the largest two units", () => {
    expect(elapsed("2026-09-15T11:59:12", now)).toBe("48s");
    expect(elapsed("2026-09-15T11:57:46Z", now)).toBe("2m 14s");
    expect(elapsed("2026-09-15T10:55:00Z", now)).toBe("1h 5m");
    expect(elapsed("2026-09-13T10:00:00Z", now)).toBe("2d 2h");
  });

  it("shows a dash without a start and never goes negative", () => {
    expect(elapsed(null, now)).toBe("—");
    expect(elapsed(undefined, now)).toBe("—");
    expect(elapsed("2026-09-15T12:00:30Z", now)).toBe("0s");
  });
});
