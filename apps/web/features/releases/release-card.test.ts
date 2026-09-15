import { describe, expect, it } from "vitest";
import { bump, withNotes } from "./release-card";

describe("bump", () => {
  it("follows SemVer", () => {
    expect(bump("0.3.2", "patch")).toBe("0.3.3");
    expect(bump("0.3.2", "minor")).toBe("0.4.0");
    expect(bump("0.3.2", "major")).toBe("1.0.0");
    expect(bump("1.2.3-rc.1", "patch")).toBe("1.2.4");
  });
});

describe("withNotes", () => {
  it("puts the notes under the heading, above the generated list", () => {
    expect(withNotes("## v0.1.1 — 2026-09-15\n\n### Fixes\n\n- x", "Notes.")).toBe("## v0.1.1 — 2026-09-15\n\nNotes.\n\n### Fixes\n\n- x");
  });

  it("leaves the entry alone without notes", () => {
    expect(withNotes("## v1", "  ")).toBe("## v1");
  });
});
