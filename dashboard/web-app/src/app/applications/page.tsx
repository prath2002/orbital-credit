import Link from "next/link";
import { cookies } from "next/headers";
import { AUTH_BANKER_COOKIE } from "@/lib/auth";
import { getBankerApplications } from "@/lib/backend";
import { resolveActorHeadersFromCookies } from "@/lib/actor";
import { BankerApplicationItem } from "@/lib/types";

type ApplicationsPageProps = {
  searchParams: Promise<{
    banker_id?: string;
    zone?: string;
    q?: string;
  }>;
};

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);
}

function zoneClass(zone: string | null): string {
  if (zone === "GREEN") return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
  if (zone === "RED") return "bg-rose-500/15 text-rose-300 border-rose-500/30";
  return "bg-amber-500/15 text-amber-300 border-amber-500/30";
}

function extractErrorContext(error: string | null): { code: string; correlationId: string } {
  if (!error) return { code: "UNKNOWN_ERROR", correlationId: "n/a" };
  const jsonStart = error.indexOf("{");
  if (jsonStart === -1) return { code: "REQUEST_FAILED", correlationId: "n/a" };
  try {
    const parsed = JSON.parse(error.slice(jsonStart));
    return {
      code: parsed?.error?.code ?? "REQUEST_FAILED",
      correlationId: parsed?.error?.correlation_id ?? "n/a",
    };
  } catch {
    return { code: "REQUEST_FAILED", correlationId: "n/a" };
  }
}

export default async function ApplicationsPage({ searchParams }: ApplicationsPageProps) {
  const params = await searchParams;
  const cookieStore = await cookies();
  const actorHeaders = resolveActorHeadersFromCookies(cookieStore);
  const cookieBankerId = cookieStore.get(AUTH_BANKER_COOKIE)?.value;
  const bankerId = params.banker_id?.trim() || cookieBankerId || "";

  const applicationsResult = bankerId
    ? await getBankerApplications(bankerId, actorHeaders)
    : { data: null, error: "Missing banker_id" };
  const allApplications = applicationsResult.data?.applications ?? [];

  const query = (params.q ?? "").trim().toLowerCase();
  const zone = (params.zone ?? "").toUpperCase();

  const filteredApplications = allApplications.filter((application: BankerApplicationItem) => {
    const queryMatch =
      !query ||
      application.application_id.toLowerCase().includes(query) ||
      application.farmer_mobile.toLowerCase().includes(query);

    const zoneMatch = !zone || zone === "ALL" || (application.traffic_light_status ?? "YELLOW") === zone;
    return queryMatch && zoneMatch;
  });
  const errorContext = extractErrorContext(applicationsResult.error);

  return (
    <main className="min-h-screen bg-background-dark p-6 text-slate-100">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Application Queue</p>
            <h1 className="mt-1 text-3xl font-bold">Loan Application Queue</h1>
            <p className="mt-2 text-slate-300">
              Banker ID: <span className="font-semibold text-white">{bankerId || "N/A"}</span>
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:opacity-90" href="/applications/new">
              New Application
            </Link>
            <Link className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800" href="/profile">
              Profile & Settings
            </Link>
            <form action="/api/auth/logout" method="post">
              <button className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800" type="submit">
                Logout
              </button>
            </form>
          </div>
        </div>

        <form className="grid gap-3 rounded-xl border border-slate-700 bg-slate-900/70 p-4 sm:grid-cols-3">
          <input type="hidden" name="banker_id" value={bankerId} />
          <input
            type="text"
            name="q"
            defaultValue={params.q ?? ""}
            placeholder="Search application ID or mobile"
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white outline-none ring-primary focus:ring-2"
          />
          <select
            name="zone"
            defaultValue={zone || "ALL"}
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white outline-none ring-primary focus:ring-2"
          >
            <option value="ALL">All Zones</option>
            <option value="GREEN">Green</option>
            <option value="YELLOW">Yellow</option>
            <option value="RED">Red</option>
          </select>
          <button type="submit" className="rounded-lg bg-primary px-4 py-2 font-semibold text-white hover:opacity-90">
            Apply Filters
          </button>
        </form>

        {applicationsResult.error ? (
          <section className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-8 text-center">
            <h2 className="text-2xl font-bold text-rose-200">Connection Error</h2>
            <p className="mt-2 text-rose-100">
              Unable to load the application queue. This may be due to a network interruption or service maintenance.
            </p>
            <Link
              href={`/applications?banker_id=${encodeURIComponent(bankerId)}&zone=${encodeURIComponent(params.zone ?? "ALL")}&q=${encodeURIComponent(params.q ?? "")}`}
              className="mt-5 inline-flex rounded-lg bg-primary px-5 py-2 font-semibold text-white hover:opacity-90"
            >
              Retry Connection
            </Link>
            <div className="mx-auto mt-6 max-w-md rounded-lg border border-rose-500/20 bg-slate-900/60 p-4 text-left text-xs text-rose-100">
              <p className="font-semibold uppercase tracking-wide text-rose-200">Technical Details</p>
              <p className="mt-2">
                Error Code: <span className="font-mono">{errorContext.code}</span>
              </p>
              <p>
                Correlation ID: <span className="font-mono">{errorContext.correlationId}</span>
              </p>
              <p className="mt-1 text-rose-200/90">Raw: {applicationsResult.error}</p>
            </div>
          </section>
        ) : filteredApplications.length === 0 ? (
          <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-8 text-center">
            <h2 className="text-2xl font-bold text-white">No applications found</h2>
            <p className="mx-auto mt-2 max-w-xl text-slate-300">
              We could not find any applications matching your current filters. Try adjusting your search criteria or clear filters.
            </p>
            <div className="mt-5 flex items-center justify-center gap-3">
              <Link
                href={`/applications?banker_id=${encodeURIComponent(bankerId)}&zone=ALL&q=`}
                className="rounded-lg border border-slate-600 px-4 py-2 text-slate-200 hover:bg-slate-800"
              >
                Clear All Filters
              </Link>
              <Link className="rounded-lg bg-primary px-4 py-2 font-semibold text-white hover:opacity-90" href="/applications/new">
                Create Application
              </Link>
            </div>
          </section>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-900/70">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="border-b border-slate-700 bg-slate-800/70 text-slate-300">
                <tr>
                  <th className="px-4 py-3 font-medium">Application ID</th>
                  <th className="px-4 py-3 font-medium">Farmer Mobile</th>
                  <th className="px-4 py-3 font-medium">Loan Amount</th>
                  <th className="px-4 py-3 font-medium">Overall Score</th>
                  <th className="px-4 py-3 font-medium">Zone</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                  <th className="px-4 py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredApplications.map((application) => (
                  <tr key={application.application_id} className="border-b border-slate-800 last:border-none">
                    <td className="px-4 py-3 font-mono text-xs text-slate-200">{application.application_id}</td>
                    <td className="px-4 py-3">{application.farmer_mobile}</td>
                    <td className="px-4 py-3">{formatCurrency(application.loan_amount)}</td>
                    <td className="px-4 py-3">{application.overall_score ?? "-"}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full border px-2 py-1 text-xs font-semibold ${zoneClass(application.traffic_light_status)}`}>
                        {application.traffic_light_status ?? "YELLOW"}
                      </span>
                    </td>
                    <td className="px-4 py-3">{application.status}</td>
                    <td className="px-4 py-3">{new Date(application.created_at).toLocaleString("en-IN")}</td>
                    <td className="px-4 py-3">
                      <Link className="text-primary hover:underline" href={`/applications/${application.application_id}`}>
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
