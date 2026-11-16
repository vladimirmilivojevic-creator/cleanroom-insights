"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import type { Role } from "@/lib/types";

const NAV: { href: string; label: string; roles: Role[] }[] = [
  { href: "/", label: "Dashboard", roles: ["admin", "trainer"] },
  { href: "/trainees", label: "Trainees", roles: ["admin", "trainer"] },
  { href: "/analytics", label: "Analytics", roles: ["admin", "trainer"] },
  { href: "/users", label: "Users", roles: ["admin"] },
  { href: "/audit", label: "Audit trail", roles: ["admin"] },
];

/** Layout for logged-in pages: top navigation filtered by role, redirects to /login if needed. */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) return <div className="p-10 text-sm text-slate-400">Loading…</div>;

  const links =
    user.role === "trainee"
      ? [{ href: `/trainees/${user.id}`, label: "My progress" }]
      : NAV.filter((n) => n.roles.includes(user.role));

  return (
    <div className="min-h-screen">
      <header className="no-print border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-8 gap-y-2 px-4 py-3 sm:px-6">
          <Link
            href={user.role === "trainee" ? `/trainees/${user.id}` : "/"}
            className="flex items-center gap-2 font-semibold"
          >
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-sm text-white">CI</span>
            CleanroomInsights
          </Link>
          <nav className="flex flex-wrap gap-1">
            {links.map((link) => {
              const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-md px-3 py-1.5 text-sm ${active ? "bg-brand-50 font-medium text-brand-700" : "text-slate-600 hover:bg-slate-100"}`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <div className="text-right leading-tight">
              <p className="font-medium" data-testid="current-user">
                {user.full_name}
              </p>
              <p className="text-xs text-slate-500">
                {user.role} · {user.organization_name}
              </p>
            </div>
            <button
              onClick={() => {
                logout();
                router.replace("/login");
              }}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-slate-600 hover:bg-slate-50"
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">{children}</main>
    </div>
  );
}
