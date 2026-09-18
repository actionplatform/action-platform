import { describe, expect, it } from "vitest";
import { PER_PAGE } from "./pagination";

describe("pagination", () => {
  it("offers the sizes people expect", () => {
    expect([...PER_PAGE]).toEqual([10, 25, 50, 100]);
  });
});
