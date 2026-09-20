import { loadApp } from "@/features/projects/load";
import { SettingsTab } from "@/features/projects";

export default async function SettingsPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  return <SettingsTab view={loaded.view} hosts={loaded.hosts} currentHost={loaded.currentHost} />;
}
