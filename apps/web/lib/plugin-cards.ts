import { headers } from "next/headers";
import type { PluginCardData } from "@/features/plugins";
import { publicOrigin } from "@/lib/origin";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export type PluginGroup = "ci" | "deploy" | "observability" | "notifications" | "access" | "other";

const GROUPS: [PluginGroup, RegExp][] = [
  ["deploy", /lambda|cloud-run|dokploy|kubernetes|fly|vercel|render/],
  ["observability", /sentry|datadog|grafana|prometheus|loki|tempo|pyroscope|newrelic|honeycomb|betterstack|uptime/],
  ["notifications", /notify|slack|discord|teams|mail/],
  ["ci", /jenkins|circleci|buildkite|drone/],
  ["access", /access|github/],
];

export function groupOf(slug: string): PluginGroup {
  return GROUPS.find(([, pattern]) => pattern.test(slug))?.[0] ?? "other";
}

function filled(text: string, issuer: string, organization: string, encode: (v: string) => string = encodeURIComponent): string {
  return text.replaceAll("{issuer}", encode(issuer)).replaceAll("{organization}", encode(organization));
}

export async function pluginCards(groups?: PluginGroup[]): Promise<{ plugins: PluginCardData[]; canManage: boolean }> {
  const { session, org } = await requireOrg();
  const canManage = !!session.grants["org.manage"];
  const issuer = publicOrigin(await headers());
  const catalog = await v1.plugins().catch(() => ({ plugins: [] }));
  const wanted = catalog.plugins.filter((p) => !groups || groups.includes(groupOf(p.slug)));
  const plugins = await Promise.all(
    wanted.map(async (p) => {
      const options = (p.options ?? []).map((o) => ({
        ...o,
        action_url: o.action_url ? filled(o.action_url, issuer, org.slug) : "",
        action_copy: o.action_copy ? filled(o.action_copy, issuer, org.slug, (v) => v) : "",
      }));
      const stored = canManage && options.length > 0 ? await v1.pluginOptions(p.slug).catch(() => ({ options: {}, secrets: [] })) : { options: {}, secrets: [] };
      return { slug: p.slug, name: p.name || p.slug, version: p.version, description: p.description, error: p.error ?? null, options, values: stored.options as Record<string, unknown>, secrets: stored.secrets ?? [] };
    }),
  );
  return { plugins, canManage };
}
