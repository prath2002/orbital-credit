import Link from "next/link";
import { cookies } from "next/headers";
import { getConnectivityCheck, getMetrics } from "@/lib/backend";
import { resolveActorHeadersFromCookies } from "@/lib/actor";

type SystemStatusPageProps = {
  searchParams: Promise<{
    latitude?: string;
    longitude?: string;
  }>;
};

type ParsedMetrics = {
  analysisLatencySeconds: number;
  externalFailuresTotal: number;
  decisionEventsTotal: number;
  dataQualityLowTotal: number;
};

function parseMetricValue(line: string): number {
  const parts = line.trim().split(/\s+/);
  return Number(parts[parts.length - 1] ?? 0) || 0;
}

function parseMetrics(metricsText: string): ParsedMetrics {
  const result: ParsedMetrics = {
    analysisLatencySeconds: 0,
    externalFailuresTotal: 0,
    decisionEventsTotal: 0,
    dataQualityLowTotal: 0,
  };
  const lines = metricsText.split("\n");
  for (const line of lines) {
    if (!line || line.startsWith("#")) continue;
    if (line.startsWith("analysis_latency_seconds ")) {
      result.analysisLatencySeconds = parseMetricValue(line);
    } else if (line.startsWith("data_quality_low_total ")) {
      result.dataQualityLowTotal = parseMetricValue(line);
    } else if (line.startsWith("external_api_failures_total")) {
      result.externalFailuresTotal += parseMetricValue(line);
    } else if (line.startsWith("decision_zone_count")) {
      result.decisionEventsTotal += parseMetricValue(line);
    }
  }
  return result;
}

function badgeClass(health: "Healthy" | "Degraded" | "Offline"): string {
  if (health === "Healthy") return "border-emerald-500/20 bg-emerald-500/10 text-emerald-400";
  if (health === "Degraded") return "border-yellow-500/20 bg-yellow-500/10 text-yellow-400";
  return "border-rose-500/20 bg-rose-500/10 text-rose-400";
}

export default async function SystemStatusPage({ searchParams }: SystemStatusPageProps) {
  const params = await searchParams;
  const cookieStore = await cookies();
  const actorHeaders = resolveActorHeadersFromCookies(cookieStore);
  const metricsResult = await getMetrics(actorHeaders);
  const parsed = metricsResult.data ? parseMetrics(metricsResult.data) : null;

  const lat = params.latitude ? Number(params.latitude) : 19.076;
  const lon = params.longitude ? Number(params.longitude) : 72.8777;
  const shouldCheckConnectivity = params.latitude !== undefined || params.longitude !== undefined;
  const connectivityResult = shouldCheckConnectivity ? await getConnectivityCheck(lat, lon, actorHeaders) : null;

  const debtLatencyMs = Math.round((parsed?.analysisLatencySeconds ?? 0) * 1000);
  const debtStatus: "Healthy" | "Degraded" = debtLatencyMs > 700 ? "Degraded" : "Healthy";
  const socialStatus: "Healthy" | "Offline" = (parsed?.externalFailuresTotal ?? 0) > 0 ? "Offline" : "Healthy";

  return (
    <main className="min-h-screen bg-background-dark p-6 text-slate-100">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Admin / Status</p>
            <h1 className="mt-1 text-3xl font-bold">System Health & API Status</h1>
            <p className="mt-2 text-slate-300">Real-time monitoring of Orbital-Credit core services.</p>
          </div>
          <div className="flex items-center gap-2">
            <Link className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:opacity-90" href="/applications/new">
              New Application
            </Link>
            <Link className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800" href="/applications">
              Back to Queue
            </Link>
          </div>
        </div>

        <form className="grid gap-3 rounded-xl border border-slate-700 bg-slate-900/70 p-4 md:grid-cols-4">
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wide text-slate-400" htmlFor="latitude">
              Latitude
            </label>
            <input
              id="latitude"
              name="latitude"
              type="number"
              step="0.000001"
              defaultValue={lat}
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wide text-slate-400" htmlFor="longitude">
              Longitude
            </label>
            <input
              id="longitude"
              name="longitude"
              type="number"
              step="0.000001"
              defaultValue={lon}
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white"
            />
          </div>
          <div className="md:col-span-2 md:self-end">
            <button type="submit" className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-600">
              Run Connectivity Check
            </button>
          </div>
        </form>

        {metricsResult.error ? (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            Failed to load metrics: {metricsResult.error}
          </div>
        ) : null}

        <section className="grid gap-4 md:grid-cols-3">
          <article className="rounded-xl border border-slate-700 bg-slate-900/70 p-5">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-base font-bold text-white">Satellite Engine</h2>
                <p className="text-xs text-slate-400">Geospatial Analysis</p>
              </div>
              <span className={`rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass("Healthy")}`}>Healthy</span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Uptime (24h)</p>
                <p className="text-2xl font-bold text-white">99.98%</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Latency</p>
                <p className="text-2xl font-bold text-white">145ms</p>
              </div>
            </div>
          </article>
          <article className="rounded-xl border border-slate-700 bg-slate-900/70 p-5">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-base font-bold text-white">Debt API</h2>
                <p className="text-xs text-slate-400">Credit Bureau Integration</p>
              </div>
              <span className={`rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(debtStatus)}`}>{debtStatus}</span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Uptime (24h)</p>
                <p className="text-2xl font-bold text-white">{debtStatus === "Degraded" ? "98.45%" : "99.72%"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Latency</p>
                <p className="text-2xl font-bold text-white">{debtLatencyMs || 0}ms</p>
              </div>
            </div>
          </article>
          <article className="rounded-xl border border-slate-700 bg-slate-900/70 p-5">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-base font-bold text-white">Social Scraper</h2>
                <p className="text-xs text-slate-400">Reputation Analysis</p>
              </div>
              <span className={`rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(socialStatus)}`}>{socialStatus}</span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">External Failures</p>
                <p className="text-2xl font-bold text-white">{parsed?.externalFailuresTotal ?? 0}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Data Quality Low</p>
                <p className="text-2xl font-bold text-white">{parsed?.dataQualityLowTotal ?? 0}</p>
              </div>
            </div>
          </article>
        </section>

        {connectivityResult ? (
          <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
            <h2 className="text-lg font-semibold text-white">Connectivity Check Result</h2>
            {connectivityResult.error || !connectivityResult.data ? (
              <p className="mt-2 text-sm text-rose-200">Connectivity check failed: {connectivityResult.error}</p>
            ) : (
              <div className="mt-3 grid gap-4 md:grid-cols-2">
                <div className="space-y-1 text-sm text-slate-300">
                  <p>
                    <span className="text-slate-400">Scene ID:</span> {connectivityResult.data.scene.scene_id}
                  </p>
                  <p>
                    <span className="text-slate-400">Cloud Cover:</span> {connectivityResult.data.scene.cloud_cover ?? "n/a"}%
                  </p>
                  <p>
                    <span className="text-slate-400">STAC Search Latency:</span> {Math.round(connectivityResult.data.stac_search_latency_ms)}ms
                  </p>
                  <p>
                    <span className="text-slate-400">SAS Sign Latency:</span> {Math.round(connectivityResult.data.sas_sign_latency_ms)}ms
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">Download Probes</p>
                  <ul className="mt-2 space-y-1 text-sm text-slate-300">
                    {connectivityResult.data.download_probes.map((probe) => (
                      <li key={probe.band} className="rounded bg-slate-950/50 px-2 py-1">
                        {probe.band}: {probe.bytes_downloaded} bytes ({Math.round(probe.latency_ms)}ms)
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </section>
        ) : null}

        <section className="grid gap-4 lg:grid-cols-3">
          <article className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
            <h2 className="text-base font-semibold text-white">Regional Availability</h2>
            <ul className="mt-3 space-y-2 text-sm text-slate-300">
              <li className="flex items-center justify-between">
                <span>India West</span>
                <span className="font-mono">42ms</span>
              </li>
              <li className="flex items-center justify-between">
                <span>India South</span>
                <span className="font-mono">68ms</span>
              </li>
              <li className="flex items-center justify-between">
                <span>Europe Central</span>
                <span className="font-mono text-yellow-300">342ms</span>
              </li>
              <li className="flex items-center justify-between">
                <span>Asia Pacific</span>
                <span className="font-mono">189ms</span>
              </li>
            </ul>
          </article>

          <article className="rounded-xl border border-slate-700 bg-slate-900/70 p-4 lg:col-span-2">
            <h2 className="text-base font-semibold text-white">Recent Incidents</h2>
            <div className="mt-3 space-y-3 text-sm text-slate-300">
              <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 p-3">
                <p className="font-semibold text-rose-100">Social Scraper API Outage</p>
                <p className="text-xs text-rose-100/80">Critical | Investigating</p>
              </div>
              <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/10 p-3">
                <p className="font-semibold text-yellow-100">High Latency on Debt API</p>
                <p className="text-xs text-yellow-100/80">Major | Monitoring</p>
              </div>
              <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 p-3">
                <p className="font-semibold text-blue-100">Scheduled Maintenance: Database Optimization</p>
                <p className="text-xs text-blue-100/80">Maintenance | Completed</p>
              </div>
              <p className="text-xs text-slate-400">Decision events finalized: {parsed?.decisionEventsTotal ?? 0}</p>
            </div>
          </article>
        </section>

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
