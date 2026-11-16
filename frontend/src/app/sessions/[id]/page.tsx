"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Card, ErrorMessage, Loading, PageTitle, ResultBadge, SeverityBadge, Stat } from "@/components/ui";
import { api, liveSessionUrl } from "@/lib/api";
import { formatDateTime, formatTime } from "@/lib/format";
import { useModules } from "@/lib/hooks";
import type { LiveMessage, SessionDetail, SessionEvent } from "@/lib/types";

export default function SessionPage() {
  return (
    <AppShell>
      <LiveSession />
    </AppShell>
  );
}

/**
 * Live view of one training session.
 * 1. Open the WebSocket. 2. When the server confirms the subscription, load the
 * current state over REST. 3. Append every new event pushed by the server.
 */
function LiveSession() {
  const { id } = useParams<{ id: string }>();
  const sessionId = Number(id);
  const { modules, stepTitle, deviationTitle, moduleTitle } = useModules();
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const socket = new WebSocket(liveSessionUrl(sessionId));
    const load = () =>
      api<SessionDetail>(`/api/sessions/${sessionId}`)
        .then((data) => {
          setSession(data);
          if (data.status === "completed") socket.close(); // nothing live left to watch
        })
        .catch(setError);

    socket.onmessage = (message) => {
      const data: LiveMessage = JSON.parse(message.data);
      if (data.type === "subscribed") {
        setConnected(true);
        load(); // snapshot after subscribing, so no event can fall in between
      } else if (data.type === "event") {
        setSession((current) => (current ? { ...current, events: addEvent(current.events, data.event) } : current));
      } else if (data.type === "finished") {
        load(); // reload to get the final score, skipped steps and certificate
      }
    };
    socket.onclose = () => setConnected(false);
    socket.onerror = () => load(); // e.g. session already finished: just show the stored data

    return () => socket.close();
  }, [sessionId]);

  if (error) return <ErrorMessage error={error} />;
  if (!session) return <Loading />;

  const trainingModule = modules.find((m) => m.code === session.module);
  const doneSteps = new Set(session.events.filter((e) => e.kind === "step").map((e) => e.step));
  const deviations = session.events.filter((e) => e.kind === "deviation");
  const penalty = deviations.reduce((sum, e) => sum + e.penalty, 0);
  const running = session.status === "running";

  return (
    <>
      <PageTitle
        title={`${session.trainee_name} · ${moduleTitle(session.module)}`}
        subtitle={`Started ${formatDateTime(session.started_at)}`}
      >
        <div className="flex items-center gap-3 text-sm">
          {running && (
            <span className={connected ? "text-emerald-600" : "text-slate-400"} data-testid="ws-status">
              {connected ? "● connected" : "○ connecting…"}
            </span>
          )}
          <ResultBadge passed={session.passed} status={session.status} />
        </div>
      </PageTitle>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Steps done" value={`${doneSteps.size} / ${trainingModule?.steps.length ?? "?"}`} />
        <Stat label="Deviations" value={deviations.length} />
        <Stat
          label={running ? "Score so far" : "Final score"}
          value={running ? Math.max(0, 100 - penalty) : session.score}
        />
        <Stat
          label="Certificate"
          value={
            session.certificate_code ? (
              <Link href={`/certificates/${session.certificate_code}`} className="text-base text-brand-700 underline">
                view certificate
              </Link>
            ) : (
              "–"
            )
          }
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <Card title="Procedure" className="lg:col-span-2">
          <ol className="space-y-2">
            {trainingModule?.steps.map((step, i) => {
              const done = doneSteps.has(step.code);
              const skipped = deviations.some((d) => d.step === step.code && d.deviation === "skipped_step");
              return (
                <li key={step.code} className="flex items-center gap-3 text-sm">
                  <span
                    className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-medium ${
                      done
                        ? "bg-emerald-500 text-white"
                        : skipped
                          ? "bg-red-500 text-white"
                          : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {done ? "✓" : skipped ? "!" : i + 1}
                  </span>
                  <span className={done ? "" : "text-slate-500"}>{step.title}</span>
                </li>
              );
            })}
          </ol>
        </Card>

        <Card title="Event stream" className="lg:col-span-3">
          <ul className="max-h-[28rem] space-y-1 overflow-y-auto" data-testid="event-stream">
            {session.events.length === 0 && <li className="text-sm text-slate-400">Waiting for the first event…</li>}
            {[...session.events].reverse().map((e) => (
              <li key={e.id} className="flex items-center gap-3 rounded-md px-2 py-1.5 text-sm odd:bg-slate-50">
                <span className="w-20 shrink-0 font-mono text-xs text-slate-400">{formatTime(e.created_at)}</span>
                {e.kind === "step" ? (
                  <span>
                    <span className="text-emerald-600">✓</span> {stepTitle(session.module, e.step)}
                  </span>
                ) : (
                  <span className="flex flex-1 flex-wrap items-center gap-2">
                    <SeverityBadge severity={e.severity ?? "minor"} />
                    {deviationTitle(e.deviation ?? "")}
                    <span className="text-slate-400">at “{stepTitle(session.module, e.step)}”</span>
                    <span className="ml-auto font-mono text-xs text-red-600">−{e.penalty}</span>
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}

function addEvent(events: SessionEvent[], event: SessionEvent): SessionEvent[] {
  return events.some((e) => e.id === event.id) ? events : [...events, event];
}
