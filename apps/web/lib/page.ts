export type PageQuery = { page: number; per: number };
export type Paged<T> = { items: T[]; total: number; page: number; per: number };

export const DEFAULT_PER = 10;

export function pageQuery(params: Record<string, string | string[] | undefined>, key = ""): PageQuery {
  const pageKey = key ? `${key}_page` : "page";
  const perKey = key ? `${key}_per` : "per";
  const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);
  const page = Math.max(1, Number(one(params[pageKey])) || 1);
  const per = Math.max(1, Math.min(100, Number(one(params[perKey])) || DEFAULT_PER));
  return { page, per };
}
