import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Protection } from "@/lib/protection";
import { enforceOf, settingOf, summaryOf } from "./model";
import { ProtectionPanel } from "./protection-panel";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

const setProtection = vi.fn();
vi.mock("./actions", () => ({
  setProtection: (...args: unknown[]) => setProtection(...args),
  applyProtection: vi.fn(),
  checkProtection: vi.fn(),
}));

function protection(over: Partial<Protection> = {}): Protection {
  return {
    enforce: true,
    source: "app",
    organization_default: false,
    branches: [],
    checked_at: "2026-11-25T10:00:00",
    applied_at: "2026-11-25T10:00:00",
    job_id: null,
    state: {
      host: "github",
      active: true,
      branches: ["main", "develop"],
      checks: ["gitflow", "conventional-commit"],
      bypass: "GitHub App action-platform",
      drift: [],
      error: null,
      changed_by: null,
      rules: [
        { rule: "direct_push", label: "Direct push blocked", mode: "native", detail: "changes reach the branch only through a pull request" },
        { rule: "branch_names", label: "Branch names", mode: "check", detail: "the required `gitflow` check refuses the pull request" },
        { rule: "commit_messages", label: "Conventional Commits", mode: "inactive", detail: "no check" },
      ],
    },
    ...over,
  } as Protection;
}

describe("protection model", () => {
  it("maps the setting both ways", () => {
    expect(settingOf({ enforce: true, source: "organization" })).toBe("default");
    expect(settingOf({ enforce: false, source: "app" })).toBe("off");
    expect(enforceOf("default")).toBeNull();
    expect(enforceOf("on")).toBe(true);
  });

  it("never claims protection the host did not accept", () => {
    expect(summaryOf(protection({ state: { ...protection().state!, error: "GitHub refused rulesets", active: false } })).label).toBe("Not active");
    expect(summaryOf(protection({ state: null })).label).toBe("Pending");
    expect(summaryOf(protection({ state: { ...protection().state!, error: "no GitHub App key" } })).label).toBe("Not kept");
    expect(summaryOf(protection({ enforce: false })).label).toBe("Not enforced");
    expect(summaryOf(protection()).label).toBe("Partly active");
  });
});

describe("ProtectionPanel", () => {
  afterEach(() => { cleanup(); setProtection.mockReset(); });

  it("shows each rule's state in words, not colour alone", () => {
    render(<ProtectionPanel projectId="p" appId="a" initial={protection()} canEdit />);
    expect(screen.getByText("Enforced by the host")).toBeInTheDocument();
    expect(screen.getByText("Required check")).toBeInTheDocument();
    expect(screen.getByText("Not active")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "On" })).toHaveAttribute("aria-checked", "true");
  });

  it("says in place what the switch did", async () => {
    setProtection.mockResolvedValue({ ok: true, data: protection({ enforce: false, source: "app", state: null }) });
    render(<ProtectionPanel projectId="p" appId="a" initial={protection()} canEdit />);
    fireEvent.click(screen.getByRole("radio", { name: "Off" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("no longer enforced"));
    expect(setProtection).toHaveBeenCalledWith("p", "a", false);
    expect(screen.getByRole("radio", { name: "Off" })).toHaveAttribute("aria-checked", "true");
  });

  it("hides the switch and Apply from someone who cannot configure", () => {
    render(<ProtectionPanel projectId="p" appId="a" initial={protection()} canEdit={false} />);
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apply now" })).not.toBeInTheDocument();
  });
});
