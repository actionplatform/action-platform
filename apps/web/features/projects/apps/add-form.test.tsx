import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AddForm } from "./add-form";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
const addApp = vi.fn();
vi.mock("@/features/projects/actions", () => ({ addApp: (...args: unknown[]) => addApp(...args) }));

const types = [{ id: "web", label: "Web", description: "" }];

async function installThrough() {
  render(<AddForm projectId="p1" types={types} stacks={[]} />);
  fireEvent.change(screen.getByPlaceholderText("https://github.com/org/repo.git"), { target: { value: "https://github.com/acme/svc.git" } });
  fireEvent.click(screen.getByRole("button", { name: /Add/ }));
  const install = await screen.findByRole("button", { name: /Install and add/ });
  fireEvent.click(install);
}

describe("AddForm", () => {
  afterEach(() => { cleanup(); push.mockReset(); addApp.mockReset(); });

  it("installs with the CI detected from the repository and shows what it found before committing", async () => {
    addApp
      .mockResolvedValueOnce({ ok: false, error: "platform.toml not found", needsInstall: true })
      .mockResolvedValueOnce({ ok: true, appId: "a1", installed: ["platform.toml"], report: { ci: "jenkins", detected_ci: ["jenkins", "github"], warnings: [".github/workflows found; installing jenkins CI files runs a second CI next to it"], ci_snippet: "stage('Check') {}" } });

    await installThrough();

    await waitFor(() => expect(screen.getByText("Platform installed — review before committing")).toBeInTheDocument());
    expect(addApp).toHaveBeenLastCalledWith("p1", "https://github.com/acme/svc.git", { type: "web", ci: null, language: null });
    expect(screen.getByText("Jenkinsfile, .github/workflows")).toBeInTheDocument();
    expect(screen.getByText(/runs a second CI next to it/)).toBeInTheDocument();
    expect(screen.getByText("stage('Check') {}")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /Open configuration/ }));
    expect(push).toHaveBeenCalledWith("/projects/p1/apps/a1/settings/configuration");
  });

  it("goes straight to configuration when nothing was found", async () => {
    addApp
      .mockResolvedValueOnce({ ok: false, error: "platform.toml not found", needsInstall: true })
      .mockResolvedValueOnce({ ok: true, appId: "a1", installed: ["platform.toml"], report: { ci: "github", detected_ci: [], warnings: [], ci_snippet: "" } });

    await installThrough();

    await waitFor(() => expect(push).toHaveBeenCalledWith("/projects/p1/apps/a1/settings/configuration"));
  });

  it("a refusal shows inside the install dialog", async () => {
    addApp
      .mockResolvedValueOnce({ ok: false, error: "platform.toml not found", needsInstall: true })
      .mockResolvedValueOnce({ ok: false, error: "the repository already runs more than one CI (Jenkinsfile, .github/workflows)" });

    await installThrough();

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("more than one CI"));
  });
});
