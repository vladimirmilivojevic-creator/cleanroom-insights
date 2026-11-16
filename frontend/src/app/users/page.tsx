"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import AppShell from "@/components/AppShell";
import { buttonClass, Card, ErrorMessage, inputClass, PageTitle } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import type { Role, User } from "@/lib/types";

export default function UsersPage() {
  return (
    <AppShell>
      <Users />
    </AppShell>
  );
}

function Users() {
  const { user: me } = useAuth();
  const queryClient = useQueryClient();
  const users = useApi<User[]>("/api/users");
  const [error, setError] = useState<Error | null>(null);
  const [form, setForm] = useState({ full_name: "", email: "", role: "trainee" as Role, password: "" });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["/api/users"] });

  async function createUser(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/api/users", { method: "POST", body: JSON.stringify(form) });
      setForm({ full_name: "", email: "", role: "trainee", password: "" });
      refresh();
    } catch (err) {
      setError(err as Error);
    }
  }

  async function update(id: number, changes: Partial<Pick<User, "role" | "is_active">>) {
    setError(null);
    try {
      await api(`/api/users/${id}`, { method: "PATCH", body: JSON.stringify(changes) });
      refresh();
    } catch (err) {
      setError(err as Error);
    }
  }

  return (
    <>
      <PageTitle title="Users" subtitle="Accounts of your organisation. Every change is written to the audit trail." />
      <ErrorMessage error={error ?? users.error} />

      <Card title="Add user" className="mb-6">
        <form onSubmit={createUser} className="flex flex-wrap gap-2">
          <input
            className={inputClass}
            placeholder="Full name"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            required
          />
          <input
            className={inputClass}
            placeholder="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
          <select
            className={inputClass}
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value as Role })}
            aria-label="Role"
          >
            <option value="trainee">trainee</option>
            <option value="trainer">trainer</option>
            <option value="admin">admin</option>
          </select>
          <input
            className={inputClass}
            placeholder="Password (min. 8)"
            type="password"
            minLength={8}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
          <button className={buttonClass}>Add</button>
        </form>
      </Card>

      <Card>
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="pb-3">Name</th>
              <th className="pb-3">Email</th>
              <th className="pb-3">Role</th>
              <th className="pb-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {users.data?.map((u) => (
              <tr key={u.id}>
                <td className="py-2.5 font-medium">{u.full_name}</td>
                <td className="py-2.5 text-slate-500">{u.email}</td>
                <td className="py-2.5">
                  <select
                    className={inputClass}
                    value={u.role}
                    disabled={u.id === me?.id}
                    onChange={(e) => update(u.id, { role: e.target.value as Role })}
                    aria-label={`Role of ${u.full_name}`}
                  >
                    <option value="trainee">trainee</option>
                    <option value="trainer">trainer</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
                <td className="py-2.5">
                  <button
                    disabled={u.id === me?.id}
                    onClick={() => update(u.id, { is_active: !u.is_active })}
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 disabled:opacity-50 ${
                      u.is_active
                        ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                        : "bg-slate-100 text-slate-500 ring-slate-200"
                    }`}
                  >
                    {u.is_active ? "active" : "deactivated"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
