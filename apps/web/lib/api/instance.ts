import { client, unwrap } from "@/lib/api";

export const instance = {
  instanceHealth: async () => unwrap(await client.GET("/api/v1/instance/health")),
  sendTestEmail: async () => unwrap(await client.POST("/api/v1/instance/test-email")),
};
