import { describe, expect, it } from "vitest";
import { pageQuery, paginate } from "./page";

describe("pageQuery", () => {
  it("reads page and per from the URL with sane bounds", () => {
    expect(pageQuery({})).toEqual({ page: 1, per: 10 });
    expect(pageQuery({ page: "3", per: "25" })).toEqual({ page: 3, per: 25 });
    expect(pageQuery({ page: "0", per: "1000" })).toEqual({ page: 1, per: 100 });
    expect(pageQuery({ runs_page: ["2"] }, "runs")).toEqual({ page: 2, per: 10 });
  });
});

describe("paginate", () => {
  it("cuts one page out of a list and keeps the total", () => {
    const items = [1, 2, 3, 4, 5];
    expect(paginate(items, { page: 2, per: 2 })).toEqual({ items: [3, 4], total: 5, page: 2, per: 2 });
    expect(paginate(items, { page: 3, per: 2 }).items).toEqual([5]);
    expect(paginate(items, { page: 9, per: 2 }).items).toEqual([]);
  });
});
