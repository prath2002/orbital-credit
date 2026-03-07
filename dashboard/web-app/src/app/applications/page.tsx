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

  return (
    <main className="min-h-screen bg-background-dark p-6 text-slate-100">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold">Loan Application Queue</h1>
            <p className="mt-2 text-slate-300">
              Banker ID: <span className="font-semibold text-white">{bankerId || "N/A"}</span>
            </p>
          </div>
          <form action="/api/auth/logout" method="post">
            <button className="rounded-lg border border-slate-600 px-4 py-2 text-slate-200 hover:bg-slate-800" type="submit">
              Logout
            </button>
          </form>
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
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            Failed to load applications: {applicationsResult.error}
          </div>
        ) : null}

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
              {filteredApplications.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-400" colSpan={8}>
                    No applications found for this filter.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
