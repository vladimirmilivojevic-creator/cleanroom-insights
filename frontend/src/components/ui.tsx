// Small presentational building blocks shared by all pages.

export function PageTitle({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {title && <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>}
      {children}
    </section>
  );
}

export function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-semibold tabular-nums" data-testid={`stat-${label}`}>
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

const SEVERITY_STYLES: Record<string, string> = {
  minor: "bg-amber-50 text-amber-700 ring-amber-200",
  major: "bg-orange-50 text-orange-700 ring-orange-200",
  critical: "bg-red-50 text-red-700 ring-red-200",
};

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${SEVERITY_STYLES[severity] ?? ""}`}>
      {severity}
    </span>
  );
}

export function ResultBadge({ passed, status }: { passed: boolean | null; status?: string }) {
  if (status === "running")
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-50 px-2 py-0.5 text-xs font-medium text-sky-700 ring-1 ring-sky-200">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-sky-500" /> live
      </span>
    );
  return passed ? (
    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">
      passed
    </span>
  ) : (
    <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700 ring-1 ring-red-200">
      failed
    </span>
  );
}

export function Loading() {
  return <p className="text-sm text-slate-400">Loading…</p>;
}

export function ErrorMessage({ error }: { error: Error | null }) {
  if (!error) return null;
  return <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error.message}</p>;
}

export const buttonClass =
  "rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 disabled:opacity-50";
export const inputClass =
  "rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100";
