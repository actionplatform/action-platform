import { redirect } from "next/navigation";

export default function PluginsPage() {
  redirect("/admin?tab=plugins");
}
