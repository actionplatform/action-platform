import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }) }));
vi.mock("@/lib/auth-actions", () => ({ signIn: vi.fn(), signOut: vi.fn() }));
vi.mock("./actions", () => ({ acceptInvite: vi.fn(), joinWithNewAccount: vi.fn() }));
vi.mock("@/components/google-button", () => ({ GoogleButton: ({ label }: { label: string }) => <button type="button">{label}</button> }));

import { InviteForm } from "./invite-form";

const byLogin = { id: "inv1", email: null, login: "ghost", host: "github", role: "developer", org: "Acme", inviter: "Ana" };
const byEmail = { ...byLogin, email: "bob@example.com", login: null, host: null };

describe("InviteForm", () => {
  afterEach(cleanup);

  it("sends a signed-in person to verify the invited login", () => {
    render(<InviteForm invitation={byLogin} mode="verify" currentEmail="ghost@elsewhere.dev" />);
    expect(screen.getByText("@ghost on GitHub")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute("href", "/api/invitations/inv1/verify");
    expect(screen.getByRole("button", { name: "Verify @ghost on GitHub and join" })).toBeInTheDocument();
  });

  it("asks for an email and hides Google when the invitation has none", () => {
    render(<InviteForm invitation={byLogin} mode="join" currentEmail={null} google />);
    expect(screen.getByLabelText("Email")).not.toHaveAttribute("readonly");
    expect(screen.queryByText(/Join with Google/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create account and verify on GitHub" })).toBeDisabled();
  });

  it("keeps the invited email fixed and shows a problem passed back", () => {
    render(<InviteForm invitation={byEmail} mode="join" currentEmail={null} google problem="this invitation is for @ghost, not @someone" />);
    expect(screen.getByLabelText("Email")).toHaveAttribute("readonly");
    expect(screen.getByText("Join with Google as bob@example.com")).toBeInTheDocument();
    expect(screen.getByText("this invitation is for @ghost, not @someone")).toBeInTheDocument();
  });
});
