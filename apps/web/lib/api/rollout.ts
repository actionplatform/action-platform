import { client, unwrap } from "@/lib/api";

type Control = "promote" | "pause" | "resume" | "abort";

export const rollout = {
  deployStrategies: async () => unwrap(await client.GET("/api/v1/deploy-strategies")),
  scopeStrategies: async (projectId: string, appId: string, scope: string) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/scopes/{scope}/strategies", { params: { path: { project_id: projectId, app_id: appId, scope } } })),
  deploymentSteps: async (projectId: string, appId: string, deploymentId: string) =>
    unwrap(await client.GET("/api/v1/projects/{project_id}/apps/{app_id}/deployments/{deployment_id}/steps", { params: { path: { project_id: projectId, app_id: appId, deployment_id: deploymentId } } })),
  deploymentControl: async (projectId: string, appId: string, deploymentId: string, action: Control) => {
    const path = { project_id: projectId, app_id: appId, deployment_id: deploymentId };
    switch (action) {
      case "promote": return unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/deployments/{deployment_id}/promote", { params: { path } }));
      case "pause": return unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/deployments/{deployment_id}/pause", { params: { path } }));
      case "resume": return unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/deployments/{deployment_id}/resume", { params: { path } }));
      case "abort": return unwrap(await client.POST("/api/v1/projects/{project_id}/apps/{app_id}/deployments/{deployment_id}/abort", { params: { path } }));
    }
  },
};
