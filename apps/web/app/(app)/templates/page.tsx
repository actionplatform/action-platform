import { ApiOffline } from "@/components/api-offline";
import { PageHeader } from "@/components/layout/page";
import { api, type Matrix } from "@/lib/api";
import { Catalog } from "./catalog";

export default async function TemplatesPage() {
  let matrix: Matrix;
  try {
    matrix = await api.matrix();
  } catch (e) {
    return <ApiOffline error={e} />;
  }

  return (
    <>
      <PageHeader title="Templates" description="Browse foundations for projects, cloud deployments, and services." />
      <Catalog matrix={matrix} />
    </>
  );
}
