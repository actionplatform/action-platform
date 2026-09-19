import type { Scopes } from "./scope-kinds";
import { v1 } from "./v1";

export type { Criticality, Scope, ScopeRequest, Scopes, Shape } from "./scope-kinds";
export { ACCEPTS, CRITICALITY, shapeOf } from "./scope-kinds";

export async function scopesOf(projectId: string, appId: string): Promise<Scopes> {
  return v1.scopes(projectId, appId);
}
