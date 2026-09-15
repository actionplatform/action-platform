import { loadApp } from "../load";
import { SettingsTab } from "../settings-tab";

export default async function SettingsPage({ params }: { params: Promise<{ project: string; app: string }> }) {
  const { project, app } = await params;
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  return <SettingsTab view={loaded.view} />;
}
