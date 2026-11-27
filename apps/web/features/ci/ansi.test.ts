import { describe, expect, it } from "vitest";
import { applySgr, parseLog, stripAnsi } from "./ansi";

describe("parseLog", () => {
  it("turns SGR codes into styled segments and keeps the plain text", () => {
    const [line] = parseLog("\x1b[1;31mfailed\x1b[0m at step\n");
    expect(line.text).toBe("failed at step");
    expect(line.segments).toEqual([{ text: "failed", bold: true, fg: "#dc2626" }, { text: " at step" }]);
  });

  it("carries a colour across lines until it is reset", () => {
    const lines = parseLog("\x1b[32mone\ntwo\x1b[0m\nthree\n");
    expect(lines.map((l) => l.segments[0].fg)).toEqual(["#16a34a", "#16a34a", undefined]);
    expect(lines.map((l) => l.number)).toEqual([1, 2, 3]);
  });

  it("drops hidden console notes and other escapes", () => {
    const [line] = parseLog("\x1b[8mha:////4Lnote\x1b[0m[Pipeline] sh\x1b[2K\n");
    expect(line.text).toBe("[Pipeline] sh");
  });

  it("splits a leading timestamp off the line", () => {
    const [line] = parseLog("[2026-11-27T03:10:00.123Z] \x1b[33mbuild\x1b[0m\n");
    expect(line.time).toBe("2026-11-27T03:10:00.123Z");
    expect(line.text).toBe("build");
    expect(line.segments[0]).toEqual({ text: "build", fg: "#ca8a04" });
  });

  it("keeps what a carriage return left on screen", () => {
    expect(parseLog("10%\r50%\r100%\n")[0].text).toBe("100%");
  });
});

describe("applySgr", () => {
  it("reads 256-colour and true-colour codes", () => {
    expect(applySgr({}, "38;5;196").fg).toBe("rgb(255,0,0)");
    expect(applySgr({}, "48;2;1;2;3").bg).toBe("rgb(1,2,3)");
    expect(applySgr({ bold: true, fg: "x" }, "")).toEqual({});
  });
});

describe("stripAnsi", () => {
  it("leaves plain text", () => {
    expect(stripAnsi("\x1b[31mred\x1b[0m")).toBe("red");
  });
});
