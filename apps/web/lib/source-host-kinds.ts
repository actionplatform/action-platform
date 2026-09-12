export const HOST_KINDS = [
  { id: "github", label: "GitHub", tokenLabel: "Personal access token", tokenHint: "Classic: repo + workflow. Fine-grained: Contents, Workflows and Administration (write).", baseUrlHint: "Leave empty for github.com; GitHub Enterprise: https://ghe.example.com/api/v3", needsUsername: false },
  { id: "gitlab", label: "GitLab", tokenLabel: "Access token", tokenHint: "Scopes: api, write_repository.", baseUrlHint: "Leave empty for gitlab.com; self-hosted: https://gitlab.example.com", needsUsername: false },
  { id: "bitbucket", label: "Bitbucket", tokenLabel: "App password or access token", tokenHint: "Repositories: read, write, admin. Pull requests: write.", baseUrlHint: "Bitbucket Cloud only", needsUsername: true },
  { id: "generic", label: "Other", tokenLabel: "Token or password", tokenHint: "Used as the HTTPS password on push.", baseUrlHint: "Any git server over HTTPS, e.g. https://git.example.com", needsUsername: true },
] as const;

export type HostKind = (typeof HOST_KINDS)[number]["id"];

export type SourceHost = {
  id: string;
  organizationId: string;
  kind: HostKind;
  name: string;
  baseUrl: string | null;
  username: string | null;
  defaultOwner: string | null;
  authKind: "token" | "oauth";
  login: string | null;
  createdAt: Date;
};
