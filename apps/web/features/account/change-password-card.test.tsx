import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChangePasswordCard } from "./change-password-card";

const changePassword = vi.fn();
vi.mock("./actions", () => ({ changePassword: (...args: unknown[]) => changePassword(...args) }));

function fill(current: string, next: string, confirm: string) {
  fireEvent.change(screen.getByLabelText("Current password"), { target: { value: current } });
  fireEvent.change(screen.getByLabelText(/^New password/), { target: { value: next } });
  fireEvent.change(screen.getByLabelText("Repeat the new password"), { target: { value: confirm } });
  fireEvent.submit(screen.getByRole("button", { name: "Change password" }).closest("form")!);
}

describe("ChangePasswordCard", () => {
  afterEach(() => {
    cleanup();
    changePassword.mockReset();
  });

  it("says it signs out the other sessions, the CLI and the MCP servers", () => {
    render(<ChangePasswordCard />);
    expect(screen.getByText(/every other browser session/)).toHaveTextContent(/CLI and the MCP servers/);
  });

  it("sends the current and the new password and confirms", async () => {
    changePassword.mockResolvedValue({ ok: true, data: null });
    render(<ChangePasswordCard />);
    fill("old-password1", "new-password1", "new-password1");
    await waitFor(() => expect(screen.getByRole("status")).toBeInTheDocument());
    expect(changePassword).toHaveBeenCalledWith("old-password1", "new-password1");
  });

  it("does not call the API when the new passwords differ", () => {
    render(<ChangePasswordCard />);
    fill("old-password1", "new-password1", "other-password1");
    expect(screen.getByRole("alert")).toHaveTextContent("the new passwords do not match");
    expect(changePassword).not.toHaveBeenCalled();
  });

  it("shows what the API refused", async () => {
    changePassword.mockResolvedValue({ ok: false, error: "the current password is wrong" });
    render(<ChangePasswordCard />);
    fill("nope", "new-password1", "new-password1");
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("the current password is wrong"));
    expect(screen.queryByRole("status")).toBeNull();
  });
});
