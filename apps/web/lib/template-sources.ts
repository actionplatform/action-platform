import { type TemplateSourceRow, v1 } from "./v1";

export type TemplateSource = { id: string; organizationId: string; name: string; url: string; ref: string; sourceHostId: string | null; createdAt: Date };

function source(row: TemplateSourceRow, orgId: string): TemplateSource {
  return { id: row.id, organizationId: orgId, name: row.name, url: row.url, ref: row.ref, sourceHostId: row.source_host_id ?? null, createdAt: new Date(row.created_at) };
}

export async function templateSourcesOf(orgId: string): Promise<TemplateSource[]> {
  return (await v1.templateSources()).map((r) => source(r, orgId));
}
