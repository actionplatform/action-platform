import { client, type Schemas, unwrap } from "@/lib/api";

export const integrations = {
  hosts: async () => unwrap(await client.GET("/api/v1/hosts")),
  addHost: async (body: Schemas["AddHostRequest"]) => unwrap(await client.POST("/api/v1/hosts", { body })),
  removeHost: async (id: string) => unwrap(await client.DELETE("/api/v1/hosts/{host_id}", { params: { path: { host_id: id } } })),
  rotateHostToken: async (id: string, token: string) => unwrap(await client.PUT("/api/v1/hosts/{host_id}/token", { params: { path: { host_id: id } }, body: { token } })),
  setHostOwner: async (id: string, owner: string) => unwrap(await client.PUT("/api/v1/hosts/{host_id}/owner", { params: { path: { host_id: id } }, body: { owner } })),
  hostAccess: async (id: string) => unwrap(await client.GET("/api/v1/hosts/{host_id}/access", { params: { path: { host_id: id } } })),
  oauthApps: async () => unwrap(await client.GET("/api/v1/oauth/apps")),
  saveOAuthApp: async (provider: string, body: Schemas["OAuthAppRequest"]) => unwrap(await client.PUT("/api/v1/oauth/apps/{provider}", { params: { path: { provider } }, body })),
  clearOAuthApp: async (provider: string) => unwrap(await client.DELETE("/api/v1/oauth/apps/{provider}", { params: { path: { provider } } })),
  oauthStart: async (provider: string, origin: string, returnTo: string) =>
    unwrap(await client.POST("/api/v1/oauth/{provider}/start", { params: { path: { provider } }, body: { origin, return_to: returnTo } })),
  oauthCallback: async (provider: string, body: Schemas["OAuthCallbackRequest"]) =>
    unwrap(await client.POST("/api/v1/oauth/{provider}/callback", { params: { path: { provider } }, body })),
  disconnectOAuthHost: async (provider: string, login: string) =>
    unwrap(await client.DELETE("/api/v1/oauth/{provider}/hosts/{login}", { params: { path: { provider, login } } })),
  githubManifest: async (body: Schemas["GitHubAppManifestRequest"]) => unwrap(await client.POST("/api/v1/oauth/github/manifest", { body })),
  githubManifestCallback: async (body: Schemas["ManifestCallbackRequest"]) => unwrap(await client.POST("/api/v1/oauth/github/manifest/callback", { body })),
  githubInstall: async (origin: string, returnTo: string) => unwrap(await client.POST("/api/v1/oauth/github/install", { body: { origin, return_to: returnTo } })),
  ciHosts: async () => unwrap(await client.GET("/api/v1/ci-hosts")),
  addCiHost: async (body: Schemas["AddCiHostRequest"]) => unwrap(await client.POST("/api/v1/ci-hosts", { body })),
  removeCiHost: async (id: string) => unwrap(await client.DELETE("/api/v1/ci-hosts/{host_id}", { params: { path: { host_id: id } } })),
  testCiHost: async (id: string) => unwrap(await client.POST("/api/v1/ci-hosts/{host_id}/test", { params: { path: { host_id: id } } })),
  templateSources: async () => unwrap(await client.GET("/api/v1/template-sources")),
  addTemplateSource: async (name: string, url: string, ref: string) => unwrap(await client.POST("/api/v1/template-sources", { body: { name, url, ref } })),
  removeTemplateSource: async (id: string) => unwrap(await client.DELETE("/api/v1/template-sources/{id}", { params: { path: { id } } })),
  plugins: async () => unwrap(await client.GET("/api/v1/plugins")),
  pluginOptions: async (slug: string) => unwrap(await client.GET("/api/v1/plugins/{slug}/options", { params: { path: { slug } } })),
  setPluginOptions: async (slug: string, options: Record<string, unknown>) =>
    unwrap(await client.PUT("/api/v1/plugins/{slug}/options", { params: { path: { slug } }, body: { options } })),
};
