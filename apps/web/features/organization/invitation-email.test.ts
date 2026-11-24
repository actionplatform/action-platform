import { describe, expect, it } from "vitest";
import { invitationEmail, invitationEmailNotice } from "./invitation-email";

describe("invitationEmail", () => {
  it("says sent", () => {
    expect(invitationEmail("sent", null)).toEqual({ label: "Sent", tone: "success", reason: null });
  });

  it("carries the reason of a failure", () => {
    expect(invitationEmail("failed", "535 bad login")).toEqual({ label: "Not sent", tone: "warning", reason: "535 bad login" });
  });

  it("shows nothing when the instance sends no email", () => {
    expect(invitationEmail("off", null)).toBeNull();
  });

  it("marks an invitation a mailer has not sent yet", () => {
    expect(invitationEmail("not_sent", null)?.label).toBe("Not sent");
  });
});

describe("invitationEmailNotice", () => {
  it("tells where the email went", () => {
    expect(invitationEmailNotice("sent", null, "bob@example.com")).toBe("An email with the link went to bob@example.com.");
  });

  it("explains a failure and the way out", () => {
    expect(invitationEmailNotice("failed", "smtp down", "bob@example.com")).toContain("smtp down");
  });

  it("is silent without a mailer", () => {
    expect(invitationEmailNotice("off", null, "bob@example.com")).toBeNull();
  });
});
