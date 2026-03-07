import Link from "next/link";
import { cookies } from "next/headers";
import { getMetrics } from "@/lib/backend";
import { resolveActorHeadersFromCookies } from "@/lib/actor";

function parseMetrics(metricsText: string): Record<string, string> {
  const output: Record<string, string> = {};
  const lines = metricsText.split("\n");
  for (const line of lines) {
    if (!line || line.startsWith("#")) continue;
    if (line.startsWith("analysis_latency_seconds ")) {
      output.analysis_latency_seconds = line.split(" ")[1] || "0";
    } else if (line.startsWith("data_quality_low_total ")) {
      output.data_quality_low_total = line.split(" ")[1] || "0";
    } else if (line.startsWith("external_api_failures_total")) {
      output.external_api_failures_total = String((Number(output.external_api_failures_total || "0") + 1));
    } else if (line.startsWith("decision_zone_count")) {
      output.decision_zone_count = String((Number(output.decision_zone_count || "0") + 1));
    }
  }
  return output;
}

export default async function SystemStatusPage() {
  const cookieStore = await cookies();
  const actorHeaders = resolveActorHeadersFromCookies(cookieStore);
  const metricsResult = await getMetrics(actorHeaders);
  const parsed = metricsResult.data ? parseMetrics(metricsResult.data) : null;

  return (
    <main className="min-h-screen bg-background-dark p-6 text-slate-100">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-bold">System Status Monitoring</h1>
            <p className="mt-2 text-slate-300">Real-time health check for external data providers and internal engines.</p>
          </div>
          <Link className="rounded-lg border border-slate-600 px-4 py-2 text-slate-200" href="/">
            Home
          </Link>
        </div>

        {metricsResult.error ? (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            Failed to load metrics: {metricsResult.error}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
              <p className="text-sm text-slate-400">Satellite Data Stream</p>
              <p className="mt-2 text-2xl font-bold text-white">99.9% Uptime</p>
              <p className="mt-1 text-xs text-slate-400">Operational</p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
              <p className="text-sm text-slate-400">Debt Provider API</p>
              <p className="mt-2 text-2xl font-bold text-white">{parsed?.analysis_latency_seconds ?? "0"}s Avg Latency</p>
              <p className="mt-1 text-xs text-slate-400">Detected from live analysis metrics</p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
              <p className="text-sm text-slate-400">Social Risk Engine</p>
              <p className="mt-2 text-2xl font-bold text-white">{parsed?.decision_zone_count ?? "0"} Decision Events</p>
              <p className="mt-1 text-xs text-slate-400">External API failures: {parsed?.external_api_failures_total ?? "0"}</p>
            </div>
          </div>
        )}

        {metricsResult.data ? (
          <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
            <h2 className="font-semibold text-white">Raw Prometheus Metrics</h2>
            <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-200">{metricsResult.data}</pre>
          </section>
        ) : null}
      </div>
    </main>
  );
}
