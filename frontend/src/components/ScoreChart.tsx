"use client";

import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatDate } from "@/lib/format";
import type { TrainingSession } from "@/lib/types";

/** Score of each completed session over time, with the pass line at 80. */
export default function ScoreChart({ sessions }: { sessions: TrainingSession[] }) {
  const data = sessions
    .filter((s) => s.status === "completed")
    .map((s) => ({ date: formatDate(s.started_at), score: s.score, module: s.module }));

  if (data.length === 0) return <p className="text-sm text-slate-400">No completed sessions yet.</p>;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 10, right: 16, bottom: 0, left: -16 }}>
        <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#64748b" }} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: "#64748b" }} />
        <Tooltip />
        <ReferenceLine
          y={80}
          stroke="#10b981"
          strokeDasharray="4 4"
          label={{ value: "pass", fontSize: 11, fill: "#10b981" }}
        />
        <Line type="monotone" dataKey="score" stroke="#0e7a74" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
