"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { buttonClass, inputClass } from "@/components/ui";
import { useAuth } from "@/lib/auth";

const DEMO_ACCOUNTS = [
  { label: "Trainer", email: "trainer@alpine.demo", hint: "live sessions, progress, heatmaps" },
  { label: "Admin", email: "admin@alpine.demo", hint: "+ users, audit trail, ETL" },
  { label: "Trainee", email: "lukas@alpine.demo", hint: "own progress and certificates" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function signIn(loginEmail: string, loginPassword: string) {
    setBusy(true);
    setError("");
    try {
      const me = await login(loginEmail, loginPassword);
      router.replace(me.role === "trainee" ? `/trainees/${me.id}` : "/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <span className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-xl bg-brand-600 font-semibold text-white">
            CI
          </span>
          <h1 className="text-2xl font-semibold">CleanroomInsights</h1>
          <p className="mt-1 text-sm text-slate-500">Analytics for VR cleanroom training</p>
        </div>

        <form
          className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          onSubmit={(e) => {
            e.preventDefault();
            signIn(email, password);
          }}
        >
          <label className="block text-sm">
            <span className="text-slate-600">Email</span>
            <input
              className={`${inputClass} mt-1 w-full`}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-600">Password</span>
            <input
              className={`${inputClass} mt-1 w-full`}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button className={`${buttonClass} w-full`} disabled={busy}>
            Sign in
          </button>
        </form>

        <div className="mt-6 rounded-xl border border-dashed border-slate-300 bg-white/60 p-4">
          <p className="mb-3 text-sm font-medium text-slate-600">Demo accounts (password demo1234)</p>
          <div className="space-y-2">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.email}
                onClick={() => signIn(account.email, "demo1234")}
                disabled={busy}
                className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-sm hover:border-brand-500"
              >
                <span>
                  <span className="font-medium">Log in as {account.label}</span>
                  <span className="block text-xs text-slate-500">{account.hint}</span>
                </span>
                <span className="text-xs text-slate-400">{account.email}</span>
              </button>
            ))}
          </div>
          <p className="mt-3 text-xs text-slate-400">
            The API runs on a free hosting plan: the first request after a quiet period can take up to a minute.
          </p>
        </div>
      </div>
    </div>
  );
}
