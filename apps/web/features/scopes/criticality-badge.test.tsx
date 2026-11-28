import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { CriticalityBadge } from "./criticality-badge";

afterEach(cleanup);

describe("CriticalityBadge", () => {
  it("labels a known criticality and explains it on hover", () => {
    render(<CriticalityBadge value="critical" />);
    const badge = screen.getByText("Critical");
    expect(badge).toHaveAttribute("title", expect.stringContaining("Essential to the business"));
  });

  it("shows an unknown criticality as it came", () => {
    render(<CriticalityBadge value="experimental" />);
    expect(screen.getByText("experimental")).toBeInTheDocument();
  });
});
