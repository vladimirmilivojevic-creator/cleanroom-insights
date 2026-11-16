"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import AppShell from "@/components/AppShell";
import ScoreChart from "@/components/ScoreChart";
import { Card, ErrorMessage, Loading, PageTitle, ResultBadge, Stat } from "@/components/ui";
import { formatDate, formatDateTime } from "@/lib/format";
import { useApi, useModules } from "@/lib/hooks";
import type { TraineeDetail } from "@/lib/types";

export default function TraineePage() {
  return (
    <AppShell>
      <Trainee />
    </AppShell>
  );
}

function Trainee() {
  const { id } = useParams<{ id: string }>();
  const { data, error } = useApi<TraineeDetail>(`/api/analytics/trainees/${id}`, { refetchInterval: 10000 });
  const { moduleTitle } = useModules();

  if (error) return <ErrorMessage error={error} />;
  if (!data) return <Loading />;

  const completed = data.sessions.filter((s) => s.status === "completed");
  const passed = completed.filter((s) => s.passed).length;
  const average = completed.length
    ? Math.round(completed.reduce((sum, s) => sum + (s.score ?? 0), 0) / completed.length)
    : "–";
  const validCertificates = data.certificates.filter((c) => new Date(c.valid_until) > new Date());

  return (
    <>
      <PageTitle title={data.trainee.full_name} subtitle={data.trainee.email} />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Sessions" value={completed.length} />
        <Stat label="Passed" value={passed} />
        <Stat label="Average score" value={average} />
        <Stat label="Valid certificates" value={validCertificates.length} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card title="Score over time" className="lg:col-span-2">
          <ScoreChart sessions={data.sessions} />
        </Card>
        <Card title="Certificates">
          <ul className="space-y-2">
            {data.certificates.length === 0 && <li className="text-sm text-slate-400">No certificate yet.</li>}
            {data.certificates.map((c) => (
              <li key={c.code}>
                <Link
                  href={`/certificates/${c.code}`}
                  className="flex justify-between rounded-lg border border-slate-200 p-3 text-sm hover:border-brand-500"
                >
                  <span>
                    <span className="font-medium">{moduleTitle(c.module)}</span>
                    <span className="block text-xs text-slate-500">valid until {formatDate(c.valid_until)}</span>
                  </span>
                  <span className="font-semibold tabular-nums">{c.score}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Sessions" className="mt-6">
        <table className="w-full text-sm">
          <tbody className="divide-y divide-slate-100">
            {[...data.sessions].reverse().map((s) => (
              <tr key={s.id}>
                <td className="py-2.5">
                  <Link href={`/sessions/${s.id}`} className="text-brand-700 hover:underline">
                    {moduleTitle(s.module)}
                  </Link>
                </td>
                <td className="py-2.5 text-slate-500">{formatDateTime(s.started_at)}</td>
                <td className="py-2.5 text-right font-semibold tabular-nums">{s.score ?? ""}</td>
                <td className="py-2.5 pl-4 text-right">
                  <ResultBadge passed={s.passed} status={s.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
