import type { Heatmap } from "@/lib/types";

/** Steps (rows) x deviation types (columns). Darker cell = deviation happens more often there. */
export default function DeviationHeatmap({ heatmap }: { heatmap: Heatmap }) {
  const counts = new Map(heatmap.cells.map((c) => [`${c.step}|${c.deviation}`, c.count]));
  const max = Math.max(1, ...heatmap.cells.map((c) => c.count));

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-1 text-sm" data-testid="heatmap">
        <thead>
          <tr>
            <th className="w-56" />
            {heatmap.deviations.map((d) => (
              <th key={d.code} className="px-1 pb-2 text-left align-bottom text-xs font-medium text-slate-500">
                {d.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {heatmap.steps.map((step) => (
            <tr key={step.code}>
              <td className="pr-3 text-slate-700">{step.title}</td>
              {heatmap.deviations.map((d) => {
                const count = counts.get(`${step.code}|${d.code}`) ?? 0;
                const intensity = count / max;
                return (
                  <td
                    key={d.code}
                    title={`${step.title} · ${d.title}: ${count}`}
                    className="h-10 min-w-16 rounded-md text-center text-xs font-medium tabular-nums"
                    style={{
                      background: count ? `rgba(220, 38, 38, ${0.12 + intensity * 0.78})` : "#f1f5f9",
                      color: intensity > 0.5 ? "white" : "#334155",
                    }}
                  >
                    {count || ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
