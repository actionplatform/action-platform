import { redirect } from "next/navigation";

export default function CiActivityPage() {
  redirect("/connect/ci?tab=activity");
}
