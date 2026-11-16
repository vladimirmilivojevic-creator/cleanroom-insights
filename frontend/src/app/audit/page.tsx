"use client";

import AppShell from "@/components/AppShell";
import { Card, ErrorMessage, Loading, PageTitle } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { AuditEntry, AuditVerification, User } from "@/lib/types";

export default function AuditPage() {
  return (
    <AppShell>
      <AuditTrail />
    </AppShell>
  );
}

function AuditTrail() {
  const entries = useApi<AuditEntry[]>("/api/audit?limit=200");
  const verification = useApi<AuditVerification>("/api/audit/verify");
  const users = useApi<User[]>("/api/users");
  const userName = (id: number | null) =>
    id === null ? "system" : (users.data?.find((u) => u.id === id)?.full_name ?? `#${id}`);
  const v = verification.data;

  return (
    <>
      <PageTitle title="Audit trail" subtitle="Append-only record of who did what and when. Entries are hash-chained.">
        {v && (
          <span
            data-testid="chain-status"
            className={`rounded-lg px-3 py-2 text-sm font-medium ${v.valid ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}
          >
            {v.valid ? `✓ Chain intact (${v.checked} entries)` : `✗ Chain broken at entry #${v.broken_at_id}`}
          </span>
        )}
      </PageTitle>
      <ErrorMessage error={entries.error} />
      {entries.isLoading && <Loading />}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="pb-3">Time</th>
                <th className="pb-3">User</th>
                <th className="pb-3">Action</th>
                <th className="pb-3">Entity</th>
                <th className="pb-3">Details</th>
                <th className="pb-3">Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {entries.data?.map((e) => (
                <tr key={e.id} className="align-top">
                  <td className="whitespace-nowrap py-2 pr-4 text-slate-500">{formatDateTime(e.created_at)}</td>
                  <td className="whitespace-nowrap py-2 pr-4">{userName(e.actor_id)}</td>
                  <td className="py-2 pr-4 font-mono text-xs">{e.action}</td>
                  <td className="whitespace-nowrap py-2 pr-4 text-slate-500">
                    {e.entity_type} {e.entity_id.slice(0, 8)}
                  </td>
                  <td className="py-2 pr-4 font-mono text-xs text-slate-500">
                    {Object.keys(e.details).length ? JSON.stringify(e.details) : ""}
                  </td>
                  <td className="py-2 font-mono text-xs text-slate-400" title={e.hash}>
                    {e.hash.slice(0, 10)}…
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
