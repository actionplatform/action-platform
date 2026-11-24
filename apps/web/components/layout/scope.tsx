"use client";

import { createContext, type ReactNode, useContext, useEffect, useState } from "react";

export type AppScope = { projectId: string; projectName: string; appId: string; appName: string };

type ScopeState = { scope: AppScope | null; setScope: (s: AppScope | null) => void; switchingTo: string | null; setSwitchingTo: (orgId: string | null) => void };

const Ctx = createContext<ScopeState>({ scope: null, setScope: () => {}, switchingTo: null, setSwitchingTo: () => {} });

export function ScopeProvider({ children }: { children: ReactNode }) {
  const [scope, setScope] = useState<AppScope | null>(null);
  const [switchingTo, setSwitchingTo] = useState<string | null>(null);
  return <Ctx.Provider value={{ scope, setScope, switchingTo, setSwitchingTo }}>{children}</Ctx.Provider>;
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
