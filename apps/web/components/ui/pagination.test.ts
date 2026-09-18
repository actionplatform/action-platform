import { describe, expect, it } from "vitest";
import { PER_PAGE, TABLE } from "./data-table";

describe("data table", () => {
  it("offers the sizes people expect and ten rows by default", () => {
    expect([...PER_PAGE]).toEqual([10, 25, 50, 100]);
    expect(TABLE.rows).toBe(10);
    expect(TABLE.toolbar + TABLE.header + TABLE.row * TABLE.rows + TABLE.footer).toBe(672);
  });
});
