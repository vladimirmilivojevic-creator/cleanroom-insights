"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import AppShell from "@/components/AppShell";
import DeviationHeatmap from "@/components/DeviationHeatmap";
import { buttonClass, Card, ErrorMessage, inputClass, Loading, PageTitle, SeverityBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/format";
import { useApi, useModules } from "@/lib/hooks";
import type { Heatmap, WarehouseReport } from "@/lib/types";

export default function AnalyticsPage() {
  return (
    <AppShell>
      <Analytics />
    </AppShell>
  );
}

function Analytics() {
  const [module, setModule] = useState("gowning");
  const { modules } = useModules();
  const heatmap = useApi<Heatmap>(`/api/analytics/heatmap?module=${module}`);

  return (
    <>
      <PageTitle title="Analytics" subtitle="Where do trainees make mistakes, and are they getting better?">
        <select className={inputClass} value={module} onChange={(e) => setModule(e.target.value)} aria-label="Module">
          {modules.map((m) => (
            <option key={m.code} value={m.code}>
              {m.title}
            </option>
          ))}
        </select>
      </PageTitle>

      <Card title="Deviation heatmap (live data, PostgreSQL)">
        <ErrorMessage error={heatmap.error} />
        {heatmap.data ? <DeviationHeatmap heatmap={heatmap.data} /> : <Loading />}
      </Card>

      <Warehouse />
    </>
  );
}

/** Reports computed by DuckDB on the Parquet files written by the nightly ETL. */
function Warehouse() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { data, error } = useApi<WarehouseReport>("/api/analytics/warehouse");
  const { deviationTitle, moduleTitle } = useModules();
  const [running, setRunning] = useState(false);

  async function runEtl() {
    setRunning(true);
    await api("/api/analytics/etl", { method: "POST" });
    await queryClient.invalidateQueries({ queryKey: ["/api/analytics/warehouse"] });
    setRunning(false);
  }

  return (
    <div className="mt-6 grid gap-6 lg:grid-cols-3">
      <Card title="Weekly trend (DuckDB on Parquet)" className="lg:col-span-2">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <span data-testid="etl-last-run">
            {data?.last_run
              ? `Last ETL run ${formatDateTime(data.last_run.finished_at)} · ${data.last_run.sessions} sessions, ${data.last_run.events} events`
              : "The ETL has not run yet."}
          </span>
          {user?.role === "admin" && (
            <button className={buttonClass} onClick={runEtl} disabled={running}>
              {running ? "Running…" : "Run ETL now"}
            </button>
          )}
        </div>
        <ErrorMessage error={error} />
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data?.weekly ?? []} margin={{ left: -16 }}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
            <XAxis dataKey="week" tick={{ fontSize: 12, fill: "#64748b" }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: "#64748b" }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="average_score" name="Average score" fill="#0e7a74" radius={[4, 4, 0, 0]} />
            <Bar dataKey="pass_rate" name="Pass rate %" fill="#94d3cb" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <div className="space-y-6">
        <Card title="Costliest deviations">
          <ul className="space-y-2 text-sm">
            {data?.top_deviations.map((d) => (
              <li key={d.deviation} className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2">
                  <SeverityBadge severity={d.severity} />
                  {deviationTitle(d.deviation)}
                </span>
                <span className="text-xs text-slate-500 tabular-nums">
                  {d.occurrences}× · −{d.total_penalty}
                </span>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="By module">
          <ul className="space-y-2 text-sm">
            {data?.modules.map((m) => (
              <li key={m.module} className="flex justify-between">
                <span>{moduleTitle(m.module)}</span>
                <span className="text-slate-500 tabular-nums">
                  avg {m.average_score} · {m.pass_rate}% pass
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
