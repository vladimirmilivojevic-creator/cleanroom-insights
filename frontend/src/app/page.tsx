"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import AppShell from "@/components/AppShell";
import { buttonClass, Card, ErrorMessage, inputClass, PageTitle, ResultBadge, Stat } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useApi, useModules } from "@/lib/hooks";
import type { Overview, TrainingSession, User } from "@/lib/types";

export default function DashboardPage() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}

function Dashboard() {
  const overview = useApi<Overview>("/api/analytics/overview", { refetchInterval: 5000 });
  const running = useApi<TrainingSession[]>("/api/sessions?status=running", { refetchInterval: 3000 });
  const recent = useApi<TrainingSession[]>("/api/sessions?status=completed&limit=8", { refetchInterval: 5000 });
  const { moduleTitle } = useModules();
  const o = overview.data;

  return (
    <>
      <PageTitle title="Training dashboard" subtitle="Live sessions and results of your organisation" />
      <ErrorMessage error={overview.error} />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Stat label="Trainees" value={o?.trainees ?? "–"} />
        <Stat label="Completed sessions" value={o?.completed_sessions ?? "–"} />
        <Stat label="Pass rate" value={o ? `${o.pass_rate}%` : "–"} hint="score ≥ 80, no critical deviation" />
        <Stat label="Average score" value={o?.average_score ?? "–"} />
        <Stat label="Valid certificates" value={o?.valid_certificates ?? "–"} hint="valid for 12 months" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card title="Live sessions">
          <StartSimulation />
          <ul className="mt-4 divide-y divide-slate-100" data-testid="running-sessions">
            {running.data?.length === 0 && (
              <li className="py-3 text-sm text-slate-400">No session is running right now.</li>
            )}
            {running.data?.map((s) => (
              <li key={s.id} className="flex items-center justify-between py-3 text-sm">
                <span>
                  <span className="font-medium">{s.trainee_name}</span>
                  <span className="text-slate-500"> · {moduleTitle(s.module)}</span>
                </span>
                <Link href={`/sessions/${s.id}`} className="flex items-center gap-2 text-brand-700 hover:underline">
                  <ResultBadge passed={null} status="running" /> watch
                </Link>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Recently completed">
          <ul className="divide-y divide-slate-100">
            {recent.data?.map((s) => (
              <li key={s.id} className="flex items-center justify-between py-2.5 text-sm">
                <Link href={`/sessions/${s.id}`} className="hover:underline">
                  <span className="font-medium">{s.trainee_name}</span>
                  <span className="text-slate-500"> · {moduleTitle(s.module)}</span>
                  <span className="block text-xs text-slate-400">{formatDateTime(s.started_at)}</span>
                </Link>
                <span className="flex items-center gap-3">
                  <span className="font-semibold tabular-nums">{s.score}</span>
                  <ResultBadge passed={s.passed} />
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}

/** Start a simulated VR session: the backend plays headset events in the background. */
function StartSimulation() {
  const router = useRouter();
  const trainees = useApi<User[]>("/api/users?role=trainee");
  const { modules } = useModules();
  const [traineeId, setTraineeId] = useState("");
  const [module, setModule] = useState("gowning");
  const [error, setError] = useState<Error | null>(null);
  const [busy, setBusy] = useState(false);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const id = Number(traineeId || trainees.data?.[0]?.id);
      const session = await api<TrainingSession>("/api/sessions/simulate", {
        method: "POST",
        body: JSON.stringify({ trainee_id: id, module }),
      });
      router.push(`/sessions/${session.id}`);
    } catch (e) {
      setError(e as Error);
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <p className="mb-2 text-xs text-slate-500">
        No headset at hand? Start a simulated session and watch the events arrive over WebSockets.
      </p>
      <div className="flex flex-wrap gap-2">
        <select
          className={inputClass}
          value={traineeId}
          onChange={(e) => setTraineeId(e.target.value)}
          aria-label="Trainee"
        >
          {trainees.data?.map((t) => (
            <option key={t.id} value={t.id}>
              {t.full_name}
            </option>
          ))}
        </select>
        <select className={inputClass} value={module} onChange={(e) => setModule(e.target.value)} aria-label="Module">
          {modules.map((m) => (
            <option key={m.code} value={m.code}>
              {m.title}
            </option>
          ))}
        </select>
        <button className={buttonClass} onClick={start} disabled={busy || !trainees.data?.length}>
          Start simulated session
        </button>
      </div>
      <ErrorMessage error={error} />
    </div>
  );
}
