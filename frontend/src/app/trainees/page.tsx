"use client";

import Link from "next/link";
import AppShell from "@/components/AppShell";
import { Card, ErrorMessage, Loading, PageTitle } from "@/components/ui";
import { useApi, useModules } from "@/lib/hooks";
import type { TraineeProgress } from "@/lib/types";

export default function TraineesPage() {
  return (
    <AppShell>
      <TraineeTable />
    </AppShell>
  );
}

function TraineeTable() {
  const { data, error, isLoading } = useApi<TraineeProgress[]>("/api/analytics/trainees");
  const { moduleTitle } = useModules();

  return (
    <>
      <PageTitle title="Trainee progress" subtitle="Completed sessions, scores and valid certificates per trainee" />
      <ErrorMessage error={error} />
      {isLoading && <Loading />}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="pb-3">Trainee</th>
                <th className="pb-3 text-right">Sessions</th>
                <th className="pb-3 text-right">Passed</th>
                <th className="pb-3 text-right">Avg score</th>
                <th className="pb-3 text-right">Last score</th>
                <th className="pb-3 pl-6">Certified for</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((t) => (
                <tr key={t.trainee_id}>
                  <td className="py-3">
                    <Link href={`/trainees/${t.trainee_id}`} className="font-medium text-brand-700 hover:underline">
                      {t.trainee_name}
                    </Link>
                  </td>
                  <td className="py-3 text-right tabular-nums">{t.sessions}</td>
                  <td className="py-3 text-right tabular-nums">{t.passed_sessions}</td>
                  <td className="py-3 text-right tabular-nums">{t.average_score ?? "–"}</td>
                  <td className="py-3 text-right tabular-nums">{t.last_score ?? "–"}</td>
                  <td className="py-3 pl-6">
                    <div className="flex flex-wrap gap-1">
                      {t.certified_modules.length === 0 && <span className="text-slate-400">none</span>}
                      {t.certified_modules.map((m) => (
                        <span
                          key={m}
                          className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700 ring-1 ring-emerald-200"
                        >
                          {moduleTitle(m)}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
