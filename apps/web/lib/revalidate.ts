import { revalidatePath } from "next/cache";

export function refreshProject(projectId: string) {
  revalidatePath(`/projects/${projectId}`, "layout");
}
