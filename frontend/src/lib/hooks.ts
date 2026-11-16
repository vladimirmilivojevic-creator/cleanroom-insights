"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type { Module } from "./types";

/** GET an API path with TanStack Query (caching, loading and error state). */
export function useApi<T>(path: string | null, options: { refetchInterval?: number } = {}) {
  return useQuery({
    queryKey: [path],
    queryFn: () => api<T>(path!),
    enabled: path !== null,
    ...options,
  });
}

/** Module catalogue, used to show readable step and deviation names. */
export function useModules() {
  const { data } = useApi<Module[]>("/api/modules");
  const modules = Object.fromEntries((data ?? []).map((m) => [m.code, m]));

  const stepTitle = (module: string, step: string) =>
    modules[module]?.steps.find((s) => s.code === step)?.title ?? step;
  const deviationTitle = (code: string) =>
    (data ?? []).flatMap((m) => m.deviations).find((d) => d.code === code)?.title ??
    (code === "skipped_step" ? "Step skipped" : code);
  const moduleTitle = (module: string) => modules[module]?.title ?? module;

  return { modules: data ?? [], stepTitle, deviationTitle, moduleTitle };
}
