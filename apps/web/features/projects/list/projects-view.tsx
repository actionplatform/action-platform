"use client";

import { useMemo, useState } from "react";
import { NewProjectDialog } from "./new-project-form";
import { ProjectCard, type ProjectItem, type TeamOption } from "./project-card";
import { ProjectsEmptyState, ProjectsNoResults } from "./projects-empty-state";
import { ProjectsToolbar, type SortId } from "./projects-toolbar";

export function ProjectsView({ projects, teams, canManage }: { projects: ProjectItem[]; teams: TeamOption[]; canManage: boolean }) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortId>("updated-desc");
  const [creating, setCreating] = useState(false);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = projects.filter((p) => !q || p.name.toLowerCase().includes(q) || p.slug.toLowerCase().includes(q));
    const by: Record<SortId, (a: ProjectItem, b: ProjectItem) => number> = {
      "updated-desc": (a, b) => b.updatedAt.localeCompare(a.updatedAt),
      "updated-asc": (a, b) => a.updatedAt.localeCompare(b.updatedAt),
      "name-asc": (a, b) => a.name.localeCompare(b.name),
      "name-desc": (a, b) => b.name.localeCompare(a.name),
    };
    return [...list].sort(by[sort]);
  }, [projects, query, sort]);

  if (projects.length === 0) {
    return (
      <>
        <ProjectsEmptyState onCreate={canManage ? () => setCreating(true) : undefined} />
        <NewProjectDialog open={creating} onClose={() => setCreating(false)} />
      </>
    );
  }

  return (
    <>
      <ProjectsToolbar query={query} onQuery={setQuery} sort={sort} onSort={setSort} />
      {visible.length === 0 ? (
        <ProjectsNoResults query={query.trim()} onClear={() => setQuery("")} />
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 md:gap-4 xl:grid-cols-3">
          {visible.map((p) => <ProjectCard key={p.id} project={p} teams={teams} canManage={canManage} />)}
        </div>
      )}
    </>
  );
}
