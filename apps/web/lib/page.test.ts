import { describe, expect, it } from "vitest";
import { pageQuery } from "./page";

describe("pageQuery", () => {
  it("reads page and per from the URL with sane bounds", () => {
    expect(pageQuery({})).toEqual({ page: 1, per: 10 });
    expect(pageQuery({ page: "3", per: "25" })).toEqual({ page: 3, per: 25 });
    expect(pageQuery({ page: "0", per: "1000" })).toEqual({ page: 1, per: 100 });
    expect(pageQuery({ runs_page: ["2"] }, "runs")).toEqual({ page: 2, per: 10 });
  });
});
