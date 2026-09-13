"use client";

import { createContext, type ReactNode, useContext, useEffect, useState } from "react";

export type AppScope = { projectId: string; projectName: string; appId: string; appName: string };

const Ctx = createContext<{ scope: AppScope | null; setScope: (s: AppScope | null) => void }>({ scope: null, setScope: () => {} });

export function ScopeProvider({ children }: { children: ReactNode }) {
  const [scope, setScope] = useState<AppScope | null>(null);
  return <Ctx.Provider value={{ scope, setScope }}>{children}</Ctx.Provider>;
}

export function useScope() {
  return useContext(Ctx);
}

export function AppScopeMarker(scope: AppScope) {
  const { setScope } = useScope();
  useEffect(() => {
    setScope(scope);
    return () => setScope(null);
  }, [scope.projectId, scope.projectName, scope.appId, scope.appName, setScope]);
  return null;
}
