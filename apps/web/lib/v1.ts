import type { Schemas } from "./api";
import { integrations } from "./api/integrations";
import { jobs } from "./api/jobs";
import { organization } from "./api/organization";
import { projects } from "./api/projects";

export type ProjectRow = Schemas["ProjectRow"];
export type TeamRow = Schemas["TeamRow"];
export type MemberRow = Schemas["MemberRow"];
export type InvitationRow = Schemas["InvitationRow"];
export type HostRow = Schemas["HostRow"];
export type OAuthAppRow = Schemas["OAuthAppRow"];
export type TemplateSourceRow = Schemas["TemplateSourceRow"];
export type ImportsRow = Schemas["Imports"];
export type ReleaseRow = Schemas["ReleaseRow"];
export type PullRequestRow = Schemas["PullRequestRow"];
export type JobRow = Schemas["JobOut"];
export type CiHostRow = Schemas["CiHostRow"];
export type CiRunRow = Schemas["CiRunRow"];
export type CiRunsRow = Schemas["CiRuns"];
export type DeploymentsRow = Schemas["Deployments"];
export type DeploymentRow = Schemas["DeploymentRow"];
export type TargetRow = Schemas["TargetRow"];

export const v1 = { ...organization, ...projects, ...integrations, ...jobs };
