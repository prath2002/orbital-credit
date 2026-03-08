import Link from "next/link";
import { cookies } from "next/headers";
import { DecisionActionPanel } from "@/components/decision-action-panel";
import { getRiskScore } from "@/lib/backend";
import { resolveActorHeadersFromCookies } from "@/lib/actor";

type DetailPageProps = {
  params: Promise<{
    applicationId: string;
  }>;
};

function zoneClass(zone: string | null): string {
  if (zone === "GREEN") return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
  if (zone === "RED") return "bg-rose-500/15 text-rose-300 border-rose-500/30";
  return "bg-amber-500/15 text-amber-300 border-amber-500/30";
}

function percent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return `${Math.round(value * 100)}%`;
}

export default async function ApplicationDetailPage({ params }: DetailPageProps) {
  const { applicationId } = await params;
  const cookieStore = await cookies();
  const actorHeaders = resolveActorHeadersFromCookies(cookieStore);
  const riskResult = await getRiskScore(applicationId, actorHeaders);

  return (
    <main className="min-h-screen bg-background-dark p-6 text-slate-100">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold">Application Risk Analysis</h1>
            <p className="mt-2 font-mono text-xs text-slate-300">Application ID: {applicationId}</p>
          </div>
          <div className="flex items-center gap-2">
            <Link className="rounded-lg border border-slate-600 px-4 py-2 text-slate-200" href="/applications">
              Back to Queue
            </Link>
            <Link className="rounded-lg border border-slate-600 px-4 py-2 text-slate-200" href="/system-status">
              System Status
            </Link>
          </div>
        </div>

        {riskResult.error || !riskResult.data ? (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            Failed to load risk score: {riskResult.error ?? "Unknown error"}
          </div>
        ) : (
          <>
            <section
              className={`rounded-xl border p-4 ${
                riskResult.data.traffic_light_status === "GREEN"
                  ? "border-emerald-500/30 bg-emerald-500/10"
                  : riskResult.data.traffic_light_status === "RED"
                    ? "border-rose-500/30 bg-rose-500/10"
                    : "border-amber-500/30 bg-amber-500/10"
              }`}
            >
              <p className="text-sm text-slate-100">
                Decision zone for this snapshot:{" "}
                <span className="font-semibold">{riskResult.data.traffic_light_status ?? "YELLOW"}</span>
              </p>
            </section>

            <section className="grid gap-4 md:grid-cols-4">
              <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
                <p className="text-sm text-slate-400">Overall Score</p>
                <p className="mt-2 text-3xl font-bold text-white">{riskResult.data.overall_score ?? "-"}</p>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4 md:col-span-2">
                <p className="text-sm text-slate-400">Traffic Light Status</p>
                <span className={`mt-2 inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${zoneClass(riskResult.data.traffic_light_status)}`}>
                  {riskResult.data.traffic_light_status ?? "YELLOW"}
                </span>
                <p className="mt-3 text-sm text-slate-300">{riskResult.data.rationale ?? "No rationale available."}</p>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
                <p className="text-sm text-slate-400">Processing Time</p>
                <p className="mt-2 text-2xl font-semibold text-white">{riskResult.data.metadata.processing_time_seconds}s</p>
              </div>
            </section>

            <section className="grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
                <h2 className="font-semibold text-white">Satellite</h2>
                <p className="mt-2 text-sm text-slate-300">Score: {riskResult.data.satellite.score ?? "-"}</p>
                <p className="text-sm text-slate-300">Status: {riskResult.data.satellite.status ?? "-"}</p>
                <p className="text-sm text-slate-300">Quality: {percent(riskResult.data.satellite.quality)}</p>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
                <h2 className="font-semibold text-white">Debt</h2>
                <p className="mt-2 text-sm text-slate-300">Score: {riskResult.data.debt.score ?? "-"}</p>
                <p className="text-sm text-slate-300">Status: {riskResult.data.debt.status ?? "-"}</p>
                <p className="text-sm text-slate-300">DTI Ratio: {riskResult.data.debt.debt_to_income_ratio ?? "-"}</p>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
                <h2 className="font-semibold text-white">Social</h2>
                <p className="mt-2 text-sm text-slate-300">Score: {riskResult.data.social.score ?? "-"}</p>
                <p className="text-sm text-slate-300">Status: {riskResult.data.social.status ?? "-"}</p>
                <p className="text-sm text-slate-300">Verified References: {riskResult.data.social.verified_references ?? "-"}</p>
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
              <h2 className="font-semibold text-white">Data Quality & Flags</h2>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-300">
                {(riskResult.data.metadata.data_quality_flags ?? []).map((flag) => (
                  <li key={flag}>{flag}</li>
                ))}
                {(riskResult.data.metadata.data_quality_flags ?? []).length === 0 ? <li>No active flags</li> : null}
              </ul>
            </section>

            {riskResult.data.traffic_light_status === "YELLOW" ? (
              <section className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
                <h2 className="font-semibold text-amber-200">YELLOW Explainability Bundle</h2>
                {riskResult.data.yellow_explanation ? (
                  <div className="mt-3 grid gap-4 md:grid-cols-2">
                    <div>
                      <h3 className="text-sm font-semibold text-amber-100">Primary Reasons</h3>
                      <ul className="mt-1 list-disc pl-5 text-sm text-amber-50">
                        {riskResult.data.yellow_explanation.primary_reasons.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-amber-100">Missing / Low Confidence Data</h3>
                      <ul className="mt-1 list-disc pl-5 text-sm text-amber-50">
                        {riskResult.data.yellow_explanation.missing_or_low_confidence_data.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-amber-100">Recommended Manual Checks</h3>
                      <ul className="mt-1 list-disc pl-5 text-sm text-amber-50">
                        {riskResult.data.yellow_explanation.recommended_manual_checks.map((check) => (
                          <li key={check}>{check}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="space-y-2 text-sm text-amber-50">
                      <div>
                        <h3 className="text-sm font-semibold text-amber-100">Expected Impact if Approved</h3>
                        <p>{riskResult.data.yellow_explanation.expected_impact_if_approved}</p>
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-amber-100">Expected Impact if Rejected</h3>
                        <p>{riskResult.data.yellow_explanation.expected_impact_if_rejected}</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-amber-100">
                    YELLOW explanation is not available yet for this assessment snapshot.
                  </p>
                )}
              </section>
            ) : null}

            <DecisionActionPanel applicationId={applicationId} risk={riskResult.data} />
          </>
        )}
      </div>
    </main>
  );
}
