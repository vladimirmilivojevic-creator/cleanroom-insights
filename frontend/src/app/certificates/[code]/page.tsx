"use client";

import { useParams } from "next/navigation";
import { buttonClass, ErrorMessage, Loading } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { CertificateVerification } from "@/lib/types";

const MODULE_TITLES: Record<string, string> = {
  gowning: "Grade B gowning",
  aseptic_intervention: "Aseptic intervention (Grade A)",
};

/** Public, printable certificate. Anyone with the code (e.g. an auditor) can verify it. */
export default function CertificatePage() {
  const { code } = useParams<{ code: string }>();
  const { data, error } = useApi<CertificateVerification>(`/api/certificates/verify/${code}`);

  if (error)
    return (
      <div className="p-10">
        <ErrorMessage error={error} />
      </div>
    );
  if (!data)
    return (
      <div className="p-10">
        <Loading />
      </div>
    );

  return (
    <div className="mx-auto max-w-3xl p-6">
      <div className="no-print mb-4 flex justify-end">
        <button className={buttonClass} onClick={() => window.print()}>
          Print / save as PDF
        </button>
      </div>
      <div className="rounded-2xl border-8 border-double border-brand-600 bg-white p-12 text-center shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-brand-600">Certificate of training</p>
        <p className="mt-8 text-slate-500">This certifies that</p>
        <h1 className="mt-2 text-4xl font-semibold" data-testid="certificate-name">
          {data.trainee_name}
        </h1>
        <p className="mt-1 text-slate-500">{data.organization_name}</p>
        <p className="mt-8 text-slate-500">has successfully completed the VR training module</p>
        <h2 className="mt-2 text-2xl font-medium">{MODULE_TITLES[data.module] ?? data.module}</h2>
        <p className="mt-4 text-lg">
          with a score of <span className="font-semibold">{data.score} / 100</span>
        </p>
        <div className="mt-10 grid grid-cols-2 gap-6 text-sm">
          <div>
            <p className="text-slate-500">Issued</p>
            <p className="font-medium">{formatDate(data.issued_at)}</p>
          </div>
          <div>
            <p className="text-slate-500">Valid until</p>
            <p className="font-medium">{formatDate(data.valid_until)}</p>
          </div>
        </div>
        <p
          className={`mt-8 inline-block rounded-full px-3 py-1 text-sm font-medium ${data.valid ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}
        >
          {data.valid ? "✓ Valid" : "✗ Expired"}
        </p>
        <p className="mt-6 font-mono text-xs text-slate-400">Verification code: {data.code}</p>
      </div>
    </div>
  );
}
