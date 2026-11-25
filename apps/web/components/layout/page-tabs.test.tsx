import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { PageTabs, pickTab } from "./page-tabs";

const tabs = [{ id: "general", label: "General" }, { id: "ci", label: "CI" }];

describe("PageTabs", () => {
  afterEach(cleanup);

  it("links each tab by ?tab= and marks the active one", () => {
    render(<PageTabs label="Settings" tabs={tabs} active="ci" />);
    expect(screen.getByRole("tab", { name: "General" })).toHaveAttribute("href", "?tab=general");
    expect(screen.getByRole("tab", { name: "CI" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "General" })).toHaveAttribute("aria-selected", "false");
  });

  it("falls back to the first tab for a missing or unknown id", () => {
    expect(pickTab(tabs, undefined)).toBe("general");
    expect(pickTab(tabs, "nope")).toBe("general");
    expect(pickTab(tabs, ["ci"])).toBe("ci");
  });
});
